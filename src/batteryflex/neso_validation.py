"""Fail-closed final eligibility checks using raw status and applicable DFS definitions."""

import hashlib
import json
from datetime import UTC, date, datetime
from math import isfinite
from urllib.parse import parse_qs, urlparse

from batteryflex.neso import API_URL, RESOURCES, Sample, parse_date
from batteryflex.neso_intervals import IntervalError, event_intervals
from batteryflex.neso_selection import diverse_recommendations, historical_groups

TERMS_2024 = "https://www.neso.energy/document/348106/download"
GUIDANCE_2023 = "https://www.neso.energy/document/286981/download"
RULES_CURRENT = "https://www.neso.energy/document/379391/download"
WINTER_REVIEW_2023 = "https://www.neso.energy/document/319911/download"


def direction_evidence(sample: Sample, records: list[dict]) -> tuple[str, str, str | None]:
    """Use only raw direction or an audited resource + applicable historical definition."""
    directions = {r.get("Event Type") for r in records}
    days = [parse_date(r.get("Delivery Date")) for r in records]
    if directions == {"Downwards"}:
        if sample.resource_id != RESOURCES["DFS Service Requirement"]:
            return "UNVERIFIED", "Direction label lacks audited resource semantics.", None
        if not all(d is not None and d >= date(2026, 4, 9) for d in days):
            return "UNVERIFIED", "Direction definition not verified for these dates.", None
        return "PASS", "Explicit Downwards = demand reduction/generation increase.", RULES_CURRENT
    if directions != {None}:
        return "FAIL", "Direction is not uniformly verified demand reduction.", RULES_CURRENT
    archive = sample.resource_id == RESOURCES["DFS Service Requirement (Archive 2025/2026)"]
    legacy = sample.resource_id == RESOURCES["DFS Service Requirements (2023/2024)"]
    if archive and all(d is not None and date(2024, 11, 27) <= d < date(2026, 4, 9) for d in days):
        return (
            "PASS",
            "DFS Service Terms v3, clause 5.2: demand below operational baseline; "
            "raw direction absent.",
            TERMS_2024,
        )
    if legacy and all(d is not None and date(2023, 11, 1) <= d <= date(2024, 3, 31) for d in days):
        return (
            "PASS",
            "Winter 2023/24 participation guidance: service delivery is demand reduction; "
            "raw direction absent.",
            GUIDANCE_2023,
        )
    return "UNVERIFIED", "No applicable official direction definition established.", None


def validate_event(sample: Sample, event: dict, *, as_of: date | None = None) -> dict:
    """Assess each mandatory criterion, retaining original values and explicit internal ID."""
    result = dict(event)
    as_of = as_of or datetime.now(UTC).date()
    records = [sample.records[i] for i in event["source_rows"]]
    checks, reasons = {}, {}
    statuses = [r.get("Service Requirement Type") for r in records]
    checks["live"] = (
        "UNVERIFIED"
        if not records or any(v is None or v == "" for v in statuses)
        else "PASS"
        if all(v == "Live" for v in statuses)
        else "FAIL"
    )
    reasons["live"] = "Every original Service Requirement Type must explicitly equal Live."
    checks["direction"], reasons["direction"], definition = direction_evidence(sample, records)
    days = [parse_date(r.get("Delivery Date")) for r in records]
    checks["historical_date"] = (
        "UNVERIFIED"
        if not days or any(d is None for d in days)
        else "PASS"
        if len(set(days)) == 1 and all(d is not None and d < as_of for d in days)
        else "FAIL"
    )
    reasons["historical_date"] = "One valid past original delivery date."
    ids = [r.get("_id") for r in records]
    traceable = bool(ids) and all(isinstance(v, int) and not isinstance(v, bool) for v in ids)
    traceable = traceable and len(set(ids)) == len(ids)
    checks["original_records"] = "PASS" if traceable else "UNVERIFIED"
    reasons["original_records"] = "Resource-scoped CKAN IDs trace every original interval record."
    urls = sample.request_urls or [sample.source_url]

    def official_request(url):
        parsed = urlparse(url)
        return (
            url.split("?")[0] == API_URL
            and parsed.scheme == "https"
            and parse_qs(parsed.query).get("resource_id") == [sample.resource_id]
        )

    checks["source_resource"] = (
        "PASS"
        if sample.resource_id in RESOURCES.values() and all(official_request(u) for u in urls)
        else "UNVERIFIED"
    )
    reasons["source_resource"] = (
        "Known official requirement resource and exact public API request URLs."
    )
    checks["complete_retrieval"] = (
        "PASS" if sample.complete and len(sample.records) == sample.total else "UNVERIFIED"
    )
    reasons["complete_retrieval"] = "Complete source prevents accepting a truncated event."
    requirements = [r.get("Service Requirement MW", r.get("DFS Required MW")) for r in records]
    try:
        checks["requirement_mw"] = (
            "UNVERIFIED"
            if not requirements or any(v is None or v == "" for v in requirements)
            else "PASS"
            if all(
                not isinstance(v, bool) and isfinite(float(v)) and float(v) > 0
                for v in requirements
            )
            else "FAIL"
        )
    except (ValueError, TypeError):
        checks["requirement_mw"] = "FAIL"
    reasons["requirement_mw"] = "Every original source requirement is finite, positive MW."
    try:
        intervals = event_intervals(sample, event)
        checks["valid_times"] = "PASS" if intervals else "UNVERIFIED"
        checks["continuous_window"] = "PASS" if intervals else "UNVERIFIED"
    except (IntervalError, ValueError, KeyError) as exc:
        intervals = []
        checks["valid_times"] = "UNVERIFIED"
        checks["continuous_window"] = "FAIL"
        reasons["continuous_window"] = str(exc)
    reasons["valid_times"] = "Source clocks resolve to positive aware instants with GMT/BST checks."
    reasons.setdefault(
        "continuous_window", "Consecutive windows without gaps, overlap or duplicates."
    )
    verdict = (
        "FAIL"
        if "FAIL" in checks.values()
        else "UNVERIFIED"
        if "UNVERIFIED" in checks.values()
        else "PASS"
    )
    identity = {
        "resource": sample.resource_id,
        "date": str(event["delivery_date"]),
        "records": ids,
        "start": event.get("start_utc"),
        "end": event.get("end_utc"),
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:10]
    day = event["delivery_date"]
    season_start = day.year - (day.month < 11) if isinstance(day, date) else None
    internal_id = f"BF-SCENARIO-{str(event['delivery_date']).replace('-', '')}-{digest}"
    result.update(
        {
            "validation_status": verdict,
            "validation_criteria": checks,
            "validation_reasons": reasons,
            "direction_definition_url": definition,
            "verified_direction_meaning": "Demand reduction"
            if checks["direction"] == "PASS"
            else None,
            "internal_scenario_id": internal_id,
            "internal_id_notice": "Internal BatteryFlex scenario ID; not an official NESO Event ID",
            "winter_season": f"{season_start}/{(season_start + 1) % 100:02}"
            if season_start is not None
            else None,
            "source_records_sha256": hashlib.sha256(
                json.dumps(records, sort_keys=True).encode()
            ).hexdigest(),
            "verified_interval_count": len(intervals),
        }
    )
    return result


def validated_groups(samples: list[Sample]) -> list[dict]:
    return [validate_event(s, g) for s in samples for g in historical_groups(s)]


def final_recommendations(samples: list[Sample]) -> list[dict]:
    eligible = [g for g in validated_groups(samples) if g["validation_status"] == "PASS"]
    return diverse_recommendations(samples, groups=eligible)
