"""Scenario controls and method tabs for the BatteryFlex Simulation Lab."""

from dataclasses import asdict, replace

import pandas as pd
import streamlit as st

from batteryflex.defaults import ForecastingDefaults, SimulationDefaults, load_defaults
from batteryflex.dispatch import METHODS, STEPS, Scenario
from batteryflex.dispatch_dashboard import performance_row
from batteryflex.dispatch_event import (
    EVENT_START_SOC,
    event_start_batteries,
    resources,
    standard_scenario,
)
from batteryflex.neso_intervals import event_intervals
from batteryflex.storage.dispatch_runs import (
    _identity,
    load_saved_run,
    replay_load,
    resolve_inputs,
    saved_or_run,
    saved_portfolio,
)
from batteryflex.storage.repository import Repository
from batteryflex.ui.dispatch_batch import render_batch_summary
from batteryflex.ui.dispatch_benchmark import refresh_saved_benchmarks
from batteryflex.ui.dispatch_results import render_results
from batteryflex.ui.neso_events import event_label, reviewed_selection

LABELS = (
    "Rule-Based Control (RBC)",
    "Model Predictive Control (MPC)",
    "Standalone MILP",
)
DESCRIPTIONS = {
    "RBC": "Deterministic dispatch using predefined operational rules and asset availability.",
    "MPC": "Rolling-horizon optimisation with repeated dispatch decisions based on updated "
    "asset states. Each optimisation uses a MILP solver.",
    "MILP": "Single multi-period Mixed-Integer Linear Programming optimisation of the complete "
    "flexibility event dispatch schedule.",
}


@st.cache_data(ttl=120, max_entries=18, show_spinner=False)
def _forecast(_repo: Repository, storage: str, event_id: str, event: dict, _sample, algorithm: str):
    return resolve_inputs(_repo, event, _sample, algorithm)


@st.cache_data(ttl=120, max_entries=5, show_spinner=False)
def _actual(_repo: Repository, storage: str, dataset: str, timeline: tuple):
    return replay_load(_repo, dataset, pd.DatetimeIndex(timeline))


def _settings(batteries, steps: tuple[int, ...]) -> Scenario:
    default = standard_scenario(batteries, steps)
    defaults = load_defaults("simulation.yaml", SimulationDefaults)
    st.subheader("Flexibility delivery obligation")
    st.caption(
        "Only event half-hours are executed. Flexibility uses uncontrolled household load for each "
        "trajectory as the simulation baseline. The portfolio target, tariffs, reserves and grid "
        "limits are scenario assumptions. Official settlement is outside this evaluation."
    )
    left, right = st.columns(2)
    with left:
        target = st.number_input(
            "Requested flexibility (kW)",
            min_value=0.0,
            value=default.target_kw,
            key="simulation_commitment",
        )
    with right:
        target_type = st.selectbox(
            "Target type",
            ["interval", "energy"],
            format_func=lambda value: (
                "Minimum kW in each event interval"
                if value == "interval"
                else "Total event kWh (kW × event hours)"
            ),
        )
    with st.expander("Tariffs, grid limits, reserves and solver settings"):
        a, b, c = st.columns(3)
        with a:
            import_price = st.number_input(
                "Import (£/kWh)", min_value=0.0, value=default.import_price
            )
            export_price = st.number_input(
                "Export (£/kWh)", min_value=0.0, value=default.export_price
            )
            degradation = st.number_input(
                "Degradation (£/kWh throughput)", min_value=0.0, value=default.degradation_price
            )
            terminal_price = st.number_input(
                "Terminal deficit (£/kWh)", min_value=0.0, value=default.terminal_price
            )
        with b:
            limit_import = st.checkbox("Set a household import cap")
            import_cap = st.number_input(
                "Household import cap (kW)",
                min_value=0.0,
                value=defaults.optional_import_cap_kw,
                disabled=not limit_import,
            )
            reserve = st.slider("Hard final reserve (%)", 0, 100, round(default.reserve_soc * 100))
            terminal = st.slider("Soft final target (%)", 0, 100, round(default.target_soc * 100))
        with c:
            horizon = st.slider(
                "MPC prediction horizon (half-hours)", 1, STEPS, default.prediction_steps
            )
            time_limit = st.number_input(
                "Time limit per solve (seconds)", 0.1, 120.0, default.time_limit
            )
            gap = st.number_input(
                "Relative MIP gap tolerance", 0.0, 1.0, default.gap, format="%.4f"
            )
        w1, w2, w3, w4 = (
            column.number_input(name, min_value=0.0, value=value)
            for column, name, value in zip(
                st.columns(4),
                (
                    "Energy weight",
                    "Shortfall weight (£/kWh)",
                    "Degradation weight",
                    "Terminal weight",
                ),
                default.weights,
                strict=True,
            )
        )
    return replace(
        default,
        target_kw=target,
        import_price=import_price,
        export_price=export_price,
        import_limit_kw=import_cap if limit_import else None,
        reserve_soc=reserve / 100,
        target_soc=terminal / 100,
        degradation_price=degradation,
        terminal_price=terminal_price,
        weights=(w1, w2, w3, w4),
        prediction_steps=horizon,
        time_limit=time_limit,
        gap=gap,
        target_type=target_type,
    )


