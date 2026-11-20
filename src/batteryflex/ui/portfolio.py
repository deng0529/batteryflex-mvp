"""Four-section portfolio workspace; working edits and saved active assets stay separate."""

import pandas as pd
import streamlit as st

from batteryflex.battery_demo import demonstrate
from batteryflex.defaults import SimulationDefaults, load_defaults
from batteryflex.dispatch import DT
from batteryflex.portfolio import (
    HOUSEHOLDS,
    Portfolio,
    capability,
    default_portfolio,
    explain_commitment,
)
from batteryflex.portfolio_editor import calculate_round_trip, portfolio_rows, validate_rows
from batteryflex.portfolio_storage import export_configuration, import_configuration
from batteryflex.storage.repository import Repository
from batteryflex.storage.settings import Settings, runtime_repository
from batteryflex.ui.neso_events import event_label, reviewed_selection


def current_portfolio(repository: Repository | None = None) -> Portfolio:
    """Saved active portfolio only: unsaved editor/demo/scenario changes never enter it."""
    if "battery_portfolio" not in st.session_state:
        if repository is None:
            repository, _ = runtime_repository()
        st.session_state.battery_portfolio = (
            repository.portfolio() if repository else default_portfolio()
        )
    return st.session_state.battery_portfolio


def _restore_working() -> None:
    st.session_state.battery_working_rows = portfolio_rows(default_portfolio())
    st.session_state.battery_editor_revision += 1
    st.session_state.battery_save_message = (
        "info",
        "Defaults restored in the working table. Click Save Configuration to activate them.",
    )


def _save_configuration(payload: str, editor_key: str) -> None:
    # A cell edit arriving together with a save must be reviewed first: the download
    # payload and the committed snapshot must describe the same rendered table.
    try:
        pending = st.session_state.get(editor_key, {})
        rows = [dict(row) for row in st.session_state.battery_working_rows]
        if pending.get("added_rows") or pending.get("deleted_rows"):
            raise ValueError("The five household rows cannot be added or removed.")
        for index, changes in pending.get("edited_rows", {}).items():
            rows[int(index)].update(changes)
        if calculate_round_trip(rows) != st.session_state.battery_working_rows:
            raise ValueError("New table edits arrived; review the updated table and save again.")
        validated, errors = validate_rows(st.session_state.battery_working_rows)
        if validated is None:
            raise ValueError("; ".join(errors))
        if export_configuration(validated) != payload:
            raise ValueError("Working values changed; review the table and save again.")
        saved = import_configuration(payload, reviewed_five=True)
        repository, _ = runtime_repository()
        if repository is not None:
            identity = repository.save_portfolio(payload)
            st.session_state.battery_portfolio_version = identity
        st.session_state.battery_portfolio = saved
        st.session_state.battery_saved_json = payload
        st.session_state.battery_save_message = (
            "success",
            (
                "Configuration version saved in persistent storage and activated. JSON "
                "download requested."
                if repository
                else "Active configuration saved for this session. JSON download requested; "
                "retain the downloaded file for durable storage. No shared server file was written."
            ),
        )
    except (ValueError, TypeError, IndexError, OSError) as exc:
        st.session_state.battery_save_message = ("error", f"Configuration was not saved: {exc}")


