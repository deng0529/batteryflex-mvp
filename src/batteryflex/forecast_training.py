"""Origin-safe daily examples, household models and aligned backtests (no dispatch)."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from batteryflex.forecast_contracts import ForecastDatasetConfig, ForecastModelConfig, gmt_half_hour
from batteryflex.forecast_data import historical_series
from batteryflex.portfolio import HOUSEHOLDS

FEATURES = (
    "time_sin",
    "time_cos",
    "weekday",
    "weekend",
    "step",
    "lag_day",
    "lag_week",
    "day_mean",
    "day_std",
    "week_mean",
    "week_std",
)


def history(frame: pd.DataFrame, household: str) -> pd.Series:
    rows = historical_series(
        frame,
        (household,),
        frame.interval_start_gmt.min().date(),
        frame.interval_start_gmt.max().date(),
    )
    return rows.set_index("interval_start_gmt").average_power_kw


def features(series: pd.Series, origin: datetime) -> np.ndarray:
    """Only intervals ending <= origin may contribute measured inputs."""
    gmt_half_hour(origin)
    if origin.hour or origin.minute:
        raise ValueError("Daily forecasters require midnight GMT origins")
    targets = pd.date_range(origin, periods=48, freq="30min")
    past = series.reindex(
        pd.date_range(pd.Timestamp(origin) - pd.Timedelta(days=7), periods=336, freq="30min")
    ).to_numpy(dtype=float)
    day = series.reindex(targets - pd.Timedelta(days=1)).to_numpy(dtype=float)
    week = series.reindex(targets - pd.Timedelta(days=7)).to_numpy(dtype=float)
    if not np.isfinite(past).all() or not np.isfinite(day).all() or not np.isfinite(week).all():
        raise ValueError("Incomplete seven-day origin history; no imputation")
    step = np.arange(48)
    return np.column_stack(
        (
            np.sin(2 * np.pi * step / 48),
            np.cos(2 * np.pi * step / 48),
            targets.day_of_week,
            targets.day_of_week >= 5,
            step + 1,
            day,
            week,
            np.full(48, past[-48:].mean()),
            np.full(48, past[-48:].std()),
            np.full(48, past.mean()),
            np.full(48, past.std()),
        )
    )


def examples(series: pd.Series, period: Any) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    xs, ys, times = [], [], []
    for origin in pd.date_range(period.start, period.end, tz="UTC", freq="D"):
        index = pd.date_range(origin, periods=48, freq="30min")
        y = series.reindex(index).to_numpy(dtype=float)
        if not np.isfinite(y).all():
            continue
        try:
            x = features(series, origin.to_pydatetime())
        except ValueError:
            continue
        xs.append(x)
        ys.append(y)
        times.extend(index)
    if not xs:
        raise ValueError("No complete day-ahead examples in partition after warm-up/exclusions")
    return np.concatenate(xs), np.concatenate(ys), pd.DatetimeIndex(times)


def fit(config: ForecastModelConfig, x: np.ndarray, y: np.ndarray) -> Any:
    params = json.loads(config.hyperparameters_json)
    if config.method == "Seasonal Naive":
        return None
    if config.method == "Ridge Regression":
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        return make_pipeline(StandardScaler(), Ridge(alpha=params.get("alpha", 1.0))).fit(x, y)
    from lightgbm import LGBMRegressor

    settings: dict[str, Any] = dict(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=15,
        max_depth=-1,
        random_state=42,
        min_child_samples=30,
        reg_lambda=1.0,
        n_jobs=1,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )
    settings.update(params)
    settings["random_state"] = 42
    return LGBMRegressor(**settings).fit(x, y)


def predict(model: Any, method: str, x: np.ndarray) -> np.ndarray:
    if method == "Seasonal Naive":
        values = x[:, FEATURES.index("lag_day")]
    elif isinstance(model, dict):
        values = ((x - np.array(model["mean"])) / np.array(model["scale"])) @ np.array(
            model["coef"]
        ) + model["intercept"]
    else:
        values = model.predict(x)
    values = np.asarray(values, dtype=float)
    if values.shape != (len(x),) or not np.isfinite(values).all():
        raise ValueError("Model returned invalid/incomplete predictions")
    return np.maximum(values, 0.0)  # physical demand, applied consistently in evaluation/inference


def metric(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float]:
    if (
        len(actual) == 0
        or actual.shape != predicted.shape
        or not (np.isfinite(actual).all() and np.isfinite(predicted).all())
    ):
        raise ValueError("Metrics require aligned finite nonempty observations")
    error = actual - predicted
    return float(np.abs(error).mean()), float(np.sqrt(np.mean(error**2)))


def improvement(baseline: float, value: float) -> float | None:
    return 100 * (baseline - value) / baseline if baseline > 0 else None


def aggregate(rows: pd.DataFrame, household_ids: tuple[str, ...] = HOUSEHOLDS) -> pd.DataFrame:
    keys = ["partition", "method", "interval_start"]
    groups = rows.groupby(keys, sort=True)
    valid = groups.household.agg(
        lambda x: len(x) == len(household_ids) and set(x) == set(household_ids)
    )
    result = (
        groups[["actual", "prediction"]].sum(min_count=len(household_ids)).loc[valid].reset_index()
    )
    result["household"] = "Portfolio"
    return result


def metrics_table(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for key, group in rows.groupby(["partition", "household", "method"]):
        partition, household, method = tuple(key) if isinstance(key, tuple) else (key, "", "")
        mae, rmse = metric(group.actual.to_numpy(), group.prediction.to_numpy())
        records.append(
            dict(
                partition=partition,
                household=household,
                method=method,
                mae_kw=mae,
                rmse_kw=rmse,
                observations=len(group),
            )
        )
    table = pd.DataFrame(records)
    base = table[table.method == "Seasonal Naive"].set_index(["partition", "household"])
    table["mae_improvement_pct"] = [
        improvement(base.loc[(r["partition"], r["household"]), "mae_kw"], r["mae_kw"])
        for r in table.to_dict("records")
    ]
    table["rmse_improvement_pct"] = [
        improvement(base.loc[(r["partition"], r["household"]), "rmse_kw"], r["rmse_kw"])
        for r in table.to_dict("records")
    ]
    return table


@dataclass
class ModelRun:
    dataset: ForecastDatasetConfig
    configs: tuple[ForecastModelConfig, ...]
    models: dict[str, dict[str, Any]]
    predictions: pd.DataFrame
    metrics: pd.DataFrame
    counts: pd.DataFrame
    source_sha256: str


def run_models(
    frame: pd.DataFrame,
    configs: tuple[ForecastModelConfig, ...],
    dataset: ForecastDatasetConfig,
    source_sha256: str,
) -> ModelRun:
    if not dataset.household_ids or not configs:
        raise ValueError("Select algorithms and a nonempty validated household selection")
    if len({c.method for c in configs}) != len(configs):
        raise ValueError("Duplicate algorithms")
    if not any(c.method == "Seasonal Naive" for c in configs):
        configs = (ForecastModelConfig(), *configs)
    models: dict[str, dict[str, Any]] = {c.method: {} for c in configs}
    rows, counts = [], []
    for household in dataset.household_ids:
        series = history(frame, household)
        parts = {
            p: examples(series, getattr(dataset, p)) for p in ("training", "validation", "testing")
        }
        for p, (_, y, _) in parts.items():
            counts.append(
                dict(household=household, partition=p, origins=len(y) // 48, observations=len(y))
            )
        for config in configs:
            try:
                models[config.method][household] = fit(
                    config, parts["training"][0], parts["training"][1]
                )
                for p in ("validation", "testing"):
                    x, y, times = parts[p]
                    predicted = predict(models[config.method][household], config.method, x)
                    rows.append(
                        pd.DataFrame(
                            dict(
                                household=household,
                                partition=p,
                                method=config.method,
                                interval_start=times,
                                actual=y,
                                prediction=predicted,
                            )
                        )
                    )
            except Exception as exc:
                raise ValueError(f"{config.method} / {household} failed: {exc}") from exc
    individual = pd.concat(rows, ignore_index=True)
    # All methods share each household's admitted origins; sum only all-five intervals.
    all_rows = pd.concat(
        [individual, aggregate(individual, dataset.household_ids)], ignore_index=True
    )
    return ModelRun(
        dataset,
        configs,
        models,
        all_rows,
        metrics_table(all_rows),
        pd.DataFrame(counts),
        source_sha256,
    )
