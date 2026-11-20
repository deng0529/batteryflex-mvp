"""Saved comparison, MPC evidence and cache recovery acceptance checks."""

import json
from dataclasses import replace

import numpy as np
import pytest

from batteryflex.dispatch import Scenario
from batteryflex.dispatch_evaluation import control_rows, objective_steps
from batteryflex.portfolio import default_portfolio
from batteryflex.storage import dispatch_runs as runs
from batteryflex.storage.database import SQLiteDatabase, migrate, query
from batteryflex.storage.objects import Objects
from batteryflex.storage.repository import Repository, canonical, object_statement
from batteryflex.ui.dispatch_benchmark import grouped_runs


@pytest.fixture
def inputs(tmp_path):
    db = SQLiteDatabase(tmp_path / "sim.sqlite", create=True)
    migrate(db)
    repo = Repository(db, Objects(tmp_path))
    scenario = Scenario(default_portfolio().batteries, (36, 37), 8, prediction_steps=4)
    ref = {
        "event_id": "fixture",
        "forecast_origin": "2013-03-19T00:00:00+00:00",
        "original_event_date": "2025-03-18",
        "artifact_id": "fixture-forecast",
    }
    demand = np.ones((48, 5))
    return repo, scenario, ref, demand


def test_mpc_saved_first_reconciles_event_and_daily_costs(inputs, monkeypatch):
    repo, s, ref, demand = inputs
    result, reused = runs.saved_or_run(repo, s, "MPC", ref, demand, lambda: demand * 0.6)
    assert not reused
    assert result["schema_version"] == 2
    for key, trace in (("planned", "planned_trace"), ("realized", "realized_trace")):
        assert len(result[trace]) == 48 and result[trace][-1]["horizon_steps"] == 1
        rows, actions = control_rows(result, s, key)
        assert len(rows) == 2 and len(actions) == 10
        assert all(row["Horizon (steps)"] == 4 for row in rows)
        assert rows[-1]["Cumulative (kWh)"] == pytest.approx(result[key]["delivered_kwh"])
        costs = objective_steps(s, result[key])
        np.testing.assert_allclose(costs, result["executed_weighted_costs_gbp"][key])
        assert costs.sum() == pytest.approx(result[key]["objective"])
        assert not np.any(costs[:-1, 3])
        one_step = actions[:5]
        assert sum(row["Flexibility (kW)"] for row in one_step) == pytest.approx(
            rows[0]["Delivered (kW)"]
        )

    def forbidden(*args):
        raise AssertionError("Saved-first execution requested compute or replay data")

    monkeypatch.setattr(runs, "run_dispatch", forbidden)
    fresh = Repository(SQLiteDatabase(repo.db.path), Objects(repo.objects.cache))
    second, reused = runs.saved_or_run(fresh, s, "MPC", ref, demand, forbidden)
    assert reused and second == result


def test_comparison_adds_methods_and_isolates_terminal_price(inputs, monkeypatch):
    repo, s, ref, demand = inputs
    for method in ("RBC", "MPC"):
        runs.saved_or_run(repo, s, method, ref, demand, demand)
    grouped = grouped_runs(runs.discover_runs(repo)[0])
    assert [set(items) for items in grouped.values()] == [{"RBC", "MPC"}]
    runs.saved_or_run(repo, replace(s, prediction_steps=6), "MILP", ref, demand, demand)
    runs.saved_or_run(repo, replace(s, terminal_price=0.25), "RBC", ref, demand, demand)
    grouped = grouped_runs(runs.discover_runs(repo)[0])
    assert {frozenset(items) for items in grouped.values()} == {
        frozenset({"RBC", "MPC", "MILP"}),
        frozenset({"RBC"}),
    }
    original = runs._identity(s, "RBC", ref)[0]
    assert (
        original
        == runs._identity(
            s,
            "RBC",
            {
                **ref,
                "forecast_origin": "2013-03-18T23:00:00-01:00",
            },
        )[0]
    )
    assert (
        len(
            {
                runs._identity(replace(s, terminal_price=v), "RBC", ref)[0]
                for v in (0.10, 0.25, 0.50)
            }
        )
        == 3
    )
    monkeypatch.setattr(runs, "ENGINE_VERSION", "future-numerical-version")
    assert original != runs._identity(s, "RBC", ref)[0]


