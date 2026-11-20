"""UI fixtures are synthetic and isolated from the ignored real prepared dataset."""

import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from batteryflex.lcl import parse_observations
from batteryflex.lcl_analysis import map_day, replay
from batteryflex.lcl_source import digest
from batteryflex.neso_manifest import load_selection
from batteryflex.ui import lcl_lab
from batteryflex.ui.lcl_charts import HOUSEHOLDS

APP = Path(__file__).resolve().parent / "fixtures" / "research_explorer.py"


def fixture_data(path):
    ids = [*HOUSEHOLDS, *[f"MAC{n:06d}" for n in range(95)]]
    events, _, _ = load_selection()
    days = {map_day(e["delivery_date"]) for e in events}
    rows = []
    for day in sorted(days):
        for timestamp in pd.date_range(str(day), periods=48, freq="30min", tz="UTC"):
            end = timestamp + pd.Timedelta(minutes=30)
            rows.extend(
                {
                    "household_id": h,
                    "source_timestamp": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "source_kwh": "0.25" if h == HOUSEHOLDS[0] else "0.5",
                }
                for h in ids
            )
    frame = parse_observations(rows)
    frame.to_parquet(path / "observations.parquet")
    candidates = pd.DataFrame(
        {
            "household_id": ids,
            "average_daily_kwh": [12.0] * 100,
            "mean_evening_kw": [0.5] * 100,
            "peak_kw": [1.0] * 100,
            "completeness": [1.0] * 100,
            "valid_winter_days": [90] * 100,
            "demand_std_kw": [0.2] * 100,
            "demand_cv": [0.4] * 100,
        }
    )
    candidates.to_csv(path / "candidates.csv", index=False)
    candidates.iloc[:5].assign(reason="Synthetic UI fixture").to_csv(
        path / "recommended.csv", index=False
    )
    replay(frame, HOUSEHOLDS).to_csv(path / "replay.csv", index=False)
    audit = {
        "parser_version": 1,
        "household_count": 4443,
        "retained_days": sorted(str(d) for d in days),
        "artifacts": {p.name: digest(p) for p in path.iterdir()},
    }
    (path / "audit.json").write_text(json.dumps(audit))


def test_lab_empty_state_no_implicit_download(tmp_path, monkeypatch):
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    monkeypatch.setattr("batteryflex.lcl_source.urlopen", lambda *a, **k: pytest.fail("network"))
    app = AppTest.from_file(str(APP)).run()
    app.toggle(key="lcl_enabled").set_value(True).run()
    assert not app.exception
    assert any("No prepared local LCL" in e.value for e in app.info)


def test_prepared_integrity_rejects_changed_data(tmp_path):
    fixture_data(tmp_path)
    (tmp_path / "replay.csv").write_text("changed")
    with pytest.raises(ValueError, match="integrity"):
        lcl_lab.load_prepared(str(tmp_path), 1)


