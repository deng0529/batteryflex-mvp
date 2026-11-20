"""Final mandatory criteria reject Test, missing evidence, invalid data and partial sources."""

from datetime import date

import pytest

from batteryflex.neso import API_URL, RESOURCES, Sample
from batteryflex.neso_selection import historical_groups
from batteryflex.neso_validation import final_recommendations, validate_event


def sample():
    rid = RESOURCES["DFS Service Requirement (Archive 2025/2026)"]
    records = [
        {
            "_id": i + 1,
            "Delivery Date": "2025-11-06",
            "From": a,
            "To": b,
            "Service Requirement MW": 200,
            "Service Requirement Type": "Live",
        }
        for i, (a, b) in enumerate([("17:00", "17:30"), ("17:30", "18:00")])
    ]
    return Sample(
        "archive",
        rid,
        f"{API_URL}?resource_id={rid}&limit=1000",
        "timestamp",
        records,
        [],
        2,
        complete=True,
    )


def validate(s):
    return validate_event(s, historical_groups(s)[0], as_of=date(2026, 11, 16))


def test_all_criteria_and_internal_identity_preserve_absent_official_id():
    s = sample()
    g = validate(s)
    assert set(g["validation_criteria"].values()) == {"PASS"}
    assert g["validation_status"] == "PASS"
    assert g["event_id"] is None and g["direction"] is None
    assert g["internal_scenario_id"].startswith("BF-SCENARIO-20251106-")
    assert validate(s)["internal_scenario_id"] == g["internal_scenario_id"]
    assert g["direction_definition_url"].endswith("348106/download")
    assert len(g["source_records_sha256"]) == 64
    assert g["winter_season"] == "2025/26"


@pytest.mark.parametrize(
    "value,expected",
    [("Test", "FAIL"), (None, "UNVERIFIED"), ("", "UNVERIFIED"), ("live", "FAIL"), (True, "FAIL")],
)
def test_raw_status_is_mandatory_for_every_window(value, expected):
    s = sample()
    s.records[1]["Service Requirement Type"] = value
    g = validate(s)
    assert g["validation_criteria"]["live"] == expected
    assert final_recommendations([s]) == []
    assert len(s.records) == 2  # Raw Test records are never removed.


def test_direction_not_inferred_from_live_price_dispatch_or_unrelated_flags():
    s = sample()
    s.resource_id = "unknown"
    for r in s.records:
        r.update(
            {
                "Guaranteed Acceptance Price GBP per MWh": 0,
                "Dispatch Type": "All Providers",
                "demand_reduction": True,
            }
        )
    g = validate(s)
    assert g["validation_criteria"]["direction"] == "UNVERIFIED"
    assert final_recommendations([s]) == []


def test_upwards_is_not_demand_reduction_under_current_dfs_definition():
    s = sample()
    s.resource_id = RESOURCES["DFS Service Requirement"]
    for r in s.records:
        r["Event Type"] = "Upwards"
    assert validate(s)["validation_criteria"]["direction"] == "FAIL"
    assert final_recommendations([s]) == []


@pytest.mark.parametrize(
    "mutation,criterion,expected",
    [
        (lambda s: s.records[0].update({"Service Requirement MW": 0}), "requirement_mw", "FAIL"),
        (
            lambda s: s.records[0].update({"Service Requirement MW": None}),
            "requirement_mw",
            "UNVERIFIED",
        ),
        (
            lambda s: s.records[0].update({"Service Requirement MW": "NaN"}),
            "requirement_mw",
            "FAIL",
        ),
        (lambda s: s.records[0].update({"To": "17:15"}), "continuous_window", "FAIL"),
        (lambda s: s.records[0].update({"_id": 2}), "original_records", "UNVERIFIED"),
        (lambda s: setattr(s, "complete", False), "complete_retrieval", "UNVERIFIED"),
        (
            lambda s: setattr(s, "source_url", "https://unrelated.example/data"),
            "source_resource",
            "UNVERIFIED",
        ),
    ],
)
def test_each_failed_or_unverified_criterion_excludes_final_event(mutation, criterion, expected):
    s = sample()
    mutation(s)
    assert validate(s)["validation_criteria"][criterion] == expected
    assert final_recommendations([s]) == []


def test_invalid_date_is_reported_without_crashing_validation():
    s = sample()
    for r in s.records:
        r["Delivery Date"] = "bad"
    assert validate(s)["validation_criteria"]["historical_date"] == "UNVERIFIED"
    assert final_recommendations([s]) == []
