"""Preserve acquisition/advanced inspection component regressions outside public navigation."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent / "fixtures" / "research_explorer.py"


def test_explicit_fetch_filter_and_record_preview(monkeypatch):
    from unittest.mock import Mock

    from batteryflex import neso

    sample = neso.Sample(
        "DFS Service Requirement",
        "resource",
        "https://api.neso.energy",
        "2026-11-16T00:00:00+00:00",
        [
            {"Delivery Date": "2025-01-01", "From": "17:00", "Service Requirement MW": 100},
            {"Delivery Date": "2026-02-02", "From": "18:00", "Service Requirement MW": 200},
        ],
        [],
        2,
    )
    fetch = Mock(return_value=sample)
    monkeypatch.setattr(neso, "fetch_sample", fetch)
    app = AppTest.from_file(str(APP)).run()
    fetch.assert_not_called()
    app.toggle(key="neso_advanced").set_value(True).run()
    app.button(key="neso_fetch").click().run()
    assert not app.exception
    assert len(app.dataframe[1].value) == 2
    app.selectbox(key="neso_year").select(2025).run()
    assert not app.exception
    assert len(app.dataframe[1].value) == 1
    assert "2025-01-01" in app.json[-1].value
    fetch.assert_called_once()


def test_fetch_failure_is_visible(monkeypatch):
    from unittest.mock import Mock

    from batteryflex import neso

    monkeypatch.setattr(neso, "fetch_sample", Mock(side_effect=neso.NesoError("Offline")))
    app = AppTest.from_file(str(APP)).run()
    app.toggle(key="neso_advanced").set_value(True).run()
    app.button(key="neso_fetch").click().run()
    assert not app.exception
    assert app.error[0].value == "Offline"


def test_full_fetch_and_summary_survive_filtering(monkeypatch):
    from unittest.mock import Mock

    from batteryflex import neso

    sample = neso.Sample(
        "DFS Service Requirement",
        "resource",
        "url",
        "timestamp",
        [
            {
                "_id": 1,
                "Event ID": 5,
                "Delivery Date": "2026-11-12",
                "From_UTC": "17:00",
                "To_UTC": "17:30",
                "Service Requirement MW": 500,
                "Event Type": "Downwards",
                "Service Requirement Type": "Live",
                "Participant Bids Eligible": "Provider A",
            }
        ],
        [],
        1,
        request_urls=["url"],
        complete=True,
        completed_at="timestamp",
    )
    fetch = Mock(return_value=sample)
    monkeypatch.setattr(neso, "fetch_all", fetch)
    app = AppTest.from_file(str(APP)).run()
    fetch.assert_not_called()
    app.toggle(key="neso_advanced").set_value(True).run()
    app.button(key="neso_fetch_all").click().run()
    assert not app.exception
    assert "1 of 1" in app.success[0].value
    assert any("Complete retrieval" in item.value for item in app.caption)
    assert len(app.dataframe[-1].value) == 1
    assert app.dataframe[-1].value.iloc[0]["candidate_status"] == "Provisional candidate"
    app.run()
    fetch.assert_called_once()


def test_cross_resource_review_duration_filter_and_interval_chart(monkeypatch):
    from unittest.mock import Mock

    from batteryflex import neso

    rows = [
        {
            "_id": i + 1,
            "Delivery Date": "2025-11-06",
            "From": start,
            "To": end,
            "Service Requirement MW": mw,
            "Service Requirement Type": "Live",
        }
        for i, (start, end, mw) in enumerate([("17:00", "17:30", 200), ("17:30", "18:00", 300)])
    ]
    sample = neso.Sample(
        "archive",
        "f5605e2b-b677-424c-8df7-d0ce4ee03cef",
        neso.API_URL + "?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef",
        "timestamp",
        rows,
        [],
        2,
        request_urls=[neso.API_URL + "?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef"],
        complete=True,
    )
    fetch = Mock(return_value=sample)
    monkeypatch.setattr(neso, "fetch_all", fetch)
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    fetch.assert_not_called()
    app.toggle(key="neso_advanced").set_value(True).run()
    app.button(key="neso_fetch_histories").click().run()
    assert not app.exception
    assert fetch.call_count == len(neso.RESOURCES)
    intervals = app.dataframe[-1].value
    assert len(intervals) == 2
    assert intervals["national_requirement_mw"].tolist() == [200, 300]
    assert all(intervals["requirement_basis"].str.startswith("Directly reported"))
    assert len(app.get("vega_lite_chart")) == 1
    app.selectbox(key="neso_duration").select(60.0).run()
    assert not app.exception
    assert fetch.call_count == len(neso.RESOURCES)


def test_final_shortlist_live_default_test_records_still_inspectable():
    from batteryflex import neso

    rid = neso.RESOURCES["DFS Service Requirement (Archive 2025/2026)"]
    sample = neso.Sample(
        "archive",
        rid,
        neso.API_URL + "?resource_id=" + rid,
        "timestamp",
        [
            {
                "_id": 1,
                "Delivery Date": "2025-11-06",
                "From": "17:00",
                "To": "17:30",
                "Service Requirement MW": 200,
                "Service Requirement Type": "Live",
            },
            {
                "_id": 2,
                "Delivery Date": "2025-11-07",
                "From": "17:00",
                "To": "17:30",
                "Service Requirement MW": 300,
                "Service Requirement Type": "Test",
            },
        ],
        [],
        2,
        complete=True,
    )
    app = AppTest.from_file(str(APP), default_timeout=15)
    app.session_state["neso_histories"] = [sample]
    app.run()
    app.toggle(key="neso_advanced").set_value(True).run()
    assert not app.exception
    assert app.selectbox(key="neso_review_status").value == "Live"
    comparison = next(d.value for d in app.dataframe if "validation_criteria" in d.value.columns)
    assert comparison["requirement_type"].tolist() == ["Live"]
    assert comparison["validation_status"].tolist() == ["PASS"]
    app.selectbox(key="neso_detail_scope").select("All historical groups").run()
    app.selectbox(key="neso_review_status").select("Test").run()
    assert not app.exception
    assert app.dataframe[-1].value["source_record_id"].tolist() == [2]
    assert '"Service Requirement Type": "Test"' in app.json[-1].value
    assert len(app.session_state["neso_histories"][0].records) == 2
