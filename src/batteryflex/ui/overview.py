"""Product landing page and read-only Experiment A benchmark."""

import pandas as pd
import streamlit as st

from batteryflex.defaults import AppDefaults, ForecastingDefaults, load_defaults
from batteryflex.dispatch import DT, EPS, METHODS
from batteryflex.dispatch_event import event_start_batteries, standard_scenario
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import default_portfolio
from batteryflex.storage.dispatch_runs import scenario_from_result
from batteryflex.storage.repository import Repository
from batteryflex.storage.settings import runtime_repository
from batteryflex.ui.dispatch_benchmark import five_event_families, grouped_runs, saved_benchmarks
from batteryflex.ui.dispatch_overview import grouped_bars, run_row
from batteryflex.ui.portfolio import current_portfolio


def standard_results(results: list[dict], events: list[dict]) -> dict[str, dict[str, dict]]:
    """Select one compatible family matching the published Experiment A settings."""
    batteries = event_start_batteries(default_portfolio().batteries)
    defaults = load_defaults("forecasting.yaml", ForecastingDefaults)
    by_id = {event["internal_scenario_id"]: event for event in events}
    matching = []
    for result in results:
        inputs = result["provenance"]["inputs"]
        event = by_id.get(inputs["event_id"])
        if event is None or result.get("realized") is None:
            continue
        if (
            inputs["algorithm"] != defaults.dispatch_priority[0]
            or inputs["event_source_hash"] != event["source_records_sha256"]
            or inputs["original_event_start"] != event["start_utc"]
            or inputs["original_event_end"] != event["end_utc"]
        ):
            continue
        steps = tuple(range(round(event["duration_minutes"] / (DT * 60))))
        if scenario_from_result(result) == standard_scenario(batteries, steps):
            matching.append(result)
    families = five_event_families(grouped_runs(matching))
    best: dict[str, dict[str, dict]] = {}
    for family in families.values():
        selected: dict[str, dict[str, dict]] = {}
        for group in family:
            key = next(iter(group.values()))["provenance"]["inputs"]["event_id"]
            if len(group) > len(selected.get(key, {})):
                selected[key] = group
        if sum(map(len, selected.values())) > sum(map(len, best.values())):
            best = selected
    return best


def benchmark_summary(selected: dict[str, dict[str, dict]], count: int) -> pd.DataFrame | None:
    if (
        not count
        or len(selected) != count
        or any(set(group) != set(METHODS) for group in selected.values())
    ):
        return None
    rows = [run_row(group[method], "realized") for group in selected.values() for method in METHODS]
    totals = []
    for method in METHODS:
        runs = [row for row in rows if row["Controller"] == method]
        totals.append(
            {
                "Controller": method,
                "Events fulfilled": sum(row["Fulfilment"] == "MET" for row in runs),
                **{
                    key: sum(row[key] for row in runs)
                    for key in (
                        "Requested (kWh)",
                        "Delivered (kWh)",
                        "Simulated objective (£)",
                        "Degradation (£)",
                        "Household import (kWh)",
                        "Optimisation solves",
                    )
                },
            }
        )
    return pd.DataFrame(totals)


