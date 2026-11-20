"""Resolve immutable Task 05 inputs and store Task 06 runs through existing Turso/R2 IO."""

import json
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from uuid import uuid4

import numpy as np
import pandas as pd

from batteryflex.battery import BatteryConfig
from batteryflex.dispatch import DT, METHODS, STEPS, Scenario, run_dispatch
from batteryflex.dispatch_evaluation import objective_steps, validate_result
from batteryflex.dispatch_event import event_evidence, qualify
from batteryflex.event_engine import replay_intervals
from batteryflex.forecast_training import history
from batteryflex.neso import Sample
from batteryflex.portfolio import HOUSEHOLDS, Portfolio
from batteryflex.portfolio_storage import import_configuration
from batteryflex.storage.database import query
from batteryflex.storage.event_forecasts import load_history
from batteryflex.storage.forecast_resolver import ResolvedEventForecast, resolve_event_forecast
from batteryflex.storage.objects import ObjectReference, sha256
from batteryflex.storage.repository import Repository, canonical, object_statement

NAMESPACE = "task06.dispatch.v1."
REPAIR_NAMESPACE = "task06.dispatch.repair."
RESULT_SCHEMA = 2
LEGACY_PROTOCOL = "causal-replay-v1"
PROTOCOL = LEGACY_PROTOCOL
# Bump for numerical implementation changes without changing the discovery namespace.
ENGINE_VERSION = NAMESPACE
ATTEMPT_NAMESPACE = "task06.dispatch.attempt."
STAGE_NAMESPACE = "task06.dispatch.stage."
RESULT_KIND = "task06-dispatch-v2"


def saved_portfolio(repo: Repository) -> tuple[str, Portfolio]:
    identity = repo.setting("portfolio")
    rows = query(repo.db, "SELECT config_json FROM portfolios WHERE id=?", (identity,))
    if not rows:
        raise ValueError("Saved database battery portfolio is missing")
    return identity, import_configuration(rows[0]["config_json"], reviewed_five=True)


def resolve_inputs(
    repo: Repository,
    event: dict,
    samples: dict[str, Sample],
    algorithm: str,
) -> tuple[ResolvedEventForecast, dict, pd.DatetimeIndex, tuple[int, ...], np.ndarray]:
    event_id = event["internal_scenario_id"]
    forecast = resolve_event_forecast(repo, event_id, algorithm=algorithm)
    artifacts = query(
        repo.db,
        "SELECT fingerprint,artifact_id,predictions_id FROM event_forecast_models "
        "WHERE request_id=? AND version=?",
        (forecast.request_id, forecast.model_version),
    )
    if len(artifacts) != 1:
        raise ValueError("Exact forecast artifact is unavailable")
    reference = {
        **artifacts[0],
        "event_id": event_id,
        "dataset_id": forecast.dataset_id,
        "request_id": forecast.request_id,
        "model_version": forecast.model_version,
        "algorithm": algorithm,
        "replay_date": str(forecast.replay_date),
        "forecast_origin": forecast.forecast_origin.isoformat(),
        "original_event_date": str(event["delivery_date"]),
        "original_event_start": event["start_utc"],
        "original_event_end": event["end_utc"],
        "event_source_hash": event["source_records_sha256"],
    }
    timeline = pd.date_range(forecast.forecast_origin, periods=STEPS, freq="30min")
    positions = timeline.get_indexer(replay_intervals(event, samples[event["resource_id"]]))
    if (positions < 0).any():
        raise ValueError("Event intervals are outside the saved forecast horizon")
    steps = tuple(sorted(int(k) for k in positions))
    prediction = forecast.household_forecasts.pivot(
        index="interval_start", columns="household", values="prediction"
    ).reindex(index=timeline, columns=list(HOUSEHOLDS))
    return forecast, reference, timeline, steps, prediction.to_numpy(dtype=float)


def replay_load(repo: Repository, dataset_id: str, timeline: pd.DatetimeIndex) -> np.ndarray:
    frame, _, _ = load_history(repo, dataset_id)
    return np.column_stack(
        [
            history(frame, household).reindex(timeline).to_numpy(dtype=float)
            for household in HOUSEHOLDS
        ]
    )


def _legacy_identity(scenario: Scenario, method: str, reference: dict) -> tuple[str, dict]:
    settings = asdict(scenario)
    if scenario.simulation_mode == "FULL_DAY":
        settings.pop("simulation_mode")
    if not scenario.target_export_only:
        # Keep previous scenario IDs addressable through the existing engine namespace.
        settings.pop("target_export_only")
    # Streamlit may return a decimal representation of an integer-valued input.
    settings["target_kw"] = _number(scenario.target_kw)
    settings["time_limit"] = _number(scenario.time_limit)
    settings["weights"] = [_number(weight) for weight in scenario.weights]
    payload = {
        "engine": NAMESPACE,
        "solver": version("scipy") if method != "RBC" else None,
        "method": method,
        "inputs": reference,
        "scenario": settings,
        "baseline": "same-scenario uncontrolled household load",
    }
    return sha256(canonical(payload).encode()), payload


