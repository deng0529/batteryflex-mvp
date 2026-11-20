"""Results-first presentation of saved planned and replay dispatch."""

from collections.abc import Callable
from typing import cast

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from batteryflex.dispatch import DT, EPS, Scenario
from batteryflex.dispatch_comparison import replay_evidence
from batteryflex.dispatch_dashboard import EventOutcome, diagnose_interval, event_outcome
from batteryflex.dispatch_evaluation import control_rows, objective_steps
from batteryflex.dispatch_event import EXPLANATION_VERSION, event_evidence

PLAN = "Forecast-Based Dispatch Plan"
REPLAY = "Historical Replay"
REQUEST = "Requested minimum"
METHOD_REPLAY = {
    "RBC": "RBC applies its rules using current measured demand and battery state.",
    "MPC": "MPC updates its rolling plan using current measured demand and battery state.",
    "MILP": "MILP reuses its day-ahead schedule with battery, grid and export corrections.",
}


def conclusion(result: dict, data: dict, timeline: pd.DatetimeIndex, s: Scenario) -> str:
    active = [name for name, count in data["binding_counts"].items() if count]
    trajectory = result["realized_trace"] if data is result["realized"] else result["planned_trace"]
    adjusted = sum(bool(row.get("constrained_households")) for row in trajectory)
    missed = [
        f"{timeline[k]:%H:%M}" for k in s.event_steps if data["flex_kw"][k] < s.target_kw - EPS
    ]
    reason = f" Intervals below the reference (GMT) {', '.join(missed)}." if missed else ""
    if s.target_kw > 0 and not any(b.export_enabled for b in s.batteries):
        load_ceiling = np.asarray(data["load_kw"])[list(s.event_steps)].sum(axis=1)
        insufficient = int((load_ceiling < s.target_kw - EPS).sum())
        if insufficient:
            reason += (
                f"With export disabled, household demand capped reduction below the kW "
                f"reference in {insufficient} of {len(s.event_steps)} event intervals."
            )
    boundaries = ", ".join(active) if active else "none observed"
    return (
        f"{data['status']} for the configured portfolio target. Event discharge less charging "
        f"delivered {data['delivered_kwh']:.2f} kWh with {data['shortfall_kwh']:.2f} kWh of "
        f"shortfall and {data['surplus_kwh']:.2f} kWh above the applicable target.{reason} "
        f"Grid export was {data['export_kwh']:.2f} kWh. Electricity cost £{data['cost_gbp']:.2f} "
        f"and savings versus uncontrolled demand £{data['savings_gbp']:.2f}. "
        f"Observed active boundaries were {boundaries}. "
        f"Physical or connection limits adjusted the requested action in {adjusted} intervals. "
        f"{result['solver_status']} and the simulated trajectory satisfied the hard constraints."
    )


def _event_delivery(result: dict, timeline: pd.DatetimeIndex, s: Scenario) -> pd.DataFrame:
    """Show power against the configured reference independently of energy-mode scoring."""
    steps = list(s.event_steps)
    rows = pd.DataFrame(
        {
            "Interval (GMT)": timeline[steps].strftime("%H:%M"),
            REQUEST: event_outcome(s, result["planned"]).requested_kw,
            PLAN: np.asarray(result["planned"]["flex_kw"])[steps],
            REPLAY: np.asarray(result["realized"]["flex_kw"])[steps]
            if result["realized"]
            else np.nan,
        }
    )
    return rows


def _power_check(kw: pd.Series, target_kw: float) -> tuple[str, int, float]:
    if target_kw <= 0:
        return "NOT ASSESSABLE", 0, 0.0
    deficit = target_kw - kw
    met = int((deficit <= EPS).sum())
    shortfall = float(deficit.where(deficit > EPS, 0).sum() * DT)
    return ("MET" if met == len(kw) else "NOT MET"), met, shortfall


