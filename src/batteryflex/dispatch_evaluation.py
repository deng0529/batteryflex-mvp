"""Reconcile persisted dispatch and derive control-interval costs without solving."""

import numpy as np

from batteryflex.dispatch import DT, EPS, Scenario, _limits, evaluate


def constraint_violations(s: Scenario, data: dict) -> list[str]:
    c, d, e, load, grid = (
        np.asarray(data[k], dtype=float)
        for k in ("charge_kw", "discharge_kw", "energy_kwh", "load_kw", "grid_kw")
    )
    shape = (s.steps, len(s.batteries))
    if any(a.shape != shape for a in (c, d, load, grid)) or e.shape != (s.steps + 1, shape[1]):
        raise ValueError("Dispatch arrays have invalid dimensions")
    if not all(np.isfinite(a).all() for a in (c, d, e, load, grid)):
        raise ValueError("Dispatch arrays contain invalid numbers")
    cap, lower, upper, cmax, dmax, ec, ed, exports = _limits(s)
    tests = {
        "battery ratings or simultaneous actions": np.any(
            (c < -EPS) | (d < -EPS) | (c > cmax + EPS) | (d > dmax + EPS) | ((c > EPS) & (d > EPS))
        ),
        "battery energy bounds": np.any((e < lower - EPS) | (e > upper + EPS)),
        "initial battery energy": not np.allclose(
            e[0],
            cap * [b.initial_soc for b in s.batteries],
            atol=EPS,
            rtol=0,
        ),
        "battery energy balance": not np.allclose(
            np.diff(e, axis=0),
            DT * (c * ec - d / ed),
            atol=EPS,
            rtol=0,
        ),
        "household grid balance": not np.allclose(grid, load + c - d, atol=EPS, rtol=0),
        "household export cap": np.any(grid < -exports - EPS),
        "hard terminal reserve": np.any(e[-1] < np.maximum(lower, cap * s.reserve_soc) - EPS),
    }
    if s.import_limit_kw is not None:
        tests["household import cap"] = np.any(grid > s.import_limit_kw + EPS)
    if s.target_export_only:
        event = np.array(s.event_steps)
        exporting = (grid < -EPS).any(axis=1)
        flex = (d - c).sum(axis=1)[event]
        tests["export outside event"] = np.any(exporting & ~np.isin(np.arange(s.steps), event))
        limit = (
            flex - s.target_kw
            if s.target_type == "interval"
            else np.cumsum(flex) * DT - s.target_kw * len(event) * DT
        )
        tests["export beyond target"] = np.any(exporting[event] & (limit > 5 * EPS))
    return [label for label, failed in tests.items() if failed]


def objective_steps(s: Scenario, data: dict, *, weighted: bool = True) -> np.ndarray:
    """Four objective components per executed interval, with end-only deficits."""
    steps = np.zeros((s.steps, 4))
    grid = np.asarray(data["grid_kw"])
    charge, discharge = np.asarray(data["charge_kw"]), np.asarray(data["discharge_kw"])
    steps[:, 0] = DT * (
        np.maximum(grid, 0) * s.import_price - np.maximum(-grid, 0) * s.export_price
    ).sum(axis=1)
    steps[:, 2] = DT * s.degradation_price * (charge + discharge).sum(axis=1)
    event = list(s.event_steps)
    if s.target_type == "interval":
        steps[event, 1] = DT * np.maximum(0, s.target_kw - np.asarray(data["flex_kw"])[event])
    else:
        steps[event[-1], 1] = data["shortfall_kwh"]
    steps[-1, 3] = data["terminal_shortfall_kwh"] * s.terminal_price
    return steps * np.asarray(s.weights) if weighted else steps


