"""Canonical Normalized Hardware Scan Schema for Ghost-OS.

Ensures strict cross-OS parity across Windows Companion Mode (.NET C#)
and Linux Boot Mode (Python / dmidecode / lshw / smartctl).
"""

from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator


class PlatformEnum(str, Enum):
    WINDOWS = "Windows"
    LINUX = "Linux"
    MACOS = "macOS"


class ModuleCompatibility(str, Enum):
    SUPPORTED = "supported"
    LIMITED = "limited"
    UNSUPPORTED = "unsupported"
    PERMISSION_DENIED = "permission_denied"


class DiagnosticStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class CpuSpec(BaseModel):
    model: str
    architecture: str
    physical_cores: int = Field(ge=1)
    logical_threads: int = Field(ge=1)
    base_clock_mhz: Optional[float] = None
    max_clock_mhz: Optional[float] = None
    temp_c: Optional[float] = None


class MemoryModule(BaseModel):
    slot: str
    capacity_bytes: int = Field(ge=0)
    speed_mhz: Optional[int] = None
    type: Optional[str] = None  # e.g. "DDR4", "DDR5", "LPDDR5"
    manufacturer: Optional[str] = None


class MemorySpec(BaseModel):
    total_bytes: int = Field(ge=0)
    slots_used: int = Field(ge=0)
    slots_total: int = Field(ge=0)
    modules: List[MemoryModule] = Field(default_factory=list)


class StorageDevice(BaseModel):
    device_id: str
    model: str
    serial_hash: str
    interface: str  # NVMe, SATA, USB, etc.
    capacity_bytes: int = Field(ge=0)
    smart_status: str  # "PASSED", "WARNING", "FAILED", "UNKNOWN"
    temp_c: Optional[float] = None
    wear_level_pct: Optional[float] = None  # 0.0 to 100.0
    power_on_hours: Optional[int] = None


class GpuSpec(BaseModel):
    name: str
    vendor: str  # NVIDIA, AMD, Intel, Apple, etc.
    vram_bytes: Optional[int] = None
    driver_version: Optional[str] = None
    temp_c: Optional[float] = None


class MotherboardSpec(BaseModel):
    manufacturer: str
    product: str
    bios_version: str
    bios_date: Optional[str] = None
    secure_boot_enabled: Optional[bool] = None


class BatterySpec(BaseModel):
    present: bool
    design_capacity_mwh: Optional[float] = None
    full_charge_capacity_mwh: Optional[float] = None
    health_pct: Optional[float] = None
    cycle_count: Optional[int] = None
    status: Optional[str] = None  # "Charging", "Discharging", "Full", "Not charging", "Unknown"


class NetworkInterface(BaseModel):
    interface: str
    mac_hash: str
    type: str  # "Ethernet", "Wireless", "Virtual", "Loopback", etc.
    link_speed_mbps: Optional[int] = None
    status: str  # "Connected", "Disconnected", "Disabled"


class VirtualizationSpec(BaseModel):
    is_virtual: bool = False
    hypervisor: Optional[str] = None  # "VMware", "VirtualBox", "KVM", "QEMU", "Hyper-V", "WSL2", "Bare-Metal"
    detection_method: Optional[str] = None


class MobileDeviceSpec(BaseModel):
    device_type: str = "iOS"  # "iOS", "Android", "iPadOS"
    model: str
    os_version: str
    serial_hash: str
    battery_health_pct: Optional[float] = None
    battery_cycles: Optional[int] = None
    status: str = "Connected"
    motherboard_model: Optional[str] = None
    soc_chipset: Optional[str] = None
    firmware_version: Optional[str] = None
    storage_capacity_bytes: Optional[int] = None
    storage_wear_pct: Optional[float] = None
    ram_bytes: Optional[int] = None
    battery_wear_pct: Optional[float] = None
    battery_design_mwh: Optional[float] = None
    battery_full_mwh: Optional[float] = None
    temperatures_c: Optional[Dict[str, float]] = None
    voltages: Optional[Dict[str, float]] = None


