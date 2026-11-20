"""Working table, explicit saved snapshots, real model curves and scenario isolation."""

import json

import pytest
from streamlit.testing.v1 import AppTest

from batteryflex.portfolio import HOUSEHOLDS, INITIAL_SOC, default_portfolio
from batteryflex.portfolio_editor import portfolio_rows
from batteryflex.portfolio_storage import import_configuration

SCRIPT = """
import streamlit as st
from batteryflex.ui.portfolio import render_portfolio
st.session_state.setdefault("portfolio_technical", True)
render_portfolio()
"""


def edit(app, changes):
    key = app.data_editor[0].key
    app.session_state[key] = {"edited_rows": changes, "added_rows": [], "deleted_rows": []}
    app.run()
    assert not app.exception
    return app


def metric(app, label):
    return next(m.value for m in app.metric if m.label == label)


def quantity(app, label):
    table = app.dataframe[-1].value
    assert list(table.columns) == ["Quantity", "Value", "Unit", "Explanation"]
    return float(table.loc[table.Quantity == label, "Value"].iloc[0])


def test_four_sections_one_table_two_actions_and_actual_model_chart():
    app = AppTest.from_string(SCRIPT).run()
    assert not app.exception
    assert [s.value for s in app.subheader] == [
        "Asset configuration",
        "Asset qualification",
        "Battery and household power models",
        "Battery charge and discharge performance",
    ]
    assert len(app.data_editor) == len(app.dataframe) == 1
    assert len(app.data_editor[0].value) == 5
    assert [b.label for b in app.button] == ["Restore Defaults"]
    assert [b.label for b in app.download_button] == ["Save Configuration"]
    assert len(app.checkbox) == 5 and all(c.value for c in app.checkbox)
    assert len(app.latex) == 4
    assert len(app.get("vega_lite_chart")) == 1
    assert metric(app, "Final SOC") == "100.00%"
    assert metric(app, "Total charging time") == "0.421637 h"
    assert len(app.number_input) == 2
    assert app.selectbox(key="demo_mode").options == ["Charge", "Discharge"]
    assert all("interval_hours" not in row for row in app.session_state.battery_working_rows)


def test_all_table_parameters_roundtrip_and_live_calculated_efficiency():
    app = AppTest.from_string(SCRIPT).run()
    changed = {
        i: {
            "capacity_kwh": 12 + i,
            "charge_limit_kw": 2,
            "discharge_limit_kw": 3,
            "initial_soc": 50 + i,
            "min_soc": 10,
            "max_soc": 90,
            "charge_efficiency": 80,
            "discharge_efficiency": 90,
            "export_enabled": False,
            "export_limit_kw": 1,
            "participating": False,
        }
        for i in range(5)
    }
    edit(app, changed)
    rows = app.session_state.battery_working_rows
    assert all(row["round_trip_efficiency"] == 72 for row in rows)
    assert app.data_editor[0].value["round_trip_efficiency"].tolist() == [72] * 5
    assert app.session_state.battery_portfolio == default_portfolio()
    app.download_button(key="battery_save").click().run()
    assert not app.exception
    saved = app.session_state.battery_portfolio
    assert [b.capacity_kwh for b in saved.batteries] == list(range(12, 17))
    assert saved.batteries[0].initial_soc == 0.5
    assert saved.batteries[0].charge_efficiency == 0.8
    assert saved.batteries[0].discharge_efficiency == 0.9
    assert all(not b.participating and not b.export_enabled for b in saved.batteries)
    assert import_configuration(app.session_state.battery_saved_json, reviewed_five=True) == saved
    assert any("saved for this session" in x.value for x in app.success)
    # Checkboxes rebase to working participation but never mutate saved settings themselves.
    assert all(not app.checkbox(key=f"check_participation_{h}").value for h in HOUSEHOLDS)


def test_invalid_working_values_cannot_save_and_report_household():
    app = AppTest.from_string(SCRIPT).run()
    edit(app, {0: {"initial_soc": 20.01}})
    assert not app.error
    assert app.session_state.battery_working_rows[0]["initial_soc"] == 20.01
    assert app.session_state.battery_portfolio.batteries[0].initial_soc == 0.8
    edit(app, {0: {"min_soc": 30}, 1: {"discharge_efficiency": 0}})
    assert any(HOUSEHOLDS[0] in e.value and "SOC" in e.value for e in app.error)
    assert any(HOUSEHOLDS[1] in e.value and "efficiency" in e.value for e in app.error)
    assert app.download_button(key="battery_save").disabled
    assert not app.get("vega_lite_chart") and len(app.metric) == 5
    assert app.session_state.battery_portfolio == default_portfolio()


