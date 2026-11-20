"""Phase A coverage using original observations; immutable expanded dataset preparation."""

from datetime import timedelta

import numpy as np
import pandas as pd

from batteryflex.event_policy import DEFAULT_POLICY, EventPolicy, event_examples, midnight
from batteryflex.forecast_training import features as benchmark_features
from batteryflex.forecast_training import history
from batteryflex.lcl_analysis import map_day
from batteryflex.neso_intervals import event_intervals
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import HOUSEHOLDS


def combine_sources(annual: pd.DataFrame, original: pd.DataFrame) -> pd.DataFrame:
    # Preserve the already validated refactored 2013 measurements. Only add earlier original rows.
    year_start = pd.Timestamp("2013-01-01", tz="UTC")
    before = original[original.interval_start_gmt < year_start].copy()
    before["source_dataset"] = "UKPN-original-pre2013"
    retained = annual.copy()
    retained["source_dataset"] = "4TU-2013-v1"
    result = pd.concat([before, retained], ignore_index=True).sort_values(
        ["household_id", "interval_start_gmt"]
    )
    if (
        set(result.household_id) != set(HOUSEHOLDS)
        or result.duplicated(["household_id", "interval_start_gmt"]).any()
    ):
        raise ValueError("Expanded source requires the same five unique household/time identities")
    return result.reset_index(drop=True)


def coverage_matrix(frame: pd.DataFrame, policy: EventPolicy = DEFAULT_POLICY) -> pd.DataFrame:
    events, samples, _ = load_selection()
    rows = []
    for event in events:
        replay = map_day(event["delivery_date"])
        origin = midnight(replay)
        periods = policy.periods(origin)
        for household in HOUSEHOLDS:
            series = history(frame, household)
            valid = series.dropna()
            before = valid[valid.index < origin]
            target = pd.date_range(origin, periods=48, freq="30min")
            previous_day = bool(np.isfinite(series.reindex(target - pd.Timedelta(days=1))).all())
            previous_week = bool(np.isfinite(series.reindex(target - pd.Timedelta(days=7))).all())
            available = {
                p: len(event_examples(series, period)[1]) // 48 for p, period in periods.items()
            }
            try:
                benchmark_features(series, origin)
                legacy = True
            except ValueError:
                legacy = False
            event_targets = [
                midnight(replay)
                + pd.Timedelta(
                    hours=pd.Timestamp(i["start_utc"]).hour,
                    minutes=pd.Timestamp(i["start_utc"]).minute,
                )
                for i in event_intervals(samples[event["resource_id"]], event)
            ]
            actual_event = bool(np.isfinite(series.reindex(event_targets)).all())
            feasible = (
                previous_day
                and previous_week
                and available["training"] >= policy.minimum_training_origins
                and available["validation"] >= policy.minimum_evaluation_origins
                and available["holdout"] >= policy.minimum_evaluation_origins
            )
            missing_window = pd.date_range(
                midnight(periods["training"].start) - timedelta(days=7),
                origin,
                freq="30min",
                inclusive="left",
            )
            rows.append(
                dict(
                    household=household,
                    scenario_id=event["internal_scenario_id"],
                    original_neso_date=str(event["delivery_date"]),
                    event_window=event["start_uk"][11:16] + "–" + event["end_uk"][11:16],
                    duration_minutes=event["duration_minutes"],
                    replay_date=str(replay),
                    forecast_origin=origin.isoformat(),
                    earliest_observation=str(valid.index.min()),
                    latest_before_origin=str(before.index.max()),
                    training_days=available["training"],
                    validation_days=available["validation"],
                    holdout_days=available["holdout"],
                    missing_history_intervals=int(series.reindex(missing_window).isna().sum()),
                    previous_day_available=previous_day,
                    previous_week_available=previous_week,
                    full_day_actual_available=bool(np.isfinite(series.reindex(target)).all()),
                    actual_event_available=actual_event,
                    legacy_strict_week_features_available=legacy,
                    event_features_available=previous_day and previous_week,
                    ridge_feasible=feasible,
                    lightgbm_feasible=feasible,
                    unavailable_reason=""
                    if feasible
                    else "Insufficient complete pre-origin examples or missing historical profiles",
                )
            )
    return pd.DataFrame(rows)