def _number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else float(value)


def _stable(value):
    if isinstance(value, float):
        return 0 if value == 0 else _number(value)
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_stable(v) for v in value]
    return value


def _identity(scenario: Scenario, method: str, reference: dict) -> tuple[str, dict]:
    _, previous = _legacy_identity(scenario, method, reference)
    payload = canonical_payload(
        {
            **previous,
            "engine": ENGINE_VERSION,
            "protocol": PROTOCOL,
            "evaluation_steps": scenario.steps,
            "forecast_steps": STEPS,
            "step_hours": DT,
        }
    )
    if scenario.simulation_mode == "EVENT_ONLY":
        payload.update(
            engine="event-window-v1",
            protocol="forecast-at-boundary-v1",
            experiment_id="STANDARD",
            simulation_mode="EVENT_ONLY",
        )
    return sha256(canonical(payload).encode()), payload


def canonical_payload(source: dict) -> dict:
    inputs = dict(source["inputs"])
    for field in ("forecast_origin", "original_event_start", "original_event_end"):
        if field in inputs:
            stamp = datetime.fromisoformat(inputs[field])
            if stamp.tzinfo is None:
                raise ValueError("Dispatch provenance timestamp lacks a timezone")
            inputs[field] = stamp.astimezone(UTC).isoformat()
    scenario = {"target_export_only": False, **source["scenario"]}
    return _stable(
        {
            "protocol": LEGACY_PROTOCOL,
            "evaluation_steps": 48,
            "forecast_steps": 48,
            "step_hours": 0.5,
            "units": {"power": "kW", "energy": "kWh", "currency": "GBP"},
            "fingerprint_version": 2,
            **source,
            "inputs": inputs,
            "scenario": scenario,
        }
    )


def comparison_payload(provenance: dict) -> dict:
    payload = canonical_payload(provenance)
    payload.pop("method")
    payload.pop("solver", None)
    for field in ("event_soc", "precharge_price", "prediction_steps", "time_limit", "gap"):
        payload["scenario"].pop(field, None)
    for field in ("portfolio_id", "assumed_export_caps_kw"):
        payload["inputs"].pop(field, None)
    return payload


def comparison_identity(provenance: dict) -> str:
    return sha256(canonical(comparison_payload(provenance)).encode())


def scenario_from_result(result: dict) -> Scenario:
    config = dict(result["provenance"]["scenario"])
    config["batteries"] = tuple(BatteryConfig(**b) for b in config["batteries"])
    config["event_steps"] = tuple(config["event_steps"])
    config["weights"] = tuple(config["weights"])
    return Scenario(**config)


def _load_record(repo: Repository, row: dict, *, verify_remote: bool = False) -> dict:
    record = json.loads(row["value_json"])
    if record.get("status", "COMPLETED") != "COMPLETED":
        raise ValueError("Simulation index does not reference a completed run")
    result = json.loads(
        repo.objects.get(repo.reference(record["object_id"]), verify_remote=verify_remote)
    )
    schema = result.get("schema_version", 1)
    if schema not in (1, RESULT_SCHEMA) or record.get("schema_version", schema) != schema:
        raise ValueError("Saved optimisation schema is incompatible")
    if schema == RESULT_SCHEMA and result.get("status") != "COMPLETED":
        raise ValueError("Saved bundle does not contain a completed simulation")
    identity = row["name"].removeprefix(NAMESPACE)
    if row["name"].startswith(REPAIR_NAMESPACE):
        identity = row["name"].removeprefix(REPAIR_NAMESPACE).split(".")[0]
    if (
        result["fingerprint"] != identity
        or result["method"] not in METHODS
        or result["method"] != record["method"]
        or result["method"] != result["provenance"]["method"]
        or sha256(canonical(result["provenance"]).encode()) != identity
    ):
        raise ValueError("Saved optimisation provenance failed verification")
    return result


def _verify_complete(result: dict) -> None:
    s = scenario_from_result(result)
    validate_result(result, s)
    if s.simulation_mode != "EVENT_ONLY":
        return
    if result["provenance"].get("experiment_id") != "STANDARD":
        raise ValueError("Unsupported event experiment")
    for slot, name in (("planned", "planned_trace"), ("realized", "realized_trace")):
        data = result.get(slot)
        if data is None:
            raise ValueError("Event result must contain both trajectories")
        applied = [step for step in result[name] if "applied_kw" in step]
        if [step["step"] for step in applied] != list(range(1, s.steps + 1)):
            raise ValueError("Event execution trace is incomplete")
        if not np.allclose(
            [step["applied_kw"] for step in applied],
            np.asarray(data["charge_kw"]) - np.asarray(data["discharge_kw"]),
            atol=1e-6,
            rtol=0,
        ):
            raise ValueError("Event execution trace does not match the trajectory")