def _configuration_table() -> Portfolio | None:
    st.subheader("Asset configuration")
    st.caption(
        "Five simulated research batteries; initial SOC values are illustrative, not measurements. "
        "Edit the working table; Simulation Lab uses the saved active configuration."
    )
    st.write("Simulation interval: 30 minutes (0.5 hours)")
    active = current_portfolio()
    settings = Settings.load()
    if not settings.writable and (settings.url or settings.require_cloud_credentials):
        st.dataframe(pd.DataFrame(portfolio_rows(active)), hide_index=True, alt="Saved portfolio")
        st.caption("The owner manages the saved portfolio.")
        return active
    if "battery_working_rows" not in st.session_state:
        st.session_state.battery_working_rows = portfolio_rows(active)
    st.session_state.setdefault("battery_editor_revision", 0)
    rows = st.session_state.battery_working_rows
    key = f"battery_table_{st.session_state.battery_editor_revision}"
    frame = pd.DataFrame(rows)
    for field in (
        "capacity_kwh",
        "charge_limit_kw",
        "discharge_limit_kw",
        "initial_soc",
        "min_soc",
        "max_soc",
        "charge_efficiency",
        "discharge_efficiency",
        "round_trip_efficiency",
        "export_limit_kw",
    ):
        frame[field] = frame[field].astype(float)
    number = st.column_config.NumberColumn
    edited = st.data_editor(
        frame,
        key=key,
        num_rows="fixed",
        hide_index=True,
        width="stretch",
        height=245,
        disabled=["household_id", "round_trip_efficiency"],
        column_config={
            "household_id": st.column_config.TextColumn("Household ID", pinned=True),
            "capacity_kwh": number("Capacity (kWh)", min_value=0.01, required=True),
            "charge_limit_kw": number("Max charge (kW)", min_value=0.0, required=True),
            "discharge_limit_kw": number("Max discharge (kW)", min_value=0.0, required=True),
            "initial_soc": number(
                "Initial SOC (%)",
                min_value=0.0,
                max_value=100.0,
                required=True,
                help="Stored energy at the start, as a percentage of battery capacity.",
            ),
            "min_soc": number(
                "Min SOC (%)",
                min_value=0.0,
                max_value=100.0,
                required=True,
                help="Minimum permitted SOC; this stored-energy reserve cannot be discharged.",
            ),
            "max_soc": number(
                "Max SOC (%)",
                min_value=0.0,
                max_value=100.0,
                required=True,
                help="Maximum permitted SOC; charging stops at this stored-energy boundary.",
            ),
            "charge_efficiency": number(
                "Charge efficiency (%)",
                help="Percentage of electrical charging energy added to stored battery energy.",
                min_value=0.01,
                max_value=100.0,
                required=True,
                format="%.4f",
            ),
            "discharge_efficiency": number(
                "Discharge efficiency (%)",
                help="Percentage of withdrawn stored energy delivered as electrical energy.",
                min_value=0.01,
                max_value=100.0,
                required=True,
                format="%.4f",
            ),
            "round_trip_efficiency": number(
                "Round-trip efficiency (%)",
                format="%.4f",
                help="The percentage of electrical energy recovered after a complete "
                "charge/discharge "
                "cycle. Calculated as charging efficiency multiplied by discharging efficiency. "
                "It is read-only.",
            ),
            "export_enabled": st.column_config.CheckboxColumn(
                "Export permission",
                required=True,
                help="Allows net household export; when disabled, grid power must "
                "remain nonnegative.",
            ),
            "export_limit_kw": number(
                "Net export cap (kW)",
                min_value=0.0,
                help="Maximum permitted net power exported from the household to the "
                "grid. For example, "
                "a 3.68 kW cap limits net grid export to 3.68 kW, even if the "
                "battery can discharge "
                "at 5 kW. Blank means no additional export cap is configured.",
            ),
            "participating": st.column_config.CheckboxColumn(
                "Participating",
                required=True,
                help="Participation in this working portfolio. Save to activate; check-specific "
                "checkboxes can temporarily override participation without "
                "changing saved settings.",
            ),
        },
        alt="Editable settings for all five household batteries",
    )
    result = calculate_round_trip(
        edited.astype(object).where(pd.notna(edited), None).to_dict("records")
    )
    if result != rows:
        # Fixed-row keyed editors preserve edits when values change in Streamlit
        # 1.67. Keep the key stable, retain the full working table and refresh the
        # calculated column. Only Restore Defaults resets the editor identity.
        st.session_state.battery_working_rows = result
        st.rerun()
    working, errors = validate_rows(result)
    for error in errors:
        st.error(error)
    with st.container(horizontal=True):
        st.download_button(
            "Save Configuration",
            export_configuration(working) if working is not None else "",
            file_name="batteryflex-portfolio-v1.json",
            mime="application/json",
            key="battery_save",
            on_click=_save_configuration,
            args=(export_configuration(working) if working is not None else "", key),
            disabled=working is None,
            type="primary",
        )
        st.button("Restore Defaults", key="battery_defaults", on_click=_restore_working)
    message = st.session_state.pop("battery_save_message", None)
    if message:
        getattr(st, message[0])(message[1])
    if working is None:
        st.warning(
            "Invalid working configuration: save, demonstration and capability results "
            "are unavailable."
        )
    elif working != active:
        st.caption("Unsaved working changes. The saved active portfolio is unchanged.")
    else:
        st.caption(
            "Working values match the active portfolio. Session state is not permanent storage."
        )
    return working


