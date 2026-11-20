"""Read-only diagnostics from pinned event metadata and measured training targets."""

from datetime import date

import numpy as np
import pandas as pd

from batteryflex.event_policy import event_examples
from batteryflex.forecast_contracts import DatePeriod
from batteryflex.forecast_training import history
from batteryflex.portfolio import HOUSEHOLDS

LABELS = dict(training="Training", validation="Validation", holdout="Testing / Holdout")


def training_context(
    frame: pd.DataFrame, artifact: dict
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Recover exact admitted origins, checking counts against the immutable model artifact.

    Main dates are persisted inclusive calendar bounds. Household dates are first/last
    admitted daily origins, which can have gaps. Portfolio thresholds use coincident sums,
    never sums of household quantiles. No validation or final-day target enters a threshold.
    """
    request = artifact["request"]
    origin = pd.Timestamp(request["forecast_origin"])
    members = tuple(request["households"])
    if set(members) != set(HOUSEHOLDS):
        raise ValueError("Peak analysis requires the five saved households")
    rows, detail, thresholds = [], [], {}
    for scope, label in LABELS.items():
        bounds = request["periods"][scope]
        period = DatePeriod(date.fromisoformat(bounds["start"]), date.fromisoformat(bounds["end"]))
        if period.available_through > origin.to_pydatetime():
            raise ValueError("Historical diagnostics cannot include event-day targets")
        targets = {}
        for household in members:
            _, y, index = event_examples(history(frame, household), period)
            days = index.normalize().unique()
            if len(days) != artifact["counts"][household][scope]:
                raise ValueError("Admitted historical samples disagree with the saved model")
            targets[household] = pd.Series(y, index=index, dtype=float)
            detail.append(
                dict(
                    Dataset=label,
                    Household=household,
                    **{
                        "Configured Start": bounds["start"],
                        "Configured End": bounds["end"],
                        "First Usable Date": str(days[0].date()) if len(days) else None,
                        "Last Usable Date": str(days[-1].date()) if len(days) else None,
                        "Usable Days": len(days),
                        "Samples": len(y),
                    },
                )
            )
            if scope == "training":
                thresholds[household] = float(np.quantile(y, 0.9)) if len(y) else np.nan
        common = pd.concat(targets, axis=1, sort=True).dropna()
        portfolio = common.sum(axis=1)
        rows.append(
            dict(
                Dataset=label,
                **{
                    "Start Date": bounds["start"],
                    "End Date": bounds["end"],
                    "Usable Days": len(pd.DatetimeIndex(common.index).normalize().unique()),
                },
            )
        )
        if scope == "training":
            thresholds["Portfolio"] = float(portfolio.quantile(0.9)) if len(portfolio) else np.nan
    rows.append(
        dict(
            Dataset="Event Forecast",
            **{
                "Start Date": str(origin.date()),
                "End Date": str(origin.date()),
                "Usable Days": 1,
            },
        )
    )
    return pd.DataFrame(rows), pd.DataFrame(detail), thresholds


def peak_diagnostics(predictions: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    """Daily max bias, absolute clock-time error, and MAE strictly above training Q90.

    Tied maxima use the earliest interval start. Timing is non-circular at 30-minute
    resolution. Undefined high-demand MAE is NaN with zero samples, never invented zero.
    """
    rows = []
    full = predictions[predictions.partition.eq("full_day")]
    for (household, method), group in full.groupby(["household", "method"]):
        group = group.sort_values("interval_start").reset_index(drop=True)
        times = pd.DatetimeIndex(group.interval_start)
        if (
            len(group) != 48
            or times.has_duplicates
            or len(times.normalize().unique()) != 1
            or not times.equals(pd.date_range(times[0].normalize(), periods=48, freq="30min"))
            or not np.isfinite(group[["actual", "prediction"]].to_numpy()).all()
        ):
            raise ValueError("Peak diagnostics require a complete measured 48-step day")
        actual_i, predicted_i = group.actual.idxmax(), group.prediction.idxmax()
        actual_max, predicted_max = float(group.actual.max()), float(group.prediction.max())
        threshold = thresholds[household]
        high = group[group.actual > threshold] if np.isfinite(threshold) else group.iloc[:0]
        window_times = predictions[
            predictions.partition.eq("event_window")
            & predictions.household.eq(household)
            & predictions.method.eq(method)
        ].interval_start
        event = group[group.interval_start.isin(window_times)]
        rows.append(
            dict(
                household=household,
                method=method,
                actual_peak_kw=actual_max,
                predicted_peak_kw=predicted_max,
                peak_magnitude_error_kw=predicted_max - actual_max,
                actual_peak_time=times[actual_i].isoformat(),
                predicted_peak_time=times[predicted_i].isoformat(),
                peak_timing_error_minutes=abs(
                    (times[predicted_i] - times[actual_i]).total_seconds()
                )
                / 60,
                training_q90_kw=threshold,
                high_demand_intervals=len(high),
                high_demand_mae_kw=float((high.prediction - high.actual).abs().mean()),
                event_underforecast_kwh=float(
                    (event.actual - event.prediction).clip(lower=0).sum() * 0.5
                ),
                event_intervals=len(event),
                actual_peak_in_event=bool(times[actual_i] in set(window_times)),
            )
        )
    return pd.DataFrame(rows)


def peak_summary(diagnostics: pd.DataFrame) -> str:
    """Describe the selected sample without presenting test-day ranking as model selection."""
    parts = []
    for method, group in diagnostics.groupby("method"):
        parts.append(
            f"{method}: {int((group.peak_magnitude_error_kw < 0).sum())}/{len(group)} "
            "daily maxima underestimated; "
            f"mean peak bias {group.peak_magnitude_error_kw.mean():+.3f} kW, "
            f"mean timing error {group.peak_timing_error_minutes.mean():.0f} min"
        )
    return "; ".join(parts) + ". These are post-hoc diagnostics, not model recommendations."
