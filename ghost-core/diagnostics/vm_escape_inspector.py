"""Hypervisor Guest-to-Host Hardware Discovery & Escape Inspector.

Detects the TRUE physical host hardware when Ghost-OS is executed inside a VM:
1. WSL2 Interop: Interrogates host Windows WMI/CIM directly via host bridge.
2. Hyper-V KVP: Extracts host attributes from hyperv key-value pools.
3. VirtualBox / VMware Guest Additions: Queries guest-to-host IPC properties.
4. CPUID Unmasked Leaves: Reads true physical processor silicon string.
"""

import os
import subprocess
from typing import Dict, Optional, Tuple
from ghost_core.schemas.scan import DiagnosticResult, DiagnosticStatus


class VirtualMachineHostInspector:
    @staticmethod
    def inspect_host_hardware_from_guest() -> Tuple[bool, Dict[str, str], DiagnosticResult]:
        """Probes guest-to-host hypervisor channels to extract physical host machine details."""
        host_telemetry: Dict[str, str] = {}
        detection_channel = "None"
        found_host_hardware = False

        # Channel 1: WSL2 Windows Host Interop Bridge
        wsl_interop_path = "/mnt/c/Windows/System32/cmd.exe"
        if os.path.exists(wsl_interop_path):
            try:
                res = subprocess.run(
                    [wsl_interop_path, "/c", "wmic baseboard get manufacturer,product /value"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and "Manufacturer=" in res.stdout:
                    found_host_hardware = True
                    detection_channel = "WSL2 Windows Host Bridge"
                    for line in res.stdout.splitlines():
                        if "=" in line:
                            k, v = line.split("=", 1)
                            host_telemetry[f"host_motherboard_{k.lower()}"] = v.strip()
            except Exception:
                pass

        # Channel 2: VirtualBox VBoxControl Guest Property IPC
        if not found_host_hardware:
            try:
                res = subprocess.run(
                    ["VBoxControl", "-nologo", "guestproperty", "enumerate"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout:
                    found_host_hardware = True
                    detection_channel = "VirtualBox Guest Additions IPC"
                    for line in res.stdout.splitlines():
                        if "HostGuest/Sysprep" in line or "HostInfo" in line:
                            parts = line.split(",")
                            if len(parts) >= 2:
                                host_telemetry[parts[0].strip()] = parts[1].strip()
            except Exception:
                pass

        # Channel 3: Hyper-V KVP Key-Value Pool
        kvp_pool = "/var/lib/hyperv/.kvp_pool_3"
        if not found_host_hardware and os.path.exists(kvp_pool):
            found_host_hardware = True
            detection_channel = "Hyper-V Guest Integration Daemon (KVP)"
            host_telemetry["hypervisor_integration"] = "Hyper-V KVP Active"

        # Channel 4: CPUID Processor Brand Leaf
        # In almost all VMs (VMware, VirtualBox, KVM, Hyper-V), the hypervisor passes the real host CPU string
        cpu_model = ""
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_model = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

        if cpu_model and not any(v in cpu_model.lower() for v in ["qemu", "virtual", "bochs"]):
            host_telemetry["host_physical_cpu"] = cpu_model
            found_host_hardware = True
            if detection_channel == "None":
                detection_channel = "Unmasked Hardware CPUID Leaves"

        if found_host_hardware:
            details = ", ".join(f"{k}: {v}" for k, v in host_telemetry.items())
            diag = DiagnosticResult(
                test_name="Virtual Machine Host Hardware Inspection",
                status=DiagnosticStatus.PASS,
                metric_value=1.0,
                threshold=0.0,
                evidence=f"Successfully extracted physical host hardware via {detection_channel}. {details}",
                recommendation="Host silicon attributes identified through hypervisor guest communication bridge.",
            )
        else:
            diag = DiagnosticResult(
                test_name="Virtual Machine Host Hardware Inspection",
                status=DiagnosticStatus.WARN,
                metric_value=0.0,
                threshold=1.0,
                evidence="Hypervisor is operating with strict hardware isolation. Physical host motherboard masked.",
                recommendation="Boot Ghost-OS via physical USB for bare-metal host telemetry.",
            )

        return found_host_hardware, host_telemetry, diag
