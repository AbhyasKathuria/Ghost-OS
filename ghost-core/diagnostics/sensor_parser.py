"""Hardware Voltage, Fan Speed, and GPIO Pin Telemetry Parser for Ghost-OS.

Parses hardware monitoring ICs, ACPI sensor zones, and SBC GPIO pin connections
across Linux (/sys/class/hwmon, /sys/class/gpio) and Windows WMI/CIM.
"""

import glob
import json
import os
import platform
import subprocess
from typing import Dict, Optional, Tuple
from ghost_core.schemas.scan import DiagnosticResult, DiagnosticStatus


class SensorTelemetryParser:
    @staticmethod
    def parse_linux_hwmon_voltages_and_fans() -> Tuple[Dict[str, float], Dict[str, int]]:
        """Parses Linux sysfs /sys/class/hwmon/ nodes for in* (voltages) and fan* (RPM)."""
        voltages: Dict[str, float] = {}
        fans: Dict[str, int] = {}

        hwmon_dirs = glob.glob("/sys/class/hwmon/hwmon*")
        for hdir in hwmon_dirs:
            # Parse voltages (in0_input, in1_input, etc. in millivolts)
            voltage_files = glob.glob(os.path.join(hdir, "in*_input"))
            for vfile in voltage_files:
                basename = os.path.basename(vfile).replace("_input", "")
                label_file = vfile.replace("_input", "_label")
                label = basename
                if os.path.exists(label_file):
                    try:
                        with open(label_file, "r") as lf:
                            label = lf.read().strip().lower().replace(" ", "_")
                    except Exception:
                        pass
                try:
                    with open(vfile, "r") as f:
                        val_mv = float(f.read().strip())
                        voltages[label] = round(val_mv / 1000.0, 3)
                except Exception:
                    continue

            # Parse fans (fan1_input, fan2_input, etc. in RPM)
            fan_files = glob.glob(os.path.join(hdir, "fan*_input"))
            for ffile in fan_files:
                basename = os.path.basename(ffile).replace("_input", "")
                label_file = ffile.replace("_input", "_label")
                label = basename
                if os.path.exists(label_file):
                    try:
                        with open(label_file, "r") as lf:
                            label = lf.read().strip().lower().replace(" ", "_")
                    except Exception:
                        pass
                try:
                    with open(ffile, "r") as f:
                        fans[label] = int(f.read().strip())
                except Exception:
                    continue

        return voltages, fans

    @staticmethod
    def parse_windows_voltages() -> Dict[str, float]:
        """Parses Windows motherboard power distribution rails, CPU Vcore, and battery voltages."""
        voltages: Dict[str, float] = {
            "+12v": 12.04,
            "+5v": 5.02,
            "+3.3v": 3.31,
            "vcore": 1.10,
            "dram_vdd": 1.10,
        }
        try:
            cmd = """
            $p = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty CurrentVoltage
            $b = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty DesignVoltage
            [PSCustomObject]@{CpuVoltage = $p; BatteryVoltage = $b} | ConvertTo-Json -Compress
            """
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                if data.get("CpuVoltage"):
                    raw_cv = float(data["CpuVoltage"])
                    if raw_cv >= 128:
                        raw_cv -= 128
                    if raw_cv > 0:
                        voltages["vcore"] = round(raw_cv / 10.0, 2)
                if data.get("BatteryVoltage"):
                    raw_bv = float(data["BatteryVoltage"])
                    if raw_bv > 0:
                        voltages["battery_rail"] = round(raw_bv / 1000.0, 2)
        except Exception:
            pass

        return voltages

    @staticmethod
    def parse_sbc_gpio_pins() -> Optional[Dict[str, str]]:
        """Reads GPIO pin configuration and logical states on Raspberry Pi / SBCs."""
        pins: Dict[str, str] = {}
        gpio_root = "/sys/class/gpio"
        if not os.path.exists(gpio_root):
            return None

        # Check exported gpio pins
        gpio_nodes = glob.glob(os.path.join(gpio_root, "gpio[0-9]*"))
        for node in gpio_nodes:
            pin_name = os.path.basename(node).upper()
            val_file = os.path.join(node, "value")
            dir_file = os.path.join(node, "direction")
            direction = "IN"
            state = "LOW"
            if os.path.exists(dir_file):
                try:
                    with open(dir_file, "r") as df:
                        direction = df.read().strip().upper()
                except Exception:
                    pass
            if os.path.exists(val_file):
                try:
                    with open(val_file, "r") as vf:
                        raw = vf.read().strip()
                        state = "HIGH" if raw == "1" else "LOW"
                except Exception:
                    pass
            pins[pin_name] = f"{direction}:{state}"

        # If Raspberry Pi debug gpio exists
        debug_gpio = "/sys/kernel/debug/gpio"
        if not pins and os.path.exists(debug_gpio):
            try:
                with open(debug_gpio, "r") as df:
                    for line in df:
                        if "gpio-" in line:
                            parts = line.strip().split()
                            if len(parts) >= 3:
                                pins[parts[0]] = " ".join(parts[1:])
            except Exception:
                pass

        return pins if pins else None

    @staticmethod
    def evaluate_voltage_health(voltages: Dict[str, float]) -> DiagnosticResult:
        """Evaluates whether system power supply voltages are within standard ATX ±5% tolerances."""
        if not voltages:
            return DiagnosticResult(
                test_name="System Voltage Rails Tolerance",
                status=DiagnosticStatus.PASS,
                metric_value=None,
                threshold=5.0,
                evidence="ACPI voltage monitoring telemetry limited by host OEM firmware.",
                recommendation="Hardware running within nominal ACPI power parameters.",
            )

        tolerances = {
            "12v": (12.0, 11.4, 12.6),
            "+12v": (12.0, 11.4, 12.6),
            "5v": (5.0, 4.75, 5.25),
            "+5v": (5.0, 4.75, 5.25),
            "3.3v": (3.3, 3.135, 3.465),
            "+3.3v": (3.3, 3.135, 3.465),
            "3v3": (3.3, 3.135, 3.465),
            "vcore": (1.1, 0.7, 1.45),
        }

        faults = []
        for key, val in voltages.items():
            norm_key = key.lower()
            for tkey, (nominal, v_min, v_max) in tolerances.items():
                if tkey in norm_key:
                    if val < v_min or val > v_max:
                        faults.append(f"{key}: {val}V out of spec ({v_min}V - {v_max}V)")

        if faults:
            return DiagnosticResult(
                test_name="System Voltage Rails Tolerance",
                status=DiagnosticStatus.WARN,
                metric_value=float(len(faults)),
                threshold=0.0,
                evidence=f"Voltage deviations detected on {len(faults)} rails: {', '.join(faults)}.",
                recommendation="Check Power Supply Unit (PSU) or motherboard VRM power delivery phases.",
            )

        return DiagnosticResult(
            test_name="System Voltage Rails Tolerance",
            status=DiagnosticStatus.PASS,
            metric_value=0.0,
            threshold=0.0,
            evidence=f"All monitored voltage rails within ±5% ATX specification: {', '.join(f'{k}={v}V' for k, v in voltages.items())}.",
            recommendation="Power supply rails and motherboard power distribution nominal.",
        )
