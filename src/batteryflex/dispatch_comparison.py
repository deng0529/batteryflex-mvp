"""Compare two trajectories against the same uncontrolled-demand definition."""

import numpy as np

from batteryflex.dispatch import DT, EPS, Scenario


def replay_evidence(result: dict, s: Scenario) -> dict:
    """Attribute event differences to recorded actions and bound observations."""
    planned, replay = result["planned"], result["realized"]
    event = list(s.event_steps)
    p_action = np.asarray(planned["charge_kw"]) - np.asarray(planned["discharge_kw"])
    r_action = np.asarray(replay["charge_kw"]) - np.asarray(replay["discharge_kw"])
    load_error = np.asarray(replay["load_kw"]) - np.asarray(planned["load_kw"])
    changed = np.any(np.abs(r_action - p_action) > EPS, axis=1)
    trace = {row["step"] - 1: row for row in result["realized_trace"] if "applied_kw" in row}
    complete = all(k in trace and "requested_kw" in trace[k] for k in event)
    if complete:
        requested = np.asarray([trace[k]["requested_kw"] for k in event])
        request_effect = float((p_action[event] - requested).sum() * DT)
        correction_effect = float((requested - r_action[event]).sum() * DT)
    else:
        request_effect = correction_effect = None
    limits = {
        "export cap": 0,
        "import cap": 0,
        "discharge rating": 0,
        "stored energy floor": 0,
    }
    for k in event:
        if replay["flex_kw"][k] >= s.target_kw - EPS:
            continue
        for i, battery in enumerate(s.batteries):
            if not battery.participating:
                continue
            grid = replay["grid_kw"][k][i]
            exp_cap = battery.export_limit_kw
            if exp_cap is not None and abs(grid + exp_cap) <= EPS:
                limits["export cap"] += 1
            if s.import_limit_kw is not None and abs(grid - s.import_limit_kw) <= EPS:
                limits["import cap"] += 1
            discharge = replay["discharge_kw"][k][i]
            if discharge > EPS and abs(discharge - battery.discharge_limit_kw) <= EPS:
                limits["discharge rating"] += 1
            floor = (
                battery.min_soc
                if result["method"] != "RBC"
                else max(battery.min_soc, s.reserve_soc)
            )
            if replay["energy_kwh"][k + 1][i] <= floor * battery.capacity_kwh + EPS:
                limits["stored energy floor"] += 1
    return {
        "load_mae_kw": float(np.abs(load_error[event]).mean()),
        "load_delta_kwh": float(load_error[event].sum() * DT),
        "changed_intervals": int(changed[event].sum()),
        "day_changed_intervals": int(changed.sum()),
        "day_load_delta_kwh": float(load_error.sum() * DT),
        "day_physical_intervals": sum(
            bool(row.get("physical_adjustment")) for row in trace.values()
        ),
        "day_export_intervals": sum(bool(row.get("export_adjustment")) for row in trace.values()),
        "request_effect_kwh": request_effect,
        "correction_effect_kwh": correction_effect,
        "physical_intervals": sum(bool(trace.get(k, {}).get("physical_adjustment")) for k in event),
        "export_intervals": sum(bool(trace.get(k, {}).get("export_adjustment")) for k in event),
        "event_boundaries": {name: count for name, count in limits.items() if count},
    }


def explain_replay(result: dict, evidence: dict) -> str:
    changed = evidence["changed_intervals"]
    if not changed:
        return (
            "Event battery actions matched. The uncontrolled-load baseline cancels the load "
            "term, so forecast error did not change flexibility. A different load can still "
            "change the split between electricity used at home and grid export."
        )
    requested, correction = evidence["request_effect_kwh"], evidence["correction_effect_kwh"]
    if requested is None or correction is None:
        return (
            f"Applied actions differed in {changed} event intervals. The available execution "
            "trace does not establish the cause of those action changes."
        )
    policy = {
        "RBC": "current-load rules and their evolving battery state",
        "MPC": "rolling updates using current load and battery state",
        "MILP": "the day-ahead schedule",
    }[result["method"]]
    requested = 0.0 if abs(requested) <= EPS else requested
    correction = 0.0 if abs(correction) <= EPS else correction
    return (
        f"Applied actions differed in {changed} event intervals. Requests from {policy} "
        f"accounted for {requested:+.3f} kWh relative to the applied forecast plan. "
        f"Replay adjustments accounted for {correction:+.3f} kWh "
        f"({evidence['physical_intervals']} intervals with physical corrections, "
        f"{evidence['export_intervals']} with export-policy corrections). "
        "This decomposition measures action effects. Current load and carried battery state "
        "can interact, so it does not isolate a forecast-error effect."
    )
