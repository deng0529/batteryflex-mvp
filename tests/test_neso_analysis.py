"""Event screening does not confuse IDs, coincident windows or missing semantics."""

from datetime import date

from batteryflex.neso import Sample, filter_events, standardise
from batteryflex.neso_analysis import coverage, event_groups, recommend_events, unique_records


def sample(records):
    return Sample(
        "source", "resource", "url", "2026-11-16T00:00:00+00:00", records, [], len(records)
    )


def window(event=1, day="2026-11-12", start="17:00", end="17:30", **extra):
    return {
        "Event ID": event,
        "Delivery Date": day,
        "From_UTC": start,
        "To_UTC": end,
        "Service Requirement MW": 500,
        "Event Type": "Downwards",
        "Service Requirement Type": "Live",
        **extra,
    }


def test_exact_dedup_keeps_different_event_direction_and_unknown_fields():
    original = [
        window(_id=1),
        window(_id=2),
        window(event=2, _id=3),
        window(_id=4, **{"Event Type": "Upwards"}),
        window(_id=5, new="x"),
    ]
    unique, duplicates = unique_records(original)
    assert len(unique) == 4 and duplicates == [1]
    assert len(original) == 5
    c = coverage(sample(original))
    assert c["exact_duplicate_rows"] == 1
    assert c["repeated_window_keys"] == 1


def test_whole_event_duration_and_mw_not_sum():
    s = sample([window(), window(start="17:30", end="18:00")])
    g = event_groups(s)[0]
    assert g["duration_minutes"] == 60
    assert g["required_mw_by_window"] == "500.0"
    assert g["window_count"] == 2 and g["contiguous_30min"]
    assert len(recommend_events(s)) == 1


def test_gaps_duplicates_missing_direction_and_tests_do_not_qualify():
    for records in [
        [window(), window(start="18:00", end="18:30")],
        [window(), window()],
        [window(**{"Event Type": None})],
        [window(**{"Service Requirement Type": "Test"})],
        [window(start="23:30", end="00:00")],
        [window(start="17:15", end="17:45")],
        [window(event=None)],
        [window(**{"Service Requirement MW": 0})],
    ]:
        assert recommend_events(sample(records)) == []


def test_archive_unknown_id_and_direction_stay_unknown():
    s = sample(
        [
            {
                "Delivery Date": "2026-01-06",
                "From": "17:00",
                "To": "17:30",
                "Service Requirement MW": 500,
                "Service Requirement Type": "Live",
            }
        ]
    )
    g = event_groups(s)[0]
    assert g["event_id"] is None and g["direction"] is None
    assert recommend_events(s) == []


def test_distinct_dates_and_requested_winter_preferred():
    records = [window(event=i, day=f"2026-10-{i:02}") for i in range(1, 8)]
    records += [window(event=10, day="2026-01-06"), window(event=11, day="2026-01-06")]
    picks = recommend_events(sample(records))
    assert len(picks) == 5 and len({r["delivery_date"] for r in picks}) == 5
    assert picks[0]["delivery_date"] == date(2026, 1, 6)
    rows = standardise(sample(records))
    assert (
        len(
            filter_events(
                rows,
                year=2026,
                month=1,
                requirement_type="Live",
                start=date(2026, 1, 6),
                end=date(2026, 1, 6),
            )
        )
        == 2
    )


def test_dfs_demand_reduction_is_downwards_and_upwards_is_separate():
    s = sample([window(event=1), window(event=2, **{"Event Type": "Upwards"})])
    assert [g["event_id"] for g in recommend_events(s)] == [1]
    assert [g["event_id"] for g in recommend_events(s, direction="Upwards")] == [2]
