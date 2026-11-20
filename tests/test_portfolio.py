"""Portfolio aggregation, atomic edits, durable JSON and future input snapshots."""

import json
from dataclasses import replace

import pytest

from batteryflex.battery import BatteryConfig
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import (
    HOUSEHOLDS,
    INITIAL_SOC,
    Portfolio,
    assess_commitment,
    capability,
    default_portfolio,
    event_capabilities,
    explain_commitment,
    scenario_snapshot,
)
from batteryflex.portfolio_storage import export_configuration, import_configuration


def test_five_defaults_and_aggregation():
    p = default_portfolio()
    assert tuple(b.household_id for b in p.batteries) == HOUSEHOLDS
    assert tuple(b.initial_soc for b in p.batteries) == INITIAL_SOC
    v = capability(p, 1)
    assert v.participating == 5
    assert v.installed_capacity_kwh == v.participating_capacity_kwh == 50
    assert v.usable_kwh == pytest.approx(26.5)
    assert v.deliverable_kwh == pytest.approx(25.1401073983)
    assert v.instantaneous_rating_kw == 25
    assert v.constant_discharge_kw == pytest.approx(22.5894663844)


def test_exclusion_and_no_participants():
    p = default_portfolio().select([HOUSEHOLDS[0]])
    v = capability(p, 1)
    assert v.participating == 1 and v.installed_capacity_kwh == 50
    assert v.participating_capacity_kwh == 10
    assert v.constant_discharge_kw == 5
    assert [power for _, power in v.contributions_kw] == [5, 0, 0, 0, 0]
    v = capability(p.select([]), 1)
    assert v.participating == v.constant_discharge_kw == v.deliverable_kwh == 0
    assert assess_commitment(p.select([]), 1, 0).feasible
    assert not assess_commitment(p.select([]), 1, 1).feasible


@pytest.mark.parametrize(
    "duration,expected",
    [
        (1, 22.5894663844),
        (1.5, 16.7600715989),
        (2, 12.5700536992),
        (3, 8.3800357994),
    ],
)
def test_feasibility_durations(duration, expected):
    p = default_portfolio()
    v = capability(p, duration)
    assert v.constant_discharge_kw == pytest.approx(expected)
    assert assess_commitment(p, duration, v.constant_discharge_kw).feasible
    assert assess_commitment(p, duration, 5).feasible
    bad = assess_commitment(p, duration, 30)
    assert not bad.feasible and bad.shortfall_kw == pytest.approx(30 - expected)
    assert tuple(b.initial_soc for b in p.batteries) == INITIAL_SOC


def test_all_five_reviewed_event_durations():
    events, _, _ = load_selection()
    rows = event_capabilities(default_portfolio(), events)
    assert [(r["Event date"], r["Duration (h)"]) for r in rows] == [
        ("2025-03-18", 1),
        ("2025-11-06", 1),
        ("2023-12-01", 1.5),
        ("2026-01-11", 2),
        ("2025-02-02", 3),
    ]
    assert all(r["Participating households"] == 5 for r in rows)


def test_apply_all_preserves_individual_soc_and_participation_and_can_explicitly_copy():
    p = default_portfolio().select([HOUSEHOLDS[0]])
    source = replace(p.batteries[0], capacity_kwh=12, export_limit_kw=2)
    changed = p.apply_to_all(source)
    assert all(b.capacity_kwh == 12 and b.export_limit_kw == 2 for b in changed.batteries)
    assert tuple(b.initial_soc for b in changed.batteries) == INITIAL_SOC
    assert [b.participating for b in changed.batteries] == [True, False, False, False, False]
    copied = p.apply_to_all(source, copy_soc=True, copy_participation=True)
    assert all(b.initial_soc == 0.8 and b.participating for b in copied.batteries)
    # Bounds incompatible with an individually preserved SOC must reject the entire update.
    with pytest.raises(ValueError):
        p.apply_to_all(replace(source, min_soc=0.7))
    assert p.batteries[3].initial_soc == 0.55
    assert default_portfolio() == default_portfolio()  # restore creates pristine defaults


def test_configuration_roundtrip_all_fields_and_snapshot_is_immutable(tmp_path):
    p = default_portfolio()
    p = p.update(
        replace(
            p.batteries[2],
            initial_soc=0.3,
            export_enabled=False,
            export_limit_kw=0,
            participating=False,
            charge_efficiency=0.8,
            discharge_efficiency=0.85,
            interval_hours=0.25,
        )
    )
    path = tmp_path / "portfolio.json"
    path.write_text(export_configuration(p))
    assert import_configuration(path.read_bytes(), reviewed_five=True) == p
    snap = scenario_snapshot(p, "reviewed-event", 10)
    changed = p.update(replace(p.batteries[0], capacity_kwh=11))
    assert json.loads(snap.portfolio_json)[0]["capacity_kwh"] == 10
    assert scenario_snapshot(changed, "reviewed-event", 10) != snap


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "null",
        "[]",
        '{"schema_version":2,"batteries":[]}',
        '{"schema_version":true,"batteries":[]}',
        '{"schema_version":1,"batteries":[{}]}',
        "x" * 100_001,
    ],
)
def test_invalid_configuration_import(payload):
    with pytest.raises(ValueError):
        import_configuration(payload)