def test_restore_only_changes_working_table_until_explicit_save():
    app = AppTest.from_string(SCRIPT).run()
    edit(app, {0: {"capacity_kwh": 15, "initial_soc": 40}})
    app.download_button(key="battery_save").click().run()
    saved = app.session_state.battery_portfolio
    app.button(key="battery_defaults").click().run()
    assert not app.exception
    assert app.session_state.battery_working_rows == portfolio_rows(default_portfolio())
    assert app.data_editor[0].value["initial_soc"].tolist() == pytest.approx([80, 65, 90, 55, 75])
    assert app.session_state.battery_portfolio == saved
    assert any("working table" in item.value for item in app.info)
    app.download_button(key="battery_save").click().run()
    assert app.session_state.battery_portfolio == default_portfolio()


def test_scenario_selection_and_commitments_never_mutate_saved_or_table_participation():
    app = AppTest.from_string(SCRIPT).run()
    for index in range(5):
        app.selectbox(key="battery_event").select_index(index).run()
        assert not app.exception
        assert any(
            s.proto.title == "Preliminary Battery Capability Sufficient" for s in app.success
        ) == (index != 4)
    assert any("Power shortfall: 1.62 kW" in w.value for w in app.warning)
    app.selectbox(key="battery_event").select_index(0).run()
    for h in HOUSEHOLDS[1:]:
        app.checkbox(key=f"check_participation_{h}").uncheck().run()
    assert quantity(app, "Participating households") == 1
    assert quantity(app, "Maximum constant portfolio discharge") == 5
    assert any("Power shortfall: 5.00 kW" in w.value for w in app.warning)
    app.number_input(key="battery_commitment").set_value(5).run()
    assert any(s.proto.title == "Preliminary Battery Capability Sufficient" for s in app.success)
    assert all(row["participating"] for row in app.session_state.battery_working_rows)
    assert (
        tuple(b.initial_soc for b in app.session_state.battery_portfolio.batteries) == INITIAL_SOC
    )


def test_demo_uses_working_parameters_and_keeps_saved_soc_unchanged():
    app = AppTest.from_string(SCRIPT).run()
    edit(app, {0: {"initial_soc": 21}})
    app.selectbox(key="demo_mode").select("Discharge").run()
    assert metric(app, "Initial SOC") == "21.00%"
    assert metric(app, "Final SOC") == "20.00%"
    assert metric(app, "Electrical energy discharged") == "0.094868 kWh"
    assert metric(app, "Total discharging time") == "0.018974 h"
    assert metric(app, "Operating power") == "5 kW"
    assert not app.warning
    assert app.session_state.battery_portfolio.batteries[0].initial_soc == 0.8
    assert app.session_state.battery_working_rows[0]["initial_soc"] == 21


def test_simulation_reads_saved_snapshot_and_page_switch_preserves_unsaved_work():
    script = """
import streamlit as st
from batteryflex.ui.portfolio import render_portfolio
from batteryflex.ui.planned import render_simulation
page = st.selectbox("Page", ["Portfolio", "Simulation"], key="test_page")
if page == "Portfolio":
    render_portfolio()
else:
    render_simulation()
"""
    app = AppTest.from_string(script).run()
    edit(app, {0: {"initial_soc": 40, "participating": False}})
    app.selectbox(key="battery_event").select_index(2).run()
    app.checkbox(key=f"check_participation_{HOUSEHOLDS[1]}").uncheck().run()
    app.selectbox(key="test_page").select("Simulation").run()
    assert not app.exception
    snapshot = json.loads(app.session_state.battery_scenario.portfolio_json)
    assert snapshot[0]["initial_soc"] == 0.8 and snapshot[0]["participating"]
    assert snapshot[1]["participating"]
    app.session_state["simulation_tabs"] = "Dispatch Simulation"
    app.run()
    assert not app.exception and app.button(key="dispatch_run_RBC").disabled
    app.selectbox(key="test_page").select("Portfolio").run()
    assert app.session_state.battery_working_rows[0]["initial_soc"] == 40
    app.download_button(key="battery_save").click().run()
    app.selectbox(key="test_page").select("Simulation").run()
    snapshot = json.loads(app.session_state.battery_scenario.portfolio_json)
    assert snapshot[0]["initial_soc"] == 0.4 and not snapshot[0]["participating"]
    assert snapshot[1]["participating"]


