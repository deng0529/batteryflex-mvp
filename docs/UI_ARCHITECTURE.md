> Task 05 final cleanup supersedes the development UI below: retain the main exact-date table, model controls, Run Event Models, selectable household/portfolio full-day curves, accuracy bar chart and visible full-day MAE/RMSE table. Remove quality/detailed-date, recommendation/version, extra evaluation and peak sections from this page. Backend resolution/research code and all cloud records remain unchanged. [Cleanup report](TASK05_FINAL_UI_CLEANUP.md).

> Forecast activation controls/status have been removed. The selected event shows its recommended saved algorithm/version independent of chart controls. Planning resolves the same saved reference directly, with execution still disabled. [Current resolver contract](FORECAST_RESOLVER.md).

> Task 05E supersedes the forecast UI below: event-only development, immediate exact saved calendar/usable dates, one household/portfolio full-day chart with event shading and legend selection, full-day RMSE, expandable evaluation/peak tables. Existing Run/explicit event activation and all three tabs remain. [Current report](TASK05E_PEAK_ANALYSIS.md).

> Task 05D preserves the three Simulation Lab tabs and adds Event-aligned forecasting within Forecast Model Development. Five event selections restore saved cloud results; six GMT forecast curves and one RMSE comparison expose full-day/event/holdout errors. Activation is explicit and event-specific; there is no manual Save Model. [Current report](TASK05D_EVENT_FORECASTING.md).

> Task 05C: A4 Run Models means load existing or train/persist missing. Saved exact results
> restore on opening the tab. Save Model/version-entry controls are removed; validation-based
> selection and explicit Activate Model persist in SQL. Five household curves, grouped test
> RMSE and the automatic conclusion remain. Portfolio confirmation persists immutable versions.
> Three pages/tabs and disabled simulation execution remain. See [storage details](STORAGE.md).

> Task 05B final A4 refinement: Run Models and a common test-day selector; five household
> 48-step curves; one interactive grouped full-test RMSE chart; computed winner conclusion;
> validation-portfolio-based save recommendation and explicit Save/Activate controls.
> No accuracy or technical tables in A4. Portfolio metrics remain internal; the portfolio
> curve is removed from the main display. See [forecasting UI details](FORECASTING_MODELS.md).

> Task 05B now implements forecasting training/evaluation, safe bundles and explicit
> A4 save/activation. Earlier foundation-only statements below are historical.
> See [current forecasting specification and measured results](FORECASTING_MODELS.md).

> Task 05A update: exactly three main pages remain. Simulation Lab now contains Forecast Model
> Development, Run Simulation & Results, and Comparison & Evaluation tabs. Data Explorer separates
> full-study and selected-range summaries. Portfolio Configuration and saved-only inputs remain
> intact. No forecast training, predictions or dispatch. See
> [FORECASTING_FOUNDATION.md](FORECASTING_FOUNDATION.md). Earlier layout descriptions below are historical.

# Final three-page UI and future retained results — Task 03E

Date: 17 November 2026. This architecture supersedes any earlier five-page proposal and the
Task 03B public exploration layout. It introduces no battery, forecasting, MILP or MPC engine.

## Product and navigation

Audience: flexibility aggregator, conducting automated or manually initiated historical
experiments. The banner reads BatteryFlex — Automated VPP Flexibility Optimisation & Control,
with a historical simulation/research label and explanatory automatic workflow:

NESO Request → Forecast → Feasibility → Optimisation → Simulated Dispatch → Evaluation

Exactly three `st.Page` entries: Data Explorer (default, route /), Portfolio Configuration
(/portfolio), Simulation Lab (/simulation). No Operations Dashboard, Results & Evaluation or
individual modelling pages. The latter two pages clearly distinguish planned functionality.

## Data Explorer

`ui/explorer.py` presents two native tabs, tracked with `on_change='rerun'`; only the active
tab renders. The default NESO selection is empty. It reads the frozen reviewed manifest and
existing interval generator. Selected summary shows date/GMT window/duration/national MW,
original interval count, and energy equivalent sum(MW × interval hours). Each half-hour table
row retains original interval instants, MW and derived MWh. Energy is requested, not delivered.
The large plot and technical panels are absent. Provenance, reviewed row IDs/hashes and
validation remain intact in source modules/assets, with an official source link in the view.

LCL uses the existing verified/cached local artifacts. Five recommended households only;
select a household to show its original anonymised ID, London study area, coverage and
summary. One GMT dated demand line plus chronological original readings; comparison switches
to one typical-daily profile overlay and table for the same five homes. Original kWh and
source interval-END text remain intact. January–March summaries are clearly distinguished
from selected-range readings and from full-source 2013 coverage. Only 92 dates are retained.
No addresses, fabricated assets, missing-to-zero conversion or full-source rerun parsing.

Detailed Task 03B lab and advanced research acquisition/review components remain unregistered
internal components. A standalone test harness exercises their existing regressions; they do
not add product pages, public toggles or technical clutter. Pure source validation tests are
unchanged. The Task 03B UI guide is historical; this document describes current navigation.

