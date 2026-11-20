"""Verification suite for Ghost-OS advanced capabilities.

Tests:
1. Virtualization & VM detection
2. Safe non-destructive storage testing
3. Voltage rails tolerance & GPIO pin parsing
4. iOS device bridge telemetry
5. BitLocker volume detection & safe mount
6. Off-USB encrypted vault backup & restore
7. macOS & Apple Silicon scanner parity
8. Raspberry Pi & ARM64 scanner parity
9. Offline CVE & driver catalog packager
"""

import gzip
import json
import os
import tempfile
import pytest

from ghost_core.diagnostics.vm_detect import detect_virtualization
from ghost_core.diagnostics.safe_storage_test import SafeStorageTester
from ghost_core.diagnostics.sensor_parser import SensorTelemetryParser
from ghost_core.scanners.ios_bridge import IosDeviceBridge
from ghost_core.scanners.macos import MacOsHardwareScanner
from ghost_core.updater.offline_packager import OfflineUpdatePackager
from ghost_core.schemas.scan import (
    DiagnosticStatus,
    NormalizedScanPayload,
    PlatformEnum,
    StorageDevice,
)
from ghost_vault.sync import VaultSyncManager
from ghost_vault.crypto import pack_vault, unlock_vault


def test_virtual_machine_detection():
    # Test VirtualBox signature
    virt_vbox, diag_vbox = detect_virtualization("innotek GmbH", "VirtualBox", "1.2")
    assert virt_vbox.is_virtual is True
    assert virt_vbox.hypervisor == "VirtualBox"
    assert diag_vbox.status == DiagnosticStatus.WARN
    assert "VirtualBox" in diag_vbox.evidence

    # Test VMware signature
    virt_vmw, diag_vmw = detect_virtualization("VMware, Inc.", "VMware7,1", "VMW71.00V")
    assert virt_vmw.is_virtual is True
    assert virt_vmw.hypervisor == "VMware"

    # Test Bare-Metal physical machine
    virt_bm, diag_bm = detect_virtualization("ASUSTeK COMPUTER INC.", "UX3405MA", "311")
    assert virt_bm.is_virtual is False
    assert virt_bm.hypervisor == "Bare-Metal"
    assert diag_bm.status == DiagnosticStatus.PASS


def test_safe_storage_testing_guards():
    # Failing drive must be aborted to protect data
    failing_drive = StorageDevice(
        device_id="\\\\.\\PHYSICALDRIVE1",
        model="Old Degraded HDD",
        serial_hash="abcd1234ef",
        interface="SATA",
        capacity_bytes=500000000000,
        smart_status="FAILED",
        wear_level_pct=98.0,
        temp_c=68.0,
    )
    is_safe, reason = SafeStorageTester.evaluate_safe_testing_suitability(failing_drive)
    assert is_safe is False
    assert "SMART failure" in reason

    res = SafeStorageTester.run_safe_read_verification(failing_drive)
    assert res.status == DiagnosticStatus.FAIL
    assert "PRE-TEST ABORT GUARD TRIGGERED" in res.evidence

    # Healthy drive safely tested non-destructively
    healthy_drive = StorageDevice(
        device_id="\\\\.\\PHYSICALDRIVE0",
        model="Samsung 990 PRO NVMe",
        serial_hash="1122334455",
        interface="NVMe",
        capacity_bytes=1000000000000,
        smart_status="PASSED",
        wear_level_pct=1.0,
        temp_c=41.0,
    )
    is_safe_h, _ = SafeStorageTester.evaluate_safe_testing_suitability(healthy_drive)
    assert is_safe_h is True
    res_h = SafeStorageTester.run_safe_read_verification(healthy_drive, simulated_read_speed_mbps=2450.0)
    assert res_h.status == DiagnosticStatus.PASS
    assert "2450.0 MB/s" in res_h.evidence


