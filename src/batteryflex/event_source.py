"""Validated source preparation for event history; no startup/network side effects."""

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from batteryflex.event_history import combine_sources, coverage_matrix
from batteryflex.lcl import endpoint, parse_observations
from batteryflex.lcl_source import FILES, digest
from batteryflex.portfolio import HOUSEHOLDS


def read_annual(archive: Path) -> pd.DataFrame:
    if digest(archive, "md5") != FILES[archive.name][1]:
        raise ValueError("Annual archive differs from publisher checksum")
    rows = []
    with ZipFile(archive) as zipped:
        members = [m for m in zipped.infolist() if m.filename.endswith(".csv")]
        if len(members) != 1:
            raise ValueError("Unexpected annual archive layout")
        with zipped.open(members[0]) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8"))
            header = next(reader)
            indices = [(header.index(h), h) for h in HOUSEHOLDS]
            for row in reader:
                if len(row) != len(header):
                    raise ValueError("Annual source row width changed")
                rows.extend(
                    dict(household_id=h, source_timestamp=row[0], source_kwh=row[i])
                    for i, h in indices
                )
    frame = parse_observations(rows)
    if frame.duplicated(["household_id", "interval_end_gmt"]).any():
        raise ValueError("Annual source contains duplicate intervals")
    return frame


def read_original(archive: Path, acquisition: dict) -> tuple[pd.DataFrame, dict, list[dict]]:
    if digest(archive) != acquisition["sha256"] or archive.stat().st_size != acquisition["bytes"]:
        raise ValueError("Original archive acquisition hash mismatch")
    pattern = re.compile(
        rb"^(?:" + b"|".join(h.encode() for h in HOUSEHOLDS) + rb"),[^\r\n]*", re.M
    )
    rows = []
    quarantine = []
    members = []
    scanned = 0
    with ZipFile(archive) as zipped:
        for info in zipped.infolist():
            if not info.filename.lower().endswith(".csv"):
                continue
            raw = zipped.read(
                info
            )  # Complete read verifies ZIP CRC even for unselected partitions.
            scanned += 1
            matches = list(pattern.finditer(raw))
            if not matches:
                continue
            header = next(csv.reader([raw.splitlines()[0].decode("utf-8-sig")]))
            members.append(
                dict(
                    name=info.filename,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    crc32=info.CRC,
                    bytes=len(raw),
                )
            )
            for match in matches:
                source = dict(
                    zip(header, next(csv.reader([match.group().decode("utf-8")])), strict=True)
                )
                if source["stdorToU"] != "Std":
                    raise ValueError("Selected household tariff changed")
                row = dict(
                    household_id=source["LCLid"],
                    source_timestamp=source["DateTime"],
                    source_kwh=source["KWH/hh (per half hour) "],
                    source_member=info.filename,
                    source_byte_offset=match.start(),
                    source_tariff=source["stdorToU"],
                )
                try:
                    endpoint(str(row["source_timestamp"]))
                except ValueError:
                    quarantine.append({**row, "reason": "off_grid_timestamp"})
                    continue
                rows.append(row)
    frame = parse_observations(rows)
    quarantine.extend(
        {**row, "reason": "duplicate_key"}
        for row in frame[frame.quality.eq("duplicate")].to_dict("records")
    )
    frame = frame.drop_duplicates(["household_id", "interval_end_gmt"]).reset_index(drop=True)
    return frame, dict(members=members, scanned_csv_members=scanned), quarantine


def prepare_history(root: Path, output: Path) -> dict:
    if output.exists():
        audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
        for name, expected in audit["artifacts"].items():
            if Path(name).name != name or digest(output / name) != expected:
                raise ValueError("Existing immutable event dataset is corrupted")
        return audit
    annual_path = root / "data/lcl/raw/LCL_2013_kWh.csv.zip"
    original_path = root / "data/lcl/task05d-source/PartitionedLCLData.zip"
    acquisition = json.loads(
        (original_path.parent / "acquisition.json").read_text(encoding="utf-8")
    )
    annual = read_annual(annual_path)
    original, source_audit, quarantine = read_original(original_path, acquisition)
    common = annual.merge(
        original, on=["household_id", "interval_end_gmt"], suffixes=("_annual", "_original")
    )
    valid = common[common.quality_annual.eq("valid") & common.quality_original.eq("valid")]
    if not (valid.energy_kwh_annual - valid.energy_kwh_original).abs().le(1e-9).all():
        raise ValueError("Original/annual consumption conflict")
    expanded = combine_sources(annual, original)
    coverage = coverage_matrix(expanded)
    # Stage a new path only, never overwrite any existing Task 05B/05C prepared artifact.
    output.mkdir(parents=True)
    expanded.to_parquet(output / "observations.parquet", index=False)
    coverage.to_csv(output / "coverage.csv", index=False)
    (output / "quarantine.json").write_text(
        json.dumps(quarantine, default=str, indent=2), encoding="utf-8"
    )
    original_summary = []
    for h in HOUSEHOLDS:
        rows = original[original.household_id.eq(h)]
        original_summary.append(
            dict(
                household=h,
                first_start=str(rows.interval_start_gmt.min()),
                last_end=str(rows.interval_end_gmt.max()),
                quality=rows.quality.value_counts().to_dict(),
            )
        )
    audit = dict(
        format="event-history-v1",
        household_ids=list(HOUSEHOLDS),
        rows=len(expanded),
        quality=expanded.quality.value_counts().to_dict(),
        original_coverage=original_summary,
        annual_source_sha256=digest(annual_path),
        original_source=acquisition,
        source_members=source_audit,
        valid_overlap_agreement=len(valid),
        quarantined_rows=len(quarantine),
        merge_policy="unchanged 4TU 2013 rows; only pre-2013 original rows added; no imputation",
        artifacts={p.name: digest(p) for p in output.iterdir()},
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit
