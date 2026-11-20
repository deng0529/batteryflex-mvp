"""Forecast development UI consuming verified persistent or local source data."""

from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from batteryflex.forecast_contracts import (
    METHODS,
    DatePeriod,
    ForecastDatasetConfig,
    ForecastModelConfig,
)
from batteryflex.forecast_data import (
    coverage_report,
    historical_series,
    summarize_series,
    summary_row,
)
from batteryflex.forecast_registry import LocalModelRegistry, ModelRegistry
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.simulation_contracts import snapshot
from batteryflex.storage.registry import DatabaseModelRegistry
from batteryflex.storage.settings import runtime_repository
from batteryflex.ui import lcl_lab

REGISTRY_DIRECTORY = Path(__file__).resolve().parents[3] / "outputs" / "forecast_models"


def read_event_store():
    """Connect event storage without inspecting any legacy activation registry."""
    try:
        repository, _ = runtime_repository()
        if repository is not None:
            return DatabaseModelRegistry(
                repository, repository.objects.cache.parent / "model-cache"
            )
    except (ValueError, OSError) as exc:
        st.error(f"Persistent forecast storage unavailable: {exc}")
    return LocalModelRegistry(REGISTRY_DIRECTORY)


def read_registry():
    store = LocalModelRegistry(REGISTRY_DIRECTORY)
    try:
        repository, _ = runtime_repository()
        if repository is not None:
            store = DatabaseModelRegistry(
                repository, repository.objects.cache.parent / "model-cache"
            )
        registry = store.read()
        active, reason = store.active_model(registry)
        if active is not None:
            from batteryflex.forecast_persistence import load_bundle

            load_bundle(store, active)
        return store, registry, active, reason
    except (ValueError, OSError) as exc:
        return store, None, None, f"Registry unavailable or incompatible: {exc}"


def load_history():
    try:
        repository, _ = runtime_repository()
        if repository is not None:
            from batteryflex.storage.bootstrap import load_prepared

            frame, _, _, _, audit = load_prepared(repository)
            return frame[frame.household_id.isin(HOUSEHOLDS)].copy(), audit
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"Persistent household data unavailable: {exc}")
        return None, None
    manifest = lcl_lab.DATA_DIRECTORY / "audit.json"
    if not manifest.exists():
        st.info("Prepared household data is unavailable. No downloads or training are performed.")
        return None, None
    try:
        frame, _, _, _, audit = lcl_lab.load_prepared(
            str(lcl_lab.DATA_DIRECTORY), manifest.stat().st_mtime_ns
        )
        return frame[frame.household_id.isin(HOUSEHOLDS)].copy(), audit
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Validated LCL data unavailable: {exc}")
        return None, None