def _rbc_rules() -> None:
    st.markdown("**1. Feasible battery actions · every interval**")
    st.latex(r"a_i\in[\ell_i,h_i],\quad a_i=P^c_i-P^d_i")
    st.latex(r"\ell_i=\max\{-\bar P^d_i,-(E_i-E_i^{min})_+\eta_{d,i}/\Delta t,-L_i-\bar X_i\}")
    st.latex(r"h_i=\min\{\bar P^c_i,(E_i^{max}-E_i)_+/(\eta_{c,i}\Delta t),\bar I_i-L_i\}")
    st.write(
        "Signed battery action a, its lower and upper bounds ℓ and h, demand L, battery "
        "ratings P and connection caps X and I are in kW. Omit the import term when its cap "
        "is unset. Stored energy E and its SoC bounds are in kWh. Efficiencies η are fractions "
        "and Δt is 0.5 h. Nonparticipants have zero battery power. Project idle or a rule's "
        "request into each home's feasible interval. An empty interval is infeasible."
    )
    st.markdown("**2. Reserve protection · before discretionary discharge**")
    st.latex(r"B_i=\max(E_i^{min},\, C_i r),\quad E_{i,T}\ge B_i")
    st.write(
        "B is the reserve in kWh, C is capacity in kWh, r is the configured hard reserve "
        "fraction, and T is event end. Minimum SoC applies at every step. Binding connection "
        "limits can require discharge below B during the day. The hard event-end check still "
        "applies. The soft final target only enters RBC's performance score."
    )
    st.markdown("**3. Pre-event preparation · before the first event interval**")
    st.latex(
        r"E_i^{prep}=\max(B_i,C_i r_{evt}),\quad P_i^c=(E_i^{prep}-E_i)_+/(\eta_{c,i}\Delta t)"
    )
    st.write(
        "When import costs at most the ceiling in £/kWh, charge toward the pre-event "
        "fraction rₑᵥₜ, clipped to the feasible action range. At a higher tariff skip "
        "discretionary precharge and recover only the hard reserve. Forecast load or current "
        "measured demand determines grid headroom for each home."
    )
    st.markdown("**4. Event discharge allocation · inside the event window**")
    st.latex(r"a_i^0=\operatorname{clip}(0,\ell_i,h_i)")
    st.latex(r"A_{i,k}=[a_i^0+[-\max(\ell_i,-(E_i-B_i)_+\eta_{d,i}/\Delta t)]_+]_+")
    st.latex(r"R_k^{remaining}=[R_k+\sum_i a_i^0]_+")
    st.latex(
        r"P^{extra}_{i,k}=A_{i,k}\min(1,\ R^{remaining}_k/\sum_j A_{j,k})"
        r"\quad\text{when }\sum_j A_{j,k}>0"
    )
    st.write(
        "Connection support a⁰ comes first. A is additional discharge available above the "
        "reserve, and R remaining is the unmet portfolio request after required connection "
        "support. Quantities are kW. For an event energy target, R is outstanding kWh divided "
        "by remaining event hours. All five homes share the request in proportion to A. "
        "When total A is zero, allocation is zero. The applied action is a⁰ minus extra "
        "discharge. Surplus beyond home demand may export up to the connection cap. The "
        "positive target-minus-delivery gap is counted as shortfall."
    )
    st.markdown("**5. Reserve recovery and cycling · outside the event**")
    st.latex(r"a_i=\operatorname{clip}((B_i-E_i)_+/(\eta_{c,i}\Delta t),\ell_i,h_i)")
    st.write(
        "After the event, and when preparation is skipped, recover B and otherwise idle "
        "subject to connection limits. The rule avoids discretionary cycling. The five "
        "batteries must satisfy the hard reserve at event end."
    )


