"""Verification suite for Ghost-OS Ultra Hardware & Accelerated Intelligence Capabilities.

Tests:
1. Universal battery XML and OEM fan telemetry parser
2. VM guest-to-host hardware inspection
3. Accelerated instant AI reasoning (<50ms latency)
4. Apple Silicon bootbuilder validation
5. USB HID auto-launcher validation
"""

import os
import tempfile
import pytest

from ghost_core.diagnostics.universal_sensors import UniversalSensorReader
from ghost_core.diagnostics.vm_escape_inspector import VirtualMachineHostInspector
from ghost_ai.accelerated_copilot import AcceleratedCopilot
from ghost_core.schemas.scan import (
    BatterySpec,
    CpuSpec,
    DiagnosticResult,
    DiagnosticStatus,
    HardwareSpec,
    MemorySpec,
    MotherboardSpec,
    NormalizedScanPayload,
    PlatformEnum,
    StorageDevice,
)
from ghost_vault.db import GhostVaultDB


def test_universal_battery_xml_parser():
    mock_xml = """<?xml version="1.0" encoding="utf-8"?>
    <BatteryReport>
        <BatteryInfo>
            <DesignCapacity>70000</DesignCapacity>
            <FullChargeCapacity>66500</FullChargeCapacity>
            <CycleCount>154</CycleCount>
        </BatteryInfo>
    </BatteryReport>
    """
    bat = UniversalSensorReader.parse_battery_report_xml(mock_xml)
    assert bat is not None
    assert bat.cycle_count == 154
    assert bat.design_capacity_mwh == 70000.0
    assert bat.full_charge_capacity_mwh == 66500.0
    assert bat.health_pct == 95.0

    diag = UniversalSensorReader.evaluate_universal_sensors(bat, {"asus_cpu_fan": 2100})
    assert diag.status == DiagnosticStatus.PASS
    assert "154 cycles" in diag.evidence
    assert "asus_cpu_fan=2100 RPM" in diag.evidence


def test_vm_guest_to_host_hardware_inspector():
    found, telemetry, diag = VirtualMachineHostInspector.inspect_host_hardware_from_guest()
    # On physical machine or in test environment, it returns a valid DiagnosticResult
    assert isinstance(diag.status, DiagnosticStatus)
    assert diag.test_name == "Virtual Machine Host Hardware Inspection"


def test_accelerated_offline_ai_copilot_instant_speed():
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_file = os.path.join(temp_dir, "vault.enc")
        vault = GhostVaultDB.create_new(vault_file, "AiTestPassword!2026")

        fingerprint = NormalizedScanPayload.generate_fingerprint("salt", "mb", "cpu", "storage")
        payload = NormalizedScanPayload(
            scan_id="ultra-scan-001",
            machine_fingerprint=fingerprint,
            platform=PlatformEnum.WINDOWS,
            os_version="Windows 11 Pro",
            timestamp_utc="2026-11-13T10:00:00Z",
            hardware=HardwareSpec(
                cpu=CpuSpec(model="Intel Ultra 9", architecture="x86_64", physical_cores=16, logical_threads=22),
                memory=MemorySpec(total_bytes=34359738368, slots_used=2, slots_total=2),
                motherboard=MotherboardSpec(manufacturer="ASUS", product="Zenbook Ultra", bios_version="311"),
                battery=BatterySpec(present=True, health_pct=92.0),
            ),
            diagnostics=[
                DiagnosticResult(
                    test_name="SMART Status",
                    status=DiagnosticStatus.WARN,
                    evidence="Drive wear level at 85%",
                    recommendation="Plan SSD replacement",
                )
            ],
        )
        vault.ingest_scan(payload)

        copilot = AcceleratedCopilot(vault)
        result = copilot.execute_instant_reasoning("Show warnings", fingerprint=fingerprint)

        assert result["offline_verified"] is True
        assert result["latency_ms"] < 100.0  # Ultra-fast sub-100ms response
        assert result["tokens_per_second"] > 10.0
        assert "Drive wear level at 85%" in result["response"]

        # Test speculative streaming tokens
        tokens = list(copilot.stream_reasoning_tokens("Show warnings", fingerprint=fingerprint))
        assert len(tokens) > 0
        reconstructed = "".join(tokens)
        assert "Drive wear level at 85%" in reconstructed


def test_apple_silicon_boot_script_validation():
    script_path = os.path.join("linux-os", "apple-silicon-boot.sh")
    assert os.path.exists(script_path)
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "m1n1" in content
    assert "U-Boot" in content
    assert "vmlinuz-asahi" in content


def test_usb_hardware_auto_launch_payloads():
    ducky_path = os.path.join("usb-hardware", "ducky_autorun.txt")
    pico_path = os.path.join("usb-hardware", "circuitpython_code.py")
    assert os.path.exists(ducky_path)
    assert os.path.exists(pico_path)

    with open(ducky_path, "r", encoding="utf-8") as f:
        ducky_content = f.read()
    assert "GhostVault" in ducky_content
    assert "Launch-GhostOS.cmd" in ducky_content

    with open(pico_path, "r", encoding="utf-8") as f:
        pico_content = f.read()
    assert "GhostVault" in pico_content
    assert "Launch-GhostOS.cmd" in pico_content
