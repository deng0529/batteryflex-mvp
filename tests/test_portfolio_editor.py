"""All table fields, percentage conversion and per-household validation."""

import pytest

from batteryflex.portfolio import HOUSEHOLDS, default_portfolio
from batteryflex.portfolio_editor import calculate_round_trip, portfolio_rows, validate_rows


def test_percentages_and_defaults_roundtrip():
    rows = portfolio_rows(default_portfolio())
    assert [r["initial_soc"] for r in rows] == pytest.approx([80, 65, 90, 55, 75])
    assert all(r["round_trip_efficiency"] == pytest.approx(90) for r in rows)
    assert "interval_hours" not in rows[0]
    assert validate_rows(rows) == (default_portfolio(), [])


def test_every_editable_field_and_readonly_efficiency():
    rows = portfolio_rows(default_portfolio())
    for i, row in enumerate(rows):
        row.update(
            capacity_kwh=12 + i,
            charge_limit_kw=3,
            discharge_limit_kw=4,
            initial_soc=40 + i,
            min_soc=10,
            max_soc=95,
            charge_efficiency=80,
            discharge_efficiency=90,
            export_enabled=False,
            export_limit_kw=1.5,
            participating=False,
            round_trip_efficiency=99,
        )
    recalculated = calculate_round_trip(rows)
    assert all(r["round_trip_efficiency"] == 72 for r in recalculated)
    portfolio, errors = validate_rows(recalculated)
    assert not errors and portfolio is not None
    for i, b in enumerate(portfolio.batteries):
        assert b.household_id == HOUSEHOLDS[i]
        assert b.capacity_kwh == 12 + i
        assert (b.charge_limit_kw, b.discharge_limit_kw) == (3, 4)
        assert b.initial_soc == (40 + i) / 100
        assert (b.min_soc, b.max_soc) == (0.1, 0.95)
        assert (b.charge_efficiency, b.discharge_efficiency) == (0.8, 0.9)
        assert b.round_trip_efficiency == pytest.approx(0.72)
        assert not b.export_enabled and b.export_limit_kw == 1.5 and not b.participating
        assert b.interval_hours == 0.5


@pytest.mark.parametrize(
    "field,value",
    [
        ("capacity_kwh", 0),
        ("charge_limit_kw", -1),
        ("discharge_limit_kw", -1),
        ("initial_soc", 19),
        ("initial_soc", 101),
        ("min_soc", 95),
        ("max_soc", 75),
        ("charge_efficiency", 0),
        ("discharge_efficiency", 101),
        ("export_limit_kw", -1),
        ("participating", "yes"),
        ("export_enabled", 1),
        ("initial_soc", None),
        ("capacity_kwh", float("inf")),
    ],
)
def test_invalid_rows_identify_household_and_parameter(field, value):
    rows = portfolio_rows(default_portfolio())
    rows[2][field] = value
    result, errors = validate_rows(rows)
    assert result is None and len(errors) == 1
    assert HOUSEHOLDS[2] in errors[0]
    assert errors[0].split(": ", 1)[1]


def test_multiple_bad_households_are_reported_and_nullable_cap_is_preserved():
    rows = portfolio_rows(default_portfolio())
    rows[0]["capacity_kwh"] = 0
    rows[1]["initial_soc"] = 1
    assert len(validate_rows(rows)[1]) == 2
    rows = portfolio_rows(default_portfolio())
    rows[0]["export_limit_kw"] = 0
    rows[1]["export_limit_kw"] = float("nan")
    result, errors = validate_rows(rows)
    assert not errors and result is not None
    assert result.batteries[0].export_limit_kw == 0
    assert result.batteries[1].export_limit_kw is None
    rows[0]["household_id"] = "other"
    assert validate_rows(rows)[0] is None
