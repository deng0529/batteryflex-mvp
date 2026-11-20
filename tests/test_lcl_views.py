"""Display aggregates preserve the validated energy/time/quality contract."""

from datetime import date

import pandas as pd

from batteryflex.lcl import parse_observations
from batteryflex.ui.lcl_views import daily_totals, demand_segments, readings_table, typical_profile


def test_complete_day_totals_missing_days_and_unretained_dates():
    rows = []
    for i, end in enumerate(pd.date_range("2013-01-01 00:30", periods=96, freq="30min")):
        rows.append(
            {
                "household_id": "MAC000001",
                "source_timestamp": str(end),
                "source_kwh": "" if i == 48 else "0.25",
            }
        )
    frame = parse_observations(rows)
    totals = daily_totals(
        frame, date(2013, 1, 1), date(2013, 1, 3), {date(2013, 1, 1), date(2013, 1, 2)}
    )
    assert totals.status.tolist() == ["Complete", "Incomplete", "Not retained"]
    assert totals.valid_intervals.tolist() == [48, 47, 0]
    assert totals.energy_kwh.iloc[0] == 12
    assert totals.energy_kwh.iloc[1:].isna().all()
    display = readings_table(frame.iloc[::-1])
    assert display.iloc[0]["Original timestamp — interval END (GMT)"] == "2013-01-01 00:30:00"
    assert display.iloc[0]["Interval start (GMT)"].isoformat() == "2013-01-01T00:00:00+00:00"
    assert display.iloc[0]["Average demand (kW)"] == 0.5
    assert display.iloc[48]["Original energy (kWh)"] == ""
    assert pd.isna(display.iloc[48]["Average demand (kW)"])
    # Midnight END remains part of the previous consumption day.
    assert totals.valid_intervals.iloc[0] == 48
    csv = display.to_csv(index=False)
    assert "2013-01-01 00:30:00" in csv and "interval END" in csv


def test_typical_profile_excludes_missing_and_lines_break_at_gaps():
    frame = parse_observations(
        [
            {"household_id": "MAC000001", "source_timestamp": timestamp, "source_kwh": value}
            for timestamp, value in [
                ("2013-01-01 00:30:00", ".25"),
                ("2013-01-01 01:00:00", ""),
                ("2013-01-01 01:30:00", ".5"),
                ("2013-01-02 00:30:00", ".75"),
            ]
        ]
    )
    profile = typical_profile(frame)
    at_midnight = profile[profile.hour_gmt == 0].iloc[0]
    assert at_midnight.average_power_kw == 1 and at_midnight.valid_readings == 2
    assert 0.5 not in profile.hour_gmt.tolist()  # Missing half-hour never becomes zero.
    plotted = demand_segments(frame)
    assert plotted.segment.nunique() == 3
    assert plotted.average_power_kw.tolist() == [0.5, 1.0, 1.5]
