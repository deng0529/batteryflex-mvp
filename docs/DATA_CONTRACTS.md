> Task 05E adds derived read-only peak diagnostics. Q90 uses admitted training targets only; portfolio Q90 uses coincident sums on complete common origins. Peak timing uses earliest ties and non-circular 30-minute clock differences. No qualifying high-demand intervals means unavailable MAE. Exact saved period bounds and checked household admission counts drive date displays. No database or model contract/fingerprint changed. [Current report](TASK05E_PEAK_ANALYSIS.md).

> Task 05D adds immutable event-history-v1 data, load-event-dayweek-v1 features and event-model-v1 bundles. Request identity pins households, unchanged NESO source hash/replay origin, dataset, policy and windows; model identity also pins exact configuration, numeric library versions and estimator/feature code. Model information cutoff excludes final event actuals; separate evaluation artifacts record availability and all scoped errors. [Current event contract and results](TASK05D_EVENT_FORECASTING.md). Earlier status notices below are historical.

> Task 05C implements versioned relational metadata and content-addressed object storage.
> [STORAGE.md](STORAGE.md) is the current storage/bootstrap/cache contract; earlier foundation-only
> and explicit-save descriptions below are historical. Cloud migration awaits dedicated access.

> Task 05B now implements forecasting training/evaluation, safe bundles and explicit
> A4 save/activation. Earlier foundation-only statements below are historical.
> See [current forecasting specification and measured results](FORECASTING_MODELS.md).

# Data contracts

These are design requirements, not implemented database schemas. Task 04 battery models
and versioned JSON configuration are implemented as described below. Source-specific
column names, licensing and timestamp semantics must be verified during exploration.

| Entity | Required semantics |
| --- | --- |
| Import batch | ID, source URL/version, acquisition time in UTC, content hash, parser version, validation report, row counts and outcome |
| NESO event | Source event ID, original date/time values and source time-zone semantics, event interval and source units, import batch ID |
| Household observation | Source household ID, original 2013 timestamp text, source interval/unit, measured energy, quality flags, import batch ID |
| Battery configuration | Versioned simulated ID, household selection ID, capacity kWh, charge/discharge kW, efficiency convention, SOC bounds and initial SOC |
| Scenario | Versioned ID, selected five households/batteries, source references, simulation clock, explicit event-to-household mapping, duration and assumptions |
| Forecast | Scenario/run ID, issue time, target intervals, horizon, model/version, values and units |
| Run/result | Run ID, input/config versions, solver status and settings, interval actions/SOC, objective, diagnostics and evaluation metrics |

## Invariants for later implementation

- Preserve raw source timestamps and dates immutably; store derived normalized values
  separately only after documenting timezone and daylight-saving handling.
- Never overwrite 2013 household timestamps with NESO event dates. Derived alignment
  records both original time references and simulation time with a mapping policy/version.
- Energy is kWh, power is kW; interval duration and power sign convention must be declared.
- Validate required fields, duplicates, temporal coverage, missing/invalid measurements
  and units before import. Reject or quarantine failures with traceable reasons.
- Do not silently fill missing demand or interpret quality markers as zero.
- Keep source observations independent of simulated assets and optimisation outputs.
- Choose database keys, constraints and conversion rules after source inspection;
  migrations must be reviewed and tested against a disposable database.

## Task 02 exploration representation

Raw API objects and all columns are retained unchanged in session memory. Derived rows
contain nullable event_id, delivery_date, start_time, end_time, required_mw, direction,
requirement_type, time_basis and a sample-local source_row. This is not an import schema.
No synthetic event identifiers or complete timestamps are generated. See
NESO_SOURCE_DISCOVERY.md for exact sources, mapping, missing fields and timezone limits.

## Task 02B additions