def _mathematical_model() -> None:
    st.subheader("Battery and household power models")
    st.markdown("**A. Battery Energy/SOC Model**")
    st.latex(
        r"E_{i,k+1}=E_{i,k}+\eta_{c,i}P^{ch}_{i,k}\Delta t"
        r"-\frac{P^{dis}_{i,k}\Delta t}{\eta_{d,i}}"
    )
    st.latex(r"SOC_{i,k}=\frac{E_{i,k}}{C_i},\qquad SOC_i^{min}\le SOC_{i,k}\le SOC_i^{max}")
    st.latex(
        r"0\le P^{ch}_{i,k}\le P_i^{ch,max},\quad 0\le P^{dis}_{i,k}\le P_i^{dis,max},"
        r"\quad P^{ch}_{i,k}P^{dis}_{i,k}=0"
    )
    st.caption(
        "Discrete-time battery energy balance for energy scheduling and optimisation, appropriate "
        "for this 30-minute residential aggregator simulation. E and capacity C: kWh; P: kW; "
        "Δt: hours (0.5 normally); SOC and efficiencies: fractions. "
        "No simultaneous charging and discharging."
    )
    st.caption(
        "First-order and second-order RC equivalent-circuit models describe voltage and transient "
        "electrical dynamics; this energy/SOC model does not. It is not a manufacturer's BMS "
        "model and has not been validated against real battery measurements."
    )
    st.markdown("**B. Household Grid Power Balance**")
    st.latex(r"P^{grid}_{i,k}=P^{load}_{i,k}+P^{ch}_{i,k}-P^{dis}_{i,k}")
    st.caption(
        "Positive grid power means grid import; negative means grid export. This is a household "
        "power-balance equation, not an internal battery state equation. It will later be "
        "combined with battery energy/SOC dynamics for aggregator optimisation."
    )


def _demonstration(working: Portfolio | None) -> None:
    st.subheader("Battery charge and discharge performance")
    st.caption(
        "Uses valid working table values, including unsaved edits. Constant-power battery energy "
        "dynamics to the permitted SOC boundary; household load and "
        "export restrictions are excluded. "
        "This is not a NESO event simulation and does not mutate saved initial SOC."
    )
    cols = st.columns(3)
    household = cols[0].selectbox(
        "Household battery", HOUSEHOLDS, key="demo_household", persist_state="session"
    )
    mode = cols[1].selectbox(
        "Operation", ["Charge", "Discharge"], key="demo_mode", persist_state="session"
    )
    battery = (
        next((b for b in working.batteries if b.household_id == household), None)
        if working
        else None
    )
    rating = (
        (battery.charge_limit_kw if mode == "Charge" else battery.discharge_limit_kw)
        if battery
        else 0.0
    )
    context = (household, mode, rating)
    if st.session_state.get("performance_context") != context:
        st.session_state.demo_power = float(rating)
        st.session_state.performance_context = context
    power = cols[2].number_input(
        "Operating Power (kW)",
        min_value=0.0,
        max_value=float(rating) if rating > 0 else None,
        disabled=battery is None or rating == 0,
        key="demo_power",
        persist_state="session",
    )
    if battery is None:
        st.info("Correct the working table to view battery performance.")
        return
    if rating == 0:
        st.info(
            f"The {mode.lower()} power rating is zero; no positive operating power is available."
        )
        return
    try:
        result = demonstrate(battery, mode, power)
    except ValueError as exc:
        st.error(str(exc))
        return
    curve = pd.DataFrame(
        [{"elapsed_hours": 0.0, "soc_pct": result.initial_soc * 100}]
        + [
            {"elapsed_hours": row.elapsed_hours, "soc_pct": row.soc * 100}
            for row in result.intervals
        ]
    )
    st.vega_lite_chart(
        curve,
        {
            "height": 270,
            "mark": {"type": "line", "point": True},
            "params": [
                {
                    "name": "performance_zoom",
                    "select": {"type": "interval", "encodings": ["x"]},
                    "bind": "scales",
                }
            ],
            "encoding": {
                "x": {
                    "field": "elapsed_hours",
                    "type": "quantitative",
                    "title": "Elapsed time (hours)",
                },
                "y": {
                    "field": "soc_pct",
                    "type": "quantitative",
                    "title": "SOC (%)",
                    "scale": {"domain": [0, 100]},
                },
                "tooltip": [
                    {
                        "field": "elapsed_hours",
                        "type": "quantitative",
                        "title": "Elapsed hours",
                        "format": ".6f",
                    },
                    {
                        "field": "soc_pct",
                        "type": "quantitative",
                        "title": "SOC (%)",
                        "format": ".4f",
                    },
                ],
            },
        },
        alt="Battery SOC to its permitted boundary, including the exact final partial interval",
    )
    with st.container(horizontal=True):
        st.metric("Initial SOC", f"{result.initial_soc:.2%}")
        st.metric("Final SOC", f"{result.final_soc:.2%}")
        st.metric("Operating power", f"{power:g} kW")
        st.metric(
            "Total charging time" if mode == "Charge" else "Total discharging time",
            f"{result.completion_hours:.6f} h",
        )
        st.metric(
            "Electrical energy charged" if mode == "Charge" else "Electrical energy discharged",
            f"{result.electrical_energy_kwh:.6f} kWh",
        )
    if result.completion_hours == 0:
        st.info(
            f"Initial SOC is already at the {'maximum' if mode == 'Charge' else 'minimum'} "
            "permitted boundary; remaining time and electrical energy are zero."
        )


