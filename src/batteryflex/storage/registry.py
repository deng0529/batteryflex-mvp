"""Database-backed registry adapter preserving the Task 05B loading contracts."""

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from batteryflex.forecast_contracts import (
    ActiveModelReference,
    DatePeriod,
    ForecastDatasetConfig,
    ForecastMetrics,
    ForecastModelConfig,
    ForecastModelMetadata,
)
from batteryflex.forecast_registry import LocalModelRegistry, ModelRegistry
from batteryflex.storage.database import query
from batteryflex.storage.objects import atomic_write, sha256
from batteryflex.storage.repository import Repository


def decode_record(stored: dict) -> ForecastModelMetadata:
    row = dict(stored)
    row["reference"] = ActiveModelReference(**row["reference"])
    row["config"] = ForecastModelConfig(**row["config"])
    dataset = dict(row["dataset"])
    for name in ("training", "validation", "testing"):
        dataset[name] = DatePeriod(**{k: date.fromisoformat(v) for k, v in dataset[name].items()})
    dataset["household_ids"] = tuple(dataset["household_ids"])
    row["dataset"] = ForecastDatasetConfig(**dataset)
    for name in ("fitted_at", "information_cutoff"):
        row[name] = datetime.fromisoformat(row[name]) if row[name] else None
    for name in ("validation_metrics", "test_metrics"):
        row[name] = ForecastMetrics(**row[name]) if row[name] else None
    return ForecastModelMetadata(**row)


class DatabaseModelRegistry(LocalModelRegistry):
    def __init__(self, repository: Repository, root: Path):
        super().__init__(root)
        self.repository = repository

    def read(self) -> ModelRegistry:
        rows = query(
            self.repository.db,
            "SELECT metadata_json FROM forecast_models ORDER BY created_at,fingerprint",
        )
        active = self.repository.setting("forecast_model")
        return ModelRegistry(
            tuple(decode_record(json.loads(r["metadata_json"])) for r in rows),
            ActiveModelReference(**active) if active else None,
        )

    def artifact_path(self, location: str) -> Path:
        path = super().artifact_path(location)
        rows = query(self.repository.db, "SELECT artifact_id,metadata_json FROM forecast_models")
        matches = [
            r for r in rows if json.loads(r["metadata_json"])["artifact_location"] == location
        ]
        if len(matches) != 1:
            raise ValueError("Model artifact has no unique database reference")
        digest = matches[0]["artifact_id"]
        if not path.exists() or sha256(path.read_bytes()) != digest:
            atomic_write(path, self.repository.get_object(digest))
        return path

    def write(self, registry: ModelRegistry, *, owner_authorized: bool = False) -> None:
        if not owner_authorized:
            raise PermissionError("Activation requires an explicit action")
        if registry.records != self.read().records:
            raise ValueError("Database model registry records are immutable")
        if registry.active is None:
            raise ValueError("Choose an existing model to activate")
        record = next((r for r in registry.records if r.reference == registry.active), None)
        if record is None:
            raise ValueError("Unknown model reference")
        from batteryflex.forecast_persistence import load_bundle

        load_bundle(self, record)
        self.repository.set_active("forecast_model", asdict(registry.active))
