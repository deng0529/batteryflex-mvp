"""Load-or-train forecasting, automatic persistence and explicit model selection."""

import streamlit as st

from batteryflex.forecast_persistence import activate_bundle
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.storage.forecast_cache import ForecastCache, fingerprint
from batteryflex.storage.registry import DatabaseModelRegistry
from batteryflex.ui.forecast_comparison import (
    comparison_conclusion,
    lowest_rmse,
    rmse_rows,
    rmse_spec,
)


def recommended_label(registry, run) -> str | None:
    methods = tuple(c.method for c in run.configs)
    best = lowest_rmse(run.metrics, "validation", "Portfolio", methods)
    if not best:
        return None
    config = next(c for c in run.configs if c.method == best[0])
    wanted = "auto-" + fingerprint(config, run.dataset, run.source_sha256)
    record = next(
        (
            r
            for r in registry.records
            if r.config.method == best[0] and r.reference.model_version == wanted
        ),
        None,
    )
    return f"{record.reference.model_name} / {record.reference.model_version}" if record else None


def render_results(store, registry, reason, frame, audit, configs, dataset):
    st.subheader("A4. Run Forecast Models & Results")
    cache = (
        ForecastCache(store.repository, store.root.parent)
        if isinstance(store, DatabaseModelRegistry)
        else None
    )
    if "forecast_run_result" not in st.session_state and cache and dataset and configs and audit:
        try:
            existing = cache.lookup(configs, dataset, audit["artifacts"]["observations.parquet"])
            if existing is not None:
                st.session_state.forecast_run_result = existing
        except (ValueError, OSError) as exc:
            st.error(f"Stored forecast unavailable: {exc}")
    if st.button(
        "Run Models",
        type="primary",
        key="forecast_run",
        disabled=frame is None or dataset is None or not configs,
    ):
        st.session_state.pop("forecast_run_result", None)
        try:
            if cache is None:
                raise ValueError(
                    "Persistent storage is not bootstrapped. Run the explicit storage "
                    "bootstrap command."
                )
            with st.spinner("Loading existing models or training missing models…"):
                result = cache.run(
                    frame, configs, dataset, audit["artifacts"]["observations.parquet"]
                )
            registry = store.read()
            st.success(
                f"Verified persistent models: {len(cache.reused)} reused; "
                f"{len(cache.trained)} trained."
            )
            st.session_state.forecast_run_result = result
            recommended = recommended_label(registry, result)
            if recommended:
                st.session_state.forecast_activate_version = recommended
        except Exception as exc:
            st.error(f"Forecast run failed; no complete bundle is available: {exc}")
    run = st.session_state.get("forecast_run_result")
    if run is None:
        st.info("No trained forecast available.")
    else:
        # A changed configuration must never relabel or save stale results as a new run.
        requested = tuple(c for c in run.configs if c.method != "Seasonal Naive")
        current = tuple(c for c in configs if c.method != "Seasonal Naive")
        if requested != current or run.dataset != dataset:
            st.warning(
                "Configuration changed. Results below retain their original run settings; "
                "click Run Models to evaluate the new settings."
            )
        # Render the recorded run, never relabel it with unexecuted A2 settings.
        shown = tuple(c.method for c in run.configs)
        test = run.predictions[run.predictions.partition == "testing"]
        dates = sorted(test[test.household == "Portfolio"].interval_start.dt.date.unique())
        if dates:
            selected = st.selectbox("Held-out test day (GMT)", dates, key="forecast_test_day")
            for household in HOUSEHOLDS:
                rows = test[
                    (test.household == household) & (test.interval_start.dt.date == selected)
                ]
                st.markdown(f"**{household} · {selected} · origin 00:00 GMT**")
                wide = rows.pivot(index="interval_start", columns="method", values="prediction")
                wide = wide[[m for m in shown if m in wide]]
                wide.insert(0, "Actual", rows.groupby("interval_start").actual.first())
                st.line_chart(
                    wide,
                    x_label="Interval start (GMT)",
                    y_label="Average demand (kW)",
                    height=250,
                    alt=f"{household} actual and selected 48-step forecasts",
                )
        else:
            st.warning("No common complete five-household test day; household curves unavailable.")
        st.markdown("**Held-out test RMSE**")
        bars = rmse_rows(run.metrics, shown)
        if bars.empty:
            st.info("No held-out test RMSE available.")
        else:
            st.vega_lite_chart(
                bars,
                rmse_spec(shown),
                alt="Full held-out test RMSE by household and algorithm; lower is better",
            )
        st.caption(
            "Full held-out test partition; lower RMSE is better. Algorithms within each "
            "household use the same valid dates. Changing the display day does not change "
            "these scores or retrain models."
        )
        st.write(comparison_conclusion(run.metrics, shown))
        st.markdown("**Active forecasting model**")
        recommended = lowest_rmse(run.metrics, "validation", "Portfolio", shown)
        if recommended:
            st.caption(
                "Recommended from lowest validation portfolio RMSE: "
                + " and ".join(recommended)
                + (" (tie)." if len(recommended) > 1 else ".")
                + " Select any available complete model below without retraining."
            )
        else:
            st.caption(
                "Validation portfolio recommendation unavailable; choose an evaluated algorithm."
            )
        st.caption(
            "Models and forecast results persist automatically after a successful Run Models. "
            "Activation is an explicit selection; each version contains one algorithm for all "
            "five homes."
        )
    if registry is None:
        st.error(reason)
        return
    if not registry.records:
        st.info("No forecast model records.")
    else:
        labels = {
            f"{r.reference.model_name} / {r.reference.model_version}": r for r in registry.records
        }
        if "forecast_activate_version" not in st.session_state:
            result = st.session_state.get("forecast_run_result")
            if result is not None:
                recommended = recommended_label(registry, result)
                if recommended:
                    st.session_state.forecast_activate_version = recommended
        if st.session_state.get("forecast_activate_version") not in labels:
            st.session_state.forecast_activate_version = next(iter(labels))
        chosen = st.selectbox(
            "Saved model to activate", list(labels), key="forecast_activate_version"
        )
        if st.button("Activate Model", key="forecast_activate"):
            try:
                activate_bundle(store, labels[chosen].reference)
                registry = store.read()
                st.success("Saved model activated and verified.")
            except Exception as exc:
                st.error(f"Activation failed: {exc}")
    active, status = store.active_model(registry)
    st.write(
        f"Current active model: {active.reference.model_name} / {active.reference.model_version}"
        if active
        else status
    )
