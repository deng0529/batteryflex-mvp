"""Event fulfilment and physical shortfall evidence from saved trajectories."""

from dataclasses import dataclass

import numpy as np

from batteryflex.dispatch import DT, EPS, Scenario


@dataclass(frozen=True)
class EventOutcome:
    steps: tuple[int, ...]
    requested_kw: np.ndarray
    delivered_kw: np.ndarray
    requested_kwh: float
    delivered_kwh: float
    credited_kwh: float
    shortfall_kwh: float
    fulfilment_pct: float | None
    failed_steps: tuple[int, ...]
    status: str


def event_outcome(s: Scenario, data: dict) -> EventOutcome:
    steps = list(s.event_steps)
    delivered = np.asarray(data["flex_kw"], dtype=float)[steps]
    if "request_kw" in data:
        requested = np.asarray(data["request_kw"], dtype=float)[steps]
    else:
        requested = np.full(len(steps), s.target_kw, dtype=float)
    required, gross = float(requested.sum() * DT), float(delivered.sum() * DT)
    interval_target = s.target_type == "interval"
    gap = requested - delivered
    failed = tuple(step for step, deficit in zip(steps, gap, strict=True) if deficit > EPS)
    shortfall = (
        float(np.maximum(0, gap).sum() * DT) if interval_target else max(0, required - gross)
    )
    credited = max(0, required - shortfall)
    met = not failed if interval_target else shortfall <= EPS
    status = "NOT ASSESSABLE" if required <= 0 else "MET" if met else "NOT MET"
    return EventOutcome(
        s.event_steps,
        requested,
        delivered,
        required,
        gross,
        credited,
        shortfall,
        100 * credited / required if required > 0 else None,
        failed if interval_target and required > 0 else (),
        status,
    )


@dataclass(frozen=True)
class ShortfallEvidence:
    physical_ceiling_kw: float | None
    verified: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    extra_stored_kwh: float | None = None


def diagnose_interval(
    s: Scenario, result: dict, slot: str, step: int, requested_kw: float
) -> ShortfallEvidence:
    """Check instantaneous headroom at the recorded state and household demand."""
    data = result[slot]
    trace_name = "planned_trace" if slot == "planned" else "realized_trace"
    trace = next(
        (
            r
            for r in result.get(trace_name) or []
            if r.get("step") == step + 1 and "applied_kw" in r
        ),
        {},
    )
    observed = []
    if (
        trace.get("physical_adjustment")
        or trace.get("export_adjustment")
        or trace.get("constrained_households")
    ):
        observed.append("The execution trace records a setpoint correction.")
    if trace.get("status") == "Feasible incumbent":
        observed.append(
            "The solver returned a feasible incumbent. Its effect on delivery is unknown."
        )
    if any(not b.participating for b in s.batteries):
        observed.append("Some batteries were outside the participating portfolio.")
    if result.get("method") == "RBC" and any(
        str(r.get("rule", "")).endswith("precharge skipped above price ceiling")
        for r in result.get(trace_name) or []
        if r.get("step", 0) <= step
    ):
        observed.append(
            "The RBC price ceiling skipped pre-event charging. Its effect is unverified."
        )
    if result.get("method") == "MILP" and "Completed with feasible incumbents" == result.get(
        "solver_status"
    ):
        observed.append("The day-ahead solver used a feasible incumbent. Its effect is unverified.")
    try:
        before = np.asarray(data["energy_kwh"][step], dtype=float)
        load = np.asarray(data["load_kw"][step], dtype=float)
        delivered = float(data["flex_kw"][step])
    except (KeyError, IndexError, TypeError, ValueError):
        return ShortfallEvidence(None, observed=tuple(observed))
    expected = (len(s.batteries),)
    if (
        before.shape != expected
        or load.shape != expected
        or not (np.isfinite(before).all() and np.isfinite(load).all() and np.isfinite(delivered))
    ):
        return ShortfallEvidence(None, observed=tuple(observed))

    capacity = np.array([b.capacity_kwh for b in s.batteries])
    physical_floor = capacity * np.array([b.min_soc for b in s.batteries])
    efficiency = np.array([b.discharge_efficiency for b in s.batteries])
    active = np.array([b.participating for b in s.batteries])
    rating = np.array([b.discharge_limit_kw for b in s.batteries]) * active
    export = np.array(
        [
            (b.discharge_limit_kw if b.export_limit_kw is None else b.export_limit_kw)
            if b.export_enabled
            else 0
            for b in s.batteries
        ]
    )
    grid = np.maximum(0, load + export) * active
    energy = np.maximum(0, before - physical_floor) * efficiency / DT * active
    actual_bound = np.minimum.reduce([rating, grid, energy])
    ceiling = float(actual_bound.sum())
    verified = []
    extra = None
    if ceiling < requested_kw - EPS:
        for name, relaxed in (
            ("Battery energy availability was a limiting factor.", np.minimum(rating, grid)),
            ("Battery discharge ratings limited additional discharge.", np.minimum(energy, grid)),
            (
                "Household grid export limits restricted additional discharge.",
                np.minimum(energy, rating),
            ),
        ):
            if np.any(relaxed > actual_bound + EPS):
                verified.append(name)
        if not verified:
            observed.append("Several battery limits coincide at the instantaneous ceiling.")
        extra_for_energy = (
            np.minimum.reduce(
                [
                    rating,
                    grid,
                    np.maximum(0, capacity * np.array([b.max_soc for b in s.batteries]) - before)
                    * efficiency
                    / DT
                    + energy,
                ]
            )
            - actual_bound
        )
        remaining = requested_kw - ceiling
        if abs(delivered - ceiling) <= EPS and float(extra_for_energy.sum()) >= remaining - EPS:
            extra = 0.0
            for i in np.argsort(-efficiency):
                share = min(remaining, max(0, extra_for_energy[i]))
                extra += share * DT / efficiency[i]
                remaining -= share
    if result.get("method") == "RBC":
        reserve = np.maximum(physical_floor, capacity * s.reserve_soc)
        reserve_power = np.maximum(0, before - reserve) * efficiency / DT * active
        reserve_ceiling = np.minimum.reduce([rating, grid, reserve_power]).sum()
        if reserve_ceiling < requested_kw - EPS and reserve_ceiling < ceiling - EPS:
            observed.append(
                "Keeping the RBC reserve reduced discretionary headroom. "
                "The controller may still discharge below it for connection support."
            )
    return ShortfallEvidence(ceiling, tuple(verified), tuple(observed), extra)


def performance_row(s: Scenario, result: dict, source: str) -> dict:
    data = result.get("realized") or result["planned"]
    outcome = event_outcome(s, data)
    costs = data["weighted_terms"]
    return {
        "NESO event date": result["provenance"]["inputs"]["original_event_date"],
        "Hours": len(s.event_steps) * DT,
        "Requested (kWh)": outcome.requested_kwh,
        "Delivered (kWh)": outcome.delivered_kwh,
        "Fulfilment (%)": outcome.fulfilment_pct,
        "Status": outcome.status,
        "Shortfall (kWh)": outcome.shortfall_kwh,
        "Net electricity (£)": data["cost_gbp"],
        "Shortfall penalty (£)": costs[1],
        "Degradation (£)": costs[2],
        "Terminal deficit (£)": costs[3],
        "Total objective (£)": data["objective"],
        "Source": source,
    }
