"""Saved-only, scenario-compatible controller benchmarks."""

from collections import defaultdict
from typing import cast

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from batteryflex.dispatch import DT, METHODS
from batteryflex.dispatch_dashboard import event_outcome
from batteryflex.dispatch_evaluation import constraint_violations
from batteryflex.neso_manifest import load_selection
from batteryflex.storage.dispatch_runs import (
    comparison_identity,
    comparison_payload,
    discover_runs,
    scenario_from_result,
)
from batteryflex.storage.objects import sha256
from batteryflex.storage.repository import Repository, canonical
from batteryflex.storage.settings import Settings
from batteryflex.ui.dispatch_overview import COLORS, TRAJECTORIES, grouped_bars, render_overview
from batteryflex.ui.dispatch_results import render_event_steps


@st.cache_data(
    ttl=30, max_entries=2, scope="session", show_spinner="Checking saved dispatch coverage…"
)
def _read_benchmarks(settings: Settings, _repo: Repository) -> tuple[list[dict], list[dict]]:
    issues: list[dict] = []
    results, _ = discover_runs(_repo, standard_only=True, issues=issues)
    return results, issues


def saved_benchmarks(repo: Repository) -> tuple[list[dict], list[dict]]:
    return _read_benchmarks(Settings.load(), repo)


def refresh_saved_benchmarks() -> None:
    _read_benchmarks.clear()


def grouped_runs(results: list[dict]) -> dict[str, dict[str, dict]]:
    groups: dict[str, dict[str, dict]] = defaultdict(dict)
    for result in sorted(results, key=lambda r: r.get("created_at", ""), reverse=True):
        groups[comparison_identity(result["provenance"])].setdefault(result["method"], result)
    return dict(groups)