Derived rows also expose source_name/resource_id/source_record_id, original local clocks,
tag, dispatch type, eligible participants and original zonal cap text. Retrieval metadata
includes ordered request_urls, explicit complete flag and UTC completed_at. `total` counts
service-window rows, not events. Exact-row comparison ignores only CKAN _id and does not
remove raw records. Event grouping uses resource + Event ID + delivery date; archive date
groups never create event IDs. Contiguous-window duration is derived only on validated
half-hour boundaries; overnight rollover is not guessed. See NESO_DATA_DICTIONARY.md.

NESO DFS v5 Downwards denotes demand reduction/generation increase, and Upwards denotes
demand increase/generation reduction. The raw direction is preserved; no signed MW,
portfolio target, battery action or household time alignment is inferred from that label.

## Task 02C exploration contracts

See NESO_DIVERSE_EVENTS.md for the replacement provisional shortlist. Older directionless
archives retain event_id=None and direction=None. `demand_reduction`, `direction_evidence`
and its official URL are separate contextual annotations, allowlisted to known resources
before the 9 April 2026 bidirectional change. Source/date groups are event proxies only.

Interval rows contain number, start/end UTC and offset-qualified UK times, actual elapsed
hours, original national MW, source event ID (nullable), CKAN row ID, resource ID,
requirement_basis and partial_interval. Direct half-hours retain reported values. Splitting
an event-wide source window repeats MW with an explicit constant-within-window simulation
assumption. Source changes are never averaged. Partial pieces remain partial; chronology
errors and disjoint source windows fail clearly. Raw dates/times remain unchanged.
National MW never becomes a five-house kW commitment through implicit conversion/scaling.

## Task 02D validation result fields

Each inspected group carries validation_status, validation_criteria and validation_reasons;
each criterion is PASS, FAIL or UNVERIFIED. Only all-PASS groups can enter final
recommendations. Live requires every original Service Requirement Type to equal Live.
Missing status is UNVERIFIED and Test is FAIL. Raw records are never deleted.

verified_direction_meaning and direction_definition_url record independent official
semantic evidence; absent raw Event Type stays null. internal_scenario_id uses a
BF-SCENARIO prefix plus date and deterministic source/window-reference fingerprint and
is labelled internal, never an official NESO Event ID. Original IDs remain unchanged.
source_records_sha256 fingerprints the reviewed original record set. winter_season is
separate from the publisher's archive title; February/March 2025 belong to 2024/25.
These are reviewed historical inputs, not saved runs, final commitments or Turso rows.

## Task 02E — reviewed selection manifest

Manifest version 1 stores reviewed events, unchanged source records, full-acquisition
provenance and original validation output. The included resource records are a selection
subset (`complete=False`); original total/retrieval timestamps still describe the reviewed
full acquisition. Loader rebases lookup positions from original CKAN IDs without changing
official fields, source hashes or internal scenario IDs. This package asset is not an import
batch, household dataset or final scenario persistence. Eligibility remains implemented only
in neso_validation; the UI reads its previously reviewed results.

## Task 03 — prepared household exploration v1

Source v1: 4TU DOI 10.4121/fbbe775b-48d8-469f-a39b-b64488bfd6fd.v1, CC BY 4.0.
IDs match the actual unique `MAC` + six-digit headers. `source_timestamp` and `source_kwh`
preserve original cell text. Source labels mark the END of the preceding 30 minutes in
fixed GMT, including BST periods. `interval_end_gmt` is aware UTC; `interval_start_gmt` is
end minus 30 minutes. `energy_kwh` is finite nonnegative energy; `average_power_kw` = energy × 2.
`quality` is valid/missing/invalid/duplicate. Missing/invalid/duplicate demand stays null.
All duplicate keys are quarantined; timestamp/ID/row-width failures stop preparation.

Full audit counts every source slot. Sample retains original missing cells; absent rows
remain missing in fixed-denominator completeness and replay lookup. Full days require 48
valid unique intervals, assigned by START (midnight end belongs to prior day). Analysis:
Jan–Mar 2013, 90 heating-season days; two November/December replay days retained separately.

