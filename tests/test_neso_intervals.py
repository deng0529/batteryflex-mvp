"""Elapsed-time, source provenance and UK clock-change interval tests."""

from datetime import UTC, date, datetime, timedelta

import pytest

from batteryflex.neso import Sample
from batteryflex.neso_intervals import (
    IntervalError,
    RequirementWindow,
    interval_view,
    local_instant,
    source_window,
)


def instant(value):
    return datetime.fromisoformat(value)


def test_constant_whole_event_expansion_is_explicit_assumption():
    start = instant("2026-01-11T17:00:00+00:00")
    rows = interval_view([RequirementWindow(start, start + timedelta(hours=2), 500, 12, 7)])
    assert len(rows) == 4
    assert all(r["duration_hours"] == 0.5 and r["national_requirement_mw"] == 500 for r in rows)
    assert all("simulation assumption" in r["requirement_basis"] for r in rows)
    assert rows[-1]["end_utc"] == "2026-01-11T19:00:00+00:00"
    assert rows[0]["source_event_id"] == 12 and rows[0]["source_record_id"] == 7


def test_time_varying_half_hours_are_direct_not_averaged():
    start = instant("2024-12-13T16:00:00+00:00")
    rows = interval_view(
        [
            RequirementWindow(
                start + timedelta(minutes=30 * i), start + timedelta(minutes=30 * (i + 1)), mw
            )
            for i, mw in enumerate([500, 100, 500, 100])
        ]
    )
    assert [r["national_requirement_mw"] for r in rows] == [500, 100, 500, 100]
    assert all(r["requirement_basis"].startswith("Directly reported") for r in rows)


def test_partial_end_interval_and_non_grid_source_change():
    start = instant("2026-01-11T17:10:00+00:00")
    rows = interval_view([RequirementWindow(start, start + timedelta(minutes=75), 200)])
    assert [r["duration_hours"] for r in rows] == [0.5, 0.5, 0.25]
    assert rows[-1]["partial_interval"]
    rows = interval_view(
        [
            RequirementWindow(start, start + timedelta(minutes=20), 100),
            RequirementWindow(start + timedelta(minutes=20), start + timedelta(minutes=60), 300),
        ]
    )
    assert [r["duration_hours"] for r in rows] == [1 / 3, 1 / 6, 0.5]
    assert [r["national_requirement_mw"] for r in rows] == [100, 300, 300]


def test_uk_spring_transition_elapsed_duration_is_not_wall_duration():
    start = local_instant(date(2026, 3, 29), "00:30")
    end = local_instant(date(2026, 3, 29), "02:30")
    rows = interval_view([RequirementWindow(start, end, 500)])
    assert len(rows) == 2 and sum(r["duration_hours"] for r in rows) == 1
    assert rows[0]["start_uk"].endswith("00:30:00+00:00")
    assert rows[0]["end_uk"].endswith("02:00:00+01:00")
    with pytest.raises(IntervalError):
        local_instant(date(2026, 3, 29), "01:30")


def test_autumn_ambiguous_time_requires_fold_or_source_utc_evidence():
    day = date(2026, 10, 25)
    with pytest.raises(IntervalError):
        local_instant(day, "01:30")
    first = local_instant(day, "01:30", fold=0)
    second = local_instant(day, "01:30", fold=1)
    assert second - first == timedelta(hours=1)
    assert local_instant(day, "01:30", utc_clock="00:30") == first
    s = Sample("source", "rid", "url", "timestamp", [], [], 0)
    window = source_window(
        s,
        {
            "Delivery Date": "2026-10-25",
            "From_Local": "01:30",
            "To_Local": "01:00",
            "From_UTC": "00:30",
            "To_UTC": "01:00",
            "Service Requirement MW": 500,
        },
    )
    rows = interval_view([window])
    assert len(rows) == 1
    assert rows[0]["start_uk"].endswith("01:30:00+01:00")
    assert rows[0]["end_uk"].endswith("01:00:00+00:00")


def test_overnight_gmt_and_dual_clock_date_rollover():
    s = Sample("source", "rid", "url", "timestamp", [], [], 0)
    w = source_window(
        s,
        {
            "Delivery Date": "2026-01-11",
            "From": "23:30",
            "To": "00:30",
            "Service Requirement MW": 500,
        },
    )
    assert w.end.date() == date(2026, 1, 12)
    assert len(interval_view([w])) == 2
    w = source_window(
        s,
        {
            "Delivery Date": "2026-06-01",
            "From_Local": "23:30",
            "To_Local": "00:30",
            "From_UTC": "22:30",
            "To_UTC": "23:30",
        },
    )
    assert w.start == datetime(2026, 6, 1, 22, 30, tzinfo=UTC)
    assert w.end == datetime(2026, 6, 1, 23, 30, tzinfo=UTC)
    assert interval_view([w])[0]["national_requirement_mw"] is None


@pytest.mark.parametrize("delta", [0, -30, 30])
def test_duplicates_gaps_and_overlaps_rejected(delta):
    t = datetime(2026, 1, 11, 17, tzinfo=UTC)
    first = RequirementWindow(t, t + timedelta(minutes=30), 500)
    second = RequirementWindow(
        t + timedelta(minutes=30 + delta), t + timedelta(minutes=60 + delta), 500
    )
    if delta == 0:
        assert len(interval_view([first, second])) == 2
    else:
        with pytest.raises(IntervalError):
            interval_view([first, second])
    with pytest.raises(IntervalError):
        interval_view([first, first])
    with pytest.raises(IntervalError):
        interval_view([RequirementWindow(t, t, 500)])


def test_naive_timestamps_are_rejected():
    with pytest.raises(IntervalError):
        interval_view([RequirementWindow(datetime(2026, 1, 1), datetime(2026, 1, 1, 1), 500)])