def _math(method: str, scenario: Scenario | None) -> None:
    with st.expander("Physical constraints and controller procedure"):
        st.write(DESCRIPTIONS[method])
        if method == "RBC":
            if scenario is None or scenario.simulation_mode == "EVENT_ONLY":
                st.write(
                    "RBC applies its existing event allocation using forecast demand and current "
                    "battery energy. Execution checks use realised demand. The portfolio "
                    "is qualified before control. Preparation and recovery are outside this window."
                )
            else:
                _rbc_rules()
        elif method == "MPC":
            st.write(
                "At each interval, read battery states and keep the saved future forecast. "
                "Solve the available forecast window and apply only the first action. "
                "Future intervals use the saved forecast. Intermediate windows keep the final "
                "reserve reachable by rated charging capacity. The soft terminal penalty enters "
                "when the window reaches event end. For an energy target, the model apportions "
                "the remaining energy across "
                "the remaining event intervals."
            )
            st.latex(
                r"E_{i,h}\geq\max\{E_i^{min},\, E_i^{reserve}"
                r"-(T-h)\eta_{c,i}\bar P_i^c\Delta t\}"
            )
            st.caption("Here h is the end of this window and T is the end of the event.")
            if scenario is not None and scenario.target_type == "energy":
                st.latex(
                    r"R_{E,\mathrm{window}}=\max(0,R_E-D_{\mathrm{past}})"
                    r"\frac{|\mathcal E_{\mathrm{window}}|}{|\mathcal E_{\mathrm{remaining}}|}"
                )
                st.caption("Past delivery D and both energy targets R are in kWh.")
        else:
            st.write(
                "SciPy HiGHS schedules the complete event using the saved forecast. In historical "
                "replay, each scheduled action is bounded by the current load, battery state "
                "and connection limits. A violated final hard reserve makes the replay infeasible."
            )
        st.markdown(
            "**Performance evaluation function**" if method == "RBC" else "**Minimised objective**"
        )
        st.latex(r"J=w_1J_{energy}+w_2J_{shortfall}+w_3J_{degradation}+w_4J_{terminal}")
        st.latex(r"J_{energy}=\sum_{i,k}\Delta t(c^{imp}I_{i,k}-c^{exp}X_{i,k})")
        if scenario is not None and scenario.target_type == "energy":
            st.latex(
                r"J_{shortfall}=s_E,\quad s_E\geq R_E-\sum_{k\in\mathcal E}\Delta tF_k,\quad s_E\geq0"  # noqa: E501
            )
        else:
            st.latex(
                r"J_{shortfall}=\sum_{k\in\mathcal E}\Delta t\,s_k,\quad s_k\geq R_k-F_k,\quad s_k\geq0"  # noqa: E501
            )
        st.latex(
            r"J_{degradation}=\sum_{i,k}\Delta t\,c^{deg}(P^c_{i,k}+P^d_{i,k}),\quad J_{terminal}=\sum_i c^{terminal}z_i"  # noqa: E501
        )
        st.latex(r"E_{i,k+1}=E_{i,k}+\Delta t\left(\eta_{c,i}P^c_{i,k}-P^d_{i,k}/\eta_{d,i}\right)")
        st.caption(
            "Home i and half-hour k index stored energy E in kWh. Charge and discharge "
            "powers are measured at the AC side in kW. The two efficiency fractions η "
            "convert AC flows to battery energy over Δt = 0.5 h."
        )
        st.latex(
            r"P^{grid}_{i,k}=L_{i,k}+P^c_{i,k}-P^d_{i,k}=I_{i,k}-X_{i,k},\quad F_k=\sum_i(L_{i,k}-P^{grid}_{i,k})"  # noqa: E501
        )
        st.caption(
            "L is uncontrolled household demand. Positive grid power is import and negative "
            "grid power is export. F is portfolio reduction in kW against the uncontrolled "
            "demand of that trajectory."
        )
        st.latex(
            r"E_i^{min}\leq E_{i,k}\leq E_i^{max},\quad E_{i,T}\geq E_i^{reserve},\quad z_i\geq \max(0,E_i^{target}-E_{i,T})"  # noqa: E501
        )
        st.caption(
            "Multiply capacity by the SoC limits and reserve or target fractions to get kWh. "
            "Minimum and maximum energy apply at every step. The reserve is hard at event end T. "
            "The soft target contributes a nonnegative deficit z in kWh."
        )
        st.latex(
            r"0\leq P^c_{i,k}\leq \bar P_i^c u_{i,k},\quad 0\leq P^d_{i,k}\leq\bar P_i^d(1-u_{i,k}),\quad u_{i,k}\in\{0,1\}"  # noqa: E501
        )
        st.caption(
            "Available power ratings are in kW. In the solvers u selects charge or discharge, "
            "with idle feasible in either direction. RBC applies a single signed action."
        )
        st.latex(
            r"0\leq I_{i,k}\leq\bar I_{i,k}v_{i,k},\quad 0\leq X_{i,k}\leq\bar X_i(1-v_{i,k}),\quad v_{i,k}\in\{0,1\}"  # noqa: E501
        )
        st.caption(
            "The solver's binary v selects grid direction per home. The import upper bound "
            "is demand plus available charge, limited by any configured import cap. The "
            "export upper bound is the scenario connection cap, in kW."
        )
        st.latex(r"I_{i,k}=\max(P^{grid}_{i,k},0),\qquad X_{i,k}=\max(-P^{grid}_{i,k},0)")
        st.write(
            "I and X are separate import and export powers in kW. Battery discharge can "
            "supply both household demand and export."
        )
        st.latex(
            r"\bar P_i^c=q_iP_i^{c,rated},\quad\bar P_i^d=q_iP_i^{d,rated},\quad q_i\in\{0,1\}"
        )
        st.write(
            "Participation q enables rated battery power in kW. A nonparticipant can still "
            "import electricity to supply its load."
        )
        st.latex(r"X_{i,k}=0\quad(k\notin\mathcal E)")
        if scenario is not None and scenario.target_type == "energy":
            st.latex(
                r"\sum_i X_{i,k}>0\ \Longrightarrow\ "
                r"\sum_{j\le k,\ j\in\mathcal E}\Delta t F_j\le R_E"
            )
        else:
            st.latex(r"\sum_i X_{i,k}>0\ \Longrightarrow\ F_k\le R_k")
        st.write(
            "For interval targets, export is confined to the event and to meeting the "
            "target. For an energy target the same guard compares cumulative delivered "
            "event energy through that step with the event energy target. MILP and MPC "
            "apply this as a conditional constraint. Replay can trim scheduled export "
            "after applying the physical limits. Behind-the-meter discharge can still "
            "reduce household imports beyond the event target."
        )
        st.caption(
            "Power, load, import I, export X, interval target R and interval slack s are in kW. "
            "Stored energy E, total target Rₑ, energy slack sₑ and terminal deficit z are in kWh. "
            "∆t is 0.5 h. Tariff, degradation and terminal rates are £/kWh. Weights are "
            "dimensionless except the flexibility penalty in £/kWh. A disabled/nonparticipating "
            "operation has zero available power. This scenario contains no PV generation."
        )
        if scenario is not None:
            st.write(
                f"Weights (energy, shortfall, degradation, terminal) {scenario.weights}. "
                f"Rates per kWh (import, export, degradation, terminal) "
                f"£{scenario.import_price:g}, £{scenario.export_price:g}, "
                f"£{scenario.degradation_price:g}, £{scenario.terminal_price:g}. "
                f"Hard final reserve {scenario.reserve_soc:.0%}. Each battery's configured "
                f"minimum SoC applies throughout the window. The preferred soft terminal target "
                f"is {scenario.target_soc:.0%}."
            )
            if method == "RBC" and scenario.simulation_mode == "FULL_DAY":
                st.caption(
                    f"Legacy full-day RBC prepares toward {scenario.event_soc:.0%} when "
                    "the import tariff permits."
                )
            if method != "RBC":
                horizon = (
                    min(scenario.prediction_steps, scenario.steps)
                    if method == "MPC"
                    else scenario.steps
                )
                st.caption(
                    f"HiGHS time limit {scenario.time_limit:g} s per solve, "
                    f"relative MIP gap {scenario.gap:g}, prediction horizon "
                    f"{horizon} steps."
                )