def _event_chart(delivery: pd.DataFrame, outcome: EventOutcome, label: str) -> None:
    series = [REQUEST, PLAN, REPLAY] if delivery[REPLAY].notna().any() else [REQUEST, label]
    values = delivery.melt("Interval (GMT)", value_vars=series, var_name="Series", value_name="kW")
    failed = {
        time
        for step, time in zip(outcome.steps, delivery["Interval (GMT)"], strict=True)
        if step in outcome.failed_steps
    }
    values["Key"] = [
        "Missed interval" if name == label and time in failed else name
        for name, time in zip(values["Series"], values["Interval (GMT)"], strict=True)
    ]
    chart = cast(alt.Chart, alt.Chart(values).mark_bar()).encode(
        x=alt.X(
            "Interval (GMT):N",
            sort=delivery["Interval (GMT)"].tolist(),
            axis=alt.Axis(labelAngle=0),
        ),
        xOffset=alt.XOffset("Series:N", sort=series),
        y=alt.Y("kW:Q", title="Power (kW)"),
        color=alt.Color(
            "Key:N",
            title=None,
            scale=alt.Scale(
                domain=[REQUEST, PLAN, REPLAY, "Missed interval"],
                range=["#7d8793", "#3167b8", "#008174", "#b94b36"],
            ),
            legend=alt.Legend(orient="bottom", labelLimit=230, columns=2),
        ),
        tooltip=["Interval (GMT):N", "Key:N", alt.Tooltip("kW:Q", format=".3f")],
    )
    misses = values[values["Key"] == "Missed interval"]
    marker = cast(
        alt.Chart, alt.Chart(misses).mark_point(filled=True, color="#b94b36", size=65)
    ).encode(
        x=alt.X("Interval (GMT):N", sort=delivery["Interval (GMT)"].tolist()),
        xOffset=alt.XOffset("Series:N", sort=series),
        y=alt.Y("kW:Q"),
    )
    st.altair_chart(
        alt.layer(chart, marker).properties(height=235),
        width="stretch",
        alt="Requested and delivered power for each event half-hour",
    )


def _interval_label(timeline: pd.DatetimeIndex, step: int) -> str:
    start = timeline[step]
    return f"{start:%H:%M}–{start + pd.Timedelta(minutes=30):%H:%M}"


def _event_reason(
    result: dict,
    slot: str,
    timeline: pd.DatetimeIndex,
    s: Scenario,
    outcome: EventOutcome,
) -> None:
    st.markdown("**Why was the request MET or NOT MET?**")
    if outcome.status == "NOT ASSESSABLE":
        st.write("Set a positive flexibility target to assess this event.")
        return
    data = result[slot]
    if outcome.status == "MET":
        criterion = (
            "Every required half-hour was satisfied."
            if s.target_type == "interval"
            else "The whole-event energy target was satisfied."
        )
        event = list(s.event_steps)
        export = sum(data["portfolio_export_kw"][i] for i in event) * DT
        supplied = float(np.asarray(data["discharge_kw"])[event].sum() * DT) - export
        top = sorted(
            (h for h in data["households"] if h["event_flex_kwh"] > EPS),
            key=lambda h: -h["event_flex_kwh"],
        )[:2]
        leaders = ", ".join(f"{h['household']} ({h['event_flex_kwh']:.2f} kWh)" for h in top)
        st.write(
            f"{criterion} Delivery was {outcome.delivered_kwh:.2f} kWh. "
            f"Batteries supplied {supplied:.2f} kWh to homes and exported {export:.2f} kWh."
            + (f" Leading net contributors were {leaders}." if leaders else "")
        )
        return
    if s.target_type == "energy":
        st.write(
            f"The event delivered {outcome.delivered_kwh:.2f} of "
            f"{outcome.requested_kwh:.2f} kWh. There is no mandatory half-hour power minimum."
        )
        limits = [
            diagnose_interval(s, result, slot, k, demand)
            for k, demand in zip(outcome.steps, outcome.requested_kw, strict=True)
        ]
        ceilings = [
            item.physical_ceiling_kw for item in limits if item.physical_ceiling_kw is not None
        ]
        if len(ceilings) == len(limits) and sum(ceilings) * DT < outcome.requested_kwh - EPS:
            st.write(
                f"At the recorded states and loads, the interval ceilings summed to "
                f"{sum(ceilings) * DT:.2f} kWh. Different dispatch earlier in the day "
                "could change those states."
            )
        else:
            st.write("The exact limiting constraint for the energy deficit could not be confirmed.")
        with st.expander("Shortfall calculation"):
            st.latex(
                rf"E_{{shortfall}}=\max(0,{outcome.requested_kwh:.3f}"
                rf"-({outcome.delivered_kwh:.3f}))={outcome.shortfall_kwh:.3f}\ \mathrm{{kWh}}"
            )
        return
    evidence = []
    for step in outcome.failed_steps:
        i = outcome.steps.index(step)
        request, actual = outcome.requested_kw[i], outcome.delivered_kw[i]
        info = diagnose_interval(s, result, slot, step, request)
        evidence.append((step, request, actual, info))
        msg = " ".join(info.verified) or (
            "The exact limiting constraint could not be confirmed "
            "from the available execution data."
        )
        if info.physical_ceiling_kw is not None and info.physical_ceiling_kw < request - EPS:
            msg = (
                f"Recorded states and load allowed at most {info.physical_ceiling_kw:.2f} kW. "
                + msg
            )
        st.write(
            f"**{_interval_label(timeline, step)} GMT** · {request:.2f} kW requested, "
            f"{actual:.2f} kW delivered, {request - actual:.2f} kW short. {msg}"
        )
        if info.observed:
            st.caption(" ".join(info.observed))
    with st.expander("Shortfall calculation"):
        for step, request, actual, info in evidence:
            deficit = request - actual
            st.caption(f"{_interval_label(timeline, step)} GMT")
            st.latex(
                rf"\Delta P={request:.3f}-({actual:.3f})={deficit:.3f}\ \mathrm{{kW}},"
                rf"\quad \Delta E={deficit:.3f}\times {DT:g}={deficit * DT:.3f}\ \mathrm{{kWh}}"
            )
            if info.extra_stored_kwh is not None:
                st.latex(
                    rf"\sum_i \frac{{\Delta P_i\Delta t}}{{\eta_i}}"
                    rf"={info.extra_stored_kwh:.3f}\ \mathrm{{kWh}}"
                )
                st.caption(
                    "Minimum additional stored energy at this boundary using feasible "
                    "per-battery headroom and the recorded discharge efficiencies."
                )
        st.caption("Extra stored energy alone cannot overcome a power or grid connection limit.")


