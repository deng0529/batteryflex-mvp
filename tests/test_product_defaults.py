"""Defaults and landing-page coverage retain the validated Experiment A contract."""

from dataclasses import asdict, replace

import pytest
from streamlit.testing.v1 import AppTest

from batteryflex.defaults import AppDefaults, SimulationDefaults, load_defaults
from batteryflex.dispatch import METHODS, Scenario, export_batteries
from batteryflex.dispatch_event import event_start_batteries, standard_scenario
from batteryflex.portfolio import default_portfolio
from batteryflex.storage.dispatch_runs import _identity
from batteryflex.ui.overview import benchmark_summary


def test_configured_event_inputs_keep_the_previous_fingerprint():
    assets = event_start_batteries(default_portfolio().batteries)
    assert tuple(asset.initial_soc for asset in assets) == (0.9, 0.9, 0.95, 0.85, 0.85)
    previous = Scenario(
        export_batteries(assets),
        (0, 1),
        10.0,
        simulation_mode="EVENT_ONLY",
        target_export_only=True,
    )
    configured = standard_scenario(assets, (0, 1))
    assert configured == previous
    for method in METHODS:
        assert _identity(configured, method, {}) == _identity(previous, method, {})
        assert _identity(replace(configured, target_kw=12.5), method, {}) != _identity(
            previous, method, {}
        )
    assert standard_scenario(assets, (0, 1)).target_kw == 10.0


def test_config_rejects_invalid_simulation_values():
    baseline = asdict(load_defaults("simulation.yaml", SimulationDefaults))
    with pytest.raises(ValueError, match="prediction steps"):
        SimulationDefaults(**{**baseline, "prediction_steps": 0})
    with pytest.raises(ValueError, match="four objective weights"):
        SimulationDefaults(**{**baseline, "weights": (1.0, 2.0)})
    with pytest.raises(ValueError, match="finite number"):
        SimulationDefaults(**{**baseline, "target_kw": True})
    with pytest.raises(ValueError, match="Display precision"):
        AppDefaults("BatteryFlex", "Simulation", "0.1.0", True)


def test_missing_configuration_has_a_file_specific_error():
    with pytest.raises(ValueError, match="Invalid missing.yaml"):
        load_defaults("missing.yaml", AppDefaults)


def test_error_is_rendered_before_startup_storage_work(monkeypatch):
    from batteryflex.ui import app

    def invalid():
        raise ValueError("Invalid portfolio.yaml: Battery interval must be 0.5 hours")

    monkeypatch.setattr(app, "portfolio_defaults", invalid)
    test_app = AppTest.from_string("from batteryflex.ui.app import main; main()").run()
    assert not test_app.exception
    assert "Invalid portfolio.yaml" in test_app.error[0].value
    assert not test_app.metric


def test_partial_five_event_coverage_does_not_produce_totals():
    assert benchmark_summary({}, 5) is None
    assert benchmark_summary({"event": {"RBC": {}, "MPC": {}, "MILP": {}}}, 5) is None
    assert benchmark_summary({"event": {"MPC": {}, "MILP": {}}}, 1) is None
