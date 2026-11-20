"""Future one-click simulation inputs and orchestration contract; no pipeline implementation."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Protocol

from batteryflex.battery import finite
from batteryflex.forecast_contracts import ActiveModelReference, ForecastRequest, gmt_half_hour
from batteryflex.portfolio import Portfolio
from batteryflex.simulation_contracts import ExperimentInputs, SimulationRun, Strategy, snapshot


@dataclass(frozen=True)
class SimulationPlan:
    event_id: str
    original_event_start: datetime
    replay_date: date
    forecast_origin: datetime
    portfolio: Portfolio  # must be the saved active snapshot supplied by the caller
    commitment_kw: float
    forecast_model: ActiveModelReference | None
    demand_scenario: str = "historical-synthetic-replay-v1"
    tariff_assumptions: str = "Unconfigured"
    baseline_assumptions: str = "Unconfigured"
    source_reference: str = ""

    def __post_init__(self) -> None:
        gmt_half_hour(self.original_event_start)
        gmt_half_hour(self.forecast_origin)
        finite(self.commitment_kw, "Local commitment")
        if not self.event_id or self.replay_date != self.forecast_origin.date():
            raise ValueError(
                "Require event identity and an explicit same-day replay forecast origin"
            )

    def forecast_request(self) -> ForecastRequest:
        return ForecastRequest(
            tuple(b.household_id for b in self.portfolio.batteries if b.participating),
            self.forecast_origin,
            replay_date=self.replay_date,
        )

    def experiment_inputs(self) -> ExperimentInputs:
        """Include replay/model/demand/tariff/baseline metadata in existing compatibility keys."""
        return ExperimentInputs(
            self.event_id,
            snapshot([asdict(b) for b in self.portfolio.batteries]),
            snapshot({b.household_id: b.initial_soc for b in self.portfolio.batteries}),
            snapshot(
                {
                    b.household_id: {"enabled": b.export_enabled, "limit_kw": b.export_limit_kw}
                    for b in self.portfolio.batteries
                }
            ),
            self.commitment_kw,
            snapshot(
                {
                    "model": asdict(self.forecast_model) if self.forecast_model else None,
                    "origin": self.forecast_origin.isoformat(),
                    "horizon_steps": 48,
                    "demand_scenario": self.demand_scenario,
                    "tariff": self.tariff_assumptions,
                    "baseline": self.baseline_assumptions,
                }
            ),
            snapshot(
                {
                    "original_event_start": self.original_event_start.isoformat(),
                    "replay_date": self.replay_date.isoformat(),
                    "source": self.source_reference,
                    "mapping": "v1-same-month-weekday-nearest-day",
                }
            ),
        )


class SimulationPipeline(Protocol):
    def execute(self, plan: SimulationPlan, strategy: Strategy) -> SimulationRun: ...
