"""Numerical, leakage, batch and durable bundle acceptance tests."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from batteryflex.forecast_contracts import METHODS, ForecastDatasetConfig, ForecastModelConfig
from batteryflex.forecast_persistence import (
    SavedForecaster,
    activate_bundle,
    load_bundle,
    save_bundle,
)
from batteryflex.forecast_registry import LocalModelRegistry
from batteryflex.forecast_training import (
    FEATURES,
    aggregate,
    examples,
    features,
    history,
    improvement,
    metric,
    predict,
    run_models,
)
from batteryflex.portfolio import HOUSEHOLDS


@pytest.fixture(scope="module")
def frame():
    index = pd.date_range("2013-01-01", "2013-04-09", freq="30min", tz="UTC", inclusive="left")
    rows = []
    for k, household in enumerate(HOUSEHOLDS):
        power = 1 + k / 5 + 0.5 * np.sin(np.arange(len(index)) * 2 * np.pi / 48)
        rows.append(
            pd.DataFrame(
                dict(
                    household_id=household,
                    interval_start_gmt=index,
                    interval_end_gmt=index + pd.Timedelta(minutes=30),
                    quality="valid",
                    energy_kwh=power / 2,
                    average_power_kw=power,
                )
            )
        )
    return pd.concat(rows, ignore_index=True)


@pytest.fixture(scope="module")
def result(frame):
    return run_models(
        frame, tuple(ForecastModelConfig(m) for m in METHODS), ForecastDatasetConfig(), "a" * 64
    )


def test_origin_features_cannot_read_target_or_future(frame):
    origin = datetime(2013, 3, 20, tzinfo=UTC)
    series = history(frame, HOUSEHOLDS[0])
    before = features(series, origin)
    changed = series.copy()
    changed.loc[changed.index >= origin] = 10000
    np.testing.assert_array_equal(before, features(changed, origin))
    assert before.shape == (48, len(FEATURES))
    np.testing.assert_allclose(
        predict(None, "Seasonal Naive", before), series.loc["2013-03-19"].to_numpy()
    )
    with pytest.raises(ValueError, match="midnight"):
        features(series, datetime(2013, 3, 20, 1, tzinfo=UTC))


def test_warmup_missing_and_split_boundaries(frame):
    series = history(frame, HOUSEHOLDS[0])
    dataset = ForecastDatasetConfig()
    for partition, expected in (("training", 52), ("validation", 15), ("testing", 16)):
        period = getattr(dataset, partition)
        x, y, times = examples(series, period)
        assert len(y) == len(x) == expected * 48
        assert times.min().date() >= period.start and times.max().date() <= period.end
    missing = series.copy()
    missing.loc[pd.Timestamp("2013-03-19 02:00", tz="UTC")] = np.nan
    with pytest.raises(ValueError, match="Incomplete"):
        features(missing, datetime(2013, 3, 20, tzinfo=UTC))
    _, y, _ = examples(missing, dataset.testing)
    assert len(y) == 8 * 48  # missing target day plus next seven origin-history days
    with pytest.raises(ValueError):
        examples(series, replace(dataset.training, end=dataset.training.start))


def test_complete_batch_metrics_aggregate_and_no_retraining(result, frame, tmp_path, monkeypatch):
    assert set(result.models) == set(METHODS)
    assert all(set(models) == set(HOUSEHOLDS) for models in result.models.values())
    assert len(result.counts) == 15
    assert set(result.metrics.household) == {*HOUSEHOLDS, "Portfolio"}
    assert result.predictions.groupby(["partition", "household", "method"]).size().min() >= 720
    for method in METHODS:
        store = LocalModelRegistry(tmp_path / method)
        record = save_bundle(store, result, method, "v1")
        assert store.read().active is None
        restored = load_bundle(store, record)
        x = features(history(frame, HOUSEHOLDS[0]), datetime(2013, 4, 2, tzinfo=UTC))
        np.testing.assert_allclose(
            predict(restored[HOUSEHOLDS[0]], method, x),
            predict(result.models[method][HOUSEHOLDS[0]], method, x),
            atol=1e-10,
        )
        with pytest.raises(ValueError, match="Immutable"):
            save_bundle(store, result, method, "v1")
        activate_bundle(store, record.reference)

        def forbidden(*args, **kwargs):
            raise AssertionError("inference attempted fitting")

        monkeypatch.setattr("batteryflex.forecast_training.fit", forbidden)
        forecaster = SavedForecaster(store, frame, "a" * 64)
        outputs = forecaster.predict(
            household_ids=HOUSEHOLDS, forecast_origin=datetime(2013, 4, 2, tzinfo=UTC)
        )
        assert len(outputs) == 240 and all(o.predicted_average_power_kw >= 0 for o in outputs)
        with pytest.raises(ValueError, match="later than"):
            forecaster.predict(
                household_ids=HOUSEHOLDS, forecast_origin=datetime(2013, 3, 20, tzinfo=UTC)
            )
        with pytest.raises(ValueError, match="provenance"):
            SavedForecaster(store, frame, "b" * 64)
        with pytest.raises(ValueError):
            forecaster.predict(
                household_ids=("unknown",), forecast_origin=datetime(2013, 4, 2, tzinfo=UTC)
            )
        path = store.artifact_path(record.artifact_location)
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        payload["payload"]["features"] = ["bad"]
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="checksum"):
            load_bundle(store, record)
        payload["sha256"] = hashlib.sha256(
            json.dumps(payload["payload"], allow_nan=False, sort_keys=True).encode()
        ).hexdigest()
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="Incompatible"):
            load_bundle(store, record)
        path.unlink()
        with pytest.raises(ValueError, match="Missing"):
            activate_bundle(store, record.reference)


def test_metrics_and_incomplete_portfolio(result):
    assert metric(np.array([1.0, 3.0]), np.array([2.0, 1.0])) == (1.5, np.sqrt(2.5))
    assert improvement(2, 1) == 50 and improvement(1, 2) == -100
    assert improvement(0, 1) is None
    with pytest.raises(ValueError):
        metric(np.array([np.nan]), np.array([1.0]))
    rows = result.predictions[result.predictions.household.isin(HOUSEHOLDS)]
    assert len(aggregate(rows)) == (15 + 16) * 48 * 3
    assert aggregate(rows[rows.household != HOUSEHOLDS[0]]).empty
    duplicate = pd.concat([rows, rows[rows.household == HOUSEHOLDS[0]]])
    assert aggregate(duplicate).empty


def test_training_failure_does_not_return_partial_bundle(frame, monkeypatch):
    def fail(*args):
        raise RuntimeError("intentional failure")

    monkeypatch.setattr("batteryflex.forecast_training.fit", fail)
    with pytest.raises(ValueError, match="Seasonal Naive / MAC001391 failed"):
        run_models(frame, (ForecastModelConfig(),), ForecastDatasetConfig(), "a" * 64)


def test_bundle_write_failure_and_competing_writer(result, tmp_path, monkeypatch):
    store = LocalModelRegistry(tmp_path / "models")

    def fail(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(store, "write", fail)
    with pytest.raises(OSError, match="disk unavailable"):
        save_bundle(store, result, "Ridge Regression", "v1")
    assert not store.read().records
    assert not list(store.artifacts.glob("*.json"))
    assert not (store.root / ".writer.lock").exists()
    (store.root / ".writer.lock").write_text("busy")
    with pytest.raises(ValueError, match="write is in progress"):
        save_bundle(store, result, "Ridge Regression", "v1")


def test_missing_inference_history_is_rejected(result, frame, tmp_path):
    store = LocalModelRegistry(tmp_path)
    record = save_bundle(store, result, "Seasonal Naive", "v1")
    activate_bundle(store, record.reference)
    incomplete = frame[frame.interval_start_gmt != pd.Timestamp("2013-04-01", tz="UTC")]
    forecaster = SavedForecaster(store, incomplete, "a" * 64)
    with pytest.raises(ValueError, match="Incomplete"):
        forecaster.predict(
            household_ids=HOUSEHOLDS, forecast_origin=datetime(2013, 4, 2, tzinfo=UTC)
        )
