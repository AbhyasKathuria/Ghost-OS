"""Gate 2 Verification: Hardware Change Detection, Parity & Diagnostics.

Verifies:
1. Cross-OS schema parity between Windows and Linux scan payloads.
2. Hardware upgrade detection (RAM expansion, speed increases).
3. Component replacement detection (SSD drive swapped).
4. Firmware / configuration changes (BIOS version update, GPU driver update).
5. Degradation alerts (Battery health drop > 2%, SSD wear increase, rising thermals).
6. Deterministic rules engine health scoring (0-100).
7. Report generation in JSON, CSV, HTML, and PDF formats.
8. End-to-end Localhost IPC API server integration with token authentication.
"""

import json
import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from ghost_core.api.server import app, SESSION_TOKEN, GLOBAL_VAULT
import ghost_core.api.server as api_module
from ghost_core.compatibility.matrix import CompatibilityEvaluator
from ghost_core.diagnostics.diff import ChangeType, HardwareDiffEngine
from ghost_core.diagnostics.rules import DeterministicRulesEngine, DiagnosticStatus
from ghost_core.reporting.exporters import ReportExporter
from ghost_core.schemas.scan import (
    BatterySpec,
    CpuSpec,
    DiagnosticResult,
    GpuSpec,
    HardwareSpec,
    MemoryModule,
    MemorySpec,
    MotherboardSpec,
    NetworkInterface,
    NormalizedScanPayload,
    PlatformEnum,
    StorageDevice,
)
from ghost_vault.db import GhostVaultDB


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="ghost_gate2_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_windows_scan() -> NormalizedScanPayload:
    """Mock scan produced by Windows Companion Mode."""
    fingerprint = NormalizedScanPayload.generate_fingerprint(
        salt="vault_anchor_salt_abc",
        motherboard_uuid="ASUS-MB-UX3404-9876",
        cpu_id="CPU-INTEL-13700H-BFEBFBFF",
        primary_storage_serial="SAMSUNG-MZVL21T0-S676NF0W",
    )
    return NormalizedScanPayload(
        schema_version="1.0.0",
        scan_id="w1111111-2222-3333-4444-555566667777",
        machine_fingerprint=fingerprint,
        platform=PlatformEnum.WINDOWS,
        os_version="Microsoft Windows 11 Pro 10.0.22631",
        timestamp_utc="2026-11-13T08:00:00Z",
        compatibility_matrix=CompatibilityEvaluator.evaluate_capabilities(PlatformEnum.WINDOWS),
        hardware=HardwareSpec(
            cpu=CpuSpec(
                model="13th Gen Intel Core i7-13700H",
                architecture="x86_64",
                physical_cores=14,
                logical_threads=20,
                base_clock_mhz=2400.0,
                max_clock_mhz=5000.0,
                temp_c=45.0,
            ),
            memory=MemorySpec(
                total_bytes=17179869184,  # 16 GB
                slots_used=2,
                slots_total=2,
                modules=[
                    MemoryModule(
                        slot="ChannelA-DIMM0",
                        capacity_bytes=8589934592,
                        speed_mhz=4800,
                        type="DDR5",
                        manufacturer="Micron",
                    ),
                    MemoryModule(
                        slot="ChannelB-DIMM0",
                        capacity_bytes=8589934592,
                        speed_mhz=4800,
                        type="DDR5",
                        manufacturer="Micron",
                    ),
                ],
            ),
            storage=[
                StorageDevice(
                    device_id="\\\\.\\PhysicalDrive0",
                    model="SAMSUNG MZVL21T0HCLR-00B00",
                    serial_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
                    interface="NVMe",
                    capacity_bytes=1024209543168,
                    smart_status="PASSED",
                    temp_c=38.0,
                    wear_level_pct=2.0,
                    power_on_hours=1200,
                )
            ],
            gpu=[
                GpuSpec(
                    name="Intel Iris Xe Graphics",
                    vendor="Intel",
                    vram_bytes=1073741824,
                    driver_version="31.0.101.4575",
                    temp_c=42.0,
                )
            ],
            motherboard=MotherboardSpec(
                manufacturer="ASUSTeK COMPUTER INC.",
                product="UX3404VC",
                bios_version="UX3404VC.308",
                bios_date="2024-03-15",
                secure_boot_enabled=True,
            ),
            battery=BatterySpec(
                present=True,
                design_capacity_mwh=70000.0,
                full_charge_capacity_mwh=65800.0,
                health_pct=94.0,
                cycle_count=85,
                status="Discharging",
            ),
            network=[
                NetworkInterface(
                    interface="Wi-Fi 6E",
                    mac_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                    type="Wireless",
                    link_speed_mbps=866,
                    status="Connected",
                )
            ],
        ),
        diagnostics=[],
    )


