"""No fitted models or predictions are produced; records are explicitly synthetic fixtures."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from batteryflex.forecast_contracts import (
    ActiveModelReference,
    DatePeriod,
    ForecastDatasetConfig,
    ForecastMetrics,
    ForecastModelConfig,
    ForecastModelMetadata,
    ForecastOutput,
    ForecastRequest,
    HistoricalLoadObservation,
    validate_forecast_batch,
    validate_model_for_request,
)
from batteryflex.forecast_registry import LocalModelRegistry, ModelRegistry
from batteryflex.forecast_simulation import SimulationPlan
from batteryflex.portfolio import HOUSEHOLDS, default_portfolio


def model():
    return ForecastModelMetadata(
        ActiveModelReference("fixture", "v1"),
        ForecastModelConfig(),
        ForecastDatasetConfig(),
        "Saved",
        "a" * 64,
        datetime(2013, 4, 2, tzinfo=UTC),
        datetime(2013, 4, 1, tzinfo=UTC),
        ForecastMetrics(0.1, 0.2),
        ForecastMetrics(0.2, 0.3),
        "fixture/v1/model.txt",
    )


def test_historical_observation_units_quality_and_gmt():
    row = HistoricalLoadObservation(
        HOUSEHOLDS[0],
        datetime(2013, 1, 1, tzinfo=UTC),
        datetime(2013, 1, 1, 0, 30, tzinfo=UTC),
        "original",
        "0.5",
        0.5,
        1,
        "valid",
    )
    assert row.average_power_kw == row.energy_kwh * 2
    with pytest.raises(ValueError):
        replace(row, average_power_kw=0.5)
    with pytest.raises(ValueError):
        replace(row, interval_start=row.interval_start.replace(tzinfo=None))
    with pytest.raises(ValueError):
        replace(row, quality="missing")
    assert (
        replace(row, quality="missing", energy_kwh=None, average_power_kw=None).energy_kwh is None
    )


def test_chronological_split_validation():
    cfg = ForecastDatasetConfig()
    assert cfg.training.end == date(2013, 2, 28)
    assert cfg.validation.start == date(2013, 3, 1) and cfg.testing.end == date(2013, 3, 31)
    with pytest.raises(ValueError):
        replace(cfg, validation=DatePeriod(date(2013, 2, 28), date(2013, 3, 15)))
    with pytest.raises(ValueError):
        DatePeriod(date(2013, 2, 1), date(2013, 1, 1))
    with pytest.raises(ValueError):
        replace(cfg, horizon_steps=24)


@pytest.mark.parametrize(
    "method,parameters",
    [
        ("unknown", "{}"),
        ("Seasonal Naive", '{"alpha":1}'),
        ("Ridge Regression", '{"alpha":-1}'),
        ("Ridge Regression", '{"alpha":NaN}'),
        ("LightGBM", '{"num_leaves":1}'),
        ("LightGBM", '{"n_estimators":1.5}'),
        ("LightGBM", '{"learning_rate":0}'),
        ("LightGBM", '{"max_depth":0}'),
    ],
)
def test_bad_model_configuration(method, parameters):
    with pytest.raises(ValueError):
        ForecastModelConfig(method, parameters)


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "Active"},
        {"artifact_location": None},
        {"validation_metrics": None},
        {"test_metrics": None},
        {"training_data_sha256": "wrong"},
        {"fitted_at": None},
        {"information_cutoff": datetime(2013, 1, 1, tzinfo=UTC)},
    ],
)
def test_metadata_cannot_claim_unsupported_lifecycle_state(changes):
    with pytest.raises(ValueError):
        replace(model(), **changes)
    with pytest.raises(ValueError):
        replace(model(), status="Not trained")


def test_registry_roundtrip_active_reference_missing_artifact_and_owner_writes(tmp_path):
    store = LocalModelRegistry(tmp_path / "models")
    assert store.read() == ModelRegistry() and not store.root.exists()
    record = model()
    registry = ModelRegistry().add(record)
    with pytest.raises(ValueError):
        registry.add(record)
    with pytest.raises(PermissionError):
        store.write(registry)
    assert not store.root.exists()
    with pytest.raises(ValueError, match="missing"):
        store.activate(registry, record.reference)
    path = store.artifact_path(record.artifact_location)
    path.parent.mkdir(parents=True)
    path.write_text("fixture marker only; never deserialized")
    registry = store.activate(registry, record.reference)
    store.write(registry, owner_authorized=True)
    assert store.read() == registry
    assert store.active_model(registry)[0] == record
    assert store.status(registry, record) == "Active"
    path.unlink()
    assert store.status(registry, record) == "Unavailable"
    assert store.active_model(registry)[0] is None
    for path in ("../escape.txt", str(tmp_path / "outside.txt")):
        with pytest.raises(ValueError):
            store.artifact_path(path)
    with pytest.raises(ValueError):
        ModelRegistry(active=ActiveModelReference("absent", "v1"))


def test_registry_corrupt_metadata_is_not_a_fake_empty_state(tmp_path):
    store = LocalModelRegistry(tmp_path)
    store.metadata_path.write_text('{"schema_version":2,"records":[],"active":null}')
    with pytest.raises(ValueError):
        store.read()


def test_replay_model_admission_rejects_training_and_selection_information_from_future():
    early = ForecastRequest(
        HOUSEHOLDS, datetime(2013, 3, 19, tzinfo=UTC), replay_date=date(2013, 3, 19)
    )
    with pytest.raises(ValueError, match="later than"):
        validate_model_for_request(model(), early)
    later = replace(
        early, forecast_origin=datetime(2013, 11, 7, tzinfo=UTC), replay_date=date(2013, 11, 7)
    )
    validate_model_for_request(model(), later)
    with pytest.raises(ValueError):
        replace(early, horizon_steps=49)
    with pytest.raises(ValueError):
        replace(early, forecast_origin=datetime(2013, 3, 19, 0, 15, tzinfo=UTC))


def test_forecast_output_batch_origin_intervals_identity_and_units():
    origin = datetime(2013, 4, 1, tzinfo=UTC)
    request = ForecastRequest((HOUSEHOLDS[0],), origin)
    # Synthetic contract fixtures; this is not a forecaster implementation or UI output.
    rows = tuple(
        ForecastOutput(
            HOUSEHOLDS[0],
            origin,
            origin + timedelta(minutes=30 * step),
            origin + timedelta(minutes=30 * (step + 1)),
            step + 1,
            0.5,
            model().reference,
        )
        for step in range(48)
    )
    validate_forecast_batch(request, rows, model().reference)
    with pytest.raises(ValueError):
        validate_forecast_batch(request, rows[:-1], model().reference)
    with pytest.raises(ValueError):
        validate_forecast_batch(request, rows + rows[:1], model().reference)
    with pytest.raises(ValueError):
        replace(rows[0], interval_end=origin)
    with pytest.raises(ValueError):
        replace(rows[0], predicted_average_power_kw=-1)


def test_simulation_metadata_makes_changed_assumptions_incompatible():
    plan = SimulationPlan(
        "reviewed-event",
        datetime(2025, 3, 18, 18, tzinfo=UTC),
        date(2013, 3, 19),
        datetime(2013, 3, 19, tzinfo=UTC),
        default_portfolio(),
        10,
        model().reference,
    )
    original = plan.experiment_inputs().experiment_id
    for changed in (
        replace(plan, forecast_model=ActiveModelReference("fixture", "v2")),
        replace(plan, tariff_assumptions="different tariff"),
        replace(plan, baseline_assumptions="different baseline"),
        replace(plan, demand_scenario="different demand"),
        replace(plan, portfolio=plan.portfolio.select([HOUSEHOLDS[0]])),
        replace(
            plan, replay_date=date(2013, 3, 20), forecast_origin=datetime(2013, 3, 20, tzinfo=UTC)
        ),
    ):
        assert changed.experiment_inputs().experiment_id != original
    assert plan.forecast_request().household_ids == HOUSEHOLDS
    assert "2025" in plan.experiment_inputs().input_data_references_json
    assert "2013" in plan.experiment_inputs().forecast_assumptions_json
