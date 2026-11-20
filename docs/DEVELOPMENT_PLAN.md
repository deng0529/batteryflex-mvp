> Task 05D completed on 18 November 2026: source/coverage investigation, event-aligned Ridge/LightGBM rebuild, immutable Turso/R2 persistence and read-only cold-cache reuse. Task 06 remains unstarted. [Completion report](TASK05D_EVENT_FORECASTING.md). Earlier task numbering below is historical planning.

# Development plan

Complete one numbered task, update CURRENT_HANDOFF and stop for review each time.
All source inspection/import requires explicit approval in its own task; this plan
does not authorize downloads or database changes during foundation work.

| Task | Deliverable | Independent verification |
| --- | --- | --- |
| 01 Foundation | Package, app shell, docs, tests, lint | App starts, Data Explorer renders, tests/lint pass; no external IO |
| 02 NESO exploration | Inspect source metadata, event semantics, dates, units, licence and provenance design | Reviewed source report; fixtures validate observed schema and date preservation |
| 03 Low Carbon London exploration | Inspect household format, original 2013 intervals, missingness and quality markers | Reviewed coverage report; fixtures preserve source times and distinguish gaps from zero |
| 04a Turso contracts | Final schemas, reviewed migrations, environment configuration | Constraints and migrations pass on a disposable database |
| 04b Explicit import | Validated batch import tools with provenance and duplicate policy | Fixture import is traceable and repeatable; invalid batches fail safely |
| 04c Saved-data explorer | Turso read repositories and read-only Data Explorer views | Repository tests plus UI empty/error/data states; no render-time writes/downloads |
| 05 Household and battery selection | Reproducible five-household selection and versioned battery settings | Coverage checks; invalid battery bounds rejected; selection reproducible |
| 06 Scenario feasibility | Explicit cross-period mapping, limits, interval conventions | Original times retained; mapping, energy balance and infeasible scenarios tested |
| 07a Forecast baseline | Simple declared baseline and time-based backtest | No future leakage; hand-checkable forecasts and metrics |
| 07b Forecast integration | Versioned forecast outputs for MPC horizons | Horizon, missing data and boundary cases tested |
| 08a MILP model | Objective, constraints, solver policy and diagnostics | Tiny analytical examples, energy/SOC bounds and infeasibility tests |
| 08b Optimisation persistence | Versioned run manifests and saved dispatch outputs | Reproducible inputs, solver status and output round trips |
| 09 Closed-loop MPC | Receding-horizon simulation for five batteries | Only first action applied; state propagation and end-of-horizon tests |
| 10 Performance evaluation | Declared no-control/baseline comparison, delivery and constraint metrics | Hand-computed metric fixtures and reproducible comparison report |
| 11 Deployment | Reproducible dependencies, secrets, hosted read-only app and operations guide | Clean-environment install/start, smoke checks and no startup writes |

Do not select solver details or claim feasibility/performance before the corresponding
inputs and acceptance tests exist. Each subtask remains a separate review checkpoint.

Task 02 delivered explicit public NESO sample exploration in the existing Data Explorer;
see NESO_SOURCE_DISCOVERY.md. The Task 02 user request authorizes these reads and UI
controls. Permanent import and saved event selection remain deferred to later review.

## Task 02B — complete history and analysis (complete; review pending)

Add explicit paginated full NESO retrieval alongside the existing sample. Compare complete
schemas, chronology, duplication and overlap; document every field and available date;
show event-level screening with full original records and eligibility. Provisional
recommendations use observed Downwards (demand reduction) per DFS rules, not generic
upward-reserve terminology. Winter 2025/26 archive identity/direction need confirmation;
November 2026 identified events are the provisional fallback. No final event persistence,
household integration, Turso or model implementation is authorised by this task.

## Task 02C — diverse events and interval view (complete; review pending)

Inspect all three official complete requirement resources, including 2023/24. Separate
source-identified event counts from date groups with missing IDs; document pre-bidirectional
service-regime evidence without filling raw fields. Review five winter delivery groups
across months/years and 1, 1, 1.5, 2, 3 hour durations, pending identity review. Add duration
filtering, comparison/detail/interval tables and national MW chart. Validate direct/derived
requirements, partial pieces, DST and duplicates. No household/Turso/model work.

## Task 02D — final Live-only event validation (complete; review pending)

Retain five reviewed candidates only after all mandatory criteria pass; explicit raw Live
status is independent of direction. Audit exact original CSV/API records and applicable
historical DFS definitions, mixed-history archive attribution, internal scenario IDs and
all interval values. The final comparison defaults to Live and admits PASS only; tests
remain available in raw/detail inspection. No household, Turso or model task is started.
See NESO_FINAL_VALIDATION.md and CURRENT_HANDOFF.md for evidence and results.

