> Task 05B now implements forecasting training/evaluation, safe bundles and explicit
> A4 save/activation. Earlier foundation-only statements below are historical.
> See [current forecasting specification and measured results](FORECASTING_MODELS.md).

# Task 05A — forecasting foundation and Simulation Lab

17 November 2026 · Branch `codex/task05a-forecast-foundation` · Complete; review pending.
No forecasting model was trained, no predictions were generated and no dispatch was implemented.

## 1. Files changed

Created:

- `src/batteryflex/forecast_data.py`: read-only GMT range views, missing-safe aligned aggregation,
  coverage/continuity and range summaries over the existing prepared LCL observations.
- `src/batteryflex/forecast_contracts.py`: immutable historical/dataset/model/metadata/active-reference/
  request/output contracts, admission checks and algorithm-independent Forecaster protocol.
- `src/batteryflex/forecast_registry.py`: JSON metadata, explicit active reference, safe artifact
  locations and explicit local-owner atomic persistence. No artifact deserialisation.
- `src/batteryflex/forecast_simulation.py`: future saved-input SimulationPlan, replay/forecast
  context, comparison fingerprints and one-click orchestration protocol, without execution.
- `src/batteryflex/ui/forecasting.py`: five-section model-development interface.
- `tests/test_forecast_data.py`, `tests/test_forecast_contracts.py`, `tests/test_forecast_ui.py`.
- `docs/FORECASTING_FOUNDATION.md`: this completion report.

Updated:

- `src/batteryflex/ui/explorer.py`: separate full-study and selected-observation-range summaries.
- `src/batteryflex/ui/planned.py`: replaces the previous setup/results layout with exactly three
  Simulation Lab tabs, preserving saved battery inputs and unavailable execution.
