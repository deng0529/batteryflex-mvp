"""Standard event-only execution and cache isolation."""

from dataclasses import replace

import numpy as np
import pytest

from batteryflex import dispatch
from batteryflex.dispatch import METHODS, Scenario, export_batteries, run_dispatch
from batteryflex.dispatch_evaluation import validate_result
from batteryflex.dispatch_event import event_evidence, event_start_batteries, qualify
from batteryflex.neso_intervals import event_intervals
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import default_portfolio
from batteryflex.storage.database import SQLiteDatabase, migrate
from batteryflex.storage.dispatch_runs import _identity, saved_or_run
from batteryflex.storage.objects import Objects
from batteryflex.storage.repository import Repository


def scenario(n):
    return Scenario(
        export_batteries(event_start_batteries(default_portfolio().batteries)),
        tuple(range(n)),
        10,
        simulation_mode="EVENT_ONLY",
        target_export_only=True,
    )


def test_registry_and_standard_qualification():
    events, samples, _ = load_selection()
    assert [
        (
            str(e["delivery_date"]),
            e["start_utc"][11:16],
            e["end_utc"][11:16],
            len(event_intervals(samples[e["resource_id"]], e)),
        )
        for e in events
    ] == [
        ("2025-03-18", "18:00", "19:00", 2),
        ("2025-11-06", "17:00", "18:00", 2),
        ("2023-12-01", "16:30", "18:00", 3),
        ("2026-01-11", "17:00", "19:00", 4),
        ("2025-02-02", "16:00", "19:00", 6),
    ]
    s = scenario(6)
    forecast = np.ones((6, 5))
    q = qualify(s, forecast)
    assert q["status"] == "QUALIFIED"
    assert q["initial_kwh"] == pytest.approx(44.5)
    assert q["available_kwh"] == pytest.approx(32.73, abs=0.01)
    poor = replace(s, batteries=tuple(replace(b, initial_soc=0.30) for b in s.batteries))
    assert qualify(poor, forecast)["status"] == "INFEASIBLE"
    blocked = replace(s, batteries=tuple(replace(b, export_limit_kw=0) for b in s.batteries))
    assert qualify(blocked, forecast)["status"] == "INFEASIBLE"


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("n", [2, 6])
def test_event_execution_and_objective(method, n):
    s = scenario(n)
    forecast = np.ones((n, 5))
    actual = forecast * 0.6
    result = run_dispatch(s, method, forecast, actual)
    validate_result(result, s)
    evidence = event_evidence(result, s, {"original_event_start": "2025-02-02T16:00:00+00:00"})
    rows = evidence["execution_records"]["realized"]
    assert len(rows) == n
    np.testing.assert_allclose(
        rows[0]["energy_before_kwh"], [b.capacity_kwh * b.initial_soc for b in s.batteries]
    )
    assert rows[-1]["cumulative_running_cost"] + rows[-1]["weighted_interval_costs"][
        3
    ] == pytest.approx(result["realized"]["objective"])
    assert all(row["weighted_interval_costs"][3] == 0 for row in rows[:-1])
    if method == "MPC":
        assert [row["horizon_steps"] for row in rows] == list(range(n, 0, -1))
    if method == "MILP":
        assert result["solver_iterations"] == 1
    if method == "RBC":
        assert result["solver_iterations"] == 0 and all(r["rule"].startswith("Event") for r in rows)
    for trace in (result["planned_trace"], result["realized_trace"]):
        for r in trace:
            if "solver_objective" in r:
                assert sum(r["predicted_weighted_terms"]) == pytest.approx(r["solver_objective"])


def test_replay_uses_no_completed_interval_average(monkeypatch):
    s = scenario(6)
    forecast = np.ones((6, 5))
    measured = np.full((6, 5), 0.6)
    original = dispatch._solve
    observed = []

    def spy(s, load, energy, k, delivered):
        observed.append(load.copy())
        return original(s, load, energy, k, delivered)

    monkeypatch.setattr(dispatch, "_solve", spy)
    run_dispatch(s, "MPC", forecast, measured)
    for k, window in enumerate(observed[6:]):
        np.testing.assert_array_equal(window, forecast[k:])


def test_event_cache_and_legacy_isolation(tmp_path, monkeypatch):
    s = scenario(2)
    path = tmp_path / "runs.sqlite"
    db = SQLiteDatabase(path, create=True)
    migrate(db)
    repo = Repository(db, Objects(tmp_path))
    ref = {"original_event_start": "2025-03-18T18:00:00+00:00"}
    forecast = np.ones((2, 5))
    result, hit = saved_or_run(repo, s, "RBC", ref, forecast, forecast)
    assert not hit and result["provenance"]["experiment_id"] == "STANDARD"
    assert (
        _identity(s, "RBC", ref)[0]
        != _identity(replace(s, simulation_mode="FULL_DAY"), "RBC", ref)[0]
    )
    assert _identity(s, "RBC", ref)[0] != _identity(replace(s, target_kw=9), "RBC", ref)[0]

    def fail(*args, **kwargs):
        raise AssertionError("Cache reuse unexpectedly executed a controller")

    monkeypatch.setattr("batteryflex.storage.dispatch_runs.run_dispatch", fail)
    fresh = Repository(SQLiteDatabase(path), Objects(tmp_path))
    assert saved_or_run(fresh, s, "RBC", ref, forecast, fail) == (result, True)
    assert event_evidence(result, s, ref)["explanations"] == result["explanations"]