## Task 02E — final public NESO UI (complete; review pending)

Preserve Task 02D source records/IDs/validation and expose exactly five reviewed choices
immediately from a versioned reproducible local manifest. Default to no selected event;
render concise summary and direct-source interval table/chart only after selection. Keep
provenance/audit details collapsed and gate all existing advanced exploration behind a
separate toggle. Do not repeat discovery, change selections or start household/Turso/models.

## Task 03 — Low Carbon London Data Lab (complete; review pending)

The explicit Task 03 request authorises source acquisition, 100-household exploration and
five-house recommendation with replay now, ahead of battery configuration and feasibility.
Verified actual 4TU v1 files; audited 4,443 households and 17,520 timestamps. Prepared 90 Jan–Mar
heating-season days plus two replay dates. Added separate acquisition/parsing/analysis/UI,
deterministic selection and all 17 NESO half-hour comparisons. See LCL_DATA_LAB.md and
CURRENT_HANDOFF.md. No Turso or modelling work. Stop for review.

## Task 03B — finalise LCL Data Lab UI (complete; review pending)

Presentation finalisation of Task 03, not Task 04. Household Explorer defaults to the reviewed
five and no selected ID; all 100 candidates are a separate scope. Added summaries/help,
original chronological readings/CSV export, zoomable demand, complete-day quality marking,
typical daily profiles, stable-colour comparison and separately selected NESO replay/provenance
views. Source data, five-house recommendation, mapping and NESO logic are unchanged.
98 tests plus lint/format/type, real-app smoke and browser checks passed. See LCL_UI_GUIDE.md
and CURRENT_HANDOFF.md. Stop for review before any Task 04 work.

## Task 03E — final three-page architecture (complete; review pending)

Supersedes earlier five-page proposals. Exactly Data Explorer (default), Portfolio Configuration
and Simulation Lab. Simplified NESO/LCL tabs, national MWh equivalents, planned export-enabled
configuration and one integrated setup/run/results/comparison page. Immutable input/run/metric
contracts define unique append-only runs, equivalent-input experiments and scoped clear semantics.
No actual persistence adapter or simulation/model work. See UI_ARCHITECTURE.md. Stop before Task 04.


## Task 04 — battery model, configuration and preliminary feasibility (complete; review pending)

The explicit Task 04 brief supersedes historical task numbering above: Task 04 now delivers
five simulated batteries and preliminary battery-only feasibility; the next user-defined
Task 05 is household load forecasting. It does not authorize the old table's later work.

Implemented independent typed battery configuration/state/action/transition, grid exchange,
participation and sustainable capability. Functional Portfolio Configuration supports every
battery setting, safe common-setting application, defaults and validated JSON save/load.
Five reviewed NESO durations drive local kW commitment checks without national-MW scaling.
Simulation Lab reads current inputs and retains its disabled execution/results placeholder.
No measured source changes, imports, database writes, forecasting, optimisation or dispatch.

Verification: 178 tests, Ruff lint/format and ty pass; real localhost agent-API navigation,
all five events, capability warnings, editing, participation, apply-all/defaults and Simulation
Lab smoke checks pass. SHA-256 matches all 19 files in the Task 03E source/data baseline.
See BATTERY_MODEL.md and CURRENT_HANDOFF.md. Stop for review before Task 05.


## Task 04B — simplified configuration and battery demonstration (complete; review pending)

This user-defined UI/model refinement supersedes Task 04's per-household editor and load/apply-all
controls; it is unrelated to the historical 04b database-import row above. No new modelling stage.

Exactly four sections: one editable five-row battery table, mathematical equations, single-battery
charge/discharge/idle SOC demonstration and concise one-event commitment check. Global interval
is fixed at 0.5 h. Save validates/activates session values and offers durable JSON download;
Restore Defaults resets only working values until Save. Simulation Lab reads only saved assets.
Demonstration and feasibility use valid working values; temporary scenario checkboxes do not
change saved participation. The demo reuses strict Task 04 transitions with explicit feasible
power curtailment and recorded AC energy; it excludes demand/export constraints and event dispatch.

Verification: 216 tests pass, Ruff lint/format and ty pass. Real-app health/agent-API checks cover
all sections, SOC chart, charge/discharge/idle limits, save/download, all five events and unchanged
NESO/LCL navigation. Grid editing is unsupported by the agent API; AppTest exercises actual editor
state, all fields, save/restore, reruns, invalid cells and saved/working/scenario isolation. All
19 preserved source/data hashes match. See PORTFOLIO_CONFIGURATION.md and CURRENT_HANDOFF.md.
Stop after Task 04B; do not start forecasting, MILP, MPC or full event dispatch.


