"""Simulated battery physics. Power: kW; energy: kWh; time: hours; SOC: fraction.

AC-side charge/discharge powers are nonnegative; positive grid power is import.
Requests fail explicitly rather than being clipped. No measured battery data is implied.
"""

from dataclasses import dataclass
from math import isfinite, sqrt


def finite(value: float, name: str, *, minimum: float = 0.0, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not isfinite(value) or value < minimum or (positive and value == minimum):
        raise ValueError(f"{name} must be finite and {'>' if positive else '>='} {minimum}")


@dataclass(frozen=True)
class BatteryConfig:
    household_id: str
    capacity_kwh: float = 10.0
    charge_limit_kw: float = 5.0
    discharge_limit_kw: float = 5.0
    min_soc: float = 0.2
    max_soc: float = 1.0
    initial_soc: float = 0.8
    charge_efficiency: float = sqrt(0.9)
    discharge_efficiency: float = sqrt(0.9)
    export_enabled: bool = True
    export_limit_kw: float | None = None
    participating: bool = True
    interval_hours: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.household_id, str) or not self.household_id.strip():
            raise ValueError("Household ID must be nonempty")
        finite(self.capacity_kwh, "Capacity", positive=True)
        finite(self.interval_hours, "Interval", positive=True)
        for name in ("charge_limit_kw", "discharge_limit_kw"):
            finite(getattr(self, name), name)
        for name in ("min_soc", "max_soc", "initial_soc"):
            finite(getattr(self, name), name)
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not self.min_soc <= self.initial_soc <= self.max_soc:
            raise ValueError("Require minimum SOC <= initial SOC <= maximum SOC")
        for name in ("charge_efficiency", "discharge_efficiency"):
            finite(getattr(self, name), name, positive=True)
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if self.export_limit_kw is not None:
            finite(self.export_limit_kw, "Export limit")
        if type(self.export_enabled) is not bool or type(self.participating) is not bool:
            raise ValueError("Export permission and participation must be booleans")

    @property
    def round_trip_efficiency(self) -> float:
        return self.charge_efficiency * self.discharge_efficiency


@dataclass(frozen=True)
class BatteryState:
    energy_kwh: float

    def __post_init__(self) -> None:
        finite(self.energy_kwh, "Stored energy")

    def soc(self, config: BatteryConfig) -> float:
        validate_state(config, self)
        return self.energy_kwh / config.capacity_kwh


@dataclass(frozen=True)
class BatteryAction:
    charge_kw: float = 0.0
    discharge_kw: float = 0.0

    def __post_init__(self) -> None:
        finite(self.charge_kw, "Charge power")
        finite(self.discharge_kw, "Discharge power")
        if self.charge_kw > 0 and self.discharge_kw > 0:
            raise ValueError("Simultaneous charging and discharging is forbidden")


def initial_state(config: BatteryConfig) -> BatteryState:
    return BatteryState(config.initial_soc * config.capacity_kwh)


def validate_state(config: BatteryConfig, state: BatteryState) -> None:
    if not (
        config.min_soc * config.capacity_kwh - 1e-10
        <= state.energy_kwh
        <= config.max_soc * config.capacity_kwh + 1e-10
    ):
        raise ValueError("Stored energy violates SOC bounds")


def grid_power(config: BatteryConfig, action: BatteryAction, load_kw: float) -> float:
    """Net household exchange; export cap limits net export, not discharge rating."""
    finite(load_kw, "Household load")
    if action.charge_kw > config.charge_limit_kw or action.discharge_kw > config.discharge_limit_kw:
        raise ValueError("Action exceeds battery power rating")
    power = load_kw + action.charge_kw - action.discharge_kw
    limit = config.export_limit_kw if config.export_enabled else 0.0
    if limit is not None and power < -limit - 1e-10:
        raise ValueError("Action violates household grid export permission/limit")
    return power


def transition(
    config: BatteryConfig,
    state: BatteryState,
    action: BatteryAction,
    *,
    load_kw: float,
    duration_hours: float | None = None,
) -> BatteryState:
    """Validate power, grid exchange and both energy states; never clip an action."""
    duration = config.interval_hours if duration_hours is None else duration_hours
    finite(duration, "Duration", positive=True)
    validate_state(config, state)
    grid_power(config, action, load_kw)
    energy = (
        state.energy_kwh
        + config.charge_efficiency * action.charge_kw * duration
        - action.discharge_kw * duration / config.discharge_efficiency
    )
    # Validate before constructing so a negative energy also gives a physical-state error.
    if energy < -1e-10:
        raise ValueError("Stored energy violates SOC bounds")
    result = BatteryState(max(0.0, energy))  # numerical round-off only, never control clipping
    validate_state(config, result)
    return result


@dataclass(frozen=True)
class Availability:
    stored_kwh: float
    usable_kwh: float
    deliverable_kwh: float
    instantaneous_rating_kw: float
    constant_discharge_kw: float


def availability(
    config: BatteryConfig, duration_hours: float, state: BatteryState | None = None
) -> Availability:
    """Battery-only limit: no recharge; no household/grid restriction or participation filter.

    The instantaneous rating is a nameplate limit, not sustainable energy availability.
    """
    finite(duration_hours, "Duration", positive=True)
    current = initial_state(config) if state is None else state
    validate_state(config, current)
    usable = max(0.0, current.energy_kwh - config.min_soc * config.capacity_kwh)
    deliverable = usable * config.discharge_efficiency
    return Availability(
        current.energy_kwh,
        usable,
        deliverable,
        config.discharge_limit_kw,
        min(config.discharge_limit_kw, deliverable / duration_hours),
    )


def final_soc(config: BatteryConfig, discharge_kw: float, duration_hours: float) -> float:
    """Expected SOC for feasible battery-only constant discharge, ignoring grid restrictions."""
    finite(discharge_kw, "Discharge power")
    available = availability(config, duration_hours)
    if discharge_kw > available.constant_discharge_kw + 1e-10:
        raise ValueError("Constant discharge exceeds sustainable battery capability")
    return config.initial_soc - discharge_kw * duration_hours / (
        config.discharge_efficiency * config.capacity_kwh
    )