def render_dispatch(repo: Repository | None) -> None:
    st.subheader("Historical flexibility event")
    models = load_defaults("forecasting.yaml", ForecastingDefaults).dispatch_priority
    try:
        events, sample, _ = reviewed_selection()
    except (KeyError, OSError, ValueError) as exc:
        st.error(f"Reviewed event data unavailable: {exc}")
        return
    by_id = {event["internal_scenario_id"]: event for event in events}
    prior = st.session_state.get("battery_event")
    a, b = st.columns(2)
    event_id = a.selectbox(
        "NESO event",
        list(by_id),
        index=list(by_id).index(prior) if prior in by_id else 0,
        format_func=lambda k: event_label(by_id[k]),
        key="simulation_event",
        persist_state="session",
    )
    algorithm = b.selectbox(
        "Saved forecast model",
        models,
        key="dispatch_forecast_model",
    )
    event = by_id[event_id]
    st.write(
        f"Original NESO event {event['delivery_date']} · "
        f"{event['start_time']}–{event['end_time']} {event['time_basis']} · "
        f"{event['duration_minutes']:g} minutes"
    )
    with st.expander("Original national NESO requirements"):
        st.caption(
            "National MW from the reviewed source. Enter the household portfolio target separately."
        )
        intervals = event_intervals(sample[event["resource_id"]], event)
        st.dataframe(
            pd.DataFrame(
                {
                    "Start (GMT)": row["start_utc"],
                    "End (GMT)": row["end_utc"],
                    "National request (MW)": row["national_requirement_mw"],
                }
                for row in intervals
            ),
            hide_index=True,
            alt="National requirements",
        )
    scenario = None
    reference = None
    writable = repo is not None and repo.writable
    if repo is None:
        st.info(
            "Connect the prepared persistent database to load the saved forecast and batteries."
        )
    else:
        storage = str(getattr(repo.db, "endpoint", getattr(repo.db, "path", repo.objects.cache)))
        try:
            with st.spinner("Retrieving the saved battery portfolio…"):
                portfolio_id, portfolio = saved_portfolio(repo)
            obligation = st.container()
            with st.expander("Event-start asset configuration"):
                overridden = [
                    b.household_id
                    for b in portfolio.batteries
                    if not b.min_soc <= EVENT_START_SOC[b.household_id] <= b.max_soc
                ]
                if overridden:
                    st.caption(
                        "The standard starting SoC is outside the saved bounds for "
                        + ", ".join(overridden)
                        + ". Their saved starting SoCs are shown in the editor."
                    )
                visible = pd.DataFrame(
                    asdict(battery) for battery in event_start_batteries(portfolio.batteries)
                ).drop(columns=["interval_hours", "export_enabled"])
                st.caption(
                    "Participating batteries can export during the event to meet the target. "
                    "A blank export cap uses the battery's discharge rating as a simulation "
                    "assumption. Enter a connection cap when one is available."
                )
                visible["export_limit_kw"] = visible["export_limit_kw"].astype(float)
                edited = st.data_editor(
                    visible,
                    column_config={
                        "household_id": "Household",
                        "capacity_kwh": "Capacity (kWh)",
                        "charge_limit_kw": "Charge limit (kW)",
                        "discharge_limit_kw": "Discharge limit (kW)",
                        "min_soc": "Minimum SoC (fraction)",
                        "max_soc": "Maximum SoC (fraction)",
                        "initial_soc": "Event-start SoC (fraction)",
                        "charge_efficiency": "Charge efficiency (fraction)",
                        "discharge_efficiency": "Discharge efficiency (fraction)",
                        "export_limit_kw": st.column_config.NumberColumn("Export cap (kW)"),
                        "participating": "Participating",
                    },
                    disabled=["household_id"] if writable else True,
                    hide_index=True,
                    key=f"dispatch_batteries_{portfolio_id}",
                    alt="Editable five-battery simulation configuration",
                )
            batteries = tuple(
                replace(
                    original,
                    **{
                        key: (None if key == "export_limit_kw" and pd.isna(value) else value)
                        for key, value in row.items()
                        if key != "household_id"
                    },
                )
                for original, row in zip(
                    portfolio.batteries, edited.to_dict("records"), strict=True
                )
            )
            with obligation:
                steps = tuple(range(len(intervals)))
                scenario = (
                    _settings(batteries, steps) if writable else standard_scenario(batteries, steps)
                )
                if not writable:
                    st.caption("Public demonstration · saved dispatch results")
            limits = resources(scenario)
            st.markdown("**Portfolio qualification**")
            st.caption(
                f"{scenario.steps} control intervals · {scenario.target_kw:g} kW · "
                f"{limits['requested_kwh']:.2f} kWh requested. "
                "Initial SoCs are synthetic event-start assumptions."
            )
            st.write(
                f"Installed {limits['capacity_kwh']:.2f} kWh · "
                f"stored {limits['initial_kwh']:.2f} kWh "
                f"· reserved {limits['reserved_kwh']:.2f} kWh · available "
                f"{limits['available_kwh']:.2f} kWh and {limits['power_kw']:.2f} kW · "
                f"margin {limits['margin_kwh']:+.2f} kWh."
            )
            usable = limits["usable_at_final_reserve_kwh"]
            if usable < limits["available_kwh"] - 1e-6:
                st.caption(f"The hard final reserve reduces usable discharge to {usable:.2f} kWh.")
            if (
                usable < limits["requested_kwh"] - 1e-6
                or limits["power_kw"] < scenario.target_kw - 1e-6
            ):
                st.warning("The portfolio lacks usable energy or rated discharge power.")
            else:
                st.caption(
                    "The full forecast feasibility check runs before a new controller execution."
                )
            assumed = {
                b.household_id: b.discharge_limit_kw
                for b in batteries
                if b.participating and b.export_limit_kw is None
            }
            if assumed:
                st.caption(
                    "Assumed export caps (kW) · "
                    + " · ".join(f"{home} {cap:g}" for home, cap in assumed.items())
                )
        except (KeyError, OSError, ValueError) as exc:
            message = str(exc).replace(event_id, "the selected event")
            st.error(f"Simulation inputs unavailable: {message}")
        if scenario is not None:
            try:
                with st.spinner("Retrieving the saved forecast…"):
                    resolved, ref, timeline, steps, prediction = _forecast(
                        repo, storage, event_id, event, sample, algorithm
                    )
                timeline, prediction, steps = _event_window(timeline, prediction, steps)
                if scenario.event_steps != steps:
                    raise ValueError("Saved forecast intervals differ from the registered event")
                reference = _dispatch_reference(ref, portfolio_id, assumed)
            except (KeyError, OSError, ValueError) as exc:
                st.error(f"Simulation inputs unavailable for the selected event: {exc}")
    tabs = st.tabs(LABELS, key="dispatch_method_tabs", on_change="rerun")
    for method, tab in zip(METHODS, tabs, strict=True):
        if not tab.open:
            continue
        with tab:
            st.caption(DESCRIPTIONS[method])
            run = st.button(
                "Run Dispatch Simulation",
                key=f"dispatch_run_{method}",
                disabled=reference is None or not writable,
            )
            if scenario is None or repo is None:
                _math(method, scenario)
                continue
            key = f"dispatch_result_{method}"
            batch_key = f"dispatch_batch_result_{method}"
            batch_signature = (
                storage,
                algorithm,
                portfolio_id,
                replace(scenario, event_steps=(0,)),
            )
            batch_clicked = st.button(
                "Run All Five Events", key=f"dispatch_batch_{method}", disabled=not writable
            )
            if batch_clicked:
                refresh_saved_benchmarks()
                st.session_state[batch_key] = (
                    batch_signature,
                    _batch(
                        repo,
                        storage,
                        events,
                        sample,
                        algorithm,
                        method,
                        portfolio_id,
                        assumed,
                        scenario,
                    ),
                )
            if reference is None:
                _math(method, scenario)
                batch = st.session_state.get(batch_key)
                if batch and batch[0] == batch_signature:
                    render_batch_summary(batch[1], method)
                continue
            signature = (storage, _identity(scenario, method, reference)[0])
            shown = st.session_state.get(key)
            try:
                if run:
                    with st.spinner(f"Loading or running {method}…"):
                        result, reused = saved_or_run(
                            repo,
                            scenario,
                            method,
                            reference,
                            prediction,
                            lambda: _actual(repo, storage, resolved.dataset_id, tuple(timeline)),
                        )
                    if not reused:
                        refresh_saved_benchmarks()
                    st.session_state[key] = signature, result, reused
                elif batch_clicked or not shown or shown[0] != signature:
                    result = load_saved_run(repo, scenario, method, reference)
                    st.session_state[key] = signature, result, True
            except (KeyError, OSError, RuntimeError, ValueError) as exc:
                st.session_state.pop(key, None)
                st.error(f"Optimisation or saved result verification failed: {exc}")
            shown = st.session_state.get(key)
            if shown and shown[0] == signature and shown[1] is not None:
                render_results(shown[1], shown[2], timeline, scenario, _math)
            else:
                _math(method, scenario)
            batch = st.session_state.get(batch_key)
            if batch and batch[0] == batch_signature:
                render_batch_summary(batch[1], method)


