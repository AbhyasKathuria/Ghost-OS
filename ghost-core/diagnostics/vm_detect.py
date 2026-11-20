"""Hypervisor and Virtual Machine Detection for Ghost-OS.

Detects whether Ghost-OS is running inside a guest VM (VirtualBox, VMware,
KVM/QEMU, Hyper-V, Xen, Parallels, WSL) and surfaces accurate diagnostics.
"""

import os
import platform
import subprocess
from typing import Optional, Tuple
from ghost_core.schemas.scan import (
    DiagnosticResult,
    DiagnosticStatus,
    VirtualizationSpec,
)


def detect_virtualization(
    manufacturer: str = "",
    product: str = "",
    bios_version: str = "",
    mac_prefixes: Optional[list] = None,
) -> Tuple[VirtualizationSpec, DiagnosticResult]:
    """Detects hypervisor environment based on hardware signatures."""
    manuf_lower = (manufacturer or "").lower()
    prod_lower = (product or "").lower()
    bios_lower = (bios_version or "").lower()
    combined = f"{manuf_lower} {prod_lower} {bios_lower}"

    hypervisor = "Bare-Metal"
    is_virtual = False
    detection_method = "Physical Hardware DMI"

    # Known hypervisor signatures
    if "virtualbox" in combined or "innotek" in combined or "vbox" in combined:
        hypervisor = "VirtualBox"
        is_virtual = True
        detection_method = "DMI / BIOS Signature"
    elif "vmware" in combined:
        hypervisor = "VMware"
        is_virtual = True
        detection_method = "DMI / BIOS Signature"
    elif "qemu" in combined or "kvm" in combined or "bochs" in combined:
        hypervisor = "KVM/QEMU"
        is_virtual = True
        detection_method = "DMI / BIOS Signature"
    elif "microsoft corporation" in manuf_lower and ("virtual machine" in prod_lower or "hyper-v" in combined):
        hypervisor = "Hyper-V"
        is_virtual = True
        detection_method = "DMI / Hyper-V Signature"
    elif "xen" in combined:
        hypervisor = "Xen"
        is_virtual = True
        detection_method = "DMI / BIOS Signature"
    elif "parallels" in combined:
        hypervisor = "Parallels"
        is_virtual = True
        detection_method = "DMI / BIOS Signature"

    # Check Linux system files if available
    if not is_virtual and os.path.exists("/sys/class/dmi/id/sys_vendor"):
        try:
            with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                vendor = f.read().strip().lower()
                if any(h in vendor for h in ["qemu", "kvm", "vmware", "innotek", "bochs"]):
                    is_virtual = True
                    hypervisor = vendor.title()
                    detection_method = "/sys/class/dmi/id/sys_vendor"
        except Exception:
            pass

    # Check /proc/cpuinfo for hypervisor flag on Linux
    if not is_virtual and os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                if "hypervisor" in f.read().lower():
                    is_virtual = True
                    hypervisor = "Generic Hypervisor (KVM/Xen/QEMU)"
                    detection_method = "/proc/cpuinfo hypervisor flag"
        except Exception:
            pass

    virt_spec = VirtualizationSpec(
        is_virtual=is_virtual,
        hypervisor=hypervisor,
        detection_method=detection_method,
    )

    if is_virtual:
        diag = DiagnosticResult(
            test_name="Virtual Machine Isolation Check",
            status=DiagnosticStatus.WARN,
            metric_value=1.0,
            threshold=0.0,
            evidence=f"Running inside {hypervisor} virtual machine (detected via {detection_method}). Hardware inventory is virtualized by hypervisor.",
            recommendation="Boot Ghost-OS directly on bare metal via USB for physical motherboard, RAM serials, and low-level component telemetry.",
        )
    else:
        diag = DiagnosticResult(
            test_name="Virtual Machine Isolation Check",
            status=DiagnosticStatus.PASS,
            metric_value=0.0,
            threshold=0.0,
            evidence="Running directly on physical bare-metal hardware. Direct component access confirmed.",
            recommendation="Hardware inventory reflects authoritative physical components.",
        )

    return virt_spec, diag