def test_import_rejects_duplicate_missing_nonfinite_and_unknown_fields():
    data = json.loads(export_configuration(default_portfolio()))
    for mutation in ("duplicate", "missing", "nonfinite", "unknown", "wrong_type"):
        copy = json.loads(json.dumps(data))
        if mutation == "duplicate":
            copy["batteries"][1] = copy["batteries"][0]
        elif mutation == "missing":
            copy["batteries"].pop()
        elif mutation == "nonfinite":
            copy["batteries"][0]["initial_soc"] = float("nan")
        elif mutation == "unknown":
            copy["batteries"][0]["extra"] = 1
        else:
            copy["batteries"][0]["export_enabled"] = "false"
        with pytest.raises(ValueError):
            import_configuration(json.dumps(copy), reviewed_five=True)


def test_extendable_model_and_invalid_portfolio_requests():
    extended = Portfolio(default_portfolio().batteries + (BatteryConfig("sixth"),))
    assert capability(extended, 1).participating == 6
    assert import_configuration(export_configuration(extended)) == extended
    with pytest.raises(ValueError):
        import_configuration(export_configuration(extended), reviewed_five=True)
    with pytest.raises(ValueError):
        default_portfolio().select(["unknown"])
    with pytest.raises(ValueError):
        default_portfolio().update(BatteryConfig("unknown"))
    for value in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            assess_commitment(default_portfolio(), 1, value)


def test_constraint_explanation_distinguishes_energy_power_and_combined_limits():
    energy_asset = BatteryConfig(
        "energy",
        capacity_kwh=10,
        min_soc=0,
        initial_soc=0.2,
        discharge_efficiency=1,
        discharge_limit_kw=100,
    )
    result = explain_commitment(Portfolio((energy_asset,)), 1, 3)
    assert result.limiting_cause == "energy"
    assert result.energy_limited_households == ("energy",)
    assert result.required_energy_kwh == 3
    assert result.assessment.shortfall_kw == result.shortfall_energy_kwh == 1
    power_asset = BatteryConfig(
        "power",
        capacity_kwh=100,
        min_soc=0,
        initial_soc=1,
        discharge_efficiency=1,
        discharge_limit_kw=2,
    )
    result = explain_commitment(Portfolio((power_asset,)), 1, 3)
    assert result.limiting_cause == "power"
    assert result.power_limited_households == ("power",)
    both = replace(energy_asset, discharge_limit_kw=1)
    assert explain_commitment(Portfolio((both,)), 1, 5).limiting_cause == "combined"


def test_mixed_individual_limits_fail_despite_sufficient_independent_aggregate_totals():
    energy_poor = BatteryConfig(
        "energy-poor",
        capacity_kwh=10,
        min_soc=0,
        initial_soc=0.1,
        discharge_efficiency=1,
        discharge_limit_kw=10,
    )
    power_poor = BatteryConfig(
        "power-poor",
        capacity_kwh=20,
        min_soc=0,
        initial_soc=1,
        discharge_efficiency=1,
        discharge_limit_kw=1,
    )
    result = explain_commitment(Portfolio((energy_poor, power_poor)), 1, 5)
    assert result.energy_only_power_kw == 21
    assert result.capability.instantaneous_rating_kw == 11
    assert result.capability.constant_discharge_kw == 2
    assert result.assessment.margin_kw == -3
    assert result.limiting_cause == "combined"
    assert result.energy_limited_households == ("energy-poor",)
    assert result.power_limited_households == ("power-poor",)


def test_explanation_default_events_equality_exclusion_and_empty_scenario():
    p = default_portfolio()
    assert explain_commitment(p, 3, 10).limiting_cause == "energy"
    assert explain_commitment(p, 1, 24).limiting_cause == "combined"
    exact = capability(p, 3).constant_discharge_kw
    assert explain_commitment(p, 3, exact).limiting_cause == "none"
    result = explain_commitment(p.select([]), 2, 10)
    assert result.limiting_cause == "no_participants"
    assert result.assessment.shortfall_kw == 10 and result.shortfall_energy_kwh == 20
    assert explain_commitment(p.select([]), 2, 0).limiting_cause == "none"
