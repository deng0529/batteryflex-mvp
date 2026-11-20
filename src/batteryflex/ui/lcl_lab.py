"""Local prepared-data exploration. No downloads or source parsing on app reruns."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from batteryflex.lcl_source import DOI, LICENSE, digest
from batteryflex.neso_intervals import event_intervals
from batteryflex.ui import lcl_charts as charts
from batteryflex.ui.lcl_views import (
    analysis_rows,
    daily_totals,
    readings_table,
    selection_table,
    typical_profile,
)
from batteryflex.ui.neso_events import event_label, reviewed_selection

DATA_DIRECTORY = Path(__file__).resolve().parents[3] / "data" / "lcl" / "prepared"


@st.cache_data(show_spinner=False, max_entries=2)
def _load_local_prepared(directory: str, revision: int) -> tuple:
    """Cache the local subset, invalidated by the preparation manifest's modification time."""
    path = Path(directory)
    audit = json.loads((path / "audit.json").read_text(encoding="utf-8"))
    if audit["parser_version"] != 1:
        raise ValueError("Unsupported LCL preparation version")
    for name, expected in audit["artifacts"].items():
        if Path(name).name != name or digest(path / name) != expected:
            raise ValueError("Prepared dataset integrity check failed; rerun preparation")
    return (
        pd.read_parquet(path / "observations.parquet"),
        pd.read_csv(path / "candidates.csv"),
        pd.read_csv(path / "recommended.csv"),
        pd.read_csv(path / "replay.csv"),
        audit,
    )


def load_prepared(directory: str, revision: int) -> tuple:
    from batteryflex.storage.settings import runtime_repository

    repository, _ = runtime_repository()
    if repository is not None:
        from batteryflex.storage.bootstrap import load_prepared as load_stored

        return load_stored(repository)
    return _load_local_prepared(directory, revision)


def overview(candidates: pd.DataFrame, selected: pd.DataFrame, audit: dict) -> None:
    with st.container(border=True):
        st.markdown("**Low Carbon London smart meter data · 4TU.ResearchData**")
        st.caption("Simon Tindemans (2023), version 1 · Original measurements: UK Power Networks")
        cols = st.columns(3)
        cols[0].metric("Original households", f"{audit['household_count']:,}")
        cols[1].metric("Prepared for exploration", len(candidates))
        cols[2].metric("Recommended households", len(selected))
        st.caption(
            "Original consumption period: 1 January–31 December 2013. "
            "Prepared dates: 1 January–31 March, 7 November and 6 December 2013."
        )
        st.caption(
            "30-minute readings · Original energy: kWh per interval · Derived average power: kW · "
            "Fixed GMT throughout, including summer."
        )
        st.markdown(f"[Dataset and provenance]({DOI}) · [CC BY 4.0]({LICENSE})")


def summary_table(stats: pd.DataFrame, recommended: set[str] | None = None) -> None:
    display = selection_table(stats)
    if recommended is not None:
        display.insert(1, "Recommended", stats.household_id.isin(recommended).to_numpy())
    st.dataframe(
        display,
        hide_index=True,
        key="lcl_selection_table",
        column_config={
            name: st.column_config.NumberColumn(format="%.2f")
            for name in display.columns
            if "(" in name
        },
        alt="Household selection, energy, power, completeness and complete days",
    )


