"""Battery energy/SOC performance to its boundary, independent of household operation."""

from dataclasses import dataclass, replace
from math import ceil, isfinite

from batteryflex.battery import (
    BatteryAction,
    BatteryConfig,
    BatteryState,
    finite,
    initial_state,
    transition,
)

INTERVAL_HOURS = 0.5
MAX_CURVE_STEPS = 100_000


@dataclass(frozen=True)
class PerformanceInterval:
    elapsed_hours: float
    duration_hours: float
    energy_kwh: float
    soc: float
    charge_kw: float
    discharge_kw: float


@dataclass(frozen=True)
class BatteryPerformance:
    initial_soc: float
    initial_energy_kwh: float
    operating_power_kw: float
    completion_hours: float
    intervals: tuple[PerformanceInterval, ...]

    @property
    def final_soc(self) -> float:
        return self.intervals[-1].soc if self.intervals else self.initial_soc

    @property
    def electrical_energy_kwh(self) -> float:
        """AC energy drawn in charge mode or delivered in discharge mode."""
        return sum((i.charge_kw + i.discharge_kw) * i.duration_hours for i in self.intervals)


def demonstrate(config: BatteryConfig, mode: str, operating_power_kw: float) -> BatteryPerformance:
    """Integrate strict Task 04 transitions, with a shorter exact final interval.

    Constant power must be positive and within its rating. There is no clipping,
    arbitrary user duration, idle mode or household/export restriction assessment.
    """
    finite(operating_power_kw, "Operating power", positive=True)
    if mode not in ("Charge", "Discharge"):
        raise ValueError("Operation must be Charge or Discharge")
    rating = config.charge_limit_kw if mode == "Charge" else config.discharge_limit_kw
    if operating_power_kw > rating:
        raise ValueError("Operating power exceeds the selected battery's physical rating")
    if mode == "Charge":
        hours = (
            (config.max_soc - config.initial_soc)
            * config.capacity_kwh
            / (config.charge_efficiency * operating_power_kw)
        )
        action = BatteryAction(charge_kw=operating_power_kw)
    else:
        hours = (
            (config.initial_soc - config.min_soc)
            * config.capacity_kwh
            * (config.discharge_efficiency / operating_power_kw)
        )
        action = BatteryAction(discharge_kw=operating_power_kw)
    if not isfinite(hours) or hours / INTERVAL_HOURS > MAX_CURVE_STEPS:
        raise ValueError(
            "Performance curve exceeds 100,000 half-hour steps; increase operating power."
        )
    physics = replace(
        config, export_enabled=True, export_limit_kw=None, interval_hours=INTERVAL_HOURS
    )
    state = initial_state(physics)
    initial_energy = state.energy_kwh
    rows = []
    # Zero remaining energy produces no transitions and an initial-only chart.
    steps = ceil(hours / INTERVAL_HOURS)
    for step in range(steps):
        start = step * INTERVAL_HOURS
        end = min((step + 1) * INTERVAL_HOURS, hours)
        duration = end - start
        state = transition(physics, state, action, load_kw=0, duration_hours=duration)
        if step == steps - 1:
            target = (config.max_soc if mode == "Charge" else config.min_soc) * config.capacity_kwh
            if abs(state.energy_kwh - target) > 1e-9:
                raise ValueError("Boundary integration error exceeds floating-point tolerance")
            state = BatteryState(target)  # normalize final floating-point round-off only
        rows.append(
            PerformanceInterval(
                end,
                duration,
                state.energy_kwh,
                state.soc(physics),
                action.charge_kw,
                action.discharge_kw,
            )
        )
    return BatteryPerformance(
        config.initial_soc, initial_energy, operating_power_kw, hours, tuple(rows)
    )
