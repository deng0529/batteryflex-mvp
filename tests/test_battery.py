"""Analytical energy conservation, physical limits and grid-side restrictions."""

from dataclasses import replace
from math import sqrt

import pytest

from batteryflex.battery import (
    BatteryAction,
    BatteryConfig,
    BatteryState,
    availability,
    final_soc,
    grid_power,
    initial_state,
    transition,
)


def test_defaults_and_energy_conversion():
    b = BatteryConfig("house")
    assert (b.capacity_kwh, b.charge_limit_kw, b.discharge_limit_kw) == (10, 5, 5)
    assert (b.min_soc, b.max_soc, b.initial_soc, b.interval_hours) == (0.2, 1, 0.8, 0.5)
    assert b.round_trip_efficiency == pytest.approx(0.9)
    assert b.export_enabled and b.export_limit_kw is None and b.participating
    assert initial_state(b).energy_kwh == 8
    assert initial_state(b).soc(b) == 0.8


def test_charge_discharge_energy_conservation_and_losses():
    b = BatteryConfig("house", initial_soc=0.5)
    charged = transition(b, initial_state(b), BatteryAction(charge_kw=2), load_kw=1)
    assert charged.energy_kwh == pytest.approx(5 + sqrt(0.9))
    discharged = transition(b, charged, BatteryAction(discharge_kw=2), load_kw=1)
    assert discharged.energy_kwh == pytest.approx(5 + sqrt(0.9) - 1 / sqrt(0.9))
    assert discharged.energy_kwh < 5
    # Stored energy gained in a charge yields exactly 90% back on the AC side.
    restored = transition(b, charged, BatteryAction(discharge_kw=1.8), load_kw=1)
    assert restored.energy_kwh == pytest.approx(5)


@pytest.mark.parametrize(
    "state, action",
    [
        (2, BatteryAction(discharge_kw=0.1)),
        (10, BatteryAction(charge_kw=0.1)),
        (1.9, BatteryAction()),
        (10.1, BatteryAction()),
        (5, BatteryAction(charge_kw=5.01)),
        (5, BatteryAction(discharge_kw=5.01)),
    ],
)
def test_transition_rejects_soc_and_rating_violations(state, action):
    with pytest.raises(ValueError):
        transition(BatteryConfig("house"), BatteryState(state), action, load_kw=1)


def test_soc_boundaries_and_idle_and_explicit_duration():
    b = BatteryConfig("house", charge_efficiency=1, discharge_efficiency=1)
    assert transition(b, BatteryState(2), BatteryAction(), load_kw=0).energy_kwh == 2
    assert transition(b, BatteryState(10), BatteryAction(), load_kw=0).soc(b) == 1
    assert (
        transition(
            b, BatteryState(7), BatteryAction(charge_kw=3), load_kw=0, duration_hours=1
        ).energy_kwh
        == 10
    )
    assert (
        transition(
            b, BatteryState(7), BatteryAction(discharge_kw=5), load_kw=0, duration_hours=1
        ).energy_kwh
        == 2
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"charge_kw": 1, "discharge_kw": 1},
        {"charge_kw": -1},
        {"discharge_kw": float("nan")},
        {"charge_kw": float("inf")},
    ],
)
def test_invalid_actions(kwargs):
    with pytest.raises(ValueError):
        BatteryAction(**kwargs)


def test_grid_import_export_and_net_export_limit():
    b = BatteryConfig("house")
    assert grid_power(b, BatteryAction(charge_kw=2), 1) == 3
    assert grid_power(b, BatteryAction(discharge_kw=3), 1) == -2
    assert grid_power(b, BatteryAction(discharge_kw=1), 1) == 0
    no_export = replace(b, export_enabled=False)
    assert grid_power(no_export, BatteryAction(discharge_kw=1), 1) == 0
    with pytest.raises(ValueError, match="export"):
        transition(no_export, initial_state(b), BatteryAction(discharge_kw=2), load_kw=1)
    capped = replace(b, export_limit_kw=1)
    assert grid_power(capped, BatteryAction(discharge_kw=4), 3) == -1
    with pytest.raises(ValueError, match="export"):
        grid_power(capped, BatteryAction(discharge_kw=4), 2)
    with pytest.raises(ValueError):
        grid_power(b, BatteryAction(), -1)


@pytest.mark.parametrize(
    "duration,expected", [(1, 5), (1.5, 3.7947331922), (2, 2.8460498942), (3, 1.8973665961)]
)
def test_availability_and_final_soc(duration, expected):
    b = BatteryConfig("house")
    a = availability(b, duration)
    assert (a.stored_kwh, a.usable_kwh, a.instantaneous_rating_kw) == (8, 6, 5)
    assert a.deliverable_kwh == pytest.approx(5.6920997883)
    assert a.constant_discharge_kw == pytest.approx(expected)
    end_soc = final_soc(b, a.constant_discharge_kw, duration)
    assert b.min_soc - 1e-10 <= end_soc <= b.initial_soc
    assert end_soc == pytest.approx(0.2 if duration > 1 else 0.2729537233)
    with pytest.raises(ValueError):
        final_soc(b, a.constant_discharge_kw + 0.01, duration)


def test_low_soc_is_valid_and_not_raised():
    b = BatteryConfig("house", initial_soc=0.2001)
    assert availability(b, 3).constant_discharge_kw == pytest.approx(0.000316227766)
    assert b.initial_soc == 0.2001
    empty = replace(b, initial_soc=b.min_soc)
    assert availability(empty, 1).constant_discharge_kw == 0
    assert availability(b, 1, BatteryState(5)).usable_kwh == 3


@pytest.mark.parametrize(
    "kwargs",
    [
        {"capacity_kwh": 0},
        {"capacity_kwh": -1},
        {"capacity_kwh": True},
        {"charge_limit_kw": -1},
        {"discharge_limit_kw": -1},
        {"min_soc": -0.1},
        {"max_soc": 1.1},
        {"initial_soc": 1.1},
        {"min_soc": 0.9, "max_soc": 0.8},
        {"initial_soc": 0.1},
        {"initial_soc": 0.95, "max_soc": 0.9},
        {"initial_soc": float("nan")},
        {"charge_efficiency": 0},
        {"charge_efficiency": 1.01},
        {"discharge_efficiency": -1},
        {"discharge_efficiency": float("inf")},
        {"export_limit_kw": -1},
        {"export_enabled": "yes"},
        {"participating": 1},
        {"interval_hours": 0},
        {"household_id": ""},
    ],
)
def test_invalid_configurations(kwargs):
    with pytest.raises(ValueError):
        BatteryConfig(**({"household_id": "house"} | kwargs))


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf")])
def test_invalid_duration(duration):
    b = BatteryConfig("house")
    with pytest.raises(ValueError):
        availability(b, duration)
    with pytest.raises(ValueError):
        transition(b, initial_state(b), BatteryAction(), load_kw=0, duration_hours=duration)
