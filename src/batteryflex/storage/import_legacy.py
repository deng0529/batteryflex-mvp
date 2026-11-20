"""Import existing trusted model/evaluation artifacts without training or reforecasting."""

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from batteryflex.forecast_persistence import load_bundle
from batteryflex.forecast_registry import LocalModelRegistry
from batteryflex.forecast_training import metrics_table
from batteryflex.storage.database import Statement, query
from batteryflex.storage.objects import sha256
from batteryflex.storage.repository import Repository, canonical, now, object_statement


def import_models(repository: Repository, root: Path, dataset_id: str, selection_id: str) -> int:
    store = LocalModelRegistry(root / "outputs/forecast_models")
    registry = store.read()
    count = 0
    for record in registry.records:
        if record.status != "Saved":
            continue
        if record.training_data_sha256 != dataset_id:
            raise ValueError("Legacy model provenance differs from the validated dataset")
        load_bundle(store, record)
        assert record.artifact_location is not None
        ref = repository.objects.put(
            store.artifact_path(record.artifact_location).read_bytes(), "forecast-bundle-v1"
        )
        identity = "legacy-" + sha256(canonical(asdict(record)).encode())
        old = query(
            repository.db,
            "SELECT fingerprint,artifact_id FROM forecast_models WHERE algorithm=? AND version=?",
            (record.config.method, record.reference.model_version),
        )
        if old:
            if old[0]["artifact_id"] != ref.sha256:
                raise ValueError("Existing immutable model version differs")
            continue
        statements: list[Statement] = [
            object_statement(ref),
            (
                "INSERT INTO forecast_configs VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                (
                    identity,
                    dataset_id,
                    selection_id,
                    record.config.feature_version,
                    canonical(asdict(record.config)),
                ),
            ),
            (
                "INSERT INTO forecast_models VALUES(?,?,?,?,?,?,?)",
                (
                    identity,
                    record.config.method,
                    record.reference.model_version,
                    ref.sha256,
                    None,
                    canonical(asdict(record)),
                    now(),
                ),
            ),
        ]
        details = json.loads(record.evaluation_details_json)
        for r in details.get("metrics", []):
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
        if registry.active == record.reference:
            statements.append(
                (
                    "INSERT INTO active_selections VALUES('forecast_model',?) ON "
                    "CONFLICT(name) DO NOTHING",
                    (canonical(asdict(record.reference)),),
                )
            )
        repository.db.batch(statements)
        count += 1
    return count


def import_evaluation_archive(
    repository: Repository, root: Path, dataset_id: str, frame: pd.DataFrame
) -> bool:
    directory = root / "outputs/task05b"
    names = ("metrics.csv", "counts.csv", "predictions.parquet", "source-hashes.json")
    if not all((directory / name).is_file() for name in names):
        return False
    hashes = json.loads((directory / "source-hashes.json").read_text(encoding="utf-8"))
    observed_hash = next(
        (
            value
            for name, value in hashes.items()
            if name.replace("\\", "/") == "data/lcl/prepared/observations.parquet"
        ),
        None,
    )
    if observed_hash != dataset_id:
        raise ValueError("Evaluation archive source reference differs from the active dataset")
    predictions = pd.read_parquet(directory / "predictions.parquet")
    if predictions.duplicated(["household", "partition", "method", "interval_start"]).any():
        raise ValueError("Duplicate archived forecast rows")
    source = (
        frame[frame.quality.eq("valid")]
        .set_index(["household_id", "interval_start_gmt"])
        .average_power_kw
    )
    from batteryflex.portfolio import HOUSEHOLDS

    for row in predictions.to_dict("records"):
        if row["household"] == "Portfolio":
            actual = sum(float(source.loc[(h, row["interval_start"])]) for h in HOUSEHOLDS)
        else:
            actual = float(source.loc[(row["household"], row["interval_start"])])
        if not np.isclose(actual, row["actual"], rtol=1e-12, atol=1e-12):
            raise ValueError("Archived actuals do not match validated measured source")
    measured = pd.read_csv(directory / "metrics.csv")
    recomputed = metrics_table(predictions)
    keys = ["partition", "household", "method"]
    expected = recomputed.sort_values(keys).reset_index(drop=True)
    actual_metrics = measured.sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        expected, actual_metrics, check_dtype=False, rtol=1e-10, atol=1e-12
    )
    refs = {
        name: repository.objects.put((directory / name).read_bytes(), "evaluation-archive")
        for name in names[:3]
    }
    identity = sha256(canonical({name: r.sha256 for name, r in refs.items()}).encode())
    statements = [object_statement(r) for r in refs.values()]
    statements.append(
        (
            "INSERT INTO evaluation_archives VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
            (
                identity,
                dataset_id,
                refs["predictions.parquet"].sha256,
                refs["metrics.csv"].sha256,
                refs["counts.csv"].sha256,
                canonical(
                    {
                        "matched_model_artifacts": False,
                        "actuals_verified": True,
                        "metrics_recomputed": True,
                    }
                ),
            ),
        )
    )
    repository.db.batch(statements)
    return True