## Task 04C — final models, boundary performance and explainable feasibility (complete; review pending)

Focused refinement of Task 04/04B. Keep the five-row table, fixed global 30-minute interval,
Save/Restore semantics and three-page architecture. Add concise header help for efficiencies,
SOC, net export cap, permission and participation. Explain energy/SOC scheduling separately
from household grid power and RC voltage/transient models.

Replace duration/idle/curtailment demo controls with Charge/Discharge and positive rated operating
power, defaulting to the selected battery/mode rating. Compute time to the permitted SOC boundary;
reuse strict transitions at 0.5 h with an exact shorter final step. Handle initial-boundary zero
time without mutating initial SOC. Replace feasibility metric cards with one explained table,
dynamic equations and energy/power/combined shortfall diagnosis from individual battery limits.
Scenario participation defaults/rebases from working settings while preserving saved assets.

225 tests pass, including existing NESO/LCL/model/save/restore regressions; Ruff lint/format and ty
pass. Real localhost health/agent-API checks cover final labels/tooltips, charge/discharge times,
power validation, five reviewed event durations, one results table, causes, save/download and
navigation. AppTest covers grid edits, zero-time curves and state isolation (agent API cannot edit
grid cells). All 19 preserved source/data hashes match. See BATTERY_PERFORMANCE.md and handoff.
Stop after Task 04C; Task 05 forecasting, MILP, MPC and full event dispatch remain unstarted.


## Task 05A — load forecasting foundation and Simulation Lab (complete; review pending)

The explicit Task 05A request now authorizes forecasting data/contracts/UI/registry foundation,
but no training, predictions or dispatch. Three main pages remain. Simulation Lab now has
Forecast Model Development / Run Simulation & Results / Comparison & Evaluation tabs, with
saved-only battery inputs, explicit synthetic replay/forecast context and disabled Run/Clear.

Verified all five prepared series: 4,416 retained half-hours/92 retained days each, 4,416 valid
for three households and 4,415 valid for MAC001534/MAC001395. Jan–Mar spans all 90 calendar days
but contains two known missing cells across the portfolio; November 7/December 6 are additional
isolated validated days, not an annual continuous series. Raw annual source remains separate.
Use the proposed chronological Jan 1–Feb 28 / Mar 1–15 / Mar 16–31 split, with missingness explicit
and incomplete origin/target exclusion planned. Target is average kW = measured kWh / 0.5 h.

Data Explorer separates all-retained-study and selected-range summaries. Forecast development
reuses the same validated pipeline for five homes/aggregate, dates, units, measured chart, model
mathematics, editable hyperparameters, independent split config and honest empty results/registry.
Typed contracts, safe local JSON metadata/active-reference storage and future one-click/comparison
input contracts are implemented; actual model artifacts, fit/predict/orchestration are not.

262 tests plus Ruff lint/format and ty pass. Localhost smoke checks passed for three pages/tabs,
six historical series, actual split counts/missing-safe aggregation, independent dates, three
model choices, five replay contexts, unavailable execution and unchanged existing routes. All
19 preserved source/data hashes match; no production registry file/directory was created.
See FORECASTING_FOUNDATION.md and CURRENT_HANDOFF.md. Stop before Task 05B training.


## Task 05B — real multi-model forecasting (complete; review pending)

Three algorithms across five homes, shared origin-safe daily examples, held-out validation/test,
six comparison figures and explicit immutable local bundle save/activation. Saved inference
requires compatible provenance/schema and information cutoff <= origin. No dispatch or simulation.
See FORECASTING_MODELS.md for measured counts, results, artifact lifecycle and restrictions.
Stop after Task 05B for review; later control/optimisation work remains unstarted.


## Task 05C — database-first persistence and automatic reuse

Implementation and local integration verified; cloud provisioning/migration pending dedicated
Turso/R2 access. Versioned SQL, verified content-addressed objects, controlled idempotent bootstrap,
immutable portfolio versions and per-method model/result fingerprints with concurrency leases.
Run Models reuses exact results or persists missing fits automatically; no manual model save.
Historical cutoff rules remain. Dedicated-resource guards prohibit prior-project SQL/object writes.
See STORAGE.md and CURRENT_HANDOFF.md for status, setup steps, tests and known limitations.
Stop after Task 05C; no dispatch, MILP, MPC or full simulation.


### Task 05C cloud completion — 18 November 2026

Dedicated connections verified, migration/bootstrap completed, and three five-household method
bundles/results persisted to Turso/R2. Cold-cache identical request reused all three without
training or remote mutations. Bootstrap idempotency, object integrity, foreign keys and live
cloud-backed UI checks passed; 294 tests plus lint/format/type checks pass. See
TASK05C_CLOUD_COMPLETION.md. Task 05C complete; stop before Task 06.
