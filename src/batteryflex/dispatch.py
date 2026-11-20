"""Shared forecast-planned and historical-replay dispatch for the reviewed portfolio."""

from dataclasses import asdict, dataclass, replace
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from batteryflex.battery import BatteryAction, BatteryConfig, BatteryState, transition
from batteryflex.portfolio import HOUSEHOLDS

DT = 0.5
STEPS = 48
EPS = 1e-6
METHODS = ("RBC", "MPC", "MILP")


@dataclass(frozen=True)
class Scenario:
    batteries: tuple[BatteryConfig, ...]
    event_steps: tuple[int, ...]
    target_kw: float
    import_price: float = 0.25
    export_price: float = 0.05
    import_limit_kw: float | None = None
    reserve_soc: float = 0.2
    target_soc: float = 0.5
    event_soc: float = 0.8
    degradation_price: float = 0.02
    terminal_price: float = 0.1
    weights: tuple[float, float, float, float] = (1, 20, 1, 1)
    prediction_steps: int = 12
    time_limit: float = 10
    gap: float = 0.001
    target_type: str = "interval"
    replay: bool = True
    precharge_price: float = 0.25
    target_export_only: bool = False

    simulation_mode: str = "FULL_DAY"

    @property
    def steps(self) -> int:
        return len(self.event_steps) if self.simulation_mode == "EVENT_ONLY" else STEPS

    def __post_init__(self) -> None:
        if tuple(b.household_id for b in self.batteries) != HOUSEHOLDS:
            raise ValueError("The five reviewed batteries must be supplied in household order")
        if any(b.interval_hours != DT for b in self.batteries):
            raise ValueError("Battery intervals must be 30 minutes")
        if not self.event_steps or tuple(sorted(set(self.event_steps))) != self.event_steps:
            raise ValueError("Supply unique chronological event intervals")
        if self.simulation_mode not in {"FULL_DAY", "EVENT_ONLY"}:
            raise ValueError("Unsupported dispatch simulation mode")
        if self.simulation_mode == "EVENT_ONLY" and self.event_steps != tuple(range(self.steps)):
            raise ValueError("Event-only control steps must start at zero and be contiguous")
        if min(self.event_steps) < 0 or max(self.event_steps) >= STEPS:
            raise ValueError("Event intervals must fall within the forecast day")
        numbers = [
            self.target_kw,
            self.import_price,
            self.export_price,
            self.reserve_soc,
            self.target_soc,
            self.event_soc,
            self.degradation_price,
            self.terminal_price,
            self.time_limit,
            self.gap,
            self.precharge_price,
            *self.weights,
        ]
        if self.import_limit_kw is not None:
            numbers.append(self.import_limit_kw)
        if any(not np.isfinite(v) or v < 0 for v in numbers):
            raise ValueError("Scenario settings must be finite and nonnegative")
        if (
            len(self.weights) != 4
            or not 1 <= self.prediction_steps <= STEPS
            or self.time_limit <= 0
            or self.gap > 1
            or self.target_type not in {"interval", "energy"}
            or max(self.reserve_soc, self.target_soc, self.event_soc) > 1
        ):
            raise ValueError("Invalid objective, reserve, target or solver settings")
        if any(self.reserve_soc > b.max_soc for b in self.batteries):
            raise ValueError("Hard terminal reserve exceeds a battery maximum SoC")


def export_batteries(batteries: tuple[BatteryConfig, ...]) -> tuple[BatteryConfig, ...]:
    """Apply automatic event export using a finite, explicitly simulated connection cap."""
    return tuple(
        replace(
            b,
            export_enabled=b.participating,
            export_limit_kw=b.discharge_limit_kw
            if b.export_limit_kw is None
            else b.export_limit_kw,
        )
        for b in batteries
    )


