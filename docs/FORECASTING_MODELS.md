> Task 05C supersedes the explicit Save Model UI and local-only registry workflow described
> in this historical Task 05B report. Models/results now persist automatically on Run Models,
> with exact configuration reuse, SQL active references and R2 artifacts when configured.
> Numerical algorithms and benchmark results below remain unchanged. See [storage architecture](STORAGE.md).

# Task 05B — measured forecasting implementation and benchmark

Date: 18 November 2026. Branch: `codex/task05b-household-forecasting`.
Forecasting only; dispatch, optimisation, settlement and simulation execution remain disabled.

## Implementation and dependencies

- `forecast_training.py`: shared origin-safe features, daily examples, household estimators,
  aligned predictions, metrics and complete-member portfolio aggregation.
- `forecast_persistence.py`: verified JSON/native-text five-household bundles, immutable versions,
  serialized write lifecycle, explicit activation and algorithm-independent `SavedForecaster`.
- `forecast_contracts.py`: compatible optional evaluation details in metadata.
- `ui/forecasting.py`, `ui/forecast_results.py`: multiple selection, Run Models, six forecast
  charts, daily and full-partition metrics, save/activate within A4; separate A5 removed.
- `ui/planned.py`: forecasting status wording; existing three tabs and disabled simulation preserved.
- `scripts/benchmark_forecasts.py`: repeatable measured-data benchmark, no save/activation.
- Tests: numerical/leakage/persistence acceptance and updated UI/regression tests.
- `pyproject.toml`: scikit-learn >=1.6,<2 and LightGBM >=4.6,<5. Verified versions:
  scikit-learn 1.9.1, LightGBM 4.7.0; dependency installs include scipy 1.18.1,
  joblib 1.6.0, threadpoolctl 3.8.0 and cloudpickle 3.1.2. No pickle loading is used.

## Features, training and evaluation

Target is measured half-hour kWh / 0.5 = average kW. Original source files/timestamps/hashes
are unchanged. Fixed GMT, interval START indexed; midnight origin predicts 00:00–24:00 in 48 steps.
Each home has its own Ridge and LightGBM estimator. No household identifier is needed.

Ordered `load-origin-v1` features: target half-hour sine/cosine, weekday, weekend, horizon step
1–48, corresponding previous-day and previous-week load, previous-day mean/std, previous-week
mean/std (population standard deviation). All measured features use intervals ending <= origin.
No target-day measured value is read. Calendar values are known in advance.

Only complete seven-day historical windows and complete 48-step target days are admitted.
No interpolation, forward fill, zero fill or invented warm-up is used. All algorithms, including
Seasonal Naive, share this conservative admission policy for fair paired metrics. The baseline
itself uses only the previous day. No reduced feature set was needed.

Training labels: Jan 1–Feb 28; validation labels: Mar 1–15; test labels: Mar 16–31, 2013.
Fit only on training; no refit on validation/test, early stopping or parameter search. Rolling
held-out daily origins may use prior held-out days' measured history, which is available by
that origin. Predictions are clipped at zero before both scoring and saved inference.

Ridge: StandardScaler fitted on training only, Ridge alpha 1. LightGBM: 200 trees, rate .05,
15 leaves, max depth -1, seed 42, minimum leaf samples 30, L2 1, one thread, deterministic,
force column-wise. Other effective estimator defaults and library versions are saved.
Baseline is always computed even when its checkbox is off. Positive percentage improvement
means less error; zero baseline error returns unavailable improvement. Repeated test inspection
can bias later selection; use validation for manual selection, test for final comparison.

## Usable origins / target observations

| Household | Training | Validation | Test |
| --- | ---: | ---: | ---: |
| MAC001391 | 52 / 2496 | 15 / 720 | 16 / 768 |
| MAC003288 | 52 / 2496 | 15 / 720 | 16 / 768 |
| MAC000143 | 52 / 2496 | 15 / 720 | 16 / 768 |
| MAC001534 | 52 / 2496 | 8 / 384 | 15 / 720 |
| MAC001395 | 44 / 2112 | 15 / 720 | 16 / 768 |
| Portfolio common evaluation dates | — | 8 / 384 | 15 / 720 |

Jan 1–7 are warm-up. MAC001395 Jan 10 missing excludes its target day and Jan 11–17.
MAC001534 Mar 9 missing excludes Mar 9 target and Mar 10–16 history-dependent origins.
Individual scores use each home's admitted dates; portfolio scores sum all five only on
common complete time-aligned intervals. Within each row, all algorithms share identical dates.

## Validation results

