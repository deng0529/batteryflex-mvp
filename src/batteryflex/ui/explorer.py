"""Simplified public exploration, separate from retained research components."""

from datetime import timedelta

import streamlit as st

from batteryflex.defaults import SimulationDefaults, load_defaults
from batteryflex.forecast_data import historical_series, summarize_series, summary_row
from batteryflex.lcl_analysis import map_day
from batteryflex.lcl_source import DOI
from batteryflex.neso_intervals import event_intervals
from batteryflex.ui import lcl_lab
from batteryflex.ui.lcl_charts import demand_chart, profile_chart
from batteryflex.ui.lcl_views import analysis_rows, readings_table, selection_table, typical_profile
from batteryflex.ui.neso_events import event_label, reviewed_selection


def neso_explorer() -> None:
    st.subheader("NESO Flexibility Events")
    st.caption("Five validated historical Live demand-reduction events · Times GMT")
    try:
        events, samples, _ = reviewed_selection()
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Reviewed event data unavailable: {exc}")
        return
    lookup = {e["internal_scenario_id"]: e for e in events}
    chosen = st.selectbox(
        "Choose a historical event",
        list(lookup),
        index=None,
        format_func=lambda key: event_label(lookup[key]),
        key="neso_public_event",
    )

    if chosen is None:
        st.info("Choose an event to view its delivery window and half-hour requirements.")
        return
    event = lookup[chosen]
    intervals = event_intervals(samples[event["resource_id"]], event)
    defaults = load_defaults("simulation.yaml", SimulationDefaults)
    energy_mwh = sum(i["national_requirement_mw"] * i["duration_hours"] for i in intervals)
    with st.container(border=True):
        st.markdown(f"**{event['delivery_date']:%d %B %Y} · Live · Validated demand reduction**")
        columns = st.columns(3)
        columns[0].metric(
            "Delivery window (GMT)", f"{event['start_uk'][11:16]}–{event['end_uk'][11:16]}"
        )
        columns[1].metric("Duration", f"{event['duration_minutes'] / 60:g} h")
        columns[2].metric("National requirement", f"{float(event['required_mw_by_window']):g} MW")
        st.caption(
            f"{len(intervals)} original half-hour intervals · "
            f"National requirement energy equivalent: {energy_mwh:g} MWh"
        )
    st.dataframe(
        [
            {
                "Interval start (GMT)": i["start_uk"][11:16],
                "Interval end (GMT)": i["end_uk"][11:16],
                "Duration (hours)": i["duration_hours"],
                "National requirement (MW)": i["national_requirement_mw"],
                "Energy equivalent (MWh)": i["national_requirement_mw"] * i["duration_hours"],
            }
            for i in intervals
        ],
        hide_index=True,
        alt="Original NESO half-hour requirements and energy equivalents",
    )
    st.caption(
        "Energy equivalent = sum of published MW × interval hours; "
        "this is requested energy, not achieved delivery."
    )
    st.caption(
        f"Default simulated portfolio obligation: {defaults.target_kw:g} kW · "
        f"{defaults.target_kw * event['duration_minutes'] / 60:g} kWh. "
        "Set the obligation for a run in Simulation Lab."
    )
    replay_day = map_day(event["delivery_date"])
    st.caption(f"Historical replay uses Low Carbon London demand from {replay_day:%d %B %Y}.")
    st.markdown(f"[Official NESO source]({samples[event['resource_id']].source_url})")
    st.caption("Supported by National Energy SO Open Data")


