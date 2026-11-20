"""Run explicitly: python scripts/prepare_lcl.py [--acquire]. Never called by the UI."""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from batteryflex.lcl import inspect_archive
from batteryflex.lcl_analysis import map_day, recommend, replay, statistics
from batteryflex.lcl_source import FILES, acquire, digest
from batteryflex.neso_manifest import load_selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--directory", type=Path, default=Path("data/lcl"))
    args = parser.parse_args()
    raw = args.directory / "raw"
    archive = acquire(raw) if args.acquire else raw / "LCL_2013_kWh.csv.zip"
    if digest(archive, "md5") != FILES[archive.name][1]:
        raise ValueError("Raw archive does not match the publisher's v1 checksum")
    events, _, _ = load_selection()
    days = {date(2013, 1, 1) + timedelta(days=n) for n in range(90)}
    days.update(map_day(e["delivery_date"]) for e in events)
    frame, audit = inspect_archive(archive, days)
    stats = statistics(frame)
    selected = recommend(stats)
    comparison = replay(frame, selected.household_id.tolist())
    output = args.directory / "prepared"
    output.mkdir(parents=True, exist_ok=True)
    for column in ("household_id", "quality"):
        frame[column] = frame[column].astype("category")
    frame.to_parquet(output / "observations.parquet", index=False)
    stats.to_csv(output / "candidates.csv", index=False)
    selected.to_csv(output / "recommended.csv", index=False)
    comparison.to_csv(output / "replay.csv", index=False)
    audit.update(
        {
            "parser_version": 1,
            "archive_sha256": digest(archive),
            "analysis_days": 90,
            "retained_days": sorted(str(d) for d in days),
            "prepared_rows": len(frame),
            "prepared_quality": frame.quality.value_counts().to_dict(),
            "mapping_policy": (
                "v1: same 2013 month + exact weekday; nearest day number, earlier tie"
            ),
            "source": json.loads((raw / "acquisition.json").read_text()),
            "artifacts": {
                p.name: digest(p) for p in output.iterdir() if p.suffix in (".csv", ".parquet")
            },
        }
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(selected.to_string(index=False))
    print(comparison.to_string(index=False))
    print({k: v for k, v in audit.items() if k not in ("household_ids", "sample_ids", "source")})


if __name__ == "__main__":
    main()