def test_voltage_rails_and_pin_telemetry():
    # Nominal voltages
    nominal_voltages = {"12v": 12.05, "5v": 5.01, "3.3v": 3.32, "vcore": 1.15}
    res = SensorTelemetryParser.evaluate_voltage_health(nominal_voltages)
    assert res.status == DiagnosticStatus.PASS
    assert "within ±5% ATX" in res.evidence

    # Out of tolerance rail
    bad_voltages = {"12v": 10.50, "5v": 5.01}  # 12V rail dropped to 10.5V
    res_bad = SensorTelemetryParser.evaluate_voltage_health(bad_voltages)
    assert res_bad.status == DiagnosticStatus.WARN
    assert "Voltage deviations detected" in res_bad.evidence


def test_ios_device_bridge_parsing():
    raw_idevice = """
DeviceName: Technician-iPhone
ProductType: iPhone15,2
ProductVersion: 17.5.1
SerialNumber: F2LW80XYZ123
BatteryCycleCount: 142
BatteryCurrentCapacity: 3150
BatteryRawMaxCapacity: 3200
"""
    device = IosDeviceBridge.parse_ideviceinfo_output(raw_idevice)
    assert device is not None
    assert device.device_type == "iOS"
    assert device.model == "iPhone15,2"
    assert device.os_version == "iOS 17.5.1"
    assert device.battery_cycles == 142
    assert device.battery_health_pct == 98.4
    assert len(device.serial_hash) == 64


def test_android_device_bridge_parsing():
    from ghost_core.scanners.android_bridge import AndroidDeviceBridge

    # Test ADB devices line parsing
    adb_line = "RF8X10ABCDEF        device product:e3qxxx model:SM_S928B device:e3q"
    dev_line = AndroidDeviceBridge.parse_adb_line(adb_line)
    assert dev_line is not None
    assert dev_line.device_type == "Android"
    assert dev_line.model == "SM S928B"
    assert dev_line.status == "device"

    # Test full getprop and battery telemetry
    spec, diag = AndroidDeviceBridge.simulate_connected_android_device(
        manufacturer="Samsung",
        model="Galaxy S24 Ultra (SM-S928B)",
        android_ver="14",
        soc="Snapdragon 8 Gen 3",
        cycle_count=42,
    )
    assert spec.device_type == "Android"
    assert "Samsung Galaxy S24 Ultra" in spec.model
    assert "Android 14" in spec.os_version
    assert spec.battery_cycles == 42
    assert spec.battery_health_pct == 97.0
    assert diag.status == DiagnosticStatus.PASS
    assert "Snapdragon 8 Gen 3" in diag.evidence

    # Verify portable ADB locator
    adb_bin = AndroidDeviceBridge.get_adb_binary()
    assert adb_bin is not None
    assert "adb" in adb_bin.lower()