@pytest.fixture
def mock_linux_scan(mock_windows_scan: NormalizedScanPayload) -> NormalizedScanPayload:
    """Mock scan produced by Bootable Linux Mode on the same machine."""
    return NormalizedScanPayload(
        schema_version="1.0.0",
        scan_id="l2222222-3333-4444-5555-666677778888",
        machine_fingerprint=mock_windows_scan.machine_fingerprint,
        platform=PlatformEnum.LINUX,
        os_version="Ubuntu 24.04 LTS (Ghost-OS Live 6.8.0-minimal)",
        timestamp_utc="2026-11-13T08:15:00Z",
        compatibility_matrix=CompatibilityEvaluator.evaluate_capabilities(PlatformEnum.LINUX),
        hardware=HardwareSpec(
            cpu=mock_windows_scan.hardware.cpu.model_copy(update={"temp_c": 46.0}),
            memory=mock_windows_scan.hardware.memory.model_copy(),
            storage=mock_windows_scan.hardware.storage,
            gpu=mock_windows_scan.hardware.gpu,
            motherboard=mock_windows_scan.hardware.motherboard,
            battery=mock_windows_scan.hardware.battery,
            network=mock_windows_scan.hardware.network,
        ),
        diagnostics=[],
    )


def test_cross_os_schema_parity(mock_windows_scan, mock_linux_scan):
    """Verifies that Windows and Linux payloads share identical fingerprints and parity."""
    assert mock_windows_scan.machine_fingerprint == mock_linux_scan.machine_fingerprint
    assert mock_windows_scan.platform == PlatformEnum.WINDOWS
    assert mock_linux_scan.platform == PlatformEnum.LINUX

    diff = HardwareDiffEngine.compare_scans(mock_windows_scan, mock_linux_scan)
    assert diff.machine_fingerprint == mock_windows_scan.machine_fingerprint

    # Platform and OS changes detected, but no hardware component changes or degradations
    assert len(diff.degradations) == 0
    change_components = [c.component for c in diff.changes]
    assert "Platform" in change_components
    assert "Operating System" in change_components


