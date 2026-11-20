"""Read-only analytical views of the existing validated LCL prepared observations.

No ingestion, interpolation or missing-to-zero policy. Dates select interval START
in fixed GMT; original interval-end labels and kWh remain unchanged in source rows.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from batteryflex.portfolio import HOUSEHOLDS


def filter_observations(
    frame: pd.DataFrame, household_ids: tuple[str, ...], start: date, end: date
) -> pd.DataFrame:
    if start > end or not household_ids or len(set(household_ids)) != len(household_ids):
        raise ValueError("Require ordered date bounds and unique nonempty household IDs")
    lower = pd.Timestamp(start, tz="UTC")
    upper = pd.Timestamp(end + timedelta(days=1), tz="UTC")
    return (
        frame[
            frame.household_id.isin(household_ids)
            & frame.interval_start_gmt.between(lower, upper, inclusive="left")
        ]
        .sort_values(["interval_start_gmt", "household_id"])
        .copy()
    )


def historical_series(
    frame: pd.DataFrame, household_ids: tuple[str, ...], start: date, end: date
) -> pd.DataFrame:
    """One aligned observation per half-hour; an aggregate requires ALL selected homes.

    Absent calendar slots remain not_retained, distinct from explicit missing cells.
    Any duplicate or nonvalid member makes the aggregate unavailable.
    """
    source = filter_observations(frame, household_ids, start, end)
    for field in ("interval_start_gmt", "interval_end_gmt"):
        if (
            not isinstance(source[field].dtype, pd.DatetimeTZDtype)
            or str(source[field].dt.tz) != "UTC"
        ):
            raise ValueError("Prepared observations must preserve aware fixed GMT/UTC timestamps")
    if not (source.interval_end_gmt - source.interval_start_gmt).eq(pd.Timedelta(minutes=30)).all():
        raise ValueError("Prepared intervals must be exactly 30 minutes")
    starts = source.interval_start_gmt
    if not (
        starts.dt.minute.isin([0, 30]) & starts.dt.second.eq(0) & starts.dt.microsecond.eq(0)
    ).all():
        raise ValueError("Prepared interval starts must lie on the GMT half-hour grid")
    valid_source = source[source.quality == "valid"]
    if not (
        np.isfinite(valid_source.energy_kwh)
        & np.isfinite(valid_source.average_power_kw)
        & valid_source.energy_kwh.ge(0)
        & (valid_source.average_power_kw - 2 * valid_source.energy_kwh).abs().le(1e-9)
    ).all():
        raise ValueError("Prepared average kW must equal valid nonnegative interval kWh / 0.5")
    index = pd.date_range(
        pd.Timestamp(start, tz="UTC"),
        pd.Timestamp(end + timedelta(days=1), tz="UTC"),
        freq="30min",
        inclusive="left",
        name="interval_start_gmt",
    )
    energies, powers, present, good = [], [], [], []
    for household in household_ids:
        rows = source[source.household_id == household].copy()
        rows["quality"] = rows.quality.astype(object)
        duplicate = rows.duplicated("interval_start_gmt", keep=False)
        rows.loc[duplicate, "quality"] = "duplicate"
        rows = rows.drop_duplicates("interval_start_gmt").set_index("interval_start_gmt")
        aligned = rows.reindex(index)
        valid = aligned.quality.eq("valid") & aligned.energy_kwh.notna()
        energies.append(aligned.energy_kwh.where(valid))
        powers.append(aligned.average_power_kw.where(valid))
        present.append(pd.Series(index.isin(rows.index), index=index))
        good.append(valid)
    all_valid = pd.concat(good, axis=1).all(axis=1)
    all_present = pd.concat(present, axis=1).all(axis=1)
    result = pd.DataFrame(index=index)
    result["interval_end_gmt"] = index + pd.Timedelta(minutes=30)
    result["energy_kwh"] = pd.concat(energies, axis=1).sum(axis=1, min_count=len(household_ids))
    result["average_power_kw"] = pd.concat(powers, axis=1).sum(axis=1, min_count=len(household_ids))
    result["quality"] = "missing_or_invalid"
    result.loc[~all_present, "quality"] = "not_retained"
    result.loc[all_valid, "quality"] = "valid"
    return result.reset_index()


@dataclass(frozen=True)
class LoadSummary:
    start: date
    end: date
    expected_intervals: int
    retained_intervals: int
    valid_intervals: int
    missing_intervals: int  # all unavailable, including absent/invalid; never assumed zero
    not_retained_intervals: int
    complete_days: int
    total_energy_kwh: float | None
    mean_power_kw: float | None
    peak_power_kw: float | None


def summarize_series(series: pd.DataFrame, start: date, end: date) -> LoadSummary:
    valid = series[series.quality == "valid"]
    counts = valid.groupby(valid.interval_start_gmt.dt.date).size()
    return LoadSummary(
        start,
        end,
        len(series),
        int(series.quality.ne("not_retained").sum()),
        len(valid),
        len(series) - len(valid),
        int(series.quality.eq("not_retained").sum()),
        int(counts.eq(48).sum()),
        float(valid.energy_kwh.sum()) if len(valid) else None,
        float(valid.average_power_kw.mean()) if len(valid) else None,
        float(valid.average_power_kw.max()) if len(valid) else None,
    )


def coverage_report(frame: pd.DataFrame) -> list[dict]:
    """Actual retained rows plus longest uninterrupted VALID run for each reviewed home."""
    report = []
    for household in HOUSEHOLDS:
        rows = frame[frame.household_id == household].sort_values("interval_start_gmt")
        if rows.empty:
            report.append({"Household": household, "Available rows": 0})
            continue
        valid = rows[rows.quality == "valid"]
        daily = valid.groupby(valid.interval_start_gmt.dt.date).size()
        starts = valid.interval_start_gmt
        groups = (starts.diff() != pd.Timedelta(minutes=30)).cumsum()
        runs = starts.groupby(groups).agg(["min", "max", "size"])
        longest = runs.sort_values("size", ascending=False).iloc[0] if len(runs) else None
        report.append(
            {
                "Household": household,
                "Earliest interval start (GMT)": str(rows.interval_start_gmt.min()),
                "Latest interval end (GMT)": str(rows.interval_end_gmt.max()),
                "Available rows": len(rows),
                "Valid rows": len(valid),
                "Missing cells": int(rows.quality.eq("missing").sum()),
                "Other invalid rows": int((~rows.quality.isin(["valid", "missing"])).sum()),
                "Complete retained days": int(daily.eq(48).sum()),
                "Longest valid run (half-hours)": int(longest["size"])
                if longest is not None
                else 0,
                "Longest valid start (GMT)": str(longest["min"]) if longest is not None else None,
                "Longest valid end (GMT)": str(longest["max"] + pd.Timedelta(minutes=30))
                if longest is not None
                else None,
            }
        )
    return report


def summary_row(summary: LoadSummary) -> dict:
    return {
        "Start date (GMT)": str(summary.start),
        "End date (GMT)": str(summary.end),
        "Retained half-hours": summary.retained_intervals,
        "Valid half-hours": summary.valid_intervals,
        "Missing/unavailable half-hours": summary.missing_intervals,
        "Of which not retained": summary.not_retained_intervals,
        "Complete days": summary.complete_days,
        "Observed energy (kWh)": summary.total_energy_kwh,
        "Average power (kW)": summary.mean_power_kw,
        "Peak half-hour average power (kW)": summary.peak_power_kw,
    }