| Household | Algorithm | MAE kW | RMSE kW | MAE improvement % | Intervals |
| --- | --- | ---: | ---: | ---: | ---: |
| MAC000143 | LightGBM | 0.188183 | 0.273787 | 17.03 | 720 |
| MAC000143 | Ridge Regression | 0.185402 | 0.272617 | 18.25 | 720 |
| MAC000143 | Seasonal Naive | 0.226797 | 0.357648 | 0.00 | 720 |
| MAC001391 | LightGBM | 0.076935 | 0.130270 | 8.20 | 720 |
| MAC001391 | Ridge Regression | 0.067232 | 0.118849 | 19.78 | 720 |
| MAC001391 | Seasonal Naive | 0.083811 | 0.160916 | 0.00 | 720 |
| MAC001395 | LightGBM | 0.395464 | 0.596912 | 20.26 | 720 |
| MAC001395 | Ridge Regression | 0.444202 | 0.652428 | 10.44 | 720 |
| MAC001395 | Seasonal Naive | 0.495958 | 0.801590 | 0.00 | 720 |
| MAC001534 | LightGBM | 0.311044 | 0.411411 | -16.47 | 384 |
| MAC001534 | Ridge Regression | 0.288623 | 0.367092 | -8.07 | 384 |
| MAC001534 | Seasonal Naive | 0.267068 | 0.425610 | 0.00 | 384 |
| MAC003288 | LightGBM | 0.168275 | 0.258866 | -14.45 | 720 |
| MAC003288 | Ridge Regression | 0.185403 | 0.264011 | -26.10 | 720 |
| MAC003288 | Seasonal Naive | 0.147031 | 0.314592 | 0.00 | 720 |
| Portfolio | LightGBM | 0.636845 | 0.829418 | 7.57 | 384 |
| Portfolio | Ridge Regression | 0.706281 | 0.922735 | -2.50 | 384 |
| Portfolio | Seasonal Naive | 0.689031 | 1.005976 | 0.00 | 384 |

## Held-out test results

| Household | Algorithm | MAE kW | RMSE kW | MAE improvement % | Intervals |
| --- | --- | ---: | ---: | ---: | ---: |
| MAC000143 | LightGBM | 0.185788 | 0.274351 | 5.62 | 768 |
| MAC000143 | Ridge Regression | 0.177735 | 0.260089 | 9.71 | 768 |
| MAC000143 | Seasonal Naive | 0.196854 | 0.320599 | 0.00 | 768 |
| MAC001391 | LightGBM | 0.108420 | 0.164659 | -25.38 | 768 |
| MAC001391 | Ridge Regression | 0.087302 | 0.136569 | -0.96 | 768 |
| MAC001391 | Seasonal Naive | 0.086474 | 0.161987 | 0.00 | 768 |
| MAC001395 | LightGBM | 0.422715 | 0.680087 | 25.07 | 768 |
| MAC001395 | Ridge Regression | 0.484724 | 0.733016 | 14.08 | 768 |
| MAC001395 | Seasonal Naive | 0.564159 | 0.877778 | 0.00 | 768 |
| MAC001534 | LightGBM | 0.285054 | 0.387647 | 7.13 | 720 |
| MAC001534 | Ridge Regression | 0.294482 | 0.376537 | 4.06 | 720 |
| MAC001534 | Seasonal Naive | 0.306933 | 0.460448 | 0.00 | 720 |
| MAC003288 | LightGBM | 0.178346 | 0.311106 | 27.44 | 768 |
| MAC003288 | Ridge Regression | 0.183672 | 0.314734 | 25.27 | 768 |
| MAC003288 | Seasonal Naive | 0.245789 | 0.426245 | 0.00 | 768 |
| Portfolio | LightGBM | 0.684537 | 0.946907 | 16.88 | 720 |
| Portfolio | Ridge Regression | 0.736022 | 0.977148 | 10.63 | 720 |
| Portfolio | Seasonal Naive | 0.823539 | 1.159441 | 0.00 | 720 |

LightGBM reduces portfolio MAE by 16.88% and RMSE by 18.33%. It does not win on every home:
MAC001391 baseline MAE is lower. These are small winter-study results, not general performance
claims or evidence of dispatch feasibility. No algorithm was tuned to these test results.

## UI and persistence lifecycle

A2 checkboxes default to Seasonal Naive + LightGBM. Relevant parameters are editable.
A4 Run Models explicitly trains all selected methods for all five homes. Failure aborts the
whole run and removes stale saveable results. Results stay in session memory until explicit
Save Model. Config changes show a stale-results notice; run configuration remains recorded.
The date selector contains common valid test dates. Exactly five main household figures
show all 48 intervals, actuals and evaluated algorithms on the same axis. The optional portfolio
curve is removed from the main display; portfolio numerical evaluation remains unchanged.
One interactive Vega-Lite grouped bar chart shows full-test RMSE for five homes, adjacent bars
by algorithm, with household/algorithm/RMSE-kW hover values to four decimals. There are no A4
accuracy, run-configuration, counts, daily-metric or registry tables. A3 retains chronological
dates and missing-data information. Internal MAE, RMSE and improvements remain in run data
and saved metadata.

