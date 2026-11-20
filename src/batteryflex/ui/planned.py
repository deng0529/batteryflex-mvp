"""Forecast development, dispatch and saved cross-method comparison."""

import streamlit as st

from batteryflex.defaults import SimulationDefaults, load_defaults
from batteryflex.portfolio import scenario_snapshot
from batteryflex.ui.dispatch import render_dispatch
from batteryflex.ui.dispatch_benchmark import render_comparison
from batteryflex.ui.forecasting import development_tab, read_event_store
from batteryflex.ui.portfolio import current_portfolio, render_portfolio  # noqa: F401


def _run_tab(store) -> None:
    render_dispatch(getattr(store, "repository", None))


def render_simulation() -> None:
    st.title("Simulation Lab")
    st.caption("Qualify assets, simulate event dispatch and evaluate saved performance.")
    try:
        portfolio = current_portfolio()
    except (ValueError, OSError, KeyError, RuntimeError):
        st.error("The active portfolio could not be read from storage.")
        return
    # Keep the saved-only snapshot accessible even when the development tab is open.
    st.session_state.battery_scenario = scenario_snapshot(
        portfolio,
        st.session_state.get("simulation_event") or st.session_state.get("battery_event"),
        st.session_state.get(
            "simulation_commitment",
            st.session_state.get(
                "battery_commitment", load_defaults("simulation.yaml", SimulationDefaults).target_kw
            ),
        ),
    )
    store = read_event_store()
    tabs = st.tabs(
        ["Dispatch Simulation", "Dispatch Performance & Evaluation", "Demand Forecasting"],
        key="simulation_tabs",
        on_change="rerun",
    )
    if tabs[0].open:
        with tabs[0]:
            _run_tab(store)
    if tabs[1].open:
        with tabs[1]:
            render_comparison(getattr(store, "repository", None))
    if tabs[2].open:
        with tabs[2]:
            development_tab(store, None, "")
