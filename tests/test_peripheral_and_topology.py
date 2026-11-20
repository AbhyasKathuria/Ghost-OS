"""Verification suite for Connected Peripheral Device Tree and Network Topology Scanning.

Tests:
1. Connected peripheral discovery (Displays, Webcams, Mice, Keyboards, Audio devices, USB Hubs).
2. Network topology discovery (Domain/Workgroup, DNS, Gateway, Connected Servers, Subnet Neighbors).
3. Schema compliance and serialization roundtrip within NormalizedScanPayload.
4. Live platform execution on the active workstation.
"""

import pytest

from ghost_core.scanners.network_topology import NetworkTopologyScanner
from ghost_core.scanners.peripheral_scanner import PeripheralScanner
from ghost_core.schemas.scan import (
    BatterySpec,
    ConnectedPeripheralSpec,
    ConnectedServerSpec,
    CpuSpec,
    DiscoveredNeighborSpec,
    HardwareSpec,
    MemorySpec,
    MotherboardSpec,
    NetworkTopologyTreeSpec,
    NormalizedScanPayload,
    PlatformEnum,
)


def test_peripheral_scanner_categories():
    peripherals = PeripheralScanner.create_simulated_peripheral_tree(
        monitor_name="ASUS ProArt PA32UCG-K 4K HDR",
        webcam_name="Logitech Brio 4K Webcam",
        keyboard_name="Custom Mechanical Keyboard (QMK)",
        mouse_name="Razer DeathAdder V3 Pro",
        audio_name="Realtek ALC4082 HD Audio",
    )

    assert len(peripherals) == 5
    cats = {p.category for p in peripherals}
    assert "Display / Monitor" in cats
    assert "Camera / Video" in cats
    assert "Keyboard / Input" in cats
    assert "Mouse / Pointing Device" in cats
    assert "Audio / Speaker / Mic" in cats

    # Check monitor specifics
    mon = next(p for p in peripherals if p.category == "Display / Monitor")
    assert "3840x2160" in mon.details["resolution"]
    assert mon.connection_type == "DisplayPort 1.4 / Type-C"

    # Check webcam specifics
    cam = next(p for p in peripherals if p.category == "Camera / Video")
    assert "4K" in cam.details["sensor_resolution"]
    assert cam.details["fps"] == 60


def test_network_topology_scanner():
    topo = NetworkTopologyScanner.create_simulated_topology()

    assert topo.domain_or_workgroup == "ENTERPRISE.CORP"
    assert "10.0.0.10" in topo.dns_servers
    assert topo.default_gateway == "10.0.0.1"
    assert len(topo.connected_servers) == 4
    assert len(topo.subnet_neighbors) == 4

    # Verify server types
    srv_types = [s.service_type for s in topo.connected_servers]
    assert any("Active Directory" in t for t in srv_types)
    assert any("SMB Enterprise File Share" in t for t in srv_types)
    assert any("SQL Server Database" in t for t in srv_types)
    assert any("Siemens S7 Industrial" in t for t in srv_types)

    # Verify discovered subnet neighbors
    assert any(n.device_type == "Default Gateway Router" for n in topo.subnet_neighbors)
    assert any(n.device_type == "Storage NAS / SAN Appliance" for n in topo.subnet_neighbors)


def test_schema_parity_with_peripherals_and_network_tree():
    periphs = PeripheralScanner.create_simulated_peripheral_tree()
    topo = NetworkTopologyScanner.create_simulated_topology()

    payload = NormalizedScanPayload(
        machine_fingerprint="b" * 64,
        platform=PlatformEnum.WINDOWS,
        os_version="Windows 11 Pro 24H2",
        timestamp_utc="2026-11-15T15:00:00Z",
        hardware=HardwareSpec(
            cpu=CpuSpec(model="Intel Core Ultra 9 185H", architecture="x86_64", physical_cores=16, logical_threads=22),
            memory=MemorySpec(total_bytes=34359738368, slots_used=8, slots_total=8),
            motherboard=MotherboardSpec(manufacturer="ASUSTeK COMPUTER INC.", product="UX3405MA", serial_number="ASUS123", bios_version="311"),
            battery=BatterySpec(present=True, status="Remaining 85%"),
            connected_peripherals=periphs,
            network_topology=topo,
        ),
    )

    # Validate JSON serialization and deserialization
    json_data = payload.model_dump_json()
    assert "Logitech Brio" in json_data
    assert "ENTERPRISE.CORP" in json_data
    assert "3840x2160" in json_data

    reloaded = NormalizedScanPayload.model_validate_json(json_data)
    assert len(reloaded.hardware.connected_peripherals) == 5
    assert reloaded.hardware.network_topology is not None
    assert reloaded.hardware.network_topology.domain_or_workgroup == "ENTERPRISE.CORP"
    assert len(reloaded.hardware.network_topology.connected_servers) == 4


def test_live_peripheral_and_topology_execution():
    # Test on active Windows machine
    peripherals = PeripheralScanner.scan_peripherals()
    assert isinstance(peripherals, list)
    # The machine has at least audio, display, or internal devices
    print(f"Discovered {len(peripherals)} live connected peripherals.")

    topology = NetworkTopologyScanner.scan_topology()
    assert isinstance(topology, NetworkTopologyTreeSpec)
    assert topology.domain_or_workgroup != ""
    print(f"Discovered domain: {topology.domain_or_workgroup}, Gateway: {topology.default_gateway}, Active servers: {len(topology.connected_servers)}")