def _show_benchmark(repository: Repository | None, events: list[dict], precision: int) -> None:
    st.subheader("Experiment A · Historical Replay")
    st.caption("Published default portfolio, event-only execution and saved demand forecasts.")
    try:
        runs, _ = saved_benchmarks(repository) if repository is not None else ([], [])
        selected = standard_results(runs, events)
        summary = benchmark_summary(selected, len(events))
    except (KeyError, OSError, ValueError, TypeError, RuntimeError):
        st.info("Saved benchmark coverage is unavailable. Open Simulation Lab to review storage.")
        return
    coverage = sum(map(len, selected.values()))
    st.caption(f"Available compatible scenarios · {coverage} / {len(events) * len(METHODS)}")
    if summary is None:
        st.info(
            "A compatible result for each controller and event is needed for five-event totals."
        )
        return
    left, right = st.columns(2)
    with left:
        volume = summary.melt(
            "Controller",
            value_vars=["Requested (kWh)", "Delivered (kWh)"],
            var_name="Flexibility volume",
            value_name="Energy (kWh)",
        )
        grouped_bars(volume, "Flexibility volume", "Energy (kWh)")
    with right:
        grouped_bars(
            summary.assign(Trajectory="Historical Replay"), "Trajectory", "Simulated objective (£)"
        )
    st.dataframe(
        summary.drop(
            columns=["Requested (kWh)", "Delivered (kWh)", "Simulated objective (£)"]
        ).round(precision),
        hide_index=True,
        alt="Events fulfilled, degradation, grid imports and controller solves",
    )
    ranked = summary.sort_values("Simulated objective (£)")
    low = ranked["Simulated objective (£)"].min()
    leaders = ", ".join(
        ranked.loc[(ranked["Simulated objective (£)"] - low).abs() <= EPS, "Controller"]
    )
    st.write(
        f"{leaders} recorded the lowest realised objective (£{low:.{precision}f}) "
        "under these conditions."
    )
    if ranked["Events fulfilled"].eq(len(events)).all():
        st.write("All three strategies met every event.")
    if ranked["Degradation (£)"].max() - ranked["Degradation (£)"].min() <= EPS:
        st.write("The weighted battery degradation contribution was the same across all methods.")
    lowest_import = ranked.sort_values("Household import (kWh)").iloc[0]
    if ranked["Household import (kWh)"].max() - lowest_import["Household import (kWh)"] > EPS:
        st.write(
            f"{lowest_import['Controller']} recorded the lowest realised household grid import "
            f"at {lowest_import['Household import (kWh)']:.{precision}f} kWh."
        )
    st.caption(
        "Model Predictive Control uses rolling feedback. Its value depends on meaningful updates "
        "to forecasts, asset states or operating conditions."
    )


def render_overview(config: AppDefaults, pages, diagram: str) -> None:
    st.title(config.name)
    st.subheader(config.subtitle)
    st.write(
        "Aggregator-level decision support for qualifying, coordinating and evaluating "
        "distributed residential battery assets against historical flexibility events."
    )
    with st.container(horizontal=True, gap="medium"):
        for page, label in zip(
            pages, ("Explore Data", "Configure Portfolio", "Open Simulation Lab"), strict=True
        ):
            st.page_link(page, label=label)
    events, _, _ = load_selection()
    repository = None
    portfolio = default_portfolio()
    try:
        repository, _ = runtime_repository()
        if repository is not None:
            portfolio = current_portfolio(repository)
    except (ValueError, OSError, KeyError, RuntimeError):
        st.caption("The saved portfolio is unavailable. The configured defaults are shown.")
    capacity = sum(b.capacity_kwh for b in portfolio.batteries)
    rating = sum(b.discharge_limit_kw for b in portfolio.batteries)
    with st.container(horizontal=True, gap="medium"):
        st.metric("Configured assets", len(portfolio.batteries), width="content")
        st.metric("Installed capacity", f"{capacity:g} kWh", width="content")
        st.metric("Rated discharge power", f"{rating:g} kW", width="content")
        st.metric("Historical events", len(events), width="content")
        st.metric("Dispatch strategies", len(METHODS), width="content")
    st.divider()
    st.subheader("From demand evidence to dispatch decisions")
    st.write(
        "Explore historical NESO event requirements and household demand, qualify battery assets, "
        "then compare a forecast-based dispatch plan with historical replay. Persistent results "
        "support repeatable operational and economic evaluation."
    )
    st.subheader("System architecture")
    st.image(
        diagram,
        width="stretch",
        alt="Three layers linking NESO, BatteryFlex and residential assets",
    )
    _show_benchmark(repository, events, config.precision)
    st.subheader("Prototype scope")
    st.write(
        "BatteryFlex is a simulation and decision-support MVP using historical data and "
        "configurable battery assets. The architecture provides a foundation for live "
        "telemetry, flexibility market integration and uncertainty-aware dispatch."
    )