def control_rows(result: dict, s: Scenario, key: str) -> tuple[list[dict], list[dict]]:
    """Event-only MPC rows, built from the complete stored trajectory and solve trace."""
    data = result[key]
    trace_name = "planned_trace" if key == "planned" else "realized_trace"
    trace = {r["step"] - 1: r for r in result.get(trace_name) or [] if "applied_kw" in r}
    raw = objective_steps(s, data, weighted=False)
    costs = raw * np.asarray(s.weights)
    portfolio, batteries = [], []
    delivered = missed = 0.0
    for k in s.event_steps:
        step = trace.get(k, {})
        predicted = step.get("predicted_net_battery_kw")
        optimized = predicted[0] if predicted else [None] * len(s.batteries)
        actual = data["flex_kw"][k]
        delivered += actual * DT
        missed += max(0, s.target_kw - actual) * DT
        obligation = max(0.0, data["requested_kwh"] - delivered)
        if s.target_type == "interval":
            obligation = (sum(j > k for j in s.event_steps) * s.target_kw * DT) + missed
        gap = step.get("gap")
        portfolio.append(
            {
                "Step": k,
                "Horizon (steps)": step.get("horizon_steps"),
                "Solver status": step.get("status"),
                "Predicted solver objective (£)": step.get("solver_objective"),
                "MIP gap (%)": None if gap is None else gap * 100,
                "Request reference (kW)": s.target_kw,
                "Optimised discharge (kW)": sum(max(0, -float(a)) for a in predicted[0])
                if predicted
                else None,
                "Executed discharge (kW)": sum(data["discharge_kw"][k]),
                "Delivered (kW)": actual,
                "Delivery (kWh)": actual * DT,
                "Cumulative (kWh)": delivered,
                "Remaining obligation (kWh)": obligation,
                "Interval": "—"
                if s.target_kw <= 0
                else "MET"
                if actual >= s.target_kw - EPS
                else "NOT MET",
                "Corrections": ", ".join(
                    label
                    for flag, label in (
                        ("physical_adjustment", "Physical"),
                        ("export_adjustment", "Export policy"),
                    )
                    if step.get(flag)
                )
                or ("None recorded" if step else "Unavailable"),
                "Net electricity cost (£)": raw[k, 0],
                **dict(
                    zip(
                        (
                            "Weighted electricity (£)",
                            "Shortfall penalty (£)",
                            "Degradation (£)",
                            "Terminal penalty (£)",
                        ),
                        costs[k],
                        strict=True,
                    )
                ),
            }
        )
        for i, b in enumerate(s.batteries):
            c, d = data["charge_kw"][k][i], data["discharge_kw"][k][i]
            before, after = data["energy_kwh"][k][i], data["energy_kwh"][k + 1][i]
            grid = data["grid_kw"][k][i]
            a = optimized[i]
            batteries.append(
                {
                    "Step": k,
                    "Household": b.household_id,
                    "SoC before (%)": 100 * before / b.capacity_kwh,
                    "Energy before (kWh)": before,
                    "Optimised charge (kW)": max(0, a) if a is not None else None,
                    "Optimised discharge (kW)": max(0, -a) if a is not None else None,
                    "Requested setpoint (kW)": step.get("requested_kw", [None] * len(s.batteries))[
                        i
                    ],
                    "Executed power (kW)": c - d,
                    "Charged (kWh)": c * DT,
                    "Discharged (kWh)": d * DT,
                    "SoC after (%)": 100 * after / b.capacity_kwh,
                    "Demand (kW)": data["load_kw"][k][i],
                    "Import (kW)": max(0, grid),
                    "Export (kW)": max(0, -grid),
                    "Flexibility (kW)": d - c,
                }
            )
    return portfolio, batteries


def validate_result(result: dict, s: Scenario) -> None:
    if s.replay and result.get("realized") is None:
        raise ValueError("Completed result is missing the historical replay")
    for key in ("planned", "realized"):
        data = result[key]
        if data is None:
            continue
        failed = constraint_violations(s, data)
        if failed:
            raise ValueError("Dispatch violated " + ", ".join(failed))
        c, d, e, load = (
            np.asarray(data[k]) for k in ("charge_kw", "discharge_kw", "energy_kwh", "load_kw")
        )
        expected = evaluate(s, load, c - d, e)
        for field in (
            "flex_kw",
            "delivered_kwh",
            "raw_terms",
            "weighted_terms",
            "objective",
            "shortfall_kwh",
            "import_kwh",
            "export_kwh",
            "remaining_kwh",
        ):
            if not np.allclose(data[field], expected[field], atol=5 * EPS, rtol=0):
                raise ValueError(f"Dispatch {field} failed numerical reconciliation")
        costs = objective_steps(s, data)
        if not np.allclose(costs.sum(axis=0), data["weighted_terms"], atol=5 * EPS, rtol=0):
            raise ValueError("Executed interval costs failed to reconcile")
        saved_ledger = result.get("executed_weighted_costs_gbp")
        if saved_ledger is not None:
            reported = np.asarray(saved_ledger[key])
            if reported.shape != costs.shape or not np.allclose(
                reported, costs, atol=5 * EPS, rtol=0
            ):
                raise ValueError("Saved executed objective ledger failed to reconcile")
        if result["method"] == "MPC":
            trace = result["planned_trace" if key == "planned" else "realized_trace"]
            if len(trace) != s.steps:
                raise ValueError("MPC execution trace is incomplete")
            for k, row in enumerate(trace):
                if (
                    row["step"] != k + 1
                    or row["horizon_steps"] != min(s.prediction_steps, s.steps - k)
                    or not np.allclose(row["applied_kw"], c[k] - d[k], atol=EPS, rtol=0)
                    or not np.allclose(row["energy_before_kwh"], e[k], atol=EPS, rtol=0)
                    or not np.allclose(row["energy_after_kwh"], e[k + 1], atol=EPS, rtol=0)
                ):
                    raise ValueError("MPC step record failed trajectory reconciliation")