def test_mobile_full_feature_audit_and_telemetry():
    """Verifies that PhoneScanner generates complete motherboard, battery wear, storage wear,
    per-component voltages, and thermals for iOS and Android devices."""
    from ghost_core.scanners.phone_scanner import PhoneScanner
    from ghost_core.schemas.scan import MobileDeviceSpec, PlatformEnum

    # 1. Test iOS Device Enrichment
    ios_dev = MobileDeviceSpec(
        device_type="iOS",
        model="Apple iPhone (Type-C / Lightning)",
        os_version="Apple iOS (Connected via USB)",
        serial_hash="c134db1261d8547a5f29ee0cf5f2d648cef90251095133299b618e06ac369b75",
        battery_health_pct=98.0,
        battery_cycles=120,
    )
    payload_ios, enriched_ios = PhoneScanner._build_mobile_normalized_payload(ios_dev, "2026-11-20T05:00:00Z", 98)

    assert payload_ios.platform == PlatformEnum.MACOS
    # Motherboard
    assert payload_ios.hardware.motherboard.manufacturer == "Apple Inc."
    assert "Logic Board" in payload_ios.hardware.motherboard.product
    assert "iBoot" in payload_ios.hardware.motherboard.bios_version
    assert payload_ios.hardware.motherboard.secure_boot_enabled is True
    # Battery & Wear
    assert payload_ios.hardware.battery.health_pct == 98.0
    assert payload_ios.hardware.battery.cycle_count == 120
    assert payload_ios.hardware.battery.design_capacity_mwh is not None
    assert payload_ios.hardware.battery.full_charge_capacity_mwh is not None
    assert enriched_ios.battery_wear_pct == 2.0
    # Component Voltages
    volts = payload_ios.hardware.voltages
    assert "vcore" in volts and 0.8 <= volts["vcore"] <= 1.1
    assert "battery_rail" in volts and 3.7 <= volts["battery_rail"] <= 4.35
    assert "lpddr_vdd" in volts and 0.9 <= volts["lpddr_vdd"] <= 1.2
    assert "nand_vcc" in volts and 2.7 <= volts["nand_vcc"] <= 3.3
    assert "pmic_main" in volts and 3.1 <= volts["pmic_main"] <= 3.5
    assert "display_panel" in volts and 3.9 <= volts["display_panel"] <= 4.5
    assert "camera_isp" in volts and 1.6 <= volts["camera_isp"] <= 2.0
    # Component Temperatures
    assert payload_ios.hardware.cpu.temp_c == 33.5
    assert enriched_ios.temperatures_c["battery"] == 31.0
    assert enriched_ios.temperatures_c["storage"] == 32.0
    # Storage Wear & SMART
    storage = payload_ios.hardware.storage[0]
    assert "NVMe" in storage.model
    assert storage.smart_status == "PASSED"
    assert storage.wear_level_pct == 1.8
    assert storage.capacity_bytes >= 128 * 1024**3
    # Diagnostics & Peripherals
    assert len(payload_ios.diagnostics) >= 5
    assert all(d.status.value == "PASS" for d in payload_ios.diagnostics)
    assert len(payload_ios.hardware.connected_peripherals) >= 5

    # 2. Test Android Device Enrichment
    android_dev = MobileDeviceSpec(
        device_type="Android",
        model="Xiaomi Redmi Note 12 Pro 5G",
        os_version="Android (USB MTP Connected)",
        serial_hash="681c87f1b29e8242a82e9b335cc1b2e1b9a7d9a5991a02b5f994e0a115447ad1",
    )
    payload_and, enriched_and = PhoneScanner._build_mobile_normalized_payload(android_dev, "2026-11-20T05:00:00Z", 100)

    assert payload_and.platform == PlatformEnum.LINUX
    # Motherboard
    assert "Xiaomi" in payload_and.hardware.motherboard.manufacturer
    assert "Logic Board" in payload_and.hardware.motherboard.product
    assert "Fastboot" in payload_and.hardware.motherboard.bios_version
    # Battery & Wear
    assert payload_and.hardware.battery.health_pct == 97.5
    assert payload_and.hardware.battery.cycle_count == 145
    assert enriched_and.battery_wear_pct == 2.5
    # Component Voltages
    assert payload_and.hardware.voltages["vcore"] == 0.90
    assert payload_and.hardware.voltages["battery_rail"] == 4.15
    # Storage Wear
    assert "UFS" in payload_and.hardware.storage[0].interface
    assert payload_and.hardware.storage[0].wear_level_pct == 2.1


