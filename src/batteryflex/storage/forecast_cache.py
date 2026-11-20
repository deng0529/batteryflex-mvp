"""Load exact verified forecasts or train/persist missing methods on explicit Run Models."""

import io
import json
import tempfile
import time
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from batteryflex.forecast_contracts import ForecastDatasetConfig, ForecastModelConfig
from batteryflex.forecast_persistence import load_bundle, save_bundle
from batteryflex.forecast_registry import LocalModelRegistry
from batteryflex.forecast_training import ModelRun, metric, metrics_table, run_models
from batteryflex.storage.database import Statement, query
from batteryflex.storage.objects import sha256
from batteryflex.storage.registry import DatabaseModelRegistry, decode_record
from batteryflex.storage.repository import Repository, canonical, now, object_statement


def fingerprint(
    config: ForecastModelConfig, dataset: ForecastDatasetConfig, source_hash: str
) -> str:
    # A UI edit, event selection or battery setting does not change forecasting inputs.
    code = {
        name: sha256((Path(__file__).parents[1] / name).read_bytes())
        for name in (
            "forecast_training.py",
            "forecast_data.py",
            "forecast_contracts.py",
            "forecast_persistence.py",
        )
    }
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
    payload = dict(
        dataset=asdict(dataset),
        source_hash=source_hash,
        method=config.method,
        parameters=params,
        feature_version=config.feature_version,
        horizon=config.horizon_steps,
        cache_format=1,
        code=code,
        libraries={n: version(n) for n in ("numpy", "pandas", "scikit-learn", "lightgbm")},
    )
    return sha256(canonical(payload).encode())


