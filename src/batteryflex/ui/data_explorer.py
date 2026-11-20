"""Permanent Data Explorer with explicit, session-only NESO investigation."""

import streamlit as st

from batteryflex import neso, neso_analysis
from batteryflex.ui.lcl_lab import render_lcl_lab
from batteryflex.ui.neso_events import render_event_selection
from batteryflex.ui.neso_history import render_history_review


def render_neso() -> None:
    st.subheader("NESO")
    st.markdown(f"[Demand Flexibility Service]({neso.PORTAL_URL})")
    st.caption("Supported by National Energy SO Open Data")
    st.info(
        "NESO DFS direction convention: Downwards = demand reduction / generation "
        "increase; Upwards = demand increase / generation reduction. Original labels "
        "are preserved. Directionless archive rows are not inferred."
    )
    source = st.selectbox("Data source", list(neso.RESOURCES), key="neso_source")
    st.caption("Explicit public retrieval · Session only · No import or persistence")
    sample_clicked = st.button("Fetch NESO Sample", key="neso_fetch")
    full_clicked = st.button("Fetch full NESO history", key="neso_fetch_all")
    if sample_clicked or full_clicked:
        st.session_state.pop("neso_sample", None)
        st.session_state.pop("neso_error", None)
        try:
            with st.spinner("Retrieving public NESO records…"):
                st.session_state.neso_sample = (
                    neso.fetch_all(source) if full_clicked else neso.fetch_sample(source)
                )
        except neso.NesoError as exc:
            st.session_state.neso_error = str(exc)
    if st.session_state.get("neso_error"):
        st.error(st.session_state.neso_error)
    sample = st.session_state.get("neso_sample")
    if sample is None or sample.source_name != source:
        st.info("Not fetched. Use either fetch button to connect to this public resource.")
        return
    st.success(f"Connected · Retrieved {len(sample.records)} of {sample.total} source rows")
    st.markdown(f"Request: [exact API URL]({sample.source_url})")
    st.caption(f"Resource ID: {sample.resource_id} · Retrieved (UTC): {sample.retrieved_at}")
    st.caption(
        "Complete retrieval · All source rows available for filtering."
        if sample.complete
        else "Sample only · Filters do not search the full historical dataset."
    )
    if sample.complete:
        st.caption(f"Completed (UTC): {sample.completed_at} · {len(sample.request_urls)} pages")
        with st.expander("Retrieval provenance"):
            st.json(sample.request_urls)
    summary = neso_analysis.coverage(sample)
    st.write(
        f"Coverage: {summary['earliest']} to {summary['latest']} · "
        f"{len(summary['dates'])} delivery dates"
    )
    st.write("Available years", summary["years"])
    st.write("Available year-months", summary["months"])
    with st.expander("All available delivery dates"):
        st.write([str(d) for d in summary["dates"]])
    st.caption(
        f"Exact duplicate business rows (ignoring only _id): "
        f"{summary['exact_duplicate_rows']} · Repeated date/window keys: "
        f"{summary['repeated_window_keys']}. Coincident windows can be distinct events."
    )
    st.dataframe(neso.discover_schema(sample), hide_index=True, alt="Discovered source schema")
    st.write("Standardised field mapping", neso.field_mapping(sample))
    if not sample.records:
        st.warning("NESO returned no records for this resource.")
        return
    rows = neso.standardise(sample)
    dates = sorted({r["delivery_date"] for r in rows if r["delivery_date"] is not None})
    invalid_dates = sum(r["delivery_date"] is None for r in rows)
    if invalid_dates:
        st.warning(f"{invalid_dates} rows have missing or unrecognised delivery dates.")
    year = st.selectbox(
        "Year",
        [None, *sorted({d.year for d in dates})],
        key="neso_year",
        format_func=lambda v: "All" if v is None else str(v),
    )
    months = sorted({d.month for d in dates if year is None or d.year == year})
    month = st.selectbox(
        "Month", [None, *months], format_func=lambda v: "All" if v is None else str(v)
    )
    bounds = st.date_input("Delivery date range", value=[], key="neso_dates")
    start = bounds[0] if len(bounds) else None
    end = bounds[-1] if len(bounds) else None
    categories = {}
    for field, label in (
        ("direction", "Event direction"),
        ("requirement_type", "Service requirement type"),
    ):
        options = sorted({r[field] for r in rows if not neso.missing(r[field])})
        categories[field] = (
            st.selectbox(
                label, [None, *options], format_func=lambda v: "All" if v is None else str(v)
            )
            if options
            else None
        )
        if not options:
            st.caption(f"{label}: unavailable in this sample; no value inferred.")
    filtered = neso.filter_events(rows, year=year, month=month, start=start, end=end, **categories)
    st.write(f"{len(filtered)} matching service-window records")
    st.markdown("**Raw historical records**")
    st.dataframe(
        [sample.records[r["source_row"]] for r in filtered],
        height=350,
        hide_index=True,
        alt="Original NESO records",
    )
    st.markdown("**Standardised events / service windows**")
    st.caption(
        "Times retain source text and time basis. MW is not converted to kW. "
        "A source event may span multiple rows. No synthetic event IDs are assigned."
    )
    st.dataframe(filtered, height=350, hide_index=True, alt="Standardised NESO windows")
    if filtered:
        selected = st.selectbox(
            "Inspect event / service-window record",
            filtered,
            format_func=lambda r: (
                f"Row {r['source_row']} · Event {r['event_id']} · "
                f"{r['delivery_date']} · {r['start_time']}–{r['end_time']}"
            ),
        )
        st.json(sample.records[selected["source_row"]])
        st.write(
            f"This service window requests {selected['required_mw']} MW of "
            f"{selected['direction'] or 'unspecified-direction'} flexibility on "
            f"{selected['delivery_date']}, {selected['start_time']}–{selected['end_time']} "
            f"({selected['time_basis']}). Status: {selected['requirement_type'] or 'unknown'}. "
            "This is a published service requirement, not evidence of delivered flexibility."
        )
        st.write("Bid eligibility", selected["eligible_participants"])
        st.caption(
            "National service MW is not a five-house portfolio commitment. "
            "Bidder lists do not establish household or BatteryFlex eligibility."
        )
        st.caption("Preview only. Selecting and saving five events is deferred.")
    groups = neso_analysis.event_groups(sample)
    st.markdown("**Candidate event screening / date-based archive inspection**")
    st.caption(
        "Groups use original event IDs when present. Archive date groups have "
        "unknown event identity and direction; they are not confirmed candidates. "
        "Durations require contiguous 30-minute windows; MW is never summed over time."
    )
    st.dataframe(groups, hide_index=True, height=350, alt="Event screening and eligibility")
    if groups:
        event = st.selectbox(
            "Explain complete event / archive date group",
            groups,
            format_func=lambda g: (
                f"{g['delivery_date']} · Event {g['event_id'] or 'ID absent'} · "
                f"{g['start_time']}–{g['end_time']}"
            ),
        )
        st.write(
            f"{event['window_count']} source windows · "
            f"Contiguous half-hours: {event['contiguous_30min']} · "
            f"Duration: {event['duration_minutes']} minutes · "
            f"Direction: {event['direction'] or 'absent'} · "
            f"Status: {event['requirement_type'] or 'absent'}. "
            f"{event['screening_reason']}"
        )
        with st.expander("All original records for this event / date group"):
            st.dataframe(
                [sample.records[i] for i in event["source_rows"]],
                hide_index=True,
                alt="Complete original event or archive date group",
            )
    candidate_direction = st.selectbox(
        "Candidate screening direction", ["Downwards", "Upwards"], key="neso_candidate_direction"
    )
    recommended = neso_analysis.recommend_events(sample, direction=candidate_direction)
    if recommended:
        st.markdown("**Task 02B per-source ranking · previous method**")
        st.caption(
            "For the replacement diverse shortlist, use the historical review below. "
            "This preserved ranking prefers requested "
            "winter 2025/26, evening windows, winter months and recent distinct dates. "
            "This table uses the complete retrieved data, independently of row filters."
        )
        st.dataframe(recommended, hide_index=True, alt="Provisional event recommendations")
    else:
        st.info(
            "No candidates for this direction with explicit event ID, Live and valid contiguous "
            "30-minute windows in this retrieval. Missing direction is not assumed."
        )


def render_data_explorer() -> None:
    render_event_selection()
    st.divider()
    if st.toggle("Low Carbon London Data Lab", key="lcl_enabled"):
        render_lcl_lab()
    st.divider()
    if st.toggle("Advanced Historical Explorer", key="neso_advanced"):
        st.caption(
            "Inspect original resources, including Test records. External retrieval "
            "runs only when you use a fetch button."
        )
        st.info(
            "No saved datasets are connected to Turso. The default five events use "
            "the reviewed local selection snapshot."
        )
        st.warning(
            "Historical NESO events and original 2013 Low Carbon London measurements "
            "are from different periods. Any alignment will be an explicit "
            "simulation assumption."
        )
        with st.expander("Data dictionary"):
            from pathlib import Path

            dictionary = Path(__file__).resolve().parents[3] / "docs" / "NESO_DATA_DICTIONARY.md"
            if dictionary.exists():
                st.markdown(dictionary.read_text(encoding="utf-8"))
            else:
                st.write("Source field types and standardised mappings are shown after retrieval.")
        render_neso()
        render_history_review()
