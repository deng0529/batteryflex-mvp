"""Event chronology, source integrity, leakage, scoring and immutable reuse acceptance."""

import json
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
from test_forecast_training import frame as frame_fixture
from test_storage import FakeR2, prepared_root

from batteryflex.event_engine import build_event, replay_intervals, score_predictions
from batteryflex.event_history import combine_sources, coverage_matrix
from batteryflex.event_policy import EventPolicy, event_features, midnight
from batteryflex.forecast_contracts import ForecastModelConfig
from batteryflex.forecast_training import features, history
from batteryflex.lcl_analysis import map_day
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.storage.bootstrap import bootstrap
from batteryflex.storage.database import SQLiteDatabase, query
from batteryflex.storage.event_forecasts import (
    EventForecaster,
    EventForecasts,
    load_history,
    publish_history,
)
from batteryflex.storage.objects import Objects, sha256
from batteryflex.storage.repository import Repository


@pytest.fixture
def event_repo(tmp_path, tmp_path_factory):
    root, frame, _ = prepared_root.__wrapped__(tmp_path_factory)
    repository = Repository(
        SQLiteDatabase(tmp_path / "db.sqlite", create=True), Objects(tmp_path / "cache")
    )
    bootstrap(repository, root)
    repository.objects.client = FakeR2()
    directory = tmp_path / "event-data"
    directory.mkdir()
    frame = frame.assign(source_dataset="synthetic event test fixture")
    frame.to_parquet(directory / "observations.parquet", index=False)
    coverage_matrix(frame).to_csv(directory / "coverage.csv", index=False)
    (directory / "quarantine.json").write_text("[]")
    audit = dict(
        format="event-history-v1",
        artifacts={p.name: sha256(p.read_bytes()) for p in directory.iterdir()},
    )
    (directory / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
    identity = publish_history(repository, directory)
    return repository, frame, directory, identity


def test_exact_event_mapping_and_half_hours():
    events, samples, _ = load_selection()
    expected = {
        "2025-03-18": ("2013-03-19", 2),
        "2025-11-06": ("2013-11-07", 2),
        "2023-12-01": ("2013-12-06", 3),
        "2026-01-11": ("2013-01-13", 4),
        "2025-02-02": ("2013-02-03", 6),
    }
    for event in events:
        mapped, count = expected[str(event["delivery_date"])]
        index = replay_intervals(event, samples[event["resource_id"]])
        assert len(index) == count and set(index.date) == {pd.Timestamp(mapped).date()}
        assert str(map_day(event["delivery_date"])) == mapped
        assert event["validation_status"] == "PASS"


def test_new_features_do_not_read_future_or_fill_missing():
    series = history(frame_fixture.__wrapped__(), HOUSEHOLDS[0])
    origin = midnight(pd.Timestamp("2013-03-19").date())
    x = event_features(series, origin)
    altered = series.copy()
    altered.loc[altered.index >= origin] = 10000
    np.testing.assert_array_equal(x, event_features(altered, origin))
    altered = series.copy()
    altered.loc[pd.Timestamp("2013-03-16", tz="UTC")] = np.nan
    with pytest.raises(ValueError, match="Incomplete"):
        features(altered, origin)
    np.testing.assert_array_equal(x, event_features(altered, origin))  # irrelevant intervening day
    altered.loc[pd.Timestamp("2013-03-18", tz="UTC")] = np.nan
    with pytest.raises(ValueError, match="Incomplete"):
        event_features(altered, origin)


def test_chronological_windows_and_future_labels_cannot_affect_predictions():
    events, samples, _ = load_selection()
    event = events[0]
    origin = midnight(map_day(event["delivery_date"]))
    periods = EventPolicy().periods(origin)
    assert periods["training"].end < periods["validation"].start
    assert periods["validation"].end < periods["holdout"].start
    assert periods["holdout"].available_through == origin
    frame = frame_fixture.__wrapped__()
    first = build_event(
        frame, event, samples[event["resource_id"]], ForecastModelConfig("Ridge Regression")
    )
    changed = frame.copy()
    future = changed.interval_start_gmt >= origin
    changed.loc[future, "energy_kwh"] = 5000
    changed.loc[future, "average_power_kw"] = 10000
    second = build_event(
        changed, event, samples[event["resource_id"]], ForecastModelConfig("Ridge Regression")
    )
    np.testing.assert_array_equal(first[1].prediction, second[1].prediction)
    full = first[1][first[1].partition == "full_day"]
    assert full.groupby("household").size().eq(48).all()
    assert set(full.household) == {*HOUSEHOLDS, "Portfolio"}
    for _timestamp, rows in full.groupby("interval_start"):
        assert rows.loc[rows.household.eq("Portfolio"), "prediction"].iloc[0] == pytest.approx(
            rows.loc[rows.household.isin(HOUSEHOLDS), "prediction"].sum()
        )
    window = first[2][first[2].scope.eq("event_window")]
    assert len(window) == 6 and window.observations.eq(2).all()


def test_event_scoring_missing_actuals_are_not_zero():
    rows = pd.DataFrame(
        dict(
            partition=["event_window"] * 2,
            household=["home"] * 2,
            method=["Ridge Regression"] * 2,
            actual=[1.0, np.nan],
            prediction=[2.0, 100.0],
        )
    )
    score = score_predictions(rows).iloc[0]
    assert (
        score.mae_kw == score.rmse_kw == 1
        and score.observations == 1
        and score.expected_observations == 2
    )


def test_immutable_sources_merge_and_dataset(event_repo):
    repo, frame, directory, identity = event_repo
    original = repo.setting("dataset")
    assert original != identity
    assert publish_history(repo, directory) == identity and repo.setting("dataset") == original
    loaded, coverage, _ = load_history(repo)
    pd.testing.assert_frame_equal(loaded, frame)
    annual = frame[frame.interval_start_gmt.dt.year.eq(2013)]
    combined = combine_sources(annual, frame)
    pd.testing.assert_series_equal(
        combined.energy_kwh.reset_index(drop=True),
        annual.sort_values(["household_id", "interval_start_gmt"]).energy_kwh.reset_index(
            drop=True
        ),
    )
    (directory / "coverage.csv").write_text("bad source")
    with pytest.raises(ValueError, match="integrity"):
        publish_history(repo, directory)


def test_event_cloud_style_persistence_cold_reuse_and_cutoff(event_repo, tmp_path, monkeypatch):
    repo, frame, _, _ = event_repo
    events, samples, _ = load_selection()
    event = events[0]
    service = EventForecasts(repo)
    configs = (ForecastModelConfig("Ridge Regression"), ForecastModelConfig("LightGBM"))
    first = service.run(event, samples[event["resource_id"]], configs)
    assert len(service.trained) == 3
    assert len(query(repo.db, "SELECT * FROM event_forecast_models")) == 3
    assert len(query(repo.db, "SELECT * FROM event_forecast_metrics")) == 72
    assert not query(repo.db, "SELECT * FROM event_active_models")
    cold = Repository(repo.db, Objects(tmp_path / "fresh-cache", repo.objects.client))

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected refit or upload")

    monkeypatch.setattr("batteryflex.storage.event_forecasts.build_event", forbidden)
    monkeypatch.setattr(cold.objects.client, "put_object", forbidden)
    before = query(repo.db, "SELECT * FROM event_forecast_models")
    reused = EventForecasts(cold)
    second = reused.run(event, samples[event["resource_id"]], configs)
    assert len(reused.reused) == 3 and not reused.trained
    assert before == query(repo.db, "SELECT * FROM event_forecast_models")
    for a, b in zip(first, second, strict=True):
        pd.testing.assert_frame_equal(a["predictions"], b["predictions"])
    origin = midnight(map_day(event["delivery_date"]))
    forecaster = EventForecaster(second[1], frame)
    assert len(forecaster.predict(household_ids=HOUSEHOLDS, forecast_origin=origin)) == 240
    with pytest.raises(ValueError, match="later than"):
        forecaster.predict(household_ids=HOUSEHOLDS, forecast_origin=origin - timedelta(days=1))
    service.activate(first[1])
    assert len(query(repo.db, "SELECT * FROM event_active_models")) == 1


def test_unavailable_event_records_reason_without_fit(event_repo, monkeypatch):
    repo, _, _, _ = event_repo
    events, samples, _ = load_selection()
    event = events[3]
    monkeypatch.setattr(
        "batteryflex.storage.event_forecasts.build_event",
        lambda *a, **k: pytest.fail("unavailable fit"),
    )
    with pytest.raises(ValueError, match="insufficient"):
        EventForecasts(repo).run(
            event, samples[event["resource_id"]], (ForecastModelConfig("LightGBM"),)
        )
    assert not query(repo.db, "SELECT * FROM event_forecast_models")
    status = query(repo.db, "SELECT * FROM event_forecast_status")[0]
    assert status["state"] == "unavailable" and status["reason"]


def test_original_source_integrity_and_quarantine(tmp_path):
    from zipfile import ZipFile

    from batteryflex.event_source import read_original

    path = tmp_path / "original.zip"
    text = (
        "LCLid,stdorToU,DateTime,KWH/hh (per half hour) \n"
        "MAC001391,Std,2012-12-01 00:30:00.0000000,1\n"
        "MAC001391,Std,2012-12-01 00:30:00.0000000,2\n"
        "MAC001391,Std,2012-12-01 01:00:00.0000000,Null\n"
        "MAC001391,Std,2012-12-01 01:13:00.0000000,3\n"
    )
    with ZipFile(path, "w") as zipped:
        zipped.writestr("original.csv", text)
    acquisition = dict(sha256=sha256(path.read_bytes()), bytes=path.stat().st_size)
    frame, audit, quarantine = read_original(path, acquisition)
    assert audit["scanned_csv_members"] == 1 and len(frame) == 2
    assert set(frame.quality) == {"duplicate", "missing"} and frame.energy_kwh.isna().all()
    assert len(quarantine) == 3 and set(r["reason"] for r in quarantine) == {
        "duplicate_key",
        "off_grid_timestamp",
    }
    with pytest.raises(ValueError, match="hash mismatch"):
        read_original(path, {**acquisition, "sha256": "0" * 64})


def test_event_failure_and_concurrent_claim_do_not_publish(event_repo, monkeypatch):
    import time

    from batteryflex.storage.event_forecasts import model_identity, request_identity

    repo, _, _, identity = event_repo
    events, samples, _ = load_selection()
    event = events[0]
    request, _ = request_identity(identity, event, EventPolicy())
    fingerprint = model_identity(request, ForecastModelConfig())
    repo.db.batch(
        [("INSERT INTO model_leases VALUES(?,?,?)", (fingerprint, "other", int(time.time()) + 600))]
    )
    with pytest.raises(ValueError, match="already being computed"):
        EventForecasts(repo).run(
            event, samples[event["resource_id"]], (ForecastModelConfig("LightGBM"),)
        )
    assert not query(repo.db, "SELECT * FROM event_forecast_models")
    repo.db.batch([("DELETE FROM model_leases WHERE fingerprint=?", (fingerprint,))])
    monkeypatch.setattr(
        repo.objects, "put", lambda *a, **k: (_ for _ in ()).throw(ValueError("upload failure"))
    )
    with pytest.raises(ValueError, match="upload failure"):
        EventForecasts(repo).run(
            event, samples[event["resource_id"]], (ForecastModelConfig("LightGBM"),)
        )
    assert not query(repo.db, "SELECT * FROM event_forecast_models")
    assert not query(repo.db, "SELECT * FROM model_leases")


def test_event_fingerprint_parameters_and_origin():
    from batteryflex.storage.event_forecasts import model_identity, request_identity

    events, _, _ = load_selection()
    first, _ = request_identity("a" * 64, events[0], EventPolicy())
    other, _ = request_identity("a" * 64, events[1], EventPolicy())
    assert model_identity(first, ForecastModelConfig("Ridge Regression")) == model_identity(
        first, ForecastModelConfig("Ridge Regression", '{"alpha":1.0}')
    )
    assert model_identity(first, ForecastModelConfig("Ridge Regression")) != model_identity(
        first, ForecastModelConfig("Ridge Regression", '{"alpha":2.0}')
    )
    assert first != other


def test_event_ui_restores_without_fit_and_has_no_activation_controls(
    event_repo, tmp_path, monkeypatch
):
    from streamlit.testing.v1 import AppTest

    repo, _, _, _ = event_repo
    script = """
import streamlit as st
from batteryflex.storage.registry import DatabaseModelRegistry
from batteryflex.ui.event_forecasts import render_event_development
render_event_development(DatabaseModelRegistry(st.session_state.repo,st.session_state.directory))
"""
    app = AppTest.from_string(script, default_timeout=40)
    app.session_state.repo = repo
    app.session_state.directory = tmp_path
    app.run()
    assert not app.exception and not app.error
    assert len(app.selectbox(key="event_forecast_event").options) == 5
    app.button(key="event_forecast_run").click().run()
    assert not app.exception and not app.error
    assert len(app.get("vega_lite_chart")) == 2
    assert any(row.value == "Models trained and saved" for row in app.success)
    assert not any(
        w.key in {"event_metric_scope", "forecast_workflow"} for w in app.segmented_control
    )
    dates = app.dataframe[0].value
    assert list(dates.Dataset) == ["Training", "Validation", "Testing / Holdout", "Event Forecast"]
    assert dates.iloc[0]["Start Date"] == "2012-11-21"
    assert dates.iloc[0]["End Date"] == "2013-02-18"
    assert dates.iloc[2]["End Date"] == "2013-03-18"
    assert dates.iloc[3]["Start Date"] == "2013-03-19"
    assert app.selectbox(key="event_curve_household").options == ["Portfolio", *HOUSEHOLDS]
    assert not query(repo.db, "SELECT * FROM event_active_models")
    assert not any(b.label == "Save Model" for b in app.button)

    def forbidden(*args, **kwargs):
        raise AssertionError("rerun attempted model training")

    monkeypatch.setattr("batteryflex.storage.event_forecasts.build_event", forbidden)
    monkeypatch.setattr("batteryflex.event_engine.predict", forbidden)
    monkeypatch.setattr("batteryflex.forecast_training.predict", forbidden)
    app.selectbox(key="event_curve_household").select_index(1).run()
    assert not app.exception and len(app.get("vega_lite_chart")) == 2
    assert not app.expander
    assert len(app.dataframe) == 2
    assert len(app.dataframe[1].value) == 18
    assert set(app.dataframe[1].value.Model) == {"Ridge Regression", "LightGBM", "Seasonal Naive"}
    assert not any("Recommended" in row.value or "Peak" in row.value for row in app.markdown)
    app.button(key="event_forecast_run").click().run()
    assert any(row.value == "Saved forecasting results loaded" for row in app.success)
    assert not any("activat" in b.label.lower() for b in app.button)
    assert not query(repo.db, "SELECT * FROM event_active_models")
    fresh = AppTest.from_string(script, default_timeout=40)
    fresh.session_state.repo = repo
    fresh.session_state.directory = tmp_path
    fresh.run()
    assert not fresh.exception and len(fresh.get("vega_lite_chart")) == 2
    assert any(row.value == "Saved forecasting results loaded" for row in fresh.success)
    assert not any("Active event model:" in row.value for row in fresh.markdown)
    fresh.selectbox(key="event_forecast_event").select_index(3).run()
    assert not fresh.exception and fresh.button(key="event_forecast_run").disabled
    assert not fresh.get("vega_lite_chart")


@pytest.mark.parametrize("fault", ["missing", "corrupt", "incompatible"])
def test_clean_ui_reports_invalid_saved_artifacts_without_training(
    event_repo, tmp_path, monkeypatch, fault
):
    from streamlit.testing.v1 import AppTest

    from batteryflex.storage.repository import canonical, object_statement

    repo, _, _, _ = event_repo
    events, samples, _ = load_selection()
    results = EventForecasts(repo).run(
        events[0],
        samples[events[0]["resource_id"]],
        (ForecastModelConfig("Ridge Regression"), ForecastModelConfig("LightGBM")),
    )
    ridge = next(r for r in results if r["record"]["algorithm"] == "Ridge Regression")
    object_id = ridge["record"]["artifact_id"]
    key = "objects/" + object_id
    if fault == "incompatible":
        changed = {**ridge["artifact"], "feature_schema": "unsupported-schema"}
        ref = repo.objects.put(canonical(changed).encode(), "event-model-v1")
        repo.db.batch(
            [
                object_statement(ref),
                (
                    "UPDATE event_forecast_models SET artifact_id=? WHERE fingerprint=?",
                    (ref.sha256, ridge["record"]["fingerprint"]),
                ),
            ]
        )
    else:
        (repo.objects.cache / key).unlink()
        if fault == "missing":
            del repo.objects.client.data[key]
        else:
            repo.objects.client.data[key] = b"corrupted remote model"
    before = query(repo.db, "SELECT * FROM event_forecast_models")

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid saved artifacts must not cause implicit training or writes")

    monkeypatch.setattr("batteryflex.storage.event_forecasts.build_event", forbidden)
    monkeypatch.setattr(repo.objects, "put", forbidden)
    script = """
import streamlit as st
from batteryflex.storage.registry import DatabaseModelRegistry
from batteryflex.ui.event_forecasts import render_event_development
render_event_development(DatabaseModelRegistry(st.session_state.repo,st.session_state.directory))
"""
    app = AppTest.from_string(script, default_timeout=40)
    app.session_state.repo, app.session_state.directory = repo, tmp_path
    app.run()
    assert not app.exception
    assert any("Event forecast unavailable:" in row.value for row in app.error)
    assert not app.get("vega_lite_chart")
    assert before == query(repo.db, "SELECT * FROM event_forecast_models")