def historical_load(frame: pd.DataFrame | None) -> None:
    st.subheader("A1. Historical Load Data")
    st.write(
        "The forecasting target is 30-minute average household electricity demand (kW), "
        "calculated from the original LCL energy measurements (kWh)."
    )
    st.caption(
        "P = E / 0.5 h = 2E. This is interval-average demand, not instantaneous power. "
        "Original interval-END labels and fixed GMT are preserved. Observation dates are "
        "for visual inspection only and do not change training periods."
    )
    if frame is None or frame.empty:
        return
    chosen = st.selectbox(
        "Historical load series",
        [*HOUSEHOLDS, "Aggregated portfolio"],
        key="forecast_household",
        persist_state="session",
    )
    first, last = frame.interval_start_gmt.dt.date.min(), frame.interval_start_gmt.dt.date.max()
    bounds = st.date_input(
        "Inspection observation date range (GMT)",
        value=(first, min(first + timedelta(days=6), last)),
        min_value=first,
        max_value=last,
        key="forecast_observation_dates",
        persist_state="session",
    )
    measure = st.segmented_control(
        "Historical measurement",
        ["Average power (kW)", "Original energy (kWh per interval)"],
        default="Average power (kW)",
        key="forecast_measurement",
        persist_state="session",
    )
    if len(bounds) != 2:
        st.info("Choose both inspection date bounds.")
        return
    ids = HOUSEHOLDS if chosen == "Aggregated portfolio" else (chosen,)
    series = historical_series(frame, ids, bounds[0], bounds[1])
    st.dataframe(
        [summary_row(summarize_series(series, bounds[0], bounds[1]))],
        hide_index=True,
        alt="Selected historical observation-range energy, power and missingness",
    )
    st.caption(
        "Aggregated values require all five aligned valid readings. Unavailable readings "
        "and unretained calendar dates stay missing. Energy totals cover valid observations only."
    )
    valid = series[series.quality == "valid"].copy()
    valid["segment"] = (valid.interval_start_gmt.diff() != pd.Timedelta(minutes=30)).cumsum()
    field = "average_power_kw" if measure == "Average power (kW)" else "energy_kwh"
    if valid.empty:
        st.info("No valid retained observations in the selected range.")
    else:
        st.vega_lite_chart(
            valid,
            {
                "height": 250,
                "mark": {"type": "line", "point": True},
                "params": [
                    {
                        "name": "forecast_history_zoom",
                        "select": {"type": "interval", "encodings": ["x"]},
                        "bind": "scales",
                    }
                ],
                "encoding": {
                    "x": {
                        "field": "interval_start_gmt",
                        "type": "temporal",
                        "scale": {"type": "utc"},
                        "title": "Interval start (GMT)",
                    },
                    "y": {"field": field, "type": "quantitative", "title": measure},
                    "detail": {"field": "segment", "type": "nominal"},
                    "tooltip": [
                        {"field": "interval_start_gmt", "type": "temporal", "title": "Start (GMT)"},
                        {"field": "interval_end_gmt", "type": "temporal", "title": "End (GMT)"},
                        {"field": field, "type": "quantitative", "title": measure},
                    ],
                },
            },
            alt="Measured historical load only, with gaps where observations are unavailable",
        )
    with st.expander("Detailed inspection readings"):
        st.dataframe(
            series,
            hide_index=True,
            alt="Aligned historical energy, average power, GMT intervals and quality",
        )
    with st.expander("Verified retained household coverage"):
        st.dataframe(
            coverage_report(frame),
            hide_index=True,
            alt="Actual per-household processed coverage and longest valid continuous run",
        )
        st.caption(
            "Prepared data retains January–March and two isolated replay dates (7 November, "
            "6 December 2013). It is not a continuous annual dataset. The audited raw annual "
            "archive is separate; this page does not expand or reprocess it."
        )


def model_configuration() -> tuple[ForecastModelConfig, ...]:
    st.subheader("A2. Forecast Model & Mathematics")
    configs = []
    for method in METHODS:
        if not st.checkbox(
            method,
            value=method != "Ridge Regression",
            key=f"select_{method}",
            persist_state="session",
        ):
            continue
        params = {}
        if method == "Seasonal Naive":
            st.latex(r"\hat P_{t+h}=P_{t+h-48}")
            st.caption("Corresponding previous-day measurement, available at the forecast origin.")
        elif method == "Ridge Regression":
            st.latex(r"\hat P=\beta_0+\boldsymbol{\beta}^{T}X")
            params["alpha"] = st.number_input(
                "Ridge L2 alpha",
                min_value=0.0,
                value=1.0,
                key="forecast_ridge_alpha",
                persist_state="session",
            )
            st.caption("Household-specific linear model with StandardScaler and L2 regularisation.")
        else:
            st.latex(r"\hat P=\sum_{m=1}^{M}f_m(X)")
            cols = st.columns(3)
            params["n_estimators"] = cols[0].number_input(
                "Number of trees",
                min_value=1,
                value=200,
                key="forecast_lgb_trees",
                persist_state="session",
            )
            params["learning_rate"] = cols[1].number_input(
                "Learning rate",
                min_value=0.001,
                max_value=1.0,
                value=0.05,
                key="forecast_lgb_rate",
                persist_state="session",
            )
            params["num_leaves"] = cols[2].number_input(
                "Number of leaves",
                min_value=2,
                value=15,
                key="forecast_lgb_leaves",
                persist_state="session",
            )
            st.caption(
                "Household-specific regression trees; seed 42, minimum leaf samples 30, L2 1."
            )
        configs.append(ForecastModelConfig(method, snapshot(params)))
    st.caption(
        "48 half-hour intervals / 24 hours, average kW. Features: target time sine/cosine, "
        "weekday/weekend, horizon step, previous-day/week load, origin-day/week mean/std. "
        "All measured features end at or before midnight GMT origin. Seven complete days "
        "of history required; no imputation. Seasonal Naive is always computed internally "
        "as the comparison reference. Negative model predictions are clipped to zero."
    )
    st.session_state.forecast_model_configs = tuple(configs)
    return tuple(configs)


