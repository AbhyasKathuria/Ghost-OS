"""Gate 6 Verification: Offline AI Copilot, Read-Only Tool Scoping & Anti-Hallucination.

Verifies:
1. Strict read-only database query tools (get_machine_history, find_warnings, compare_scans, explain_smart_attribute).
2. Deterministic AI Copilot query synthesis anchoring directly to vault facts with zero hallucinations.
3. Offline natural-language queries accurately citing hardware models, RAM capacities, and SMART thresholds.
4. Localhost IPC AI API endpoints (/api/v1/ai/status and /api/v1/ai/chat).
"""

import json
import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from ghost_ai.inference import GhostAiCopilot
from ghost_ai.tools import VaultInspectionTools
from ghost_core.api.server import app, SESSION_TOKEN
from ghost_core.schemas.scan import (
    BatterySpec,
    CpuSpec,
    DiagnosticResult,
    DiagnosticStatus,
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
    d = tempfile.mkdtemp(prefix="ghost_gate6_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def populated_vault(temp_dir) -> GhostVaultDB:
    vault_file = os.path.join(temp_dir, "vault.enc")
    vault = GhostVaultDB.create_new(
        vault_path=vault_file,
        password="AiTestPassword!2026",
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
    )

    fingerprint = NormalizedScanPayload.generate_fingerprint(
        salt="salt_ai_verify",
        motherboard_uuid="MB-FRAMEWORK-13",
        cpu_id="AMD Ryzen 7 7840U w/ Radeon 780M",
        primary_storage_serial="WD-BLACK-SN850X-SN9900",
    )

    # 1. Baseline scan with a failing SMART drive
    baseline = NormalizedScanPayload(
        schema_version="1.0.0",
        scan_id="s1111111-1111-1111-1111-111111111111",
        machine_fingerprint=fingerprint,
        platform=PlatformEnum.LINUX,
        os_version="Ubuntu 24.04 LTS (Noble)",
        timestamp_utc="2026-11-10T10:00:00Z",
        hardware=HardwareSpec(
            cpu=CpuSpec(
                model="AMD Ryzen 7 7840U w/ Radeon 780M",
                architecture="x86_64",
                physical_cores=8,
                logical_threads=16,
                base_clock_mhz=3300.0,
                max_clock_mhz=5100.0,
                temp_c=52.0,
            ),
            memory=MemorySpec(
                total_bytes=17179869184,  # 16 GB
                slots_used=1,
                slots_total=2,
                modules=[MemoryModule(slot="ChannelA-DIMM0", capacity_bytes=17179869184, speed_mhz=5600, type="DDR5", manufacturer="Crucial")],
            ),
            storage=[
                StorageDevice(
                    device_id="/dev/nvme0n1",
                    model="WD_BLACK SN850X 1TB",
                    serial_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
                    interface="NVMe",
                    capacity_bytes=1000204886016,
                    smart_status="FAILED",
                    temp_c=48.0,
                    wear_level_pct=92.0,
                    power_on_hours=8200,
                )
            ],
            motherboard=MotherboardSpec(
                manufacturer="Framework",
                product="Laptop 13 (AMD Ryzen 7040Series)",
                bios_version="03.03",
                secure_boot_enabled=True,
            ),
            battery=BatterySpec(
                present=True,
                design_capacity_mwh=61000.0,
                full_charge_capacity_mwh=57000.0,
                health_pct=93.4,
                cycle_count=142,
                status="Discharging",
            ),
        ),
        diagnostics=[
            DiagnosticResult(
                test_name="NVMe SMART Health",
                status=DiagnosticStatus.FAIL,
                metric_value=92.0,
                threshold=90.0,
                evidence="NAND flash write endurance consumed 92% (Threshold: 90%). Spare blocks critically low.",
                recommendation="Replace SSD drive immediately. Data loss imminent.",
            )
        ],
    )
    vault.ingest_scan(baseline, overall_health_score=55)

    # 2. Second scan: RAM upgraded from 16 GB to 32 GB (added second 16GB stick)
    second_scan = baseline.model_copy(deep=True)
    second_scan.scan_id = "s2222222-2222-2222-2222-222222222222"
    second_scan.timestamp_utc = "2026-11-13T12:00:00Z"
    second_scan.hardware.memory.total_bytes = 34359738368  # 32 GB
    second_scan.hardware.memory.slots_used = 2
    second_scan.hardware.memory.modules.append(
        MemoryModule(slot="ChannelB-DIMM0", capacity_bytes=17179869184, speed_mhz=5600, type="DDR5", manufacturer="Crucial")
    )
    vault.ingest_scan(second_scan, overall_health_score=58)

    return vault


def test_vault_inspection_tools(populated_vault):
    """Verifies that read-only query tools return precise database telemetry."""
    tools = VaultInspectionTools(populated_vault)
    machines = populated_vault.list_machines()
    assert len(machines) == 1
    fp = machines[0]["machine_fingerprint"]

    # 1. Test get_machine_history
    history = tools.get_machine_history(fp)
    assert history["total_scans"] == 2
    assert history["machine"]["latest_health_score"] == 58
    assert history["hardware_summary"]["cpu"]["model"] == "AMD Ryzen 7 7840U w/ Radeon 780M"
    assert history["hardware_summary"]["memory"]["total_bytes"] == 34359738368

    # 2. Test find_warnings
    warnings = tools.find_warnings(severity="FAIL")
    assert len(warnings) >= 1
    assert warnings[0]["test_name"] == "NVMe SMART Health"
    assert "92%" in warnings[0]["evidence"]

    # 3. Test compare_scans
    diff = tools.compare_scans(fp)
    assert diff["changes_detected"] is True
    assert diff["total_changes"] >= 1
    ram_upgrades = [c for c in diff["changes"] if c["component"] == "RAM"]
    assert len(ram_upgrades) >= 1
    assert "16.0 GB" in ram_upgrades[0]["old_value"]
    assert "32.0 GB" in ram_upgrades[0]["new_value"]

    # 4. Test explain_smart_attribute
    smart_info = tools.explain_smart_attribute("percentage_used")
    assert smart_info["critical_threshold"] == 90
    assert "rated write endurance" in smart_info["description"]


def test_copilot_deterministic_query_synthesis(populated_vault, temp_dir):
    """Verifies that the Copilot accurately answers natural-language queries citing vault facts."""
    empty_models = os.path.join(temp_dir, "no_models")
    os.makedirs(empty_models, exist_ok=True)
    copilot = GhostAiCopilot(models_dir=empty_models)
    machines = populated_vault.list_machines()
    fp = machines[0]["machine_fingerprint"]

    # Query 1: Active warnings inquiry
    res1 = copilot.query("What warnings or hardware issues were detected on this machine?", populated_vault, machine_fingerprint=fp)
    assert "NVMe SMART Health" in res1["reply"]
    assert "92%" in res1["reply"]
    assert res1["engine_used"] == "deterministic_fallback"
    assert any("Vault DB: diagnostic_results" in s for s in res1["sources"])

    # Query 2: SMART attribute inquiry
    res2 = copilot.query("Explain the percentage used SMART attribute and what action I should take", populated_vault)
    assert "NVMe Flash Wear" in res2["reply"]
    assert "90" in res2["reply"]
    assert "plan drive replacement" in res2["reply"].lower()

    # Query 3: Component changes inquiry
    res3 = copilot.query("Did anything change or get upgraded since the previous scan?", populated_vault, machine_fingerprint=fp)
    assert "RAM capacity upgraded" in res3["reply"]
    assert "16.0 GB to 32.0 GB" in res3["reply"]

    # Query 4: Machine specs inquiry
    res4 = copilot.query("What are the processor and memory specs?", populated_vault, machine_fingerprint=fp)
    assert "AMD Ryzen 7 7840U" in res4["reply"]
    assert "32.0 GB RAM" in res4["reply"]


def test_ai_api_endpoints_integration(populated_vault, temp_dir):
    """Verifies Localhost IPC AI Copilot endpoints."""
    # Wire the populated vault into global API state
    import ghost_core.api.server as api_server
    api_server.GLOBAL_VAULT = populated_vault
    old_copilot = api_server.GLOBAL_AI_COPILOT
    empty_models = os.path.join(temp_dir, "api_test_no_models")
    os.makedirs(empty_models, exist_ok=True)
    api_server.GLOBAL_AI_COPILOT = GhostAiCopilot(models_dir=empty_models)

    try:
        client = TestClient(app)
        auth_headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}

        # 1. Test /api/v1/ai/status
        res_status = client.get("/api/v1/ai/status")
        assert res_status.status_code == 200
        status_json = res_status.json()
        assert "is_gguf_active" in status_json
        assert "fallback_engine" in status_json

        # 2. Test /api/v1/ai/chat
        machines = populated_vault.list_machines()
        fp = machines[0]["machine_fingerprint"]

        res_chat = client.post(
            "/api/v1/ai/chat",
            headers=auth_headers,
            json={"message": "Summarize all active warnings across the fleet", "machine_fingerprint": fp},
        )
        assert res_chat.status_code == 200
        chat_json = res_chat.json()
        assert "NVMe SMART Health" in chat_json["reply"]
        assert len(chat_json["sources"]) >= 1

        # 3. Test empty message validation
        res_empty = client.post("/api/v1/ai/chat", headers=auth_headers, json={"message": "   "})
        assert res_empty.status_code == 400
    finally:
        api_server.GLOBAL_VAULT = None
        api_server.GLOBAL_AI_COPILOT = old_copilot