Below the bar chart, a short computed conclusion groups households by minimum test RMSE,
counts wins and identifies the minimum portfolio test RMSE. Ties use relative tolerance 1e-9
and absolute tolerance 1e-12; tied homes count for every tied algorithm and are identified.
Missing/nonfinite/negative results or unequal comparison counts cannot produce a complete
winner claim. The existing training pipeline admits identical dates across methods within
an entity. Each household may have a different admitted period from other households.

The Save Model selector defaults to minimum **validation portfolio RMSE**, among successfully
evaluated complete algorithms; test winners never determine this default. Validation ties
are stated and the first tied algorithm in recorded run order is the deterministic default.
If all validation portfolio scores are unavailable, the interface states that no recommendation
is available and keeps an explicit user choice. Manual overrides survive display-day reruns;
a new successful Run Models refreshes the recommendation. Charts retain the original evaluated
run when A2 settings change, with a stale-configuration notice. Changing the display day only
filters stored predictions and never trains or updates full-partition RMSE.

Implementation: `ui/forecast_results.py` renders the simplified A4; presentation-only helpers
in `ui/forecast_comparison.py` derive chart data/specification, winners and recommendations.
No new dependency, forecasting mathematics, artifact format, source hash, registry lifecycle,
information-cutoff policy or simulation-execution behaviour changes in this refinement.

Select an evaluated algorithm, enter an immutable version and click Save Model. Artifacts are
verified before atomic registry publication; then metadata is read back. Click Activate Model
separately to verify/load and persist the active reference. Training does not automatically
save/activate, and the benchmark did not create a production active model.

Storage: ignored `outputs/forecast_models/registry.json` schema 1, separate `artifacts/<uuid>.json`.
Envelope contains SHA-256 of canonical JSON payload. Payload format 1 contains feature order,
method/version/source hash, all five model states, configuration/effective settings, dependency
versions, counts, all household/portfolio metrics and physical clipping policy. Ridge states are
numeric scaling/coefficient arrays; LightGBM states are native model text; Naive stores config
and source reference, no fictitious coefficients. No pickle/joblib executable deserialization.
The checksum detects corruption, not malicious rewriting by someone with filesystem access;
only load local-owner trusted artifacts. Directory confinement and schema/identity/shape checks
reject incompatible, missing and incomplete bundles. Registry evaluation details also retain
all metrics/counts/features/settings/provenance. Registry summary metrics are portfolio errors.

Save and activation take an exclusive writer lock; competing writes fail clearly and can be
retried. A crashed writer may leave `.writer.lock`: inspect that no writer runs before removing
that one lock file. Orphaned artifacts after a process crash are never automatically activated.
Local files survive restarts on this machine; ephemeral hosted disks are temporary. Back up
this directory/use a durable volume. There is no cloud/database storage or automatic startup write.

## Reuse and replay restrictions

`SavedForecaster(store, validated_frame, observations_sha256)` loads the active bundle once.
Call `.predict(household_ids=..., forecast_origin=..., horizon_steps=48)` without any fitting.
Outputs follow the existing contracts: home, origin, step, interval start/end, nonnegative kW,
and algorithm/version reference. Subsets of known homes are allowed; unknown homes fail.
The input frame must come from the existing audit-verified prepared loader; its supplied source
hash must match. Extending/replacing data requires an explicit provenance/version policy.

Information cutoff conservatively includes all evaluation/selection labels: 1 April 2013 00:00 GMT
for this benchmark. Earlier March/January replays are rejected. April 1 inference can use retained
March history. November/December isolated replay days lack preceding seven-day prepared history
and are rejected. No automatic history download, cutoff bypass or invented lag data. Tab B reads
the active reference, reports incompatible origins and remains disabled. Tab C stays empty.

## Verification and limitations

Run `.venv/Scripts/python.exe scripts/benchmark_forecasts.py` to reproduce ignored CSV/Parquet
outputs. Prepared audit hashes verified and all 19 Task 03E preserved hashes match. Final A4 refinement suite: 276 tests pass; Ruff lint/format and ty pass. Real localhost agent-API smoke
ran actual models and all three Simulation Lab tabs without new warnings or tracebacks.
Additional verification details are recorded in CURRENT_HANDOFF.md. Only 90 winter days and five homes;
no weather, holidays, PV, uncertainty intervals, automatic search or annual generalisation.
This completes Task 05B only; do not start dispatch, MILP, MPC or full simulation here.