def test_corrupt_result_is_repaired_append_only_and_reused(inputs):
    repo, s, ref, demand = inputs
    first, _ = runs.saved_or_run(repo, s, "RBC", ref, demand, demand)
    key = runs.NAMESPACE + first["fingerprint"]
    row = query(repo.db, "SELECT value_json FROM system_settings WHERE name=?", (key,))[0]
    digest = json.loads(row["value_json"])["object_id"]
    (repo.objects.cache / "objects" / digest).write_bytes(b"damaged fixture")
    repaired, reused = runs.saved_or_run(repo, s, "RBC", ref, demand, demand)
    assert not reused and repaired["fingerprint"] == first["fingerprint"]
    assert query(repo.db, "SELECT value_json FROM system_settings WHERE name=?", (key,)) == [row]
    assert runs.saved_or_run(repo, s, "RBC", ref, demand, None) == (repaired, True)
    found, invalid = runs.discover_runs(repo)
    assert found == [repaired] and invalid == 1


def test_legacy_bundle_and_failed_attempt(inputs, monkeypatch):
    repo, s, ref, demand = inputs
    key, provenance = runs._legacy_identity(s, "RBC", ref)
    result = runs.run_dispatch(s, "RBC", demand, demand)
    result.update(fingerprint=key, provenance=provenance)
    obj = repo.objects.put(canonical(result).encode(), "task06-dispatch-v1")
    repo.db.batch(
        [
            object_statement(obj),
            (
                "INSERT INTO system_settings(name,value_json) VALUES(?,?)",
                (runs.NAMESPACE + key, canonical({"object_id": obj.sha256, "method": "RBC"})),
            ),
        ]
    )

    def fail(*args):
        raise ValueError("injected incomplete simulation")

    monkeypatch.setattr(runs, "run_dispatch", fail)
    saved, reused = runs.saved_or_run(repo, s, "RBC", ref, demand, None)
    assert reused and saved["fingerprint"] == key
    with pytest.raises(ValueError, match="incomplete"):
        runs.saved_or_run(repo, replace(s, target_kw=9), "RBC", ref, demand, demand)
    assert len(runs.discover_runs(repo)[0]) == 1
    assert not query(repo.db, "SELECT * FROM model_leases")
    assert (
        len(
            query(
                repo.db,
                "SELECT * FROM system_settings WHERE name LIKE ?",
                (runs.ATTEMPT_NAMESPACE + "%",),
            )
        )
        == 1
    )


def test_retry_recovers_uploaded_bundle_after_publication_failure(inputs, monkeypatch):
    repo, s, ref, demand = inputs
    original = repo.db.batch

    def fail_publishing(statements):
        if any(sql.startswith("INSERT INTO objects") for sql, _ in statements):
            raise ValueError("injected publication failure")
        return original(statements)

    monkeypatch.setattr(repo.db, "batch", fail_publishing)
    with pytest.raises(ValueError, match="publication failure"):
        runs.saved_or_run(repo, s, "RBC", ref, demand, demand)
    assert not runs.discover_runs(repo)[0]
    monkeypatch.setattr(repo.db, "batch", original)

    def forbidden(*args):
        raise AssertionError("Retry should recover the uploaded bundle")

    monkeypatch.setattr(runs, "run_dispatch", forbidden)
    monkeypatch.setattr(repo.objects, "put", forbidden)
    _, reused = runs.saved_or_run(repo, s, "RBC", ref, demand, forbidden)
    assert reused and len(runs.discover_runs(repo)[0]) == 1
    assert not query(
        repo.db, "SELECT * FROM system_settings WHERE name LIKE ?", (runs.STAGE_NAMESPACE + "%",)
    )
