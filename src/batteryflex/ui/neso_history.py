"""Cross-resource historical review and interval inspection, without persistence."""

import streamlit as st

from batteryflex import neso
from batteryflex.neso_intervals import IntervalError, event_intervals
from batteryflex.neso_selection import (
    availability,
    duration_distribution,
)
from batteryflex.neso_validation import final_recommendations, validated_groups


def render_history_review() -> None:
    st.subheader("Diverse historical event review")
    st.caption(
        "National NESO requirements are MW. Future five-house commitments will be "
        "separate kW values; no scaling or commitment is assigned here."
    )
    if st.button("Fetch all historical requirement resources", key="neso_fetch_histories"):
        st.session_state.pop("neso_histories", None)
        st.session_state.pop("neso_histories_error", None)
        try:
            with st.spinner("Retrieving all three complete official requirement resources…"):
                samples = [neso.fetch_all(name) for name in neso.RESOURCES]
            st.session_state.neso_histories = samples
        except neso.NesoError as exc:
            st.session_state.neso_histories_error = str(exc)
    if st.session_state.get("neso_histories_error"):
        st.error(st.session_state.neso_histories_error)
    samples = st.session_state.get("neso_histories", [])
    if not samples:
        st.info("Fetch complete histories to compare years, months and provisional events.")
        return
    st.success(f"Complete cross-resource review: {sum(len(s.records) for s in samples)} rows")
    st.caption(
        "Includes the official 2023/24 requirement archive. Older raw direction and "
        "event ID remain absent. Demand-reduction interpretation is a separate, "
        "documented service-regime annotation; date groups are not confirmed event keys."
    )
    st.markdown(
        "[NESO service history and 9 April 2026 bidirectional change]"
        "(https://www.neso.energy/industry-information/balancing-services/demand-flexibility-service-dfs)"
    )
    st.dataframe(
        availability(samples), hide_index=True, alt="Historical availability by year and month"
    )
    st.dataframe(
        duration_distribution(samples),
        hide_index=True,
        alt="Demand-reduction event and date-group duration distribution",
    )
    with st.expander("Complete historical retrieval provenance"):
        st.json(
            [
                {
                    "source": s.source_name,
                    "resource_id": s.resource_id,
                    "retrieved_at": s.retrieved_at,
                    "completed_at": s.completed_at,
                    "rows": len(s.records),
                    "request_urls": s.request_urls,
                }
                for s in samples
            ]
        )
    recommendations = final_recommendations(samples)
    st.markdown("**Validated Live-only scenario shortlist · final recommendations for review**")
    st.caption(
        "Target mixture: two 1h, two 1.5–2h, one 2–3h. Actual complete source "
        "windows take priority. Original IDs may be absent; row references are shown. "
        "Only events with PASS for every mandatory criterion enter this shortlist. "
        "Internal scenario IDs are BatteryFlex identifiers, never official NESO IDs."
    )
    st.dataframe(recommendations, hide_index=True, alt="Validated Live-only five-event comparison")
    st.dataframe(
        [
            {
                "internal_scenario_id": g["internal_scenario_id"],
                "delivery_date": g["delivery_date"],
                **g["validation_criteria"],
                "overall": g["validation_status"],
            }
            for g in recommendations
        ],
        hide_index=True,
        alt="Final event validation matrix",
    )
    st.caption(
        "Live is checked in every original Service Requirement Type value. "
        "Older direction verification cites applicable official DFS definitions; "
        "no Live status or raw direction is filled from unrelated fields. "
        "These are recommended historical scenario inputs, not saved simulation runs."
    )
    mode = st.selectbox(
        "Interval detail scope",
        ["Final Live-only recommendations", "All historical groups"],
        key="neso_detail_scope",
    )
    pool = (
        recommendations if mode == "Final Live-only recommendations" else validated_groups(samples)
    )
    status = st.selectbox(
        "Review Live/Test status", ["Live", "Test", "All"], key="neso_review_status"
    )
    st.caption(
        "Detail filters below do not change the validated Live-only comparison above. "
        "Use All historical groups and Test to inspect excluded test records."
    )
    if status != "All":
        pool = [g for g in pool if g["requirement_type"] == status]
    year = st.selectbox(
        "Review year",
        [None, *sorted({g["delivery_date"].year for g in pool if g["delivery_date"] is not None})],
        format_func=lambda v: "All" if v is None else str(v),
    )
    if year is not None:
        pool = [
            g for g in pool if g["delivery_date"] is not None and g["delivery_date"].year == year
        ]
    month = st.selectbox(
        "Review month",
        [None, *sorted({g["delivery_date"].month for g in pool if g["delivery_date"] is not None})],
        format_func=lambda v: "All" if v is None else str(v),
    )
    if month is not None:
        pool = [
            g for g in pool if g["delivery_date"] is not None and g["delivery_date"].month == month
        ]
    delivery_date = st.selectbox(
        "Review delivery date",
        [None, *sorted({g["delivery_date"] for g in pool if g["delivery_date"] is not None})],
        format_func=lambda v: "All" if v is None else str(v),
    )
    if delivery_date is not None:
        pool = [g for g in pool if g["delivery_date"] == delivery_date]
    durations = sorted({g["duration_minutes"] for g in pool if g["duration_minutes"] is not None})
    duration = st.selectbox(
        "Event duration (minutes)",
        [None, *durations],
        format_func=lambda v: "All" if v is None else f"{v:g}",
        key="neso_duration",
    )
    if duration is not None:
        pool = [g for g in pool if g["duration_minutes"] == duration]
    if not pool:
        st.info("No historical groups match the duration filter.")
        return
    selected = st.selectbox(
        "Selected historical event / date group",
        pool,
        format_func=lambda g: (
            f"{g['delivery_date']} · {g['source_name']} · "
            f"Event ID {g['event_id'] if g['event_id'] is not None else 'absent'} · "
            f"{g['duration_minutes']} minutes"
        ),
        key="neso_interval_event",
    )
    st.write("Internal BatteryFlex scenario ID", selected["internal_scenario_id"])
    st.caption(selected["internal_id_notice"])
    st.write("Validation status", selected["validation_status"])
    st.dataframe(
        [
            {"criterion": name, "status": value, "reason": selected["validation_reasons"][name]}
            for name, value in selected["validation_criteria"].items()
        ],
        hide_index=True,
        alt="Selected event validation criteria",
    )
    if selected["direction_definition_url"]:
        st.markdown(
            f"[Applicable official direction definition]({selected['direction_definition_url']})"
        )
    st.write(selected["identity_basis"])
    st.write("Original bid eligibility", selected["eligible_participants"])
    st.write("Original zonal cap", selected["zonal_cap"])
    sample = next(s for s in samples if s.resource_id == selected["resource_id"])
    with st.expander("Original records behind the selected event"):
        st.json([sample.records[i] for i in selected["source_rows"]])
    try:
        intervals = event_intervals(sample, selected)
    except (IntervalError, ValueError, KeyError) as exc:
        st.warning(f"Interval view unavailable: {exc}")
        return
    st.markdown("**30-minute interval view**")
    st.caption(
        "Intervals use elapsed UTC time, with offset-qualified Europe/London clocks. "
        "Partial boundary pieces are retained. Source changes are never averaged. "
        "Repeating an event-wide requirement is explicitly labelled as a simulation "
        "assumption; directly reported half-hours retain their own MW values."
    )
    st.dataframe(intervals, hide_index=True, alt="Selected event requirement intervals")
    st.bar_chart(
        intervals,
        x="interval_number",
        y="national_requirement_mw",
        x_label="Interval number",
        y_label="National requirement (MW)",
        alt="National NESO requirement by delivery interval",
    )
