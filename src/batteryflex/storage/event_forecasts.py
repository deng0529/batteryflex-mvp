"""Immutable event datasets, model bundles and verified exact-request reuse on Task 05C IO."""

import io
import json
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from batteryflex.event_engine import admission, build_event, score_predictions
from batteryflex.event_policy import (
    DEFAULT_POLICY,
    FEATURES,
    SCHEMA,
    EventPolicy,
    event_features,
    midnight,
)
from batteryflex.forecast_contracts import (
    ActiveModelReference,
    ForecastModelConfig,
    ForecastOutput,
    ForecastRequest,
    validate_forecast_batch,
)
from batteryflex.forecast_persistence import _restore, _state
from batteryflex.forecast_training import history, predict
from batteryflex.lcl_analysis import map_day
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.storage.database import query
from batteryflex.storage.objects import sha256
from batteryflex.storage.repository import Repository, canonical, now, object_statement


def publish_history(repo: Repository, directory: Path) -> str:
    repo.require_owner()
    audit = json.loads((directory / "audit.json").read_text(encoding="utf-8"))
    if audit["format"] != "event-history-v1":
        raise ValueError("Unsupported event history schema")
    assets = {name: (directory / name).read_bytes() for name in audit["artifacts"]}
    for name, expected in audit["artifacts"].items():
        if Path(name).name != name or sha256(assets[name]) != expected:
            raise ValueError("Expanded immutable source integrity failed")
    assets["audit.json"] = (directory / "audit.json").read_bytes()
    refs = {name: repo.objects.put(data, "event-history-v1") for name, data in assets.items()}
    identity = refs["observations.parquet"].sha256
    old = query(repo.db, "SELECT id FROM datasets WHERE id=?", (identity,))
    if old:
        for name, ref in refs.items():
            existing = query(
                repo.db,
                "SELECT object_id FROM dataset_assets WHERE dataset_id=? AND name=?",
                (identity, name),
            )
            if not existing or existing[0]["object_id"] != ref.sha256:
                raise ValueError("Cannot overwrite an immutable expanded dataset version")
    statements = [object_statement(ref) for ref in refs.values()]
    statements.append(
        (
            "INSERT INTO datasets VALUES(?,?,?) ON CONFLICT(id) DO NOTHING",
            (identity, canonical(audit), now()),
        )
    )
    statements.extend(
        (
            "INSERT INTO dataset_assets VALUES(?,?,?) ON CONFLICT DO NOTHING",
            (identity, name, ref.sha256),
        )
        for name, ref in refs.items()
    )
    statements.append(
        (
            "INSERT INTO feature_schemas VALUES(?,?) ON CONFLICT(id) DO NOTHING",
            (SCHEMA, canonical(FEATURES)),
        )
    )
    statements.append(
        (
            "INSERT INTO active_selections VALUES('event_dataset',?) ON CONFLICT(name) "
            "DO UPDATE SET value_json=excluded.value_json",
            (canonical(identity),),
        )
    )
    repo.db.batch(statements)
    return identity


