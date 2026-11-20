"""Ghost-OS Hardware Change Detection & Diff Engine.

Compares historical scans for a machine fingerprint to detect component upgrades,
replacements, firmware changes, and progressive degradation (battery wear > 2%,
SSD wear increases, rising idle temperatures).
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from ghost_core.schemas.scan import NormalizedScanPayload


class ChangeType(str, Enum):
    UPGRADE = "UPGRADE"
    REPLACEMENT = "REPLACEMENT"
    DEGRADATION = "DEGRADATION"
    FIRMWARE_CONFIG = "FIRMWARE_CONFIG"
    REMOVAL = "REMOVAL"
    INFO = "INFO"


class ComponentChange(BaseModel):
    component: str  # "RAM", "Storage", "Motherboard BIOS", "GPU", "Battery", "OS"
    change_type: ChangeType
    property_name: str
    old_value: Any
    new_value: Any
    description: str


class HardwareDiffReport(BaseModel):
    machine_fingerprint: str
    baseline_scan_id: str
    current_scan_id: str
    baseline_timestamp_utc: str
    current_timestamp_utc: str
    baseline_platform: str
    current_platform: str
    changes_detected: bool
    total_changes: int
    changes: List[ComponentChange] = Field(default_factory=list)
    degradations: List[ComponentChange] = Field(default_factory=list)
    summary: str


class HardwareDiffEngine:
    """Computes fine-grained hardware deltas between two NormalizedScanPayload instances."""

    @classmethod
    def find_historical_match(
        cls,
        current_scan: NormalizedScanPayload,
        historical_scans: List[NormalizedScanPayload],
        threshold: float = 75.0,
    ) -> Optional[Tuple[NormalizedScanPayload, Dict[str, Any]]]:
        """Finds matching historical machine record even if primary SSD serial or MAC address has changed."""
        best_match = None
        highest_score = 0.0
        best_analysis = None

        for hist in historical_scans:
            analysis = NormalizedScanPayload.compute_anchor_similarity(hist, current_scan)
            if analysis["similarity_score"] > highest_score and analysis["similarity_score"] >= threshold:
                highest_score = analysis["similarity_score"]
                best_match = hist
                best_analysis = analysis

        if best_match and best_analysis:
            return best_match, best_analysis
        return None

    @classmethod
    def compare_scans(
        cls,
        baseline: NormalizedScanPayload,
        current: NormalizedScanPayload,
    ) -> HardwareDiffReport:
        changes: List[ComponentChange] = []
        degradations: List[ComponentChange] = []

        # 1. OS & Platform Parity / Transition Check
        if baseline.platform != current.platform:
            changes.append(
                ComponentChange(
                    component="Platform",
                    change_type=ChangeType.INFO,
                    property_name="platform",
                    old_value=baseline.platform.value,
                    new_value=current.platform.value,
                    description=f"Cross-OS scan transition from {baseline.platform.value} to {current.platform.value}.",
                )
            )

        if baseline.os_version != current.os_version:
            changes.append(
                ComponentChange(
                    component="Operating System",
                    change_type=ChangeType.FIRMWARE_CONFIG,
                    property_name="os_version",
                    old_value=baseline.os_version,
                    new_value=current.os_version,
                    description=f"Operating system version updated from {baseline.os_version} to {current.os_version}.",
                )
            )

        # 2. Motherboard & BIOS Check
        cls._diff_motherboard(baseline, current, changes)

        # 3. RAM Modules & Capacity Check
        cls._diff_memory(baseline, current, changes, degradations)

        # 4. Storage Drives, SMART, & Wear Check
        cls._diff_storage(baseline, current, changes, degradations)

        # 5. GPU & Display Drivers Check
        cls._diff_gpu(baseline, current, changes)

        # 6. Battery Degradation & Cycle Life Check
        cls._diff_battery(baseline, current, changes, degradations)

        # 7. Thermal Trends Check
        cls._diff_thermals(baseline, current, degradations)

        total = len(changes) + len(degradations)
        changes_detected = total > 0

        if not changes_detected:
            summary = "No hardware modifications or degradation detected between scans. Configuration is identical."
        else:
            summary = (
                f"Detected {total} difference(s): {len(changes)} modification(s) and {len(degradations)} degradation alert(s)."
            )

        return HardwareDiffReport(
            machine_fingerprint=current.machine_fingerprint,
            baseline_scan_id=baseline.scan_id,
            current_scan_id=current.scan_id,
            baseline_timestamp_utc=baseline.timestamp_utc,
            current_timestamp_utc=current.timestamp_utc,
            baseline_platform=baseline.platform.value,
            current_platform=current.platform.value,
            changes_detected=changes_detected,
            total_changes=total,
            changes=changes,
            degradations=degradations,
            summary=summary,
        )

    @classmethod
    def _diff_motherboard(
        cls,
        base: NormalizedScanPayload,
        curr: NormalizedScanPayload,
        changes: List[ComponentChange],
    ) -> None:
        b_mb = base.hardware.motherboard
        c_mb = curr.hardware.motherboard

        if b_mb.bios_version != c_mb.bios_version:
            changes.append(
                ComponentChange(
                    component="Motherboard BIOS",
                    change_type=ChangeType.FIRMWARE_CONFIG,
                    property_name="bios_version",
                    old_value=b_mb.bios_version,
                    new_value=c_mb.bios_version,
                    description=f"BIOS firmware updated from '{b_mb.bios_version}' to '{c_mb.bios_version}'.",
                )
            )

        if b_mb.secure_boot_enabled != c_mb.secure_boot_enabled and c_mb.secure_boot_enabled is not None:
            changes.append(
                ComponentChange(
                    component="Motherboard Security",
                    change_type=ChangeType.FIRMWARE_CONFIG,
                    property_name="secure_boot_enabled",
                    old_value=b_mb.secure_boot_enabled,
                    new_value=c_mb.secure_boot_enabled,
                    description=f"Secure Boot changed from {b_mb.secure_boot_enabled} to {c_mb.secure_boot_enabled}.",
                )
            )

    @classmethod
    def _diff_memory(
        cls,
        base: NormalizedScanPayload,
        curr: NormalizedScanPayload,
        changes: List[ComponentChange],
        degradations: List[ComponentChange],
    ) -> None:
        b_mem = base.hardware.memory
        c_mem = curr.hardware.memory

        b_gb = round(b_mem.total_bytes / (1024**3), 1)
        c_gb = round(c_mem.total_bytes / (1024**3), 1)

        if c_mem.total_bytes > b_mem.total_bytes:
            changes.append(
                ComponentChange(
                    component="RAM",
                    change_type=ChangeType.UPGRADE,
                    property_name="total_capacity",
                    old_value=f"{b_gb} GB",
                    new_value=f"{c_gb} GB",
                    description=f"RAM capacity upgraded from {b_gb} GB to {c_gb} GB.",
                )
            )
        elif c_mem.total_bytes < b_mem.total_bytes:
            degradations.append(
                ComponentChange(
                    component="RAM",
                    change_type=ChangeType.DEGRADATION,
                    property_name="total_capacity",
                    old_value=f"{b_gb} GB",
                    new_value=f"{c_gb} GB",
                    description=f"RAM capacity decreased from {b_gb} GB to {c_gb} GB (possible module failure or removal).",
                )
            )

        # Check speed or module replacement
        if c_mem.modules and b_mem.modules:
            b_speeds = [m.speed_mhz for m in b_mem.modules if m.speed_mhz]
            c_speeds = [m.speed_mhz for m in c_mem.modules if m.speed_mhz]
            if b_speeds and c_speeds and max(c_speeds) > max(b_speeds):
                changes.append(
                    ComponentChange(
                        component="RAM",
                        change_type=ChangeType.UPGRADE,
                        property_name="speed_mhz",
                        old_value=max(b_speeds),
                        new_value=max(c_speeds),
                        description=f"Memory speed increased from {max(b_speeds)} MHz to {max(c_speeds)} MHz.",
                    )
                )

    @classmethod
    def _diff_storage(
        cls,
        base: NormalizedScanPayload,
        curr: NormalizedScanPayload,
        changes: List[ComponentChange],
        degradations: List[ComponentChange],
    ) -> None:
        b_drives = {d.device_id: d for d in base.hardware.storage}
        c_drives = {d.device_id: d for d in curr.hardware.storage}

        # Check drive additions/replacements by device_id or serial_hash
        b_serials = {d.serial_hash: d for d in base.hardware.storage}
        c_serials = {d.serial_hash: d for d in curr.hardware.storage}

        for serial, c_dev in c_serials.items():
            if serial not in b_serials:
                changes.append(
                    ComponentChange(
                        component="Storage",
                        change_type=ChangeType.REPLACEMENT,
                        property_name="drive_serial",
                        old_value="None",
                        new_value=c_dev.model,
                        description=f"New or replaced storage drive detected: {c_dev.model} ({c_dev.interface}).",
                    )
                )

        for serial, b_dev in b_serials.items():
            if serial not in c_serials:
                changes.append(
                    ComponentChange(
                        component="Storage",
                        change_type=ChangeType.REMOVAL,
                        property_name="drive_serial",
                        old_value=b_dev.model,
                        new_value="None",
                        description=f"Storage drive removed or replaced: {b_dev.model}.",
                    )
                )

        # Check wear level and SMART changes on matching drives
        for serial, c_dev in c_serials.items():
            if serial in b_serials:
                b_dev = b_serials[serial]
                # Wear level degradation
                if (
                    b_dev.wear_level_pct is not None
                    and c_dev.wear_level_pct is not None
                    and c_dev.wear_level_pct > b_dev.wear_level_pct
                ):
                    wear_delta = round(c_dev.wear_level_pct - b_dev.wear_level_pct, 1)
                    degradations.append(
                        ComponentChange(
                            component="Storage Wear",
                            change_type=ChangeType.DEGRADATION,
                            property_name="wear_level_pct",
                            old_value=f"{b_dev.wear_level_pct}%",
                            new_value=f"{c_dev.wear_level_pct}%",
                            description=f"Drive '{c_dev.model}' wear level increased by {wear_delta}% ({b_dev.wear_level_pct}% -> {c_dev.wear_level_pct}%).",
                        )
                    )

                # SMART status change
                if b_dev.smart_status != c_dev.smart_status:
                    ch_type = ChangeType.DEGRADATION if c_dev.smart_status in ("WARNING", "FAILED") else ChangeType.INFO
                    target_list = degradations if ch_type == ChangeType.DEGRADATION else changes
                    target_list.append(
                        ComponentChange(
                            component="Storage SMART",
                            change_type=ch_type,
                            property_name="smart_status",
                            old_value=b_dev.smart_status,
                            new_value=c_dev.smart_status,
                            description=f"Drive '{c_dev.model}' SMART health changed from {b_dev.smart_status} to {c_dev.smart_status}.",
                        )
                    )

    @classmethod
    def _diff_gpu(
        cls,
        base: NormalizedScanPayload,
        curr: NormalizedScanPayload,
        changes: List[ComponentChange],
    ) -> None:
        b_gpus = {g.name: g for g in base.hardware.gpu}
        c_gpus = {g.name: g for g in curr.hardware.gpu}

        for name, c_gpu in c_gpus.items():
            if name in b_gpus:
                b_gpu = b_gpus[name]
                if b_gpu.driver_version and c_gpu.driver_version and b_gpu.driver_version != c_gpu.driver_version:
                    changes.append(
                        ComponentChange(
                            component="GPU Driver",
                            change_type=ChangeType.FIRMWARE_CONFIG,
                            property_name="driver_version",
                            old_value=b_gpu.driver_version,
                            new_value=c_gpu.driver_version,
                            description=f"Graphics driver for '{name}' changed from {b_gpu.driver_version} to {c_gpu.driver_version}.",
                        )
                    )
            else:
                changes.append(
                    ComponentChange(
                        component="GPU",
                        change_type=ChangeType.UPGRADE,
                        property_name="name",
                        old_value="None",
                        new_value=name,
                        description=f"New GPU hardware detected: {name}.",
                    )
                )

    @classmethod
    def _diff_battery(
        cls,
        base: NormalizedScanPayload,
        curr: NormalizedScanPayload,
        changes: List[ComponentChange],
        degradations: List[ComponentChange],
    ) -> None:
        b_bat = base.hardware.battery
        c_bat = curr.hardware.battery

        if not b_bat.present and not c_bat.present:
            return

        if b_bat.present and not c_bat.present:
            changes.append(
                ComponentChange(
                    component="Battery",
                    change_type=ChangeType.REMOVAL,
                    property_name="present",
                    old_value=True,
                    new_value=False,
                    description="Battery is no longer detected.",
                )
            )
            return

        if not b_bat.present and c_bat.present:
            changes.append(
                ComponentChange(
                    component="Battery",
                    change_type=ChangeType.UPGRADE,
                    property_name="present",
                    old_value=False,
                    new_value=True,
                    description="Battery detected in system.",
                )
            )
            return

        # Check battery health percentage drop > 2%
        b_health = b_bat.health_pct
        c_health = c_bat.health_pct

        if b_health is not None and c_health is not None:
            health_drop = round(b_health - c_health, 1)
            if health_drop > 2.0:
                degradations.append(
                    ComponentChange(
                        component="Battery Wear",
                        change_type=ChangeType.DEGRADATION,
                        property_name="health_pct",
                        old_value=f"{b_health}%",
                        new_value=f"{c_health}%",
                        description=f"Battery health degraded by {health_drop}% (dropped from {b_health}% to {c_health}%).",
                    )
                )

        # Check cycle count increase
        if b_bat.cycle_count is not None and c_bat.cycle_count is not None:
            cycle_delta = c_bat.cycle_count - b_bat.cycle_count
            if cycle_delta > 0:
                changes.append(
                    ComponentChange(
                        component="Battery Cycles",
                        change_type=ChangeType.INFO,
                        property_name="cycle_count",
                        old_value=b_bat.cycle_count,
                        new_value=c_bat.cycle_count,
                        description=f"Battery accumulated {cycle_delta} additional charge cycle(s) ({b_bat.cycle_count} -> {c_bat.cycle_count}).",
                    )
                )

    @classmethod
    def _diff_thermals(
        cls,
        base: NormalizedScanPayload,
        curr: NormalizedScanPayload,
        degradations: List[ComponentChange],
    ) -> None:
        b_cpu = base.hardware.cpu
        c_cpu = curr.hardware.cpu

        if b_cpu.temp_c is not None and c_cpu.temp_c is not None:
            temp_delta = round(c_cpu.temp_c - b_cpu.temp_c, 1)
            # Rising idle thermal delta > 10°C is an actionable warning
            if temp_delta >= 10.0:
                degradations.append(
                    ComponentChange(
                        component="Thermal Performance",
                        change_type=ChangeType.DEGRADATION,
                        property_name="cpu_temp_c",
                        old_value=f"{b_cpu.temp_c}°C",
                        new_value=f"{c_cpu.temp_c}°C",
                        description=f"CPU thermal baseline increased by +{temp_delta}°C ({b_cpu.temp_c}°C -> {c_cpu.temp_c}°C). Indicates thermal paste degradation or heatsink fouling.",
                    )
                )
