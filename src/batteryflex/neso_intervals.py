"""Aware source windows and bounded 30-minute views; never invent source requests."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

from batteryflex.neso import Sample

LONDON = ZoneInfo("Europe/London")


class IntervalError(ValueError):
    """Ambiguous, invalid or conflicting source chronology."""


def clock(value: str):
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            pass
    raise IntervalError(f"Invalid source clock: {value}")


def local_instant(
    day: date, value: str, *, fold: int | None = None, utc_clock: str | None = None
) -> datetime:
    """Round-trip detects nonexistent times; disambiguation requires explicit evidence."""
    naive = datetime.combine(day, clock(value))
    possible = {}
    for candidate_fold in (0, 1):
        local = naive.replace(tzinfo=LONDON, fold=candidate_fold)
        instant = local.astimezone(UTC)
        if instant.astimezone(LONDON).replace(tzinfo=None) != naive:
            continue
        if fold is not None and candidate_fold != fold:
            continue
        if utc_clock is not None and instant.time().replace(tzinfo=None) != clock(utc_clock):
            continue
        possible[instant] = local
    if len(possible) != 1:
        raise IntervalError(
            "Nonexistent, ambiguous or inconsistent UK local time; offset required."
        )
    return next(iter(possible)).astimezone(UTC)


@dataclass(frozen=True)
class RequirementWindow:
    start: datetime
    end: datetime
    required_mw: float | None
    event_id: object = None
    source_record_id: object = None
    resource_id: str = ""


def source_window(sample: Sample, record: dict) -> RequirementWindow:
    """Original delivery date is local for dual-clock rows, GMT for From/To metadata.

    An earlier end clock can indicate following day after checking same-day DST evidence.
    Equal clocks without positive elapsed-time evidence are rejected,
    not assumed to mean 24 hours. Raw values are untouched; derived ISO instants are separate.
    """
    day = date.fromisoformat(record["Delivery Date"])
    if record.get("From_Local") is not None and record.get("To_Local") is not None:
        start_clock, end_clock = record["From_Local"], record["To_Local"]
        start = local_instant(day, start_clock, utc_clock=record.get("From_UTC"))
        # A backward wall clock may be the autumn fold, not midnight rollover.
        end = None
        end_days = [day]
        if clock(end_clock) < clock(start_clock):
            end_days.append(day + timedelta(days=1))
        for end_day in end_days:
            try:
                candidate = local_instant(end_day, end_clock, utc_clock=record.get("To_UTC"))
            except IntervalError:
                continue
            if candidate > start:
                end = candidate
                break
        if end is None:
            raise IntervalError("Cannot resolve positive end time from source clocks.")
    elif "From" in record and "To" in record:
        start_clock, end_clock = record["From"], record["To"]
        end_day = day + timedelta(days=clock(end_clock) < clock(start_clock))
        start = datetime.combine(day, clock(start_clock), UTC)
        end = datetime.combine(end_day, clock(end_clock), UTC)
    else:
        raise IntervalError("Source lacks a documented complete local/UTC or GMT window.")
    mw = record.get("Service Requirement MW", record.get("DFS Required MW"))
    if mw is not None:
        try:
            mw = float(mw) if not isinstance(mw, bool) else None
        except (TypeError, ValueError) as exc:
            raise IntervalError("Invalid source requirement.") from exc
        if mw is None or not isfinite(mw):
            raise IntervalError("Invalid source requirement.")
    return RequirementWindow(
        start, end, mw, record.get("Event ID"), record.get("_id"), sample.resource_id
    )


def interval_view(windows: list[RequirementWindow]) -> list[dict]:
    """Split elapsed UTC time at 30-minute grid AND original requirement boundaries.

    Preserve source partial intervals, gaps/overlaps fail clearly. For a whole-event
    constant window split into pieces, repetition is an explicit simulation assumption.
    No interpolation or averaging of time-varying source requirements is performed.
    """
    for w in windows:
        if w.start.utcoffset() is None or w.end.utcoffset() is None:
            raise IntervalError("Aware timestamps are required.")
        if w.required_mw is not None and not isfinite(w.required_mw):
            raise IntervalError("Finite requirement or an explicit missing value is required.")
    ordered = sorted(windows, key=lambda w: w.start.astimezone(UTC))
    if not ordered:
        return []
    anchor = ordered[0].start.astimezone(UTC)
    previous = anchor
    output = []
    for w in ordered:
        start, end = w.start.astimezone(UTC), w.end.astimezone(UTC)
        if end <= start or start != previous:
            raise IntervalError("Zero/negative, gapped, overlapping or duplicate source windows.")
        cursor = start
        while cursor < end:
            grid_end = anchor + timedelta(
                minutes=(int((cursor - anchor).total_seconds() // 1800) + 1) * 30
            )
            stop = min(end, grid_end)
            direct = cursor == start and stop == end
            output.append(
                {
                    "interval_number": len(output) + 1,
                    "start_utc": cursor.isoformat(),
                    "end_utc": stop.isoformat(),
                    "start_uk": cursor.astimezone(LONDON).isoformat(),
                    "end_uk": stop.astimezone(LONDON).isoformat(),
                    "duration_hours": (stop - cursor).total_seconds() / 3600,
                    "national_requirement_mw": w.required_mw,
                    "source_event_id": w.event_id,
                    "source_record_id": w.source_record_id,
                    "resource_id": w.resource_id,
                    "requirement_basis": "Directly reported source window"
                    if direct
                    else "Derived: constant within source window (simulation assumption)",
                    "partial_interval": (stop - cursor).total_seconds() != 1800,
                }
            )
            cursor = stop
        previous = end
    return output


def event_intervals(sample: Sample, event: dict) -> list[dict]:
    return interval_view([source_window(sample, sample.records[i]) for i in event["source_rows"]])
