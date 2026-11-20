"""Load the reviewed selection snapshot; no acquisition, reranking or duplicate validation."""

import hashlib
import json
from datetime import date
from importlib.resources import files

from batteryflex.neso import Sample


def load_selection() -> tuple[list[dict], dict[str, Sample], dict]:
    manifest = json.loads(
        files("batteryflex")
        .joinpath("resources/neso_selection_v1.json")
        .read_text(encoding="utf-8")
    )
    if manifest["manifest_version"] != 1 or len(manifest["events"]) != 5:
        raise ValueError("Unsupported or incomplete reviewed NESO selection manifest.")
    samples = {entry["resource_id"]: Sample(**entry) for entry in manifest["resources"]}
    events = []
    for stored in manifest["events"]:
        event = dict(stored)
        sample = samples[event["resource_id"]]
        lookup = {r["_id"]: i for i, r in enumerate(sample.records)}
        event["source_rows"] = [lookup[rid] for rid in event["source_record_ids"]]
        raw = [sample.records[i] for i in event["source_rows"]]
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        if digest != event["source_records_sha256"] or event["validation_status"] != "PASS":
            raise ValueError("Reviewed NESO selection integrity check failed.")
        event["delivery_date"] = date.fromisoformat(event["delivery_date"])
        events.append(event)
    return events, samples, manifest