def test_hardware_upgrades_and_replacements(mock_windows_scan):
    """Verifies detection of RAM upgrades, SSD replacements, BIOS updates, and GPU driver updates."""
    # Create upgraded scan payload
    upgraded = mock_windows_scan.model_copy(deep=True)
    upgraded.scan_id = "w9999999-0000-1111-2222-333344445555"
    upgraded.timestamp_utc = "2026-11-20T10:00:00Z"

    # 1. Upgrade RAM from 16 GB to 32 GB (2x16GB)
    upgraded.hardware.memory.total_bytes = 34359738368
    upgraded.hardware.memory.modules = [
        MemoryModule(slot="ChannelA-DIMM0", capacity_bytes=17179869184, speed_mhz=5600, type="DDR5", manufacturer="Crucial"),
        MemoryModule(slot="ChannelB-DIMM0", capacity_bytes=17179869184, speed_mhz=5600, type="DDR5", manufacturer="Crucial"),
    ]

    # 2. Replaced SSD
    upgraded.hardware.storage = [
        StorageDevice(
            device_id="\\\\.\\PhysicalDrive0",
            model="WD_BLACK SN850X 2TB",
            serial_hash="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            interface="NVMe",
            capacity_bytes=2048400000000,
            smart_status="PASSED",
            temp_c=40.0,
            wear_level_pct=0.0,
            power_on_hours=5,
        )
    ]

    # 3. BIOS update
    upgraded.hardware.motherboard.bios_version = "UX3404VC.310"

    # 4. GPU driver update
    upgraded.hardware.gpu[0].driver_version = "31.0.101.5555"

    diff = HardwareDiffEngine.compare_scans(mock_windows_scan, upgraded)
    assert diff.changes_detected is True

    # Validate RAM Upgrade
    ram_changes = [c for c in diff.changes if c.component == "RAM" and c.change_type == ChangeType.UPGRADE]
    assert len(ram_changes) >= 1
    assert "16.0 GB" in ram_changes[0].old_value
    assert "32.0 GB" in ram_changes[0].new_value

    # Validate Storage Replacement
    storage_replacements = [c for c in diff.changes if c.component == "Storage" and c.change_type == ChangeType.REPLACEMENT]
    assert len(storage_replacements) == 1
    assert "WD_BLACK SN850X" in storage_replacements[0].new_value

    # Validate BIOS Firmware Update
    bios_changes = [c for c in diff.changes if c.component == "Motherboard BIOS"]
    assert len(bios_changes) == 1
    assert bios_changes[0].old_value == "UX3404VC.308"
    assert bios_changes[0].new_value == "UX3404VC.310"

    # Validate GPU Driver Update
    gpu_changes = [c for c in diff.changes if c.component == "GPU Driver"]
    assert len(gpu_changes) == 1
    assert gpu_changes[0].old_value == "31.0.101.4575"
    assert gpu_changes[0].new_value == "31.0.101.5555"


def test_hardware_degradation_alerts(mock_windows_scan):
    """Verifies degradation alerts: Battery wear drop > 2%, SSD wear increase, and rising thermals."""
    degraded = mock_windows_scan.model_copy(deep=True)
    degraded.scan_id = "w-degraded-1111"
    degraded.timestamp_utc = "2026-11-25T12:00:00Z"

    # 1. Battery health dropped from 94% to 89% (5% drop > 2% threshold)
    degraded.hardware.battery.health_pct = 89.0
    degraded.hardware.battery.cycle_count = 110

    # 2. SSD wear increased from 2% to 14%
    degraded.hardware.storage[0].wear_level_pct = 14.0

    # 3. CPU idle temperature increased from 45°C to 58°C (+13°C > 10°C threshold)
    degraded.hardware.cpu.temp_c = 58.0

    diff = HardwareDiffEngine.compare_scans(mock_windows_scan, degraded)
    assert len(diff.degradations) == 3

    deg_components = {d.component for d in diff.degradations}
    assert "Battery Wear" in deg_components
    assert "Storage Wear" in deg_components
    assert "Thermal Performance" in deg_components


def test_deterministic_rules_engine_scoring(mock_windows_scan):
    """Verifies health scoring computation across healthy and failing states."""
    # 1. Healthy baseline
    health_good = DeterministicRulesEngine.evaluate(mock_windows_scan)
    assert health_good.overall_score >= 90
    assert health_good.storage_score == 100
    assert health_good.battery_score == 100

    # 2. Failing SMART and critical CPU thermal
    failing_payload = mock_windows_scan.model_copy(deep=True)
    failing_payload.hardware.storage[0].smart_status = "FAILED"
    failing_payload.hardware.cpu.temp_c = 94.0  # Critical thermal

    health_bad = DeterministicRulesEngine.evaluate(failing_payload)
    assert health_bad.overall_score < 70
    assert health_bad.storage_score <= 50
    assert health_bad.cpu_score <= 60

    # Check that critical diagnostics are raised
    failed_diags = [d for d in health_bad.diagnostics if d.status == DiagnosticStatus.FAIL]
    assert len(failed_diags) >= 2