class IndustrialControllerSpec(BaseModel):
    protocol: str = "Modbus-TCP"  # "Modbus-TCP", "Siemens-S7comm", "EtherNet/IP-CIP", "Native-Hardware-UEFI"
    endpoint: str = "192.168.1.10:502"
    vendor: str = "Generic-Industrial"
    model_or_catalog: str = "PLC Controller"
    firmware_revision: Optional[str] = None
    serial_number: Optional[str] = None
    operating_state: Optional[str] = "RUN"
    cycle_time_ms: Optional[float] = None
    diagnostics_status: str = "OK"


class ConnectedPeripheralSpec(BaseModel):
    category: str  # "Display / Monitor", "Camera / Video", "Audio / Speaker / Mic", "Keyboard / Input", "Mouse / Pointing Device", "USB Hub / Controller", "Printer"
    name: str  # e.g., "Logitech Brio 4K Webcam", "Dell UltraSharp U2723QE", "Logitech MX Master 3S"
    hardware_id: Optional[str] = None  # e.g. "USB\VID_046D&PID_085E"
    connection_type: str = "Wired / USB"  # "Wired / USB", "Internal / eDP", "HDMI / DisplayPort", "Bluetooth", "PCIe"
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    status: str = "Active / Connected"
    details: Dict[str, Any] = Field(default_factory=dict)  # e.g. resolution: "3840x2160 @ 60Hz", audio_channels: 2


class ConnectedServerSpec(BaseModel):
    server_address: str  # e.g. "192.168.1.5:443" or "10.0.0.1:389"
    service_type: str  # "Active Directory Domain Controller", "HTTPS Server", "Database / SQL", "SMB File Share", "SSH Server", "DNS Server"
    state: str = "ESTABLISHED"
    process_name: Optional[str] = None
    remote_hostname: Optional[str] = None


class DiscoveredNeighborSpec(BaseModel):
    ip_address: str  # "192.168.1.1"
    mac_address: str  # "00:1A:2B:3C:4D:5E"
    device_type: str = "Host / Gateway"  # "Gateway Router", "Server / Workstation", "Printer", "IoT Device"
    hostname: Optional[str] = None


class NetworkTopologyTreeSpec(BaseModel):
    domain_or_workgroup: str = "WORKGROUP"
    dns_servers: List[str] = Field(default_factory=list)
    default_gateway: Optional[str] = None
    dhcp_server: Optional[str] = None
    connected_servers: List[ConnectedServerSpec] = Field(default_factory=list)
    subnet_neighbors: List[DiscoveredNeighborSpec] = Field(default_factory=list)
    active_connections_count: int = 0


class HardwareSpec(BaseModel):
    cpu: CpuSpec
    memory: MemorySpec
    storage: List[StorageDevice] = Field(default_factory=list)
    gpu: List[GpuSpec] = Field(default_factory=list)
    motherboard: MotherboardSpec
    battery: BatterySpec
    network: List[NetworkInterface] = Field(default_factory=list)
    voltages: Dict[str, float] = Field(default_factory=dict)  # e.g., {"vcore": 1.15, "12v": 12.08, "5v": 5.02, "3v3": 3.31}
    fan_rpm: Dict[str, int] = Field(default_factory=dict)    # e.g., {"cpu_fan": 1850, "chassis_fan": 1200}
    gpio_pins: Optional[Dict[str, str]] = None               # e.g., for SBC/Raspberry Pi: {"GPIO4": "HIGH", "GPIO17": "LOW"}
    virtualization: Optional[VirtualizationSpec] = None
    connected_mobile_devices: List[MobileDeviceSpec] = Field(default_factory=list)
    industrial_controllers: List[IndustrialControllerSpec] = Field(default_factory=list)
    connected_peripherals: List[ConnectedPeripheralSpec] = Field(default_factory=list)
    network_topology: Optional[NetworkTopologyTreeSpec] = None