## Portfolio Configuration

Explicit planned state pending Task 04. Future five-battery fields: capacity kWh, maximum
charge/discharge kW, initial/minimum/maximum SOC %, efficiency convention/value, export permission,
optional export-limit kW. Export-enabled is the intended default; no numerical values or
simulated battery objects are assigned. Fields are documented as a planned schema, rather
than ineffective editable settings. No battery dynamics, export constraints or feasibility.

## Simulation Lab

Four sections on one page:

- Experiment Setup: reviewed event, Rule-based/MILP/Rolling MPC strategy, planned export mode.
  Export-enabled default. Current battery configuration and future commitment explicitly unset.
- Run Simulation: engine-not-implemented message and disabled Run Simulation action. A future
  invocation must orchestrate the whole explanatory pipeline, not fake a progress/result flow.
- Results: explicit absence of successful runs. Future display includes event/strategy,
  commitment, delivered flexibility, shortfall, grid import/export, SOC, schedules, cost/runtime.
- Comparison & Evaluation: empty until compatible runs exist; disabled Clear Results for the
  current experiment. No example result tables, zero-valued metrics or fake dispatch charts.

Planning controls create no runs and assign no operational commitments. Durable storage,
configuration submission, model execution, result rendering and metric calculation await later tasks.

## Future append-only history contract

`simulation_contracts.py` contains data contracts and pure record-handling functions, not a
persistence adapter. No production page constructs runs or calls a model. Test fixtures exist
only under tests and are not included as production data.

`ExperimentInputs` freezes these fields:

| Field | Meaning |
| --- | --- |
| event_id | Existing internal BatteryFlex NESO scenario ID; not an invented official NESO ID |
| battery_configuration_json | Canonical versioned five-house battery configuration snapshot |
| initial_soc_json | Canonical household→initial SOC %, recorded even when configuration contains it |
| export_settings_json | Canonical enabled/disabled permission, optional limit kW and convention |
| portfolio_commitment_kw | Explicit future commitment, independent of national NESO MW |
| forecast_assumptions_json | Model/version, issue/horizon/baseline/weather assumptions needed for equivalence |
| input_data_references_json | Source versions/hashes, household IDs/date ranges, original NESO rows and replay mapping version |

JSON is normalized at construction and stored as immutable text; dictionary key order cannot
change grouping. Input objects cannot later mutate a stored JSON snapshot. `experiment_id` is
BF-EXPERIMENT- plus SHA-256 of the complete canonical input record. A different event,
configuration, initial SOC, export policy, commitment, forecasts or data references creates a
different experiment. Strategy and run creation time are deliberately outside this fingerprint.
Future input admission must validate required schema, source integrity and unit conventions;
these contract helpers do not establish battery feasibility or operational validity.

`SimulationRun` records UUID run_id, completion UTC, frozen inputs, strategy, immutable results
JSON and typed evaluation metrics. Repeated runs of one strategy get different UUIDs.
`append_run` returns a new tuple, rejecting duplicate run IDs instead of upserting by strategy.
`compatible_runs` admits only identical experiment fingerprints. `clear_experiment` removes
only the explicitly selected experiment in a new tuple, preserving all other experiments.
These are pure future-storage semantics, with no implicit writes, sessions or database work.

Future durable storage must use unique run IDs, append-only inserts, an indexed experiment
fingerprint, atomic input/result/metric snapshots and an explicit scoped clear/delete action.
A different strategy never overwrites an old run. Repeated trials stay separately selectable;
no automatic strategy averaging or incompatible performance comparison. Forecast differences
are incompatible unless a future reviewed comparison policy explicitly defines otherwise.

## Future result/evaluation payloads

Result JSON must preserve original event/run/household references and interval timestamps,
commitment/delivery/shortfall, grid import/export, SOC trajectories and dispatch schedules with
units and sign conventions. Economic assumptions and tariff references belong in input refs
or forecast assumptions when they affect comparability. Cost/runtime and the following metrics
must be retained with each successful run, not recomputed from changing live settings:

- Commitment fulfilment (%)
- Delivery shortfall (kWh)
- Electricity cost (£)
- Battery energy throughput (kWh)
- Final SOC by household (%)
- Computation time (seconds)

No definitions/equations for their evaluation are implemented here. Final SOC is per household,
not a misleading sum/mean. Input/result schema versions and migration review belong with the
later durable storage/engine implementation. This task defines the shape and retention rules.

## Verification and limitations

Public navigation, tabs, all five event energies/17 intervals, five household choices, one-chart
views, honest planned states and append/non-comparison/clear rules are tested. Existing source
and advanced-component checks are retained. Local Streamlit smoke tests cover each real route,
all reviewed events/households and both exploration tabs without external calls.

Partial 2013 coverage, anonymous attributes and calendar replay limitations remain. No actual
simulation history survives restarts because no engine/storage exists; the UI explicitly states
this. Persisting real successful runs and activating Clear Results are later tasks. Stop for review.
