"""Physical, economic, causality and immutable-reuse checks for dispatch."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from batteryflex import dispatch
from batteryflex.dispatch import DT, METHODS, Scenario, evaluate, run_dispatch
from batteryflex.portfolio import default_portfolio
from batteryflex.storage import dispatch_runs
from batteryflex.storage.database import SQLiteDatabase, migrate, query
from batteryflex.storage.objects import Objects
from batteryflex.storage.repository import Repository
from batteryflex.ui.dispatch_results import conclusion


@pytest.fixture
def case():
    batteries = tuple(replace(b, export_enabled=False) for b in default_portfolio().batteries)
    s = Scenario(batteries, (34, 35, 36), 3, prediction_steps=5)
    load = np.tile([0.8, 0.9, 1, 1.1, 1.2], (48, 1))
    return s, load


@pytest.mark.parametrize("method", METHODS)
def test_shared_physics_and_objective(case, method):
    s, forecast = case
    actual = forecast * 0.8
    run = run_dispatch(s, method, forecast, actual)
    for name, load in (("planned", forecast), ("realized", actual)):
        result = run[name]
        c, d, e = map(
            np.asarray, (result["charge_kw"], result["discharge_kw"], result["energy_kwh"])
        )
        config = s.batteries
        np.testing.assert_allclose(
            np.diff(e, axis=0),
            DT
            * (
                c * [b.charge_efficiency for b in config]
                - d / [b.discharge_efficiency for b in config]
            ),
            atol=1e-7,
        )
        assert not (c * d).any()
        assert (e >= np.array([b.capacity_kwh * b.min_soc for b in config]) - 1e-7).all()
        assert (e <= np.array([b.capacity_kwh * b.max_soc for b in config]) + 1e-7).all()
        assert (e[-1] >= np.array([b.capacity_kwh * s.reserve_soc for b in config]) - 1e-7).all()
        assert (c <= [b.charge_limit_kw for b in config]).all()
        assert (d <= [b.discharge_limit_kw for b in config]).all()
        grid = load + c - d
        np.testing.assert_allclose(result["portfolio_grid_kw"], grid.sum(axis=1), atol=1e-7)
        np.testing.assert_allclose(result["flex_kw"], (load - grid).sum(axis=1), atol=1e-7)
        assert result["export_kwh"] == pytest.approx(0)
        assert sum(b["discharged_kwh"] for b in result["households"]) == pytest.approx(d.sum() * DT)
        assert sum(b["event_flex_kwh"] for b in result["households"]) == pytest.approx(
            result["delivered_kwh"]
        )
        short = (
            np.maximum(0, s.target_kw - np.asarray(result["flex_kw"])[list(s.event_steps)]).sum()
            * DT
        )
        terminal = np.maximum(
            0, np.array([b.capacity_kwh * s.target_soc for b in config]) - e[-1]
        ).sum()
        expected = [
            grid.sum() * DT * s.import_price,
            short,
            (c + d).sum() * DT * s.degradation_price,
            terminal * s.terminal_price,
        ]
        assert result["raw_terms"] == pytest.approx(expected)
        assert result["objective"] == pytest.approx(np.dot(expected, s.weights))
    assert run["planned"]["status"] == "MET"
    if method == "MILP":
        solver = run["planned_trace"][0]
        assert solver["status"] == "Optimal within tolerance"
        assert solver["constraints"] > 0 and solver["variables"] > 0
        assert solver["solver_objective"] == pytest.approx(run["planned"]["objective"], abs=1e-5)


def test_rbc_rules_reserve_proportional_allocation_and_export(case):
    s, load = case
    s = replace(
        s,
        event_steps=(2, 3),
        target_kw=8,
        event_soc=0.9,
        batteries=tuple(replace(b, export_enabled=True, export_limit_kw=1) for b in s.batteries),
    )
    run = run_dispatch(s, "RBC", load, load)
    trace = run["realized_trace"]
    assert trace[0]["rule"].startswith("Precharge")
    assert trace[2]["rule"].startswith("Event")
    assert trace[4]["rule"].startswith("Reserve recovery")
    delivered = -np.array(trace[2]["applied_kw"])
    caps = load[2] + 1
    np.testing.assert_allclose(delivered / caps, s.target_kw / caps.sum())
    assert run["realized"]["export_kwh"] > 0
    assert run["realized"]["export_kwh"] < run["realized"]["discharged_kwh"]
    assert run_dispatch(replace(s, precharge_price=0), "RBC", load, load)["planned_trace"][0][
        "rule"
    ].startswith("Reserve recovery")


def test_interval_energy_surplus_cannot_mask_interval_failure(case):
    s, load = case
    state = np.repeat([[8.0] * 5], 49, axis=0)
    actions = np.zeros_like(load)
    actions[s.event_steps[0]] = -3
    data = evaluate(s, load, actions, state)
    assert data["status"] == "PARTIALLY MET"
    assert data["fulfilment_pct"] == pytest.approx(100 / 3)
    assert data["surplus_kwh"] > data["shortfall_kwh"]
    assert evaluate(replace(s, target_type="energy"), load, actions, state)["status"] == "MET"
    assert evaluate(s, load, np.zeros_like(load), state)["status"] == "NOT MET"
    assert evaluate(replace(s, target_kw=0), load, actions, state)["status"] == "NOT ASSESSABLE"


def test_whole_event_milp_with_export_uses_net_exchange_and_explains_outcome(case):
    s, load = case
    s = replace(
        s,
        target_kw=8,
        target_type="energy",
        replay=False,
        batteries=tuple(replace(b, export_enabled=True, export_limit_kw=1) for b in s.batteries),
    )
    run = run_dispatch(s, "MILP", load, None)
    outcome = run["planned"]
    assert outcome["status"] == "MET"
    assert outcome["export_kwh"] > 0
    grid = np.asarray(outcome["grid_kw"])
    np.testing.assert_allclose(outcome["portfolio_import_kw"], np.maximum(grid, 0).sum(axis=1))
    np.testing.assert_allclose(outcome["portfolio_export_kw"], np.maximum(-grid, 0).sum(axis=1))
    assert grid.min() >= -1 - 1e-7
    assert run["planned_trace"][0]["solver_objective"] == pytest.approx(outcome["objective"])
    timeline = pd.date_range("2013-03-19", periods=48, freq="30min", tz="UTC")
    summary = conclusion(run, outcome, timeline, s)
    assert "MET for the configured portfolio target" in summary
    assert f"Grid export was {outcome['export_kwh']:.2f} kWh" in summary
    assert "All solves optimal within tolerance" in summary


def test_mpc_uses_only_current_actual_and_updates_energy(monkeypatch, case):
    s, forecast = case
    actual = forecast * 0.6
    observed = []
    solve = dispatch._solve

    def spy(scenario, load, state, start, delivered):
        observed.append((load.copy(), state.copy()))
        return solve(scenario, load, state, start, delivered)

    monkeypatch.setattr(dispatch, "_solve", spy)
    result = run_dispatch(s, "MPC", forecast, actual)
    assert result["solver_iterations"] == 96
    for k, (window, initial) in enumerate(observed[48:]):
        assert len(window) == min(48 - k, s.prediction_steps)
        np.testing.assert_allclose(window[0], actual[k])
        np.testing.assert_allclose(window[1:], forecast[k + 1 : k + s.prediction_steps])
        np.testing.assert_allclose(initial, result["realized"]["energy_kwh"][k])
        iteration = result["realized_trace"][k]
        np.testing.assert_allclose(
            iteration["applied_kw"], iteration["predicted_net_battery_kw"][0], atol=1e-7
        )


def test_invalid_inputs_and_infeasible_solver_are_explicit(case, monkeypatch):
    s, load = case
    with pytest.raises(ValueError, match="48 complete"):
        run_dispatch(s, "RBC", load, load[:-1])
    with pytest.raises(ValueError, match="constraint|feasible dispatch"):
        run_dispatch(replace(s, import_limit_kw=0), "MILP", load, load)
    with pytest.raises(ValueError, match="Hard terminal reserve"):
        replace(s, reserve_soc=1, batteries=tuple(replace(b, max_soc=0.9) for b in s.batteries))

    from scipy.optimize import OptimizeResult

    monkeypatch.setattr(
        dispatch, "milp", lambda *a, **k: OptimizeResult(status=1, x=None, message="limit")
    )
    with pytest.raises(ValueError, match="limit"):
        run_dispatch(s, "MILP", load, load)


def test_saved_first_across_repository_instances_and_scenario_changes(case, tmp_path, monkeypatch):
    s, load = case
    path = tmp_path / "runs.sqlite"
    db = SQLiteDatabase(path, create=True)
    migrate(db)
    repo = Repository(db, Objects(tmp_path))
    ref = {"event_id": "event", "model_version": "fixture"}
    result, reused = dispatch_runs.saved_or_run(repo, s, "RBC", ref, load, load)
    assert not reused
    other, reused = dispatch_runs.saved_or_run(
        repo, replace(s, target_kw=4), "RBC", ref, load, load
    )
    assert not reused and other["fingerprint"] != result["fingerprint"]

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved reuse called optimisation or object upload")

    fresh = Repository(SQLiteDatabase(path), Objects(tmp_path))
    monkeypatch.setattr(dispatch_runs, "run_dispatch", forbidden)
    monkeypatch.setattr(fresh.objects, "put", forbidden)
    equivalent = replace(
        s,
        target_kw=float(s.target_kw),
        time_limit=float(s.time_limit),
        weights=(1.0, 20.0, 1.0, 1.0),
    )
    restored, reused = dispatch_runs.saved_or_run(fresh, equivalent, "RBC", ref, load, load)
    assert reused and restored == result
    assert len(query(db, "SELECT * FROM system_settings WHERE name LIKE 'task06.%'")) == 2
    assert not query(db, "SELECT * FROM model_leases")
    assert not query(db, "SELECT * FROM event_forecast_models")


@pytest.mark.parametrize("method", METHODS)
def test_automatic_target_export_and_paired_run(case, method):
    from batteryflex.dispatch import export_batteries
    from batteryflex.dispatch_comparison import explain_replay, replay_evidence

    s, load = case
    source = tuple(replace(b, export_enabled=False, export_limit_kw=None) for b in s.batteries)
    batteries = export_batteries(source)
    assert all(b.export_enabled and b.export_limit_kw == b.discharge_limit_kw for b in batteries)
    assert not any(b.export_enabled for b in source)
    s = replace(s, batteries=batteries, target_kw=8, target_export_only=True, export_price=1.0)
    actual = load * 0.9
    result = run_dispatch(s, method, load, actual)
    for key in ("planned", "realized"):
        data = result[key]
        event = list(s.event_steps)
        assert data["event_export_kwh"] > 0
        assert data["event_export_kwh"] == pytest.approx(data["export_kwh"])
        grid = np.asarray(data["grid_kw"])
        assert np.all(grid >= -np.array([b.export_limit_kw for b in batteries]) - 1e-6)
        assert data["export_revenue_gbp"] == pytest.approx(data["export_kwh"] * s.export_price)
        assert data["cost_gbp"] == pytest.approx(
            data["import_cost_gbp"] - data["export_revenue_gbp"]
        )
        assert data["discharged_kwh"] == pytest.approx(data["supplied_kwh"] + data["export_kwh"])
        exporting = np.asarray(data["portfolio_export_kw"])[event] > 1e-6
        assert (np.asarray(data["flex_kw"])[event][exporting] <= s.target_kw + 1e-6).all()
        assert sum(h["event_discharged_kwh"] for h in data["households"]) == pytest.approx(
            data["event_discharged_kwh"]
        )
    evidence = replay_evidence(result, s)
    expected_delta = result["realized"]["delivered_kwh"] - result["planned"]["delivered_kwh"]
    assert evidence["request_effect_kwh"] + evidence["correction_effect_kwh"] == pytest.approx(
        expected_delta
    )
    assert explain_replay(result, evidence)
    if method == "MILP":
        assert evidence["changed_intervals"] == 0
        assert result["realized"]["export_kwh"] != result["planned"]["export_kwh"]
        assert "forecast error did not change flexibility" in explain_replay(result, evidence)


def test_tight_replay_export_cap_attributes_physical_correction(case):
    from batteryflex.dispatch import export_batteries
    from batteryflex.dispatch_comparison import explain_replay, replay_evidence

    s, forecast = case
    batteries = export_batteries(tuple(replace(b, export_limit_kw=0.5) for b in s.batteries))
    s = replace(s, batteries=batteries, target_kw=7, target_export_only=True)
    result = run_dispatch(s, "MILP", forecast, forecast * 0.25)
    evidence = replay_evidence(result, s)
    assert evidence["physical_intervals"] == len(s.event_steps)
    assert evidence["request_effect_kwh"] == pytest.approx(0)
    assert evidence["correction_effect_kwh"] < 0
    assert "physical corrections" in explain_replay(result, evidence)
    result["realized_trace"] = []
    assert "does not establish the cause" in explain_replay(result, replay_evidence(result, s))


def test_export_policy_changes_fingerprint_and_respects_explicit_cap(case):
    from batteryflex.dispatch import export_batteries

    s, _ = case
    source = (
        replace(s.batteries[0], export_limit_kw=0.3),
        replace(s.batteries[1], participating=False),
        *s.batteries[2:],
    )
    batteries = export_batteries(source)
    assert batteries[0].export_limit_kw == 0.3
    assert not batteries[1].export_enabled
    new = replace(s, batteries=batteries, target_export_only=True)
    assert dispatch_runs._identity(new, "RBC", {}) != dispatch_runs._identity(
        replace(new, target_export_only=False), "RBC", {}
    )


def test_visible_power_check_never_offsets_a_missed_interval_with_surplus():
    from batteryflex.ui.dispatch_results import _power_check

    assert _power_check(pd.Series([15.0, 5.0]), 10.0) == ("NOT MET", 1, 2.5)
    assert _power_check(pd.Series([10.0, 12.0]), 10.0) == ("MET", 2, 0.0)
    assert _power_check(pd.Series([0.0, 0.0]), 0.0) == ("NOT ASSESSABLE", 0, 0.0)