def _bars(frame: pd.DataFrame, x: str, y: str, *, labels: bool = False):
    chart = alt.Chart(frame).encode(
        x=alt.X(f"{x}:N", sort=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Controller:N", sort=list(METHODS)),
        y=alt.Y(f"{y}:Q", title=y),
        color=alt.Color("Controller:N", scale=alt.Scale(domain=list(METHODS), range=COLORS)),
        tooltip=list(frame.columns),
    )
    bars = cast(alt.Chart, chart.mark_bar())
    if labels:
        text = cast(alt.Chart, chart.mark_text(dy=-8)).encode(text=alt.Text(f"{y}:Q", format=".2f"))
        return alt.layer(bars, text)
    return bars


def _trajectory_chart(container, frame: pd.DataFrame, measure: str) -> None:
    time_type = "temporal" if pd.api.types.is_datetime64_any_dtype(frame["Time"]) else "ordinal"
    chart = cast(alt.Chart, alt.Chart(frame).mark_line(point=True)).encode(
        x=alt.X("Time", type=time_type, sort=None),
        y=alt.Y(field=measure, type="quantitative"),
        color=alt.Color("Controller:N", scale=alt.Scale(domain=list(METHODS), range=COLORS)),
        tooltip=["Time", "Controller", alt.Tooltip(field=measure, type="quantitative")],
    )
    container.altair_chart(chart, width="stretch")


def five_event_families(groups: dict[str, dict[str, dict]]) -> dict[str, list[dict[str, dict]]]:
    """Group per-event compatible benchmarks by common non-event settings."""
    per_event = {
        "event_id",
        "event_source_hash",
        "original_event_date",
        "original_event_start",
        "original_event_end",
        "replay_date",
        "forecast_origin",
        "request_id",
        "fingerprint",
        "artifact_id",
        "predictions_id",
        "model_version",
    }
    families: dict[str, list[dict[str, dict]]] = defaultdict(list)
    for group in groups.values():
        first = next(iter(group.values()))
        payload = comparison_payload(first["provenance"])
        payload["scenario"].pop("event_steps")
        payload.pop("evaluation_steps", None)  # Derived from the selected event duration.
        payload["inputs"] = {k: v for k, v in payload["inputs"].items() if k not in per_event}
        key = sha256(canonical(payload).encode())
        families[key].append(group)
    return dict(families)


def _choose_family(groups: dict, events: list[dict]) -> tuple[dict, object]:
    if not groups:
        return {}, None
    families = sorted(
        five_event_families(groups).values(),
        key=lambda family: (
            -sum(
                max(
                    len(g)
                    for g in family
                    if next(iter(g.values()))["provenance"]["inputs"]["event_id"] == event_id
                )
                for event_id in {
                    next(iter(g.values()))["provenance"]["inputs"]["event_id"] for g in family
                }
            )
        ),
    )

    def label(i):
        run = next(iter(families[i][0].values()))
        s = scenario_from_result(run)
        algorithm = run["provenance"]["inputs"].get("algorithm", "Forecast")
        return (
            f"{i + 1} · {algorithm} · {s.target_kw:g} kW · {s.target_type} · "
            f"terminal £{s.terminal_price:.2f}/kWh"
        )

    selected = st.selectbox("Compatible settings", range(len(families)), format_func=label)
    family = families[selected]
    by_event = defaultdict(list)
    for runs in family:
        by_event[next(iter(runs.values()))["provenance"]["inputs"]["event_id"]].append(runs)
    matched = {}
    for e in events:
        identity = e["internal_scenario_id"]
        options = sorted(by_event[identity], key=len, reverse=True)
        if options:
            i = 0
            if len(options) > 1:
                i = st.selectbox(
                    f"Forecast snapshot for {e['delivery_date']}",
                    range(len(options)),
                    format_func=lambda i, options=options: f"{i + 1} · {', '.join(options[i])}",
                    key=f"comparison_snapshot_{identity}",
                )
            matched[identity] = options[i]
    return matched, scenario_from_result(next(iter(family[0].values())))


def _coverage(events: list[dict], matched: dict, all_runs: list, issues: list) -> None:
    valid = {(r["provenance"]["inputs"]["event_id"], r["method"]) for r in all_runs}
    invalid = {(i.get("inputs", {}).get("event_id"), i.get("method")) for i in issues}
    rows = []
    for event in events:
        k = event["internal_scenario_id"]
        rows.append(
            {
                "Event": str(event["delivery_date"]),
                **{
                    method: (
                        "Saved"
                        if method in matched.get(k, {})
                        else "Incompatible"
                        if (k, method) in valid
                        else "Invalid or unverified"
                        if (k, method) in invalid
                        else "Missing"
                    )
                    for method in METHODS
                },
            }
        )
    count = sum(row[m] == "Saved" for row in rows for m in METHODS)
    st.metric("Available compatible scenarios", f"{count} / {len(events) * len(METHODS)}")
    st.dataframe(
        pd.DataFrame(rows), hide_index=True, alt="Saved result coverage by event and method"
    )
    missing = [m for m in METHODS if any(row[m] != "Saved" for row in rows)]
    if missing:
        st.caption(
            "To fill missing compatible results, run the five-event batch for "
            + ", ".join(missing)
            + " using these shared settings. Unverified storage may require a retry."
        )


def render_comparison(repo: Repository | None) -> None:
    st.subheader("Saved dispatch performance")
    if repo is None:
        st.info("No completed simulation runs to compare.")
        return
    try:
        results, issues = saved_benchmarks(repo)
        groups = grouped_runs(results)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError):
        st.error("Saved comparisons could not be loaded. Check the simulation storage connection.")
        return
    if issues:
        st.warning(f"{len(issues)} saved references could not be verified. They are excluded.")
    events = load_selection()[0]
    scope = st.radio(
        "Comparison scope",
        ["All Five Events", "Individual Event"],
        horizontal=True,
        key="dispatch_comparison_scope",
    )
    selected, scenario = _choose_family(groups, events)
    _coverage(events, selected, results, issues)
    if not selected:
        st.info("No completed simulation runs to compare.")
    trajectory = st.radio(
        "Trajectory",
        ["realized", "planned"],
        format_func=TRAJECTORIES.__getitem__,
        horizontal=True,
        key="comparison_trajectory",
    )
    if scope == "All Five Events":
        render_overview(selected, events, trajectory, scenario)
        return
    by_id = {str(e["delivery_date"]): e for e in events}
    date = st.selectbox("NESO event", sorted(by_id), key="dispatch_comparison_event")
    runs = selected.get(by_id[date]["internal_scenario_id"], {})
    if not runs:
        st.table(
            pd.DataFrame([{"Controller": m, "Status": "Missing"} for m in METHODS]), hide_index=True
        )
        return
    first = next(iter(runs.values()))
    s = scenario_from_result(first)
    st.caption(
        " · ".join(
            f"{method} {'available' if method in runs else 'Not yet executed'}"
            for method in METHODS
        )
    )
    if len(runs) == 1:
        st.caption("Only one controller has a saved result under these shared settings.")
    choices = ["planned", "realized"] if first.get("realized") is not None else ["planned"]
    summary, objectives, delivery, soc = [], [], [], []
    selected_rows = []
    event = list(s.event_steps)
    capacity = sum(b.capacity_kwh for b in s.batteries)
    times = pd.date_range(
        first["provenance"]["inputs"]["original_event_start"], periods=s.steps, freq="30min"
    )
    for method in METHODS:
        if method not in runs:
            continue
        run = runs[method]
        for key in choices:
            data = run[key]
            try:
                violations = constraint_violations(s, data)
            except (ValueError, KeyError, TypeError):
                st.warning(f"{method} {TRAJECTORIES[key]} could not be verified and is excluded.")
                continue
            outcome = event_outcome(s, data)
            target = outcome.delivered_kw
            gaps = np.maximum(0, outcome.requested_kw - target)
            status = outcome.status
            trace = run.get("planned_trace" if key == "planned" else "realized_trace") or []
            solver_time = [step["runtime_seconds"] for step in trace if "solver_code" in step]
            penalties = data["weighted_terms"]
            exported = sum(data["portfolio_export_kw"][step] for step in event) * DT
            summary.append(
                {
                    "Controller": method,
                    "Trajectory": TRAJECTORIES[key],
                    "Fulfilment check": status,
                    "Requested (kWh)": outcome.requested_kwh,
                    "Delivery (kWh)": data["delivered_kwh"],
                    "Failed intervals": len(outcome.failed_steps),
                    "Throughput (kWh)": data["throughput_kwh"],
                    "Executed steps": s.steps,
                    "Optimisation solves": len(solver_time) or int(method == "MILP"),
                    "Weighted electricity (£)": penalties[0],
                    "Event shortfall (kWh)": outcome.shortfall_kwh,
                    "Credited fulfilment (%)": outcome.fulfilment_pct,
                    "Event export (kWh)": exported,
                    "Net electricity (£)": data["cost_gbp"],
                    "Shortfall penalty (£)": penalties[1],
                    "Degradation (£)": penalties[2],
                    "Terminal penalty (£)": penalties[3],
                    "Weighted objective (£)": data["objective"],
                    "Final stored (kWh)": data["remaining_kwh"],
                    "Final SoC (%)": 100 * data["remaining_kwh"] / capacity,
                    "Violations": ", ".join(violations) or "None",
                    "Solver time (s)": sum(solver_time) if solver_time else None,
                }
            )
            if key != trajectory:
                continue
            selected_rows.append(summary[-1])
            if not violations:
                objectives.append(
                    {
                        "Controller": method,
                        "Run": TRAJECTORIES[key],
                        "Weighted objective (£)": data["objective"],
                    }
                )
            for i, step in enumerate(event):
                delivery.append(
                    {
                        "Controller": method,
                        "Event interval (GMT)": times[step].strftime("%H:%M"),
                        "Delivered power (kW)": float(target[i]),
                        "kW shortfall": float(gaps[i]),
                        "Requested (kW)": s.target_kw,
                    }
                )
            for battery in data["households"]:
                soc.append(
                    {
                        "Controller": method,
                        "Household": battery["household"],
                        "Final SoC (%)": battery["final_soc_pct"],
                    }
                )

    st.subheader("Overall Three-Method Comparison")
    by_method = {row["Controller"]: row for row in selected_rows}
    fields = (
        [k for k in selected_rows[0] if k not in {"Controller", "Trajectory"}]
        if selected_rows
        else []
    )
    st.table(
        pd.DataFrame(
            {
                "Metric": fields,
                **{
                    method: [
                        str(round(by_method[method][k], 4))
                        if isinstance(by_method[method][k], float)
                        else str(by_method[method][k])
                        for k in fields
                    ]
                    if method in by_method
                    else ["Not yet executed"] * len(fields)
                    for method in METHODS
                },
            }
        ),
        hide_index=True,
    )
    start, end = times[0], pd.Timestamp(first["provenance"]["inputs"]["original_event_end"])
    st.caption(f"{date} · {start:%H:%M}–{end:%H:%M} GMT · {s.steps * DT:g} h · {s.target_kw:g} kW")
    st.caption(
        "Initial SoC · " + ", ".join(f"{b.household_id} {b.initial_soc:.0%}" for b in s.batteries)
    )
    st.subheader("Request Fulfilment Comparison")
    totals = [
        {"Controller": key, "Event energy (kWh)": row["Delivery (kWh)"]}
        for key, row in by_method.items()
    ]
    if totals:
        totals.append({"Controller": "Requested", "Event energy (kWh)": s.target_kw * s.steps * DT})
        grouped_bars(
            pd.DataFrame([{**row, "Event": date} for row in totals]), "Event", "Event energy (kWh)"
        )
    st.subheader("Objective Function Comparison")
    fields = [
        "Weighted electricity (£)",
        "Shortfall penalty (£)",
        "Degradation (£)",
        "Terminal penalty (£)",
    ]
    if selected_rows:
        grouped_bars(
            pd.DataFrame(selected_rows)[["Controller", *fields]].melt(
                "Controller", var_name="Component", value_name="Simulated cost (£)"
            ),
            "Component",
            "Simulated cost (£)",
        )
    st.markdown("**Total simulated weighted objective**")
    st.caption(
        "Lower objective is better under the configured weights. Only feasible runs are ranked."
    )
    if objectives:
        st.altair_chart(
            _bars(pd.DataFrame(objectives), "Run", "Weighted objective (£)", labels=True),
            alt="Weighted objective by feasible controller",
        )
    if delivery:
        st.markdown("**Event flexibility delivery**")
        st.caption(
            "The line is the interval minimum or energy reference. Tooltips show power gaps."
        )
        target_line = cast(
            alt.Chart,
            alt.Chart(pd.DataFrame({"Target": [s.target_kw]})).mark_rule(
                color="#6b7280", strokeDash=[5, 4]
            ),
        ).encode(y="Target:Q")
        st.altair_chart(
            alt.layer(
                _bars(pd.DataFrame(delivery), "Event interval (GMT)", "Delivered power (kW)"),
                target_line,
            ),
            alt="Delivered power and requested reference for every event interval",
        )
    if soc:
        st.markdown("**Final battery SoC**")
        st.caption(
            f"Dashed lines show the {s.reserve_soc:.0%} hard final reserve and the "
            f"{s.target_soc:.0%} preferred soft target."
        )
        rules = cast(
            alt.Chart,
            alt.Chart(
                pd.DataFrame({"Reference": [100 * s.reserve_soc, 100 * s.target_soc]})
            ).mark_rule(color="#6b7280", strokeDash=[5, 4]),
        ).encode(y="Reference:Q")
        st.altair_chart(
            alt.layer(_bars(pd.DataFrame(soc), "Household", "Final SoC (%)"), rules),
            alt="Final battery state of charge with reserve and target",
        )
    if summary:
        st.dataframe(
            pd.DataFrame(summary).round(3),
            hide_index=True,
            alt="Saved controller metrics for planned and replay trajectories",
        )
    st.markdown("**Household supply and grid export**")
    allocation = [
        {"Controller": method, "Allocation": caption, "Energy (kWh)": run[trajectory][field]}
        for method, run in runs.items()
        for caption, field in (("Used at home", "supplied_kwh"), ("Exported", "export_kwh"))
    ]
    grouped_bars(pd.DataFrame(allocation), "Allocation", "Energy (kWh)")
    _event_comparison_details(runs, trajectory, times)
    st.subheader("Performance Conclusions")
    feasible = [row for row in selected_rows if row["Violations"] == "None"]
    if feasible:
        lean = min(feasible, key=lambda row: row["Throughput (kWh)"])
        st.write(
            f"Lowest battery throughput was {lean['Throughput (kWh)']:.2f} kWh "
            f"({lean['Controller']})."
        )
    for method, run in runs.items():
        evidence = run.get("explanations", {}).get(trajectory, {})
        if evidence.get("status") == "NOT MET":
            verified = sorted(
                {
                    clue
                    for item in evidence.get("diagnostics", {}).values()
                    for clue in item.get("verified", [])
                }
            )
            st.write(
                f"{method} missed the request. " + " ".join(verified)
                if verified
                else f"{method} missed the request. The exact cause was unconfirmed."
            )
    if "MPC" in runs and "MILP" in runs:
        mpc, milp = runs["MPC"], runs["MILP"]
        target_trace = mpc["realized_trace"] if trajectory == "realized" else mpc["planned_trace"]
        changes = 0
        for previous, current in zip(target_trace, target_trace[1:], strict=False):
            a = previous["predicted_net_battery_kw"][1:]
            b = current["predicted_net_battery_kw"]
            count = min(len(a), len(b))
            if count and not np.allclose(a[:count], b[:count], atol=1e-6, rtol=0):
                changes += 1
        difference = mpc[trajectory]["objective"] - milp[trajectory]["objective"]
        st.write(
            f"MPC changed overlapping forecast actions at {changes} updates. The objective "
            f"difference from standalone MILP was £{difference:+.4f} for "
            f"{TRAJECTORIES[trajectory]}. "
            "With an unchanged forecast and a horizon covering the remaining event, "
            "similar objectives are expected when execution produces the same states."
        )
    if len(feasible) >= 2:
        ranked = sorted(feasible, key=lambda row: row["Weighted objective (£)"])
        best, other = ranked[0], ranked[1]
        met = ", ".join(row["Controller"] for row in feasible if row["Fulfilment check"] == "MET")
        score = (
            f"{best['Controller']} and {other['Controller']} tied on the displayed objective."
            if abs(best["Weighted objective (£)"] - other["Weighted objective (£)"]) < 0.005
            else f"{best['Controller']} had the lowest weighted objective under these settings."
        )
        match = (
            f"{met} met the configured request." if met else "No feasible method met the request."
        )
        st.write(
            f"{match} {score} {best['Controller']}'s net electricity cost was "
            f"£{best['Net electricity (£)']:.2f}, "
            f"weighted degradation £{best['Degradation (£)']:.2f} and final stored energy "
            f"{best['Final stored (kWh)']:.2f} kWh. The same values for {other['Controller']} "
            f"were £{other['Net electricity (£)']:.2f}, £{other['Degradation (£)']:.2f} and "
            f"{other['Final stored (kWh)']:.2f} kWh."
        )