def _fulfilment(
    result: dict, delivery: pd.DataFrame, timeline: pd.DatetimeIndex, s: Scenario
) -> None:
    st.subheader("Portfolio flexibility delivery")
    source = result["provenance"]["inputs"]
    start = pd.Timestamp(source["original_event_start"]).tz_convert("Europe/London")
    end = pd.Timestamp(source["original_event_end"]).tz_convert("Europe/London")
    window = f"{start:%H:%M}–{end:%H:%M %Z}"
    if start.date() != end.date():
        window = f"{start:%H:%M %Z}–{end:%d %b %H:%M %Z}"
    participants = sum(b.participating for b in s.batteries)
    st.caption(
        f"{result['method']} · {start:%d %B %Y} · {window} · "
        f"{len(s.event_steps) * DT:g} h · {participants}/{len(s.batteries)} batteries participating"
    )
    choices = [REPLAY, PLAN] if result.get("realized") is not None else [PLAN]
    label = (
        st.radio(
            "Validation trajectory",
            choices,
            horizontal=True,
            key=f"dispatch_dashboard_trajectory_{result['method']}",
        )
        if len(choices) == 2
        else PLAN
    )
    slot = "realized" if label == REPLAY else "planned"
    outcome = event_outcome(s, result[slot])
    rate_text = f"{outcome.fulfilment_pct:.2f}%" if outcome.fulfilment_pct is not None else "—"
    with st.container(horizontal=True, gap="medium"):
        st.metric("Delivery status", outcome.status, width="content")
        st.metric("Requested volume", f"{outcome.requested_kwh:.2f} kWh", width="content")
        st.metric("Delivered volume", f"{outcome.delivered_kwh:.2f} kWh", width="content")
        st.metric("Credited fulfilment", rate_text, width="content")
        st.metric("Energy shortfall", f"{outcome.shortfall_kwh:.2f} kWh", width="content")
        st.metric("Weighted objective", f"£{result[slot]['objective']:.2f}", width="content")
    power = outcome.requested_kw
    power_text = (
        f"{power[0]:g} kW" if np.all(power == power[0]) else (f"{power.min():g}–{power.max():g} kW")
    )
    target = "interval minimum" if s.target_type == "interval" else "energy target power reference"
    st.caption(
        f"Configured portfolio request · {power_text} {target} · {outcome.requested_kwh:.2f} kWh. "
        "This is a simulation target."
    )
    st.markdown("**Requested vs Delivered Flexibility**")
    _event_chart(delivery, outcome, label)
    failed = outcome.failed_steps
    rows = [
        ("Requested event energy", f"{outcome.requested_kwh:.2f} kWh"),
        ("Delivered event energy", f"{outcome.delivered_kwh:.2f} kWh"),
        ("Energy shortfall", f"{outcome.shortfall_kwh:.2f} kWh"),
        ("Credited fulfilment", rate_text),
        (
            "Failed event intervals",
            str(len(failed)) if s.target_type == "interval" and outcome.requested_kwh > 0 else "—",
        ),
        ("First failed interval (GMT)", _interval_label(timeline, failed[0]) if failed else "—"),
    ]
    if abs(outcome.credited_kwh - outcome.delivered_kwh) > EPS:
        rows.insert(2, ("Credited event energy", f"{outcome.credited_kwh:.2f} kWh"))
        if outcome.requested_kwh > 0:
            gross_rate = 100 * outcome.delivered_kwh / outcome.requested_kwh
            st.caption(
                f"Delivery before credit rules was {gross_rate:.2f}% of requested energy. "
                "Credit is capped and surplus cannot offset a missed power interval."
            )
    with st.expander("Delivery calculation"):
        st.table(pd.DataFrame(rows, columns=["Measure", "Value"]), hide_index=True)
    _event_reason(result, slot, timeline, s, outcome)