def _event_window(timeline, prediction, steps):
    positions = list(steps)
    return timeline[positions], prediction[positions], tuple(range(len(positions)))


def _dispatch_reference(ref, portfolio_id, assumed):
    return {**ref, "portfolio_id": portfolio_id, "assumed_export_caps_kw": assumed}


def _batch(
    repo, storage, events, sample, algorithm, method, portfolio_id, assumed, scenario
) -> pd.DataFrame:
    repo.require_owner()
    rows = []
    total = len(events)
    queue = [
        {
            "Event": str(e["delivery_date"]),
            "Duration (h)": e["duration_minutes"] / 60,
            "Requested (kWh)": scenario.target_kw * e["duration_minutes"] / 60,
            "Execution status": "Pending",
            "Request fulfilment": None,
            "Realised objective (£)": None,
        }
        for e in events
    ]
    display = st.empty()
    display.dataframe(pd.DataFrame(queue), hide_index=True)

    progress = st.progress(0.0, text=f"Preparing {method} for {total} events")
    with st.status("Five-event run", expanded=True) as status:
        for index, event in enumerate(events, start=1):
            event_id = event["internal_scenario_id"]
            date = str(event["delivery_date"])
            progress.progress(
                (index - 1) / total, text=f"{method} — Processing event {index} of {total}."
            )
            queue[index - 1]["Execution status"] = "Running"
            display.dataframe(pd.DataFrame(queue), hide_index=True)

            try:
                resolved, ref, timeline, steps, prediction = _forecast(
                    repo, storage, event_id, event, sample, algorithm
                )
                if scenario.simulation_mode == "EVENT_ONLY":
                    timeline, prediction, steps = _event_window(timeline, prediction, steps)
                event_scenario = replace(scenario, event_steps=steps)
                result, reused = saved_or_run(
                    repo,
                    event_scenario,
                    method,
                    _dispatch_reference(ref, portfolio_id, assumed),
                    prediction,
                    lambda dataset=resolved.dataset_id, times=tuple(timeline): _actual(
                        repo, storage, dataset, times
                    ),
                )
                update = "Loaded from database" if reused else "Newly calculated and saved"
                rows.append(
                    performance_row(
                        event_scenario, result, "Saved" if reused else "Newly calculated"
                    )
                )
            except (KeyError, OSError, RuntimeError, ValueError) as exc:
                message = str(exc).replace(event_id, "the selected event")
                update = "Failed"
                rows.append(
                    {
                        "NESO event date": date,
                        "Hours": event["duration_minutes"] / 60,
                        "Status": "FAILED",
                        "Source": "—",
                        "Issue": message,
                    }
                )
            queue[index - 1].update(
                {
                    "Execution status": update,
                    "Request fulfilment": rows[-1]["Status"],
                    "Realised objective (£)": rows[-1].get("Total objective (£)"),
                }
            )
            display.dataframe(pd.DataFrame(queue).round(4), hide_index=True)
            rows[-1]["Execution status"] = update
            rows[-1].setdefault("Requested (kWh)", queue[index - 1]["Requested (kWh)"])
            summary = f"Event {index}/{total} · {date} · {update}"
            st.write(summary)
            progress.progress(index / total, text=summary)
        complete = sum(row["Status"] != "FAILED" for row in rows)
        status.update(
            label=f"{complete}/{total} events completed",
            state="complete" if complete == total else "error",
            expanded=complete != total,
        )
    display.empty()
    return pd.DataFrame(rows)