def lcl_explorer() -> None:
    st.subheader("Low Carbon London")
    st.caption("Study area: London · Anonymised household IDs; addresses are unavailable")
    st.markdown(f"[4TU.ResearchData · Low Carbon London, version 1 · CC BY 4.0]({DOI})")
    st.caption(
        "Original consumption period: calendar 2013. Prepared dates only: "
        "1 January–31 March, 7 November and 6 December 2013; not a complete annual profile."
    )
    manifest = lcl_lab.DATA_DIRECTORY / "audit.json"
    from batteryflex.storage.settings import runtime_repository

    try:
        repository, _ = runtime_repository()
    except (ValueError, OSError) as exc:
        st.error(f"Persistent storage unavailable: {exc}")
        return
    if not manifest.exists() and repository is None:
        st.info(
            "Prepared household data is unavailable. Restore the reviewed local artifacts; "
            "this page does not download data."
        )
        return
    try:
        frame, _, selected, _, _ = lcl_lab.load_prepared(
            str(lcl_lab.DATA_DIRECTORY), manifest.stat().st_mtime_ns if manifest.exists() else 0
        )
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"Prepared household data unavailable: {exc}")
        return
    view = st.segmented_control(
        "Household view",
        ["Household", "Five-household comparison"],
        default="Household",
        key="lcl_public_view",
    )
    if view == "Five-household comparison":
        st.dataframe(
            selection_table(selected),
            hide_index=True,
            alt="Five recommended household consumption statistics",
        )
        st.caption(
            "Typical half-hour demand, valid January–March 2013 readings only. "
            "These five examples are not representative of all UK households."
        )
        profile_chart(
            typical_profile(analysis_rows(frame[frame.household_id.isin(selected.household_id)])),
            compare=True,
        )
        return
    household = st.selectbox(
        "Choose a household", selected.household_id.tolist(), index=None, key="lcl_public_household"
    )
    if household is None:
        st.info("Choose one of the five recommended households to inspect original consumption.")
        return
    rows = frame[frame.household_id == household].sort_values("interval_end_gmt")
    st.markdown(f"**Household {household} · London**")
    first, last = rows.interval_start_gmt.dt.date.min(), rows.interval_start_gmt.dt.date.max()
    st.markdown("**Full Study-Period Summary**")
    st.dataframe(
        [
            summary_row(
                summarize_series(historical_series(rows, (household,), first, last), first, last)
            )
        ],
        hide_index=True,
        alt="Full available retained study-period energy, power and coverage",
    )
    st.caption(
        "Full summary uses all retained study dates, including November/December replay days. "
        "Calendar gaps not retained are separate from missing source cells. Energy is the observed "
        "valid sum, not an estimate for unavailable intervals; peak is half-hour average power."
    )
    days = rows.interval_start_gmt.dt.date
    bounds = st.date_input(
        "Observation date range (GMT)",
        value=(days.min(), days.min() + timedelta(days=6)),
        min_value=days.min(),
        max_value=days.max(),
        key="lcl_public_dates",
    )
    if len(bounds) != 2:
        st.info("Choose both date bounds.")
        return
    selected_rows = rows[(days >= bounds[0]) & (days <= bounds[1])]
    st.markdown("**Selected Observation-Range Summary**")
    st.dataframe(
        [
            summary_row(
                summarize_series(
                    historical_series(rows, (household,), bounds[0], bounds[1]),
                    bounds[0],
                    bounds[1],
                )
            )
        ],
        hide_index=True,
        alt="Summary recalculated for the selected observation dates",
    )
    st.caption(
        f"Displayed: {bounds[0]}–{bounds[1]} GMT. Original source timestamps mark interval "
        "END: 18:30 covers 18:00–18:30. Average kW = measured kWh / 0.5. Missing stays missing."
    )
    if selected_rows.empty:
        st.info("No observations were retained for this date range.")
        return
    demand_chart(selected_rows)
    detail = st.expander(
        "Original half-hour readings", key="lcl_original_readings", on_change="rerun"
    )
    if detail.open:
        with detail:
            st.dataframe(
                readings_table(selected_rows),
                hide_index=True,
                alt="Chronological original interval-end readings, kWh and average kW",
            )


def render_data_explorer() -> None:
    st.title("Data Explorer")
    st.caption("Inspect historical service requirements and measured household demand.")
    tabs = st.tabs(
        ["NESO Flexibility Events", "Low Carbon London"], key="data_tabs", on_change="rerun"
    )
    if tabs[0].open:
        with tabs[0]:
            neso_explorer()
    if tabs[1].open:
        with tabs[1]:
            lcl_explorer()
