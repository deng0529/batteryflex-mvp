"""Local JSON metadata and explicit active reference, separate from model artifact files.

UI reads only. Future owner tools can explicitly persist metadata atomically. No artifact
is deserialized, trained, downloaded or fabricated by this foundation.
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
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


@dataclass(frozen=True)
class ModelRegistry:
    records: tuple[ForecastModelMetadata, ...] = ()
    active: ActiveModelReference | None = None

    def __post_init__(self) -> None:
        refs = [r.reference for r in self.records]
        if len(refs) != len(set(refs)):
            raise ValueError("Model name/version must be unique; no silent overwrites")
        if self.active is not None and not any(
            r.reference == self.active and r.status == "Saved" for r in self.records
        ):
            raise ValueError("Active reference must identify a saved evaluated model record")

    def add(self, record: ForecastModelMetadata) -> "ModelRegistry":
        return replace(self, records=(*self.records, record))


def _encode(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Unsupported registry value: {type(value)}")


class LocalModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.metadata_path = root / "registry.json"
        self.artifacts = root / "artifacts"

    def artifact_path(self, location: str) -> Path:
        path = (self.artifacts / location).resolve()
        if Path(location).is_absolute() or not path.is_relative_to(self.artifacts.resolve()):
            raise ValueError("Model artifact location must remain inside the artifact directory")
        return path

    def read(self) -> ModelRegistry:
        if not self.metadata_path.exists():
            return ModelRegistry()  # no mkdir, migration or startup write
        try:
            data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            if (
                set(data) != {"schema_version", "records", "active"}
                or type(data["schema_version"]) is not int
                or data["schema_version"] != 1
            ):
                raise ValueError("Unsupported registry schema")
            records = []
            for stored in data["records"]:
                row = dict(stored)
                row["reference"] = ActiveModelReference(**row["reference"])
                row["config"] = ForecastModelConfig(**row["config"])
                dataset = dict(row["dataset"])
                for name in ("training", "validation", "testing"):
                    dataset[name] = DatePeriod(
                        **{k: date.fromisoformat(v) for k, v in dataset[name].items()}
                    )
                dataset["household_ids"] = tuple(dataset["household_ids"])
                row["dataset"] = ForecastDatasetConfig(**dataset)
                for name in ("fitted_at", "information_cutoff"):
                    row[name] = datetime.fromisoformat(row[name]) if row[name] else None
                for name in ("validation_metrics", "test_metrics"):
                    row[name] = ForecastMetrics(**row[name]) if row[name] is not None else None
                record = ForecastModelMetadata(**row)
                if record.artifact_location:
                    self.artifact_path(record.artifact_location)
                records.append(record)
            active = ActiveModelReference(**data["active"]) if data["active"] is not None else None
            return ModelRegistry(tuple(records), active)
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError(f"Invalid registry metadata: {exc}") from exc

    def write(self, registry: ModelRegistry, *, owner_authorized: bool = False) -> None:
        if not owner_authorized:
            raise PermissionError(
                "Only an explicitly authorized local-owner operation may write registry metadata"
            )
        for row in registry.records:
            if row.artifact_location:
                self.artifact_path(row.artifact_location)
        payload = json.dumps(
            {
                "schema_version": 1,
                "records": [asdict(r) for r in registry.records],
                "active": asdict(registry.active) if registry.active else None,
            },
            default=_encode,
            allow_nan=False,
            indent=2,
        )
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.root, delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
            os.replace(temporary, self.metadata_path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def activate(self, registry: ModelRegistry, reference: ActiveModelReference) -> ModelRegistry:
        candidate = replace(registry, active=reference)
        model, reason = self.active_model(candidate)
        if model is None:
            raise ValueError(reason)
        return candidate  # explicit metadata write is a separate owner operation

    def active_model(self, registry: ModelRegistry) -> tuple[ForecastModelMetadata | None, str]:
        if registry.active is None:
            return None, "No active forecasting model"
        record = next(r for r in registry.records if r.reference == registry.active)
        if (
            record.artifact_location is None
            or not self.artifact_path(record.artifact_location).is_file()
        ):
            return None, "Active model unavailable: its artifact is missing"
        return record, "Active"

    def status(self, registry: ModelRegistry, record: ForecastModelMetadata) -> str:
        if record.status == "Saved":
            if (
                record.artifact_location is None
                or not self.artifact_path(record.artifact_location).is_file()
            ):
                return "Unavailable"
            if registry.active == record.reference:
                return "Active"
        return record.status
