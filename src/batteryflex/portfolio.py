"""Independent simulated assets, battery-only commitments and immutable input snapshots."""

import json
from dataclasses import asdict, dataclass, replace

from batteryflex.battery import BatteryConfig, availability, finite
from batteryflex.defaults import portfolio_defaults

HOUSEHOLDS = tuple(b.household_id for b in portfolio_defaults().batteries)
INITIAL_SOC = tuple(b.initial_soc for b in portfolio_defaults().batteries)


@dataclass(frozen=True)
class Portfolio:
    batteries: tuple[BatteryConfig, ...]

    def __post_init__(self) -> None:
        ids = [b.household_id for b in self.batteries]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Portfolio must contain unique household IDs")

    def update(self, battery: BatteryConfig) -> "Portfolio":
        if battery.household_id not in {b.household_id for b in self.batteries}:
            raise ValueError("Unknown household")
        return Portfolio(
            tuple(battery if b.household_id == battery.household_id else b for b in self.batteries)
        )

    def apply_to_all(
        self, source: BatteryConfig, *, copy_soc: bool = False, copy_participation: bool = False
    ) -> "Portfolio":
        """Atomic validation: fail without modifying any asset if preserved SOC is invalid."""
        return Portfolio(
            tuple(
                replace(
                    source,
                    household_id=b.household_id,
                    initial_soc=source.initial_soc if copy_soc else b.initial_soc,
                    participating=source.participating if copy_participation else b.participating,
                )
                for b in self.batteries
            )
        )

    def select(self, household_ids: list[str]) -> "Portfolio":
        if not set(household_ids) <= {b.household_id for b in self.batteries}:
            raise ValueError("Unknown participating household")
        return Portfolio(
            tuple(replace(b, participating=b.household_id in household_ids) for b in self.batteries)
        )


def default_portfolio() -> Portfolio:
    """Fresh defaults; these initial states are research assumptions, not LCL measurements."""
    return Portfolio(portfolio_defaults().batteries)


@dataclass(frozen=True)
class PortfolioCapability:
    participating: int
    installed_capacity_kwh: float  # includes excluded configured assets
    participating_capacity_kwh: float
    usable_kwh: float
    deliverable_kwh: float
    instantaneous_rating_kw: float
    constant_discharge_kw: float
    contributions_kw: tuple[tuple[str, float], ...]


def capability(portfolio: Portfolio, duration_hours: float) -> PortfolioCapability:
    finite(duration_hours, "Duration", positive=True)
    active = [b for b in portfolio.batteries if b.participating]
    values = [availability(b, duration_hours) for b in active]
    return PortfolioCapability(
        len(active),
        sum(b.capacity_kwh for b in portfolio.batteries),
        sum(b.capacity_kwh for b in active),
        sum(v.usable_kwh for v in values),
        sum(v.deliverable_kwh for v in values),
        sum(v.instantaneous_rating_kw for v in values),
        sum(v.constant_discharge_kw for v in values),
        tuple(
            (
                b.household_id,
                availability(b, duration_hours).constant_discharge_kw if b.participating else 0.0,
            )
            for b in portfolio.batteries
        ),
    )


@dataclass(frozen=True)
class CommitmentAssessment:
    commitment_kw: float
    capability_kw: float
    margin_kw: float
    feasible: bool

    @property
    def shortfall_kw(self) -> float:
        return max(0.0, -self.margin_kw)


def assess_commitment(
    portfolio: Portfolio, duration_hours: float, commitment_kw: float
) -> CommitmentAssessment:
    finite(commitment_kw, "Local commitment")
    power = capability(portfolio, duration_hours).constant_discharge_kw
    margin = power - commitment_kw
    return CommitmentAssessment(commitment_kw, power, margin, margin >= 0)


@dataclass(frozen=True)
class CommitmentExplanation:
    assessment: CommitmentAssessment
    capability: PortfolioCapability
    required_energy_kwh: float
    shortfall_energy_kwh: float
    energy_only_power_kw: float
    limiting_cause: str
    energy_limited_households: tuple[str, ...]
    power_limited_households: tuple[str, ...]


def explain_commitment(
    portfolio: Portfolio, duration_hours: float, commitment_kw: float
) -> CommitmentExplanation:
    """Explain independent per-asset limits, not just aggregate energy sufficiency.

    Energy-only power ignores ratings; nameplate power ignores energy. Neither is
    the actual capability, which is the sum of each asset's minimum. A combination
    can therefore fail even when both independent aggregate ceilings exceed a request.
    """
    assessment = assess_commitment(portfolio, duration_hours, commitment_kw)
    totals = capability(portfolio, duration_hours)
    energy_only = totals.deliverable_kwh / duration_hours
    energy_limited, power_limited = [], []
    for battery in portfolio.batteries:
        if not battery.participating:
            continue
        value = availability(battery, duration_hours)
        energy_power = value.deliverable_kwh / duration_hours
        if energy_power < battery.discharge_limit_kw:
            energy_limited.append(battery.household_id)
        elif battery.discharge_limit_kw < energy_power:
            power_limited.append(battery.household_id)
    if assessment.feasible:
        cause = "none"
    elif not totals.participating:
        cause = "no_participants"
    else:
        energy_contributes = bool(energy_limited) or energy_only < commitment_kw
        power_contributes = bool(power_limited) or totals.instantaneous_rating_kw < commitment_kw
        cause = (
            "combined"
            if energy_contributes and power_contributes
            else "energy"
            if energy_contributes
            else "power"
        )
    return CommitmentExplanation(
        assessment,
        totals,
        commitment_kw * duration_hours,
        assessment.shortfall_kw * duration_hours,
        energy_only,
        cause,
        tuple(energy_limited),
        tuple(power_limited),
    )


def event_capabilities(portfolio: Portfolio, events: list[dict]) -> list[dict]:
    """Reuse reviewed durations, never derive local commitments from national MW."""
    rows = []
    for event in events:
        duration = event["duration_minutes"] / 60
        value = capability(portfolio, duration)
        rows.append(
            {
                "Event date": str(event["delivery_date"]),
                "Duration (h)": duration,
                "Participating households": value.participating,
                "Usable energy (kWh)": value.usable_kwh,
                "Deliverable energy (kWh)": value.deliverable_kwh,
                "Constant discharge (kW)": value.constant_discharge_kw,
            }
        )
    return rows


@dataclass(frozen=True)
class BatteryScenarioSnapshot:
    """Future Simulation Lab input; no dispatch or artificial results."""

    portfolio_json: str
    event_id: str | None
    commitment_kw: float


def scenario_snapshot(
    portfolio: Portfolio, event_id: str | None, commitment_kw: float
) -> BatteryScenarioSnapshot:
    finite(commitment_kw, "Local commitment")
    return BatteryScenarioSnapshot(
        json.dumps([asdict(b) for b in portfolio.batteries], sort_keys=True, allow_nan=False),
        event_id,
        commitment_kw,
    )
