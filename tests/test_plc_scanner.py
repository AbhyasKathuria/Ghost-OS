"""Test suite for Ghost-OS Industrial Automation & PLC Hardware Diagnostics.

Tests:
1. Industrial Edge PC & PLC direct boot detection (Siemens SIMATIC IPC, Beckhoff TwinCAT, Advantech, WAGO).
2. Modbus TCP Device Identification (FC 43 / 14) and register query.
3. Siemens SIMATIC S7-1500/1200 RFC 1006 COTP & S7comm SZL module interrogation.
4. Rockwell Automation / Allen-Bradley EtherNet/IP CIP ListIdentity audit.
5. Canonical schema parity & serialization with industrial controllers.
"""

import pytest

from ghost_core.scanners.plc_scanner import (
    EdgeIpcDetector,
    GhostIndustrialScanner,
    ModbusTcpAuditor,
    SiemensS7Auditor,
    EtherNetIpAuditor,
)
from ghost_core.schemas.scan import (
    BatterySpec,
    CpuSpec,
    DiagnosticStatus,
    HardwareSpec,
    IndustrialControllerSpec,
    MemorySpec,
    MotherboardSpec,
    NormalizedScanPayload,
    PlatformEnum,
)


def test_edge_ipc_direct_boot_detection():
    # Test Siemens SIMATIC IPC
    is_siemens, prof_siemens = EdgeIpcDetector.inspect("Siemens AG", "SIMATIC IPC427E")
    assert is_siemens is True
    assert prof_siemens.vendor == "Siemens"
    assert prof_siemens.direct_boot_supported is True

    # Test Beckhoff TwinCAT Embedded PC
    is_beckhoff, prof_beckhoff = EdgeIpcDetector.inspect("Beckhoff Automation GmbH", "CX5140-0125")
    assert is_beckhoff is True
    assert prof_beckhoff.vendor == "Beckhoff Automation"
    assert prof_beckhoff.direct_boot_supported is True

    # Test Advantech UNO Box PC
    is_adv, prof_adv = EdgeIpcDetector.inspect("Advantech Co., Ltd.", "UNO-2484G-6731AE")
    assert is_adv is True
    assert prof_adv.vendor == "Advantech"

    # Test Consumer PC (Non-industrial)
    is_consumer, prof_consumer = EdgeIpcDetector.inspect("ASUSTeK COMPUTER INC.", "Zenbook 14 OLED UX3405MA")
    assert is_consumer is False
    assert prof_consumer is None


def test_modbus_tcp_audit():
    scanner = GhostIndustrialScanner()
    spec, diag = scanner.simulate_or_query_modbus_plc(
        endpoint="192.168.1.50:502",
        mock_vendor="Schneider Electric",
        mock_product="Modicon M241 Logic Controller",
        mock_rev="V5.1.0",
        mock_cycle_ms=3.8,
    )

    assert spec.protocol == "Modbus-TCP"
    assert spec.vendor == "Schneider Electric"
    assert "Modicon M241" in spec.model_or_catalog
    assert spec.cycle_time_ms == 3.8
    assert spec.operating_state == "RUN"
    assert diag.status == DiagnosticStatus.PASS
    assert diag.metric_value == 3.8
    assert "Schneider Electric" in diag.evidence


def test_siemens_s7_audit():
    # Verify COTP request packet construction
    cotp_packet = SiemensS7Auditor.build_cotp_connection_request()
    assert cotp_packet[:4] == bytes([0x03, 0x00, 0x00, 0x13])  # TPKT header (v3, len 19)

    scanner = GhostIndustrialScanner()
    spec, diag = scanner.simulate_or_query_siemens_s7(
        endpoint="192.168.1.10:102",
        mlfb="6ES7 516-3AN02-0AB0",
        cpu_name="SIMATIC S7-1500 (CPU 1516-3 PN/DP)",
        firmware="V2.9.2",
        cycle_ms=5.4,
    )

    assert spec.protocol == "Siemens-S7comm"
    assert spec.vendor == "Siemens"
    assert "6ES7 516-3AN02-0AB0" in spec.model_or_catalog
    assert spec.firmware_revision == "V2.9.2"
    assert spec.diagnostics_status == "OK"
    assert diag.status == DiagnosticStatus.PASS
    assert "Memory card integrity valid" in diag.recommendation


def test_allen_bradley_cip_audit():
    # Verify EtherNet/IP encapsulation header packet construction
    eip_packet = EtherNetIpAuditor.build_list_identity_request()
    assert len(eip_packet) == 24
    assert eip_packet[:2] == bytes([0x63, 0x00])  # Command 0x0063 (ListIdentity)

    scanner = GhostIndustrialScanner()
    spec, diag = scanner.simulate_or_query_allen_bradley(
        endpoint="192.168.1.20:44818",
        catalog="1769-L33ERMS CompactLogix 5370 Safety",
        firmware="v32.011",
        cycle_ms=4.1,
    )

    assert spec.protocol == "EtherNet/IP-CIP"
    assert "Allen-Bradley" in spec.vendor
    assert "CompactLogix" in spec.model_or_catalog
    assert spec.operating_state == "RUN"
    assert diag.status == DiagnosticStatus.PASS


def test_schema_parity_with_industrial_controllers():
    ctrl1 = IndustrialControllerSpec(
        protocol="Siemens-S7comm",
        endpoint="192.168.10.12:102",
        vendor="Siemens",
        model_or_catalog="SIMATIC S7-1200 CPU 1214C",
        firmware_revision="V4.5.1",
        operating_state="RUN",
        cycle_time_ms=7.2,
    )

    payload = NormalizedScanPayload(
        machine_fingerprint="a" * 64,
        platform=PlatformEnum.LINUX,
        os_version="Ghost-OS Industrial Live 24.04",
        timestamp_utc="2026-11-15T12:00:00Z",
        hardware=HardwareSpec(
            cpu=CpuSpec(model="Intel Atom x6413E (Industrial)", architecture="x86_64", physical_cores=4, logical_threads=4),
            memory=MemorySpec(total_bytes=8589934592, slots_used=1, slots_total=1),
            motherboard=MotherboardSpec(manufacturer="Siemens AG", product="SIMATIC IPC227E", serial_number="SVPB1234567", bios_version="V2.1.0"),
            battery=BatterySpec(present=False),
            industrial_controllers=[ctrl1],
        ),
    )

    # Test JSON serialization and deserialization
    json_str = payload.model_dump_json()
    assert "SIMATIC S7-1200" in json_str
    assert "Siemens-S7comm" in json_str

    reloaded = NormalizedScanPayload.model_validate_json(json_str)
    assert len(reloaded.hardware.industrial_controllers) == 1
    assert reloaded.hardware.industrial_controllers[0].model_or_catalog == "SIMATIC S7-1200 CPU 1214C"
    assert reloaded.hardware.industrial_controllers[0].cycle_time_ms == 7.2
