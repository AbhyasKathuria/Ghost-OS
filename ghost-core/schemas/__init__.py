"""Ghost-OS Canonical Pydantic Schemas."""
from .scan import (
    NormalizedScanPayload,
    HardwareSpec,
    CpuSpec,
    MemorySpec,
    MemoryModule,
    StorageDevice,
    GpuSpec,
    MotherboardSpec,
    BatterySpec,
    NetworkInterface,
    DiagnosticResult,
    DiagnosticStatus,
    ModuleCompatibility,
    CompatibilityMatrix,
)

__all__ = [
    "NormalizedScanPayload",
    "HardwareSpec",
    "CpuSpec",
    "MemorySpec",
    "MemoryModule",
    "StorageDevice",
    "GpuSpec",
    "MotherboardSpec",
    "BatterySpec",
    "NetworkInterface",
    "DiagnosticResult",
    "DiagnosticStatus",
    "ModuleCompatibility",
    "CompatibilityMatrix",
]
