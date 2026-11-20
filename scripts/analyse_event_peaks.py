"""Export read-only peak diagnostics for saved event forecasts; never train or migrate."""

import argparse
from pathlib import Path

import pandas as pd

from batteryflex.forecast_contracts import METHODS, ForecastModelConfig
from batteryflex.neso_manifest import load_selection
from batteryflex.peak_analysis import peak_diagnostics, training_context
from batteryflex.storage.event_forecasts import EventForecasts, load_history
from batteryflex.storage.settings import Settings, connect


def export(output: Path) -> None:
    repo = connect(Settings.load())
    frame, _, _ = load_history(repo)
    service = EventForecasts(repo)
    peaks, dates, households = [], [], []
    events, _, _ = load_selection()
    for event in events:
        results = [service.lookup(event, ForecastModelConfig(method)) for method in METHODS]
        if any(r is None for r in results):
            raise ValueError(
                f"Saved forecasts unavailable for {event['delivery_date']}; no training"
            )
        saved = [r for r in results if r is not None]
        ranges, details, thresholds = training_context(frame, saved[0]["artifact"])
        predictions = pd.concat([r["predictions"] for r in saved], ignore_index=True)
        diagnostics = peak_diagnostics(predictions, thresholds)
        versions = {r["record"]["algorithm"]: r["record"]["version"] for r in saved}
        peaks.append(
            diagnostics.assign(
                event=event["delivery_date"], model_version=diagnostics.method.map(versions)
            )
        )
        dates.append(ranges.assign(event=event["delivery_date"]))
        households.append(details.assign(event=event["delivery_date"]))
    output.mkdir(parents=True, exist_ok=True)
    for name, frames in (
        ("peak-diagnostics", peaks),
        ("dataset-ranges", dates),
        ("household-ranges", households),
    ):
        pd.concat(frames, ignore_index=True).to_csv(output / f"{name}.csv", index=False)
    print("Saved forecasts analysed; no fitting, migrations, activation or cloud writes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/event-peaks"))
    export(parser.parse_args().output)