Replay v1 preserves NESO internal scenario ID/date/start/end plus household date/start/end.
Match month and exact weekday in 2013, closest day number, earlier tie. Join source demand
at interval END, never START. Same five IDs in all 17 half-hours; combined kW propagates
missing values. Synthetic replay is not contemporaneous observation or deliverable flexibility.
No national-MW scaling, portfolio commitment, battery assets/configuration or Turso schema.

Ignored artifacts: observations.parquet, candidates.csv, recommended.csv, replay.csv, audit.json.
Audit records parser/mapping versions, source provenance, sample IDs, dates, raw and artifact
SHA-256. UI verifies hashes on cached load and never downloads. See LCL_DATA_LAB.md for gates.

## Task 03E — future simulation history contracts

See UI_ARCHITECTURE.md and simulation_contracts.py. Frozen ExperimentInputs retains internal
NESO scenario ID, canonical battery configuration/initial SOC/export/forecast/data-reference
snapshots and explicit portfolio commitment kW. Canonical full-input SHA-256 groups equivalent
experiments; strategy is excluded, all other experimental inputs must match. Frozen SimulationRun
retains a unique UUID, completion UTC, inputs, strategy, immutable result JSON and EvaluationMetrics.
Repeated strategy runs append separately; duplicate IDs fail rather than overwrite. Pure
compatible_runs and clear_experiment helpers group or clear only the matching experiment.

Metrics fields: commitment_fulfilment_pct, delivery_shortfall_kwh, electricity_cost_gbp,
battery_energy_throughput_kwh, final_soc_by_household_json (%), computation_time_seconds.
These are contracts, not calculations, admission validation, a database or a working engine.
Future durable storage must enforce unique IDs, append-only insertion, atomic snapshots and
scoped explicit deletion. No production runs or example model outputs are created in Task 03E.


## Task 04 — implemented simulated battery contracts

`battery.py`: frozen BatteryConfig, BatteryState and BatteryAction. All model SOC values are
fractions in [0, 1]; the UI displays percent. Stored energy is DC-side kWh; charge/discharge
are AC-side kW; time is hours. `transition(config, state, action, load_kw=..., duration_hours=...)`
uses the configured interval (default 0.5 h) unless explicitly overridden. It validates input
and output energy bounds, power ratings and net household export. Infeasible requests raise
ValueError without control clipping. A 1e-10 tolerance handles floating-point state/grid bounds.
Source household load must be nonnegative and finite; no PV is modeled.

`portfolio.py`: frozen Portfolio with unique household IDs; extensible beyond five in pure
logic. Default public page is exactly the reviewed five. Initial SOC is illustrative,
participation is explicit and excluded batteries contribute zero. Installed capacity includes
all configured assets; participating capacity, usable/deliverable energy and discharge rating
are separately defined. `availability` does not filter participation; `capability` does.
Instantaneous discharge rating is a nameplate limit; it does not guarantee available energy.

`availability(config, T, state=None)` and `final_soc(config, discharge_kw, T)` are battery-only:
constant discharge, no recharging, no household/grid restrictions. `assess_commitment` compares
the sum of participating battery limits with a nonnegative finite local kW request; equality
passes. No allocation/dispatch strategy is implied by per-household maximum contributions.
Export caps are enforced in `grid_power`/`transition` with a supplied load; they cannot be
fully assessed by the preliminary energy/power check without load profiles. UI warns explicitly.

JSON v1 envelope: `{"schema_version": 1, "batteries": [...]}`. Each battery contains exactly
household_id, capacity_kwh, charge_limit_kw, discharge_limit_kw, min_soc, max_soc, initial_soc,
charge_efficiency, discharge_efficiency, export_enabled, export_limit_kw (null = no cap;
0 = zero permitted export), participating and interval_hours. Round-trip efficiency is the
product of the two efficiencies. Every field is required on import, with no silently supplied
missing defaults. Unknown versions/fields, nonfinite values, invalid booleans/physics, duplicate
IDs and files over 100 kB fail. The public page additionally checks the exact five reviewed IDs
and restores their canonical display order. Validation completes before replacing session state.

