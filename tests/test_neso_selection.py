"""Contextual evidence remains separate from absent raw direction and source IDs."""

from batteryflex.neso import Sample
from batteryflex.neso_selection import (
    availability,
    diverse_recommendations,
    duplicate_events,
    historical_groups,
)


def archive(day="2025-11-06", resource="f5605e2b-b677-424c-8df7-d0ce4ee03cef"):
    records = [
        {
            "_id": i + 1,
            "Delivery Date": day,
            "From": start,
            "To": end,
            "Service Requirement MW": 200,
            "Service Requirement Type": "Live",
        }
        for i, (start, end) in enumerate([("17:00", "17:30"), ("17:30", "18:00")])
    ]
    return Sample("archive", resource, "url", "timestamp", records, [], 2, complete=True)


def test_contextual_reduction_does_not_fabricate_direction_or_id():
    s = archive()
    g = historical_groups(s)[0]
    assert g["demand_reduction"] and g["candidate_status"] == "Provisional candidate"
    assert g["event_id"] is None and g["direction"] is None
    assert "raw direction absent" in g["direction_evidence"]
    assert g["duration_minutes"] == 60
    assert availability([s])[0]["reduction_identified"] == 0
    assert availability([s])[0]["reduction_date_groups"] == 1
    assert not historical_groups(archive(resource="unknown"))[0]["demand_reduction"]
    assert not historical_groups(archive(day="2026-04-09"))[0]["demand_reduction"]


def test_cross_resource_duplicate_signature_and_semantic_difference():
    first = archive()
    second = archive(resource="7914dd99-fe1c-41ba-9989-5784531c58bb")
    assert len(duplicate_events([first, second])) == 1
    second.records[0]["Service Requirement MW"] = 300
    assert duplicate_events([first, second]) == []
    assert duplicate_events([first]) == []


def test_reselection_does_not_repeat_day_or_force_five():
    samples = [archive(day=d) for d in ["2025-11-06", "2025-03-18", "2025-03-18"]]
    chosen = diverse_recommendations(samples)
    assert len(chosen) == 2
    assert len({g["delivery_date"] for g in chosen}) == 2
