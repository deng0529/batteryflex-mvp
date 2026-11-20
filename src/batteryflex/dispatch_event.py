"""Qualification and reproducible records for standard event-window experiments."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta
from time import perf_counter

import numpy as np

from batteryflex.battery import BatteryConfig
from batteryflex.defaults import SimulationDefaults, load_defaults, portfolio_defaults
from batteryflex.dispatch import DT, EPS, Scenario, _limits, _solve, export_batteries
from batteryflex.dispatch_dashboard import diagnose_interval, event_outcome
from batteryflex.dispatch_evaluation import objective_steps
from batteryflex.portfolio import HOUSEHOLDS

EVENT_START_SOC = dict(zip(HOUSEHOLDS, portfolio_defaults().event_start_soc, strict=True))
EXPLANATION_VERSION = 2


def event_start_batteries(batteries: tuple[BatteryConfig, ...]) -> tuple[BatteryConfig, ...]:
    # Keep custom configurations valid and visible in the editor.
    return tuple(
        replace(b, initial_soc=EVENT_START_SOC[b.household_id])
        if b.min_soc <= EVENT_START_SOC[b.household_id] <= b.max_soc
        else b
        for b in batteries
    )


def standard_scenario(batteries: tuple[BatteryConfig, ...], steps: tuple[int, ...]) -> Scenario:
    """Build the published event-only defaults, before session overrides."""
    defaults = load_defaults("simulation.yaml", SimulationDefaults)
    return Scenario(
        export_batteries(batteries),
        steps,
        defaults.target_kw,
        import_price=defaults.import_price,
        export_price=defaults.export_price,
        reserve_soc=defaults.reserve_soc,
        target_soc=defaults.target_soc,
        degradation_price=defaults.degradation_price,
        terminal_price=defaults.terminal_price,
        weights=defaults.weights,
        prediction_steps=defaults.prediction_steps,
        time_limit=defaults.time_limit,
        gap=defaults.gap,
        simulation_mode=defaults.mode,
        target_export_only=True,
    )


def resources(s: Scenario) -> dict:
    capacity, minimum, _, _, power, _, efficiency, _ = _limits(s)
    initial = capacity * [b.initial_soc for b in s.batteries]
    active = np.asarray([b.participating for b in s.batteries])
    floor = np.maximum(minimum, capacity * s.reserve_soc)
    available = float((np.maximum(0, initial - minimum) * efficiency * active).sum())
    usable = float((np.maximum(0, initial - floor) * efficiency * active).sum())
    requested = s.target_kw * s.steps * DT
    return {
        "capacity_kwh": float(capacity.sum()),
        "initial_kwh": float(initial.sum()),
        "reserved_kwh": float(minimum.sum()),
        "available_kwh": available,
        "usable_at_final_reserve_kwh": usable,
        "power_kw": float(power.sum()),
        "requested_kwh": requested,
        "margin_kwh": available - requested,
    }


def qualify(s: Scenario, forecast: np.ndarray) -> dict:
    start = perf_counter()
    metrics = resources(s)
    if forecast.shape != (s.steps, len(s.batteries)) or not (
        np.isfinite(forecast).all() and (forecast >= 0).all()
    ):
        raise ValueError("Qualification requires complete event-window forecasts")
    _, _, _, _, rating, _, _, export = _limits(s)
    forecast_caps = np.minimum(forecast + export, rating).sum(axis=1)
    metrics["minimum_forecast_discharge_headroom_kw"] = float(forecast_caps.min())
    metrics["solver_seconds"] = 0.0
    if (
        metrics["usable_at_final_reserve_kwh"] < metrics["requested_kwh"] - EPS
        or metrics["power_kw"] < s.target_kw - EPS
    ):
        metrics.update(
            status="INFEASIBLE", reason="Usable energy or rated discharge power is insufficient."
        )
    else:
        initial = np.array([b.capacity_kwh * b.initial_soc for b in s.batteries])
        _, proof = _solve(s, forecast, initial, 0, 0.0, qualification=True)
        metrics.update(proof)
        if proof["status"] == "QUALIFIED":
            metrics["reason"] = "Zero-shortfall delivery confirmed under forecast demand."
        elif s.target_type == "interval" and forecast_caps.min() < s.target_kw - EPS:
            metrics["reason"] = (
                f"Forecast demand, export caps and ratings allow at most "
                f"{forecast_caps.min():.2f} kW in a constrained half-hour."
            )
        else:
            metrics["reason"] = (
                "Zero-shortfall delivery under battery, reserve and forecast grid limits "
                "was not confirmed."
            )
    return {**metrics, "qualification_seconds": perf_counter() - start}


def event_evidence(result: dict, s: Scenario, reference: dict) -> dict:
    """Regenerate presentation evidence using stored numerical results only."""
    origin = datetime.fromisoformat(reference["original_event_start"])
    explanations = {}
    records = {}
    for key, trace_key in (("planned", "planned_trace"), ("realized", "realized_trace")):
        data = result.get(key)
        if data is None:
            continue
        costs = objective_steps(s, data)
        shortfall = objective_steps(s, data, weighted=False)[:, 1]
        outcome = event_outcome(s, data)
        elapsed = 0.0
        rows = []
        for k, entry in enumerate(row for row in result[trace_key] if "applied_kw" in row):
            grid = np.asarray(data["grid_kw"][k])
            running = float(costs[k, :3].sum())
            elapsed += running
            gap = max(0.0, float(data["request_kw"][k] - data["flex_kw"][k]))
            rows.append(
                {
                    **entry,
                    "control_index": k,
                    "timestamp": (origin + timedelta(hours=DT * k)).isoformat(),
                    "request_kw": data["request_kw"][k],
                    "delivery_kw": data["flex_kw"][k],
                    "power_shortfall_kw": gap,
                    "interval_reference_gap_kwh": gap * DT,
                    "executed_shortfall_kwh": float(shortfall[k]),
                    "weighted_interval_costs": costs[k].tolist(),
                    "stage_cost": running,
                    "cumulative_running_cost": elapsed,
                    "forecast_load_kw": result["planned"]["load_kw"][k],
                    "actual_load_kw": result["realized"]["load_kw"][k]
                    if result["realized"]
                    else None,
                    "charge_kw": data["charge_kw"][k],
                    "discharge_kw": data["discharge_kw"][k],
                    "import_kw": np.maximum(grid, 0).tolist(),
                    "export_kw": np.maximum(-grid, 0).tolist(),
                    "soc_before": [
                        v / b.capacity_kwh
                        for v, b in zip(data["energy_kwh"][k], s.batteries, strict=True)
                    ],
                    "soc_after": [
                        v / b.capacity_kwh
                        for v, b in zip(data["energy_kwh"][k + 1], s.batteries, strict=True)
                    ],
                    "participating": [b.participating for b in s.batteries],
                    "decision": entry.get(
                        "rule", "Solve the remaining forecast and execute the first action"
                    ),
                }
            )
        records[key] = rows
        active_limits = [name for name, count in data["binding_counts"].items() if count]
        leading = sorted(data["households"], key=lambda h: -h["event_flex_kwh"])[:2]
        contributions = ", ".join(
            f"{home['household']} {home['event_flex_kwh']:.3f} kWh" for home in leading
        )
        demand_difference = float(
            np.abs(np.asarray(data["load_kw"]) - np.asarray(result["planned"]["load_kw"])).mean()
        )
        explanations[key] = {
            "status": outcome.status,
            "summary": f"{outcome.status}. Delivered {outcome.delivered_kwh:.3f} of "
            f"{outcome.requested_kwh:.3f} kWh with {outcome.shortfall_kwh:.3f} kWh shortfall.",
            "diagnostics": {
                str(k): asdict(diagnose_interval(s, result, key, k, outcome.requested_kw[k]))
                for k in outcome.failed_steps
            },
            "details": (
                f"Leading net contributions: {contributions}. "
                f"Charged {data['charged_kwh']:.3f} kWh and discharged "
                f"{data['discharged_kwh']:.3f} kWh. Mean absolute demand difference "
                f"from the forecast was {demand_difference:.3f} kW per home and interval."
            ),
            "active_limits": active_limits,
        }
    return {
        "execution_records": records,
        "event_record_schema_version": 1,
        "explanation_version": EXPLANATION_VERSION,
        "explanations": explanations,
    }