def _parquet(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


class ForecastCache:
    def __init__(self, repository: Repository, directory: Path):
        self.repository = repository
        self.registry = DatabaseModelRegistry(repository, directory / "model-cache")
        self.reused: list[str] = []
        self.trained: list[str] = []

    def _load(
        self,
        identity: str,
        config: ForecastModelConfig,
        dataset: ForecastDatasetConfig,
        source_hash: str,
    ) -> ModelRun | None:
        rows = query(
            self.repository.db, "SELECT * FROM forecast_models WHERE fingerprint=?", (identity,)
        )
        if not rows:
            return None
        row = rows[0]
        if row["predictions_id"] is None:
            return None  # Legacy fit without exact evaluation series is not an exact cache hit.
        metadata = decode_record(json.loads(row["metadata_json"]))
        if (
            metadata.config.method != config.method
            or metadata.dataset != dataset
            or metadata.training_data_sha256 != source_hash
        ):
            raise ValueError("Cached model input identity mismatch")
        models = load_bundle(self.registry, metadata)
        predictions = pd.read_parquet(io.BytesIO(self.repository.get_object(row["predictions_id"])))
        if (
            set(predictions.method) != {config.method}
            or not np.isfinite(predictions[["actual", "prediction"]].to_numpy()).all()
        ):
            raise ValueError("Cached predictions are invalid")
        if (
            not isinstance(predictions.interval_start.dtype, pd.DatetimeTZDtype)
            or str(predictions.interval_start.dt.tz) != "UTC"
            or predictions.actual.lt(0).any()
        ):
            raise ValueError("Cached evaluation requires nonnegative GMT-aligned observations")
        details = json.loads(metadata.evaluation_details_json)
        metrics = pd.DataFrame(details["metrics"])
        counts = pd.DataFrame(details["counts"])
        required = {
            (p, h) for p in ("validation", "testing") for h in (*dataset.household_ids, "Portfolio")
        }
        actual = set()
        if predictions.duplicated(["partition", "household", "interval_start"]).any() or (
            predictions.prediction.lt(0).any()
        ):
            raise ValueError("Cached evaluation has duplicate or negative predictions")
        for key, group in predictions.groupby(["partition", "household"]):
            partition, household = key if isinstance(key, tuple) else (key, "")
            actual.add((partition, household))
            period = dataset.validation if partition == "validation" else dataset.testing
            if (
                not group.interval_start.dt.date.between(period.start, period.end).all()
                or not group.groupby(group.interval_start.dt.date).size().eq(48).all()
            ):
                raise ValueError("Cached evaluation has incomplete day-ahead windows")
            for _, day in group.groupby(group.interval_start.dt.date):
                expected = pd.date_range(
                    day.interval_start.min().normalize(), periods=48, freq="30min"
                )
                if list(day.interval_start.sort_values()) != list(expected):
                    raise ValueError("Cached evaluation is not aligned to midnight GMT")
            stored = metrics[metrics.partition.eq(partition) & metrics.household.eq(household)]
            mae, rmse = metric(group.actual.to_numpy(), group.prediction.to_numpy())
            if (
                len(stored) != 1
                or int(stored.iloc[0].observations) != len(group)
                or not np.allclose(
                    [mae, rmse],
                    [stored.iloc[0].mae_kw, stored.iloc[0].rmse_kw],
                    rtol=1e-10,
                    atol=1e-12,
                )
            ):
                raise ValueError("Cached evaluation metrics do not match stored predictions")
        if actual != required:
            raise ValueError("Cached evaluation is missing households or partitions")
        return ModelRun(
            dataset, (config,), {config.method: models}, predictions, metrics, counts, source_hash
        )

    def _publish(
        self, identity: str, run: ModelRun, config: ForecastModelConfig, owner: str
    ) -> None:
        method = config.method
        with tempfile.TemporaryDirectory() as directory:
            store = LocalModelRegistry(Path(directory))
            metadata = save_bundle(store, run, method, f"auto-{identity}")
            artifact = store.artifact_path(metadata.artifact_location).read_bytes()
        model_ref = self.repository.objects.put(artifact, "forecast-bundle-v1")
        predictions = run.predictions[run.predictions.method.eq(method)]
        prediction_ref = self.repository.objects.put(
            _parquet(predictions), "forecast-evaluation-v1"
        )
        self.repository.objects.get(model_ref)
        self.repository.objects.get(prediction_ref)
        selection_id = sha256(canonical(run.dataset.household_ids).encode())
        config_payload = canonical({"config": asdict(config), "dataset": asdict(run.dataset)})
        statements: list[Statement] = [
            object_statement(model_ref),
            object_statement(prediction_ref),
            (
                "INSERT INTO household_selections VALUES(?,?) ON CONFLICT(id) DO NOTHING",
                (selection_id, now()),
            ),
            (
                "INSERT INTO forecast_configs VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                (identity, run.source_sha256, selection_id, config.feature_version, config_payload),
            ),
            (
                "INSERT INTO forecast_models SELECT ?,?,?,?,?,?,? WHERE EXISTS "
                "(SELECT 1 FROM model_leases WHERE fingerprint=? AND owner=?)",
                (
                    identity,
                    method,
                    metadata.reference.model_version,
                    model_ref.sha256,
                    prediction_ref.sha256,
                    canonical(asdict(metadata)),
                    now(),
                    identity,
                    owner,
                ),
            ),
        ]
        for position, household in enumerate(run.dataset.household_ids):
            statements.insert(
                -1,
                (
                    "INSERT INTO selection_members VALUES(?,?,?) ON CONFLICT DO NOTHING",
                    (selection_id, household, position),
                ),
            )
        for r in run.metrics[run.metrics.method.eq(method)].to_dict("records"):
            statements.append(
                (
                    "INSERT INTO forecast_metrics VALUES(?,?,?,?,?,?)",
                    (
                        identity,
                        r["partition"],
                        r["household"],
                        r["mae_kw"],
                        r["rmse_kw"],
                        r["observations"],
                    ),
                )
            )
        statements.append(
            ("DELETE FROM model_leases WHERE fingerprint=? AND owner=?", (identity, owner))
        )
        self.repository.db.batch(statements)
        if not query(
            self.repository.db,
            "SELECT fingerprint FROM forecast_models WHERE fingerprint=?",
            (identity,),
        ):
            raise ValueError("Model registry persistence verification failed")

    def lookup(
        self,
        configs: tuple[ForecastModelConfig, ...],
        dataset: ForecastDatasetConfig,
        source_hash: str,
    ) -> ModelRun | None:
        if not configs:
            return None
        if not any(c.method == "Seasonal Naive" for c in configs):
            configs = (ForecastModelConfig(), *configs)
        runs = []
        for config in configs:
            run = self._load(
                fingerprint(config, dataset, source_hash), config, dataset, source_hash
            )
            if run is None:
                return None
            runs.append(run)
        return self._combine(runs, configs, dataset, source_hash)

    @staticmethod
    def _combine(
        runs: list[ModelRun],
        configs: tuple[ForecastModelConfig, ...],
        dataset: ForecastDatasetConfig,
        source_hash: str,
    ) -> ModelRun:
        predictions = pd.concat([r.predictions for r in runs], ignore_index=True)
        return ModelRun(
            dataset,
            configs,
            {m: models for r in runs for m, models in r.models.items()},
            predictions,
            metrics_table(predictions),
            runs[0].counts,
            source_hash,
        )

    def run(
        self,
        frame: pd.DataFrame,
        configs: tuple[ForecastModelConfig, ...],
        dataset: ForecastDatasetConfig,
        source_hash: str,
    ) -> ModelRun:
        if not configs:
            raise ValueError("Select at least one forecasting algorithm")
        if not any(c.method == "Seasonal Naive" for c in configs):
            configs = (ForecastModelConfig(), *configs)
        if len({c.method for c in configs}) != len(configs):
            raise ValueError("Duplicate forecasting algorithms")
        self.repository.require_owner()
        if not query(self.repository.db, "SELECT id FROM datasets WHERE id=?", (source_hash,)):
            raise ValueError("Forecast dataset is not registered; run validated bootstrap")
        self.reused, self.trained = [], []
        runs = []
        for config in configs:
            identity = fingerprint(config, dataset, source_hash)
            cached = self._load(identity, config, dataset, source_hash)
            if cached is not None:
                runs.append(cached)
                self.reused.append(config.method)
                continue
            owner = uuid4().hex
            claimed = query(
                self.repository.db,
                "INSERT INTO model_leases VALUES(?,?,?) ON CONFLICT(fingerprint) DO UPDATE "
                "SET owner=excluded.owner,expires_at=excluded.expires_at WHERE "
                "model_leases.expires_at<? RETURNING owner",
                (identity, owner, int(time.time()) + 600, int(time.time())),
            )
            if not claimed or claimed[0]["owner"] != owner:
                raise ValueError(
                    "This model is already being computed; retry Run Models after it completes"
                )
            try:
                cached = self._load(identity, config, dataset, source_hash)
                if cached is None:
                    trained = run_models(frame, (config,), dataset, source_hash)
                    self._publish(identity, trained, config, owner)
                    cached = self._load(identity, config, dataset, source_hash)
                    if cached is None:
                        raise ValueError("Persisted forecast could not be reloaded")
                    self.trained.append(config.method)
                else:
                    self.reused.append(config.method)
                runs.append(cached)
            finally:
                self.repository.db.batch(
                    [
                        (
                            "DELETE FROM model_leases WHERE fingerprint=? AND owner=?",
                            (identity, owner),
                        )
                    ]
                )
        return self._combine(runs, configs, dataset, source_hash)