def _comparison(result: dict, s: Scenario) -> None:
    p, r = result["planned"], result["realized"]
    st.subheader("Forecast-Based Dispatch Plan vs Historical Replay" if r is not None else PLAN)
    capacity = sum(b.capacity_kwh for b in s.batteries)

    def measures(data: dict) -> list[str]:
        outcome = event_outcome(s, data)
        pct = outcome.fulfilment_pct
        score = f"{pct:.1f}% · {outcome.status}" if pct is not None else outcome.status
        return [
            f"{outcome.delivered_kwh:.2f}",
            score,
            f"{sum(data['portfolio_export_kw'][k] for k in s.event_steps) * DT:.2f}",
            f"{data['cost_gbp']:.2f}",
            f"{data['objective']:.2f}",
            f"{100 * data['remaining_kwh'] / capacity:.1f}% · {data['remaining_kwh']:.2f} kWh",
        ]

    st.table(
        pd.DataFrame(
            {
                "Measure": [
                    "Event delivery (kWh)",
                    "Configured target fulfilment",
                    "Event grid export (kWh)",
                    "Net electricity cost (£)",
                    "Total objective (£)",
                    "Final portfolio SoC",
                ],
                PLAN: measures(p),
                **({REPLAY: measures(r)} if r is not None else {}),
            }
        ),
        hide_index=True,
    )
    text = "Forecast-Based Dispatch Plan uses forecast demand."
    if r is not None:
        text += " Historical Replay uses measured 2013 demand for execution."
        if s.simulation_mode == "EVENT_ONLY":
            text += (
                " Decisions use the saved forecast and recorded battery state. "
                "Completed interval averages are unavailable at the decision boundary."
            )
        else:
            text += " " + METHOD_REPLAY[result["method"]]
    st.caption(text)


def _battery_table(result: dict, s: Scenario) -> pd.DataFrame:
    rows = []
    for label, data in ((PLAN, result["planned"]), (REPLAY, result["realized"])):
        if data is None:
            continue
        event = list(s.event_steps)
        event_export = np.maximum(0, -np.asarray(data["grid_kw"])[event]).sum(axis=0) * DT
        event_discharge = np.asarray(data["discharge_kw"])[event].sum(axis=0) * DT
        for i, h in enumerate(data["households"]):
            rows.append(
                {
                    "Battery": h["household"],
                    "Trajectory": label,
                    "Initial SoC (%)": h["initial_soc_pct"],
                    "Final SoC (%)": h["final_soc_pct"],
                    "Charge (kWh)": h["charged_kwh"],
                    "Discharge (kWh)": h["discharged_kwh"],
                    "Event contribution (kWh)": h["event_flex_kwh"],
                    "Event export (kWh)": event_export[i],
                    "Throughput (kWh)": h["charged_kwh"] + h["discharged_kwh"],
                    "Degradation (£)": (h["charged_kwh"] + h["discharged_kwh"])
                    * s.degradation_price,
                    "Event supply to home (kWh)": event_discharge[i] - event_export[i],
                }
            )
    return pd.DataFrame(rows).sort_values("Battery", kind="stable")


