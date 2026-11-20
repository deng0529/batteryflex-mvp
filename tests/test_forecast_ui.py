"""Forecast development uses measured fixture history, never illustrative predictions."""

from datetime import timedelta

from streamlit.testing.v1 import AppTest
from test_lcl_ui import fixture_data

from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.ui import forecasting, lcl_lab

# Exercise the preserved legacy workflow explicitly, outside visible navigation.
SCRIPT = """
from batteryflex.ui import planned, forecasting
original = planned.development_tab
try:
    def legacy_development(_store, _registry, _reason):
        store, registry, _, reason = forecasting.read_registry()
        forecasting.benchmark_development_tab(store, registry, reason)
    planned.development_tab = legacy_development
    import streamlit as st
    st.session_state.setdefault("simulation_tabs", "Demand Forecasting")
    planned.render_simulation()
finally:
    planned.development_tab = original
"""


def setup(tmp_path, monkeypatch):
    fixture_data(tmp_path)
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    root = tmp_path / "model-store"
    monkeypatch.setattr(forecasting, "REGISTRY_DIRECTORY", root)
    return root


def test_forecast_history_model_configuration_and_empty_registry(tmp_path, monkeypatch):
    root = setup(tmp_path, monkeypatch)
    app = AppTest.from_string(SCRIPT, default_timeout=20).run()
    assert not app.exception
    assert app.selectbox(key="forecast_household").options == [*HOUSEHOLDS, "Aggregated portfolio"]
    assert app.checkbox(key="select_Seasonal Naive").value
    assert app.checkbox(key="select_LightGBM").value
    assert not app.checkbox(key="select_Ridge Regression").value
    assert not any("A5." in heading.value for heading in app.subheader)
    assert any(i.value == "No trained forecast available." for i in app.info)
    assert any("No forecast model records" in i.value for i in app.info)
    assert not root.exists()
    original_split = app.session_state.forecast_dataset_config
    app.selectbox(key="forecast_household").select("Aggregated portfolio").run()
    assert not app.exception
    assert app.dataframe[0].value["Average power (kW)"].iloc[0] == 4.5
    first = app.date_input(key="forecast_observation_dates").value[0]
    app.date_input(key="forecast_observation_dates").set_value(
        (first + timedelta(days=1), first + timedelta(days=1))
    ).run()
    assert not app.exception
    assert app.session_state.forecast_dataset_config == original_split
    assert app.dataframe[0].value["Valid half-hours"].iloc[0] == 0
    assert not app.get("vega_lite_chart")
    app.checkbox(key="select_Ridge Regression").check().run()
    app.number_input(key="forecast_ridge_alpha").set_value(2.5).run()
    configs = app.session_state.forecast_model_configs
    assert (
        next(c for c in configs if c.method == "Ridge Regression").hyperparameters_json
        == '{"alpha":2.5}'
    )
    assert not app.exception
    assert app.number_input(key="forecast_lgb_leaves").value == 15
    assert app.number_input(key="forecast_lgb_trees").value == 200
    assert any(i.value == "No trained forecast available." for i in app.info)
    assert not root.exists()


def test_inspection_and_training_ranges_are_independent_and_bad_splits_are_reported(
    tmp_path, monkeypatch
):
    setup(tmp_path, monkeypatch)
    app = AppTest.from_string(SCRIPT, default_timeout=20).run()
    app.date_input(key="forecast_validation_dates").set_value(
        (
            app.session_state.forecast_dataset_config.training.end,
            app.session_state.forecast_dataset_config.validation.end,
        )
    ).run()
    assert not app.exception
    assert any("must not overlap" in e.value for e in app.error)
    assert any(i.value == "No trained forecast available." for i in app.info)


def test_run_tab_requires_persistent_inputs(tmp_path, monkeypatch):
    root = setup(tmp_path, monkeypatch)
    app = AppTest.from_string(SCRIPT, default_timeout=20).run()
    app.session_state["simulation_tabs"] = "Dispatch Simulation"
    app.run()
    assert not app.exception and app.button(key="dispatch_run_RBC").disabled
    app.selectbox(key="simulation_event").select_index(0).run()
    assert not app.exception
    assert any("Connect the prepared persistent database" in i.value for i in app.info)
    assert not app.metric and not app.get("vega_lite_chart")
    app.session_state["simulation_tabs"] = "Dispatch Performance & Evaluation"
    app.run()
    assert not app.exception
    assert any("No completed simulation runs" in i.value for i in app.info)
    assert not root.exists()


