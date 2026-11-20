"""Boundary completion time and strict half-hour transitions with an exact final step."""

from dataclasses import replace
from math import sqrt

import pytest

from batteryflex.battery import BatteryAction, BatteryConfig, initial_state, transition
from batteryflex.battery_demo import demonstrate


@pytest.mark.parametrize(
    "mode,expected_time,expected_energy,boundary",
    [
        ("Charge", 2 / (sqrt(0.9) * 5), 2 / sqrt(0.9), 1),
        ("Discharge", 6 * sqrt(0.9) / 5, 6 * sqrt(0.9), 0.2),
    ],
)
def test_default_boundary_completion_time_energy_and_partial_step(
    mode, expected_time, expected_energy, boundary
):
    b = BatteryConfig("house")
    result = demonstrate(b, mode, 5)
    assert result.completion_hours == pytest.approx(expected_time)
    assert result.electrical_energy_kwh == pytest.approx(expected_energy)
    assert result.final_soc == boundary
    assert result.intervals[-1].elapsed_hours == result.completion_hours
    assert 0 < result.intervals[-1].duration_hours < 0.5
    assert all(i.duration_hours == 0.5 for i in result.intervals[:-1])
    assert sum(i.duration_hours for i in result.intervals) == pytest.approx(expected_time)
    assert all(b.min_soc <= i.soc <= b.max_soc for i in result.intervals)
    assert b.initial_soc == 0.8


@pytest.mark.parametrize("mode", ["Charge", "Discharge"])
def test_soc_curve_matches_analytical_energy_balance_at_every_point(mode):
    b = BatteryConfig("house", initial_soc=0.5, charge_efficiency=0.8, discharge_efficiency=0.9)
    result = demonstrate(b, mode, 2)
    for row in result.intervals:
        expected = (
            5 + 0.8 * 2 * row.elapsed_hours if mode == "Charge" else 5 - 2 * row.elapsed_hours / 0.9
        )
        assert row.energy_kwh == pytest.approx(expected)
        assert row.soc == pytest.approx(expected / 10)
        assert row.charge_kw == (2 if mode == "Charge" else 0)
        assert row.discharge_kw == (2 if mode == "Discharge" else 0)
    assert result.electrical_energy_kwh == pytest.approx(5 / 0.8 if mode == "Charge" else 3 * 0.9)


@pytest.mark.parametrize("mode,initial,boundary", [("Charge", 0.99, 1), ("Discharge", 0.21, 0.2)])
def test_boundary_before_first_half_hour_uses_actual_short_step(mode, initial, boundary):
    b = BatteryConfig("house", initial_soc=initial)
    result = demonstrate(b, mode, 5)
    assert len(result.intervals) == 1
    assert 0 < result.completion_hours < 0.5
    assert result.intervals[0].duration_hours == result.completion_hours
    assert result.final_soc == boundary
    assert result.electrical_energy_kwh == pytest.approx(5 * result.completion_hours)


@pytest.mark.parametrize("mode,initial", [("Charge", 1), ("Discharge", 0.2)])
def test_initial_at_boundary_returns_zero_duration_and_no_transitions(mode, initial):
    result = demonstrate(BatteryConfig("house", initial_soc=initial), mode, 5)
    assert result.completion_hours == result.electrical_energy_kwh == 0
    assert result.final_soc == initial and not result.intervals


def test_exact_half_hour_completion_has_no_spurious_extra_step():
    b = BatteryConfig("house", initial_soc=0.5, max_soc=0.7, charge_efficiency=1)
    result = demonstrate(b, "Charge", 4)
    assert result.completion_hours == pytest.approx(0.5)
    assert len(result.intervals) == 1
    assert result.final_soc == 0.7


def test_reducing_power_extends_time_without_changing_electrical_energy():
    b = BatteryConfig("house")
    fast = demonstrate(b, "Discharge", 5)
    slow = demonstrate(b, "Discharge", 1)
    assert slow.completion_hours == pytest.approx(fast.completion_hours * 5)
    assert slow.electrical_energy_kwh == pytest.approx(fast.electrical_energy_kwh)
    # There is no former 24-hour duration cap.
    assert demonstrate(b, "Charge", 0.01).completion_hours > 24


def test_grid_settings_and_saved_initial_soc_are_not_mutated_or_enforced_in_performance():
    b = BatteryConfig("house", export_enabled=False, export_limit_kw=0, participating=False)
    original = replace(b)
    free = replace(b, export_enabled=True, export_limit_kw=None)
    assert demonstrate(b, "Discharge", 2) == demonstrate(free, "Discharge", 2)
    assert b == original
    with pytest.raises(ValueError, match="export"):
        transition(b, initial_state(b), BatteryAction(discharge_kw=2), load_kw=0)


@pytest.mark.parametrize(
    "mode,power",
    [
        ("Idle", 1),
        ("unknown", 1),
        ("Charge", 0),
        ("Charge", -1),
        ("Discharge", float("nan")),
        ("Charge", float("inf")),
        ("Discharge", 5.01),
    ],
)
def test_invalid_operating_power_and_mode(mode, power):
    with pytest.raises(ValueError):
        demonstrate(BatteryConfig("house"), mode, power)


def test_zero_power_rating_and_extreme_curve_workload_fail_explicitly():
    with pytest.raises(ValueError, match="rating"):
        demonstrate(BatteryConfig("house", charge_limit_kw=0), "Charge", 1)
    with pytest.raises(ValueError, match="100,000"):
        demonstrate(BatteryConfig("house"), "Charge", 0.000001)
