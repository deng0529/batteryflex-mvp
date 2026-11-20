"""Household screening and explicit cross-period replay, independent of battery models."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from batteryflex.neso_intervals import event_intervals
from batteryflex.neso_manifest import load_selection


def map_day(event_day: date) -> date:
    """Nearest day-of-month in same 2013 month and same weekday; earlier breaks ties."""
    first = date(2013, event_day.month, 1)
    days = [first + timedelta(days=n) for n in range(31)]
    candidates = [d for d in days if d.month == first.month and d.weekday() == event_day.weekday()]
    return min(candidates, key=lambda d: (abs(d.day - event_day.day), d))


def replay(frame: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    events, samples, _ = load_selection()
    valid = frame[frame.quality == "valid"]
    lookup = valid.set_index(["household_id", "interval_end_gmt"]).average_power_kw
    rows = []
    for event in events:
        mapped = map_day(event["delivery_date"])
        for interval in event_intervals(samples[event["resource_id"]], event):
            start = pd.Timestamp(interval["start_utc"])
            end = pd.Timestamp(interval["end_utc"])
            source_start = start.replace(year=2013, month=mapped.month, day=mapped.day)
            source_end = source_start + (end - start)
            row = {
                "scenario_id": event["internal_scenario_id"],
                "neso_date": str(event["delivery_date"]),
                "household_date": str(mapped),
                "neso_start_gmt": start.isoformat(),
                "neso_end_gmt": end.isoformat(),
                "source_start_gmt": source_start.isoformat(),
                "source_end_gmt": source_end.isoformat(),
            }
            for h in ids:
                row[h] = lookup.get((h, source_end), np.nan)
            row["combined_kw"] = sum(float(row[h]) for h in ids)
            rows.append(row)
    return pd.DataFrame(rows)


def statistics(frame: pd.DataFrame) -> pd.DataFrame:
    """Jan–Mar heating-season statistics; incomplete days never count as complete daily energy."""
    base = frame[frame.interval_start_gmt < pd.Timestamp("2013-04-01", tz="UTC")].copy()
    base["day"] = base.interval_start_gmt.dt.date
    valid = base[base.quality == "valid"].copy()
    daily = valid.groupby(["household_id", "day"]).energy_kwh.agg(["count", "sum"])
    complete = daily[daily["count"] == 48]
    grouped = valid.groupby("household_id")
    stats = pd.DataFrame(index=sorted(frame.household_id.unique()))
    stats.index.name = "household_id"
    stats["completeness"] = grouped.energy_kwh.count() / (90 * 48)
    stats["valid_winter_days"] = complete.groupby(level=0)["sum"].count()
    stats["average_daily_kwh"] = complete.groupby(level=0)["sum"].mean()
    stats["peak_kw"] = grouped.average_power_kw.max()
    evening = valid[valid.interval_start_gmt.dt.hour.between(16, 19)]
    stats["mean_evening_kw"] = evening.groupby("household_id").average_power_kw.mean()
    stats["demand_std_kw"] = grouped.average_power_kw.std()
    stats["demand_cv"] = stats.demand_std_kw / grouped.average_power_kw.mean()
    ids = stats.index.tolist()
    windows = replay(frame, ids)[ids]
    stats["event_interval_completeness"] = windows.notna().mean()
    stats["event_mean_kw"] = windows.mean()
    stats["event_min_kw"] = windows.min()
    return stats.fillna({"valid_winter_days": 0, "completeness": 0}).reset_index()


def recommend(stats: pd.DataFrame) -> pd.DataFrame:
    """Quality/availability gate, then five evenly spaced daily-energy representatives."""
    eligible = stats[
        (stats.completeness >= 0.99)
        & (stats.valid_winter_days >= 85)
        & (stats.average_daily_kwh.between(3, 35))
        & (stats.peak_kw <= 15)
        & (stats.event_interval_completeness == 1)
        & (stats.event_min_kw >= 0.05)
        & (stats.event_mean_kw >= 0.3)
    ].sort_values(["average_daily_kwh", "household_id"])
    if len(eligible) < 5:
        raise ValueError(
            f"Only {len(eligible)} households pass declared gates; no invented replacements"
        )
    chosen = eligible.iloc[np.linspace(0, len(eligible) - 1, 5).round().astype(int)].copy()
    chosen["reason"] = [
        f"Daily-energy representative {i + 1}/5; ≥99% coverage, ≥85 full days, "
        "all replay intervals present; ≥0.05 kW each, mean ≥0.3 kW. No battery assumed."
        for i in range(5)
    ]
    return chosen.reset_index(drop=True)