def _commitment_check(working: Portfolio | None) -> None:
    st.subheader("Asset qualification")
    st.write(
        "This check estimates whether the selected household batteries have sufficient stored "
        "energy and discharge power to support a proposed local flexibility commitment during "
        "the selected NESO event."
    )
    st.caption(
        "Uses valid working table values. The five checkboxes below are temporary scenario "
        "choices; they do not change table participation or the saved active configuration."
    )
    try:
        events, _, _ = reviewed_selection()
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Reviewed event data unavailable: {exc}")
        return
    by_id = {e["internal_scenario_id"]: e for e in events}
    event_id = st.selectbox(
        "Historical NESO event",
        list(by_id),
        index=None,
        format_func=lambda k: event_label(by_id[k]),
        key="battery_event",
        persist_state="session",
    )
    commitment = st.number_input(
        "Proposed local commitment (kW)",
        min_value=0.0,
        value=load_defaults("simulation.yaml", SimulationDefaults).target_kw,
        key="battery_commitment",
        persist_state="session",
    )
    with st.container(horizontal=True):
        selected = []
        for household in HOUSEHOLDS:
            # Rebase only a household whose working participation actually changes.
            # Other table edits preserve deliberate scenario overrides.
            default = (
                next(
                    (b.participating for b in working.batteries if b.household_id == household),
                    None,
                )
                if working
                else None
            )
            key = f"check_participation_{household}"
            source_key = f"check_participation_source_{household}"
            if default is not None and st.session_state.get(source_key) != default:
                st.session_state[key] = default
                st.session_state[source_key] = default
            if key not in st.session_state:
                st.session_state[key] = default if default is not None else True
            if st.checkbox(
                household,
                key=key,
                persist_state="session",
            ):
                selected.append(household)
    st.caption(
        "Assumes constant discharge, no charging during the event and no "
        "additional grid-side restrictions. "
        "National MW is context only and is never scaled into a local kW commitment."
    )
    if working is None:
        st.info("Correct the working table before assessing capability.")
        return
    if event_id is None:
        st.info("Select a historical event to assess the local commitment.")
        return
    duration = by_id[event_id]["duration_minutes"] / 60
    scenario = working.select(selected)
    try:
        explanation = explain_commitment(scenario, duration, commitment)
    except ValueError as exc:
        st.error(str(exc))
        return
    result, totals = explanation.assessment, explanation.capability
    rows = [
        ("Event duration", duration, "h", "Actual duration of the selected validated NESO event."),
        (
            "Participating households",
            totals.participating,
            "households",
            "Included only in this check.",
        ),
        (
            "Usable stored energy",
            totals.usable_kwh,
            "kWh",
            "Energy above each battery's minimum SOC reserve.",
        ),
        (
            "Deliverable electrical energy",
            totals.deliverable_kwh,
            "kWh",
            "Usable stored energy multiplied by discharge efficiency.",
        ),
        (
            "Maximum constant portfolio discharge",
            result.capability_kw,
            "kW",
            "Sum of min(discharge rating, deliverable energy / duration) for each battery.",
        ),
        (
            "Proposed local commitment",
            commitment,
            "kW",
            "User-entered local constant-power commitment; not national MW.",
        ),
        (
            "Required commitment energy",
            explanation.required_energy_kwh,
            "kWh",
            "Local commitment multiplied by event duration.",
        ),
        (
            "Capability margin",
            result.margin_kw,
            "kW",
            "Available portfolio power minus local commitment.",
        ),
    ]
    if not result.feasible:
        rows.extend(
            [
                (
                    "Shortfall",
                    result.shortfall_kw,
                    "kW",
                    "Positive difference between commitment and available power.",
                ),
                (
                    "Equivalent shortfall energy",
                    explanation.shortfall_energy_kwh,
                    "kWh",
                    "Constant-power shortfall multiplied by duration; not measured delivery.",
                ),
            ]
        )
    st.dataframe(
        [
            {
                "Quantity": q,
                "Value": str(int(v)) if unit == "households" else f"{v:.6f}",
                "Unit": unit,
                "Explanation": why,
            }
            for q, v, unit, why in rows
        ],
        hide_index=True,
        alt="Selected scenario battery capability, commitment, margin and explanations",
        column_config={"Explanation": st.column_config.TextColumn(width="large")},
    )
    terms = [power for household, power in totals.contributions_kw if household in selected]
    st.caption(
        "Available portfolio power is the sum of participating batteries' sustainable powers."
    )
    st.latex(
        r"P_{available}= "
        + (" + ".join(f"{p:.6f}" for p in terms) if terms else "0")
        + rf" = {result.capability_kw:.6f}\;\mathrm{{kW}}"
    )
    st.latex(
        rf"M={result.capability_kw:.6f}-{commitment:.6f}"
        rf"={result.margin_kw:.6f}\;\mathrm{{kW}}"
    )
    st.latex(
        rf"E_{{commitment}}={commitment:.6f}\times {duration:g}"
        rf"={explanation.required_energy_kwh:.6f}\;\mathrm{{kWh}}"
    )
    if result.feasible:
        st.success(
            "The selected batteries have sufficient estimated discharge capability to meet the "
            "proposed local commitment. Final delivery feasibility will be assessed during "
            "dispatch optimisation.",
            title="Preliminary Battery Capability Sufficient",
        )
    else:
        st.latex(
            rf"P_{{shortfall}}={commitment:.6f}-{result.capability_kw:.6f}"
            rf"={result.shortfall_kw:.6f}\;\mathrm{{kW}},\quad "
            rf"E_{{shortfall}}={result.shortfall_kw:.6f}\times {duration:g}"
            rf"={explanation.shortfall_energy_kwh:.6f}\;\mathrm{{kWh}}"
        )
        coverage_pct = 100 * result.capability_kw / commitment if commitment > 0 else None
        coverage = f"{coverage_pct:.1f}%" if coverage_pct is not None else "Not applicable"
        st.warning(
            f"The selected batteries can provide an estimated {result.capability_kw:.2f} kW of "
            f"constant discharge over the {duration:g}-hour event, below the proposed local "
            f"commitment of {commitment:.2f} kW.\n\n"
            f"- Available battery capability: {result.capability_kw:.2f} kW\n"
            f"- Power shortfall: {result.shortfall_kw:.2f} kW\n"
            f"- Energy shortfall: {explanation.shortfall_energy_kwh:.2f} kWh\n"
            f"- Commitment coverage: {coverage}\n\n"
            "These batteries can still contribute useful flexibility, but cannot fully satisfy "
            "the proposed commitment. Before making a commitment, the aggregator could reduce "
            "its offer, add more available batteries, or arrange pre-charging where feasible.",
            title="Proposed Commitment Exceeds Available Battery Capability",
        )
    st.caption(
        "Preliminary battery-only assessment. Actual flexibility delivery also depends on "
        "household demand, baseline and grid export constraints."
    )


