"""Display-only summaries over saved observations; no acquisition or selection policy."""

from datetime import date

import pandas as pd

SUMMARY_COLUMNS = {
    "household_id": "Household ID",
    "average_daily_kwh": "Daily energy (kWh/day)",
    "peak_kw": "Peak half-hour demand (kW)",
    "mean_evening_kw": "Evening demand (kW)",
    "completeness": "Completeness (%)",
    "valid_winter_days": "Complete days",
}
READING_COLUMNS = {
    "source_timestamp": "Original timestamp — interval END (GMT)",
    "interval_start_gmt": "Interval start (GMT)",
    "interval_end_gmt": "Interval end (GMT)",
    "source_kwh": "Original energy (kWh)",
    "average_power_kw": "Average demand (kW)",
    "quality": "Data quality",
}


def selection_table(stats: pd.DataFrame) -> pd.DataFrame:
    result = stats[list(SUMMARY_COLUMNS)].copy()
    result["completeness"] *= 100
    return result.rename(columns=SUMMARY_COLUMNS)


def readings_table(rows: pd.DataFrame) -> pd.DataFrame:
    return rows.sort_values("interval_end_gmt")[list(READING_COLUMNS)].rename(
        columns=READING_COLUMNS
    )


def analysis_rows(rows: pd.DataFrame) -> pd.DataFrame:
    return rows[
        rows.interval_start_gmt.between(
            pd.Timestamp("2013-01-01", tz="UTC"),
            pd.Timestamp("2013-04-01", tz="UTC"),
            inclusive="left",
        )
    ]


def daily_totals(
    rows: pd.DataFrame, start: date, end: date, retained_days: set[date]
) -> pd.DataFrame:
    """Never publish a partial-day sum as daily consumption; mark unretained dates separately."""
    valid = rows[rows.quality == "valid"].copy()
    valid["day"] = valid.interval_start_gmt.dt.normalize()
    grouped = valid.groupby("day").agg(
        valid_intervals=("interval_end_gmt", "nunique"), energy_kwh=("energy_kwh", "sum")
    )
    days = pd.date_range(start, end, freq="D", tz="UTC", name="day")
    result = grouped.reindex(days)
    result["valid_intervals"] = result.valid_intervals.fillna(0).astype(int)
    result["status"] = [
        "Not retained" if d.date() not in retained_days else "Complete" if n == 48 else "Incomplete"
        for d, n in zip(result.index, result.valid_intervals, strict=True)
    ]
    result.loc[result.status != "Complete", "energy_kwh"] = float("nan")
    return result.reset_index()


def typical_profile(rows: pd.DataFrame) -> pd.DataFrame:
    valid = rows[rows.quality == "valid"].copy()
    valid["hour_gmt"] = valid.interval_start_gmt.dt.hour + valid.interval_start_gmt.dt.minute / 60
    return (
        valid.groupby(["household_id", "hour_gmt"], observed=True)
        .agg(
            average_power_kw=("average_power_kw", "mean"),
            valid_readings=("average_power_kw", "count"),
        )
        .reset_index()
    )


def demand_segments(rows: pd.DataFrame) -> pd.DataFrame:
    """Break plotted lines at missing, invalid and unretained half-hours, without filling."""
    valid = rows[rows.quality == "valid"].sort_values("interval_start_gmt").copy()
    valid["segment"] = (valid.interval_start_gmt.diff() != pd.Timedelta(minutes=30)).cumsum()
    return valid
