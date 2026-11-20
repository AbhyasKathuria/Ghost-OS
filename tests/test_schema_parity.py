"""Verification of canonical schema parity between Windows and Linux models."""

import os
import subprocess
import pytest
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


def test_schema_serialization_and_deserialization():
    fingerprint = NormalizedScanPayload.generate_fingerprint("salt", "mb", "cpu", "storage")
    payload = NormalizedScanPayload(
        schema_version="1.0.0",
        scan_id="00000000-0000-0000-0000-000000000001",
        machine_fingerprint=fingerprint,
        platform=PlatformEnum.LINUX,
        os_version="Ubuntu 24.04",
        timestamp_utc="2026-11-13T10:00:00Z",
        hardware=HardwareSpec(
            cpu=CpuSpec(model="AMD Ryzen 7 7840U", architecture="x86_64", physical_cores=8, logical_threads=16),
            memory=MemorySpec(total_bytes=34359738368, slots_used=2, slots_total=2),
            motherboard=MotherboardSpec(manufacturer="Framework", product="Laptop 13", bios_version="3.03"),
            battery=BatterySpec(present=True, health_pct=98.5),
        ),
    )

    json_str = payload.model_dump_json()
    reconstituted = NormalizedScanPayload.model_validate_json(json_str)

    assert reconstituted.scan_id == payload.scan_id
    assert reconstituted.platform == PlatformEnum.LINUX
    assert reconstituted.hardware.cpu.model == "AMD Ryzen 7 7840U"
    assert reconstituted.hardware.battery.health_pct == 98.5


def test_windows_companion_binary_schema_compliance():
    """Validates that compiled Ghost-Companion.exe emits strictly compliant canonical JSON."""
    binary_path = os.path.join(
        "windows-companion", "bin", "Release", "net8.0-windows", "win-x64", "publish", "Ghost-Companion.exe"
    )
    if not os.path.exists(binary_path):
        pytest.skip("Ghost-Companion.exe binary not found")

    out = subprocess.check_output([binary_path, "--scan-only"], text=True)
    json_start = out.find("{")
    assert json_start != -1

    raw_json = out[json_start:]
    payload = NormalizedScanPayload.model_validate_json(raw_json)

    assert payload.schema_version == "1.0.0"
    assert payload.platform == PlatformEnum.WINDOWS
    assert len(payload.machine_fingerprint) == 64
    assert payload.hardware.cpu.physical_cores >= 1
    assert payload.hardware.memory.total_bytes > 0
