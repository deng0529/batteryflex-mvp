"""Event-aligned computation using existing estimators and trusted numeric/native states."""

import numpy as np
import pandas as pd

from batteryflex.event_policy import (
    DEFAULT_POLICY,
    EventPolicy,
    event_examples,
    event_features,
    midnight,
)
from batteryflex.forecast_contracts import ForecastModelConfig
from batteryflex.forecast_training import aggregate, fit, history, metric, predict
from batteryflex.lcl_analysis import map_day
from batteryflex.neso_intervals import event_intervals
from batteryflex.portfolio import HOUSEHOLDS


def replay_intervals(event: dict, sample) -> pd.DatetimeIndex:
    replay = midnight(map_day(event["delivery_date"]))
    original = event_intervals(sample, event)
    result = pd.DatetimeIndex(
        [
            replay
            + pd.Timedelta(
                hours=pd.Timestamp(row["start_utc"]).hour,
                minutes=pd.Timestamp(row["start_utc"]).minute,
            )
            for row in original
        ]
    )
    if len(result) != event["duration_minutes"] // 30 or result.has_duplicates:
        raise ValueError("Event mapping must preserve every original half-hour")
    return result


def score_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, group in predictions.groupby(["partition", "household", "method"]):
        scope, household, method = key if isinstance(key, tuple) else (key, "", "")
        available = group[np.isfinite(group.actual) & np.isfinite(group.prediction)]
        if available.empty:
            continue
        mae, rmse = metric(available.actual.to_numpy(), available.prediction.to_numpy())
        rows.append(
            dict(
                scope=scope,
                household=household,
                method=method,
                mae_kw=mae,
                rmse_kw=rmse,
                observations=len(available),
                expected_observations=len(group),
            )
        )
    return pd.DataFrame(rows)


def admission(frame: pd.DataFrame, event: dict, policy: EventPolicy = DEFAULT_POLICY) -> str:
    origin = midnight(map_day(event["delivery_date"]))
    periods = policy.periods(origin)
    problems = []
    for household in HOUSEHOLDS:
        series = history(frame, household)
        counts = {
            scope: len(event_examples(series, period)[1]) // 48 for scope, period in periods.items()
        }
        try:
            event_features(series, origin)
        except ValueError:
            problems.append(f"{household}: missing complete historical day/week profiles")
        if (
            counts["training"] < policy.minimum_training_origins
            or counts["validation"] < policy.minimum_evaluation_origins
            or counts["holdout"] < policy.minimum_evaluation_origins
        ):
            problems.append(f"{household}: insufficient complete pre-origin examples ({counts})")
    return "; ".join(problems)


def build_event(
    frame: pd.DataFrame,
    event: dict,
    sample,
    config: ForecastModelConfig,
    policy: EventPolicy = DEFAULT_POLICY,
) -> tuple[dict, pd.DataFrame, pd.DataFrame, dict]:
    origin = midnight(map_day(event["delivery_date"]))
    periods = policy.periods(origin)
    models = {}
    outputs = []
    counts = {}
    window = replay_intervals(event, sample)
    for household in HOUSEHOLDS:
        series = history(frame, household)
        parts = {scope: event_examples(series, period) for scope, period in periods.items()}
        counts[household] = {scope: len(values[1]) // 48 for scope, values in parts.items()}
        if (
            counts[household]["training"] < policy.minimum_training_origins
            or counts[household]["validation"] < policy.minimum_evaluation_origins
            or counts[household]["holdout"] < policy.minimum_evaluation_origins
        ):
            raise ValueError(
                f"{household}: insufficient complete pre-origin training/evaluation days"
            )
        target_x = event_features(series, origin)  # admission before any fitting
        models[household] = fit(config, parts["training"][0], parts["training"][1])
        for scope in ("validation", "holdout"):
            x, y, index = parts[scope]
            outputs.append(
                pd.DataFrame(
                    dict(
                        partition=scope,
                        household=household,
                        method=config.method,
                        interval_start=index,
                        actual=y,
                        prediction=predict(models[household], config.method, x),
                    )
                )
            )
        index = pd.date_range(origin, periods=48, freq="30min")
        values = predict(models[household], config.method, target_x)
        outputs.append(
            pd.DataFrame(
                dict(
                    partition="full_day",
                    household=household,
                    method=config.method,
                    interval_start=index,
                    actual=series.reindex(index).to_numpy(dtype=float),
                    prediction=values,
                )
            )
        )
    individual = pd.concat(outputs, ignore_index=True)
    combined = pd.concat([individual, aggregate(individual)], ignore_index=True)
    event_rows = combined[
        combined.partition.eq("full_day") & combined.interval_start.isin(window)
    ].copy()
    event_rows["partition"] = "event_window"
    all_rows = pd.concat([combined, event_rows], ignore_index=True)
    all_rows["forecast_origin"] = all_rows.interval_start.dt.normalize()
    all_rows["horizon_step"] = (
        all_rows.interval_start.dt.hour * 2 + all_rows.interval_start.dt.minute // 30 + 1
    )
    all_rows["interval_end"] = all_rows.interval_start + pd.Timedelta(minutes=30)
    return models, all_rows, score_predictions(all_rows), counts
