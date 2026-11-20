"""Validation-only recommendation and activation-independent saved forecast retrieval."""

import numpy as np
import pandas as pd
import pytest
from test_event_forecasts import event_repo  # noqa: F401 - shared isolated storage fixture

from batteryflex.forecast_contracts import ForecastModelConfig
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.storage.database import query
from batteryflex.storage.event_forecasts import EventForecasts
from batteryflex.storage.forecast_resolver import recommended_saved_model, resolve_event_forecast


def candidate(method, validation, final=0):
    return dict(
        record=dict(algorithm=method, version=method + "-version", request_id="same-event"),
        metrics=pd.DataFrame(
            [
                dict(
                    scope="validation", household="Portfolio", rmse_kw=validation, observations=48
                ),
                dict(scope="full_day", household="Portfolio", rmse_kw=final, observations=48),
            ]
        ),
    )


def test_recommendation_excludes_naive_and_final_day_errors_and_breaks_exact_ties():
    naive = candidate("Seasonal Naive", 0)
    ridge = candidate("Ridge Regression", 2, final=0)
    lgb = candidate("LightGBM", 1, final=99)
    assert recommended_saved_model([naive, ridge, lgb]) is lgb
    ridge["metrics"].loc[0, "rmse_kw"] = 1
    assert recommended_saved_model([lgb, ridge, naive]) is ridge


@pytest.mark.parametrize("bad", [np.nan, np.inf, -1])
def test_invalid_validation_metrics_fail_explicitly(bad):
    with pytest.raises(ValueError, match="invalid"):
        recommended_saved_model([candidate("Ridge Regression", bad), candidate("LightGBM", 1)])


def test_mixed_requests_or_incomplete_comparisons_cannot_recommend():
    ridge, lgb = candidate("Ridge Regression", 1), candidate("LightGBM", 2)
    with pytest.raises(ValueError, match="unavailable"):
        recommended_saved_model([ridge])
    lgb["record"]["request_id"] = "different-event"
    with pytest.raises(ValueError, match="same saved event"):
        recommended_saved_model([ridge, lgb])


@pytest.fixture
def saved(event_repo):  # noqa: F811 - pytest injects the imported shared fixture
    repo, _, _, _ = event_repo
    events, samples, _ = load_selection()
    event = events[0]
    service = EventForecasts(repo)
    results = service.run(
        event,
        samples[event["resource_id"]],
        (
            ForecastModelConfig("Ridge Regression"),
            ForecastModelConfig("LightGBM"),
        ),
    )
    return repo, event, results


def test_readonly_retrieval_override_and_independence_from_activation(saved, monkeypatch):
    repo, event, results = saved
    event_id = event["internal_scenario_id"]
    initial = resolve_event_forecast(repo, event_id)
    # A legacy activation deliberately selects the benchmark, which cannot affect resolution.
    EventForecasts(repo).activate(results[0])
    activation_before = query(repo.db, "SELECT * FROM event_active_models")
    original_batch = repo.db.batch

    def readonly(statements):
        assert all(sql.lstrip().upper().startswith("SELECT") for sql, _ in statements)
        assert all("event_active_models" not in sql.lower() for sql, _ in statements)
        return original_batch(statements)

    def forbidden(*a, **k):
        raise AssertionError("resolver attempted training or upload")

    monkeypatch.setattr(repo.db, "batch", readonly)
    monkeypatch.setattr(repo.objects, "put", forbidden)
    monkeypatch.setattr(EventForecasts, "run", forbidden)
    monkeypatch.setattr("batteryflex.storage.event_forecasts.build_event", forbidden)
    monkeypatch.setattr("batteryflex.event_engine.fit", forbidden)
    automatic = resolve_event_forecast(repo, event_id)
    assert automatic.algorithm == initial.algorithm
    assert automatic.model_version == initial.model_version
    assert automatic.replay_date.isoformat() == "2013-03-19"
    assert set(automatic.household_forecasts.household) == set(HOUSEHOLDS)
    assert automatic.household_forecasts.groupby("household").size().eq(48).all()
    assert list(automatic.portfolio_forecast.horizon_step) == list(range(1, 49))
    assert "actual" not in automatic.household_forecasts
    summed = automatic.household_forecasts.groupby("horizon_step").prediction.sum()
    np.testing.assert_allclose(summed, automatic.portfolio_forecast.prediction)
    for method in ("Ridge Regression", "LightGBM", "Seasonal Naive"):
        override = resolve_event_forecast(repo, event_id, algorithm=method)
        assert override.algorithm == method and override.overridden
        expected = next(r for r in results if r["record"]["algorithm"] == method)
        assert override.model_version == expected["record"]["version"]
        np.testing.assert_array_equal(
            override.portfolio_forecast.prediction,
            expected["predictions"]
            .query("partition == 'full_day' and household == 'Portfolio'")
            .sort_values("horizon_step")
            .prediction,
        )
    monkeypatch.setattr(repo.db, "batch", original_batch)
    assert activation_before == query(repo.db, "SELECT * FROM event_active_models")


