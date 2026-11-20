"""Analytical fixtures only: reused LCL parser, fixed GMT, explicit gaps and valid aggregation."""

from datetime import date

import pandas as pd
import pytest

from batteryflex.forecast_data import (
    coverage_report,
    filter_observations,
    historical_series,
    summarize_series,
)
from batteryflex.lcl import parse_observations
from batteryflex.portfolio import HOUSEHOLDS


def observations():
    rows = []
    for end in pd.date_range("2013-01-01 00:30", periods=96, freq="30min", tz="UTC"):
        for h in HOUSEHOLDS:
            rows.append(
                {
                    "household_id": h,
                    "source_timestamp": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "source_kwh": "0.25",
                }
            )
    return parse_observations(rows)


def test_average_power_conversion_filtering_and_interval_end_alignment():
    frame = observations()
    filtered = filter_observations(frame, (HOUSEHOLDS[0],), date(2013, 1, 1), date(2013, 1, 1))
    assert len(filtered) == 48 and filtered.average_power_kw.eq(0.5).all()
    assert filtered.energy_kwh.eq(0.25).all()
    assert filtered.source_kwh.eq("0.25").all()
    assert filtered.iloc[-1].source_timestamp == "2013-01-02 00:00:00"
    assert filtered.iloc[-1].interval_start_gmt == pd.Timestamp("2013-01-01 23:30", tz="UTC")
    series = historical_series(frame, (HOUSEHOLDS[0],), date(2013, 1, 1), date(2013, 1, 1))
    summary = summarize_series(series, date(2013, 1, 1), date(2013, 1, 1))
    assert summary.valid_intervals == 48 and summary.complete_days == 1
    assert summary.total_energy_kwh == 12 and summary.mean_power_kw == summary.peak_power_kw == 0.5
    assert summary.missing_intervals == 0


def test_aggregated_portfolio_requires_all_households_and_propagates_missing():
    frame = observations()
    day = date(2013, 1, 1)
    good = historical_series(frame, HOUSEHOLDS, day, day)
    assert good.average_power_kw.eq(2.5).all() and good.energy_kwh.eq(1.25).all()
    bad_index = frame.index[0]
    frame.loc[bad_index, ["quality", "energy_kwh", "average_power_kw"]] = ["missing", None, None]
    bad = historical_series(frame, HOUSEHOLDS, day, day)
    assert pd.isna(bad.iloc[0].average_power_kw) and bad.iloc[0].quality == "missing_or_invalid"
    summary = summarize_series(bad, day, day)
    assert summary.valid_intervals == 47 and summary.missing_intervals == 1
    assert summary.total_energy_kwh == 47 * 1.25 and summary.complete_days == 0
    absent = historical_series(frame.iloc[5:], HOUSEHOLDS, day, day)
    assert absent.iloc[0].quality == "not_retained" and pd.isna(absent.iloc[0].energy_kwh)


def test_not_retained_dates_and_no_observations_are_not_zero_consumption():
    series = historical_series(observations(), (HOUSEHOLDS[0],), date(2013, 2, 1), date(2013, 2, 1))
    result = summarize_series(series, date(2013, 2, 1), date(2013, 2, 1))
    assert result.not_retained_intervals == result.missing_intervals == 48
    assert result.total_energy_kwh is result.mean_power_kw is result.peak_power_kw is None


def test_duplicate_readings_are_quarantined_not_summed():
    frame = observations()
    frame = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    frame["quality"] = frame.quality.astype("category")
    series = historical_series(frame, HOUSEHOLDS, date(2013, 1, 1), date(2013, 1, 1))
    assert series.iloc[0].quality != "valid" and pd.isna(series.iloc[0].energy_kwh)


def test_coverage_reports_real_retained_rows_and_valid_continuity():
    report = coverage_report(observations())
    assert len(report) == 5
    assert all(row["Available rows"] == 96 and row["Complete retained days"] == 2 for row in report)
    assert all(row["Longest valid run (half-hours)"] == 96 for row in report)


@pytest.mark.parametrize("bad", ["power", "timezone", "duration", "off_grid"])
def test_invalid_prepared_semantics_are_rejected(bad):
    frame = observations()
    if bad == "power":
        frame.loc[0, "average_power_kw"] = 0.25
    elif bad == "timezone":
        frame["interval_start_gmt"] = frame.interval_start_gmt.dt.tz_localize(None)
    elif bad == "duration":
        frame.loc[0, "interval_end_gmt"] += pd.Timedelta(minutes=30)
    else:
        frame["interval_start_gmt"] += pd.Timedelta(minutes=1)
        frame["interval_end_gmt"] += pd.Timedelta(minutes=1)
    with pytest.raises((ValueError, TypeError)):
        historical_series(frame, HOUSEHOLDS, date(2013, 1, 1), date(2013, 1, 1))