def _battery_summary(result: dict, s: Scenario) -> None:
    st.subheader("Five-Battery Dispatch and Comparison")
    st.dataframe(
        _battery_table(result, s).round(2), hide_index=True, alt="Results for five batteries"
    )
    if result.get("realized") is None:
        return
    evidence = replay_evidence(result, s)
    if evidence["changed_intervals"] == 0:
        st.caption(
            "Event battery actions matched. Changes in household demand can still change "
            "how much discharge is used at home or exported."
        )
    else:
        n = evidence["changed_intervals"]
        correction = evidence["correction_effect_kwh"]
        if correction is None:
            st.caption(
                f"Battery actions differed in {n} event intervals. "
                "The trace does not establish why."
            )
        else:
            request = evidence["request_effect_kwh"]
            st.caption(
                f"Battery actions differed in {n} event intervals. Changes in requested actions "
                f"accounted for {request:+.2f} kWh of the delivery difference and replay "
                f"corrections accounted for {correction:+.2f} kWh."
            )


def _economics(result: dict, s: Scenario) -> None:
    st.subheader("Objective Contributions and Simulated Electricity Cost")
    components = [
        "Net electricity cost",
        "Flexibility shortfall penalty",
        "Battery degradation cost",
        "Soft terminal SoC deficit penalty",
        "Total objective",
    ]
    st.table(
        pd.DataFrame(
            {
                "Weighted contribution (£)": components,
                **{
                    label: [
                        f"{amount:.2f}" for amount in [*data["weighted_terms"], data["objective"]]
                    ]
                    for label, data in ((PLAN, result["planned"]), (REPLAY, result["realized"]))
                    if data is not None
                },
            }
        ),
        hide_index=True,
    )
    st.caption(
        f"Simulated bills use £{s.import_price:g}/kWh for import and £{s.export_price:g}/kWh "
        f"for export credit. The £{s.weights[1]:g}/kWh shortfall coefficient is an assumed "
        "model penalty for this simulation."
    )
    if s.simulation_mode == "EVENT_ONLY":
        st.caption(
            f"The {s.target_soc:.0%} terminal SoC is a soft preference. A long event may "
            f"finish below it while still respecting the {s.reserve_soc:.0%} hard final reserve."
        )


def render_results(
    result: dict,
    reused: bool,
    timeline: pd.DatetimeIndex,
    s: Scenario,
    math: Callable[[str, Scenario], None],
) -> None:
    delivery = _event_delivery(result, timeline, s)
    _fulfilment(result, delivery, timeline, s)
    st.caption("Saved result loaded" if reused else "Run saved")
    _comparison(result, s)
    st.subheader("Event Interval Delivery")
    labels = [PLAN, REPLAY] if result.get("realized") is not None else [PLAN]
    detail = delivery[["Interval (GMT)", REQUEST, *labels]].rename(
        columns={label: f"{label} (kW)" for label in [REQUEST, *labels]}
    )
    for label in labels:
        detail[f"{label} check"] = (
            np.where(delivery[label] >= delivery[REQUEST] - EPS, "MET", "NOT MET")
            if s.target_kw > 0 and s.target_type == "interval"
            else "—"
        )
    st.dataframe(detail.round(2), hide_index=True, alt="Requested and delivered kW per half-hour")
    _battery_summary(result, s)
    if s.simulation_mode == "EVENT_ONLY":
        render_event_steps(result, s)
    elif result["method"] == "MPC":
        _mpc_results(result, timeline, s)
    _economics(result, s)
    math(result["method"], s)


