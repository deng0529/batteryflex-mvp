"""Future result-persistence contracts only; no engine, evaluation or storage adapter."""

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

Strategy = Literal["Rule-based", "MILP", "Rolling MPC"]


def snapshot(value: object) -> str:
    """Immutable canonical JSON, independent of caller dictionary ordering or later mutation."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class ExperimentInputs:
    """All equivalent-input fields; canonical JSON snapshots preserve configuration versions."""

    event_id: str  # Existing internal scenario ID; not a fabricated official NESO ID.
    battery_configuration_json: str
    initial_soc_json: str
    export_settings_json: str
    portfolio_commitment_kw: float
    forecast_assumptions_json: str
    input_data_references_json: str

    def __post_init__(self) -> None:
        for field in fields(self):
            if field.name.endswith("_json"):
                object.__setattr__(
                    self, field.name, snapshot(json.loads(getattr(self, field.name)))
                )

    @property
    def experiment_id(self) -> str:
        return "BF-EXPERIMENT-" + hashlib.sha256(snapshot(self.__dict__).encode()).hexdigest()


@dataclass(frozen=True)
class EvaluationMetrics:
    commitment_fulfilment_pct: float
    delivery_shortfall_kwh: float
    electricity_cost_gbp: float
    battery_energy_throughput_kwh: float
    final_soc_by_household_json: str
    computation_time_seconds: float


@dataclass(frozen=True)
class SimulationRun:
    """Future successful run with delivery, grid, SOC and dispatch result snapshots."""

    run_id: str
    completed_at_utc: str
    inputs: ExperimentInputs
    strategy: Strategy
    results_json: str
    metrics: EvaluationMetrics

    @classmethod
    def completed(
        cls,
        inputs: ExperimentInputs,
        strategy: Strategy,
        results: object,
        metrics: EvaluationMetrics,
    ) -> "SimulationRun":
        return cls(
            str(uuid4()),
            datetime.now(UTC).isoformat(),
            inputs,
            strategy,
            snapshot(results),
            metrics,
        )


def append_run(runs: tuple[SimulationRun, ...], run: SimulationRun) -> tuple[SimulationRun, ...]:
    """Append, never upsert by strategy. Durable storage must enforce run_id uniqueness too."""
    if any(existing.run_id == run.run_id for existing in runs):
        raise ValueError("Duplicate run ID; existing results cannot be overwritten")
    return (*runs, run)


def compatible_runs(
    runs: tuple[SimulationRun, ...], inputs: ExperimentInputs
) -> tuple[SimulationRun, ...]:
    return tuple(run for run in runs if run.inputs.experiment_id == inputs.experiment_id)


def clear_experiment(
    runs: tuple[SimulationRun, ...], experiment_id: str
) -> tuple[SimulationRun, ...]:
    """Pure future action: clear only the explicitly selected experiment."""
    return tuple(run for run in runs if run.inputs.experiment_id != experiment_id)
