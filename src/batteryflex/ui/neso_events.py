"""Public presentation of the five frozen Task 02D scenarios."""

import streamlit as st

from batteryflex.neso_intervals import event_intervals
from batteryflex.neso_manifest import load_selection


def reviewed_selection():
    from batteryflex.storage.settings import runtime_repository

    repository, _ = runtime_repository()
    if repository is not None:
        import json

        digest = repository.setting("neso_manifest")
        if not isinstance(digest, str):
            raise ValueError("Stored NESO manifest is missing")
        from batteryflex.storage.repository import canonical

        stored = json.loads(repository.get_object(digest))
        reviewed = load_selection()
        if canonical(stored) != canonical(reviewed[2]):
            raise ValueError("Stored NESO manifest differs from this supported validated selection")
        return reviewed
    return load_selection()


def event_label(event: dict) -> str:
    day = event["delivery_date"]
    date_label = f"{day.day} {day:%B %Y}"
    hours = event["duration_minutes"] / 60
    return (
        f"{date_label} — {event['start_uk'][11:16]}–{event['end_uk'][11:16]} — "
        f"{hours:g} {'hour' if hours == 1 else 'hours'} — "
        f"{float(event['required_mw_by_window']):g} MW"
    )


def render_event_selection() -> None:
    st.header("NESO Flexibility Events")
    st.caption("Five validated historical Live demand-reduction scenarios")
    try:
        events, samples, manifest = reviewed_selection()
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"The reviewed NESO selection is unavailable: {exc}")
        return
    by_id = {event["internal_scenario_id"]: event for event in events}
    selection = st.selectbox(
        "Choose a historical event",
        list(by_id),
        index=None,
        placeholder="Select one of the five validated events",
        format_func=lambda value: event_label(by_id[value]),
        key="neso_public_event",
    )
    st.caption(
        "Historical national NESO requirements in MW; future five-house commitments "
        "will be defined separately in kW."
    )
    if selection is None:
        st.info("Choose an event to view its delivery window and half-hour requirements.")
        return
    event = by_id[selection]
    sample = samples[event["resource_id"]]
    intervals = event_intervals(sample, event)
    with st.container(border=True):
        st.subheader(f"{event['delivery_date'].day} {event['delivery_date']:%B %Y}")
        st.caption("Live · Verified demand-reduction service · All delivery times GMT (UK local)")
        columns = st.columns(4)
        columns[0].metric("Delivery window", f"{event['start_uk'][11:16]}–{event['end_uk'][11:16]}")
        hours = event["duration_minutes"] / 60
        columns[1].metric("Duration", f"{hours:g} {'hour' if hours == 1 else 'hours'}")
        columns[2].metric("National requirement", f"{float(event['required_mw_by_window']):g} MW")
        columns[3].metric("30-minute intervals", len(intervals))
    st.subheader("Event requirements")
    st.caption("Each half-hour requirement below is directly published by NESO.")
    display = [
        {
            "Interval": i["interval_number"],
            "Start (GMT)": i["start_uk"][11:16],
            "End (GMT)": i["end_uk"][11:16],
            "Duration (hours)": i["duration_hours"],
            "National requirement (MW)": i["national_requirement_mw"],
            "Original CKAN row ID": i["source_record_id"],
            "Source resource": sample.source_name,
        }
        for i in intervals
    ]
    st.dataframe(display, hide_index=True, alt="Published half-hour NESO requirements")
    chart_rows = [
        {**i, "start_gmt": i["start_uk"][11:16], "end_gmt": i["end_uk"][11:16]} for i in intervals
    ]
    st.vega_lite_chart(
        chart_rows,
        {
            "mark": {"type": "bar", "orient": "vertical", "tooltip": True},
            "encoding": {
                "x": {
                    "field": "start_utc",
                    "type": "temporal",
                    "scale": {"type": "utc"},
                    "axis": {"format": "%H:%M", "title": "Delivery time (GMT)"},
                },
                "x2": {"field": "end_utc"},
                "y": {
                    "field": "national_requirement_mw",
                    "type": "quantitative",
                    "axis": {"title": "National requirement (MW)"},
                    "scale": {"zero": True, "domainMin": 0},
                },
                "y2": {"datum": 0},
                "tooltip": [
                    {"field": "interval_number", "type": "ordinal", "title": "Interval"},
                    {
                        "field": "start_gmt",
                        "type": "nominal",
                        "title": "Start (GMT)",
                    },
                    {
                        "field": "end_gmt",
                        "type": "nominal",
                        "title": "End (GMT)",
                    },
                    {"field": "national_requirement_mw", "type": "quantitative", "title": "MW"},
                ],
            },
            "height": 260,
        },
        alt="Published national NESO requirement across the event delivery window",
    )
    provenance = st.expander(
        "Event provenance and validation",
        expanded=False,
        on_change="rerun",
        key="neso_public_provenance",
    )
    if provenance.open:
        with provenance:
            st.write("Internal BatteryFlex scenario ID", event["internal_scenario_id"])
            st.caption(event["internal_id_notice"])
            st.write("Original official Event ID", "Absent in the source")
            st.write("Original source resource UUID", sample.resource_id)
            st.markdown(f"[Original official API resource]({sample.source_url})")
            st.caption(
                f"Source acquired {sample.retrieved_at} · Validated {manifest['validated_on']} "
                f"· Selection manifest v{manifest['manifest_version']}"
            )
            st.write("Validation status", event["validation_status"])
            st.markdown(
                f"[Supporting official DFS definition]({event['direction_definition_url']})"
            )
            if event["delivery_date"].year == 2023:
                st.markdown(
                    "[Official winter review: Table 6, Live events]"
                    "(https://www.neso.energy/document/319911/download)"
                )
            st.dataframe(
                [
                    {
                        "Criterion": key.replace("_", " ").capitalize(),
                        "Status": status,
                        "Evidence": event["validation_reasons"][key],
                    }
                    for key, status in event["validation_criteria"].items()
                ],
                hide_index=True,
                alt="Selected event validation evidence",
            )
            st.caption(f"Original record-set SHA-256: {event['source_records_sha256']}")
            st.json([sample.records[i] for i in event["source_rows"]])
    st.caption(manifest["attribution"])