def discover_runs(
    repo: Repository, *, standard_only: bool = False, issues: list[dict] | None = None
) -> tuple[list[dict], int]:
    """Read completed result objects only. Prefer the latest valid repair per identity."""
    rows = query(
        repo.db,
        "SELECT name,value_json FROM system_settings WHERE name LIKE ? OR name LIKE ? "
        "ORDER BY name DESC",
        (NAMESPACE + "%", REPAIR_NAMESPACE + "%"),
    )
    results: dict[str, dict] = {}
    invalid = 0
    for row in rows:
        index = {}
        try:
            if standard_only:
                candidate = json.loads(row["value_json"])
                if not isinstance(candidate, dict):
                    raise ValueError("Invalid dispatch index")
                index = candidate
                # Schema 1 full-day indexes predate the scenario metadata.
                if set(index) == {"inputs", "method", "object_id"}:
                    continue
                if not isinstance(index.get("scenario"), dict):
                    raise ValueError("Invalid dispatch index")
                if index.get("scenario", {}).get("simulation_mode") != "EVENT_ONLY":
                    continue
            result = _load_record(repo, row, verify_remote=standard_only)
            if standard_only:
                _verify_complete(result)
            results.setdefault(result["fingerprint"], result)
        except (ValueError, KeyError, TypeError, OSError, RuntimeError):
            invalid += 1
            if issues is not None:
                issues.append(index)
    return list(results.values()), invalid


def _lookup(
    repo: Repository, identity: str, legacy: str, payload: dict
) -> tuple[dict | None, bool]:
    rows = query(
        repo.db,
        "SELECT name,value_json FROM system_settings WHERE name IN (?,?) OR name LIKE ? "
        "ORDER BY name DESC",
        (NAMESPACE + identity, NAMESPACE + legacy, REPAIR_NAMESPACE + identity + ".%"),
    )
    corrupted = False
    # Prefer repaired/current runs, even when a legacy candidate also exists.
    rows.sort(
        key=lambda r: r["name"].startswith(REPAIR_NAMESPACE) or r["name"] == NAMESPACE + identity,
        reverse=True,
    )
    for row in rows:
        try:
            result = _load_record(repo, row, verify_remote=True)
            if canonical_payload(result["provenance"]) != payload:
                raise ValueError("Saved optimisation inputs differ")
            _verify_complete(result)
        except (ValueError, KeyError, TypeError, OSError):
            corrupted |= row["name"] == NAMESPACE + identity
        else:
            return result, corrupted
    return None, corrupted


def load_saved_run(repo: Repository, s: Scenario, method: str, reference: dict) -> dict | None:
    """Look for the exact persisted scenario without acquiring a lease or running it."""
    identity, payload = _identity(s, method, reference)
    legacy, _ = _legacy_identity(s, method, reference)
    return _lookup(repo, identity, legacy, payload)[0]


def _staged_result(
    repo: Repository, stage: str, identity: str, payload: dict, s: Scenario
) -> tuple[dict, ObjectReference] | None:
    rows = query(repo.db, "SELECT value_json FROM system_settings WHERE name=?", (stage,))
    if not rows:
        return None
    try:
        ref = ObjectReference(**json.loads(rows[0]["value_json"])["object"])
        if ref.kind != RESULT_KIND:
            return None
        result = json.loads(repo.objects.get(ref, verify_remote=True))
        if (
            result["fingerprint"] != identity
            or result["schema_version"] != RESULT_SCHEMA
            or result["status"] != "COMPLETED"
            or result["method"] != payload["method"]
            or result["provenance"] != payload
        ):
            return None
        validate_result(result, s)
        return result, ref
    except (ValueError, KeyError, TypeError, OSError):
        return None


