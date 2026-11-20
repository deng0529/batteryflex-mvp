"""Pure historical coverage, duplicate inspection and provisional event screening."""

import json
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import cast

from batteryflex.neso import Sample, discover_schema, standardise


def unique_records(records: list[dict]) -> tuple[list[dict], list[int]]:
    """Exact business-row deduplication, ignoring ONLY CKAN _id; never mutate input.

    Event ID, direction, tag, eligibility and all unknown fields remain in the key.
    This is an analysis helper, not an import policy. Raw UI records stay intact.
    """
    seen = set()
    unique, duplicates = [], []
    for index, record in enumerate(records):
        key = json.dumps({k: v for k, v in record.items() if k != "_id"}, sort_keys=True)
        if key in seen:
            duplicates.append(index)
        else:
            seen.add(key)
            unique.append(record)
    return unique, duplicates


def minute(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.hour * 60 + parsed.minute if parsed.second == 0 else None
        except ValueError:
            pass
    return None


def coverage(sample: Sample) -> dict:
    rows = standardise(sample)
    dates = sorted({r["delivery_date"] for r in rows if r["delivery_date"] is not None})
    _, duplicates = unique_records(sample.records)
    windows = Counter((r["delivery_date"], r["start_time"], r["end_time"]) for r in rows)
    return {
        "rows": len(rows),
        "earliest": dates[0] if dates else None,
        "latest": dates[-1] if dates else None,
        "dates": dates,
        "years": sorted({d.year for d in dates}),
        "months": sorted({d.strftime("%Y-%m") for d in dates}),
        "invalid_dates": sum(r["delivery_date"] is None for r in rows),
        "directions": dict(Counter(r["direction"] for r in rows)),
        "statuses": dict(Counter(r["requirement_type"] for r in rows)),
        "exact_duplicate_rows": len(duplicates),
        "repeated_window_keys": sum(n > 1 for n in windows.values()),
        "repeated_window_excess_rows": sum(n - 1 for n in windows.values()),
        "schema": discover_schema(sample),
    }


def event_groups(sample: Sample) -> list[dict]:
    """Group real IDs by source/date; archive date groups explicitly have unknown identity.

    Do not merge separate IDs, sum MW across intervals, or infer missing direction.
    A date group without an event ID is an inspection convenience, not a source event.
    """
    grouped = defaultdict(list)
    for row in standardise(sample):
        grouped[(row["event_id"], row["delivery_date"])].append(row)
    output = []
    for (event_id, day), rows in grouped.items():
        rows.sort(
            key=lambda r: (
                minute(r["start_time"]) if minute(r["start_time"]) is not None else -1,
                r["source_row"],
            )
        )
        spans = [(minute(r["start_time"]), minute(r["end_time"])) for r in rows]
        valid = all(
            a is not None and b is not None and a % 30 == 0 and b - a == 30 for a, b in spans
        )
        contiguous = valid and all(spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1))
        directions = {r["direction"] for r in rows}
        statuses = {r["requirement_type"] for r in rows}
        explicit_direction = directions in ({"Upwards"}, {"Downwards"})
        live = statuses == {"Live"}
        positive = all(r["required_mw"] is not None and r["required_mw"] > 0 for r in rows)
        qualifies = (
            event_id is not None
            and day is not None
            and contiguous
            and explicit_direction
            and live
            and positive
            and len({r["time_basis"] for r in rows}) == 1
        )

        def values(field, rows=rows):
            return " | ".join(sorted({str(r[field]) for r in rows if r[field] is not None})) or None

        output.append(
            {
                "event_id": event_id,
                "delivery_date": day,
                "start_time": rows[0]["start_time"],
                "end_time": rows[-1]["end_time"],
                "duration_minutes": cast(int, spans[-1][1]) - cast(int, spans[0][0])
                if contiguous
                else None,
                "time_basis": values("time_basis"),
                "required_mw_by_window": values("required_mw"),
                "direction": values("direction"),
                "requirement_type": values("requirement_type"),
                "event_tag": values("event_tag"),
                "dispatch_type": values("dispatch_type"),
                "eligible_participants": values("eligible_participants"),
                "zonal_cap": values("zonal_cap"),
                "source_name": sample.source_name,
                "resource_id": sample.resource_id,
                "source_rows": [r["source_row"] for r in rows],
                "source_record_ids": [r["source_record_id"] for r in rows],
                "window_count": len(rows),
                "contiguous_30min": contiguous,
                "candidate_status": "Provisional candidate"
                if qualifies
                else "Not confirmed suitable",
                "screening_reason": (
                    "Explicit direction, Live, positive MW and contiguous 30-minute windows; "
                    "portfolio feasibility and eligibility unassessed."
                    if qualifies
                    else "Requires review: missing ID/direction, non-Live, invalid/gapped "
                    "windows, mixed time basis or non-positive requirement."
                ),
            }
        )
    return sorted(output, key=lambda g: (str(g["delivery_date"]), str(g["event_id"])))


def recommend_events(sample: Sample, limit: int = 5, direction: str = "Downwards") -> list[dict]:
    """Prefer requested winter, evening, winter-month then recent distinct-date events.

    Rank whole source events, never present a half-hour slice as the whole event.
    No recommendation establishes a five-house commitment or a saved selection.
    """
    groups = [
        g
        for g in event_groups(sample)
        if g["candidate_status"] == "Provisional candidate" and g["direction"] == direction
    ]

    def rank(group):
        day = group["delivery_date"]
        evening = (
            cast(int, minute(group["start_time"])) < 20 * 60
            and cast(int, minute(group["end_time"])) > 17 * 60
        )
        return (
            date(2025, 11, 1) <= day <= date(2026, 3, 31),
            evening,
            day.month in (11, 12, 1, 2, 3),
            day,
            group["duration_minutes"],
        )

    groups.sort(key=rank, reverse=True)
    selected, seen_dates = [], set()
    for group in groups:
        if group["delivery_date"] not in seen_dates:
            selected.append(group)
            seen_dates.add(group["delivery_date"])
        if len(selected) >= limit:
            break
    return selected