def household_explorer(
    frame: pd.DataFrame, candidates: pd.DataFrame, selected: pd.DataFrame, audit: dict
) -> None:
    st.subheader("Household Explorer")
    recommended = set(selected.household_id)
    scope = st.segmented_control(
        "Household list",
        ["Recommended five", "All prepared candidates"],
        default="Recommended five",
        key="lcl_scope",
    )
    choices = selected if scope != "All prepared candidates" else candidates
    household = st.selectbox(
        "Choose a household",
        choices.household_id.tolist(),
        index=None,
        placeholder="Search by exact household ID",
        key="lcl_household",
        format_func=lambda h: f"{h} · Recommended" if h in recommended else h,
    )
    st.caption("Summary statistics below use 1 January–31 March 2013 (90 heating-season days).")
    summary_table(choices, recommended if scope == "All prepared candidates" else None)
    if household is None:
        st.info("Choose one household to view its summary, original readings and charts.")
        return
    rows = frame[frame.household_id == household].sort_values("interval_end_gmt").copy()
    stats = candidates[candidates.household_id == household].iloc[0]
    base = analysis_rows(rows)
    valid = base[base.quality == "valid"]
    st.subheader(f"Household {household}")
    st.caption(
        "Recommended household" if household in recommended else "Prepared candidate household"
    )
    with st.container(border=True):
        cols = st.columns(3)
        cols[0].metric(
            "Average daily energy",
            f"{stats.average_daily_kwh:.2f} kWh/day",
            help="Average over complete 48-interval days in January–March 2013.",
        )
        cols[1].metric(
            "Peak half-hour demand",
            f"{stats.peak_kw:.3f} kW",
            help="Highest half-hour average power in January–March; not instantaneous peak.",
        )
        cols[2].metric(
            "Data completeness",
            f"{stats.completeness * 100:.3f}%",
            help="Valid unique January–March readings divided by 4,320 expected half-hours.",
        )
        st.caption(
            f"{int(stats.valid_winter_days)} complete analysis days · "
            f"{int((base.quality == 'missing').sum())} missing analysis readings · "
            f"{int((rows.quality == 'missing').sum())} missing readings across all retained dates"
        )
    info = st.expander("Household information and statistics", on_change="rerun", key="lcl_info")
    if info.open:
        with info:
            st.write("Source dataset: Low Carbon London smart meter data (refactored), 4TU v1.")
            st.write(
                "Prepared observation dates: 1 January–31 March, 7 November, 6 December 2013. "
                "The intervening dates were not retained in this exploration subset."
            )
            st.write(
                f"Original end labels for this household: {rows.source_timestamp.iloc[0]} to "
                f"{rows.source_timestamp.iloc[-1]} (GMT). These are timestamp bounds, "
                "not continuous coverage of the intervening months."
            )
            st.caption("30 minutes · Original kWh per interval · Derived average kW = kWh / 0.5")
            st.info(
                "Anonymised ID only. Address, postcode, occupants, property type, appliances "
                "and installed batteries are unavailable in this dataset."
            )
            values = [
                ("Average daily energy", stats.average_daily_kwh, "kWh/day"),
                ("Average power", valid.average_power_kw.mean(), "kW"),
                ("Peak half-hour average demand", stats.peak_kw, "kW"),
                ("Mean evening demand (16:00–20:00 GMT)", stats.mean_evening_kw, "kW"),
                ("Minimum observed half-hour demand", valid.average_power_kw.min(), "kW"),
                ("Demand standard deviation", stats.demand_std_kw, "kW"),
                ("Coefficient of variation", stats.demand_cv, "dimensionless"),
                ("Data completeness", stats.completeness * 100, "%"),
                ("Complete days", stats.valid_winter_days, "days"),
            ]
            st.dataframe(
                pd.DataFrame(values, columns=["Statistic", "Value", "Unit"]),
                hide_index=True,
                alt="Selected household consumption statistics",
            )
            st.caption(
                "All statistics use January–March 2013. Average/minimum power use valid "
                "half-hours only; daily energy uses complete days only. Standard deviation "
                "uses ddof=1; coefficient of variation = standard deviation / mean power. "
                "Missing readings never count as zero."
            )
    days = rows.interval_start_gmt.dt.date
    bounds = st.date_input(
        "Observation date range (GMT interval start)",
        value=(days.min(), days.min() + pd.Timedelta(days=6)),
        min_value=days.min(),
        max_value=days.max(),
        key="lcl_dates",
    )
    if len(bounds) != 2:
        st.info("Choose both date bounds to inspect readings and charts.")
        return
    filtered = rows[(days >= bounds[0]) & (days <= bounds[1])]
    st.caption(f"Selected household: {household} · Displayed range: {bounds[0]} to {bounds[1]} GMT")
    st.subheader("Original household electricity readings")
    st.caption(
        "Original timestamps mark interval END: 18:30 covers 18:00–18:30 GMT. "
        "Energy is measured kWh; average demand is derived as kWh / 0.5. "
        "Blank or invalid readings remain missing."
    )
    if filtered.empty:
        st.info(
            "No observations were retained for this range. Choose January–March, "
            "7 November or 6 December 2013."
        )
        return
    display = readings_table(filtered)
    st.dataframe(
        display, hide_index=True, alt="Chronological original household electricity readings"
    )
    st.download_button(
        "Download selected readings as CSV",
        display.to_csv(index=False).encode("utf-8"),
        file_name=f"{household}_{bounds[0]}_{bounds[1]}.csv",
        mime="text/csv",
        key="lcl_download",
    )
    st.subheader("Half-hour electricity demand")
    st.caption(
        "Scroll over the chart to zoom, drag to pan, double-click to reset; hover for readings. "
        "Lines break at missing and unretained intervals."
    )
    charts.demand_chart(filtered)
    st.subheader("Daily electricity consumption")
    retained = {date.fromisoformat(d) for d in audit["retained_days"]}
    daily = daily_totals(filtered, bounds[0], bounds[1], retained)
    charts.daily_chart(daily)
    st.caption(
        "Daily totals require all 48 valid half-hours. The coverage strip marks incomplete "
        "and unretained days; neither receives a zero or partial-day total."
    )
    quality = st.expander("Daily coverage details", on_change="rerun", key="lcl_daily_quality")
    if quality.open:
        with quality:
            st.dataframe(daily, hide_index=True, alt="Daily completeness and valid full-day energy")
    st.subheader("Typical daily demand profile")
    st.caption(
        f"Mean by half-hour of day, using valid readings for {household} within "
        f"{bounds[0]}–{bounds[1]} only. Missing observations are excluded, never zero-filled."
    )
    charts.profile_chart(typical_profile(filtered))