def test_data_explorer_range_summaries_update_without_changing_original_readings(
    tmp_path, monkeypatch
):
    setup(tmp_path, monkeypatch)
    app = AppTest.from_string(
        "from batteryflex.ui.explorer import lcl_explorer; lcl_explorer()", default_timeout=20
    ).run()
    app.selectbox(key="lcl_public_household").select(HOUSEHOLDS[0]).run()
    assert not app.exception
    assert any(m.value == "**Full Study-Period Summary**" for m in app.markdown)
    assert any(m.value == "**Selected Observation-Range Summary**" for m in app.markdown)
    full_valid = app.dataframe[0].value["Valid half-hours"].iloc[0]
    first = app.date_input(key="lcl_public_dates").value[0]
    app.date_input(key="lcl_public_dates").set_value((first, first)).run()
    assert not app.exception
    selected = app.dataframe[1].value.iloc[0]
    assert selected["Valid half-hours"] == 48
    assert selected["Observed energy (kWh)"] == 12
    assert selected["Average power (kW)"] == 0.5
    assert app.dataframe[0].value["Valid half-hours"].iloc[0] == full_valid
    app.session_state["lcl_original_readings"] = True
    app.run()
    assert len(app.dataframe[-1].value) == 48
    app.date_input(key="lcl_public_dates").set_value(
        (first + timedelta(days=1), first + timedelta(days=1))
    ).run()
    assert not app.exception and app.dataframe[1].value["Valid half-hours"].iloc[0] == 0
    assert any("No observations were retained" in i.value for i in app.info)


def test_unavailable_prepared_history_and_corrupt_registry_are_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    monkeypatch.setattr(forecasting, "REGISTRY_DIRECTORY", tmp_path / "models")
    app = AppTest.from_string(SCRIPT, default_timeout=20).run()
    assert not app.exception
    assert any("Prepared household data is unavailable" in i.value for i in app.info)
    assert any(i.value == "No trained forecast available." for i in app.info)
    root = tmp_path / "models"
    root.mkdir()
    (root / "registry.json").write_text("corrupt metadata")
    app.run()
    assert not app.exception and any("Registry unavailable" in e.value for e in app.error)


