"""Product navigation and explicit simulation actions."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_app_defaults_to_read_only_overview(monkeypatch):
    import streamlit as st

    from batteryflex.storage import dispatch_runs

    navigation = st.navigation
    titles = []

    def record_pages(pages):
        titles.extend(page.title for page in pages)
        return navigation(pages)

    def unexpected_execution(*args, **kwargs):
        pytest.fail("Opening Overview attempted dispatch")

    monkeypatch.setattr(st, "navigation", record_pages)
    monkeypatch.setattr(dispatch_runs, "run_dispatch", unexpected_execution)
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception and not app.error
    assert app.title[0].value == "BatteryFlex"
    assert titles == ["Overview", "Data Explorer", "Portfolio & Configuration", "Simulation Lab"]
    assert {m.label: m.value for m in app.metric} == {
        "Configured assets": "5",
        "Installed capacity": "50 kWh",
        "Rated discharge power": "25 kW",
        "Historical events": "5",
        "Dispatch strategies": "3",
    }
    assert any("0 / 15" in caption.value for caption in app.caption)
    assert not app.get("vega_lite_chart")


def test_portfolio_has_five_simulated_batteries_and_editing_controls():
    app = AppTest.from_string(
        "from batteryflex.ui.planned import render_portfolio; render_portfolio()"
    ).run()
    assert not app.exception
    assert len(app.data_editor) == 1
    assert len(app.data_editor[0].value) == 5
    assert len(app.checkbox) == 5
    assert [s.value for s in app.subheader] == ["Asset configuration", "Asset qualification"]
    assert not app.get("vega_lite_chart")


def test_simulation_has_three_tabs_and_honest_empty_states():
    app = AppTest.from_string(
        "from batteryflex.ui.planned import render_simulation; render_simulation()"
    ).run(timeout=20)
    assert not app.exception
    assert [
        t.label
        for t in app.tabs
        if t.label
        in {"Dispatch Simulation", "Dispatch Performance & Evaluation", "Demand Forecasting"}
    ] == [
        "Dispatch Simulation",
        "Dispatch Performance & Evaluation",
        "Demand Forecasting",
    ]
    assert len(app.selectbox(key="simulation_event").options) == 5
    assert app.selectbox(key="dispatch_forecast_model").value == "LightGBM"
    assert app.button(key="dispatch_run_RBC").disabled
    assert any("Connect the prepared persistent database" in x.value for x in app.info)
    assert not app.metric and not app.get("vega_lite_chart")
    app.session_state["simulation_tabs"] = "Dispatch Performance & Evaluation"
    app.run()
    assert not app.exception
    assert any("No completed simulation runs" in x.value for x in app.info)
    app.session_state["simulation_tabs"] = "Demand Forecasting"
    app.run()
    assert not app.exception
    assert [s.value for s in app.subheader] == ["Event-aligned forecast development"]
    assert not any(w.key == "forecast_workflow" for w in app.segmented_control)
    assert any("requires the explicitly prepared" in x.value for x in app.info)