def comparison(frame: pd.DataFrame, selected: pd.DataFrame) -> None:
    st.subheader("Five-Household Comparison")
    st.caption("January–March 2013 · The same five reviewed households throughout")
    summary_table(selected)
    st.info(
        "These illustrative lower-, middle- and higher-consumption examples are not "
        "statistically representative of all UK households. No physical batteries are assumed."
    )
    charts.profile_chart(
        typical_profile(analysis_rows(frame[frame.household_id.isin(selected.household_id)])),
        compare=True,
    )
    st.caption(
        "Typical profiles average valid half-hour readings in January–March 2013. "
        "Each household keeps the same colour across all comparison and replay charts."
    )
    cols = st.columns(2)
    for index, (field, label) in enumerate(
        [
            ("average_daily_kwh", "Average daily energy (kWh/day)"),
            ("mean_evening_kw", "Mean evening demand (kW)"),
            ("peak_kw", "Peak half-hour demand (kW)"),
            ("completeness_pct", "Data completeness (%)"),
        ]
    ):
        with cols[index % 2]:
            st.markdown(f"**{label}**")
            charts.comparison_chart(
                selected.assign(completeness_pct=selected.completeness * 100), field, label
            )


def event_replay(replay: pd.DataFrame, selected: pd.DataFrame) -> None:
    st.subheader("NESO Event Replay — Five Households")
    st.caption("Synthetic historical replay using real household measurements")
    events, samples, _ = reviewed_selection()
    by_date = {str(e["delivery_date"]): e for e in events}
    event_date = st.selectbox(
        "Choose a validated NESO Live event",
        list(by_date),
        index=None,
        format_func=lambda d: event_label(by_date[d]),
        placeholder="Select one of the five events",
        key="lcl_event",
    )
    if event_date is None:
        st.info("Choose an event to view its original delivery window and five-household replay.")
        return
    event = by_date[event_date]
    rows = replay[replay.neso_date == event_date]
    with st.container(border=True):
        st.markdown(f"**NESO: {event_date} · Live · Verified demand reduction**")
        cols = st.columns(4)
        cols[0].metric(
            "Delivery window (GMT)", f"{event['start_uk'][11:16]}–{event['end_uk'][11:16]}"
        )
        cols[1].metric("Duration", f"{event['duration_minutes'] / 60:g} hours")
        cols[2].metric("National requirement", f"{float(event['required_mw_by_window']):g} MW")
        cols[3].metric("Original half-hour intervals", len(rows))
    st.write(f"Original LCL observation date: **{rows.household_date.iloc[0]}** (GMT).")
    st.info(
        "Mapping v1 uses the same month and exact weekday in 2013, then the nearest day "
        "number (earlier date on ties). The original household reading marks interval END. "
        "Household observations and NESO events were recorded in different years."
    )
    st.caption(
        "Household demand is in kW. The national NESO requirement above is in MW and "
        "is not a household or portfolio flexibility target."
    )
    ids = selected.household_id.tolist()
    display = rows[
        [
            "neso_date",
            "household_date",
            "neso_start_gmt",
            "neso_end_gmt",
            "source_start_gmt",
            "source_end_gmt",
            *ids,
            "combined_kw",
        ]
    ].rename(
        columns={
            "neso_date": "Original NESO date",
            "household_date": "Original LCL date",
            "neso_start_gmt": "NESO interval start (GMT)",
            "neso_end_gmt": "NESO interval end (GMT)",
            "source_start_gmt": "LCL interval start (GMT)",
            "source_end_gmt": "LCL original interval END (GMT)",
            "combined_kw": "Combined demand (kW)",
            **{h: f"{h} (kW)" for h in ids},
        }
    )
    st.dataframe(
        display, hide_index=True, alt="All original NESO and LCL half-hours with five-house demand"
    )
    charts.replay_chart(rows, ids)
    national = st.expander(
        "Original NESO national requirement (MW)", on_change="rerun", key="lcl_national"
    )
    if national.open:
        with national:
            intervals = pd.DataFrame(event_intervals(samples[event["resource_id"]], event))
            st.caption("Published national requirements only; separate from household kW.")
            st.vega_lite_chart(
                intervals,
                {
                    "height": 180,
                    "mark": {"type": "bar", "tooltip": True},
                    "encoding": {
                        "x": {
                            "field": "start_utc",
                            "type": "temporal",
                            "scale": {"type": "utc"},
                            "axis": {"title": "NESO interval start (GMT)", "format": "%H:%M"},
                        },
                        "x2": {"field": "end_utc"},
                        "y": {
                            "field": "national_requirement_mw",
                            "type": "quantitative",
                            "axis": {"title": "National requirement (MW)"},
                        },
                    },
                },
                alt="Original published national NESO requirement in MW",
            )
    st.caption(
        "Observed demand alone does not establish battery feasibility or deliverable flexibility."
    )