Save/download and load/upload are browser-owned file persistence, not server-file or database
storage. Source measurements and original replay references remain independent. Session state
is the current editing workspace; users must download their settings to retain them after
session expiry. Public users cannot overwrite shared configuration. No owner-only server-write
mode or authentication bypass was added.

`BatteryScenarioSnapshot` contains canonical immutable portfolio_json (all settings including
SOC, participation and export), nullable internal event_id and explicit commitment_kw.
`scenario_snapshot` is a pure input builder; UI `current_portfolio()` supplies current validated
settings on either configuration or Simulation Lab pages. Simulation Lab seeds its event choice
from the portfolio check and snapshots the currently selected simulation event. It does not
execute. Future tasks must add original household demand/replay references, forecasts, control
strategy and validation before building existing ExperimentInputs and appending real runs.
No source timestamps are rewritten and no artificial simulation outputs are created.


## Task 04B — working, saved, demonstration and scenario contracts

This section supersedes Task 04's UI/session semantics above; the strict battery physics,
JSON v1 import/export and portfolio capability APIs are unchanged.

`portfolio_editor.py` maps model fractions to UI percentages for initial/minimum/maximum SOC
and separate charge/discharge efficiencies. `round_trip_efficiency` is calculated in percent as
`charge_efficiency_pct * discharge_efficiency_pct / 100`; it is not an independent model input.
Only household ID and calculated efficiency are read-only. All five reviewed rows have stable
order. Nullable numeric export cap becomes None when blank; zero still means zero export.
Every row uses the fixed global `INTERVAL_HOURS = 0.5`; no per-battery interval column is exposed.
`validate_rows` reuses BatteryConfig physical validation and reports affected household/parameter;
all rows must pass before returning a portfolio. There is no partial save or SOC repair.

Session state has four separate meanings:

- `battery_working_rows`: full editable table in display units, including invalid drafts.
- `battery_portfolio`: last validated saved active Portfolio, initialized with declared defaults;
  consumed by `current_portfolio()` and Simulation Lab. Working changes never enter it implicitly.
- `demo_*`: temporary household/mode/requested-power/duration controls; no asset-state mutation.
- `check_participation_<household>`: five temporary scenario choices, initially all True,
  independent of table and active participation. Working parameters plus these choices form only
  the preliminary check's local scenario. No scenario-selected portfolio replaces active assets.

The keyed fixed-row editor retains its identity during edits; full working values persist in
non-widget session state across page switches. A rerun refreshes calculated efficiency values.
Restore Defaults replaces only working rows and changes the editor revision so displayed values
reset immediately; saved assets and scenario/demo inputs remain unchanged until explicitly edited.

Save Configuration validates every working row again, serializes/revalidates schema-v1 JSON,
then sets the active portfolio and `battery_saved_json`. Its download button offers exactly that
reviewed configuration. A new cell edit arriving with the save is not silently committed using
an older download payload: the user is asked to review the updated table and save again. Saving
invalid rows fails without replacing active state. Confirmation claims only session activation
and a requested browser download, never a permanent server write or completed local file save.
Keep the JSON file for persistence beyond session expiry. No shared/public configuration writes,
Turso changes or startup writes occur. Separate load/apply-all actions were removed from this UI;
strict import/export functions remain available and regression-tested.

`battery_demo.py` defines immutable BatteryDemonstration and DemoInterval records. `demonstrate`
accepts a valid BatteryConfig, Charge/Discharge/Idle, finite nonnegative requested kW and a
0.5–24-hour duration in 0.5 h steps; Idle requires zero power. Each record contains interval end
elapsed_hours, energy_kwh, fractional soc, requested_kw, actual_charge_kw, actual_discharge_kw,
curtailed_kw and limit_reasons. Initial time/energy/SOC are separate to include time zero in the
single SOC plot. Summary energy totals are electrical AC-side kWh; stored energy remains DC-side.