def test_report_exporters(temp_dir, mock_windows_scan):
    """Verifies standalone generation of JSON, CSV, HTML, and PDF reports."""
    health = DeterministicRulesEngine.evaluate(mock_windows_scan)
    payload_dict = mock_windows_scan.model_dump()
    hs_dict = health.model_dump()

    # 1. JSON Export
    json_path = os.path.join(temp_dir, "report.json")
    json_str = ReportExporter.export_json(payload_dict, output_path=json_path)
    assert os.path.exists(json_path)
    assert mock_windows_scan.machine_fingerprint in json_str

    # 2. CSV Export
    csv_path = os.path.join(temp_dir, "report.csv")
    csv_str = ReportExporter.export_csv(payload_dict, output_path=csv_path)
    assert os.path.exists(csv_path)
    assert "GHOST-OS HARDWARE DIAGNOSTIC REPORT" in csv_str

    # 3. HTML Export
    html_path = os.path.join(temp_dir, "report.html")
    html_str = ReportExporter.export_html(payload_dict, hs_dict, output_path=html_path)
    assert os.path.exists(html_path)
    assert "<!DOCTYPE html>" in html_str
    assert "GHOST-OS HARDWARE INTELLIGENCE" in html_str

    # 4. PDF Export
    pdf_path = os.path.join(temp_dir, "report.pdf")
    out_pdf = ReportExporter.export_pdf(payload_dict, hs_dict, output_path=pdf_path)
    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 1000  # Valid non-empty PDF binary


