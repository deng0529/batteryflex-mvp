"""Read-only public NESO samples and schema-aware exploration; no persistence."""

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

PORTAL_URL = "https://www.neso.energy/data-portal/demand-flexibility"
API_URL = "https://api.neso.energy/api/3/action/datastore_search"
RESOURCES = {
    "DFS Service Requirement": "3635fd80-49d7-4d02-964d-cc8c08d50302",
    "DFS Service Requirement (Archive 2025/2026)": "f5605e2b-b677-424c-8df7-d0ce4ee03cef",
    "DFS Service Requirements (2023/2024)": "7914dd99-fe1c-41ba-9989-5784531c58bb",
}
ALIASES = {
    "event_id": ("Event ID",),
    "delivery_date": ("Delivery Date",),
    "start_time": ("From_UTC", "From", "From_Local"),
    "end_time": ("To_UTC", "To", "To_Local"),
    "required_mw": ("Service Requirement MW", "DFS Required MW"),
    "direction": ("Event Type",),
    "requirement_type": ("Service Requirement Type",),
}


class NesoError(Exception):
    """A public request failed or returned an unusable envelope."""


@dataclass
class Sample:
    source_name: str
    resource_id: str
    source_url: str
    retrieved_at: str
    records: list[dict]
    fields: list[dict]
    total: int | None
    request_urls: list[str] = field(default_factory=list)
    complete: bool = False
    completed_at: str | None = None


def _fetch_page(source_name: str, limit: int, offset: int | None = None) -> Sample:
    """Fetch a bounded sample, only when explicitly called. No auth or retries."""
    if source_name not in RESOURCES or not 1 <= limit <= 1000:
        raise ValueError("Choose a known resource and limit between 1 and 1000.")
    resource_id = RESOURCES[source_name]
    params = {"resource_id": resource_id, "limit": limit}
    if offset is not None:
        params.update({"offset": offset, "sort": "_id asc"})
    url = API_URL + "?" + urlencode(params)
    try:
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except (URLError, OSError, ValueError) as exc:
        raise NesoError(
            "NESO request failed: network error or invalid JSON. Retry the fetch."
        ) from exc
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise NesoError("NESO API reported an unsuccessful response.")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NesoError("NESO response has no result object.")
    records, fields = result.get("records"), result.get("fields", [])
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise NesoError("NESO records must be a list of objects.")
    if not isinstance(fields, list) or not all(
        isinstance(f, dict) and isinstance(f.get("id"), str) for f in fields
    ):
        raise NesoError("Unexpected NESO field metadata.")
    total = result.get("total")
    return Sample(
        source_name,
        resource_id,
        url,
        datetime.now(UTC).isoformat(),
        records,
        fields,
        total if isinstance(total, int) and not isinstance(total, bool) and total >= 0 else None,
        request_urls=[url],
    )


def fetch_sample(source_name: str, limit: int = 100) -> Sample:
    """Preserve the original explicit bounded-sample API."""
    return _fetch_page(source_name, limit)


def fetch_all(source_name: str, page_size: int = 1000) -> Sample:
    """Read all pages in stable record-ID order; fail closed on incomplete/changing data.

    No API snapshot isolation is available. Stable totals and unique IDs detect common
    pagination races, but do not guarantee unchanged content during acquisition.
    Raw business duplicates are retained; they belong in the analysis report.
    """
    sample = _fetch_page(source_name, page_size, 0)
    expected = sample.total
    if expected is None:
        raise NesoError("Full retrieval requires a valid source total.")
    if expected > 100_000:
        raise NesoError("Resource exceeds the 100,000-row exploration safety limit.")
    seen = set()
    page = sample
    while True:
        for record in page.records:
            record_id = record.get("_id")
            if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id in seen:
                raise NesoError("Missing or repeated record ID during pagination; retry retrieval.")
            seen.add(record_id)
        if len(sample.records) > expected:
            raise NesoError("NESO returned more rows than its declared total.")
        if len(sample.records) == expected:
            break
        if not page.records:
            raise NesoError("NESO pagination ended before all records were retrieved.")
        page = _fetch_page(source_name, page_size, len(sample.records))
        if page.total != expected or page.fields != sample.fields:
            raise NesoError("NESO total or schema changed during retrieval; retry.")
        sample.records.extend(page.records)
        sample.request_urls.extend(page.request_urls)
    sample.complete = True
    sample.completed_at = datetime.now(UTC).isoformat()
    return sample


def missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def discover_schema(sample: Sample) -> list[dict]:
    """Union metadata and every record's keys; never drop unrecognised columns."""
    declared = {f["id"]: f.get("type", "unknown") for f in sample.fields}
    columns = dict.fromkeys([*declared, *(k for r in sample.records for k in r)])
    return [
        {
            "column": col,
            "source_type": declared.get(col, "unknown"),
            "observed_types": ", ".join(
                sorted({type(r[col]).__name__ for r in sample.records if not missing(r.get(col))})
            )
            or "null",
            "missing_count": sum(missing(r.get(col)) for r in sample.records),
        }
        for col in columns
    ]


def field_mapping(sample: Sample) -> dict[str, str | None]:
    columns = {s["column"] for s in discover_schema(sample)}
    return {
        name: next((c for c in aliases if c in columns), None) for name, aliases in ALIASES.items()
    }


def parse_date(value: object) -> date | None:
    """Parse declared delivery dates without timezone conversion or date shifting."""
    if not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def standardise(sample: Sample) -> list[dict]:
    mapping = field_mapping(sample)
    rows = []
    for index, record in enumerate(sample.records):
        row = {name: record.get(col) if col else None for name, col in mapping.items()}
        raw_mw = row["required_mw"]
        try:
            mw = (
                float(raw_mw)
                if isinstance(raw_mw, (str, int, float)) and not isinstance(raw_mw, bool)
                else math.nan
            )
            row["required_mw"] = mw if math.isfinite(mw) else None
        except (TypeError, ValueError):
            row["required_mw"] = None
        row["delivery_date"] = parse_date(row["delivery_date"])
        start = mapping["start_time"]
        row["time_basis"] = (
            "UTC"
            if start == "From_UTC"
            else "GMT (source metadata)"
            if start == "From"
            else "Local (source metadata; no offset inferred)"
            if start
            else None
        )
        row["source_row"] = index
        row["source_record_id"] = record.get("_id")
        row["resource_id"] = sample.resource_id
        row["source_name"] = sample.source_name
        row["start_local"] = record.get("From_Local")
        row["end_local"] = record.get("To_Local")
        row["event_tag"] = record.get("Event Tag")
        row["dispatch_type"] = record.get("Dispatch Type", record.get("Despatch Type"))
        row["eligible_participants"] = record.get("Participant Bids Eligible")
        row["zonal_cap"] = record.get("Zonal Cap")
        rows.append(row)
    return rows


def filter_events(
    rows: list[dict],
    *,
    year: int | None = None,
    month: int | None = None,
    start: date | None = None,
    end: date | None = None,
    direction: str | None = None,
    requirement_type: str | None = None,
) -> list[dict]:
    """Inclusive delivery-date filters; undated rows survive only without date filters."""
    output = []
    for row in rows:
        day = row["delivery_date"]
        if any(v is not None for v in (year, month, start, end)):
            if day is None:
                continue
            if year is not None and day.year != year:
                continue
            if month is not None and day.month != month:
                continue
            if (start is not None and day < start) or (end is not None and day > end):
                continue
        if direction is not None and row["direction"] != direction:
            continue
        if requirement_type is not None and row["requirement_type"] != requirement_type:
            continue
        output.append(row)
    return output
