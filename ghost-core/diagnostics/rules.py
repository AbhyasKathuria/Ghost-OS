"""Ghost-OS Deterministic Diagnostics & Scoring Engine.

Computes a deterministic health score (0–100) and actionable diagnostic evaluations
based on storage SMART telemetry, battery wear curves, thermal limits, and hardware stability.
"""

from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field

from ghost_core.schemas.scan import (
    DiagnosticResult,
    DiagnosticStatus,
    HardwareSpec,
    NormalizedScanPayload,
)


class HealthScoreBreakdown(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    cpu_score: int = Field(ge=0, le=100)
    ram_score: int = Field(ge=0, le=100)
    storage_score: int = Field(ge=0, le=100)
    battery_score: int = Field(ge=0, le=100)
    thermal_score: int = Field(ge=0, le=100)
    summary: str
    diagnostics: List[DiagnosticResult] = Field(default_factory=list)


class DeterministicRulesEngine:
    """Evaluates hardware against deterministic diagnostic rules and calculates weighted health scores."""

    # Thermal thresholds (°C)
    CPU_TEMP_WARN = 75.0
    CPU_TEMP_CRIT = 90.0
    GPU_TEMP_WARN = 80.0
    GPU_TEMP_CRIT = 92.0
    STORAGE_TEMP_WARN = 60.0
    STORAGE_TEMP_CRIT = 70.0

    # Battery thresholds
    BATTERY_HEALTH_WARN = 80.0
    BATTERY_HEALTH_CRIT = 60.0
    BATTERY_CYCLE_WARN = 800
    BATTERY_CYCLE_CRIT = 1200

    # Storage wear thresholds
    STORAGE_WEAR_WARN = 75.0
    STORAGE_WEAR_CRIT = 90.0

    @classmethod
    def evaluate(cls, payload: NormalizedScanPayload) -> HealthScoreBreakdown:
        hw = payload.hardware
        diagnostics: List[DiagnosticResult] = []

        # 1. CPU & Thermal Evaluation
        cpu_score, cpu_diags = cls._eval_cpu(hw)
        diagnostics.extend(cpu_diags)

        # 2. RAM Evaluation
        ram_score, ram_diags = cls._eval_memory(hw)
        diagnostics.extend(ram_diags)

        # 3. Storage SMART & Wear Evaluation
        storage_score, storage_diags = cls._eval_storage(hw)
        diagnostics.extend(storage_diags)

        # 4. Battery Evaluation
        battery_score, battery_diags = cls._eval_battery(hw)
        diagnostics.extend(battery_diags)

        # 5. Combined Thermal Score
        thermal_score, thermal_diags = cls._eval_thermals(hw)
        diagnostics.extend(thermal_diags)

        # 6. Overall Weighted Score Calculation
        if hw.battery.present:
            # Laptop / Portable device weighting
            # CPU: 20%, RAM: 15%, Storage: 30%, Battery: 15%, Thermals: 20%
            overall = int(
                cpu_score * 0.20
                + ram_score * 0.15
                + storage_score * 0.30
                + battery_score * 0.15
                + thermal_score * 0.20
            )
        else:
            # Desktop / Server weighting (no battery)
            # CPU: 25%, RAM: 20%, Storage: 30%, Thermals: 25%
            overall = int(
                cpu_score * 0.25
                + ram_score * 0.20
                + storage_score * 0.30
                + thermal_score * 0.25
            )

        # Critical Safety Cap: If any diagnostic test failed (e.g. SMART drive failing or CPU overheating),
        # cap overall system health at 65 max.
        has_critical_fail = any(d.status == DiagnosticStatus.FAIL for d in diagnostics)
        if has_critical_fail:
            overall = min(overall, 65)

        overall = max(0, min(100, overall))

        # Generate summary description
        issues = [d for d in diagnostics if d.status in (DiagnosticStatus.WARN, DiagnosticStatus.FAIL)]
        if not issues:
            summary = f"All hardware subsystems passed diagnostic evaluation (Health Score: {overall}/100)."
        else:
            summary = f"Detected {len(issues)} hardware attention item(s). Health Score: {overall}/100."

        return HealthScoreBreakdown(
            overall_score=overall,
            cpu_score=cpu_score,
            ram_score=ram_score,
            storage_score=storage_score,
            battery_score=battery_score,
            thermal_score=thermal_score,
            summary=summary,
            diagnostics=diagnostics,
        )

    @classmethod
    def _eval_cpu(cls, hw: HardwareSpec) -> Tuple[int, List[DiagnosticResult]]:
        score = 100
        diags: List[DiagnosticResult] = []

        if hw.cpu.temp_c is not None:
            if hw.cpu.temp_c >= cls.CPU_TEMP_CRIT:
                score -= 40
                diags.append(
                    DiagnosticResult(
                        test_name="CPU Core Temperature",
                        status=DiagnosticStatus.FAIL,
                        metric_value=hw.cpu.temp_c,
                        threshold=cls.CPU_TEMP_CRIT,
                        evidence=f"CPU temperature reached critical {hw.cpu.temp_c:.1f}°C (Threshold: {cls.CPU_TEMP_CRIT}°C).",
                        recommendation="Check thermal paste application, clean heat sinks, and verify fan operation.",
                    )
                )
            elif hw.cpu.temp_c >= cls.CPU_TEMP_WARN:
                score -= 15
                diags.append(
                    DiagnosticResult(
                        test_name="CPU Core Temperature",
                        status=DiagnosticStatus.WARN,
                        metric_value=hw.cpu.temp_c,
                        threshold=cls.CPU_TEMP_WARN,
                        evidence=f"CPU temperature elevated at {hw.cpu.temp_c:.1f}°C.",
                        recommendation="Monitor under sustained load and inspect airflow.",
                    )
                )
            else:
                diags.append(
                    DiagnosticResult(
                        test_name="CPU Core Temperature",
                        status=DiagnosticStatus.PASS,
                        metric_value=hw.cpu.temp_c,
                        threshold=cls.CPU_TEMP_WARN,
                        evidence=f"CPU temperature nominal at {hw.cpu.temp_c:.1f}°C.",
                        recommendation="None",
                    )
                )
        return max(0, score), diags

    @classmethod
    def _eval_memory(cls, hw: HardwareSpec) -> Tuple[int, List[DiagnosticResult]]:
        score = 100
        diags: List[DiagnosticResult] = []

        # Check total capacity
        total_gb = hw.memory.total_bytes / (1024**3)
        if total_gb < 3.8:
            score -= 25
            diags.append(
                DiagnosticResult(
                    test_name="RAM Capacity",
                    status=DiagnosticStatus.WARN,
                    metric_value=total_gb,
                    threshold=4.0,
                    evidence=f"Total system memory is low: {total_gb:.1f} GB.",
                    recommendation="Upgrade to at least 8 GB or 16 GB for modern workloads.",
                )
            )
        else:
            diags.append(
                DiagnosticResult(
                    test_name="RAM Capacity",
                    status=DiagnosticStatus.PASS,
                    metric_value=total_gb,
                    threshold=4.0,
                    evidence=f"Sufficient memory detected: {total_gb:.1f} GB across {hw.memory.slots_used} slot(s).",
                    recommendation="None",
                )
            )

        # Check channel symmetry
        if len(hw.memory.modules) >= 2:
            capacities = [m.capacity_bytes for m in hw.memory.modules]
            speeds = [m.speed_mhz for m in hw.memory.modules if m.speed_mhz]
            if len(set(capacities)) > 1 or (speeds and len(set(speeds)) > 1):
                score -= 5
                diags.append(
                    DiagnosticResult(
                        test_name="RAM Module Symmetry",
                        status=DiagnosticStatus.WARN,
                        metric_value=float(len(capacities)),
                        threshold=0.0,
                        evidence="Asymmetric memory modules detected (mismatched size or speed). Multi-channel performance may be suboptimal.",
                        recommendation="Use matched pairs of identical capacity and frequency for optimal dual-channel bandwidth.",
                    )
                )

        return max(0, score), diags

    @classmethod
    def _eval_storage(cls, hw: HardwareSpec) -> Tuple[int, List[DiagnosticResult]]:
        score = 100
        diags: List[DiagnosticResult] = []

        if not hw.storage:
            return 80, [
                DiagnosticResult(
                    test_name="Storage Inventory",
                    status=DiagnosticStatus.WARN,
                    evidence="No physical storage drives detected.",
                    recommendation="Ensure storage controller drivers are loaded.",
                )
            ]

        for dev in hw.storage:
            smart_up = (dev.smart_status or "UNKNOWN").upper()
            if smart_up in ("FAILED", "FAIL", "BAD"):
                score -= 50
                diags.append(
                    DiagnosticResult(
                        test_name=f"SMART Health [{dev.model}]",
                        status=DiagnosticStatus.FAIL,
                        evidence=f"Storage drive {dev.model} ({dev.device_id}) reported failing SMART health.",
                        recommendation="BACKUP DATA IMMEDIATELY. Replace storage drive without delay.",
                    )
                )
            elif smart_up in ("WARNING", "WARN"):
                score -= 20
                diags.append(
                    DiagnosticResult(
                        test_name=f"SMART Health [{dev.model}]",
                        status=DiagnosticStatus.WARN,
                        evidence=f"Storage drive {dev.model} reported SMART warning flags.",
                        recommendation="Monitor drive for bad sectors or pending reallocation counts.",
                    )
                )
            else:
                diags.append(
                    DiagnosticResult(
                        test_name=f"SMART Health [{dev.model}]",
                        status=DiagnosticStatus.PASS,
                        evidence=f"Drive {dev.model} SMART status is healthy ({smart_up}).",
                        recommendation="None",
                    )
                )

            # Check SSD wear level
            if dev.wear_level_pct is not None:
                if dev.wear_level_pct >= cls.STORAGE_WEAR_CRIT:
                    score -= 30
                    diags.append(
                        DiagnosticResult(
                            test_name=f"SSD Endurance Wear [{dev.model}]",
                            status=DiagnosticStatus.FAIL,
                            metric_value=dev.wear_level_pct,
                            threshold=cls.STORAGE_WEAR_CRIT,
                            evidence=f"Flash wear reached critical {dev.wear_level_pct:.1f}% consumed.",
                            recommendation="SSD has reached end of rated endurance write cycles. Plan replacement.",
                        )
                    )
                elif dev.wear_level_pct >= cls.STORAGE_WEAR_WARN:
                    score -= 10
                    diags.append(
                        DiagnosticResult(
                            test_name=f"SSD Endurance Wear [{dev.model}]",
                            status=DiagnosticStatus.WARN,
                            metric_value=dev.wear_level_pct,
                            threshold=cls.STORAGE_WEAR_WARN,
                            evidence=f"Flash wear elevated at {dev.wear_level_pct:.1f}%.",
                            recommendation="Review write intensive workloads and monitor drive health.",
                        )
                    )

            # Check storage temperature
            if dev.temp_c is not None:
                if dev.temp_c >= cls.STORAGE_TEMP_CRIT:
                    score -= 20
                    diags.append(
                        DiagnosticResult(
                            test_name=f"Storage Temperature [{dev.model}]",
                            status=DiagnosticStatus.FAIL,
                            metric_value=dev.temp_c,
                            threshold=cls.STORAGE_TEMP_CRIT,
                            evidence=f"NVMe/SSD temperature critical at {dev.temp_c:.1f}°C.",
                            recommendation="Ensure heatsink or thermal pad is properly seated on the drive.",
                        )
                    )
                elif dev.temp_c >= cls.STORAGE_TEMP_WARN:
                    score -= 5
                    diags.append(
                        DiagnosticResult(
                            test_name=f"Storage Temperature [{dev.model}]",
                            status=DiagnosticStatus.WARN,
                            metric_value=dev.temp_c,
                            threshold=cls.STORAGE_TEMP_WARN,
                            evidence=f"Drive temperature elevated at {dev.temp_c:.1f}°C.",
                            recommendation="Improve chassis ventilation.",
                        )
                    )

        return max(0, score), diags

    @classmethod
    def _eval_battery(cls, hw: HardwareSpec) -> Tuple[int, List[DiagnosticResult]]:
        if not hw.battery.present:
            return 100, []

        score = 100
        diags: List[DiagnosticResult] = []
        bat = hw.battery

        # Compute or use health_pct
        health = bat.health_pct
        if health is None and bat.design_capacity_mwh and bat.full_charge_capacity_mwh and bat.design_capacity_mwh > 0:
            health = round((bat.full_charge_capacity_mwh / bat.design_capacity_mwh) * 100, 1)

        if health is not None:
            if health < cls.BATTERY_HEALTH_CRIT:
                score -= 40
                diags.append(
                    DiagnosticResult(
                        test_name="Battery Capacity Degradation",
                        status=DiagnosticStatus.FAIL,
                        metric_value=health,
                        threshold=cls.BATTERY_HEALTH_CRIT,
                        evidence=f"Battery capacity severely degraded to {health:.1f}% of design capacity.",
                        recommendation="Battery replacement is recommended to prevent premature shutdowns or cell swelling.",
                    )
                )
            elif health < cls.BATTERY_HEALTH_WARN:
                score -= 15
                diags.append(
                    DiagnosticResult(
                        test_name="Battery Capacity Degradation",
                        status=DiagnosticStatus.WARN,
                        metric_value=health,
                        threshold=cls.BATTERY_HEALTH_WARN,
                        evidence=f"Battery health is moderately degraded at {health:.1f}%.",
                        recommendation="Battery holds reduced charge. Consider replacement if runtime is insufficient.",
                    )
                )
            else:
                diags.append(
                    DiagnosticResult(
                        test_name="Battery Capacity Health",
                        status=DiagnosticStatus.PASS,
                        metric_value=health,
                        threshold=cls.BATTERY_HEALTH_WARN,
                        evidence=f"Battery health is good ({health:.1f}% remaining capacity).",
                        recommendation="None",
                    )
                )

        # Check cycle count
        if bat.cycle_count is not None:
            if bat.cycle_count >= cls.BATTERY_CYCLE_CRIT:
                score -= 20
                diags.append(
                    DiagnosticResult(
                        test_name="Battery Cycle Life",
                        status=DiagnosticStatus.FAIL,
                        metric_value=float(bat.cycle_count),
                        threshold=float(cls.BATTERY_CYCLE_CRIT),
                        evidence=f"Battery cycle count exceeded rated lifespan: {bat.cycle_count} cycles.",
                        recommendation="Cell impedance has increased significantly. Replace battery.",
                    )
                )
            elif bat.cycle_count >= cls.BATTERY_CYCLE_WARN:
                score -= 10
                diags.append(
                    DiagnosticResult(
                        test_name="Battery Cycle Life",
                        status=DiagnosticStatus.WARN,
                        metric_value=float(bat.cycle_count),
                        threshold=float(cls.BATTERY_CYCLE_WARN),
                        evidence=f"High battery cycle count: {bat.cycle_count} cycles.",
                        recommendation="Monitor battery run time under workload.",
                    )
                )

        return max(0, score), diags

    @classmethod
    def _eval_thermals(cls, hw: HardwareSpec) -> Tuple[int, List[DiagnosticResult]]:
        score = 100
        diags: List[DiagnosticResult] = []

        # GPU thermals
        for gpu in hw.gpu:
            if gpu.temp_c is not None:
                if gpu.temp_c >= cls.GPU_TEMP_CRIT:
                    score -= 35
                    diags.append(
                        DiagnosticResult(
                            test_name=f"GPU Temperature [{gpu.name}]",
                            status=DiagnosticStatus.FAIL,
                            metric_value=gpu.temp_c,
                            threshold=cls.GPU_TEMP_CRIT,
                            evidence=f"GPU {gpu.name} reached critical thermal threshold: {gpu.temp_c:.1f}°C.",
                            recommendation="Check GPU cooler mounting, fan speed curve, and case airflow.",
                        )
                    )
                elif gpu.temp_c >= cls.GPU_TEMP_WARN:
                    score -= 10
                    diags.append(
                        DiagnosticResult(
                            test_name=f"GPU Temperature [{gpu.name}]",
                            status=DiagnosticStatus.WARN,
                            metric_value=gpu.temp_c,
                            threshold=cls.GPU_TEMP_WARN,
                            evidence=f"GPU {gpu.name} thermal level is elevated: {gpu.temp_c:.1f}°C.",
                            recommendation="Verify fan curve and check for dust accumulation.",
                        )
                    )

        return max(0, score), diags