For demonstration only, charge power is capped by rating and `(E_max-E)/(eta_c*0.5)`;
discharge power is capped by rating and `(E-E_min)*eta_d/0.5`. Curtailed power is requested minus
actual; curtailed electrical energy sums curtailed kW times 0.5 h. Every feasible action is then
passed to the unchanged Task 04 `transition`. SOC-boundary intervals use feasible constant
half-hour average power, not an inferred within-interval stop time. The demonstration explicitly
ignores household load/export permissions/caps by using a temporary export-unrestricted config;
it does not alter original settings or configured initial SOC. The strict transition still
rejects infeasible actions outside this demonstration adapter. This is not event dispatch.

Feasibility calls the existing capability/assessment functions with valid working parameters
and temporary checkbox selection, preserving constant/no-recharge/battery-only assumptions.
A pass is not official NESO delivery feasibility. Export restrictions, household load,
baseline-relative flexibility and time-varying dispatch remain excluded. Simulation Lab builds
its existing immutable BatteryScenarioSnapshot only from `current_portfolio()` saved assets,
with explicit event/commitment inputs. Its Run/Clear controls remain disabled.


## Task 04C — exact-boundary performance and explained commitment contracts

This section supersedes Task 04B's duration/idle/curtailment demonstration API and all-True
scenario defaults. Core Task 04 strict battery physics, JSON v1 and working/saved separation
are preserved. Table tooltips now define round-trip efficiency as the electrical recovery
fraction `eta_charge * eta_discharge`, and export cap as permitted NET household grid export
(kW), distinct from battery discharge rating. Blank cap remains None; zero remains a zero cap.

The displayed battery equation is a discrete-time energy-balance/SOC scheduling model with
constant efficiencies, energy in kWh, AC power in kW and time in hours. It is not a first-/second-
order RC voltage/transient equivalent-circuit model, a manufacturer's BMS or a measurement-validated
battery model. Household `P_grid = P_load + P_charge - P_discharge` is a separate power balance
(positive import, negative export), intended to be combined with energy scheduling in later tasks.

`demonstrate(config, mode, operating_power_kw)` now accepts only Charge/Discharge and finite
positive power <= the corresponding charge/discharge rating. It returns frozen BatteryPerformance:
initial_soc, initial_energy_kwh, operating_power_kw, completion_hours and PerformanceInterval tuple.
Each interval contains elapsed_hours (end), duration_hours, energy_kwh, fractional soc, charge_kw
and discharge_kw. There is no user duration or curtailed/requested power field.

Completion time is `(SOC_max-SOC_initial)*C/(eta_c*P)` for charge and
`(SOC_initial-SOC_min)*C*eta_d/P` for discharge. The integrator calls the unchanged strict
transition for normal 0.5-hour steps and a shorter last step to the calculated boundary time.
Power stays constant, with no rating clipping or final-interval power averaging. Final stored
energy round-off is normalized to the exact boundary only within 1e-9 kWh; no control adjustment.
Initial SOC already at the relevant boundary yields zero time, zero electrical energy and no
transitions. The chart includes time-zero SOC even in that case. AC electrical energy sums actual
power times each actual interval duration. Saved/configured initial state is never mutated.

Performance explicitly excludes household load/export restrictions using a temporary unrestricted
copy. Zero ratings have no valid positive operating point and are explained in the UI. There is
no former 24-hour duration cap. Curves needing more than 100,000 half-hour steps fail explicitly
with a resource-limit message rather than rounding/truncating time or returning fabricated curves.

