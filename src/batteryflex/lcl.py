"""Streaming source audit and lossless selected-household parsing; fixed GMT endpoints."""

import csv
import hashlib
import io
import math
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


def sample_ids(ids: list[str], count: int = 100, seed: str = "batteryflex-lcl-v1") -> list[str]:
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"MAC\d{6}", h) for h in ids):
        raise ValueError("Invalid or duplicate household identifiers")
    return sorted(ids, key=lambda h: hashlib.sha256(f"{seed}:{h}".encode()).hexdigest())[:count]


def endpoint(text: str) -> datetime:
    """Keep original text separately; reject nonzero subsecond or off-grid labels."""
    if not re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.0+)?", text):
        raise ValueError(f"Invalid source timestamp: {text}")
    value = datetime.fromisoformat(text).replace(tzinfo=UTC)
    if value.second or value.minute not in (0, 30):
        raise ValueError(f"Off-grid endpoint: {text}")
    return value


def energy(text: str) -> tuple[float | None, str]:
    value = text.strip()
    if value.lower() in ("", "nan", "null"):
        return None, "missing"
    try:
        number = float(value)
    except ValueError:
        return None, "invalid"
    if not math.isfinite(number) or number < 0:
        return None, "invalid"
    return number, "valid"


def parse_observations(rows: list[dict]) -> pd.DataFrame:
    """Normalize selected cells. All duplicate keys are quarantined, never averaged."""
    frame = pd.DataFrame(rows)
    frame["interval_end_gmt"] = pd.to_datetime(frame["source_timestamp"].map(endpoint), utc=True)
    frame["interval_start_gmt"] = frame.interval_end_gmt - pd.Timedelta(minutes=30)
    if any(not re.fullmatch(r"MAC\d{6}", h) for h in frame.household_id):
        raise ValueError("Invalid household ID")
    parsed = frame.source_kwh.map(energy)
    frame["energy_kwh"] = [v[0] for v in parsed]
    frame["quality"] = [v[1] for v in parsed]
    duplicates = frame.duplicated(["household_id", "interval_end_gmt"], keep=False)
    frame.loc[duplicates, "quality"] = "duplicate"
    frame.loc[duplicates, "energy_kwh"] = float("nan")
    frame["average_power_kw"] = frame.energy_kwh * 2
    return frame


def inspect_archive(archive: Path, days: set[date], count: int = 100) -> tuple[pd.DataFrame, dict]:
    """One bounded-memory pass over all cells, retaining only selected dates/IDs."""
    counts: Counter = Counter()
    timestamps: Counter = Counter()
    retained = []
    with ZipFile(archive) as zipped:
        members = [i for i in zipped.infolist() if i.filename.endswith(".csv")]
        if len(members) != 1:
            raise ValueError("Expected exactly one source CSV")
        info = members[0]
        with zipped.open(info) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8"))
            header = next(reader)
            if header[0] != "DateTime":
                raise ValueError("Unexpected timestamp column")
            ids = header[1:]
            chosen = sample_ids(ids, count)
            indices = [(i + 1, h) for i, h in enumerate(ids) if h in chosen]
            for row in reader:
                if len(row) != len(header):
                    raise ValueError("Source row width does not match household header")
                end = endpoint(row[0])
                timestamps[end] += 1
                counts["timestamp_rows"] += 1
                for cell in row[1:]:
                    _, quality = energy(cell)
                    counts[quality] += 1
                    counts["blank_cells"] += int(not cell.strip())
                if (end - timedelta(minutes=30)).date() in days:
                    retained.extend(
                        {"household_id": h, "source_timestamp": row[0], "source_kwh": row[i]}
                        for i, h in indices
                    )
    earliest, latest = min(timestamps), max(timestamps)
    expected = int((latest - earliest).total_seconds() / 1800) + 1
    report = {
        key: counts[key] for key in ("timestamp_rows", "valid", "missing", "invalid", "blank_cells")
    } | {
        "member": info.filename,
        "csv_bytes": info.file_size,
        "zip_bytes": archive.stat().st_size,
        "household_count": len(ids),
        "household_ids": ids,
        "sample_ids": chosen,
        "earliest_end": earliest.isoformat(),
        "latest_end": latest.isoformat(),
        "duplicate_timestamp_rows": sum(n - 1 for n in timestamps.values()),
        "missing_timestamp_rows": expected - len(timestamps),
        "duplicate_household_timestamp_keys": sum(n > 1 for n in timestamps.values()) * len(ids),
        "sampling_policy": "first 100 SHA256(seed:ID), seed=batteryflex-lcl-v1",
    }
    return parse_observations(retained), report
