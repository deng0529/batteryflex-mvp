"""Dashboard reporting and partial batch acceptance checks."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from batteryflex.dispatch import DT, Scenario, export_batteries, run_dispatch
from batteryflex.dispatch_dashboard import diagnose_interval, event_outcome
from batteryflex.portfolio import default_portfolio
from batteryflex.storage import dispatch_runs
from batteryflex.storage.database import SQLiteDatabase, migrate
from batteryflex.storage.objects import Objects
from batteryflex.storage.repository import Repository
from batteryflex.ui import dispatch
from batteryflex.ui.dispatch_benchmark import five_event_families, grouped_runs


def test_interval_credit_and_energy_target_are_different():
    s = Scenario(default_portfolio().batteries, (36, 37), 10)
    power = np.zeros(48)
    power[[36, 37]] = [10, 10]
    first = event_outcome(s, {"flex_kw": power})
    assert first.status == "MET" and first.delivered_kwh == 10
    steps = tuple(range(34, 40))
    s = replace(s, event_steps=steps)
    power[list(steps)] = [12, 10, 10, 10, 10, 8]
    interval = event_outcome(s, {"flex_kw": power})
    assert interval.status == "NOT MET" and interval.failed_steps == (39,)
    assert interval.delivered_kwh == 30 and interval.requested_kwh == 30
    assert interval.credited_kwh == 29 and interval.shortfall_kwh == 1
    assert interval.fulfilment_pct == pytest.approx(100 * 29 / 30)
    energy = event_outcome(replace(s, target_type="energy"), {"flex_kw": power})
    assert energy.status == "MET" and energy.failed_steps == () and energy.shortfall_kwh == 0


@pytest.mark.parametrize(
    ("limit", "fragment"),
    [
        ("energy", "Battery energy availability"),
        ("power", "Battery discharge ratings"),
        ("grid", "Household grid export limits"),
    ],
)
def test_shortfall_evidence_is_specific_to_the_verified_bound(limit, fragment):
    settings = {
        "energy": {"initial_soc": 0.25, "discharge_limit_kw": 4.0, "export_limit_kw": 3.0},
        "power": {"initial_soc": 0.9, "discharge_limit_kw": 0.75, "export_limit_kw": 3.0},
        "grid": {"initial_soc": 0.9, "discharge_limit_kw": 4.0, "export_limit_kw": 0.25},
    }[limit]
    batteries = export_batteries(
        tuple(replace(b, **settings) for b in default_portfolio().batteries)
    )
    s = Scenario(batteries, (0,), 8, event_soc=0.25, reserve_soc=0.2, target_export_only=True)
    demand = np.full((48, 5), 0.25 if limit == "grid" else 1.0)
    report = run_dispatch(s, "RBC", demand, demand)
    actual = report["realized"]
    assert event_outcome(s, actual).status == "NOT MET"
    evidence = diagnose_interval(s, report, "realized", 0, s.target_kw)
    assert len(evidence.verified) == 1 and fragment in evidence.verified[0]
    assert evidence.physical_ceiling_kw == pytest.approx(actual["flex_kw"][0])
    if limit == "energy":
        expected = (s.target_kw - actual["flex_kw"][0]) * DT / s.batteries[0].discharge_efficiency
        assert evidence.extra_stored_kwh == pytest.approx(expected)
        diverse = tuple(
            replace(b, discharge_efficiency=0.70 + 0.05 * i) for i, b in enumerate(batteries)
        )
        ceiling = sum(
            b.capacity_kwh * (b.initial_soc - b.min_soc) * b.discharge_efficiency / DT
            for b in diverse
        )
        varied = replace(s, batteries=diverse, target_kw=ceiling + 1)
        varied_run = run_dispatch(varied, "RBC", demand, demand)
        assert diagnose_interval(
            varied, varied_run, "realized", 0, varied.target_kw
        ).extra_stored_kwh == pytest.approx(DT / 0.90)
    else:
        assert evidence.extra_stored_kwh is None
    report["realized"] = {"flex_kw": actual["flex_kw"]}
    assert diagnose_interval(s, report, "realized", 0, s.target_kw).physical_ceiling_kw is None


def test_batch_recovers_partial_failure_and_exposes_saved_events(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite"
    db = SQLiteDatabase(path, create=True)
    migrate(db)
    repo = Repository(db, Objects(tmp_path))
    s = Scenario(default_portfolio().batteries, (0, 1), 4, simulation_mode="EVENT_ONLY")
    dates = pd.date_range("2025-01-01", periods=5)
    events = [
        {"delivery_date": date.date(), "internal_scenario_id": str(i), "duration_minutes": minutes}
        for i, (date, minutes) in enumerate(zip(dates, (60, 60, 90, 120, 180), strict=True))
    ]
    broken = {"2"}
    demand = np.ones((48, 5))

    def forecast(_repo, storage, identity, event, samples, algorithm):
        if identity in broken:
            raise ValueError("Forecast missing")
        date = event["delivery_date"]
        timeline = pd.date_range(f"{date}T00:00:00+00:00", periods=48, freq="30min")
        return (
            SimpleNamespace(dataset_id="fixture"),
            {
                "event_id": identity,
                "original_event_date": str(date),
                "original_event_start": timeline[36].isoformat(),
                "algorithm": algorithm,
                "forecast_origin": timeline[0].isoformat(),
                "artifact_id": identity,
            },
            timeline,
            tuple(range(36, 36 + event["duration_minutes"] // 30)),
            demand,
        )

    monkeypatch.setattr(dispatch, "_forecast", forecast)
    monkeypatch.setattr(
        dispatch, "_actual", lambda repo, storage, dataset, times: demand[: len(times)]
    )
    partial = dispatch._batch(repo, "local", events, {}, "LightGBM", "RBC", "fixture", {}, s)
    assert partial["Status"].tolist() == ["MET", "MET", "FAILED", "MET", "MET"]
    assert len(dispatch_runs.discover_runs(repo)[0]) == 4
    broken.clear()
    fresh = Repository(SQLiteDatabase(path), Objects(tmp_path))
    finished = dispatch._batch(fresh, "local", events, {}, "LightGBM", "RBC", "fixture", {}, s)
    assert finished["Source"].tolist() == ["Saved", "Saved", "Newly calculated", "Saved", "Saved"]
    results, invalid = dispatch_runs.discover_runs(fresh)
    assert len(results) == 5 and invalid == 0
    assert [len(groups) for groups in five_event_families(grouped_runs(results)).values()] == [5]
    assert finished["Delivered (kWh)"].sum() == pytest.approx(34)
