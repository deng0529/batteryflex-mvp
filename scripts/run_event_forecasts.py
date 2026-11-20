"""Explicit event model request: load exact matches or fit/persist missing versions."""

import argparse
from pathlib import Path

from batteryflex.forecast_contracts import ForecastModelConfig
from batteryflex.neso_manifest import load_selection
from batteryflex.storage.database import migrate, verify_schema
from batteryflex.storage.event_forecasts import EventForecasts, publish_history
from batteryflex.storage.settings import Settings, connect

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--migrate", action="store_true", help="Explicitly apply versioned Task 05D migrations"
    )
    parser.add_argument(
        "--history", type=Path, help="Explicitly publish a prepared immutable event dataset"
    )
    parser.add_argument(
        "--event", help="Existing internal BatteryFlex scenario ID (not an official NESO ID)"
    )
    args = parser.parse_args()
    repo = connect(Settings.load())
    repo.require_owner()
    if args.migrate:
        migrate(repo.db)
    verify_schema(repo.db)
    if args.history:
        print("Event dataset:", publish_history(repo, args.history))
    events, samples, _ = load_selection()
    if args.event:
        events = [e for e in events if e["internal_scenario_id"] == args.event]
        if not events:
            raise ValueError("Unknown reviewed event")
    configs = (ForecastModelConfig("Ridge Regression"), ForecastModelConfig("LightGBM"))
    for event in events:
        service = EventForecasts(repo)
        result = service.run(event, samples[event["resource_id"]], configs)
        print(
            event["internal_scenario_id"],
            {"trained": service.trained, "reused": service.reused},
            flush=True,
        )