- `tests/test_app.py`, `tests/test_portfolio_ui.py`: current tabs and saved-only snapshot regressions.
- `README.md`, `docs/CURRENT_HANDOFF.md`, `docs/DEVELOPMENT_PLAN.md`, `docs/DATA_CONTRACTS.md`,
  `docs/UI_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `config/README.md`.

No dependency additions, staging or commits. Existing battery physics/configuration/persistence,
NESO validation and LCL parsing/acquisition/replay modules are unchanged. Unrelated parent work
is preserved. The forecasting view reads the existing hash-validated `load_prepared` output;
there is no second ingestion pipeline, acquisition, annual extraction or prepared-data rewrite.

## 2. Verified historical coverage

Actual files inspected: `data/lcl/prepared/observations.parquet`, `audit.json`, the existing
selection tables and replay metadata. Prepared artifact hashes were checked against the audit.
All five have earliest interval START **2013-01-01 00:00 GMT**, earliest END **00:30 GMT**,
latest START **2013-12-06 23:30 GMT** and latest END **2013-12-07 00:00 GMT**.

| Household | Retained half-hours | Valid | Missing cells | Invalid/duplicate | Complete retained days | Jan–Mar valid / expected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MAC001391 | 4416 | 4416 | 0 | 0 | 92 | 4320 / 4320 |
| MAC003288 | 4416 | 4416 | 0 | 0 | 92 | 4320 / 4320 |
| MAC000143 | 4416 | 4416 | 0 | 0 | 92 | 4320 / 4320 |
| MAC001534 | 4416 | 4415 | 1 | 0 | 91 | 4319 / 4320 |
| MAC001395 | 4416 | 4415 | 1 | 0 | 91 | 4319 / 4320 |

The continuous retained calendar block is 1 January–31 March 2013, 90 days/4,320 half-hours.
It is not perfect valid coverage for the last two households:

- MAC001534: missing source interval-END label `2013-03-09 21:30:00.0000000`; interval starts
  21:00 GMT. Longest uninterrupted valid run: 3,258 half-hours, 1 January 00:00 through
  9 March 21:00 GMT (end exclusive for the run).
- MAC001395: missing source interval-END label `2013-01-10 22:30:00.0000000`; interval starts
  22:00 GMT. Longest valid run: 3,843 half-hours, 10 January 22:30 through 1 April 00:00 GMT.
- The other three have uninterrupted valid runs of 4,320 half-hours, 1 January 00:00 through
  1 April 00:00 GMT.

January–March is **not all prepared data**: 7 November and 6 December 2013 are two additional
validated complete replay days, 96 half-hours per household. They are isolated; April–October
and other late-year dates are not retained in this prepared file. It is not a continuous year.

The local annual raw archive is present and its existing full-source audit spans interval ENDs
1 January 2013 00:30 through 1 January 2014 00:00. That is additional audited source material,
not an additional prepared, forecast-ready annual series for each selected household. This task
did not scan/extract additional raw rows or assume their household-specific completeness.

## 3. Chronological split

Verified calendar coverage supports the proposed split; the two isolated missing cells are
reported and remain missing rather than forcing arbitrary date shifts or invented values:

- Training: **2013-01-01–2013-02-28**, 59 days, 2,832 expected half-hours per household.
- Validation: **2013-03-01–2013-03-15**, 15 days, 720 expected half-hours per household.
- Testing: **2013-03-16–2013-03-31**, 16 days, 768 expected half-hours per household.

| Household | Training valid / missing | Validation valid / missing | Test valid / missing |
| --- | ---: | ---: | ---: |
| MAC001391 | 2832 / 0 | 720 / 0 | 768 / 0 |
| MAC003288 | 2832 / 0 | 720 / 0 | 768 / 0 |
| MAC000143 | 2832 / 0 | 720 / 0 | 768 / 0 |
| MAC001534 | 2832 / 0 | 719 / 1 | 768 / 0 |
| MAC001395 | 2831 / 1 | 720 / 0 | 768 / 0 |

Dates apply to interval START; an interval ending at midnight belongs to the preceding day.
The UI displays editable independent split date ranges with chronological non-overlap validation
and live per-household counts/missingness. These are raw observation counts, **not training-example
counts**. No model is trained, metrics are not calculated and random shuffling is not implemented.

The initial future missing policy is to exclude incomplete origins/features/targets. Task 05B must
construct origin-based examples, enforce lag/rolling history warm-up, and keep every 48-step label
window inside its evaluation partition. A 336-step lookback has no December 2012 context in the
current prepared data; early January origins cannot simply be filled or treated as complete.
The known missing cells also invalidate some later historical feature windows.

## 4. Forecast target and units

```text
P_load[i,k] = E_load[i,k] / delta_t
delta_t = 0.5 hours
P_load[i,k] = 2 * E_load[i,k]
```

Energy is the original kWh per 30-minute interval; the target is **30-minute average demand in
kW**, not instantaneous power. Original source timestamp/energy text remains in the prepared
observations. Existing parsing supplies aware GMT/UTC interval START and END and converted kW.
The analytical view verifies half-hour timing, finite valid energy and the kWh-to-kW relation;
it does not parse a second source or overwrite existing values. Fixed GMT is used throughout,
including dates on which UK civil time uses BST.

The history view aligns all selected homes on interval START and sums only when every member
has a valid observation. A missing, invalid, duplicate or absent member makes the aggregate
unavailable. `not_retained` distinguishes absent calendar slots from retained missing/invalid
cells. No unavailable measurement becomes zero. Observed-energy sums cover valid rows only and
are not estimates of total consumption over missing periods. A wholly unavailable range has no
energy/mean/peak estimate, rather than a zero-consumption value. Lines break at unavailable slots.

## 5. Data Explorer improvements

The existing household/date selectors, dated measured-load chart and original detailed readings
remain. **Full Study-Period Summary** now uses all available retained study dates, including the
two replay days, and remains fixed when inspection dates change. **Selected Observation-Range
Summary** recalculates start/end, retained/valid/unavailable half-hours, not-retained count,
complete days, observed energy, mean kW and peak half-hour-average kW for the selected range.

The detailed readings retain original interval-END text, original energy, GMT interval bounds,
average power and quality. No observation range silently changes forecast training dates.
The earlier five-house comparison remains its documented January–March screening/profile view.

## 6. Final Simulation Lab structure

Exactly three native lazy tabs; no separate Results or redundant Experiment Setup tab:

**Forecast Model Development**:

- A1 Historical Load Data: the five reviewed households plus aggregated portfolio, independent
  inspection dates, average-kW/original-kWh measurement choice, interactive measured curve,
  selected-range summary and expandable readings/verified coverage.
- A2 Forecast Model & Mathematics: method choice, LaTeX, fixed 48-step horizon, planned features
  and editable hyperparameters. These are configuration values, not fitted parameters.
- A3 Training & Evaluation Configuration: chronological split, actual counts/gaps, MAE/RMSE units
  and **Not trained** status. Inspection dates do not affect these periods.
- A4 Forecast Results: **No trained forecast available.** Future areas are described for selected
  and all-five actual-versus-predicted kW, origin/horizon, metrics and a 48-step output table.
- A5 Forecast Model Registry: actual records only, with Train → Evaluate → Save Model → Activate
  Model workflow. Current registry is empty; no fake records, artifacts or metrics are created.

**Run Simulation & Results**:

Event, explicit local kW proposal, saved battery snapshot, active-model information and Rule-based/
MILP/Rolling MPC choice. Per-battery saved export settings are authoritative; the old nonfunctional
export-mode planning toggle is removed. No active model is claimed from an untrained configuration.
Selected events show original NESO date, unchanged synthetic 2013 replay date and explicit proposed
00:00 GMT forecast origin for a 48-step day-ahead horizon. Available source SHA-256 references are
captured in the future plan; source dates are never overwritten.

Run Simulation is disabled, with all control methods labelled unavailable. Future interaction:
Select experiment → Click Run Simulation once → View results immediately below. The orchestration
contract covers saved portfolio, active model, forecasts, feasibility, control, battery/grid
simulation, metrics and retained results. Forecasting should not require a separate per-run user
action. The result area is immediately below controls, empty until real execution exists.

**Comparison & Evaluation**:

No completed runs to compare; Clear Results remains disabled. Planned metrics and compatible-input
requirements are explicit. Future run records already retain unique IDs even for repeat strategies;
strategy may differ within equivalent experiments, while event/replay, commitment, participating
homes, initial SOC/battery/export settings, model version/origin, demand scenario, tariffs, baseline
and data references must match. No artificial comparisons or overlays are shown.

## 7. Model configuration and mathematics

All methods forecast the same average-kW target at **48 half-hours = 24 hours**:

| Method | Equation | Configuration and intended role |
| --- | --- | --- |
| Seasonal Naive | `P_hat[t+h] = P[t+h-48]` | Baseline. Corresponding prior-day reading must already be available at the origin; no missing-as-zero fallback. |
| Ridge Regression | `P_hat = beta_0 + beta^T X` | Linear ML benchmark with L2 regularisation; editable nonnegative alpha, default 1. |
| LightGBM | `P_hat = sum(f_m(X), m=1..M)` | Primary nonlinear regression-tree ensemble; editable leaves (31), learning rate (0.05), trees (100); planned max depth -1, seed 42. |

Planned ML features: household ID, time of day, day of week, weekend indicator, historical lags
48/336 and rolling statistics over 48/336 half-hours. The `load-origin-v1` schema requires every
historical window to end at/before the forecast origin, even for later horizons. Future target
timestamps may contribute calendar features, but never unknown future demand. No feature matrix,
training, model coefficients/trees, metrics or predictions were computed in Task 05A. No ML
library dependency or import was introduced.

Typed frozen contracts cover source observations, periods/dataset configuration, method and
canonical hyperparameter JSON, MAE/RMSE in kW, model metadata, explicit active reference, forecast
request and per-household output. Forecaster is an algorithm-independent `predict` protocol;
there is no placeholder implementation. Outputs contain model name/version, origin, interval
start/end, step 1–48 and predicted average kW. The first predicted interval starts at the origin;
the last ends 24 hours later. Batch validation requires exactly every requested home/step and
consistent origin/model identity. Synthetic values exist only in labelled contract test fixtures.

## 8. Registry, artifacts and historical admission

Default local layout (not created by page rendering):

```text
outputs/forecast_models/registry.json
outputs/forecast_models/artifacts/<versioned-relative-model-location>
```

Metadata schema v1 records name/version, configuration/feature schema/horizon, training/validation/
test periods, household set, training-data SHA-256, fit time, information cutoff, validation/test
MAE and RMSE, artifact location and lifecycle status. An explicit separate name/version reference
designates the active model. Recorded stages are Not trained, Trained, Evaluated, Saved, Unavailable
or Incompatible; Active is derived only from the active reference plus a saved record and an
existing artifact. Duplicate name/version records are rejected, not silently upserted.

Saved/evaluated records require actual metric fields and provenance; a not-trained record cannot
claim fits, metrics or artifacts. Broken metadata is shown as unavailable/incompatible rather than
inventing an empty trained model. Missing saved/active artifacts are unavailable. All artifact paths
must resolve inside the separate artifact directory, including against traversal/symlink escapes.
Artifact contents are never loaded or deserialized by Task 05A.

Reads have no startup writes or directory creation. Explicit local-owner tools can atomically
write JSON metadata and select an active reference; the UI exposes no write/activation path.
Versioned artifacts are a separate future training responsibility. No Turso migration, cloud
storage, credential change or public shared-file write is introduced. This simple read/write/
active-reference interface can later be backed by another durable metadata/artifact adapter.

Historical admission checks the requested household set/horizon and requires model information
cutoff <= forecast origin. The cutoff conservatively covers training and recorded evaluation/
selection information; final evaluated models cannot claim validity for earlier replay origins.
Original 2013 demand is not contemporaneous with 2023–2026 NESO events. A single final model
evaluated through March cannot be presented as a historical January/February/March forecaster.
Later replay experiments need explicitly origin-safe versions/walk-forward evaluation or clearly
labelled counterfactual assumptions. November/December replay days additionally lack preceding
day/week lag history in the current prepared subset; later work must resolve that limitation.

## 9. Validation results

- **262 tests passed**, including existing Tasks 01–04 regressions, battery configuration/status
  text, physical constraints, NESO/LCL exploration, save/restore and immutable run contracts.
- Ruff lint/format checks and `ty check src app.py` passed.
- New tests cover original energy-to-average-power conversion, GMT endpoints/date filters,
  selected-range summaries, absent/missing/duplicate propagation, all-five alignment, categorical
  quality handling, continuous coverage, chronological periods, configuration/metadata lifecycle,
  active references/missing artifacts, owner-only writes, safe paths, registry JSON round trips,
  future-origin admission, output batch completeness and changed run-metadata compatibility.
- UI tests cover actual data inspection, aggregate demand, measurement/model configuration,
  inspection/training-period independence, invalid split messages, no-trained/no-model/no-run
  empty states, source dates/replay context, saved-only battery inputs and disabled execution.
- Real localhost Streamlit health/agent-API checks passed for exactly three pages/three tabs,
  all six historical series, actual split counts, the known aggregate gap, independent date
  ranges, all three configured methods, five replay contexts, disabled Run/Clear, empty comparison,
  existing battery page and NESO/LCL range functionality. No new warnings or tracebacks remained.
- All **19** preserved source/data SHA-256 values match the Task 03E baseline. No production
  registry directory/file was created. The temporary test server was stopped after verification.
  Agent API smoke evidence is ignored under `outputs/task05a-*`; browser visual QA was not performed.

Streamlit tests and localhost requests used approved escalated execution due to sandbox
restrictions. No external service or database mutation was performed.

## 10. Remaining work for Task 05B

After review, implement actual leakage-safe origin features, warm-up/missing-label selection,
chronological fit/tuning/evaluation and real MAE/RMSE, beginning with the declared baseline.
Ridge/LightGBM training libraries and artifact formats remain to be selected/installed explicitly.
Safe trusted artifact loading, immutable model versions, lifecycle actions and activation need
real training outputs. Validate household-level and aggregate forecasts, complete 48-step batches,
negative-prediction policy and per-origin historical model admission before simulation integration.

Data inspection and planned configurations are session-local and do not constitute trained models
or durable training jobs. Additional raw data retention for replay lag context requires an explicit
later reviewed step; no annual coverage is assumed. Dispatch feasibility, baseline/price/tariff
calculations, rule-based control, MILP, MPC, full simulation and result persistence remain later work.

Stop after Task 05A. Do not begin training or Task 05B without review.