def persistent_fixture(tmp_path, monkeypatch, data):
    import json

    from batteryflex.storage import settings
    from batteryflex.storage.bootstrap import bootstrap
    from batteryflex.storage.database import SQLiteDatabase
    from batteryflex.storage.objects import Objects, sha256
    from batteryflex.storage.repository import Repository
    from batteryflex.ui import portfolio

    root = tmp_path / "source"
    prepared = root / "data/lcl/prepared"
    prepared.mkdir(parents=True)
    fixture_data(prepared)
    data.to_parquet(prepared / "observations.parquet", index=False)
    audit = json.loads((prepared / "audit.json").read_text(encoding="utf-8"))
    audit["artifacts"]["observations.parquet"] = sha256(
        (prepared / "observations.parquet").read_bytes()
    )
    (prepared / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
    repository = Repository(
        SQLiteDatabase(tmp_path / "models/app.sqlite", create=True),
        Objects(tmp_path / "models/object-cache"),
    )
    bootstrap(repository, root)
    for module in (settings, forecasting, portfolio):
        monkeypatch.setattr(module, "runtime_repository", lambda: (repository, "Test database"))
    monkeypatch.setattr(forecasting, "load_history", lambda: (data, audit))
    return repository, audit


def test_run_inspect_save_activate_and_tab_b(tmp_path, monkeypatch):
    from test_forecast_training import frame as frame_fixture

    data = frame_fixture.__wrapped__()
    repository, audit = persistent_fixture(tmp_path, monkeypatch, data)
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    app.checkbox(key="select_Ridge Regression").check().run()
    app.button(key="forecast_run").click().run()
    assert not app.exception and not app.error
    assert len(app.get("vega_lite_chart")) == 7  # history + five household curves + RMSE chart
    assert not any(b.key == "forecast_save" for b in app.button)
    from batteryflex.storage.database import query

    assert len(query(repository.db, "SELECT * FROM forecast_models")) == 3
    result = app.session_state.forecast_run_result
    assert len(result.models) == 3
    assert repository.setting("forecast_model") is None
    label = next(
        label
        for label in app.selectbox(key="forecast_activate_version").options
        if label.startswith("LightGBM /")
    )
    app.selectbox(key="forecast_activate_version").select(label).run()
    app.button(key="forecast_activate").click().run()
    assert not app.exception and not app.error
    assert repository.setting("forecast_model")["model_name"] == "LightGBM"
    app.session_state["simulation_tabs"] = "Dispatch Simulation"
    app.run()
    assert not app.exception and app.button(key="dispatch_run_RBC").disabled
    app.selectbox(key="simulation_event").select_index(0).run()
    assert app.button(key="dispatch_run_RBC").disabled
    assert any("Simulation inputs unavailable" in error.value for error in app.error)
    assert not any("Active forecasting model:" in m.value for m in app.markdown)
    assert repository.setting("forecast_model")["model_name"] == "LightGBM"


def test_failed_run_clears_previous_results(tmp_path, monkeypatch):
    from test_forecast_training import frame as frame_fixture

    from batteryflex.ui import forecast_results

    data = frame_fixture.__wrapped__()
    persistent_fixture(tmp_path, monkeypatch, data)
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    app.session_state.forecast_run_result = "stale"

    def fail(*args):
        raise ValueError("intentional model failure")

    monkeypatch.setattr(forecast_results.ForecastCache, "run", fail)
    app.button(key="forecast_run").click().run()
    assert not app.exception
    assert any("intentional model failure" in e.value for e in app.error)
    assert "forecast_run_result" not in app.session_state


def test_a4_charts_validation_default_day_change_and_no_tables(tmp_path, monkeypatch):
    import pandas as pd
    import streamlit as st
    from test_forecast_training import frame as frame_fixture

    from batteryflex.forecast_contracts import METHODS, ForecastDatasetConfig, ForecastModelConfig
    from batteryflex.storage.forecast_cache import ForecastCache
    from batteryflex.ui import forecast_results

    data = frame_fixture.__wrapped__()
    repository, audit = persistent_fixture(tmp_path, monkeypatch, data)
    result = ForecastCache(repository, tmp_path / "models").run(
        data,
        tuple(ForecastModelConfig(m) for m in METHODS),
        ForecastDatasetConfig(),
        audit["artifacts"]["observations.parquet"],
    )
    # Deliberately make validation and test portfolio winners different.
    portfolio = result.metrics.household.eq("Portfolio")
    validation = portfolio & result.metrics.partition.eq("validation")
    result.metrics.loc[validation, "rmse_kw"] = 1.0
    result.metrics.loc[validation & result.metrics.method.eq("Ridge Regression"), "rmse_kw"] = 0.1
    testing = portfolio & result.metrics.partition.eq("testing")
    result.metrics.loc[testing, "rmse_kw"] = 1.0
    result.metrics.loc[testing & result.metrics.method.eq("LightGBM"), "rmse_kw"] = 0.1
    monkeypatch.setattr(forecasting, "REGISTRY_DIRECTORY", tmp_path / "models")
    curves, bars = [], []
    real_line, real_vega = st.line_chart, st.vega_lite_chart

    def line(data, **kwargs):
        curves.append(data.copy())
        return real_line(data, **kwargs)

    def vega(data, spec, **kwargs):
        bars.append((data.copy(), spec))
        return real_vega(data, spec, **kwargs)

    monkeypatch.setattr(st, "line_chart", line)
    monkeypatch.setattr(st, "vega_lite_chart", vega)

    def forbidden(*args, **kwargs):
        raise AssertionError("Display changes must not retrain")

    monkeypatch.setattr(forecast_results.ForecastCache, "run", forbidden)
    script = """
import streamlit as st
from batteryflex.ui.forecasting import read_registry
from batteryflex.ui.forecast_results import render_results
run = st.session_state.forecast_run_result
store, registry, _, reason = read_registry()
render_results(store, registry, reason, None, None, run.configs, run.dataset)
"""
    app = AppTest.from_string(script, default_timeout=30)
    app.session_state.forecast_run_result = result
    app.run()
    assert not app.exception and not app.error
    assert not app.dataframe
    assert len(curves) == 5 and len(bars) == 1
    assert app.selectbox(key="forecast_activate_version").value.startswith("Ridge Regression /")
    assert any("validation portfolio RMSE: Ridge Regression" in c.value for c in app.caption)
    assert any("Portfolio lowest RMSE: LightGBM" in m.value for m in app.markdown)
    selected = app.selectbox(key="forecast_test_day").value
    for household, wide in zip(HOUSEHOLDS, curves, strict=True):
        assert len(wide) == 48 and set(wide.index.date) == {selected}
        assert list(wide.columns) == ["Actual", *[c.method for c in result.configs]]
        expected = result.predictions[
            result.predictions.household.eq(household)
            & result.predictions.partition.eq("testing")
            & result.predictions.interval_start.dt.date.eq(selected)
        ]
        for method in [c.method for c in result.configs]:
            assert (
                wide[method].tolist()
                == expected.loc[expected.method.eq(method), "prediction"].tolist()
            )
    original_bars = bars[0][0]
    label = next(
        label
        for label in app.selectbox(key="forecast_activate_version").options
        if label.startswith("LightGBM /")
    )
    app.selectbox(key="forecast_activate_version").select(label).run()
    curves.clear()
    app.selectbox(key="forecast_test_day").select_index(1).run()
    assert not app.exception and len(curves) == 5
    assert app.selectbox(key="forecast_activate_version").value.startswith("LightGBM /")
    pd.testing.assert_frame_equal(original_bars, bars[-1][0])
    assert all(
        len(wide) == 48 and set(wide.index.date) == {app.selectbox(key="forecast_test_day").value}
        for wide in curves
    )
    assert repository.setting("forecast_model") is None