def provenance(audit: dict) -> None:
    st.subheader("Data Quality & Provenance")
    st.markdown(f"[Versioned 4TU dataset]({DOI}) · [CC BY 4.0]({LICENSE})")
    st.write(
        "Standard-tariff London households, observed in 2013. Original data: UK Power Networks. "
        "Prepared sample: 100 households, 90 January–March heating-season days and two replay days."
    )
    st.caption(
        "March is a heating-season shoulder month. The 2013 source period is broader "
        "than the particular dates retained for exploration."
    )
    st.write(
        "Timestamp contract: fixed GMT interval END; average kW = measured kWh / 0.5. "
        "Missing/invalid values stay missing, duplicate keys are quarantined. "
        "Only complete 48-interval days contribute daily totals."
    )
    st.caption(
        "Recommendation and calendar mapping policies are unchanged from the Task 03 review."
    )
    advanced = st.expander(
        "Advanced provenance and raw-data diagnostics", on_change="rerun", key="lcl_audit"
    )
    if advanced.open:
        with advanced:
            st.json({k: v for k, v in audit.items() if k not in ("household_ids", "sample_ids")})


def render_lcl_lab() -> None:
    st.header("Low Carbon London Data Lab")
    st.caption(
        "Explore real household electricity measurements, then compare historical event replays."
    )
    manifest = DATA_DIRECTORY / "audit.json"
    from batteryflex.storage.settings import runtime_repository

    try:
        repository, _ = runtime_repository()
    except (ValueError, OSError) as exc:
        st.error(f"Persistent household data unavailable: {exc}")
        return
    if not manifest.exists() and repository is None:
        st.info(
            "No prepared local LCL data. Restore the reviewed artifacts to data/lcl/prepared. "
            "This page does not acquire or reprocess data."
        )
        return
    try:
        frame, candidates, selected, replay, audit = load_prepared(
            str(DATA_DIRECTORY), manifest.stat().st_mtime_ns if manifest.exists() else 0
        )
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Prepared Low Carbon London data unavailable: {exc}")
        return
    overview(candidates, selected, audit)
    section = st.segmented_control(
        "Explore the Data Lab",
        [
            "Household Explorer",
            "Five-Household Comparison",
            "NESO Event Replay",
            "Data Quality & Provenance",
        ],
        default="Household Explorer",
        key="lcl_section",
    )
    if section == "Five-Household Comparison":
        comparison(frame, selected)
    elif section == "NESO Event Replay":
        event_replay(replay, selected)
    elif section == "Data Quality & Provenance":
        provenance(audit)
    else:
        household_explorer(frame, candidates, selected, audit)
