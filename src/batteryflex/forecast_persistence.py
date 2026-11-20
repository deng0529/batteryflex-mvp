"""Safe JSON/native-text bundles: no pickle, imports or executable artifact payloads."""

import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import wraps
from importlib.metadata import version as package_version
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from batteryflex.forecast_contracts import (
    ActiveModelReference,
    ForecastMetrics,
    ForecastModelMetadata,
    ForecastOutput,
    ForecastRequest,
    validate_forecast_batch,
    validate_model_for_request,
)
from batteryflex.forecast_registry import LocalModelRegistry
from batteryflex.forecast_training import FEATURES, ModelRun, features, history, predict


@contextmanager
def _write_lock(store: LocalModelRegistry):
    store.root.mkdir(parents=True, exist_ok=True)
    lock = store.root / ".writer.lock"
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError("Another registry write is in progress; retry after it finishes") from exc
    try:
        with handle:
            yield
    finally:
        lock.unlink(missing_ok=True)


def _serialized_write(function):
    @wraps(function)
    def wrapped(store, *args, **kwargs):
        with _write_lock(store):
            return function(store, *args, **kwargs)

    return wrapped


def _dump(value: Any) -> bytes:
    return json.dumps(value, allow_nan=False, sort_keys=True).encode("utf-8")


def _state(model: Any, method: str) -> dict:
    if method == "Seasonal Naive":
        return {"kind": "seasonal-naive"}
    if method == "Ridge Regression":
        scaler, ridge = model.steps[0][1], model.steps[1][1]
        return dict(
            kind="ridge",
            mean=scaler.mean_.tolist(),
            scale=scaler.scale_.tolist(),
            coef=ridge.coef_.tolist(),
            intercept=float(ridge.intercept_),
        )
    return dict(kind="lightgbm", text=model.booster_.model_to_string())


def _restore(state: dict, method: str) -> Any:
    if method == "Seasonal Naive" and state == {"kind": "seasonal-naive"}:
        return None
    if method == "Ridge Regression" and state.get("kind") == "ridge":
        for name in ("mean", "scale", "coef"):
            values = np.asarray(state[name], dtype=float)
            if values.shape != (len(FEATURES),) or not np.isfinite(values).all():
                raise ValueError("Invalid Ridge arrays")
        if not np.all(np.array(state["scale"]) > 0) or not np.isfinite(state["intercept"]):
            raise ValueError("Invalid Ridge preprocessing")
        return state
    if method == "LightGBM" and state.get("kind") == "lightgbm":
        from lightgbm import Booster

        model = Booster(model_str=state["text"])
        if model.num_feature() != len(FEATURES):
            raise ValueError("Incompatible LightGBM features")
        return model
    raise ValueError("Artifact algorithm/state mismatch")


def load_bundle(store: LocalModelRegistry, record: ForecastModelMetadata) -> dict[str, Any]:
    if record.status != "Saved" or not record.artifact_location:
        raise ValueError("Only saved bundles may be loaded")
    try:
        envelope = json.loads(
            store.artifact_path(record.artifact_location).read_text(encoding="utf-8")
        )
        payload = envelope["payload"]
        if hashlib.sha256(_dump(payload)).hexdigest() != envelope["sha256"]:
            raise ValueError("Artifact checksum mismatch")
        if (
            payload["format"] != 1
            or payload["features"] != list(FEATURES)
            or payload["feature_version"] != record.config.feature_version
            or payload["method"] != record.config.method
            or payload["version"] != record.reference.model_version
            or payload["source_sha256"] != record.training_data_sha256
            or payload["config"] != record.config.hyperparameters_json
            or set(payload["models"]) != set(record.dataset.household_ids)
        ):
            raise ValueError("Incompatible bundle identity, schema or household completeness")
        return {h: _restore(state, record.config.method) for h, state in payload["models"].items()}
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Missing or invalid bundle artifact: {exc}") from exc