def test_missing_candidate_requires_explicit_override_and_never_trains(saved, monkeypatch):
    repo, event, results = saved
    lgb = next(r for r in results if r["record"]["algorithm"] == "LightGBM")
    identity = lgb["record"]["fingerprint"]
    repo.db.batch(
        [
            ("DELETE FROM event_forecast_metrics WHERE model_id=?", (identity,)),
            ("DELETE FROM event_forecast_models WHERE fingerprint=?", (identity,)),
        ]
    )

    def forbidden(*a, **k):
        raise AssertionError("Missing saved model must not train")

    monkeypatch.setattr(EventForecasts, "run", forbidden)
    with pytest.raises(ValueError, match="unavailable.*LightGBM"):
        resolve_event_forecast(repo, event["internal_scenario_id"])
    assert (
        resolve_event_forecast(
            repo, event["internal_scenario_id"], algorithm="Ridge Regression"
        ).algorithm
        == "Ridge Regression"
    )
    with pytest.raises(ValueError, match="Override"):
        resolve_event_forecast(repo, event["internal_scenario_id"], algorithm="unsupported")


def test_missing_or_changed_mapping_and_unknown_event_fail(saved):
    repo, event, _ = saved
    key = event["internal_scenario_id"]
    repo.db.batch(
        [("UPDATE replay_mappings SET household_date='2013-03-20' WHERE event_id=?", (key,))]
    )
    with pytest.raises(ValueError, match="differs"):
        resolve_event_forecast(repo, key)
    repo.db.batch([("DELETE FROM replay_mappings WHERE event_id=?", (key,))])
    with pytest.raises(ValueError, match="mapping is unavailable"):
        resolve_event_forecast(repo, key)
    with pytest.raises(ValueError, match="Unknown"):
        resolve_event_forecast(repo, "not-an-event")


def test_dispatch_uses_saved_override_without_activation(saved, tmp_path):
    from streamlit.testing.v1 import AppTest

    from batteryflex.portfolio import default_portfolio
    from batteryflex.portfolio_storage import export_configuration
    from batteryflex.storage.dispatch_runs import scenario_from_result

    repo, event, _ = saved
    repo.save_portfolio(export_configuration(default_portfolio()))
    script = """
import streamlit as st
from batteryflex.storage.registry import DatabaseModelRegistry
from batteryflex.ui.planned import _run_tab
_run_tab(DatabaseModelRegistry(st.session_state.repo,st.session_state.directory))
"""
    app = AppTest.from_string(script, default_timeout=40)
    app.session_state.repo = repo
    app.session_state.directory = tmp_path
    app.run()
    app.selectbox(key="simulation_event").select_index(0).run()
    assert not app.exception and not app.error
    expected = resolve_event_forecast(repo, event["internal_scenario_id"], algorithm="LightGBM")
    assert app.selectbox(key="dispatch_forecast_model").value == "LightGBM"
    assert not app.button(key="dispatch_run_RBC").disabled
    assert not any(expected.model_version in row.value for row in app.success)
    assert not any(row.label == "Saved forecast provenance" for row in app.expander)
    assert not query(repo.db, "SELECT * FROM event_active_models")
    app.button(key="dispatch_run_RBC").click().run()
    assert not app.exception and not app.error
    sections = [row.value for row in app.subheader]
    assert sections[sections.index("Portfolio flexibility delivery") :] == [
        "Portfolio flexibility delivery",
        "Forecast-Based Dispatch Plan vs Historical Replay",
        "Event Interval Delivery",
        "Five-Battery Dispatch and Comparison",
        "Objective Contributions and Simulated Electricity Cost",
    ]
    assert len(app.get("vega_lite_chart")) == 5
    assert not app.get("download_button")
    assert not any(widget.label == "Dispatch trajectory" for widget in app.radio)
    assert not any("Allow grid export" in widget.label for widget in app.checkbox)
    signature, result, _ = app.session_state.dispatch_result_RBC
    assert result["planned"] is not None and result["realized"] is not None
    assert result["provenance"]["scenario"]["target_export_only"]
    assert result["provenance"]["inputs"]["model_version"] == expected.model_version
    assert all(b["export_enabled"] for b in result["provenance"]["scenario"]["batteries"])
    assert signature[1] == result["fingerprint"]
    assert scenario_from_result(result).replay
    assert app.session_state.dispatch_result_RBC[2] is False
    selector = app.radio(key="dispatch_dashboard_trajectory_RBC")
    assert selector.value == "Historical Replay"
    selector.set_value("Forecast-Based Dispatch Plan").run()
    assert not app.exception and app.radio(key="dispatch_dashboard_trajectory_RBC").value == (
        "Forecast-Based Dispatch Plan"
    )
    assert app.session_state.dispatch_result_RBC[1]["fingerprint"] == result["fingerprint"]
    app.button(key="dispatch_run_RBC").click().run()
    assert not app.exception and not app.error
    assert app.session_state.dispatch_result_RBC[2] is True