def test_operating_power_validation_and_defaults_follow_household_mode_and_rating():
    app = AppTest.from_string(SCRIPT).run()
    app.number_input(key="demo_power").set_value(0).run()
    assert any("Operating power" in e.value for e in app.error)
    assert not app.get("vega_lite_chart")
    edit(app, {1: {"charge_limit_kw": 3, "discharge_limit_kw": 2}})
    app.selectbox(key="demo_household").select(HOUSEHOLDS[1]).run()
    assert app.number_input(key="demo_power").value == 3
    app.number_input(key="demo_power").set_value(1).run()
    assert metric(app, "Operating power") == "1 kW"
    app.selectbox(key="demo_mode").select("Discharge").run()
    assert app.number_input(key="demo_power").value == 2
    edit(app, {1: {"discharge_limit_kw": 0}})
    assert not app.exception and app.number_input(key="demo_power").disabled
    assert any("rating is zero" in e.value for e in app.info)


def test_table_key_and_previous_edits_survive_later_edits_and_other_reruns():
    app = AppTest.from_string(SCRIPT).run()
    key = app.data_editor[0].key
    edit(app, {0: {"capacity_kwh": 12}, 4: {"charge_efficiency": 80}})
    assert app.data_editor[0].key == key
    edit(app, {1: {"initial_soc": 40}})
    app.selectbox(key="demo_household").select(HOUSEHOLDS[4]).run()
    assert app.session_state.battery_working_rows[0]["capacity_kwh"] == 12
    assert app.session_state.battery_working_rows[1]["initial_soc"] == 40
    assert app.session_state.battery_working_rows[4]["charge_efficiency"] == 80
    assert app.data_editor[0].key == key


def test_save_with_new_unreviewed_edit_does_not_commit_previous_download_payload():
    app = AppTest.from_string(SCRIPT).run()
    app.session_state[app.data_editor[0].key] = {
        "edited_rows": {0: {"capacity_kwh": 15}},
        "added_rows": [],
        "deleted_rows": [],
    }
    app.download_button(key="battery_save").click().run()
    assert not app.exception
    assert app.session_state.battery_portfolio == default_portfolio()
    assert app.session_state.battery_working_rows[0]["capacity_kwh"] == 15
    assert not app.success
    assert any("New table edits arrived" in e.value for e in app.error)
    app.download_button(key="battery_save").click().run()
    assert app.session_state.battery_portfolio.batteries[0].capacity_kwh == 15


def test_tooltips_units_and_energy_versus_household_equations():
    app = AppTest.from_string(SCRIPT).run()
    columns = json.loads(app.data_editor[0].proto.columns)
    efficiency = columns["round_trip_efficiency"]
    assert efficiency["disabled"]
    assert efficiency["help"] == (
        "The percentage of electrical energy recovered after a complete charge/discharge cycle. "
        "Calculated as charging efficiency multiplied by discharging efficiency. It is read-only."
    )
    cap = columns["export_limit_kw"]
    assert "3.68 kW" in cap["help"] and "net grid export" in cap["help"]
    assert "5 kW" in cap["help"] and "Blank" in cap["help"]
    for field in (
        "initial_soc",
        "min_soc",
        "max_soc",
        "charge_efficiency",
        "discharge_efficiency",
        "export_enabled",
        "participating",
    ):
        assert columns[field]["help"]
    captions = " ".join(c.value for c in app.caption)
    assert "RC equivalent-circuit" in captions and "voltage and transient" in captions
    assert "not an internal battery state equation" in captions
    assert "not been validated against real battery measurements" in captions
    assert any("P^{grid}" in eq.value for eq in app.latex)


def test_one_explained_results_table_with_dynamic_equations_and_energy_shortfall():
    app = AppTest.from_string(SCRIPT).run()
    app.selectbox(key="battery_event").select_index(4).run()
    assert len(app.dataframe) == 2  # editable configuration plus exactly one results table
    assert quantity(app, "Event duration") == 3
    assert quantity(app, "Required commitment energy") == 30
    assert quantity(app, "Shortfall") == pytest.approx(1.619964)
    assert quantity(app, "Equivalent shortfall energy") == pytest.approx(4.859893)
    assert any("Commitment coverage: 83.8%" in w.value for w in app.warning)
    assert any("8.380036" in eq.value and "10.000000" in eq.value for eq in app.latex)
    assert len(app.metric) == 10  # portfolio KPIs and demo only; qualification stays table-only