`explain_commitment(portfolio, T, commitment_kw)` returns frozen CommitmentExplanation wrapping
existing CommitmentAssessment and PortfolioCapability, plus required_energy_kwh, shortfall_energy_kwh,
energy_only_power_kw, limiting_cause, energy_limited_households and power_limited_households.
Capability remains sum of `min(discharge_rating_i, deliverable_energy_i/T)` across participants.
Required energy is commitment*T; nonnegative constant-power shortfall energy is shortfall_kw*T.
Neither is measured delivery or official settlement.

For infeasible scenarios, explanation checks both each battery's active energy/rating constraint
and whether aggregate deliverable-energy/rating ceilings independently fall below the request.
Cause is energy, power or combined; no selected households has its own no_participants cause.
If actual capability is sufficient, cause is none. Combined constraints can fail despite adequate
aggregate energy and aggregate ratings, because the energy-rich battery may be power-limited and
the high-rated battery energy-poor. Diagnosis therefore never relies on total energy alone.

Feasibility has one Quantity/Value/Unit/Explanation table: duration, household count, usable and
deliverable energy, sustainable power, local commitment, required energy, margin and kW/kWh
shortfalls only when insufficient. Actual contribution-sum, margin, required-energy and shortfall
equations are displayed dynamically; no household contribution or all-events table is added.
Status is Preliminary battery capability sufficient or Insufficient battery capability. Constant
discharge/no recharge/no grid-side restriction assumptions are explicit. Demand, export limits,
baseline-relative delivery and time-varying optimisation remain out of scope.

Temporary checkboxes initialize from current valid working participation. For each household,
`check_participation_source_<id>` tracks the last working participation value used to seed it;
when that working field changes, only that household's checkbox rebases. Other table edits,
performance changes, saves and reruns preserve scenario overrides. No checkbox writes into the
table or saved active portfolio. Invalid working configurations suppress performance/capability
outputs and cannot be saved. Simulation Lab continues to consume only saved active assets.


## Task 05A — implemented forecasting foundation contracts

`forecast_data.py` consumes the original existing hash-validated prepared LCL dataframe; it does
not ingest sources. Date filters apply to GMT interval START with inclusive date bounds and an
exclusive next-day midnight upper bound. Original source labels mark interval END and remain
unchanged. Valid average kW must equal original numeric kWh/0.5; 30-minute durations, zero-offset
GMT/UTC timestamps and half-hour alignment are checked. Duplicate members are quarantined in the
analytical copy. Source categorical quality is converted only in that copy, without artifact writes.

`historical_series` aligns selected households on an explicit 30-minute calendar grid. Each
aggregate requires every requested member valid; no partial sum is called total portfolio load.
Unavailable values remain null and `not_retained` distinguishes absent slots from retained missing/
invalid cells. `LoadSummary` records inclusive dates, expected/retained/valid/unavailable counts,
not-retained count, complete days, observed-valid energy sum, valid mean power and valid peak power.
No valid rows means no energy/mean/peak estimate. `coverage_report` records actual endpoints, source
row counts/quality, complete retained days and longest uninterrupted VALID run. Source observations
are not rewritten. Full-study summaries include all 92 retained days, not just the Jan–Mar screen.

`forecast_contracts.py` defines frozen HistoricalLoadObservation, DatePeriod, ForecastDatasetConfig,
ForecastModelConfig, ForecastMetrics, ForecastModelMetadata, ActiveModelReference, ForecastRequest
and ForecastOutput. Source observation records retain raw timestamp/energy text, aware GMT interval
bounds, numeric kWh/average kW and quality. Missing/invalid rows cannot contain invented targets.
DatePeriod dates are inclusive by interval start; available_through is midnight after the last day.
Dataset periods must be chronological/nonoverlapping, with unique household IDs, fixed 48-step
horizon and feature version load-origin-v1. Initial missing policy excludes incomplete origin
features/labels. No training, feature matrix or imputation is implemented.

