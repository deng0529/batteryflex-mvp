# Task 06 MPC results, saved comparison and persistent caching

Implemented on the existing `codex/task06a-rbc-export-replay` development branch. RBC, MPC
and MILP optimisation formulations and replay controls are the existing implementations.

## MPC control results

The MPC method now has a collapsed **MPC Step-by-Step Control Results** panel. It selects
Forecast Planned or Historical Replay, shows each event solve, and lets the reader inspect
the five batteries for one interval. The proposed first action and requested setpoint come
from the solver trace. Executed power comes from the trajectory after physical and export
corrections. Only current measured demand replaces a forecast value in the replay window.
There is no look-ahead to future actual demand.

For the saved 18 March 2025 example, with a 12-step configured horizon, there were 48
replay solves over the day. The event contained two execution intervals.

| Control time (GMT) | Actual solve horizon | Solver objective (£) | MIP gap | Executed discharge (kW) | Delivered (kWh) | Cumulative (kWh) | Remaining (kWh) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 18:00 | 12 | 5.7932 | 0% | 10.0 | 5.0 | 5.0 | 5.0 |
| 18:30 | 11 | 5.7903 | 0% | 10.0 | 5.0 | 10.0 | 0.0 |

The 18:30 window uses 11 steps because the model stops at midnight. The objectives above
are the respective HiGHS returned values over different horizons. Executed replay costs
reconcile to £13.3444 across the day, including weighted electricity £11.2134, degradation
£0.6310 and a single £1.5000 terminal penalty. Interval-mode obligations retain past misses
and future requirements. Whole-event mode assigns its remaining shortfall cost at the last
event interval. The objective ledger records the terminal deficit once at the end of the day.

## Fair comparison

**Comparison & Evaluation** reads completed saved results directly and groups them by
shared event window, batteries, grid constraints, prices, objective and terminal settings,
forecast artifact, replay data and protocol, and time grids. End-state and wallet trade-offs
are shown separately from the strict half-hour flexibility check. Tuning used exclusively
by a controller is recorded in its run. It does not define compatibility. Distinct shared
inputs, including £0.10, £0.25 or £0.50/kWh terminal coefficients, remain separate groups.
The chart compares the selected trajectory. The summary includes both when both are saved.

For the default £0.10 case on 18 March, all three methods met both intervals. Replay
objectives were £16.340 for RBC, £13.344 for MPC and £13.288 for MILP. Final stored energy was
30.459, 10.000 and 11.324 kWh respectively. Those results illustrate the trade-off between
electricity cost, battery throughput, and energy left for later use. The configured weights
determine the objective ordering. Runs with checked hard violations are excluded from ranking.

## Persistence and recovery

- Existing Turso structures are reused. The result index uses namespaced entries in
  `system_settings`, alongside the existing `objects` table and `model_leases`. Existing
  SQL schema and R2 bucket stay in service. Version 1 bundles remain readable.
- The canonical fingerprint includes scenario values, method, controller and solver
  settings, engine and replay protocol, time units and horizons, baseline, immutable
  event/forecast/replay metadata and ordered batteries. JSON keys are sorted, equivalent
  numbers are normalised and known timestamps are normalised to UTC. The terminal price is
  included. Cosmetic settings are outside the fingerprint. Exact legacy keys are checked
  for compatibility before a new run.
- A hit verifies the referenced result bytes and reconciles the numerical result. It skips
  the controller and measured-demand loading. Comparison discovers saved bundles independently
  of the forecast model loader.
- A miss acquires a scoped lease, calculates both trajectories, validates their arrays and
  constraints, then creates a content-addressed `task06-dispatch-v2` R2 bundle. The index
  publishes status, scenario, solver metadata, timestamps, summary metrics and object
  reference. The bundle includes both trajectories and full traces. New MPC bundles also
  contain the per-interval executed objective ledger.
- A running lease prevents a duplicate solve. A staged object pointer allows a retry to
  publish an already-uploaded, validated bundle if the final SQL transaction fails.
  The completed index and staging cleanup are transactional. Failures are recorded separately
  when the database is reachable. Corrupt or missing completed objects cannot be served.
  Their replacements are published under append-only repair references, preserving history.

## Preview

From `the BatteryFlex repository root`, run `..venvScriptspython.exe -m streamlit run app.py`.
Open **Simulation Lab → Comparison & Evaluation** for the saved comparison. For the MPC
details, open **Run Simulation & Results**, select the 18 March 2025 event and MPC, choose
**Run Optimisation**, then expand **MPC Step-by-Step Control Results**. Live UI evidence is
in `outputs/task06-comparison/comparison.json` and `outputs/task06-comparison/mpc.json`.

## Verification

- **345 regression tests passed**. The focused dispatch and persistence suite passed 20
  tests, covering numerical reconciliation, MPC event records, cache hits and misses,
  terminal-price isolation, legacy compatibility, corrupted-object repair, and recovery
  after an upload succeeded but SQL publication failed. Ruff and type checks passed.
- Dedicated Turso/R2 saved two new £0.25/kWh sensitivity results. A fresh read-only
  repository restored both v2 results and the original £0.10 legacy results with
  optimisation, measured-demand loading and writes blocked. All 18 previous result
  bundles matched their originals. The store now contains 20 completed results.
- Fresh read-only Streamlit verified three default methods and two sensitivity methods.
  MILP is marked not yet run for the sensitivity group. RBC replay objective remained
  £16.3399 and MPC replay objective was £15.5944 at £0.25/kWh. Evidence is in
  `outputs/task06-comparison/persistence.json` and `comparison-sensitivity.json`.
- The live MPC panel displayed two event intervals with five selectable battery rows.
  Its 48 solves remained available through the stored trace. No forecasting was retrained.

## Files

- `src/batteryflex/dispatch_evaluation.py` validates trajectories and reconstructs the ledger.
- `src/batteryflex/storage/dispatch_runs.py` and `storage/objects.py` handle saved-first
  discovery, versioning, verification, staging and recovery.
- `src/batteryflex/ui/dispatch_results.py`, `ui/dispatch.py`, `ui/dispatch_benchmark.py` and
  `ui/planned.py` provide the MPC panel and saved comparison.
- `tests/test_dispatch_persistence.py`, `tests/test_app.py` and `tests/test_forecast_ui.py`
  cover saved execution, costs, grouping, repair and the updated navigation.
- `docs/TASK06_MPC_COMPARISON.md` and `docs/CURRENT_HANDOFF.md` document the work.

## Interpretation limits

The existing whole-event energy score can pass while a particular half-hour misses its
power reference. The comparison's power check still evaluates every event interval.
An MPC solver objective is a forecast-window quantity. Comparing consecutive solver values
without accounting for horizon and starting state can misstate its performance.
Scenario comparisons do not establish NESO settlement eligibility or a universal controller
ranking. Charts use available results under a common scenario and a reproducible replay.
