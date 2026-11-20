"""Typed forecasting contracts only. No fit, feature construction or prediction implementation."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from typing import Protocol

from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.simulation_contracts import snapshot

HORIZON_STEPS = 48
FEATURE_VERSION = "load-origin-v1"
METHODS = ("Seasonal Naive", "Ridge Regression", "LightGBM")


def gmt_half_hour(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be aware fixed GMT/UTC")
    if value.minute not in (0, 30) or value.second or value.microsecond:
        raise ValueError("Timestamp must lie on a half-hour boundary")


@dataclass(frozen=True)
class HistoricalLoadObservation:
    household_id: str
    interval_start: datetime
    interval_end: datetime
    source_timestamp: str
    source_energy: str
    energy_kwh: float | None
    average_power_kw: float | None
    quality: str

    def __post_init__(self) -> None:
        if not self.household_id or self.quality not in {
            "valid",
            "missing",
            "invalid",
            "duplicate",
        }:
            raise ValueError("Require household identity and an LCL quality indicator")
        gmt_half_hour(self.interval_start)
        gmt_half_hour(self.interval_end)
        if self.interval_end - self.interval_start != timedelta(minutes=30):
            raise ValueError("LCL intervals must be exactly 30 minutes")
        if self.quality == "valid":
            if self.energy_kwh is None or self.average_power_kw is None:
                raise ValueError("Valid observations require energy and average power")
            if not isfinite(self.energy_kwh) or self.energy_kwh < 0:
                raise ValueError("Measured energy must be finite and nonnegative")
            if (
                not isfinite(self.average_power_kw)
                or abs(self.average_power_kw - self.energy_kwh * 2) > 1e-9
            ):
                raise ValueError("Average kW must equal original interval kWh / 0.5")
        elif self.energy_kwh is not None or self.average_power_kw is not None:
            raise ValueError("Missing/invalid observations must not carry invented numeric targets")


@dataclass(frozen=True)
class DatePeriod:
    start: date
    end: date  # inclusive dates, defined by interval START

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("Period start must not follow end")

    @property
    def available_through(self) -> datetime:
        return datetime.combine(self.end + timedelta(days=1), datetime.min.time(), UTC)


@dataclass(frozen=True)
class ForecastDatasetConfig:
    training: DatePeriod = DatePeriod(date(2013, 1, 1), date(2013, 2, 28))
    validation: DatePeriod = DatePeriod(date(2013, 3, 1), date(2013, 3, 15))
    testing: DatePeriod = DatePeriod(date(2013, 3, 16), date(2013, 3, 31))
    household_ids: tuple[str, ...] = HOUSEHOLDS
    horizon_steps: int = HORIZON_STEPS
    feature_version: str = FEATURE_VERSION
    missing_policy: str = "exclude_incomplete_origins_and_targets"

    def __post_init__(self) -> None:
        if (
            not self.training.end
            < self.validation.start
            <= self.validation.end
            < self.testing.start
        ):
            raise ValueError("Chronological training/validation/test periods must not overlap")
        if self.horizon_steps != HORIZON_STEPS or self.feature_version != FEATURE_VERSION:
            raise ValueError("Foundation supports 48 half-hours and load-origin-v1 only")
        if not self.household_ids or len(set(self.household_ids)) != len(self.household_ids):
            raise ValueError("Require unique household IDs")
        if self.missing_policy != "exclude_incomplete_origins_and_targets":
            raise ValueError("No implicit imputation policy is supported")


@dataclass(frozen=True)
class ForecastModelConfig:
    method: str = "Seasonal Naive"
    hyperparameters_json: str = "{}"
    horizon_steps: int = HORIZON_STEPS
    feature_version: str = FEATURE_VERSION

    def __post_init__(self) -> None:
        if self.method not in METHODS or self.horizon_steps != HORIZON_STEPS:
            raise ValueError("Unknown forecast method or incompatible horizon")
        if self.feature_version != FEATURE_VERSION:
            raise ValueError("Incompatible feature schema")
        parameters = json.loads(self.hyperparameters_json)
        if not isinstance(parameters, dict):
            raise ValueError("Hyperparameters must be a JSON object")
        allowed = {
            "Seasonal Naive": set(),
            "Ridge Regression": {"alpha"},
            "LightGBM": {
                "num_leaves",
                "learning_rate",
                "n_estimators",
                "max_depth",
                "random_state",
            },
        }[self.method]
        if not set(parameters) <= allowed:
            raise ValueError("Unknown configured hyperparameter")
        for name, value in parameters.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
            ):
                raise ValueError(f"{name} must be finite and numeric")
            if (
                name in {"num_leaves", "n_estimators", "max_depth", "random_state"}
                and type(value) is not int
            ):
                raise ValueError(f"{name} must be an integer")
            if name == "alpha" and value < 0:
                raise ValueError("Ridge alpha must be nonnegative")
            if name == "learning_rate" and not 0 < value <= 1:
                raise ValueError("Learning rate must be in (0, 1]")
            if name == "num_leaves" and value < 2 or name == "n_estimators" and value < 1:
                raise ValueError(f"Invalid {name}")
            if name == "max_depth" and value != -1 and value < 1:
                raise ValueError("Max depth must be -1 or positive")
        object.__setattr__(self, "hyperparameters_json", snapshot(parameters))


@dataclass(frozen=True)
class ForecastMetrics:
    mae_kw: float
    rmse_kw: float

    def __post_init__(self) -> None:
        if not all(isfinite(v) and v >= 0 for v in (self.mae_kw, self.rmse_kw)):
            raise ValueError("MAE/RMSE must be finite nonnegative kW")
        if self.rmse_kw + 1e-12 < self.mae_kw:
            raise ValueError("RMSE cannot be lower than MAE for the same evaluation")


@dataclass(frozen=True)
class ActiveModelReference:
    model_name: str
    model_version: str

    def __post_init__(self) -> None:
        if not self.model_name.strip() or not self.model_version.strip():
            raise ValueError("Active model requires explicit name and version")


@dataclass(frozen=True)
class ForecastModelMetadata:
    reference: ActiveModelReference
    config: ForecastModelConfig
    dataset: ForecastDatasetConfig
    status: str = "Not trained"
    training_data_sha256: str = ""
    fitted_at: datetime | None = None
    information_cutoff: datetime | None = None
    validation_metrics: ForecastMetrics | None = None
    test_metrics: ForecastMetrics | None = None
    artifact_location: str | None = (
        None  # relative to separate artifact directory; no deserialisation
    )

    evaluation_details_json: str = "{}"

    def __post_init__(self) -> None:
        if not isinstance(json.loads(self.evaluation_details_json), dict):
            raise ValueError("Evaluation details must be a JSON object")
        if self.status not in {
            "Not trained",
            "Trained",
            "Evaluated",
            "Saved",
            "Unavailable",
            "Incompatible",
        }:
            raise ValueError(
                "Unknown recorded model status; Active is derived from an explicit reference"
            )
        if (
            self.config.horizon_steps != self.dataset.horizon_steps
            or self.config.feature_version != self.dataset.feature_version
        ):
            raise ValueError("Model and dataset schema/horizon disagree")
        if self.status == "Not trained" and any(
            (
                self.fitted_at,
                self.information_cutoff,
                self.validation_metrics,
                self.test_metrics,
                self.artifact_location,
            )
        ):
            raise ValueError("Not-trained records cannot claim fit/results/artifacts")
        if self.status in {"Trained", "Evaluated", "Saved"}:
            if self.fitted_at is None or self.information_cutoff is None:
                raise ValueError("Trained records require fit time and information cutoff")
            if len(self.training_data_sha256) != 64 or any(
                c not in "0123456789abcdef" for c in self.training_data_sha256
            ):
                raise ValueError("Trained records require a source SHA-256")
            if self.fitted_at.tzinfo is None or self.information_cutoff.tzinfo is None:
                raise ValueError("Model times must be timezone-aware")
            if self.information_cutoff < self.dataset.training.available_through:
                raise ValueError("Information cutoff must cover training observations")
        if self.status in {"Evaluated", "Saved"}:
            if self.validation_metrics is None or self.test_metrics is None:
                raise ValueError("Evaluated/saved records require real validation and test metrics")
            if (
                self.information_cutoff is None
                or self.information_cutoff < self.dataset.testing.available_through
            ):
                raise ValueError("Information cutoff must include evaluation/model-selection data")
        if self.status == "Saved" and not self.artifact_location:
            raise ValueError("Saved records require an artifact location")


@dataclass(frozen=True)
class ForecastRequest:
    household_ids: tuple[str, ...]
    forecast_origin: datetime
    horizon_steps: int = HORIZON_STEPS
    replay_date: date | None = None

    def __post_init__(self) -> None:
        gmt_half_hour(self.forecast_origin)
        if not self.household_ids or len(set(self.household_ids)) != len(self.household_ids):
            raise ValueError("Forecast request needs unique households")
        if self.horizon_steps != HORIZON_STEPS:
            raise ValueError("Initial forecast horizon is fixed at 48 steps")
        if self.replay_date is not None and self.replay_date != self.forecast_origin.date():
            raise ValueError("Replay date must agree with the explicit forecast origin")


def validate_model_for_request(model: ForecastModelMetadata, request: ForecastRequest) -> None:
    if model.status != "Saved":
        raise ValueError("Only saved evaluated models can serve forecasts")
    if not set(request.household_ids) <= set(model.dataset.household_ids):
        raise ValueError("Requested households are incompatible with the model")
    if model.config.horizon_steps != request.horizon_steps:
        raise ValueError("Forecast horizon is incompatible")
    if model.information_cutoff is None or model.information_cutoff > request.forecast_origin:
        raise ValueError("Model used information later than replay forecast origin")


@dataclass(frozen=True)
class ForecastOutput:
    household_id: str
    forecast_origin: datetime
    interval_start: datetime
    interval_end: datetime
    horizon_step: int
    predicted_average_power_kw: float
    model: ActiveModelReference

    def __post_init__(self) -> None:
        for value in (self.forecast_origin, self.interval_start, self.interval_end):
            gmt_half_hour(value)
        if not 1 <= self.horizon_step <= HORIZON_STEPS:
            raise ValueError("Forecast step must be 1–48")
        expected = self.forecast_origin + timedelta(minutes=30 * (self.horizon_step - 1))
        if self.interval_start != expected or self.interval_end != expected + timedelta(minutes=30):
            raise ValueError("Forecast interval does not match origin and horizon step")
        if not isfinite(self.predicted_average_power_kw) or self.predicted_average_power_kw < 0:
            raise ValueError("Predicted demand must be finite nonnegative average kW")


class Forecaster(Protocol):
    def predict(
        self,
        *,
        household_ids: tuple[str, ...],
        forecast_origin: datetime,
        horizon_steps: int = HORIZON_STEPS,
    ) -> tuple[ForecastOutput, ...]: ...


def validate_forecast_batch(
    request: ForecastRequest, outputs: tuple[ForecastOutput, ...], model: ActiveModelReference
) -> None:
    expected = {
        (h, step) for h in request.household_ids for step in range(1, request.horizon_steps + 1)
    }
    actual = {(row.household_id, row.horizon_step) for row in outputs}
    if actual != expected or len(outputs) != len(expected):
        raise ValueError(
            "Forecast batch requires exactly one output per household and horizon step"
        )
    if any(row.forecast_origin != request.forecast_origin or row.model != model for row in outputs):
        raise ValueError("Forecast batch origin/model identity does not match its request")