def _mpc_results(result: dict, timeline: pd.DatetimeIndex, s: Scenario) -> None:
    with st.expander(
        "MPC Step-by-Step Control Results", key="dispatch_mpc_steps", on_change="rerun"
    ) as panel:
        if not panel.open:
            return
        choices = ["planned", "realized"] if result.get("realized") is not None else ["planned"]
        key = st.radio(
            "MPC trajectory",
            choices,
            index=len(choices) - 1,
            format_func=lambda slot: PLAN if slot == "planned" else REPLAY,
            horizontal=True,
        )
        trace = result["planned_trace"] if key == "planned" else result["realized_trace"]
        solves = [row for row in trace if "solver_code" in row]
        st.caption(
            f"{len(solves)} solves across the day · {len(s.event_steps)} event intervals · "
            f"{s.prediction_steps} configured steps ({s.prediction_steps * DT:g} h). "
            "The horizon shrinks near midnight."
        )
        st.write(
            "Every 30 minutes MPC reads current battery states and available demand, updates "
            "the forecast window, solves a rolling MILP, and executes only the first action. "
            "It advances the battery states and repeats. In replay, only the current measured "
            "load replaces a forecast step. Later steps still use forecast demand."
        )
        portfolio, batteries = control_rows(result, s, key)
        frame = pd.DataFrame(portfolio)
        frame.insert(
            0, "Control time (GMT)", timeline[frame.pop("Step").tolist()].strftime("%H:%M")
        )
        st.dataframe(frame.round(4), hide_index=True, alt="MPC solves and actions during the event")
        k = st.selectbox(
            "Inspect five batteries at",
            s.event_steps,
            format_func=lambda step: timeline[step].strftime("%H:%M GMT"),
            key="dispatch_mpc_interval",
        )
        detail = pd.DataFrame([row for row in batteries if row["Step"] == k]).drop(columns="Step")
        st.dataframe(
            detail.round(4), hide_index=True, alt="Five MPC control actions at this interval"
        )
        st.caption(
            "Positive signed power charges and negative power discharges. The requested "
            "setpoint is the first optimised action. Executed power includes any corrections."
        )
        actual_cost = objective_steps(s, result[key])
        st.dataframe(
            pd.DataFrame(
                [actual_cost.sum(axis=0)],
                columns=[
                    "Weighted electricity (£)",
                    "Weighted shortfall (£)",
                    "Weighted degradation (£)",
                    "Weighted terminal (£)",
                ],
            )
            .assign(**{"Daily total (£)": actual_cost.sum()})
            .round(4),
            hide_index=True,
            alt="Daily objective reconciled from executed intervals",
        )
        st.caption(
            "The predicted objective is the solver's returned value for that horizon. "
            "Consecutive solves can cover different steps and start from different states. "
            "Executed costs reconcile across the day. The terminal penalty posts once at day "
            "end. Energy mode shows a kW reference and posts the shortfall at the last interval. "
            "In interval mode the remaining obligation includes earlier misses and the "
            "requirement for later intervals."
        )


