"""Packaged application defaults using the JSON subset of YAML 1.2."""

import json
from dataclasses import dataclass, fields
from functools import cache
from importlib.resources import files

from batteryflex.battery import BatteryConfig, finite


@dataclass(frozen=True)
class AppDefaults:
    name: str
    subtitle: str
    version: str
    precision: int

    def __post_init__(self) -> None:
        if any(
            not isinstance(s, str) or not s.strip()
            for s in (self.name, self.subtitle, self.version)
        ):
            raise ValueError("Name, subtitle and version must be non-empty text")
        if type(self.precision) is not int or not 0 <= self.precision <= 6:
            raise ValueError("Display precision must be an integer from 0 to 6")


@dataclass(frozen=True)
class SimulationDefaults:
    experiment: str
    mode: str
    target_kw: float
    import_price: float
    export_price: float
    degradation_price: float
    terminal_price: float
    optional_import_cap_kw: float
    reserve_soc: float
    target_soc: float
    prediction_steps: int
    time_limit: float
    gap: float
    weights: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if (self.experiment, self.mode) != ("A", "EVENT_ONLY"):
            raise ValueError("The standard experiment requires event-only operation")
        if type(self.prediction_steps) is not int or not 1 <= self.prediction_steps <= 48:
            raise ValueError("MPC prediction steps must be an integer from 1 to 48")
        if len(self.weights) != 4:
            raise ValueError("Supply four objective weights")
        for name in (
            "target_kw",
            "import_price",
            "export_price",
            "degradation_price",
            "terminal_price",
            "optional_import_cap_kw",
            "reserve_soc",
            "target_soc",
            "time_limit",
            "gap",
        ):
            value = getattr(self, name)
            finite(value, name)
            object.__setattr__(self, name, float(value))
        for weight in self.weights:
            finite(weight, "Objective weight")
        object.__setattr__(self, "weights", tuple(float(v) for v in self.weights))
        if max(self.gap, self.reserve_soc, self.target_soc) > 1:
            raise ValueError("Gap and state-of-charge fractions must be between 0 and 1")
        if not 0.1 <= self.time_limit <= 120:
            raise ValueError("Time limit must be 0.1–120 seconds")
        if any(round(soc * 100) / 100 != soc for soc in (self.reserve_soc, self.target_soc)):
            raise ValueError("Reserve and target SoC must use whole percentage points")


@dataclass(frozen=True)
class ForecastingDefaults:
    dispatch_priority: tuple[str, ...]
    ridge_alpha: float
    lightgbm_trees: int
    lightgbm_learning_rate: float
    lightgbm_leaves: int

    def __post_init__(self) -> None:
        from batteryflex.forecast_contracts import METHODS, ForecastModelConfig
        from batteryflex.simulation_contracts import snapshot

        if len(self.dispatch_priority) != len(METHODS) or set(self.dispatch_priority) != set(
            METHODS
        ):
            raise ValueError("List each supported forecast model exactly once")
        ForecastModelConfig("Ridge Regression", snapshot({"alpha": self.ridge_alpha}))
        ForecastModelConfig(
            "LightGBM",
            snapshot(
                {
                    "n_estimators": self.lightgbm_trees,
                    "learning_rate": self.lightgbm_learning_rate,
                    "num_leaves": self.lightgbm_leaves,
                }
            ),
        )
        if self.lightgbm_learning_rate < 0.001:
            raise ValueError("LightGBM learning rate must be at least 0.001")
        object.__setattr__(self, "ridge_alpha", float(self.ridge_alpha))
        object.__setattr__(self, "lightgbm_learning_rate", float(self.lightgbm_learning_rate))


@dataclass(frozen=True)
class PortfolioDefaults:
    batteries: tuple[BatteryConfig, ...]
    event_start_soc: tuple[float, ...]


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    values: dict = {}
    for key, value in pairs:
        if key in values:
            raise ValueError(f"Repeated configuration key {key}")
        values[key] = value
    return values


def _read(name: str) -> dict:
    value = json.loads(
        files("batteryflex").joinpath("resources", name).read_text(encoding="utf-8"),
        object_pairs_hook=_unique_keys,
    )
    if not isinstance(value, dict):
        raise ValueError("Expected a configuration mapping")
    return value


@cache
def load_defaults[Defaults: (AppDefaults, ForecastingDefaults, SimulationDefaults)](
    name: str, kind: type[Defaults]
) -> Defaults:
    try:
        values = _read(name)
        if kind is SimulationDefaults:
            values["weights"] = tuple(values["weights"])
        if kind is ForecastingDefaults:
            values["dispatch_priority"] = tuple(values["dispatch_priority"])
        return kind(**values)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {exc}") from exc


@cache
def portfolio_defaults() -> PortfolioDefaults:
    try:
        values = _read("portfolio.yaml")
        common = values["common"]
        expected = {field.name for field in fields(BatteryConfig)} - {"household_id", "initial_soc"}
        if set(values) != {"common", "assets"} or set(common) != expected:
            raise ValueError("Supply all common battery fields and the reviewed asset list")
        batteries, event_soc = [], []
        for asset in values["assets"]:
            entry = dict(asset)
            start = entry.pop("event_start_soc")
            finite(start, "Event-start SoC")
            if set(entry) != {"household_id", "initial_soc"}:
                raise ValueError("Each asset requires an ID, initial SoC and event-start SoC")
            battery = BatteryConfig(**common, **entry)
            if battery.interval_hours != 0.5:
                raise ValueError("Battery interval must be 0.5 hours")
            if not battery.min_soc <= start <= battery.max_soc:
                raise ValueError("Event-start SoC must be within the configured battery bounds")
            batteries.append(battery)
            event_soc.append(start)
        if len(batteries) != 5 or len({b.household_id for b in batteries}) != 5:
            raise ValueError("Supply five unique reviewed households in registry order")
        return PortfolioDefaults(tuple(batteries), tuple(event_soc))
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid portfolio.yaml: {exc}") from exc