def _limits(s: Scenario) -> tuple[np.ndarray, ...]:
    b = s.batteries
    capacity = np.array([v.capacity_kwh for v in b])
    return (
        capacity,
        capacity * [v.min_soc for v in b],
        capacity * [v.max_soc for v in b],
        np.array([v.charge_limit_kw * v.participating for v in b]),
        np.array([v.discharge_limit_kw * v.participating for v in b]),
        np.array([v.charge_efficiency for v in b]),
        np.array([v.discharge_efficiency for v in b]),
        np.array(
            [
                v.export_limit_kw if v.export_limit_kw is not None else v.discharge_limit_kw
                for v in b
            ]
        )
        * [v.export_enabled for v in b],
    )


def _solve(
    s: Scenario,
    load: np.ndarray,
    state: np.ndarray,
    start: int,
    delivered: float,
    *,
    qualification: bool = False,
) -> tuple[np.ndarray, dict]:
    """Sparse HiGHS MILP with separate binary battery and grid directions."""
    capacity, lower, upper, cmax, dmax, ec, ed, export = _limits(s)
    n, homes = load.shape
    end = start + n
    event = np.isin(np.arange(start, end), s.event_steps)
    floor = np.maximum(lower, s.reserve_soc * capacity)
    # Short horizons must leave enough time to reach the final hard reserve.
    reachable = np.maximum(lower, floor - (s.steps - end) * ec * cmax * DT)
    impmax = load + cmax
    if s.import_limit_kw is not None:
        impmax = np.minimum(impmax, s.import_limit_kw)
    lows, highs, costs, integers = [], [], [], []
    row_ids, col_ids, coefficients, row_lows, row_highs = [], [], [], [], []

    def variables(shape, lo=0, hi=np.inf, cost=0, binary=False):
        indices = np.arange(len(lows), len(lows) + np.prod(shape)).reshape(shape)
        for values, value in ((lows, lo), (highs, hi), (costs, cost), (integers, int(binary))):
            values.extend(np.broadcast_to(value, shape).ravel())
        return indices

    def row(terms, lo=-np.inf, hi=np.inf):
        for col, value in terms:
            row_ids.append(len(row_lows))
            col_ids.append(col)
            coefficients.append(value)
        row_lows.append(lo)
        row_highs.append(hi)

    w1, w2, w3, w4 = s.weights
    shape = (n, homes)
    c = variables(shape, hi=cmax, cost=w3 * s.degradation_price * DT)
    d = variables(shape, hi=dmax, cost=w3 * s.degradation_price * DT)
    e = variables((n + 1, homes), lower, upper)
    imp = variables(shape, hi=impmax, cost=w1 * s.import_price * DT)
    export_bounds = event[:, None] * export if s.target_export_only else export
    exp = variables(shape, hi=export_bounds, cost=-w1 * s.export_price * DT)
    mode = variables(shape, hi=1, binary=True)
    grid_mode = variables(shape, hi=1, binary=True)
    z = variables((homes,), cost=w4 * s.terminal_price if end == s.steps else 0)
    for i in range(homes):
        row([(e[0, i], 1)], state[i], state[i])
        row([(e[-1, i], 1)], reachable[i])
        if end == s.steps:
            row([(e[-1, i], 1), (z[i], 1)], capacity[i] * s.target_soc)
        for k in range(n):
            row(
                [(e[k + 1, i], 1), (e[k, i], -1), (c[k, i], -DT * ec[i]), (d[k, i], DT / ed[i])],
                0,
                0,
            )
            row(
                [(imp[k, i], 1), (exp[k, i], -1), (c[k, i], -1), (d[k, i], 1)],
                load[k, i],
                load[k, i],
            )
            row([(c[k, i], 1), (mode[k, i], -cmax[i])], hi=0)
            row([(d[k, i], 1), (mode[k, i], dmax[i])], hi=dmax[i])
            row([(imp[k, i], 1), (grid_mode[k, i], -impmax[k, i])], hi=0)
            row([(exp[k, i], 1), (grid_mode[k, i], export[i])], hi=export[i])
    shortfalls = []
    event_indices = np.flatnonzero(event)
    if s.target_type == "interval":
        for k in event_indices:
            short = variables((1,), hi=0 if qualification else np.inf, cost=w2 * DT)[0]
            shortfalls.append((short, DT))
            row(
                [
                    (short, 1),
                    *[(d[k, i], 1) for i in range(homes)],
                    *[(c[k, i], -1) for i in range(homes)],
                ],
                s.target_kw,
            )
    elif len(event_indices):
        short = variables((1,), hi=0 if qualification else np.inf, cost=w2)[0]
        shortfalls.append((short, 1.0))
        # Recover accumulated misses across the remaining event intervals in this window.
        remaining = sum(k >= start for k in s.event_steps)
        budget = max(0.0, s.target_kw * len(s.event_steps) * DT - delivered)
        terms = [(short, 1)]
        for k in event_indices:
            terms.extend((d[k, i], DT) for i in range(homes))
            terms.extend((c[k, i], -DT) for i in range(homes))
        row(terms, budget * len(event_indices) / remaining)

    if s.target_export_only and export.any():
        for k in event_indices:
            gate = variables((1,), hi=1, binary=True)[0]
            row([*((exp[k, i], 1) for i in range(homes)), (gate, -export.sum())], hi=0)
            relevant = [k] if s.target_type == "interval" else event_indices[event_indices <= k]
            scale = 1.0 if s.target_type == "interval" else DT
            cap = (
                s.target_kw
                if s.target_type == "interval"
                else max(0.0, s.target_kw * len(s.event_steps) * DT - delivered)
            )
            if cap <= EPS:
                row([(gate, 1)], hi=0)
            # If exporting, cumulative reduction through this interval stays within target.
            big_m = scale * len(relevant) * dmax.sum()
            net = [(d[j, i], scale) for j in relevant for i in range(homes)]
            net.extend((c[j, i], -scale) for j in relevant for i in range(homes))
            row([*net, (gate, big_m)], hi=cap + big_m)

    matrix = coo_matrix(
        (coefficients, (row_ids, col_ids)), shape=(len(row_lows), len(lows))
    ).tocsc()
    before = perf_counter()
    result = milp(
        np.zeros(len(costs)) if qualification else costs,
        integrality=integers,
        bounds=Bounds(lows, highs),
        constraints=LinearConstraint(matrix, row_lows, row_highs),
        options={"time_limit": s.time_limit, "mip_rel_gap": s.gap},
    )
    elapsed = perf_counter() - before
    if qualification:
        return np.empty(0), {
            "status": "QUALIFIED"
            if result.x is not None and result.status in (0, 1)
            else "INFEASIBLE"
            if result.status == 2
            else "UNCONFIRMED",
            "solver_seconds": elapsed,
            "solver_code": int(result.status),
        }
    if result.status not in (0, 1) or result.x is None:
        raise ValueError(
            f"HiGHS could not produce feasible dispatch at step {start + 1}: {result.message}"
        )
    if not np.isfinite(result.x).all():
        raise ValueError("HiGHS returned nonfinite dispatch")
    actions = result.x[c] - result.x[d]
    actions[np.abs(actions) < EPS] = 0
    reported_gap = getattr(result, "mip_gap", None)
    gap = float(reported_gap) if reported_gap is not None and np.isfinite(reported_gap) else None
    status = (
        "Optimal within tolerance"
        if result.status == 0 and gap is not None and gap <= s.gap + EPS
        else "Feasible incumbent"
    )
    predictions = {}
    if s.simulation_mode == "EVENT_ONLY":
        v = result.x
        predictions = {
            "predicted_charge_kw": v[c].tolist(),
            "predicted_discharge_kw": v[d].tolist(),
            "predicted_energy_kwh": v[e].tolist(),
            "predicted_weighted_terms": [
                float(w1 * DT * (s.import_price * v[imp].sum() - s.export_price * v[exp].sum())),
                float(w2 * sum(v[j] * scale for j, scale in shortfalls)),
                float(w3 * DT * s.degradation_price * (v[c] + v[d]).sum()),
                float(w4 * s.terminal_price * v[z].sum()) if end == s.steps else 0.0,
            ],
        }
    return actions, {
        "step": start + 1,
        "horizon_steps": n,
        "status": status,
        "solver_code": int(result.status),
        "gap": gap,
        "runtime_seconds": elapsed,
        "variables": len(lows),
        "constraints": len(row_lows),
        "solver_objective": float(result.fun),
        "predicted_net_battery_kw": actions.tolist(),
        **predictions,
    }


