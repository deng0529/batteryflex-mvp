"""Activation-free, read-only saved forecasts for a future optimisation caller."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite

import pandas as pd

from batteryflex.forecast_contracts import METHODS, ForecastModelConfig
from batteryflex.lcl_analysis import map_day
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.storage.database import query
from batteryflex.storage.event_forecasts import EventForecasts
from batteryflex.storage.repository import Repository, canonical

CANDIDATES = ("Ridge Regression", "LightGBM")  # Order is the deterministic exact-tie policy.


@dataclass(frozen=True)
class ResolvedEventForecast:
    event_id: str
    replay_date: date
    dataset_id: str
    request_id: str
    forecast_origin: datetime
    algorithm: str
    model_version: str
    validation_portfolio_rmse_kw: float
    overridden: bool
    household_forecasts: (
        pd.DataFrame
    )  # 240 rows, interval-start/end, horizon step and predicted kW.
    portfolio_forecast: pd.DataFrame  # 48 rows, complete five-home sum; excludes actual targets.


def validation_rmse(result: dict) -> float:
    metrics = result["metrics"]
    rows = metrics[metrics.scope.eq("validation") & metrics.household.eq("Portfolio")]
    if len(rows) != 1 or int(rows.iloc[0].observations) <= 0:
        raise ValueError("Saved validation portfolio RMSE is unavailable")
    rmse = float(rows.iloc[0].rmse_kw)
    if not isfinite(rmse) or rmse < 0:
        raise ValueError("Saved validation portfolio RMSE is invalid")
    return rmse


def recommended_saved_model(results: list[dict]) -> dict:
    """Compare the two ML candidates from one request; Naive never participates."""
    candidates = []
    for method in CANDIDATES:
        matches = [r for r in results if r["record"]["algorithm"] == method]
        if len(matches) != 1:
            raise ValueError(f"Required saved forecast unavailable: {method}")
        candidates.append(matches[0])
    if len({r["record"]["request_id"] for r in candidates}) != 1:
        raise ValueError("Recommendation candidates must share the same saved event request")
    return min(candidates, key=validation_rmse)


def resolve_event_forecast(
    repo: Repository, event_id: str, *, algorithm: str | None = None
) -> ResolvedEventForecast:
    """Resolve saved default configurations, optionally overriding with any saved method.

    Automatic mode requires both Ridge and LightGBM so an incomplete comparison cannot
    silently change the recommendation. Override mode needs only that candidate. There
    is no fit, activation lookup, activation write, fallback or model regeneration path.
    Existing lookup verifies SHA-256, exact fingerprint, chronology, metrics and sums.
    """
    if algorithm is not None and algorithm not in METHODS:
        raise ValueError(
            "Override must be Ridge Regression, LightGBM or Seasonal Naive (benchmark)"
        )
    events, _, _ = load_selection()
    event = next((e for e in events if e["internal_scenario_id"] == event_id), None)
    if event is None:
        raise ValueError("Unknown reviewed NESO event ID")
    stored = query(repo.db, "SELECT * FROM neso_events WHERE id=?", (event_id,))
    mappings = query(repo.db, "SELECT * FROM replay_mappings WHERE event_id=?", (event_id,))
    if not stored or not mappings:
        raise ValueError("Saved event or historical replay mapping is unavailable")
    mapping = mappings[0]
    if (
        canonical(json.loads(stored[0]["source_json"])) != canonical(event)
        or stored[0]["source_hash"] != event["source_records_sha256"]
        or mapping["original_date"] != str(event["delivery_date"])
        or mapping["household_date"] != str(map_day(event["delivery_date"]))
        or mapping["mapping_version"] != "same-month-weekday-v1"
    ):
        raise ValueError("Saved event/replay mapping differs from the reviewed source")
    service = EventForecasts(repo)
    saved = []
    for method in (algorithm,) if algorithm else CANDIDATES:
        result = service.lookup(event, ForecastModelConfig(method))
        if result is None:
            raise ValueError(f"Required saved forecast unavailable for {event_id}: {method}")
        saved.append(result)
    chosen = saved[0] if algorithm else recommended_saved_model(saved)
    columns = [
        "household",
        "forecast_origin",
        "interval_start",
        "interval_end",
        "horizon_step",
        "prediction",
    ]
    full = chosen["predictions"][chosen["predictions"].partition.eq("full_day")][columns]
    households = full[full.household.isin(HOUSEHOLDS)].sort_values(["household", "horizon_step"])
    portfolio = full[full.household.eq("Portfolio")].sort_values("horizon_step")
    return ResolvedEventForecast(
        event_id=event_id,
        replay_date=date.fromisoformat(mapping["household_date"]),
        dataset_id=chosen["artifact"]["dataset_id"],
        request_id=chosen["record"]["request_id"],
        forecast_origin=datetime.fromisoformat(chosen["artifact"]["request"]["forecast_origin"]),
        algorithm=chosen["record"]["algorithm"],
        model_version=chosen["record"]["version"],
        validation_portfolio_rmse_kw=validation_rmse(chosen),
        overridden=algorithm is not None,
        household_forecasts=households.reset_index(drop=True).copy(),
        portfolio_forecast=portfolio.reset_index(drop=True).copy(),
    )