def test_participation_defaults_rebase_only_on_corresponding_working_field_change():
    app = AppTest.from_string(SCRIPT).run()
    app.checkbox(key=f"check_participation_{HOUSEHOLDS[0]}").uncheck().run()
    edit(app, {1: {"capacity_kwh": 12}})
    assert not app.checkbox(key=f"check_participation_{HOUSEHOLDS[0]}").value
    edit(app, {1: {"participating": False}})
    assert not app.checkbox(key=f"check_participation_{HOUSEHOLDS[1]}").value
    assert all(b.participating for b in app.session_state.battery_portfolio.batteries)
    app.checkbox(key=f"check_participation_{HOUSEHOLDS[1]}").check().run()
    assert not app.session_state.battery_working_rows[1]["participating"]
    assert app.session_state.battery_portfolio.batteries[1].participating


def test_zero_time_performance_has_initial_point_and_clear_boundary_message():
    app = AppTest.from_string(SCRIPT).run()
    edit(app, {0: {"initial_soc": 100}})
    assert metric(app, "Total charging time") == "0.000000 h"
    assert metric(app, "Initial SOC") == metric(app, "Final SOC") == "100.00%"
    assert metric(app, "Electrical energy charged") == "0.000000 kWh"
    assert len(app.get("vega_lite_chart")) == 1
    assert any("already at the maximum" in i.value for i in app.info)


def test_refined_status_copy_dynamic_values_and_safe_zero_commitment():
    app = AppTest.from_string(SCRIPT).run()
    app.selectbox(key="battery_event").select_index(4).run()
    assert not app.exception and len(app.warning) == 1
    warning = app.warning[0]
    assert warning.proto.title == "Proposed Commitment Exceeds Available Battery Capability"
    assert "estimated 8.38 kW of constant discharge over the 3-hour event" in warning.value
    assert "proposed local commitment of 10.00 kW" in warning.value
    for value in (
        "Available battery capability: 8.38 kW",
        "Power shortfall: 1.62 kW",
        "Energy shortfall: 4.86 kWh",
        "Commitment coverage: 83.8%",
    ):
        assert value in warning.value
    assert "These batteries can still contribute useful flexibility" in warning.value
    assert "arrange pre-charging where feasible" in warning.value
    assert any(
        "Preliminary battery-only assessment. Actual flexibility delivery also depends on "
        "household demand, baseline and grid export constraints." == c.value
        for c in app.caption
    )
    app.number_input(key="battery_commitment").set_value(5).run()
    assert not app.exception and not app.warning
    assert app.success[0].proto.title == "Preliminary Battery Capability Sufficient"
    assert app.success[0].value == (
        "The selected batteries have sufficient estimated discharge capability to meet the "
        "proposed local commitment. Final delivery feasibility will be assessed during "
        "dispatch optimisation."
    )
    # Surplus capability is not presented as an actual delivery percentage.
    assert not any("Commitment coverage" in x.value for x in app.success)
    app.number_input(key="battery_commitment").set_value(0).run()
    assert not app.exception and not app.warning
    assert app.success[0].proto.title == "Preliminary Battery Capability Sufficient"
    for h in HOUSEHOLDS:
        app.checkbox(key=f"check_participation_{h}").uncheck().run()
    assert not app.exception and not app.warning
    assert quantity(app, "Maximum constant portfolio discharge") == 0


def test_portfolio_confirmation_persists_immutable_version(tmp_path, monkeypatch):
    from test_forecast_training import frame as frame_fixture
    from test_forecast_ui import persistent_fixture

    from batteryflex.storage.database import query

    repository, _ = persistent_fixture(tmp_path, monkeypatch, frame_fixture.__wrapped__())
    original = repository.setting("portfolio")
    app = AppTest.from_string(SCRIPT, default_timeout=20).run()
    edit(app, {0: {"capacity_kwh": 12}})
    assert repository.setting("portfolio") == original
    app.download_button(key="battery_save").click().run()
    assert not app.exception and not app.error
    assert repository.setting("portfolio") != original
    assert len(query(repository.db, "SELECT * FROM portfolios")) == 2
    app.download_button(key="battery_save").click().run()
    assert len(query(repository.db, "SELECT * FROM portfolios")) == 2
    assert not query(repository.db, "SELECT * FROM forecast_models")
    fresh = AppTest.from_string(SCRIPT, default_timeout=20).run()
    assert not fresh.exception
    assert fresh.session_state.battery_portfolio.batteries[0].capacity_kwh == 12
