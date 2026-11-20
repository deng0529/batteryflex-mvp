"""Saved five-event metrics, coverage, and explanatory comparisons."""

from typing import cast

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from batteryflex.dispatch import DT, METHODS
from batteryflex.dispatch_dashboard import event_outcome
from batteryflex.dispatch_event import event_evidence
from batteryflex.storage.dispatch_runs import scenario_from_result

COLORS = ["#3167b8", "#008174", "#9c5810"]
COSTS = [
    "Weighted electricity (£)",
    "Shortfall penalty (£)",
    "Degradation (£)",
    "Terminal deficit (£)",
]
ENERGY = [
    "Charge (kWh)",
    "Discharge (kWh)",
    "Throughput (kWh)",
    "Battery supply (kWh)",
    "Household import (kWh)",
    "Grid export (kWh)",
]
TRAJECTORIES = {"planned": "Forecast-Based Dispatch Plan", "realized": "Historical Replay"}


def grouped_bars(data, category: str, measure: str, *, order: list[str] | None = None) -> None:
    keys = ["Requested", *METHODS] if "Requested" in data["Controller"].values else list(METHODS)
    palette = ["#818b98", *COLORS] if keys[0] == "Requested" else COLORS
    chart = cast(alt.Chart, alt.Chart(data).mark_bar()).encode(
        x=alt.X(field=category, type="nominal", sort=order, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Controller:N", sort=keys),
        y=alt.Y(field=measure, type="quantitative"),
        color=alt.Color("Controller:N", scale=alt.Scale(domain=keys, range=palette)),
        tooltip=[alt.Tooltip(field=column) for column in data.columns],
    )
    st.altair_chart(chart.properties(height=220), width="stretch", alt=f"{measure} by {category}")


def run_row(run: dict, slot: str) -> dict:
    s = scenario_from_result(run)
    data = run[slot]
    outcome = event_outcome(s, data)
    planned = run["planned_trace"]
    trace = planned if slot == "planned" else run["realized_trace"]
    shared = run["method"] == "MILP"
    solver = [step for step in (planned if shared else trace) if "solver_code" in step]
    return {
        "Controller": run["method"],
        "Requested (kWh)": outcome.requested_kwh,
        "Delivered (kWh)": outcome.delivered_kwh,
        "Fulfilment": outcome.status,
        "Failed intervals": len(outcome.failed_steps),
        "Simulated objective (£)": data["objective"],
        **dict(zip(COSTS, data["weighted_terms"], strict=True)),
        **dict(
            zip(
                ENERGY,
                [
                    data["charged_kwh"],
                    data["discharged_kwh"],
                    data["throughput_kwh"],
                    data["supplied_kwh"],
                    data["import_kwh"],
                    data["export_kwh"],
                ],
                strict=True,
            )
        ),
        "Optimisation solves": len(solver),
        "Both phases solves": run["solver_iterations"],
        "Controller (s)": run["runtime_seconds"] if shared else run["trajectory_seconds"][slot],
        "Solver (s)": sum(step["runtime_seconds"] for step in solver),
        "Qualification (s)": run["qualification"]["qualification_seconds"],
    }


def _leaders(values: pd.Series) -> str:
    minimum = values.min()
    return ", ".join(str(m) for m, v in values.items() if np.isclose(v, minimum, atol=1e-6, rtol=0))


def render_overview(selected: dict, events: list[dict], slot: str, scenario) -> None:
    rows, intervals, targets, misses = [], [], [], []
    labels = []
    for event in events:
        date = str(event["delivery_date"])
        event_id = event["internal_scenario_id"]
        hours = event["duration_minutes"] / 60
        label = f"{date} · {hours:g} h"
        labels.append(label)
        by_method = selected.get(event_id, {})
        if scenario is not None:
            targets.append(
                {
                    "Event": label,
                    "Controller": "Requested",
                    "Delivered (kWh)": scenario.target_kw * hours,
                }
            )
        for method, run in by_method.items():
            rows.append({"Event": label, **run_row(run, slot)})
            s = scenario_from_result(run)
            outcome = event_outcome(s, run[slot])
            start = pd.Timestamp(run["provenance"]["inputs"]["original_event_start"])
            for i, (req, actual) in enumerate(
                zip(outcome.requested_kw, outcome.delivered_kw, strict=True)
            ):
                intervals.append(
                    {
                        "Event": label,
                        "Controller": method,
                        "Half-hour (GMT)": (start + pd.Timedelta(hours=DT * i)).strftime("%H:%M"),
                        "Request (kW)": req,
                        "Delivered (kW)": actual,
                        "Check": "Energy target"
                        if s.target_type == "energy"
                        else ("NOT MET" if outcome.steps[i] in outcome.failed_steps else "MET")
                        if outcome.requested_kwh > 0
                        else "Not assessable",
                    }
                )
            if outcome.status == "NOT MET":
                evidence = event_evidence(run, s, run["provenance"]["inputs"])["explanations"][slot]
                clues = sorted(
                    {note for item in evidence["diagnostics"].values() for note in item["verified"]}
                )
                misses.append(
                    f"{date} · {method}: "
                    + (" ".join(clues) if clues else "No limiting constraint could be confirmed.")
                )
    st.subheader("Flexibility fulfilment")
    data = pd.DataFrame(rows)
    for col, method in zip(st.columns(3), METHODS, strict=True):
        subset = [row for row in rows if row["Controller"] == method]
        col.metric(method, f"{sum(row['Fulfilment'] == 'MET' for row in subset)}/{len(subset)} MET")
        col.caption(f"{len(subset)}/5 events available")
    if not rows:
        return
    grouped_bars(
        pd.concat([pd.DataFrame(targets), data[["Event", "Controller", "Delivered (kWh)"]]]),
        "Event",
        "Delivered (kWh)",
        order=labels,
    )
    st.dataframe(
        data.pivot(index="Event", columns="Controller", values="Fulfilment")
        .reindex(index=labels, columns=METHODS)
        .fillna("—"),
        alt="Event fulfilment by method",
    )
    with st.expander("Half-hour fulfilment checks"):
        st.dataframe(pd.DataFrame(intervals).round(4), hide_index=True)
    for miss in misses:
        st.caption(miss)
    st.subheader("Simulated objective")
    grouped_bars(
        data[["Event", "Controller", "Simulated objective (£)"]],
        "Event",
        "Simulated objective (£)",
        order=labels,
    )
    totals = data.groupby("Controller", sort=False).sum(numeric_only=True)
    complete = [method for method in METHODS if sum(data["Controller"] == method) == len(events)]
    for event, group in data.groupby("Event", sort=False):
        if len(group) > 1:
            values = group.set_index("Controller")["Simulated objective (£)"]
            spread = values.max() - values.min()
            st.caption(
                f"{event} · lowest saved objective {_leaders(values)} · spread £{spread:.4f}."
            )
    if complete:
        full = totals.loc[complete].reset_index()
        full["Scope"] = "Five independent events"
        grouped_bars(
            full[["Controller", "Scope", "Simulated objective (£)"]],
            "Scope",
            "Simulated objective (£)",
        )
    else:
        st.info("No controller has a complete five-event objective total for these settings.")
    st.subheader("Simulated objective components")
    if complete:
        for metrics, name, heading in (
            (COSTS, "Weighted cost (£)", None),
            (ENERGY, "Energy (kWh)", "Battery energy allocation"),
        ):
            if heading:
                st.subheader(heading)
            melted = full[["Controller", *metrics]].melt(
                "Controller", var_name="Metric", value_name=name
            )
            grouped_bars(melted, "Metric", name)
        st.dataframe(full[["Controller", *COSTS, *ENERGY]].round(4), hide_index=True)
    else:
        st.subheader("Battery energy allocation")
        st.caption("Five-event component and allocation totals require complete saved coverage.")
    st.subheader("Computational performance")
    grouped_bars(
        data[["Event", "Controller", "Optimisation solves"]],
        "Event",
        "Optimisation solves",
        order=labels,
    )
    timing = [
        "Optimisation solves",
        "Both phases solves",
        "Controller (s)",
        "Solver (s)",
        "Qualification (s)",
    ]
    totals["Available events"] = data.groupby("Controller").size()
    st.dataframe(totals[["Available events", *timing]].round(4))
    st.caption(
        "Timings sum stored executions for available events. Qualification is separate. "
        "MILP includes one shared initial solve in replay when recorded."
    )
    st.subheader("Overall conclusion")
    if len(complete) < len(METHODS):
        st.write(
            "A three-method conclusion requires complete compatible coverage for all five events."
        )
        return
    score = totals["Simulated objective (£)"]
    spread = score.max() - score.min()
    st.write(
        f"{_leaders(score)} had the lowest simulated total objective across the five events "
        f"(£{score.min():.4f}, with £{spread:.4f} between lowest and highest). "
        + (
            "Every saved run met its request."
            if data["Fulfilment"].eq("MET").all()
            else "Fulfilment varies across saved events. Check the half-hour results above."
        )
    )
    st.write(
        f"Lowest throughput: {_leaders(totals['Throughput (kWh)'])}. "
        f"Lowest degradation: {_leaders(totals['Degradation (£)'])}. "
        f"Shortest stored controller time: {_leaders(totals['Controller (s)'])}."
    )
    best, worst = score.idxmin(), score.idxmax()
    if best != worst:
        delta = totals.loc[worst, COSTS] - totals.loc[best, COSTS]
        parts = ", ".join(
            f"{key.split(' (£)')[0].lower()} {value:+.4f}" for key, value in delta.items()
        )
        import_delta = (
            totals.loc[worst, "Household import (kWh)"] - totals.loc[best, "Household import (kWh)"]
        )
        export_delta = (
            totals.loc[worst, "Grid export (kWh)"] - totals.loc[best, "Grid export (kWh)"]
        )
        st.caption(
            f"{worst} minus {best} in weighted GBP: {parts}. "
            f"Import difference {import_delta:+.3f} kWh; export difference {export_delta:+.3f} kWh."
        )
    st.write(
        "MPC had a lower total objective than both alternatives in this saved set."
        if score["MPC"] < min(score["RBC"], score["MILP"]) - 1e-6
        else "MPC did not lower the total objective relative to both alternatives in these runs."
    )