def test_local_ipc_api_end_to_end(temp_dir, mock_windows_scan, mock_linux_scan):
    """Verifies FastAPI Localhost IPC server endpoints, authentication, and automatic diffing."""
    api_module.GLOBAL_VAULT = None
    client = TestClient(app)
    auth_headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}
    vault_file = os.path.join(temp_dir, "vault.enc")

    # 1. Check /api/v1/health (unauthenticated)
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "online"

    # 2. Accessing protected endpoint without token returns 401
    res_unauth = client.get("/api/v1/machines")
    assert res_unauth.status_code == 401

    # 3. Accessing before unlock returns 423 Locked
    res_locked = client.get("/api/v1/machines", headers=auth_headers)
    assert res_locked.status_code == 423

    # 4. Create new vault via API
    res_create = client.post(
        "/api/v1/vault/create",
        headers=auth_headers,
        json={"password": "LocalVaultPassword_2026", "vault_path": vault_file},
    )
    assert res_create.status_code == 200
    assert res_create.json()["status"] == "created"

    # 5. Ingest Windows baseline scan
    res_ingest_1 = client.post(
        "/api/v1/scan/ingest",
        headers=auth_headers,
        json=mock_windows_scan.model_dump(),
    )
    assert res_ingest_1.status_code == 200
    data_1 = res_ingest_1.json()
    assert data_1["scan_id"] == mock_windows_scan.scan_id
    assert data_1["diff_report"] is None  # First scan, no prior history

    # 6. Ingest Linux scan on same machine -> Should automatically detect diff against baseline!
    res_ingest_2 = client.post(
        "/api/v1/scan/ingest",
        headers=auth_headers,
        json=mock_linux_scan.model_dump(),
    )
    assert res_ingest_2.status_code == 200
    data_2 = res_ingest_2.json()
    assert data_2["scan_id"] == mock_linux_scan.scan_id
    assert data_2["diff_report"] is not None
    assert data_2["diff_report"]["changes_detected"] is True

    # 7. Query machine registry
    res_machines = client.get("/api/v1/machines", headers=auth_headers)
    assert res_machines.status_code == 200
    machines = res_machines.json()
    assert len(machines) == 1
    assert machines[0]["machine_fingerprint"] == mock_windows_scan.machine_fingerprint
    assert machines[0]["scan_count"] == 2

    # 8. Query machine detail and history
    res_detail = client.get(f"/api/v1/machines/{mock_windows_scan.machine_fingerprint}", headers=auth_headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert len(detail["scan_history"]) == 2

    # 9. Query explicit diff endpoint
    res_diff = client.get(f"/api/v1/machines/{mock_windows_scan.machine_fingerprint}/diff", headers=auth_headers)
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert diff_data["changes_detected"] is True

    # 10. Add maintenance record
    res_maint = client.post(
        f"/api/v1/machines/{mock_windows_scan.machine_fingerprint}/maintenance",
        headers=auth_headers,
        json={
            "action_type": "thermal_paste_replaced",
            "technician_name": "Senior Field Eng",
            "notes": "Applied Honeywell PTM7950 phase change pad.",
        },
    )
    assert res_maint.status_code == 200

    # 11. Export HTML Report
    res_export_html = client.get(f"/api/v1/reports/{mock_windows_scan.scan_id}/export?format=html", headers=auth_headers)
    assert res_export_html.status_code == 200
    assert "<!DOCTYPE html>" in res_export_html.text

    # 12. Export PDF Report
    res_export_pdf = client.get(f"/api/v1/reports/{mock_windows_scan.scan_id}/export?format=pdf", headers=auth_headers)
    assert res_export_pdf.status_code == 200
    assert res_export_pdf.headers["content-type"] == "application/pdf"
    assert len(res_export_pdf.content) > 1000

    # 13. Lock vault
    res_lock = client.post("/api/v1/vault/lock", headers=auth_headers)
    assert res_lock.status_code == 200
    assert res_lock.json()["status"] == "locked"


def test_multi_anchor_identity_matching_on_ssd_swap(mock_windows_scan):
    """Verifies that replacing the primary SSD preserves machine identity and detects component swap."""
    swapped_scan = mock_windows_scan.model_copy(deep=True)
    swapped_scan.scan_id = "scan-after-ssd-upgrade-999"

    # Replace storage drive with a new 2TB Crucial T700 NVMe
    swapped_scan.hardware.storage = [
        StorageDevice(
            device_id="\\\\.\\PhysicalDrive0",
            model="Crucial T700 2TB PCIe Gen5 NVMe",
            serial_hash="9999888877776666555544443333222211110000aaaaabbbbbcccccdddddeeeee",
            interface="NVMe",
            capacity_bytes=2000398934016,
            smart_status="PASSED",
            temp_c=41.0,
            wear_level_pct=0.0,
            power_on_hours=5,
        )
    ]

    # Calculate multi-anchor similarity
    sim_result = NormalizedScanPayload.compute_anchor_similarity(mock_windows_scan, swapped_scan)
    assert sim_result["is_same_machine"] is True
    assert sim_result["similarity_score"] >= 80.0
    assert sim_result["status"] == "SAME_DEVICE_COMPONENT_SWAP"
    assert "Motherboard Hardware Signature" in sim_result["matched_anchors"]
    assert "CPU Silicon & Topology" in sim_result["matched_anchors"]
    assert "Primary Storage Replaced/Swapped" in sim_result["changed_anchors"]

    # Historical candidate matching
    match_tuple = HardwareDiffEngine.find_historical_match(
        current_scan=swapped_scan,
        historical_scans=[mock_windows_scan],
        threshold=75.0,
    )
    assert match_tuple is not None
    matched_hist, analysis = match_tuple
    assert matched_hist.scan_id == mock_windows_scan.scan_id

    # Compute hardware diff between baseline and swapped scan
    diff_report = HardwareDiffEngine.compare_scans(baseline=mock_windows_scan, current=swapped_scan)
    assert diff_report.changes_detected is True
    assert any(c.component == "Storage" and c.change_type == ChangeType.REPLACEMENT for c in diff_report.changes)
