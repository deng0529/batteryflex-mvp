"""Event replay policy and origin-safe day/week profile features; no fitting."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from batteryflex.forecast_contracts import DatePeriod, gmt_half_hour

SCHEMA = "load-event-dayweek-v1"
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
    "previous_weekday_mean",
    "previous_weekday_std",
)


@dataclass(frozen=True)
class EventPolicy:
    training_days: int = 90
    validation_days: int = 14
    holdout_days: int = 14
    minimum_training_origins: int = 28
    minimum_evaluation_origins: int = 7
    version: str = "event-expanding-capped-90-v1"

    def periods(self, origin: datetime) -> dict[str, DatePeriod]:
        gmt_half_hour(origin)
        if origin.hour or origin.minute:
            raise ValueError("Event forecast origins must be midnight GMT")
        day = origin.date()
        train_end = day - timedelta(days=self.validation_days + self.holdout_days + 1)
        return dict(
            training=DatePeriod(train_end - timedelta(days=self.training_days - 1), train_end),
            validation=DatePeriod(
                day - timedelta(days=self.validation_days + self.holdout_days),
                day - timedelta(days=self.holdout_days + 1),
            ),
            holdout=DatePeriod(day - timedelta(days=self.holdout_days), day - timedelta(days=1)),
        )


DEFAULT_POLICY = EventPolicy()


def event_features(series: pd.Series, origin: datetime) -> np.ndarray:
    """Only two complete measured profiles: previous day and previous weekday.

    Does not impute or summarize incomplete intervening days. This explicit reduced schema
    avoids requiring irrelevant intervening-day readings in a 336-step rolling statistic.
    """
    gmt_half_hour(origin)
    if origin.hour or origin.minute:
        raise ValueError("Event forecast requires midnight GMT")
    targets = pd.date_range(origin, periods=48, freq="30min")
    day = series.reindex(targets - pd.Timedelta(days=1)).to_numpy(dtype=float)
    week = series.reindex(targets - pd.Timedelta(days=7)).to_numpy(dtype=float)
    if not np.isfinite(day).all() or not np.isfinite(week).all():
        raise ValueError("Incomplete previous-day or previous-weekday profile; no imputation")
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
            np.full(48, day.mean()),
            np.full(48, day.std()),
            np.full(48, week.mean()),
            np.full(48, week.std()),
        )
    )


def event_examples(
    series: pd.Series, period: DatePeriod
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    x, y, times = [], [], []
    for origin in pd.date_range(period.start, period.end, tz="UTC", freq="D"):
        target = pd.date_range(origin, periods=48, freq="30min")
        values = series.reindex(target).to_numpy(dtype=float)
        if not np.isfinite(values).all():
            continue
        try:
            matrix = event_features(series, origin.to_pydatetime())
        except ValueError:
            continue
        x.append(matrix)
        y.append(values)
        times.extend(target)
    if not x:
        return np.empty((0, len(FEATURES))), np.empty(0), pd.DatetimeIndex([], tz="UTC")
    return np.concatenate(x), np.concatenate(y), pd.DatetimeIndex(times)


def policy_json(policy: EventPolicy) -> dict:
    return asdict(policy)


def midnight(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), UTC)
