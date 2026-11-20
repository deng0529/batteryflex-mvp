"""Simple event-aligned forecasting workspace; saved results restore without fitting."""

import pandas as pd
import streamlit as st

from batteryflex.defaults import ForecastingDefaults, load_defaults
from batteryflex.event_policy import midnight
from batteryflex.forecast_contracts import ForecastModelConfig
from batteryflex.lcl_analysis import map_day
from batteryflex.peak_analysis import training_context
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.simulation_contracts import snapshot
from batteryflex.storage.event_forecasts import EventForecasts, load_history
from batteryflex.ui.forecast_comparison import rmse_spec
from batteryflex.ui.neso_events import event_label, reviewed_selection


def render_event_development(store) -> None:
    st.subheader("Event-aligned forecast development")
    defaults = load_defaults("forecasting.yaml", ForecastingDefaults)
    repo = getattr(store, "repository", None)
    if repo is None:
        st.info("Event-aligned history requires the explicitly prepared persistent dataset.")
        return
    try:
        events, samples, _ = reviewed_selection()
        event_id = st.selectbox(
            "NESO replay event",
            [e["internal_scenario_id"] for e in events],
            format_func=lambda key: event_label(
                next(e for e in events if e["internal_scenario_id"] == key)
            ),
            key="event_forecast_event",
            persist_state="session",
        )
        event = next(e for e in events if e["internal_scenario_id"] == event_id)
        origin = midnight(map_day(event["delivery_date"]))
        st.write(
            f"Original NESO event: {event['delivery_date']} · {event['start_uk'][11:16]}–"
            f"{event['end_uk'][11:16]} UK time · {event['duration_minutes']} minutes. "
            f"LCL replay: {origin.date()} · forecast origin 00:00 GMT · 48 half-hours."
        )
        st.caption(
            "Historical Live demand reduction. Original dates and the established replay mapping "
            "are unchanged; internal scenario IDs are not official NESO event IDs."
        )
        frame, coverage, _ = load_history(repo)
        selected = coverage[coverage.scenario_id.eq(event_id)]
        feasible = len(selected) == 5 and bool(selected.ridge_feasible.all())
        if not feasible:
            st.warning(
                "Forecast unavailable: insufficient complete pre-origin history. No future "
                "observations or alternate replay dates are substituted."
            )
        service = EventForecasts(repo)
        saved = service.lookup(event, ForecastModelConfig()) if feasible else None
        context = None
        if saved:
            context = analysis_context(
                saved["artifact"]["dataset_id"],
                saved["record"]["fingerprint"],
                frame,
                saved["artifact"],
            )
            display_dates(context)
        else:
            st.info("Exact saved date ranges appear when a verified event model is available.")
        ridge = st.checkbox(
            "Ridge Regression", value=True, key="event_select_ridge", persist_state="session"
        )
        lgb = st.checkbox("LightGBM", value=True, key="event_select_lgb", persist_state="session")
        configs = []
        if ridge:
            alpha = st.number_input(
                "Event Ridge alpha",
                min_value=0.0,
                value=defaults.ridge_alpha,
                key="event_ridge_alpha",
                persist_state="session",
            )
            configs.append(ForecastModelConfig("Ridge Regression", snapshot({"alpha": alpha})))
        if lgb:
            cols = st.columns(3)
            trees = cols[0].number_input(
                "Event trees",
                min_value=1,
                value=defaults.lightgbm_trees,
                key="event_lgb_trees",
                persist_state="session",
            )
            rate = cols[1].number_input(
                "Event learning rate",
                min_value=0.001,
                max_value=1.0,
                value=defaults.lightgbm_learning_rate,
                key="event_lgb_rate",
                persist_state="session",
            )
            leaves = cols[2].number_input(
                "Event leaves",
                min_value=2,
                value=defaults.lightgbm_leaves,
                key="event_lgb_leaves",
                persist_state="session",
            )
            configs.append(
                ForecastModelConfig(
                    "LightGBM",
                    snapshot(dict(n_estimators=trees, learning_rate=rate, num_leaves=leaves)),
                )
            )
        st.caption(
            "Seasonal Naive is retained as a paired reference. Models/results save automatically; "
            "evaluation compares household and five-household portfolio MAE/RMSE in kW."
        )
        requested = (ForecastModelConfig(), *configs)
        results = [service.lookup(event, c) for c in requested] if configs and feasible else []
        status = "Saved forecasting results loaded" if results and all(results) else None
        if st.button(
            "Run Event Models",
            key="event_forecast_run",
            type="primary",
            disabled=not repo.writable or not feasible or not configs,
        ):
            with st.spinner("Loading exact event models or training/persisting missing models…"):
                results = service.run(event, samples[event["resource_id"]], tuple(configs))
            status = (
                "Models trained and saved"
                if service.trained
                else "Saved forecasting results loaded"
            )
        if status:
            st.success(status)
        if not results or any(r is None for r in results):
            st.info(
                "No complete saved event comparison for these settings. "
                + (
                    "Run Event Models to request it."
                    if repo.writable
                    else "Ask the owner to prepare it."
                )
            )
            return
        if context is None:
            context = analysis_context(
                results[0]["artifact"]["dataset_id"],
                results[0]["record"]["fingerprint"],
                frame,
                results[0]["artifact"],
            )
            display_dates(context)
        display_event_results(event, results)
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"Event forecast unavailable: {exc}")