def test_lab_selectors_and_all_event_intervals_offline(tmp_path, monkeypatch):
    fixture_data(tmp_path)
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    monkeypatch.setattr("batteryflex.lcl_source.urlopen", lambda *a, **k: pytest.fail("network"))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.toggle(key="lcl_enabled").set_value(True).run()
    assert not app.exception
    assert app.selectbox(key="lcl_household").value is None
    assert len(app.selectbox(key="lcl_household").options) == 5
    assert not app.get("vega_lite_chart")
    assert len(app.dataframe) == 1 and len(app.dataframe[0].value) == 5
    app.selectbox(key="lcl_household").select(HOUSEHOLDS[0]).run()
    assert not app.exception
    assert len(app.dataframe[-1].value) == 48
    assert app.dataframe[-1].value["Average demand (kW)"].tolist() == [0.5] * 48
    assert len(app.get("vega_lite_chart")) == 3
    assert app.download_button[0].label == "Download selected readings as CSV"
    app.selectbox(key="lcl_household").select(HOUSEHOLDS[1]).run()
    assert not app.exception
    assert app.dataframe[-1].value["Average demand (kW)"].tolist() == [1.0] * 48
    app.segmented_control(key="lcl_scope").set_value("All prepared candidates").run()
    assert len(app.selectbox(key="lcl_household").options) == 100
    app.selectbox(key="lcl_household").select("MAC000094").run()
    assert any("MAC000094" in item.value for item in app.subheader)
    app.date_input(key="lcl_dates").set_value(
        (pd.Timestamp("2013-02-03").date(), pd.Timestamp("2013-02-03").date())
    ).run()
    assert len(app.dataframe[-1].value) == 48
    app.segmented_control(key="lcl_section").set_value("Five-Household Comparison").run()
    assert not app.exception
    assert app.dataframe[0].value["Household ID"].tolist() == HOUSEHOLDS
    assert len(app.get("vega_lite_chart")) == 5
    app.segmented_control(key="lcl_section").set_value("NESO Event Replay").run()
    assert not app.exception
    assert app.selectbox(key="lcl_event").value is None
    assert len(app.selectbox(key="lcl_event").options) == 5
    assert not app.dataframe
    for event, count in [
        ("2025-03-18", 2),
        ("2025-11-06", 2),
        ("2023-12-01", 3),
        ("2026-01-11", 4),
        ("2025-02-02", 6),
    ]:
        app.selectbox(key="lcl_event").select(event).run()
        assert not app.exception
        assert len(app.dataframe[-1].value) == count
        table = app.dataframe[-1].value
        assert table["Combined demand (kW)"].tolist() == [4.5] * count
        assert all(f"{h} (kW)" in table for h in HOUSEHOLDS)
        assert table["Original NESO date"].str.startswith(("2023", "2025", "2026")).all()
        assert table["Original LCL date"].str.startswith("2013").all()
    app.segmented_control(key="lcl_section").set_value("Data Quality & Provenance").run()
    assert not app.exception
    assert not app.dataframe and not app.json


def test_corrupt_data_shows_clear_error(tmp_path, monkeypatch):
    fixture_data(tmp_path)
    (tmp_path / "replay.csv").write_text("corrupted")
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    app = AppTest.from_file(str(APP)).run()
    app.toggle(key="lcl_enabled").set_value(True).run()
    assert not app.exception
    assert "integrity" in app.error[0].value


def test_public_lcl_tab_has_five_homes_one_chart_and_comparison(tmp_path, monkeypatch):
    fixture_data(tmp_path)
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    monkeypatch.setattr("batteryflex.lcl_source.urlopen", lambda *a, **k: pytest.fail("network"))
    app = AppTest.from_string(
        "from batteryflex.ui.explorer import render_data_explorer; render_data_explorer()"
    ).run()
    app.session_state["data_tabs"] = "Low Carbon London"
    app.run()
    assert not app.exception
    assert app.selectbox(key="lcl_public_household").options == HOUSEHOLDS
    assert app.selectbox(key="lcl_public_household").value is None
    assert not app.dataframe and not app.get("vega_lite_chart")
    app.selectbox(key="lcl_public_household").select(HOUSEHOLDS[0]).run()
    assert not app.exception
    assert len(app.get("vega_lite_chart")) == 1
    app.session_state["lcl_original_readings"] = True
    app.run()
    table = app.dataframe[-1].value
    assert table["Average demand (kW)"].tolist() == [0.5] * 48
    assert (
        (table["Interval end (GMT)"] - table["Interval start (GMT)"])
        .dt.total_seconds()
        .eq(1800)
        .all()
    )
    app.selectbox(key="lcl_public_household").select(HOUSEHOLDS[1]).run()
    assert app.dataframe[-1].value["Average demand (kW)"].tolist() == [1.0] * 48
    app.segmented_control(key="lcl_public_view").set_value("Five-household comparison").run()
    assert not app.exception
    assert len(app.get("vega_lite_chart")) == 1
    assert app.dataframe[0].value["Household ID"].tolist() == HOUSEHOLDS


def test_public_lcl_missing_local_data_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(lcl_lab, "DATA_DIRECTORY", tmp_path)
    app = AppTest.from_string(
        "from batteryflex.ui.explorer import render_data_explorer; render_data_explorer()"
    ).run()
    app.session_state["data_tabs"] = "Low Carbon London"
    app.run()
    assert not app.exception
    assert any("Prepared household data is unavailable" in item.value for item in app.info)
