"""Mocked public responses: schema drift, chronology and transport failures."""

import io
import json
from datetime import date
from unittest.mock import patch
from urllib.error import URLError

import pytest

from batteryflex import neso


@pytest.fixture
def payload():
    return {
        "success": True,
        "result": {
            "fields": [{"id": "Delivery Date", "type": "date"}, {"id": "Empty", "type": "text"}],
            "records": [
                {
                    "Delivery Date": "2026-03-29",
                    "From_UTC": "00:30",
                    "From_Local": "00:30",
                    "To_UTC": "01:00",
                    "Event ID": 5,
                    "Event Type": "Upwards",
                    "Service Requirement MW": 0,
                    "Extra": "original",
                },
                {
                    "Delivery Date": "30/03/2026",
                    "From_UTC": "23:30",
                    "From_Local": "00:30",
                    "Service Requirement MW": "bad",
                },
                {"Delivery Date": "bad", "Later column": ""},
            ],
            "total": 3,
        },
    }


def get_sample(payload):
    with patch.object(neso, "urlopen", return_value=io.StringIO(json.dumps(payload))) as network:
        sample = neso.fetch_sample(next(iter(neso.RESOURCES)))
    assert network.call_args.kwargs["timeout"] == 30
    return sample


def test_schema_union_and_preservation(payload):
    sample = get_sample(payload)
    schema = {s["column"]: s for s in neso.discover_schema(sample)}
    assert schema["Empty"]["missing_count"] == 3
    assert schema["Later column"]["missing_count"] == 3
    assert schema["Service Requirement MW"]["observed_types"] == "int, str"
    rows = neso.standardise(sample)
    assert rows[0]["required_mw"] == 0
    assert rows[1]["required_mw"] is None
    assert rows[0]["start_time"] == "00:30"
    assert rows[0]["time_basis"] == "UTC"
    assert rows[1]["event_id"] is None
    assert sample.records == payload["result"]["records"]
    assert sample.retrieved_at.endswith("+00:00")
    assert sample.resource_id in sample.source_url


def test_inclusive_dates_and_direction(payload):
    rows = neso.standardise(get_sample(payload))
    assert len(neso.filter_events(rows)) == 3
    assert len(neso.filter_events(rows, year=2026, month=3)) == 2
    assert len(neso.filter_events(rows, start=date(2026, 3, 29), end=date(2026, 3, 29))) == 1
    assert len(neso.filter_events(rows, direction="Upwards")) == 1
    assert neso.filter_events(rows, year=2025) == []


def test_archive_does_not_invent_id_direction_or_timezone(payload):
    payload["result"]["records"] = [{"Delivery Date": "2025-10-29", "From": "17:00"}]
    row = neso.standardise(get_sample(payload))[0]
    assert row["event_id"] is None and row["direction"] is None
    assert row["start_time"] == "17:00" and row["time_basis"] == "GMT (source metadata)"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"success": False},
        {"success": True},
        {"success": True, "result": {"records": [1]}},
        {"success": True, "result": {"records": [], "fields": [1]}},
    ],
)
def test_bad_envelope(payload):
    with pytest.raises(neso.NesoError):
        get_sample(payload)


def test_empty_response():
    sample = get_sample({"success": True, "result": {"records": []}})
    assert sample.records == []


@pytest.mark.parametrize("failure", [URLError("offline"), TimeoutError("timeout")])
def test_network_errors(failure):
    with patch.object(neso, "urlopen", side_effect=failure), pytest.raises(neso.NesoError):
        neso.fetch_sample(next(iter(neso.RESOURCES)))


def test_invalid_json():
    with patch.object(neso, "urlopen", return_value=io.StringIO("not json")):
        with pytest.raises(neso.NesoError):
            neso.fetch_sample(next(iter(neso.RESOURCES)))


def test_pagination_preserves_every_record_and_provenance():
    pages = [
        {
            "success": True,
            "result": {"total": 3, "fields": [], "records": [{"_id": 1}, {"_id": 2}]},
        },
        {"success": True, "result": {"total": 3, "fields": [], "records": [{"_id": 3}]}},
    ]
    with patch.object(
        neso, "urlopen", side_effect=[io.StringIO(json.dumps(p)) for p in pages]
    ) as net:
        sample = neso.fetch_all(next(iter(neso.RESOURCES)), page_size=2)
    assert [r["_id"] for r in sample.records] == [1, 2, 3]
    assert sample.complete and sample.completed_at
    assert len(sample.request_urls) == 2
    assert "offset=2" in sample.request_urls[1] and "sort=_id+asc" in sample.request_urls[1]
    assert net.call_count == 2


@pytest.mark.parametrize(
    "second",
    [
        {"total": 3, "fields": [], "records": []},
        {"total": 4, "fields": [], "records": [{"_id": 3}]},
        {"total": 3, "fields": [], "records": [{"_id": 2}]},
        {"total": 3, "fields": [], "records": [{"missing": 3}]},
        {"total": 3, "fields": [{"id": "new"}], "records": [{"_id": 3}]},
    ],
)
def test_incomplete_or_changing_pagination_fails(second):
    first = {"total": 3, "fields": [], "records": [{"_id": 1}, {"_id": 2}]}
    pages = [io.StringIO(json.dumps({"success": True, "result": p})) for p in [first, second]]
    with patch.object(neso, "urlopen", side_effect=pages), pytest.raises(neso.NesoError):
        neso.fetch_all(next(iter(neso.RESOURCES)), page_size=2)


def test_mapping_includes_eligibility_and_resource_without_inference(payload):
    payload["result"]["records"][0].update(
        {"_id": 123, "Dispatch Type": "All Providers", "Participant Bids Eligible": "Provider A"}
    )
    sample = get_sample(payload)
    row = neso.standardise(sample)[0]
    assert row["source_record_id"] == 123
    assert row["resource_id"] == sample.resource_id
    assert row["eligible_participants"] == "Provider A"
    assert row["dispatch_type"] == "All Providers"
    assert row["start_local"] == "00:30"


def test_legacy_required_mw_seconds_and_despatch_mapping():
    sample = neso.Sample(
        "legacy",
        "7914dd99-fe1c-41ba-9989-5784531c58bb",
        "url",
        "timestamp",
        [
            {
                "Delivery Date": "2023-12-01",
                "From": "16:30:00",
                "To": "17:00:00",
                "DFS Required MW": 550,
                "Despatch Type": "All Providers",
            }
        ],
        [],
        1,
    )
    row = neso.standardise(sample)[0]
    assert row["required_mw"] == 550
    assert row["start_time"] == "16:30:00"
    assert row["dispatch_type"] == "All Providers"
    assert row["event_id"] is None and row["direction"] is None