@st.cache_data(max_entries=30, show_spinner=False)
def analysis_context(dataset_id, fingerprint, _frame, _artifact):
    # Immutable dataset/model identities pin the excluded heavy arguments.
    return training_context(_frame, _artifact)


def display_dates(context) -> None:
    dates, _, _ = context
    st.markdown("**Historical dataset dates (GMT)**")
    st.dataframe(
        dates, hide_index=True, alt="Exact saved training validation holdout and event dates"
    )


def full_day_spec(event: dict, origin: pd.Timestamp) -> dict:
    start = origin + pd.Timedelta(
        hours=int(event["start_uk"][11:13]), minutes=int(event["start_uk"][14:16])
    )
    end = start + pd.Timedelta(minutes=event["duration_minutes"])
    return {
        "height": 360,
        "layer": [
            {
                "data": {"values": [{"start": start.isoformat(), "end": end.isoformat()}]},
                "mark": {"type": "rect", "color": "#e8ab36", "opacity": 0.18},
                "encoding": {
                    "x": {"field": "start", "type": "temporal", "scale": {"type": "utc"}},
                    "x2": {"field": "end"},
                },
            },
            {
                "mark": {"type": "line", "clip": True},
                "params": [
                    {
                        "name": "visible_series",
                        "select": {"type": "point", "fields": ["series"]},
                        "bind": "legend",
                    },
                    {
                        "name": "day_zoom",
                        "select": {"type": "interval", "encodings": ["x"]},
                        "bind": "scales",
                    },
                ],
                "encoding": {
                    "x": {
                        "field": "interval_start",
                        "type": "temporal",
                        "scale": {"type": "utc"},
                        "axis": {"format": "%H:%M"},
                        "title": "Interval start (GMT)",
                    },
                    "y": {
                        "field": "average_power_kw",
                        "type": "quantitative",
                        "title": "Average demand (kW)",
                    },
                    "color": {"field": "series", "type": "nominal", "title": "Series"},
                    "opacity": {"condition": {"param": "visible_series", "value": 1}, "value": 0},
                    "tooltip": [
                        {"field": "gmt_label", "title": "Start (GMT)", "type": "nominal"},
                        {"field": "series", "type": "nominal"},
                        {"field": "average_power_kw", "type": "quantitative", "format": ".4f"},
                    ],
                },
            },
        ],
    }


def display_event_results(event: dict, results: list[dict]) -> None:
    predictions = pd.concat([r["predictions"] for r in results], ignore_index=True)
    metrics = pd.concat([r["metrics"] for r in results], ignore_index=True)
    methods = tuple(r["record"]["algorithm"] for r in results)
    household = st.selectbox(
        "Forecast series",
        ["Portfolio", *HOUSEHOLDS],
        key="event_curve_household",
        persist_state="session",
    )
    day = predictions[predictions.partition.eq("full_day") & predictions.household.eq(household)]
    data = day.pivot(index="interval_start", columns="method", values="prediction")
    data = data[[m for m in ("LightGBM", "Ridge Regression", "Seasonal Naive") if m in methods]]
    data.insert(0, "Actual", day.groupby("interval_start").actual.first())
    plot = data.reset_index().melt(
        id_vars="interval_start", var_name="series", value_name="average_power_kw"
    )
    plot["gmt_label"] = plot.interval_start.dt.strftime("%Y-%m-%d %H:%M GMT")
    st.markdown("**Full-Day Forecast**")
    st.vega_lite_chart(
        plot,
        full_day_spec(event, day.interval_start.min()),
        alt="48 half-hour actual and saved model curves with highlighted NESO event window",
    )
    st.caption(
        "Amber shading marks the replayed NESO event window. Click legend labels to select "
        "series; Shift-click selects several, double-click resets. Drag to zoom."
    )
    bars = metrics[metrics.scope.eq("full_day") & metrics.household.isin(HOUSEHOLDS)].copy()
    spec = rmse_spec(methods)
    spec["encoding"]["y"]["title"] = "Full-day RMSE (kW)"
    st.vega_lite_chart(bars, spec, alt="Full-day RMSE by household and saved forecasting method")
    accuracy = metrics[metrics.scope.eq("full_day")][
        ["household", "method", "mae_kw", "rmse_kw", "observations"]
    ].rename(
        columns={
            "household": "Series",
            "method": "Model",
            "mae_kw": "MAE (kW)",
            "rmse_kw": "RMSE (kW)",
            "observations": "Half-hours",
        }
    )
    st.markdown("**Full-day forecast accuracy**")
    st.dataframe(
        accuracy,
        hide_index=True,
        alt="Full-day household and portfolio forecast MAE RMSE and sample counts",
    )
    st.download_button(
        "Download forecast accuracy",
        accuracy.to_csv(index=False),
        file_name="forecast-accuracy.csv",
        mime="text/csv",
    )