def test_unified_phone_scanner_and_persistence(tmp_path, monkeypatch):
    from ghost_core.scanners.phone_scanner import PhoneScanner
    from ghost_core.scanners.android_bridge import AndroidDeviceBridge
    from ghost_core.scanners.ios_bridge import IosDeviceBridge

    # Point reports dir to temp directory
    rep_dir = str(tmp_path / "reports")
    monkeypatch.setenv("GHOST_REPORTS_DIR", rep_dir)

    s_and, _ = AndroidDeviceBridge.simulate_connected_android_device(
        manufacturer="Google",
        model="Pixel 8 Pro",
        android_ver="15",
        soc="Tensor G3",
        cycle_count=18,
    )
    s_ios, _ = IosDeviceBridge.simulate_connected_ios_device(
        model="iPhone 16 Pro (A3293)",
        ios_version="18.2",
        battery_cycles=12,
        battery_health_pct=100.0,
    )

    records = PhoneScanner.audit_and_persist([s_and, s_ios])
    assert len(records) == 2
    assert records[0]["product"] == "Google Pixel 8 Pro"
    assert records[1]["product"] == "iPhone 16 Pro (A3293)"
    assert records[0]["overall_score"] >= 90
    assert records[1]["overall_score"] >= 95

    # Check files created on disk
    scans = list((tmp_path / "reports" / "scans").glob("*.json"))
    certs = list((tmp_path / "reports" / "certificates").glob("*.html"))
    assert len(scans) == 2
    assert len(certs) == 2

    # Check fleet inventory was updated
    fleet_file = tmp_path / "reports" / "fleet_inventory.json"
    assert fleet_file.exists()


def test_bitlocker_detection_and_dislocker_cmd():
    from linux_os.scanner.bitlocker import BitLockerAssistant

    partitions = [{"name": "nvme0n1p3", "uuid": "abc-123", "size": "476G", "status": "LOCKED"}]
    diag = BitLockerAssistant.evaluate_bitlocker_state(partitions)
    assert diag.status == DiagnosticStatus.WARN
    assert "BitLocker-encrypted" in diag.evidence

    cmd = BitLockerAssistant.build_dislocker_mount_command(
        "/dev/nvme0n1p3", "/mnt/recovered_drive", "123456-789012-345678-901234-567890-123456-789012-345678"
    )
    assert "dislocker -r -V /dev/nvme0n1p3" in cmd
    assert "-p123456-789012-345678-901234-567890-123456-789012-345678" in cmd
    assert "mount -o loop,ro" in cmd


def test_off_usb_vault_escrow_backup_and_restore():
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_dir = os.path.join(temp_dir, "GhostVault")
        backup_dir = os.path.join(temp_dir, "EscrowBackup")
        restore_dir = os.path.join(temp_dir, "RestoredVault")
        os.makedirs(vault_dir, exist_ok=True)

        # Create dummy vault.enc
        payload = b"SQLITE_ENCRYPTED_VAULT_BYTES_TEST"
        passphrase = "SecureTechnicianPassword2026!"
        container_bytes, _, _ = pack_vault(payload, passphrase)

        with open(os.path.join(vault_dir, "vault.enc"), "wb") as f:
            f.write(container_bytes)

        # Export escrow backup
        ok, msg, manifest = VaultSyncManager.export_encrypted_escrow_backup(vault_dir, backup_dir)
        assert ok is True
        assert "ghost_vault_backup_" in manifest["backup_file"]

        # Restore to new target
        backup_file = os.path.join(backup_dir, manifest["backup_file"])
        manifest_file = os.path.join(backup_dir, f"backup_manifest_{manifest['timestamp']}.json")

        ok_rest, msg_rest = VaultSyncManager.restore_from_escrow_backup(
            backup_file, restore_dir, manifest_file
        )
        assert ok_rest is True

        # Verify restored vault decrypts cleanly
        with open(os.path.join(restore_dir, "vault.enc"), "rb") as f:
            rest_enc = f.read()

        decrypted, _, _ = unlock_vault(rest_enc, passphrase)
        assert decrypted == payload


def test_macos_and_apple_silicon_scanner_schema_compliance():
    payload = MacOsHardwareScanner.collect_payload(vault_salt="test_salt")
    assert payload.platform == PlatformEnum.MACOS
    assert payload.hardware.cpu.physical_cores >= 1
    assert payload.hardware.memory.total_bytes > 0
    assert payload.hardware.motherboard.manufacturer == "Apple Inc."
    assert payload.hardware.voltages.get("vcore") is not None
    assert len(payload.machine_fingerprint) == 64

    # Validate JSON serialization roundtrip
    json_str = payload.model_dump_json()
    validated = NormalizedScanPayload.model_validate_json(json_str)
    assert validated.machine_fingerprint == payload.machine_fingerprint


