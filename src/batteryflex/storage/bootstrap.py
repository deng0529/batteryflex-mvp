"""Explicit, idempotent bootstrap from validated project artifacts; no downloads/training."""

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from batteryflex.forecast_contracts import (
    FEATURE_VERSION,
    METHODS,
    ForecastDatasetConfig,
    ForecastModelConfig,
)
from batteryflex.forecast_training import FEATURES
from batteryflex.lcl_analysis import map_day
from batteryflex.neso_manifest import load_selection
from batteryflex.portfolio import HOUSEHOLDS, default_portfolio
from batteryflex.portfolio_storage import export_configuration
from batteryflex.storage.database import Statement, migrate, query
from batteryflex.storage.objects import sha256
from batteryflex.storage.repository import Repository, canonical, now, object_statement


def bootstrap(repository: Repository, root: Path) -> dict:
    prepared = root / "data/lcl/prepared"
    audit_bytes = (prepared / "audit.json").read_bytes()
    audit = json.loads(audit_bytes)
    if audit["parser_version"] != 1:
        raise ValueError("Unsupported prepared schema")
    assets = {"audit.json": audit_bytes}
    for name, expected in audit["artifacts"].items():
        if Path(name).name != name:
            raise ValueError("Unsafe prepared path")
        data = (prepared / name).read_bytes()
        if sha256(data) != expected:
            raise ValueError("Validated prepared source hash mismatch")
        assets[name] = data
    frame = pd.read_parquet(prepared / "observations.parquet")
    if "prepared_rows" in audit and len(frame) != audit["prepared_rows"]:
        raise ValueError("Prepared row count does not match source audit")
    if "sample_ids" in audit and set(frame.household_id) != set(audit["sample_ids"]):
        raise ValueError("Prepared household coverage differs from source audit")
    if (
        "retained_days" in audit
        and "prepared_rows" in audit
        and set(frame.interval_start_gmt.dt.date.astype(str)) != set(audit["retained_days"])
    ):
        raise ValueError("Prepared time coverage differs from source audit")
    if frame.duplicated(["household_id", "interval_start_gmt"]).any():
        raise ValueError("Prepared household timestamps are duplicated")
    from batteryflex.forecast_data import coverage_report, historical_series

    coverage = coverage_report(frame)
    for household in HOUSEHOLDS:
        rows = historical_series(
            frame,
            (household,),
            frame.interval_start_gmt.min().date(),
            frame.interval_start_gmt.max().date(),
        )
        if rows.quality.eq("not_retained").all():
            raise ValueError("Missing reviewed household")
    events, _, manifest = load_selection()
    manifest_data = canonical(manifest).encode()
    # Validate everything above before starting any migration/upload.
    migrate(repository.db)
    refs = {name: repository.objects.put(data, "prepared-lcl") for name, data in assets.items()}
    event_ref = repository.objects.put(manifest_data, "neso-manifest")
    identity = refs["observations.parquet"].sha256
    selection = sha256(canonical(HOUSEHOLDS).encode())
    statements: list[Statement] = [object_statement(ref) for ref in [*refs.values(), event_ref]]
    for household in HOUSEHOLDS:
        statements.append(
            (
                "INSERT INTO households VALUES(?,?) ON CONFLICT(id) DO NOTHING",
                (household, canonical({"area": "London", "observed_year": 2013})),
            )
        )
    statements.append(
        (
            "INSERT INTO household_selections VALUES(?,?) ON CONFLICT(id) DO NOTHING",
            (selection, now()),
        )
    )
    for position, household in enumerate(HOUSEHOLDS):
        statements.append(
            (
                "INSERT INTO selection_members VALUES(?,?,?) ON CONFLICT DO NOTHING",
                (selection, household, position),
            )
        )
    statements.append(
        (
            "INSERT INTO datasets VALUES(?,?,?) ON CONFLICT(id) DO NOTHING",
            (identity, canonical({"audit": audit, "coverage": coverage}), now()),
        )
    )
    for name, ref in refs.items():
        old = query(
            repository.db,
            "SELECT object_id FROM dataset_assets WHERE dataset_id=? AND name=?",
            (identity, name),
        )
        if old and old[0]["object_id"] != ref.sha256:
            raise ValueError(
                "Immutable dataset assets differ; create an explicitly reviewed dataset version"
            )
        statements.append(
            (
                "INSERT INTO dataset_assets VALUES(?,?,?) ON CONFLICT DO NOTHING",
                (identity, name, ref.sha256),
            )
        )
    for event in events:
        event_id = event["internal_scenario_id"]
        old = query(repository.db, "SELECT source_hash FROM neso_events WHERE id=?", (event_id,))
        if old and old[0]["source_hash"] != event["source_records_sha256"]:
            raise ValueError("Historical event identity changed")
        statements.extend(
            [
                (
                    "INSERT INTO neso_events VALUES(?,?,?) ON CONFLICT(id) DO NOTHING",
                    (event_id, event["source_records_sha256"], canonical(event)),
                ),
                (
                    "INSERT INTO replay_mappings VALUES(?,?,?,?) ON CONFLICT(event_id) DO NOTHING",
                    (
                        event_id,
                        str(event["delivery_date"]),
                        str(map_day(event["delivery_date"])),
                        "same-month-weekday-v1",
                    ),
                ),
            ]
        )
    statements.append(
        (
            "INSERT INTO feature_schemas VALUES(?,?) ON CONFLICT(id) DO NOTHING",
            (FEATURE_VERSION, canonical(FEATURES)),
        )
    )
    for name, value in (
        ("dataset", identity),
        ("households", selection),
        ("neso_manifest", event_ref.sha256),
    ):
        statements.append(
            (
                "INSERT INTO active_selections VALUES(?,?) ON CONFLICT(name) DO NOTHING",
                (name, canonical(value)),
            )
        )
    for method in METHODS:
        config = ForecastModelConfig(method)
        payload = canonical({"model": asdict(config), "dataset": asdict(ForecastDatasetConfig())})
        cid = sha256(payload.encode())
        statements.append(
            (
                "INSERT INTO forecast_configs VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                (cid, identity, selection, FEATURE_VERSION, payload),
            )
        )
    repository.db.batch(statements)
    if repository.setting("portfolio") is None:
        repository.save_portfolio(export_configuration(default_portfolio()))
    from batteryflex.storage.import_legacy import import_evaluation_archive, import_models

    imported_models = import_models(repository, root, identity, selection)
    archived = import_evaluation_archive(repository, root, identity, frame)
    result = {
        "households": len(HOUSEHOLDS),
        "events": len(events),
        "prepared_assets": len(refs),
        "dataset_sha256": identity,
        "coverage": coverage,
        "models_imported": imported_models,
        "models_available": len(query(repository.db, "SELECT fingerprint FROM forecast_models")),
        "evaluation_archive_imported": archived,
    }
    return result


def load_prepared(repository: Repository) -> tuple:
    import io

    identity = repository.setting("dataset")
    rows = query(
        repository.db, "SELECT name,object_id FROM dataset_assets WHERE dataset_id=?", (identity,)
    )
    if not rows:
        raise ValueError("Active validated dataset is missing; run explicit bootstrap")
    assets = {r["name"]: repository.get_object(r["object_id"]) for r in rows}
    audit = json.loads(assets["audit.json"])
    if audit["parser_version"] != 1:
        raise ValueError("Unsupported stored dataset schema")
    for name, expected in audit["artifacts"].items():
        if name not in assets or sha256(assets[name]) != expected:
            raise ValueError("Stored prepared dataset failed original audit verification")
    return (
        pd.read_parquet(io.BytesIO(assets["observations.parquet"])),
        pd.read_csv(io.BytesIO(assets["candidates.csv"])),
        pd.read_csv(io.BytesIO(assets["recommended.csv"])),
        pd.read_csv(io.BytesIO(assets["replay.csv"])),
        audit,
    )