def training_configuration(frame: pd.DataFrame | None) -> ForecastDatasetConfig | None:
    st.subheader("A3. Training & Evaluation Configuration")
    default = ForecastDatasetConfig()
    periods = {}
    cols = st.columns(3)
    for col, name in zip(cols, ("training", "validation", "testing"), strict=True):
        period = getattr(default, name)
        bounds = col.date_input(
            f"{name.title()} date range",
            value=(period.start, period.end),
            key=f"forecast_{name}_dates",
            persist_state="session",
        )
        if len(bounds) != 2:
            st.info("Choose both bounds for every chronological period.")
            return None
        periods[name] = DatePeriod(*bounds)
    try:
        config = ForecastDatasetConfig(
            periods["training"], periods["validation"], periods["testing"]
        )
    except ValueError as exc:
        st.error(str(exc))
        return None
    st.session_state.forecast_dataset_config = config
    st.write("Horizon: 48 half-hours · Evaluation metrics: MAE (kW), RMSE (kW).")
    st.caption(
        "Chronological evaluation only; no random shuffling. Exclude incomplete forecast-origin "
        "features/targets, with seven-day warm-up and 48-step label boundaries. "
        "Counts below are raw observations, not usable training examples. "
        "Inspection dates above do not alter this split."
    )
    if frame is not None:
        rows = []
        for name, period in periods.items():
            for household in HOUSEHOLDS:
                summary = summarize_series(
                    historical_series(frame, (household,), period.start, period.end),
                    period.start,
                    period.end,
                )
                rows.append(
                    {
                        "Period": name.title(),
                        "Household": household,
                        "Start": str(period.start),
                        "End": str(period.end),
                        "Valid observations": summary.valid_intervals,
                        "Missing/unavailable": summary.missing_intervals,
                        "Not retained": summary.not_retained_intervals,
                    }
                )
        st.dataframe(
            rows,
            hide_index=True,
            alt="Chronological split observation counts and gaps for each household",
        )
        if any(r["Missing/unavailable"] for r in rows):
            st.warning(
                "The split includes missing/unretained intervals. No imputation "
                "is performed; training excludes incomplete origins and targets."
            )
    return config


def development_tab(store: LocalModelRegistry, registry: ModelRegistry | None, reason: str) -> None:
    from batteryflex.ui.event_forecasts import render_event_development

    render_event_development(store)


def benchmark_development_tab(
    store: LocalModelRegistry, registry: ModelRegistry | None, reason: str
) -> None:
    """Preserved legacy UI for isolated regression checks; not exposed in navigation."""
    from batteryflex.ui.forecast_results import render_results

    frame, audit = load_history()
    historical_load(frame)
    configs = model_configuration()
    dataset = training_configuration(frame)
    render_results(store, registry, reason, frame, audit, configs, dataset)