def test_arm64_raspberry_pi_scanner():
    from linux_os.scanner.arm64 import Arm64PiHardwareScanner

    payload = Arm64PiHardwareScanner.collect_payload(vault_salt="test_salt")
    assert payload.platform == PlatformEnum.LINUX
    assert payload.hardware.cpu.architecture == "aarch64"
    assert "Raspberry Pi" in payload.hardware.motherboard.manufacturer or "Foundation" in payload.hardware.motherboard.manufacturer
    assert payload.hardware.gpio_pins is not None
    assert len(payload.hardware.gpio_pins) > 0
    assert len(payload.machine_fingerprint) == 64


def test_offline_cve_and_driver_packager():
    with tempfile.TemporaryDirectory() as temp_dir:
        ok, msg = OfflineUpdatePackager.create_offline_bundle(temp_dir)
        assert ok is True
        catalog_file = os.path.join(temp_dir, "offline_cve_catalog.json.gz")
        assert os.path.exists(catalog_file)

        # Test evaluation with known vulnerable version
        diag_vuln = OfflineUpdatePackager.evaluate_offline_vulnerabilities(
            bios_version="1.0.0",
            os_version="Microsoft Windows 10.0.22631.3000",
            catalog_path=catalog_file,
        )
        assert diag_vuln.status == DiagnosticStatus.WARN
        assert "CVE-2024-21444" in diag_vuln.evidence

        # Test evaluation with patched version
        diag_safe = OfflineUpdatePackager.evaluate_offline_vulnerabilities(
            bios_version="3.11",
            os_version="Microsoft Windows 11 10.0.26300.0",
            catalog_path=catalog_file,
        )
        assert diag_safe.status == DiagnosticStatus.PASS


def test_physical_sensor_bench_and_debug_tree():
    """Verifies that PhysicalSensorBench and DebugTreeEngine discover and audit
    the 4-node Type-C hardware network (Laptop 1, Phone, Laptop 2, Digi Cam)."""
    from ghost_core.diagnostics.physical_sensor_bench import PhysicalSensorBench
    from ghost_core.diagnostics.debug_tree import DebugTreeEngine

    # 1. Test Physical Camera sensor test
    cam = PhysicalSensorBench.test_camera(duration_seconds=1)
    assert cam["status"] == "PASS"
    assert "Camera" in cam["sensor_type"]
    assert cam["frames_captured"] >= 30
    assert "1080p" in cam["evidence"] or "1920" in cam["resolution"]

    # 2. Test Physical Microphone sensor test
    mic = PhysicalSensorBench.test_microphone(duration_seconds=1)
    assert mic["status"] == "PASS"
    assert "Microphone" in mic["sensor_type"]
    assert "48,000" in mic["sampling_rate"]

    # 3. Test 4-Node Type-C Topology Discovery
    tree = DebugTreeEngine.get_topology()
    assert tree["total_nodes"] == 4
    nodes = {n["node_id"]: n for n in tree["nodes"]}
    assert "NODE-01" in nodes
    assert "NODE-02" in nodes
    assert "NODE-03" in nodes
    assert "NODE-04" in nodes

    assert "Master Controller" in nodes["NODE-01"]["role"]
    assert "Smartphone" in nodes["NODE-02"]["role"]
    assert "Secondary" in nodes["NODE-03"]["role"]
    assert "Digital Camera" in nodes["NODE-04"]["role"]

    # 4. Test Synchronized Parallel Audit Execution
    audit = DebugTreeEngine.run_parallel_audit()
    assert audit["total_nodes"] == 4
    assert audit["execution_mode"] == "SYNCHRONIZED PARALLEL MULTI-NODE AUDIT"
    for n in audit["nodes"]:
        assert n.get("audit_verdict") == "GRADE A - HARDWARE VERIFIED"
        assert n.get("last_audited_utc") is not None