def render_portfolio() -> None:
    st.title("Portfolio & Configuration")
    st.caption("Manage participating residential batteries and qualify the portfolio for an event.")
    try:
        portfolio = current_portfolio()
    except (ValueError, OSError, KeyError, RuntimeError):
        st.error("The active portfolio could not be read from storage.")
        return
    active = [b for b in portfolio.batteries if b.participating]
    limits = capability(portfolio, DT)
    active_energy = sum(b.initial_soc * b.capacity_kwh for b in active)
    rating = sum(b.discharge_limit_kw for b in active)
    with st.container(horizontal=True, gap="medium"):
        st.metric("Active assets", f"{len(active)} / {len(portfolio.batteries)}", width="content")
        st.metric("Installed capacity", f"{limits.installed_capacity_kwh:g} kWh", width="content")
        st.metric("Initial stored energy", f"{active_energy:.2f} kWh", width="content")
        st.metric("Usable discharge energy", f"{limits.usable_kwh:.2f} kWh", width="content")
        st.metric("Rated discharge power", f"{rating:g} kW", width="content")
    working = _configuration_table()
    _commitment_check(working)
    with st.expander("Default operating economics"):
        defaults = load_defaults("simulation.yaml", SimulationDefaults)
        st.write(
            f"Grid import £{defaults.import_price:.2f}/kWh · grid export credit "
            f"£{defaults.export_price:.2f}/kWh · battery degradation "
            f"£{defaults.degradation_price:.2f}/kWh of throughput."
        )
        st.caption("Set event-specific tariffs, reserves and solver settings in Simulation Lab.")
    technical = st.expander(
        "Battery model and performance", key="portfolio_technical", on_change="rerun"
    )
    if technical.open:
        with technical:
            _mathematical_model()
            _demonstration(working)