class DiagnosticResult(BaseModel):
    test_name: str
    status: DiagnosticStatus
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    evidence: str
    recommendation: str


CompatibilityMatrix = Dict[str, ModuleCompatibility]


class NormalizedScanPayload(BaseModel):
    schema_version: str = "1.0.0"
    scan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    machine_fingerprint: str
    platform: PlatformEnum
    os_version: str
    timestamp_utc: str
    compatibility_matrix: CompatibilityMatrix = Field(default_factory=dict)
    hardware: HardwareSpec
    diagnostics: List[DiagnosticResult] = Field(default_factory=list)

    @field_validator("machine_fingerprint")
    @classmethod
    def validate_fingerprint_hex(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if len(v_clean) != 64:
            raise ValueError(f"machine_fingerprint must be a 64-character SHA-256 hex string, got {len(v_clean)} chars")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError("machine_fingerprint must contain valid hexadecimal characters only")
        return v_clean

    @staticmethod
    def generate_fingerprint(salt: str, motherboard_uuid: str, cpu_id: str, primary_storage_serial: str) -> str:
        """Derives a deterministic, privacy-safe SHA-256 fingerprint from hardware anchors."""
        raw_anchor = f"{salt}:{motherboard_uuid.strip()}:{cpu_id.strip()}:{primary_storage_serial.strip()}"
        return hashlib.sha256(raw_anchor.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_anchor_similarity(
        p1: "NormalizedScanPayload",
        p2: "NormalizedScanPayload",
    ) -> Dict[str, Any]:
        """Calculates a weighted multi-anchor similarity score (0-100) between two machine scans.

        Solves the component swap dilemma:
        - Motherboard product & vendor match: 50 points
        - CPU model & thread topology match: 30 points
        - Primary storage serial match: 10 points
        - Network MAC hash match: 10 points

        A score >= 75 points indicates the SAME physical machine, even if the primary storage drive
        or network card was replaced/upgraded.
        """
        score = 0.0
        matches = []
        changes = []

        mb1 = p1.hardware.motherboard
        mb2 = p2.hardware.motherboard
        if (mb1.manufacturer.strip().lower() == mb2.manufacturer.strip().lower() and
            mb1.product.strip().lower() == mb2.product.strip().lower()):
            score += 50.0
            matches.append("Motherboard Hardware Signature")
        else:
            changes.append("Motherboard Mismatch")

        cpu1 = p1.hardware.cpu
        cpu2 = p2.hardware.cpu
        if (cpu1.model.strip().lower() == cpu2.model.strip().lower() and
            cpu1.physical_cores == cpu2.physical_cores):
            score += 30.0
            matches.append("CPU Silicon & Topology")
        else:
            changes.append("CPU Mismatch")

        s1_serial = p1.hardware.storage[0].serial_hash if p1.hardware.storage else ""
        s2_serial = p2.hardware.storage[0].serial_hash if p2.hardware.storage else ""
        if s1_serial and s2_serial and s1_serial == s2_serial:
            score += 10.0
            matches.append("Primary Storage Serial")
        else:
            changes.append("Primary Storage Replaced/Swapped")

        macs1 = {n.mac_hash for n in p1.hardware.network if n.mac_hash}
        macs2 = {n.mac_hash for n in p2.hardware.network if n.mac_hash}
        if macs1 and macs2 and macs1.intersection(macs2):
            score += 10.0
            matches.append("Network Interface MAC Hash")
        else:
            changes.append("Network MAC Alteration")

        is_same_machine = score >= 75.0
        return {
            "is_same_machine": is_same_machine,
            "similarity_score": score,
            "matched_anchors": matches,
            "changed_anchors": changes,
            "status": "SAME_DEVICE_COMPONENT_SWAP" if (is_same_machine and score < 100.0) else (
                "EXACT_MATCH" if score == 100.0 else "DIFFERENT_MACHINE"
            ),
        }
