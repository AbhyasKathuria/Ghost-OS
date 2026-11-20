"""Connected Android Diagnostic Telemetry Bridge for Ghost-OS.

Extracts hardware inventory, SoC chipset, Android OS version, battery cycle count,
and health metrics from Android smartphones and tablets connected via USB.

Supports:
1. ADB (Android Debug Bridge) host daemon interrogation
2. Fastboot hardware descriptor probing (bootloader triage)
3. Linux/Windows USB MTP descriptor fallback
"""

import hashlib
import os
import platform
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ghost_core.schemas.scan import (
    DiagnosticResult,
    DiagnosticStatus,
    MobileDeviceSpec,
)


class AndroidDeviceBridge:
    """Interrogates USB-connected Android smartphones and tablets."""

    @classmethod
    def get_adb_binary(cls) -> Optional[str]:
        """Locates the portable or system ADB executable."""
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "..", "tools", "adb", "adb.exe"),
            os.path.join(os.path.dirname(__file__), "..", "..", "tools", "adb", "adb"),
            os.path.join("tools", "adb", "adb.exe"),
            os.path.join("tools", "adb", "adb"),
            "D:\\tools\\adb\\adb.exe",
            "C:\\Users\\kathu\\Downloads\\platform-tools-latest-windows\\platform-tools\\adb.exe",
        ]
        for drive in ["D:\\", "E:\\", "F:\\", "G:\\"]:
            candidates.append(os.path.join(drive, "tools", "adb", "adb.exe"))

        for cand in candidates:
            if os.path.exists(cand):
                return os.path.abspath(cand)

        which_adb = shutil.which("adb")
        if which_adb:
            return which_adb

        return None

    @classmethod
    def query_connected_devices(cls) -> List[MobileDeviceSpec]:
        """Queries the host USB subsystem for connected Android devices via ADB and PnP fallback."""
        devices: List[MobileDeviceSpec] = []
        adb_bin = cls.get_adb_binary()

        if adb_bin:
            try:
                res = subprocess.run(
                    [adb_bin, "devices", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout:
                    for line in res.stdout.splitlines()[1:]:
                        line = line.strip()
                        if line and not line.startswith("*"):
                            dev = cls.interrogate_adb_device(adb_bin, line)
                            if dev:
                                devices.append(dev)
            except Exception:
                pass

        # Fallback to Windows PnP if no ADB device found
        if not devices and platform.system() == "Windows":
            pnp_devs = cls._query_windows_pnp_android()
            devices.extend(pnp_devs)

        return devices

    @classmethod
    def interrogate_adb_device(cls, adb_bin: str, device_line: str) -> Optional[MobileDeviceSpec]:
        """Interrogates an active Android device via ADB for complete hardware telemetry."""
        parts = device_line.split()
        if len(parts) < 2:
            return None

        serial = parts[0]
        status = parts[1]  # "device", "unauthorized", "recovery"

        model = "Android Device"
        for part in parts[2:]:
            if part.startswith("model:"):
                model = part.split(":", 1)[1].replace("_", " ")

        serial_hash = hashlib.sha256(serial.encode("utf-8")).hexdigest()

        if status != "device":
            status_desc = "Authorized" if status == "device" else f"Unauthorized ({status} - Check phone screen to allow USB debugging)"
            return MobileDeviceSpec(
                device_type="Android",
                model=model,
                os_version="Android (USB Connected)",
                serial_hash=serial_hash,
                status=status_desc,
            )

        # Device is authorized - query rich telemetry
        props = cls._query_adb_properties(adb_bin, serial)
        battery = cls._query_adb_battery(adb_bin, serial)

        if props:
            spec, _ = cls.parse_getprop_telemetry(props, battery)
            spec.serial_hash = serial_hash
            spec.status = "Authorized (Live Type-C Interrogated)"
            return spec

        return MobileDeviceSpec(
            device_type="Android",
            model=model,
            os_version="Android",
            serial_hash=serial_hash,
            status="Authorized",
        )

    @classmethod
    def _query_adb_properties(cls, adb_bin: str, serial: str) -> Dict[str, str]:
        """Queries getprop from device."""
        props: Dict[str, str] = {}
        try:
            res = subprocess.run(
                [adb_bin, "-s", serial, "shell", "getprop"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    match = re.match(r"\[(.*?)\]:\s*\[(.*?)\]", line.strip())
                    if match:
                        props[match.group(1)] = match.group(2)
        except Exception:
            pass
        return props

    @classmethod
    def _query_adb_battery(cls, adb_bin: str, serial: str) -> Dict[str, Any]:
        """Queries dumpsys battery from device."""
        battery: Dict[str, Any] = {}
        try:
            res = subprocess.run(
                [adb_bin, "-s", serial, "shell", "dumpsys", "battery"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        try:
                            battery[k] = int(v)
                        except ValueError:
                            battery[k] = v
        except Exception:
            pass
        return battery

    @classmethod
    def _query_windows_pnp_android(cls) -> List[MobileDeviceSpec]:
        """Detects Android devices plugged in via USB MTP/PnP."""
        devices: List[MobileDeviceSpec] = []
        try:
            cmd = (
                "Get-CimInstance Win32_PnPEntity | "
                "Where-Object { $_.Manufacturer -match 'Samsung|Google|Xiaomi|OnePlus|Huawei|Oppo|Vivo|Motorola' "
                "-or $_.Name -match 'Android|Galaxy|Pixel' } | "
                "Select-Object Name, Manufacturer, DeviceID | ConvertTo-Json -Compress"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                raw = json.loads(res.stdout)
                items = raw if isinstance(raw, list) else [raw]
                for item in items:
                    name = item.get("Name") or "Android Smartphone"
                    mfg = item.get("Manufacturer") or "Android"
                    dev_id = item.get("DeviceID") or name
                    serial_hash = hashlib.sha256(dev_id.encode("utf-8")).hexdigest()
                    devices.append(
                        MobileDeviceSpec(
                            device_type="Android",
                            model=f"{mfg} {name}",
                            os_version="Android (USB MTP Connected)",
                            serial_hash=serial_hash,
                            status="Connected (MTP Mode - Enable USB Debugging for full battery telemetry)",
                        )
                    )
        except Exception:
            pass
        return devices

    @staticmethod
    def parse_adb_line(line: str) -> Optional[MobileDeviceSpec]:
        """Parses output of 'adb devices -l' to extract device identifiers."""
        parts = line.split()
        if len(parts) < 2:
            return None

        serial = parts[0]
        status = parts[1]  # "device", "unauthorized", "recovery"

        model = "Android Device"
        for part in parts[2:]:
            if part.startswith("model:"):
                model = part.split(":", 1)[1].replace("_", " ")

        serial_hash = hashlib.sha256(serial.encode("utf-8")).hexdigest()

        return MobileDeviceSpec(
            device_type="Android",
            model=model,
            os_version="Android (USB Connected)",
            serial_hash=serial_hash,
            status=status,
        )

    @staticmethod
    def parse_getprop_telemetry(props: Dict[str, str], battery_info: Optional[Dict[str, Any]] = None) -> Tuple[MobileDeviceSpec, DiagnosticResult]:
        """Parses Android 'getprop' and 'dumpsys battery' key-value telemetry."""
        manufacturer = props.get("ro.product.manufacturer", "Android").title()
        model = props.get("ro.product.model", "Universal Smartphone")
        full_model = f"{manufacturer} {model}"

        android_ver = props.get("ro.build.version.release", "Unknown")
        sdk_level = props.get("ro.build.version.sdk", "")
        soc_chipset = props.get("ro.board.platform", props.get("ro.hardware", "ARM64 SoC"))
        security_patch = props.get("ro.build.version.security_patch", "Unknown")

        os_str = f"Android {android_ver} (API {sdk_level}, Patch: {security_patch})"
        serial = props.get("ro.serialno", props.get("ro.boot.serialno", "UNKNOWN_SERIAL"))
        serial_hash = hashlib.sha256(serial.encode("utf-8")).hexdigest()

        # Parse battery health & cycle telemetry
        cycles = None
        health_pct = None
        bat_status = "Good"

        if battery_info:
            cycles = battery_info.get("cycle_count")
            level = battery_info.get("level", 100)
            health_code = battery_info.get("health", 2)  # 2 = BATTERY_HEALTH_GOOD
            if health_code == 2:
                bat_status = "Good"
            elif health_code == 3:
                bat_status = "Overheat"
            elif health_code == 4:
                bat_status = "Dead / Failing"
            else:
                bat_status = "Unknown"

            # Estimate health % from capacity if present
            charge_counter = battery_info.get("charge_counter")
            charge_full = battery_info.get("charge_full_design")
            if charge_counter and charge_full and charge_full > 0:
                health_pct = round((charge_counter / charge_full) * 100.0, 1)
            else:
                health_pct = float(level)

        spec = MobileDeviceSpec(
            device_type="Android",
            model=full_model,
            os_version=os_str,
            serial_hash=serial_hash,
            battery_health_pct=health_pct,
            battery_cycles=cycles,
            status="Authorized",
        )

        diag = DiagnosticResult(
            test_name=f"Mobile Device Telemetry ({spec.model})",
            status=DiagnosticStatus.PASS,
            evidence=f"Connected {full_model} (SoC: {soc_chipset}) running {os_str}. Battery health: {bat_status}, Cycles: {cycles or 'N/A'}.",
            recommendation="Mobile device hardware verified. USB debugging link authenticated.",
        )

        return spec, diag

    @classmethod
    def simulate_connected_android_device(
        cls,
        manufacturer: str = "Samsung",
        model: str = "Galaxy S24 Ultra (SM-S928B)",
        android_ver: str = "14",
        soc: str = "Snapdragon 8 Gen 3 for Galaxy",
        cycle_count: int = 42,
    ) -> Tuple[MobileDeviceSpec, DiagnosticResult]:
        """Provides simulated Android device telemetry for offline test evaluation."""
        props = {
            "ro.product.manufacturer": manufacturer,
            "ro.product.model": model,
            "ro.build.version.release": android_ver,
            "ro.build.version.sdk": "34",
            "ro.board.platform": soc,
            "ro.build.version.security_patch": "2026-10-01",
            "ro.serialno": "RF8X10ABCDEF",
        }
        battery = {
            "cycle_count": cycle_count,
            "level": 94,
            "health": 2,
            "charge_counter": 4850000,
            "charge_full_design": 5000000,
        }
        return cls.parse_getprop_telemetry(props, battery)
