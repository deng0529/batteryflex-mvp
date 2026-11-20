"""Reproduce the Task 02D frozen selection from reviewed local snapshots; no network."""

import argparse
import json
import re
from pathlib import Path

from batteryflex.neso import RESOURCES, Sample
from batteryflex.neso_validation import final_recommendations


def build(snapshot_dir: Path, report_path: Path) -> dict:
    samples = [
        Sample(**json.loads((snapshot_dir / f"{rid}.json").read_text(encoding="utf-8")))
        for rid in RESOURCES.values()
    ]
    reviewed = list(
        dict.fromkeys(
            re.findall(r"BF-SCENARIO-\d{8}-[a-f0-9]{10}", report_path.read_text(encoding="utf-8"))
        )
    )
    events = final_recommendations(samples)
    if len(reviewed) != 5 or [g["internal_scenario_id"] for g in events] != reviewed:
        raise ValueError("Selection differs from the five reviewed Task 02D IDs; review required.")
    report = report_path.read_text(encoding="utf-8")
    for event in events:
        if event["source_records_sha256"] not in report:
            raise ValueError("Original records differ from the Task 02D reviewed content hash.")
    resources = []
    for sample in samples:
        ids = {
            i
            for event in events
            if event["resource_id"] == sample.resource_id
            for i in event["source_record_ids"]
        }
        if not ids:
            continue
        resources.append(
            {
                **sample.__dict__,
                "records": [r for r in sample.records if r["_id"] in ids],
                "complete": False,
            }
        )
    return {
        "manifest_version": 1,
        "review": "Task 02D",
        "validated_on": "2026-11-16",
        "validation_report": "docs/NESO_FINAL_VALIDATION.md",
        "attribution": "Supported by National Energy SO Open Data",
        "scope": "Reviewed selection snapshot only; "
        "resource totals describe original full acquisition",
        "resources": resources,
        "events": [{k: v for k, v in e.items() if k != "source_rows"} for e in events],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("docs/NESO_FINAL_VALIDATION.md"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    content = build(args.snapshot_dir, args.report)
    args.output.write_text(
        json.dumps(content, default=str, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