def render_event_steps(result: dict, s: Scenario, *, widget_key: str = "") -> None:
    evidence = result
    if (
        result.get("explanation_version") != EXPLANATION_VERSION
        or "execution_records" not in result
    ):
        evidence = event_evidence(result, s, result["provenance"]["inputs"])
    q = result.get("qualification")
    if q:
        st.caption(
            f"Portfolio {q['status'].lower()} using forecast demand · qualification "
            f"{q['qualification_seconds']:.3f} s, measured separately from controller execution. "
            "Realised demand can still restrict delivery."
        )
    suffix = widget_key or result["method"]
    choices = list(evidence["execution_records"])
    slot = st.radio(
        "Execution detail",
        choices,
        index=len(choices) - 1,
        horizontal=True,
        format_func=lambda k: REPLAY if k == "realized" else PLAN,
        key=f"event_detail_{suffix}",
    )
    rows = evidence["execution_records"][slot]
    explanation = evidence["explanations"][slot]
    st.caption(explanation.get("details", ""))
    if explanation.get("active_limits"):
        st.caption(
            "Observed battery and grid boundaries · " + ", ".join(explanation["active_limits"])
        )
    trace = result["realized_trace"] if slot == "realized" else result["planned_trace"]
    solves = [r for r in trace if "solver_code" in r]
    initial = next((r for r in result["planned_trace"] if "solver_code" in r), None)
    st.caption(
        f"{len(rows)} executed intervals · {len(solves)} optimisation solves in this trajectory. "
        + ("Replay uses the original single event solve." if result["method"] == "MILP" else "")
    )
    names = [b.household_id for b in s.batteries]
    battery = st.selectbox("Battery trajectory", names, key=f"event_house_{suffix}")
    i = names.index(battery)
    times = [pd.Timestamp(r["timestamp"]).strftime("%H:%M") for r in rows]
    final = pd.Timestamp(rows[-1]["timestamp"]) + pd.Timedelta(minutes=30)
    cols = st.columns(2)
    cols[0].line_chart(
        pd.DataFrame(
            {
                "Time": [*times, final.strftime("%H:%M")],
                "SoC (%)": [100 * r["soc_before"][i] for r in rows]
                + [100 * rows[-1]["soc_after"][i]],
            }
        ),
        x="Time",
        y="SoC (%)",
    )
    cols[1].bar_chart(
        pd.DataFrame(
            {
                "Time": times,
                "Charge (kW)": [r["charge_kw"][i] for r in rows],
                "Discharge (kW)": [r["discharge_kw"][i] for r in rows],
            }
        ),
        x="Time",
        y=["Charge (kW)", "Discharge (kW)"],
        stack=False,
    )
    with st.expander("Step-by-Step Control and Optimisation Process"):
        if result["method"] == "MILP" and initial is not None:
            st.caption(
                f"Initial complete-event solver objective £{initial['solver_objective']:.4f} · "
                f"{initial['status']} · {initial['runtime_seconds']:.4f} s. "
                "The original schedule stays fixed in replay."
            )
        if result["method"] == "RBC":
            st.caption("Solver objectives are not applicable to RBC.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Time": t,
                        "Requested (kW)": r["request_kw"],
                        "Delivered (kW)": r["delivery_kw"],
                        "Power gap (kW)": r["power_shortfall_kw"],
                        "Stage (£)": r["stage_cost"],
                        "Running (£)": r["cumulative_running_cost"],
                        **dict(
                            zip(
                                ["Energy (£)", "Shortfall (£)", "Degradation (£)", "Terminal (£)"],
                                r["weighted_interval_costs"],
                                strict=True,
                            )
                        ),
                        "Predicted objective (£)": r.get("solver_objective"),
                        "Horizon": r.get("horizon_steps"),
                        "Solver status": r.get("status"),
                        "Solver time (s)": r.get("runtime_seconds"),
                        "MIP gap": r.get("gap"),
                        "Decision": r["decision"],
                    }
                    for t, r in zip(times, rows, strict=True)
                ]
            ).round(4),
            hide_index=True,
        )
        k = st.selectbox(
            "Inspect interval",
            range(len(rows)),
            format_func=times.__getitem__,
            key=f"event_step_{suffix}",
        )
        r = rows[k]
        forecast_first = evidence["execution_records"]["planned"][k]
        fields = {
            "SoC before": [100 * v for v in r["soc_before"]],
            "SoC after": [100 * v for v in r["soc_after"]],
            "Stored before (kWh)": r["energy_before_kwh"],
            "Stored after (kWh)": r["energy_after_kwh"],
            "Forecast demand (kW)": r["forecast_load_kw"],
            "Actual demand (kW)": r["actual_load_kw"],
            "Forecast planned (kW)": forecast_first["applied_kw"],
            "Requested (kW)": r["requested_kw"],
            "Executed (kW)": r["applied_kw"],
            "Available discharge (kW)": r.get(
                "available_discharge_kw", [max(0, -v) for v in r["min_action_kw"]]
            ),
            "Allocation (kW)": r.get("allocated_discharge_kw"),
            "Import (kW)": r["import_kw"],
            "Export (kW)": r["export_kw"],
            "Participating": r["participating"],
            "Corrected": [name in r["constrained_households"] for name in names],
        }
        st.dataframe(pd.DataFrame({"Household": names, **fields}).round(4), hide_index=True)
        plan = r if result["method"] == "MPC" else initial
        if plan is not None and plan.get("predicted_energy_kwh") is not None:
            st.caption(
                "Forecast sequence for the selected solve. Positive net power means charging."
            )
            st.dataframe(pd.DataFrame(plan["predicted_net_battery_kw"], columns=names).round(4))
            st.dataframe(pd.DataFrame(plan["predicted_energy_kwh"], columns=names).round(4))
            st.write(
                "Predicted weighted terms (£), in energy, shortfall, "
                "degradation and terminal order.",
                [round(v, 4) for v in plan["predicted_weighted_terms"]],
            )
        st.line_chart(
            pd.DataFrame(
                {"Time": times, "Running cost (£)": [r["cumulative_running_cost"] for r in rows]}
            ),
            x="Time",
            y="Running cost (£)",
        )
        final_terms = result[slot]["weighted_terms"]
        st.bar_chart(
            pd.DataFrame(
                {
                    "Term": ["Energy", "Shortfall", "Degradation", "Terminal"],
                    "Weighted (£)": final_terms,
                }
            ),
            x="Term",
            y="Weighted (£)",
        )
        st.caption(
            "The terminal penalty is applied once at event end. MPC forecast objectives "
            "cover shrinking horizons and cannot be added to realised running cost."
        )
