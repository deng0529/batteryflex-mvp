"""The public view uses frozen reviewed sources without network or validation duplication."""

from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from batteryflex import neso
from batteryflex.neso_intervals import event_intervals
from batteryflex.neso_manifest import load_selection

EXPLORER = "from batteryflex.ui.explorer import render_data_explorer; render_data_explorer()"
EXPECTED = [
    ("2025-03-18", 2, 300, "BF-SCENARIO-20250318-d83173d115"),
    ("2025-11-06", 2, 200, "BF-SCENARIO-20251106-ae30cf8298"),
    ("2023-12-01", 3, 550, "BF-SCENARIO-20231201-11bed40350"),
    ("2026-01-11", 4, 500, "BF-SCENARIO-20260111-928f24c1e7"),
    ("2025-02-02", 6, 500, "BF-SCENARIO-20250202-5bc3052ad5"),
]


def test_manifest_preserves_all_reviewed_records_and_identifiers():
    events, samples, manifest = load_selection()
    assert manifest["manifest_version"] == 1
    assert sum(len(s.records) for s in samples.values()) == 17
    for event, (day, count, mw, scenario_id) in zip(events, EXPECTED, strict=True):
        assert str(event["delivery_date"]) == day
        assert event["internal_scenario_id"] == scenario_id
        assert event["event_id"] is None
        assert set(event["validation_criteria"].values()) == {"PASS"}
        sample = samples[event["resource_id"]]
        intervals = event_intervals(sample, event)
        assert len(intervals) == count
        assert all(i["national_requirement_mw"] == mw for i in intervals)
        assert all(i["requirement_basis"] == "Directly reported source window" for i in intervals)
        assert all(
            sample.records[i]["Service Requirement Type"] == "Live" for i in event["source_rows"]
        )


def test_initial_public_view_is_empty_selection_and_offline(monkeypatch):
    fetch = Mock(side_effect=AssertionError("Public view must not fetch"))
    monkeypatch.setattr(neso, "fetch_all", fetch)
    monkeypatch.setattr(neso, "fetch_sample", fetch)
    app = AppTest.from_string(EXPLORER, default_timeout=15).run()
    assert not app.exception
    selector = app.selectbox(key="neso_public_event")
    assert len(selector.options) == 5 and selector.value is None
    assert not app.dataframe and not app.json
    assert not app.get("vega_lite_chart")
    app.run()
    fetch.assert_not_called()


def test_every_public_selection_shows_published_intervals_without_fetch(monkeypatch):
    fetch = Mock(side_effect=AssertionError("Public view must not fetch"))
    monkeypatch.setattr(neso, "fetch_all", fetch)
    app = AppTest.from_string(EXPLORER, default_timeout=15).run()
    for _, count, mw, scenario_id in EXPECTED:
        app.selectbox(key="neso_public_event").select(scenario_id).run()
        assert not app.exception
        table = app.dataframe[0].value
        assert len(table) == count
        assert table["National requirement (MW)"].tolist() == [mw] * count
        assert not app.get("vega_lite_chart")
        assert not app.json  # Provenance starts collapsed and unrendered.
        assert table["Energy equivalent (MWh)"].tolist() == [mw * 0.5] * count
    fetch.assert_not_called()