def saved_or_run(
    repo: Repository,
    s: Scenario,
    method: str,
    reference: dict,
    forecast: np.ndarray,
    actual: np.ndarray | Callable[[], np.ndarray] | None,
) -> tuple[dict, bool]:
    """Return a verified result or publish a complete immutable bundle under a lease."""
    identity, payload = _identity(s, method, reference)
    legacy, _ = _legacy_identity(s, method, reference)
    key = NAMESPACE + identity
    saved, _ = _lookup(repo, identity, legacy, payload)
    if saved is not None:
        return saved, True
    repo.require_owner()
    owner = uuid4().hex
    stamp = int(time.time())
    lifetime = int(s.time_limit * s.steps * 2 + 300)
    lease = query(
        repo.db,
        "INSERT INTO model_leases VALUES(?,?,?) ON CONFLICT(fingerprint) "
        "DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at "
        "WHERE model_leases.expires_at<? RETURNING owner",
        (key, owner, stamp + lifetime, stamp),
    )
    if not lease:
        saved, _ = _lookup(repo, identity, legacy, payload)
        if saved is not None:
            return saved, True
        raise ValueError("This scenario is already running. Retry to load the saved result.")
    try:
        saved, replace_reference = _lookup(repo, identity, legacy, payload)
        if saved is not None:
            return saved, True
        stage = STAGE_NAMESPACE + identity
        staged = _staged_result(repo, stage, identity, payload, s)
        if staged is not None:
            result, ref = staged
            created = result["created_at"]
        else:
            qualification = qualify(s, forecast) if s.simulation_mode == "EVENT_ONLY" else None
            if qualification is not None and qualification["status"] != "QUALIFIED":
                raise ValueError(f"Portfolio {qualification['status']}. {qualification['reason']}")
            replay = actual if isinstance(actual, np.ndarray) or actual is None else actual()
            result = run_dispatch(s, method, forecast, replay)
            if qualification is not None:
                result["qualification"] = qualification
                result.update(event_evidence(result, s, reference))
            validate_result(result, s)
            created = datetime.now(UTC).isoformat(timespec="microseconds")
            result.update(
                fingerprint=identity,
                provenance=payload,
                schema_version=RESULT_SCHEMA,
                status="COMPLETED",
                created_at=created,
            )
            if method == "MPC":
                result["executed_weighted_costs_gbp"] = {
                    slot: objective_steps(s, result[slot]).tolist()
                    for slot in ("planned", "realized")
                    if result[slot] is not None
                }
            body = canonical(result).encode()
            digest = sha256(body)
            expected = ObjectReference(digest, f"objects/{digest}", len(body), RESULT_KIND)
            reserved = query(
                repo.db,
                "INSERT INTO system_settings(name,value_json) SELECT ?,? WHERE EXISTS "
                "(SELECT 1 FROM model_leases WHERE fingerprint=? AND owner=?) "
                "ON CONFLICT(name) DO UPDATE SET value_json=excluded.value_json RETURNING name",
                (stage, canonical({"status": "PENDING", "object": asdict(expected)}), key, owner),
            )
            if not reserved:
                raise ValueError("Optimisation lease expired before result upload")
            ref = repo.objects.put(body, RESULT_KIND)
        indexed = canonical(
            {
                "object_id": ref.sha256,
                "inputs": payload["inputs"],
                "scenario": payload["scenario"],
                "method": method,
                "schema_version": RESULT_SCHEMA,
                "status": "COMPLETED",
                "created_at": created,
                "solver_status": result["solver_status"],
                "runtime_seconds": result["runtime_seconds"],
                "comparison": comparison_identity(payload),
                "summary": {
                    slot: {
                        field: result[slot][field]
                        for field in (
                            "objective",
                            "weighted_terms",
                            "delivered_kwh",
                            "shortfall_kwh",
                            "cost_gbp",
                            "remaining_kwh",
                            "status",
                        )
                    }
                    for slot in ("planned", "realized")
                    if result[slot] is not None
                },
            }
        )
        index_key = REPAIR_NAMESPACE + identity + "." + created if replace_reference else key
        repo.db.batch(
            [
                object_statement(ref),
                (
                    "INSERT INTO system_settings(name,value_json) SELECT ?,? WHERE EXISTS "
                    "(SELECT 1 FROM model_leases WHERE fingerprint=? AND owner=?) "
                    "ON CONFLICT(name) DO NOTHING",
                    (index_key, indexed, key, owner),
                ),
                (
                    "DELETE FROM system_settings WHERE name=? AND EXISTS "
                    "(SELECT 1 FROM model_leases WHERE fingerprint=? AND owner=?)",
                    (stage, key, owner),
                ),
            ]
        )
        saved, _ = _lookup(repo, identity, legacy, payload)
        if saved is None:
            raise ValueError("Completed optimisation could not be registered")
        return saved, staged is not None or saved.get("created_at") != created
    except (ValueError, OSError, RuntimeError) as exc:
        with suppress(ValueError, OSError):
            query(
                repo.db,
                "INSERT INTO system_settings(name,value_json) VALUES(?,?) "
                "ON CONFLICT(name) DO NOTHING",
                (
                    ATTEMPT_NAMESPACE + owner,
                    canonical(
                        {
                            "status": "FAILED",
                            "fingerprint": identity,
                            "method": method,
                            "created_at": datetime.now(UTC).isoformat(),
                            "error_type": type(exc).__name__,
                        }
                    ),
                ),
            )
        raise
    finally:
        with suppress(ValueError, OSError):
            query(repo.db, "DELETE FROM model_leases WHERE fingerprint=? AND owner=?", (key, owner))