@_serialized_write
def save_bundle(
    store: LocalModelRegistry, run: ModelRun, method: str, version: str
) -> ForecastModelMetadata:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", version):
        raise ValueError("Version must contain 1–80 letters, digits, dots, underscores or hyphens")
    config = next((c for c in run.configs if c.method == method), None)
    if config is None or set(run.models[method]) != set(run.dataset.household_ids):
        raise ValueError("Cannot save an incomplete method bundle")
    reference = ActiveModelReference(method, version)
    registry = store.read()
    if any(r.reference == reference for r in registry.records):
        raise ValueError("Immutable model version already exists")
    metrics = run.metrics[run.metrics.method == method]

    def portfolio(p: str) -> ForecastMetrics:
        r = metrics[(metrics.partition == p) & (metrics.household == "Portfolio")].iloc[0]
        return ForecastMetrics(float(r.mae_kw), float(r.rmse_kw))

    payload = dict(
        format=1,
        method=method,
        version=version,
        features=list(FEATURES),
        feature_version=config.feature_version,
        source_sha256=run.source_sha256,
        config=config.hyperparameters_json,
        counts=run.counts.to_dict("records"),
        metrics=metrics.astype(object).where(pd.notna(metrics), None).to_dict("records"),
        models={h: _state(m, method) for h, m in run.models[method].items()},
        effective_settings={
            h: m.get_params()
            if m is not None and method == "LightGBM"
            else {
                "scaling": "StandardScaler",
                "alpha": json.loads(config.hyperparameters_json).get("alpha", 1.0),
            }
            if method == "Ridge Regression"
            else {"lag_steps": 48}
            for h, m in run.models[method].items()
        },
        nonnegative_policy="clip_at_zero",
        library_versions={
            name: package_version(name) for name in ("numpy", "pandas", "scikit-learn", "lightgbm")
        },
    )
    location = f"{uuid4().hex}.json"
    record = ForecastModelMetadata(
        reference,
        config,
        run.dataset,
        "Saved",
        run.source_sha256,
        datetime.now(UTC),
        run.dataset.testing.available_through,
        portfolio("validation"),
        portfolio("testing"),
        location,
        _dump(
            {
                "metrics": payload["metrics"],
                "counts": payload["counts"],
                "features": list(FEATURES),
                "effective_settings": payload["effective_settings"],
                "library_versions": payload["library_versions"],
                "source": {
                    "prepared_observations_sha256": run.source_sha256,
                    "target": "average_power_kw=energy_kwh/0.5",
                    "timezone": "GMT",
                },
                "nonnegative_policy": "clip_at_zero",
            }
        ).decode("utf-8"),
    )
    path = store.artifact_path(location)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(
                _dump(dict(payload=payload, sha256=hashlib.sha256(_dump(payload)).hexdigest()))
            )
        load_bundle(store, record)  # verify all five estimators BEFORE publishing metadata
        store.write(registry.add(record), owner_authorized=True)
        if record not in store.read().records:
            raise ValueError("Registry persistence verification failed")
    except Exception:
        # An unreferenced artifact cannot become active; never delete published artifacts.
        if not any(r.reference == reference for r in store.read().records):
            path.unlink(missing_ok=True)
        raise
    return record


@_serialized_write
def activate_bundle(store: LocalModelRegistry, reference: ActiveModelReference) -> None:
    registry = store.read()
    record = next((r for r in registry.records if r.reference == reference), None)
    if record is None:
        raise ValueError("Unknown saved version")
    load_bundle(store, record)
    store.write(replace(registry, active=reference), owner_authorized=True)
    if store.read().active != reference:
        raise ValueError("Activation persistence verification failed")


class SavedForecaster:
    def __init__(
        self,
        store: LocalModelRegistry,
        frame: pd.DataFrame,
        source_sha256: str,
        reference: ActiveModelReference | None = None,
    ):
        registry = store.read()
        reference = reference or registry.active
        self.record = next((r for r in registry.records if r.reference == reference), None)
        if self.record is None:
            raise ValueError("No saved active forecasting model")
        if source_sha256 != self.record.training_data_sha256:
            raise ValueError("Historical data provenance hash does not match saved model")
        self.models = load_bundle(store, self.record)
        self.frame = frame

    def predict(
        self, *, household_ids: tuple[str, ...], forecast_origin: datetime, horizon_steps: int = 48
    ) -> tuple[ForecastOutput, ...]:
        assert self.record is not None
        request = ForecastRequest(household_ids, forecast_origin, horizon_steps)
        validate_model_for_request(self.record, request)
        outputs = []
        for household in household_ids:
            x = features(history(self.frame, household), forecast_origin)
            values = predict(self.models[household], self.record.config.method, x)
            for k, value in enumerate(values):
                start = forecast_origin + timedelta(minutes=30 * k)
                outputs.append(
                    ForecastOutput(
                        household,
                        forecast_origin,
                        start,
                        start + timedelta(minutes=30),
                        k + 1,
                        float(value),
                        self.record.reference,
                    )
                )
        result = tuple(outputs)
        validate_forecast_batch(request, result, self.record.reference)
        return result
