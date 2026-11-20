"""Table boundary: percentages in working rows, fractions in validated battery models."""

from math import isfinite

from batteryflex.battery import BatteryConfig, finite
from batteryflex.battery_demo import INTERVAL_HOURS
from batteryflex.portfolio import HOUSEHOLDS, Portfolio

PERCENT_FIELDS = ("initial_soc", "min_soc", "max_soc", "charge_efficiency", "discharge_efficiency")
NUMBER_FIELDS = ("capacity_kwh", "charge_limit_kw", "discharge_limit_kw", *PERCENT_FIELDS)


def portfolio_rows(portfolio: Portfolio) -> list[dict]:
    return [
        {
            "household_id": b.household_id,
            "capacity_kwh": b.capacity_kwh,
            "charge_limit_kw": b.charge_limit_kw,
            "discharge_limit_kw": b.discharge_limit_kw,
            **{field: getattr(b, field) * 100 for field in PERCENT_FIELDS},
            "round_trip_efficiency": b.round_trip_efficiency * 100,
            "export_enabled": b.export_enabled,
            "export_limit_kw": b.export_limit_kw,
            "participating": b.participating,
        }
        for b in portfolio.batteries
    ]


def calculate_round_trip(rows: list[dict]) -> list[dict]:
    """Derived display values must never become independently editable model inputs."""
    result = []
    for row in rows:
        updated = dict(row)
        try:
            value = row["charge_efficiency"] * row["discharge_efficiency"] / 100
            updated["round_trip_efficiency"] = value if isfinite(value) else None
        except (TypeError, KeyError):
            updated["round_trip_efficiency"] = None
        result.append(updated)
    return result


def validate_rows(rows: list[dict]) -> tuple[Portfolio | None, list[str]]:
    """Validate every household and report errors without partially committing rows."""
    if len(rows) != len(HOUSEHOLDS) or [r.get("household_id") for r in rows] != list(HOUSEHOLDS):
        return None, ["Household ID: require exactly the five reviewed households in order."]
    errors = []
    batteries = []
    for row in rows:
        household = row["household_id"]
        try:
            for name in NUMBER_FIELDS:
                finite(row[name], name)
            values = {name: row[name] / 100 for name in PERCENT_FIELDS}
            values.update({name: row[name] for name in NUMBER_FIELDS if name not in PERCENT_FIELDS})
            cap = row["export_limit_kw"]
            # Pandas represents a blank in an otherwise numeric column as NaN.
            if isinstance(cap, float) and cap != cap:
                cap = None
            batteries.append(
                BatteryConfig(
                    household,
                    **values,
                    export_enabled=row["export_enabled"],
                    export_limit_kw=cap,
                    participating=row["participating"],
                    interval_hours=INTERVAL_HOURS,
                )
            )
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"{household}: {exc}")
    return (None, errors) if errors else (Portfolio(tuple(batteries)), [])