Verified default split: training 2013-01-01–02-28; validation 03-01–03-15; test 03-16–03-31.
Raw expected per-house counts: 2,832 / 720 / 768. MAC001395 has one training missing cell;
MAC001534 has one validation missing cell; test windows are complete for all five. Counts are
not usable supervised-example counts; future construction must enforce lag/window warm-up,
origin-only history and complete 48-step targets inside each evaluation partition. Inspection
range widgets are independent and cannot mutate split dates. No random shuffling is permitted.

Methods: Seasonal Naive, Ridge Regression and LightGBM. Hyperparameters are canonical finite JSON
with method-specific names/ranges. They are configured values, never trained coefficients or trees.
Planned origin-safe history features include 48/336-step lags/windows plus household and calendar
features. Seasonal Naive's prior-day reference must already be available at the origin. The target
is average kW; horizon 48 half-hours/24 hours. MAE/RMSE are finite nonnegative kW with RMSE>=MAE for
the same evaluation; no real metric values were generated by this task.

A forecast origin is an explicit aware GMT half-hour timestamp representing the information
cutoff. Output step 1 starts at the origin and ends 30 minutes later; step 48 ends 24 hours later.
Each ForecastOutput includes household, origin, start/end, step, nonnegative finite predicted
average kW and explicit model name/version. `validate_forecast_batch` checks exactly every
requested household/step without duplicates and consistent origin/model identity. `Forecaster`
is only a typed predict protocol; no placeholder output implementation exists.

Model metadata includes name/version, dataset periods/households, config/horizon/feature version,
source SHA-256, fit time, information cutoff, validation/test metrics, lifecycle stage and separate
artifact location. Not trained cannot claim fitted outputs/artifacts; Trained/Evaluated/Saved
have progressively required provenance/metrics/location fields. Active is derived from an
explicit registry reference, not a contradictory status field. Missing artifacts are unavailable;
bad schema/metadata is reported, not converted into fake records or predictions.

`forecast_registry.py`: schema-v1 metadata envelope contains records and nullable active reference.
Read missing registry -> empty registry, with no directory/file creation. Future local path is
outputs/forecast_models/registry.json, artifacts beneath its separate artifacts/ directory. Duplicate
name/version pairs are rejected. Only explicit local-owner write calls (not exposed in the UI)
perform atomic JSON persistence. No startup/public writes, cloud/Turso migration or unsafe artifact
deserialisation. Relative artifact paths must resolve within the artifact directory; activation
requires a saved/evaluated record and an existing artifact. JSON round trips preserve all metadata.

`validate_model_for_request` checks saved stage, household compatibility, 48-step horizon and
information_cutoff<=forecast_origin. Metadata cutoff conservatively includes evaluation/model-
selection periods as well as training. A final evaluated March model cannot be called historically
valid at an earlier Jan–Mar replay origin. No consumption dates are changed to match NESO events.

`forecast_simulation.py`: frozen SimulationPlan retains original event ID/start, synthetic 2013
replay date, forecast origin, saved Portfolio, local kW proposal, active model reference (nullable
until available), demand scenario, tariff/baseline assumptions and source references. Current
planned origin is 00:00 GMT on the unchanged mapped LCL replay day. Actual LCL-observation/NESO-record
SHA-256 references are captured when available; unavailable source context stays explicit. The plan
builds a ForecastRequest and existing ExperimentInputs snapshots; changed model version, replay,
participation, tariffs, baseline, demand or sources changes compatibility. Strategy remains outside
the experiment fingerprint and inside the eventual SimulationRun, preserving comparative experiments.
`SimulationPipeline.execute` is a protocol only, with no dispatch or output implementation.

Simulation Lab's three native tabs are model development (five sections), run plus immediate
results, and compatible-run comparison. It reads only saved active batteries; untrained forecast
configurations never become active models. Run/Clear stay disabled. No models, registry files,
forecasts, accuracy metrics, simulation runs or comparison results are created during rendering.
Future Task 05B must supply actual training/artifacts/forecasts and origin-safe feature admission,
including missing lag context for isolated November/December replay days.
