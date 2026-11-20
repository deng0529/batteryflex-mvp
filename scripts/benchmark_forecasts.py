"""Reproduce Task 05B measured-data benchmark without saving or activating models."""

import hashlib
import json
from pathlib import Path

from batteryflex.forecast_contracts import METHODS, ForecastDatasetConfig, ForecastModelConfig
from batteryflex.forecast_training import run_models
from batteryflex.ui.lcl_lab import load_prepared

root = Path(__file__).resolve().parents[1]
prepared = root / "data/lcl/prepared"
frame, _, _, _, audit = load_prepared(str(prepared), (prepared / "audit.json").stat().st_mtime_ns)
before = {
    str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (root / "data").rglob("*")
    if p.is_file()
}
run = run_models(
    frame,
    tuple(ForecastModelConfig(m) for m in METHODS),
    ForecastDatasetConfig(),
    audit["artifacts"]["observations.parquet"],
)
out = root / "outputs/task05b"
out.mkdir(parents=True, exist_ok=True)
run.metrics.to_csv(out / "metrics.csv", index=False)
run.counts.to_csv(out / "counts.csv", index=False)
run.predictions.to_parquet(out / "predictions.parquet", index=False)
assert before == {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in before}
(out / "source-hashes.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
print(run.counts.to_string(index=False))
print(run.metrics[run.metrics.partition == "testing"].to_string(index=False))
print(f"All {len(before)} current data hashes unchanged; prepared audit verified.")
