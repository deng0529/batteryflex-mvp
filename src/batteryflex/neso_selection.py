"""Diverse provisional source-backed delivery-window groups, never saved scenarios."""

from collections import Counter, defaultdict
from datetime import date

from batteryflex.neso import Sample
from batteryflex.neso_analysis import event_groups
from batteryflex.neso_intervals import IntervalError, event_intervals

REGIME_SOURCE = (
    "https://www.neso.energy/industry-information/balancing-services/demand-flexibility-service-dfs"
)
LEGACY_RESOURCES = {"f5605e2b-b677-424c-8df7-d0ce4ee03cef", "7914dd99-fe1c-41ba-9989-5784531c58bb"}


def historical_groups(sample: Sample) -> list[dict]:
    """Keep raw direction/ID absent; contextual service meaning is a separate annotation."""
    output = []
    for original in event_groups(sample):
        g = dict(original)
        day = g["delivery_date"]
        explicit = g["direction"] == "Downwards"
        historical = (
            sample.resource_id in LEGACY_RESOURCES
            and day is not None
            and day < date(2026, 4, 9)
            and g["direction"] is None
        )
        g["demand_reduction"] = explicit or historical
        g["direction_evidence"] = (
            "Explicit Downwards source value"
            if explicit
            else "Documented pre-9-Apr-2026 demand-reduction-only DFS regime; raw direction absent"
            if historical
            else "No demand-reduction evidence"
        )
        g["direction_evidence_url"] = REGIME_SOURCE if historical else None
        g["identity_basis"] = (
            "Source Event ID"
            if g["event_id"] is not None
            else (
                "Source/date requirement group; original event ID absent "
                "(not a confirmed event key)"
            )
        )
        try:
            intervals = event_intervals(sample, g)
            g["duration_minutes"] = round(sum(i["duration_hours"] for i in intervals) * 60, 6)
            g["start_uk"] = intervals[0]["start_uk"]
            g["end_uk"] = intervals[-1]["end_uk"]
            g["start_utc"] = intervals[0]["start_utc"]
            g["end_utc"] = intervals[-1]["end_utc"]
            g["interval_error"] = None
            g["contiguous_30min"] = all(i["duration_hours"] == 0.5 for i in intervals)
            valid_mw = all(
                i["national_requirement_mw"] is not None and i["national_requirement_mw"] > 0
                for i in intervals
            )
        except (IntervalError, ValueError, KeyError) as exc:
            g["duration_minutes"] = None
            g["interval_error"] = str(exc)
            valid_mw = False
        g["candidate_status"] = (
            "Provisional candidate"
            if g["demand_reduction"]
            and valid_mw
            and g["requirement_type"] == "Live"
            and g["contiguous_30min"]
            else "Not confirmed suitable"
        )
        output.append(g)
    return output


def availability(samples: list[Sample]) -> list[dict]:
    """Identified counts and date-group counts stay separate; no fictitious event counts."""
    monthly = defaultdict(Counter)
    for sample in samples:
        for g in historical_groups(sample):
            if g["delivery_date"] is None:
                continue
            counts = monthly[(sample.source_name, g["delivery_date"].strftime("%Y-%m"))]
            counts[
                "identified_events" if g["event_id"] is not None else "date_groups_id_absent"
            ] += 1
            if g["demand_reduction"]:
                counts[
                    "reduction_identified" if g["event_id"] is not None else "reduction_date_groups"
                ] += 1
                counts[
                    "reduction_live" if g["requirement_type"] == "Live" else "reduction_test"
                ] += 1
                counts["invalid_or_disjoint_groups"] += g["duration_minutes"] is None
    names = (
        "identified_events",
        "date_groups_id_absent",
        "reduction_identified",
        "reduction_date_groups",
        "reduction_live",
        "reduction_test",
        "invalid_or_disjoint_groups",
    )
    return [
        {"source": source, "year_month": month, **{n: counts[n] for n in names}}
        for (source, month), counts in sorted(monthly.items())
    ]


def duration_distribution(samples: list[Sample]) -> list[dict]:
    counts = Counter(
        (s.source_name, g["requirement_type"], g["duration_minutes"])
        for s in samples
        for g in historical_groups(s)
        if g["demand_reduction"]
    )
    return [
        {"source": s, "status": status, "duration_minutes": duration, "groups": count}
        for (s, status, duration), count in sorted(counts.items(), key=lambda p: str(p[0]))
    ]


def diverse_recommendations(
    samples: list[Sample], *, groups: list[dict] | None = None
) -> list[dict]:
    """Greedy review shortlist: 2x1h, 2x1.5–2h, 1x2–3h, no synthetic subevents.

    Choose whole source events/date groups, prioritising unused winter months, years,
    seasons and residential evening overlap, then closeness to duration target. Never
    manufacture extra events when a duration preference is unavailable.
    """
    pool = (
        groups
        if groups is not None
        else [
            g
            for s in samples
            for g in historical_groups(s)
            if g["candidate_status"] == "Provisional candidate"
        ]
    )
    selected, days, months, years, seasons = [], set(), set(), set(), set()

    def season(day):
        return day.year if day.month >= 11 else day.year - 1

    for low, high, target in (
        (60, 60, 60),
        (60, 60, 60),
        (90, 120, 90),
        (90, 120, 120),
        (120, 180, 180),
    ):
        options = [
            g
            for g in pool
            if g["delivery_date"] not in days and low <= g["duration_minutes"] <= high
        ]
        if not options:
            options = [g for g in pool if g["delivery_date"] not in days]
        if not options:
            break

        def rank(g, target=target):
            d = g["delivery_date"]
            evening = (
                g.get("start_uk", "")[11:16] < "20:00" and g.get("end_uk", "")[11:16] > "17:00"
            )
            return (
                d.month in (11, 12, 1, 2, 3),
                d.month not in months,
                evening,
                d.year not in years,
                season(d) not in seasons,
                -abs(g["duration_minutes"] - target),
                g["event_id"] is not None,
                -d.toordinal(),
            )

        chosen = dict(max(options, key=rank))
        chosen["selection_reason"] = (
            f"Whole {chosen['duration_minutes'] / 60:g}h Live demand-reduction requirement; "
            "winter month/year/season and evening diversity, subject to source-ID limitations."
        )
        selected.append(chosen)
        d = chosen["delivery_date"]
        days.add(d)
        months.add(d.month)
        years.add(d.year)
        seasons.add(season(d))
    return selected


def duplicate_events(samples: list[Sample]) -> list[dict]:
    """Flag matching complete window signatures across sources; never drop raw records."""
    seen, output = {}, []
    for sample in samples:
        for g in historical_groups(sample):
            if g["interval_error"]:
                continue
            signature = tuple(
                (i["start_utc"], i["end_utc"], i["national_requirement_mw"])
                for i in event_intervals(sample, g)
            )
            # Include semantics so opposite directions never collapse.
            key = (
                g["direction"],
                g["demand_reduction"],
                g["requirement_type"],
                g["event_tag"],
                g["eligible_participants"],
                g["zonal_cap"],
                signature,
            )
            if key in seen and seen[key] != sample.resource_id:
                output.append(
                    {
                        "source": sample.resource_id,
                        "date": str(g["delivery_date"]),
                        "event_id": g["event_id"],
                        "matches_resource": seen[key],
                    }
                )
            else:
                seen[key] = sample.resource_id
    return output