def load_history(
    repo: Repository, dataset_id: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    identity = dataset_id or repo.setting("event_dataset")
    rows = query(
        repo.db, "SELECT name,object_id FROM dataset_assets WHERE dataset_id=?", (identity,)
    )
    assets = {r["name"]: repo.get_object(r["object_id"]) for r in rows}
    if not {"audit.json", "observations.parquet", "coverage.csv"} <= set(assets):
        raise ValueError(
            "Event history is not prepared/persisted; run explicit Task 05D preparation"
        )
    audit = json.loads(assets["audit.json"])
    for name, expected in audit["artifacts"].items():
        if name not in assets or sha256(assets[name]) != expected:
            raise ValueError("Event dataset audit mismatch")
    if sha256(assets["observations.parquet"]) != identity:
        raise ValueError("Event dataset identity mismatch")
    return (
        pd.read_parquet(io.BytesIO(assets["observations.parquet"])),
        pd.read_csv(io.BytesIO(assets["coverage.csv"])),
        audit,
    )


def request_identity(dataset_id: str, event: dict, policy: EventPolicy) -> tuple[str, dict]:
    origin = midnight(map_day(event["delivery_date"]))
    payload = dict(
        dataset_id=dataset_id,
        households=HOUSEHOLDS,
        event_id=event["internal_scenario_id"],
        source_hash=event["source_records_sha256"],
        original_date=str(event["delivery_date"]),
        replay_date=str(origin.date()),
        forecast_origin=origin.isoformat(),
        horizon=48,
        feature_schema=SCHEMA,
        features=FEATURES,
        policy=asdict(policy),
        periods={k: asdict(v) for k, v in policy.periods(origin).items()},
    )
    return sha256(canonical(payload).encode()), payload


def normalize_config(config: ForecastModelConfig) -> ForecastModelConfig:
    defaults = {
        "Seasonal Naive": {},
        "Ridge Regression": {"alpha": 1.0},
        "LightGBM": {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "num_leaves": 15,
            "max_depth": -1,
            "random_state": 42,
        },
    }
    params = {**defaults[config.method], **json.loads(config.hyperparameters_json)}
    if config.method == "LightGBM":
        params["random_state"] = 42
    return ForecastModelConfig(config.method, canonical(params))


def config_payload(config: ForecastModelConfig) -> dict:
    config = normalize_config(config)
    return dict(
        method=config.method,
        hyperparameters=json.loads(config.hyperparameters_json),
        horizon_steps=48,
        feature_schema=SCHEMA,
        preprocessing={
            "Ridge Regression": "training-only StandardScaler then Ridge",
            "LightGBM": "numeric features without scaling; fixed seed 42",
            "Seasonal Naive": "previous-day reference; no fitted estimator",
        }[config.method],
        nonnegative_policy="clip_at_zero",
    )


def model_identity(request_id: str, config: ForecastModelConfig) -> str:
    config = normalize_config(config)
    code = {
        name: sha256((Path(__file__).parents[1] / name).read_bytes())
        for name in (
            "event_policy.py",
            "event_engine.py",
            "forecast_training.py",
            "forecast_persistence.py",
        )
    }
    return sha256(
        canonical(
            dict(
                request=request_id,
                config=config_payload(config),
                code=code,
                libraries={
                    name: version(name) for name in ("numpy", "pandas", "scikit-learn", "lightgbm")
                },
                format=1,
            )
        ).encode()
    )


class EventForecasts:
    def __init__(self, repo: Repository):
        self.repo = repo
        self.trained = []
        self.reused = []

    def lookup(
        self,
        event: dict,
        config: ForecastModelConfig,
        policy: EventPolicy = DEFAULT_POLICY,
        dataset_id: str | None = None,
    ):
        config = normalize_config(config)
        dataset_id = dataset_id or self.repo.setting("event_dataset")
        request_id, _ = request_identity(dataset_id, event, policy)
        identity = model_identity(request_id, config)
        rows = query(
            self.repo.db, "SELECT * FROM event_forecast_models WHERE fingerprint=?", (identity,)
        )
        if not rows:
            return None
        row = rows[0]
        artifact = json.loads(self.repo.get_object(row["artifact_id"]))
        if (
            artifact["format"] != "event-model-v1"
            or artifact["fingerprint"] != identity
            or artifact["features"] != list(FEATURES)
            or artifact["feature_schema"] != SCHEMA
            or artifact["request_id"] != request_id
            or artifact["dataset_id"] != dataset_id
            or set(artifact["models"]) != set(HOUSEHOLDS)
            or artifact["config"] != config_payload(config)
            or row["information_cutoff"] != artifact["information_cutoff"]
            or artifact["information_cutoff"]
            != midnight(map_day(event["delivery_date"])).isoformat()
        ):
            raise ValueError("Event model bundle is incompatible")
        models = {h: _restore(state, config.method) for h, state in artifact["models"].items()}
        predictions = pd.read_parquet(io.BytesIO(self.repo.get_object(row["predictions_id"])))
        if (
            set(predictions.method) != {config.method}
            or predictions.duplicated(["partition", "household", "interval_start"]).any()
        ):
            raise ValueError("Incomplete or duplicate saved event forecasts")
        full = predictions[predictions.partition.eq("full_day")]
        if (
            set(full.household) != {*HOUSEHOLDS, "Portfolio"}
            or not full.groupby("household").size().eq(48).all()
        ):
            raise ValueError("Saved event forecast requires all five households and 48 steps")
        origin = midnight(map_day(event["delivery_date"]))
        expected_day = pd.date_range(origin, periods=48, freq="30min")
        expected_window = pd.date_range(
            origin
            + pd.Timedelta(
                hours=int(event["start_uk"][11:13]), minutes=int(event["start_uk"][14:16])
            ),
            periods=int(event["duration_minutes"] // 30),
            freq="30min",
        )
        periods = policy.periods(origin)
        if set(predictions.partition) != {"validation", "holdout", "full_day", "event_window"}:
            raise ValueError("Saved event evaluation scopes are incomplete")
        for key, group in predictions.groupby(["partition", "household"]):
            scope, _household = key if isinstance(key, tuple) else (key, "")
            scope = str(scope)
            index = pd.DatetimeIndex(group.interval_start.sort_values())
            if scope in ("full_day", "event_window"):
                expected = expected_day if scope == "full_day" else expected_window
                if list(index) != list(expected):
                    raise ValueError("Saved day/event intervals do not match the replay request")
            else:
                period = periods[scope]
                if not group.interval_start.dt.date.between(period.start, period.end).all():
                    raise ValueError("Saved evaluation crosses chronological partition boundaries")
                if not group.groupby(group.interval_start.dt.date).size().eq(48).all():
                    raise ValueError("Saved historical holdout has incomplete days")
            if not (group.interval_end - group.interval_start).eq(pd.Timedelta(minutes=30)).all():
                raise ValueError("Saved intervals are not half-hours")
        for scope in ("validation", "holdout", "full_day", "event_window"):
            rows = predictions[predictions.partition.eq(scope)]
            sums = (
                rows[rows.household.isin(HOUSEHOLDS)]
                .groupby("interval_start")
                .prediction.agg(["sum", "count"])
            )
            portfolio = rows[rows.household.eq("Portfolio")].set_index("interval_start").prediction
            expected = sums[sums["count"].eq(5)]["sum"]
            if set(portfolio.index) != set(expected.index) or not np.allclose(
                portfolio.sort_index(), expected.sort_index(), rtol=1e-10, atol=1e-12
            ):
                raise ValueError("Saved portfolio is not the complete five-household forecast sum")
        if not np.isfinite(predictions.prediction).all() or predictions.prediction.lt(0).any():
            raise ValueError("Saved event demand predictions must be finite and nonnegative")
        metrics = score_predictions(predictions)
        evaluation = json.loads(self.repo.get_object(row["evaluation_id"]))
        if (
            evaluation["format"] != "event-evaluation-v1"
            or evaluation["fingerprint"] != identity
            or evaluation["request_id"] != request_id
        ):
            raise ValueError("Saved event evaluation identity mismatch")
        stored_metrics = (
            pd.DataFrame(evaluation["metrics"])
            .sort_values(["scope", "household", "method"])
            .reset_index(drop=True)
        )
        try:
            pd.testing.assert_frame_equal(
                metrics.sort_values(["scope", "household", "method"]).reset_index(drop=True),
                stored_metrics.reindex(columns=metrics.columns),
                check_dtype=False,
                rtol=1e-10,
                atol=1e-12,
            )
        except AssertionError:
            raise ValueError(
                "Saved event evaluation metrics do not match verified predictions"
            ) from None
        recorded = query(
            self.repo.db,
            "SELECT scope,household_id,mae_kw,rmse_kw,observations FROM "
            "event_forecast_metrics WHERE model_id=?",
            (identity,),
        )
        if len(recorded) != len(metrics):
            raise ValueError("Stored event metric completeness mismatch")
        for metric in metrics.to_dict("records"):
            expected = next(
                (
                    r
                    for r in recorded
                    if r["scope"] == metric["scope"] and r["household_id"] == metric["household"]
                ),
                None,
            )
            if (
                not expected
                or expected["observations"] != metric["observations"]
                or not np.allclose(
                    [expected["mae_kw"], expected["rmse_kw"]],
                    [metric["mae_kw"], metric["rmse_kw"]],
                    rtol=1e-10,
                    atol=1e-12,
                )
            ):
                raise ValueError("Stored event metrics do not match predictions")
        return dict(
            record=row, artifact=artifact, models=models, predictions=predictions, metrics=metrics
        )

    def run(
        self,
        event: dict,
        sample,
        configs: tuple[ForecastModelConfig, ...],
        policy: EventPolicy = DEFAULT_POLICY,
    ):
        self.repo.require_owner()
        dataset_id = self.repo.setting("event_dataset")
        request_id, payload = request_identity(dataset_id, event, policy)
        configs = tuple(normalize_config(c) for c in configs)
        if not configs or len({c.method for c in configs}) != len(configs):
            raise ValueError("Select unique event algorithms")
        if not any(c.method == "Seasonal Naive" for c in configs):
            configs = (ForecastModelConfig(), *configs)
        self.trained = []
        self.reused = []
        unavailable = query(
            self.repo.db,
            "SELECT state,reason FROM event_forecast_status WHERE request_id=?",
            (request_id,),
        )
        if unavailable and unavailable[0]["state"] == "unavailable":
            raise ValueError(unavailable[0]["reason"])
        results = []
        for config in configs:
            existing = self.lookup(event, config, policy, dataset_id)
            if existing:
                results.append(existing)
                self.reused.append(config.method)
                continue
            frame, coverage, _ = load_history(self.repo, dataset_id)
            selected = coverage[coverage.scenario_id.eq(event["internal_scenario_id"])]
            coverage_ref = query(
                self.repo.db,
                "SELECT object_id FROM dataset_assets WHERE dataset_id=? AND name='coverage.csv'",
                (dataset_id,),
            )[0]["object_id"]
            statements = [
                (
                    "INSERT INTO event_forecast_requests VALUES(?,?,?,?,?,?,?) ON "
                    "CONFLICT(id) DO NOTHING",
                    (
                        request_id,
                        dataset_id,
                        event["internal_scenario_id"],
                        payload["replay_date"],
                        payload["forecast_origin"],
                        canonical(payload),
                        coverage_ref,
                    ),
                )
            ]
            reason = admission(frame, event, policy)
            feasible = len(selected) == 5 and not reason
            if len(selected) != 5:
                reason = "Coverage audit does not contain all five reviewed households"
            statements.append(
                (
                    "INSERT INTO event_forecast_status VALUES(?,?,?) ON CONFLICT(request_id) "
                    "DO NOTHING",
                    (request_id, "available" if feasible else "unavailable", reason),
                )
            )
            self.repo.db.batch(statements)
            if not feasible:
                raise ValueError(reason)
            identity = model_identity(request_id, config)
            owner = uuid4().hex
            claimed = query(
                self.repo.db,
                "INSERT INTO model_leases VALUES(?,?,?) ON CONFLICT(fingerprint) DO UPDATE "
                "SET owner=excluded.owner,expires_at=excluded.expires_at WHERE "
                "model_leases.expires_at<? RETURNING owner",
                (identity, owner, int(time.time()) + 600, int(time.time())),
            )
            if not claimed:
                raise ValueError("Identical event model is already being computed; retry later")
            try:
                existing = self.lookup(event, config, policy, dataset_id)
                if existing:
                    results.append(existing)
                    self.reused.append(config.method)
                    continue
                models, predictions, metrics, counts = build_event(
                    frame, event, sample, config, policy
                )
                # Event actuals/errors are separate from the fitted model artifact and its cutoff.
                prior = metrics[metrics.scope.isin(["validation", "holdout"])]
                artifact = dict(
                    format="event-model-v1",
                    fingerprint=identity,
                    request_id=request_id,
                    dataset_id=dataset_id,
                    config=config_payload(config),
                    feature_schema=SCHEMA,
                    features=list(FEATURES),
                    request=payload,
                    information_cutoff=payload["forecast_origin"],
                    selection_cutoff=policy.periods(midnight(map_day(event["delivery_date"])))[
                        "validation"
                    ].available_through.isoformat(),
                    created_at=now(),
                    counts=counts,
                    effective_settings={
                        h: (
                            m.get_params()
                            if config.method == "LightGBM"
                            else {
                                "alpha": json.loads(config.hyperparameters_json).get("alpha", 1.0),
                                "scaler": "StandardScaler",
                            }
                            if config.method == "Ridge Regression"
                            else {"lag_steps": 48}
                        )
                        for h, m in models.items()
                    },
                    library_versions={
                        name: version(name)
                        for name in ("numpy", "pandas", "scikit-learn", "lightgbm")
                    },
                    pre_origin_metrics=prior.to_dict("records"),
                    models={h: _state(model, config.method) for h, model in models.items()},
                    nonnegative_policy="clip_at_zero",
                )
                model_ref = self.repo.objects.put(canonical(artifact).encode(), "event-model-v1")
                buffer = io.BytesIO()
                predictions.to_parquet(buffer, index=False)
                prediction_ref = self.repo.objects.put(buffer.getvalue(), "event-evaluation-v1")
                evaluation_ref = self.repo.objects.put(
                    canonical(
                        dict(
                            format="event-evaluation-v1",
                            fingerprint=identity,
                            request_id=request_id,
                            recorded_at=now(),
                            event_actuals_available_through=(
                                midnight(map_day(event["delivery_date"])) + timedelta(days=1)
                            ).isoformat(),
                            metrics=metrics.to_dict("records"),
                        )
                    ).encode(),
                    "event-metrics-v1",
                )
                records = [
                    object_statement(evaluation_ref),
                    object_statement(model_ref),
                    object_statement(prediction_ref),
                    (
                        "INSERT INTO event_forecast_models SELECT ?,?,?,?,?,?,?,?,?,? WHERE EXISTS "
                        "(SELECT 1 FROM model_leases WHERE fingerprint=? AND owner=?)",
                        (
                            identity,
                            request_id,
                            config.method,
                            "event-" + identity,
                            canonical(config_payload(config)),
                            model_ref.sha256,
                            prediction_ref.sha256,
                            evaluation_ref.sha256,
                            payload["forecast_origin"],
                            now(),
                            identity,
                            owner,
                        ),
                    ),
                ]
                for metric in metrics.to_dict("records"):
                    records.append(
                        (
                            "INSERT INTO event_forecast_metrics VALUES(?,?,?,?,?,?)",
                            (
                                identity,
                                metric["scope"],
                                metric["household"],
                                metric["mae_kw"],
                                metric["rmse_kw"],
                                metric["observations"],
                            ),
                        )
                    )
                records.append(
                    ("DELETE FROM model_leases WHERE fingerprint=? AND owner=?", (identity, owner))
                )
                self.repo.db.batch(records)
                existing = self.lookup(event, config, policy, dataset_id)
                if not existing:
                    raise ValueError("Event persistence read-back verification failed")
                results.append(existing)
                self.trained.append(config.method)
            finally:
                self.repo.db.batch(
                    [
                        (
                            "DELETE FROM model_leases WHERE fingerprint=? AND owner=?",
                            (identity, owner),
                        )
                    ]
                )
        return results

    def activate(self, result: dict) -> None:
        row = result["record"]
        registered = query(
            self.repo.db,
            "SELECT request_id,artifact_id FROM event_forecast_models WHERE fingerprint=?",
            (row["fingerprint"],),
        )
        if (
            not registered
            or registered[0]["request_id"] != row["request_id"]
            or registered[0]["artifact_id"] != row["artifact_id"]
        ):
            raise ValueError("Cannot activate a model belonging to another event request")
        self.repo.get_object(row["artifact_id"])
        self.repo.db.batch(
            [
                (
                    "INSERT INTO event_active_models VALUES(?,?) ON CONFLICT(request_id) "
                    "DO UPDATE SET model_id=excluded.model_id",
                    (row["request_id"], row["fingerprint"]),
                )
            ]
        )


class EventForecaster:
    def __init__(self, result: dict, frame: pd.DataFrame):
        self.result = result
        self.frame = frame

    def predict(
        self, *, household_ids: tuple[str, ...], forecast_origin: datetime, horizon_steps: int = 48
    ):
        request = ForecastRequest(household_ids, forecast_origin, horizon_steps)
        artifact = self.result["artifact"]
        cutoff = datetime.fromisoformat(artifact["information_cutoff"])
        if cutoff > forecast_origin:
            raise ValueError("Event model used information later than requested origin")
        if not set(household_ids) <= set(artifact["models"]):
            raise ValueError("Incompatible event household selection")
        reference = ActiveModelReference(
            artifact["config"]["method"], self.result["record"]["version"]
        )
        output = []
        for household in household_ids:
            x = event_features(history(self.frame, household), forecast_origin)
            values = predict(self.result["models"][household], artifact["config"]["method"], x)
            for step, value in enumerate(values, 1):
                start = forecast_origin + timedelta(minutes=30 * (step - 1))
                output.append(
                    ForecastOutput(
                        household,
                        forecast_origin,
                        start,
                        start + timedelta(minutes=30),
                        step,
                        float(value),
                        reference,
                    )
                )
        result = tuple(output)
        validate_forecast_batch(request, result, reference)
        return result