def _event_comparison_details(runs: dict, slot: str, times: pd.DatetimeIndex) -> None:
    trajectory_rows, execution, computation = [], [], []
    battery_rows, battery_power = [], []
    names = [b.household_id for b in scenario_from_result(next(iter(runs.values()))).batteries]
    for method, run in runs.items():
        s = scenario_from_result(run)
        data = run[slot]
        records = run["execution_records"][slot]
        trace = (
            run["planned_trace"] if slot == "planned" or method == "MILP" else run["realized_trace"]
        )
        solves = [row for row in trace if "solver_code" in row]
        solver_times = [row["runtime_seconds"] for row in solves]
        computation.append(
            {
                "Controller": method,
                "Rule decisions": s.steps if method == "RBC" else 0,
                "Executed steps": s.steps,
                "Solver calls": len(solves),
                "Solver total (s)": sum(solver_times),
                "Solver mean (s)": np.mean(solver_times) if solves else 0,
                "Solver max (s)": max(solver_times, default=0),
                "Retries": 0,
                "Status": ", ".join(sorted({row["status"] for row in solves})) or "Rules executed",
                "Controller total (s)": (
                    run["runtime_seconds"] if method == "MILP" else run["trajectory_seconds"][slot]
                ),
                "Qualification (s)": run["qualification"]["qualification_seconds"],
            }
        )
        cap = sum(b.capacity_kwh for b in s.batteries)
        for i, stamp in enumerate(
            times.append(pd.DatetimeIndex([times[-1] + pd.Timedelta(minutes=30)]))
        ):
            energy = sum(data["energy_kwh"][i])
            trajectory_rows.append(
                {
                    "Controller": method,
                    "Time": stamp,
                    "Stored energy (kWh)": energy,
                    "Portfolio SoC (%)": 100 * energy / cap,
                }
            )
        for row in records:
            execution.append(
                {
                    "Controller": method,
                    "Time": pd.Timestamp(row["timestamp"]).strftime("%H:%M"),
                    "Requested (kW)": row["request_kw"],
                    "Delivered (kW)": row["delivery_kw"],
                    "Charge (kW)": sum(row["charge_kw"]),
                    "Discharge (kW)": sum(row["discharge_kw"]),
                    "Stored (kWh)": sum(row["energy_after_kwh"]),
                    "Interval cost (£)": row["stage_cost"],
                    "Running cost (£)": row["cumulative_running_cost"],
                    "Prediction steps": row.get("horizon_steps"),
                    "Predicted objective (£)": row.get("solver_objective"),
                    **dict(
                        zip(
                            ("Energy (£)", "Shortfall (£)", "Degradation (£)", "Terminal (£)"),
                            row["weighted_interval_costs"],
                            strict=True,
                        )
                    ),
                }
            )
    st.subheader("Battery Dispatch Comparison")
    frame = pd.DataFrame(trajectory_rows)
    a, b = st.columns(2)
    _trajectory_chart(a, frame, "Stored energy (kWh)")
    _trajectory_chart(b, frame, "Portfolio SoC (%)")
    steps = pd.DataFrame(execution)
    a, b = st.columns(2)
    _trajectory_chart(a, steps, "Charge (kW)")
    _trajectory_chart(b, steps, "Discharge (kW)")
    battery = st.selectbox("Compare individual battery", names, key="compare_event_household")
    idx = names.index(battery)
    for method, run in runs.items():
        data = run[slot]
        capacity = scenario_from_result(run).batteries[idx].capacity_kwh
        end = times[-1] + pd.Timedelta(minutes=30)
        for t, energy in zip([*times, end], data["energy_kwh"], strict=True):
            battery_rows.append(
                {"Time": t, "Controller": method, "SoC (%)": 100 * energy[idx] / capacity}
            )
        for t, charge, discharge in zip(
            times, data["charge_kw"], data["discharge_kw"], strict=True
        ):
            battery_power.append(
                {"Time": t, "Controller": method, "Net power (kW)": charge[idx] - discharge[idx]}
            )
    a, b = st.columns(2)
    _trajectory_chart(a, pd.DataFrame(battery_rows), "SoC (%)")
    _trajectory_chart(b, pd.DataFrame(battery_power), "Net power (kW)")
    st.caption(
        "For the selected battery, positive net power means charging and negative means discharge."
    )
    st.subheader("Step-by-Step Control and Optimisation Comparison")
    st.dataframe(steps.round(4), hide_index=True)
    _trajectory_chart(st, steps, "Running cost (£)")
    with st.expander("Inspect controller and individual battery actions"):
        method = st.selectbox("Controller detail", list(runs))
        run = runs[method]
        render_event_steps(run, scenario_from_result(run), widget_key="comparison")
    st.subheader("Computational Performance")
    st.dataframe(pd.DataFrame(computation).round(5), hide_index=True)
    st.caption(
        "Standalone MILP's original solve is included once. Qualification is reported separately."
    )