def _action_bounds(
    s: Scenario, load: np.ndarray, state: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    _, lower, upper, cmax, dmax, ec, ed, export = _limits(s)
    lo = np.maximum(-np.minimum(dmax, np.maximum(0, state - lower) * ed / DT), -export - load)
    hi = np.minimum(cmax, np.maximum(0, upper - state) / (ec * DT))
    if s.import_limit_kw is not None:
        hi = np.minimum(hi, s.import_limit_kw - load)
    if np.any(lo > hi + EPS):
        raise ValueError("Household connection limit is infeasible with available battery power")
    return lo, hi


def _guard_export(
    s: Scenario, load: np.ndarray, action: np.ndarray, k: int, delivered: float
) -> np.ndarray:
    if not s.target_export_only:
        return action
    exports = np.maximum(0, -load - action)
    total = exports.sum()
    if total <= EPS:
        return action
    if k not in s.event_steps:
        return action + exports
    target = (
        s.target_kw
        if s.target_type == "interval"
        else max(0.0, s.target_kw * len(s.event_steps) - delivered / DT)
    )
    if target <= EPS:
        return action + exports
    surplus = max(0.0, -action.sum() - target)
    return action + exports * min(1.0, surplus / total)


def _rbc(
    s: Scenario,
    load: np.ndarray,
    state: np.ndarray,
    k: int,
    delivered: float,
) -> tuple[np.ndarray, dict]:
    capacity, lower, _, _, _, ec, ed, _ = _limits(s)
    lo, hi = _action_bounds(s, load, state)
    floor = np.maximum(lower, capacity * s.reserve_soc)
    # Hard physical bounds and connection support precede discretionary dispatch.
    idle = np.clip(np.zeros_like(state), lo, hi)
    if k in s.event_steps:
        requested = s.target_kw
        if s.target_type == "energy":
            remaining = sum(step >= k for step in s.event_steps)
            requested = max(
                0, (s.target_kw * len(s.event_steps) * DT - delivered) / (DT * remaining)
            )
        available = np.maximum(0, -np.maximum(lo, -np.maximum(0, state - floor) * ed / DT))
        available = np.maximum(0, idle + available)
        total = available.sum()
        allocation = (
            available * min(1, max(0, requested + idle.sum()) / total) if total else available
        )
        return idle - allocation, {
            "rule": "Event | distribute requested reduction by available discharge",
            "available_discharge_kw": available.tolist(),
            "allocated_discharge_kw": allocation.tolist(),
            "remaining_request_kw": float(max(0, requested + idle.sum())),
            "unmet_allocation_kw": float(max(0, requested + idle.sum() - allocation.sum())),
        }
    if k < s.event_steps[0] and s.import_price <= s.precharge_price:
        desired = np.maximum(floor, capacity * s.event_soc)
        rule = "Precharge | import price within threshold"
    else:
        desired = floor
        rule = (
            "Reserve recovery or idle | precharge skipped above price ceiling"
            if k < s.event_steps[0]
            else "Reserve recovery or idle | meet connection limits first"
        )
    return np.clip(np.maximum(0, desired - state) / (ec * DT), lo, hi), {
        "rule": rule,
        "requested_energy_kwh": desired.tolist(),
    }


def _trajectory(
    s: Scenario,
    method: str,
    forecast: np.ndarray,
    load: np.ndarray,
    fixed: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    capacity, lower, upper, _, _, _, _, _ = _limits(s)
    states = np.zeros((s.steps + 1, len(s.batteries)))
    states[0] = capacity * [b.initial_soc for b in s.batteries]
    dispatch, trace = [], []
    delivered = 0.0
    if method == "MILP" and fixed is None:
        fixed, details = _solve(s, forecast, states[0], 0, 0)
        trace.append(details)
    for k in range(s.steps):
        state = states[k]
        details: dict = {}
        if fixed is not None:
            requested = fixed[k]
            details = {"step": k + 1, "rule": "Apply scheduled control within realised limits"}
        elif method == "MPC":
            window = forecast[k : k + s.prediction_steps].copy()
            # Only the current measurement is revealed. Later rows remain saved forecasts.
            if s.simulation_mode == "FULL_DAY":
                window[0] = load[k]
            proposal, details = _solve(s, window, state, k, delivered)
            requested = proposal[0]
        else:
            decision_load = forecast[k] if s.simulation_mode == "EVENT_ONLY" else load[k]
            requested, rule = _rbc(s, decision_load, state, k, delivered)
            details = {"step": k + 1, **rule}
        lo, hi = _action_bounds(s, load[k], state)
        feasible = np.clip(requested, lo, hi)
        applied = _guard_export(s, load[k], feasible, k, delivered)
        # Normalise numerical residues before validating against the existing battery model.
        applied[np.abs(applied) < 1e-10] = 0
        for i, b in enumerate(s.batteries):
            a = float(applied[i])
            try:
                states[k + 1, i] = transition(
                    b,
                    BatteryState(float(state[i])),
                    BatteryAction(max(a, 0), max(-a, 0)),
                    load_kw=float(load[k, i]),
                ).energy_kwh
            except ValueError as exc:
                raise ValueError(f"Step {k + 1}, {b.household_id}: {exc}") from exc
        states[k + 1] = np.clip(states[k + 1], lower, upper)
        if k in s.event_steps:
            delivered -= float(applied.sum()) * DT
        details.update(
            energy_before_kwh=state.tolist(),
            requested_kw=requested.tolist(),
            applied_kw=applied.tolist(),
            energy_after_kwh=states[k + 1].tolist(),
            min_action_kw=lo.tolist(),
            max_action_kw=hi.tolist(),
            bound_households=[
                b.household_id
                for i, b in enumerate(s.batteries)
                if abs(applied[i]) > EPS
                and (abs(applied[i] - lo[i]) <= EPS or abs(applied[i] - hi[i]) <= EPS)
            ],
            physical_adjustment=bool(np.any(np.abs(feasible - requested) > EPS)),
            export_adjustment=bool(np.any(np.abs(applied - feasible) > EPS)),
            constrained_households=[
                b.household_id
                for i, b in enumerate(s.batteries)
                if abs(applied[i] - requested[i]) > EPS
            ],
        )
        trace.append(details)
        dispatch.append(applied)
    if np.any(states[-1] < np.maximum(lower, capacity * s.reserve_soc) - EPS):
        boundary = "event-end" if s.simulation_mode == "EVENT_ONLY" else "day-end"
        raise ValueError(
            f"{method} dispatch cannot satisfy the hard {boundary} reserve in this run"
        )
    return np.array(dispatch), states, trace


def evaluate(s: Scenario, load: np.ndarray, actions: np.ndarray, states: np.ndarray) -> dict:
    """Calculate identical physical and economic metrics for every controller."""
    capacity, lower, upper, cmax, dmax, _, _, export_cap = _limits(s)
    charge, discharge = np.maximum(actions, 0), np.maximum(-actions, 0)
    grid = load + actions
    imp, exp = np.maximum(grid, 0), np.maximum(-grid, 0)
    supplied = np.maximum(0, discharge - exp)
    event = np.isin(np.arange(s.steps), s.event_steps)
    delivered = -actions.sum(axis=1)
    requested = np.where(event, s.target_kw, 0.0)
    margin = (delivered - requested)[event]
    total_target = float(requested.sum() * DT)
    total_delivered = float(delivered[event].sum() * DT)
    interval_shortfall = float(np.maximum(0, -margin).sum() * DT)
    interval_surplus = float(np.maximum(0, margin).sum() * DT)
    energy_shortfall = max(0.0, total_target - total_delivered)
    met = int((margin >= -EPS).sum())
    if s.target_type == "interval":
        shortfall, surplus = interval_shortfall, interval_surplus
        status = "MET" if met == len(margin) else "PARTIALLY MET" if met else "NOT MET"
    else:
        shortfall, surplus = energy_shortfall, max(0.0, total_delivered - total_target)
        status = (
            "MET" if shortfall <= EPS else "PARTIALLY MET" if total_delivered > EPS else "NOT MET"
        )
    if s.target_kw <= 0:
        status = "NOT ASSESSABLE"
    imported, exported = float(imp.sum() * DT), float(exp.sum() * DT)
    energy = imported * s.import_price - exported * s.export_price
    baseline_cost = float(load.sum() * DT * s.import_price)
    throughput = float((charge + discharge).sum() * DT)
    terminal_short = float(np.maximum(0, capacity * s.target_soc - states[-1]).sum())
    terms = [energy, shortfall, s.degradation_price * throughput, s.terminal_price * terminal_short]
    weighted = [value * weight for value, weight in zip(terms, s.weights, strict=True)]
    households = []
    floor = np.maximum(lower, capacity * s.reserve_soc)
    for i, b in enumerate(s.batteries):
        households.append(
            {
                "household": b.household_id,
                "capacity_kwh": float(capacity[i]),
                "initial_kwh": float(states[0, i]),
                "initial_soc_pct": float(100 * states[0, i] / capacity[i]),
                "final_kwh": float(states[-1, i]),
                "final_soc_pct": float(100 * states[-1, i] / capacity[i]),
                "usable_kwh": float(max(0, states[-1, i] - lower[i])),
                "above_terminal_reserve_kwh": float(max(0, states[-1, i] - floor[i])),
                "charged_kwh": float(charge[:, i].sum() * DT),
                "discharged_kwh": float(discharge[:, i].sum() * DT),
                "event_discharged_kwh": float(discharge[event, i].sum() * DT),
                "supplied_kwh": float(supplied[:, i].sum() * DT),
                "event_export_kwh": float(exp[event, i].sum() * DT),
                "peak_charge_kw": float(charge[:, i].max()),
                "peak_discharge_kw": float(discharge[:, i].max()),
                "import_reduction_kwh": float((load[:, i] - imp[:, i]).sum() * DT),
                "actual_export_kwh": float(exp[:, i].sum() * DT),
                "event_flex_kwh": float(-actions[event, i].sum() * DT),
            }
        )
    binding = {
        "minimum SoC": int(np.isclose(states[1:], lower, rtol=0, atol=EPS).sum()),
        "maximum SoC": int(np.isclose(states[1:], upper, rtol=0, atol=EPS).sum()),
        "charge rating": int(((charge > EPS) & np.isclose(charge, cmax, rtol=0, atol=EPS)).sum()),
        "discharge rating": int(
            ((discharge > EPS) & np.isclose(discharge, dmax, rtol=0, atol=EPS)).sum()
        ),
        "grid export boundary during discharge": int(
            ((discharge > EPS) & np.isclose(grid, -export_cap, rtol=0, atol=EPS)).sum()
        ),
        "terminal reserve": int(np.isclose(states[-1], floor, rtol=0, atol=EPS).sum()),
    }
    if s.import_limit_kw is not None:
        binding["grid import boundary"] = int(
            np.isclose(grid, s.import_limit_kw, rtol=0, atol=EPS).sum()
        )
    return {
        "status": status,
        "requested_kwh": total_target,
        "delivered_kwh": total_delivered,
        "shortfall_kwh": shortfall,
        "surplus_kwh": surplus,
        "intervals_met": met,
        "event_intervals": len(s.event_steps),
        "fulfilment_pct": 100 * max(0, total_target - shortfall) / total_target
        if total_target
        else None,
        "import_kwh": imported,
        "export_kwh": exported,
        "cost_gbp": energy,
        "import_cost_gbp": imported * s.import_price,
        "export_revenue_gbp": exported * s.export_price,
        "baseline_cost_gbp": baseline_cost,
        "savings_gbp": baseline_cost - energy,
        "charged_kwh": float(charge.sum() * DT),
        "discharged_kwh": float(discharge.sum() * DT),
        "event_discharged_kwh": float(discharge[event].sum() * DT),
        "event_export_kwh": float(exp[event].sum() * DT),
        "supplied_kwh": float(supplied.sum() * DT),
        "remaining_kwh": float(states[-1].sum()),
        "throughput_kwh": throughput,
        "terminal_shortfall_kwh": terminal_short,
        "raw_terms": terms,
        "weighted_terms": weighted,
        "objective": sum(weighted),
        "households": households,
        "binding_counts": binding,
        "charge_kw": charge.tolist(),
        "discharge_kw": discharge.tolist(),
        "grid_kw": grid.tolist(),
        "load_kw": load.tolist(),
        "energy_kwh": states.tolist(),
        "portfolio_import_kw": imp.sum(axis=1).tolist(),
        "portfolio_export_kw": exp.sum(axis=1).tolist(),
        "portfolio_grid_kw": grid.sum(axis=1).tolist(),
        "flex_kw": delivered.tolist(),
        "request_kw": requested.tolist(),
    }


def run_dispatch(
    s: Scenario,
    method: str,
    forecast: np.ndarray,
    actual: np.ndarray | None,
) -> dict:
    """Return serialisable planned/replayed results on one common schema."""
    if method not in METHODS:
        raise ValueError("Unknown dispatch method")
    for label, values in [
        ("Forecast", forecast),
        *([("Historical replay", actual)] if s.replay else []),
    ]:
        if (
            values is None
            or values.shape != (s.steps, len(s.batteries))
            or not np.isfinite(values).all()
            or (values < 0).any()
        ):
            raise ValueError(
                f"{label} requires {s.steps} complete nonnegative intervals for five homes"
            )
    start = perf_counter()
    actions, states, planned_trace = _trajectory(s, method, forecast, forecast, None)
    planned = evaluate(s, forecast, actions, states)
    planned_seconds = perf_counter() - start
    replay_start = perf_counter()
    realized = realized_trace = None
    if s.replay and actual is not None:
        # Standalone MILP replays its original forecast schedule in both modes.
        fixed = actions if method == "MILP" else None
        realized_actions, realized_states, realized_trace = _trajectory(
            s, method, forecast, actual, fixed
        )
        realized = evaluate(s, actual, realized_actions, realized_states)
    solves = [row for row in planned_trace + (realized_trace or []) if "solver_code" in row]
    status = "Rules executed"
    if solves:
        status = (
            "All solves optimal within tolerance"
            if all(row["status"] == "Optimal within tolerance" for row in solves)
            else "Completed with feasible incumbents"
        )
    return {
        "method": method,
        "scenario": asdict(s),
        "planned": planned,
        "realized": realized,
        "planned_trace": planned_trace,
        "realized_trace": realized_trace,
        "solver_status": status,
        "solver_iterations": len(solves),
        "runtime_seconds": perf_counter() - start,
        "trajectory_seconds": {
            "planned": planned_seconds,
            "realized": perf_counter() - replay_start,
        },
    }
