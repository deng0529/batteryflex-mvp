"""Contract fixtures only; no production example runs or optimisation outputs."""

from dataclasses import replace

import pytest

from batteryflex.simulation_contracts import (
    EvaluationMetrics,
    ExperimentInputs,
    SimulationRun,
    append_run,
    clear_experiment,
    compatible_runs,
    snapshot,
)


def inputs():
    return ExperimentInputs(
        "internal-event",
        snapshot({"version": 1}),
        snapshot({"home": 50}),
        snapshot({"enabled": True}),
        1.0,
        snapshot({"model": "fixture"}),
        snapshot({"source_sha256": "fixture"}),
    )


def metrics():
    return EvaluationMetrics(100, 0, 0, 0, snapshot({"home": 50}), 0.1)


def test_repeated_strategy_runs_have_unique_ids_and_cannot_overwrite():
    first = SimulationRun.completed(inputs(), "Rule-based", {"fixture": []}, metrics())
    second = SimulationRun.completed(inputs(), "Rule-based", {"fixture": []}, metrics())
    assert first.run_id != second.run_id
    runs = append_run(append_run((), first), second)
    assert len(runs) == 2
    with pytest.raises(ValueError, match="cannot be overwritten"):
        append_run(runs, first)
    assert len(runs) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("event_id", "other"),
        ("battery_configuration_json", snapshot({"version": 2})),
        ("initial_soc_json", snapshot({"home": 40})),
        ("export_settings_json", snapshot({"enabled": False})),
        ("portfolio_commitment_kw", 2.0),
        ("forecast_assumptions_json", snapshot({"model": "other"})),
        ("input_data_references_json", snapshot({"source_sha256": "other"})),
    ],
)
def test_changed_inputs_are_not_compared_and_clear_is_experiment_scoped(field, value):
    original = inputs()
    different = replace(original, **{field: value})
    first = SimulationRun.completed(original, "MILP", {}, metrics())
    second = SimulationRun.completed(different, "Rolling MPC", {}, metrics())
    runs = (first, second)
    assert compatible_runs(runs, original) == (first,)
    assert clear_experiment(runs, original.experiment_id) == (second,)


def test_strategies_share_experiment_and_snapshots_are_immutable():
    data = {"version": 1, "households": ["MAC001391"]}
    saved = snapshot(data)
    data["households"].append("MAC001395")
    assert saved == snapshot({"households": ["MAC001391"], "version": 1})
    runs = tuple(
        SimulationRun.completed(inputs(), strategy, {}, metrics())
        for strategy in ("Rule-based", "MILP", "Rolling MPC")
    )
    assert len(compatible_runs(runs, inputs())) == 3
    canonical = replace(inputs(), export_settings_json='{"enabled":true,"limit_kw":1}')
    reordered = replace(inputs(), export_settings_json='{"limit_kw": 1, "enabled": true}')
    assert canonical.experiment_id == reordered.experiment_id
