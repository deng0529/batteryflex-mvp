# Task 06 Battery Dispatch Optimisation and Simulation

Task branch `codex/task06-battery-dispatch-optimisation`. In Simulation Lab, open **Run
Simulation & Results**, choose the event and forecast, configure the five-battery scenario and
click **Run Optimisation** in a method tab. A completed single-event result unlocks the five-event
batch for that method. The dispatch CSV follows the selected forecast-planned or historical-replay
trajectory and contains all 48 intervals.

## Architecture and inputs

- `dispatch.py` defines the shared scenario, physical dispatch and scoring engine. It uses
  `BatteryConfig`, `BatteryState`, `BatteryAction` and `transition` from the existing battery model.
- `storage/dispatch_runs.py` verifies the existing saved forecast through the Task 05 resolver,
  records the exact model version, artifact and prediction identifiers, and reads the measured
  household replay from the forecast's exact immutable observation dataset. It snapshots the active
  saved database portfolio and preserves the event's reviewed UTC-to-2013 replay mapping.
- `ui/dispatch.py` and `ui/dispatch_results.py` implement the shared controls, method tabs,
  scenario-level battery edits, equations, execution trace, fulfilment, interactive charts and CSV.
  Comparison & Evaluation is still reserved for a subsequent task.

Task 05 provides the reviewed national NESO MW requirements, event windows, battery specifications,
all saved model options and complete 48-step replay demand for the five homes in all five events.
The 2013 load is historical replay, with original timestamps and source-quality rules retained.
The selector defaults to LightGBM, then offers Ridge Regression and Seasonal Naive. Forecasts are
loaded by explicit algorithm without training or model activation.

The five-home portfolio target, import/export rate, degradation, reserves and any scenario
connection limits are configurable assumptions. The baseline is uncontrolled household demand for
each evaluated trajectory. The original NESO national MW remain source data shown separately.
No official portfolio settlement baseline, award, settlement terms or household tariff were used.
There is no PV input. The dispatch day is fixed at 48 half-hours to align with the saved forecast.

## Model and controllers

Each interval is 0.5 h. Charge and discharge are nonnegative AC-side power. Energy advances as
`E_next = E + 0.5 × (eta_charge × charge − discharge / eta_discharge)`. Battery SoC, power,
participation, final hard reserve and household import/export limits are enforced. Net grid power
is `load + charge − discharge`. Positive grid power is import. Flexibility is baseline minus controlled grid
power, summed over homes. Battery discharge, avoided grid import and grid export are reported
separately. The algebra for this uncontrolled-demand baseline also gives flexibility as aggregate
discharge minus charge.

The shared weighted objective sums these terms:

| Term | Calculation | Raw unit |
| --- | --- | --- |
| Energy | Sum of half-hour import charges less export credit across households | £ |
| Shortfall | Sum of positive interval kW deficits × 0.5 h, or positive whole-event energy deficit | kWh |
| Degradation | Throughput in kWh × the configured degradation price | £ |
| Terminal | Sum of positive final target-energy deficits × the terminal deficit price | £ |

A hard final reserve bounds feasible energy. The terminal target has a soft deficit cost. The
shortfall coefficient has units £/kWh. The other objective weights are dimensionless. Interval
fulfilment counts each required half-hour individually. An interval surplus cannot offset an
interval miss. The separately configurable whole-event-energy target uses the event energy sum.

- **RBC** enforces physical and connection limits first. Before the event it charges toward the
  configured pre-event level up to the tariff ceiling. During the event it preserves the
  discretionary reserve and distributes required net reduction proportionally to available
  household discharge. Outside the event it supports connection limits and recovers the hard
  reserve or idles. It runs the same rules on current measured load in the replay and evaluates
  the objective after dispatch.
- **MPC** uses SciPy/HiGHS mixed-integer optimisation at every half-hour, with a default 12-step
  window. Only the current measurement replaces its forecast. Subsequent window rows are saved
  forecasts. The engine applies only the first action, then advances the battery state. The
  intermediate terminal lower bound keeps the day-end reserve reachable by rated charging.
  The soft target applies when the window reaches day end. For a whole-event energy target, each
  window receives a share of the outstanding energy budget based on its coverage of the remaining
  intervals. A distant event is explicitly optimised as its intervals enter the window.
- **MILP** solves the complete forecast day in one SciPy/HiGHS call. Continuous battery/grid/energy
  and slack variables and two binary operating directions prevent simultaneous charge/discharge
  and import/export at each home. Historical replay uses the scheduled actions bounded by
  current physical and grid limits. If realised constraints make final reserve infeasible the
  run reports failure. Solver status, elapsed time, objective, problem size and MIP gap are shown
  with the dispatch trace. A time-limited feasible incumbent is distinguished from a result
  optimal within the configured tolerance.

## Dedicated cloud replay results

Example assumptions were 10 kW in every reviewed event interval, export disabled, flat
£0.25/kWh import, £0.02/kWh throughput, hard terminal reserve 20% and soft target 50%.
Saved database battery settings and each event's exact default LightGBM model were used.
The cells below are realised event flexibility in kWh. Every scenario was physically executable.
All example requests scored **NOT MET**, with zero individual intervals reaching 10 kW.

| NESO event | 2013 replay | Requested kWh | RBC | MPC | MILP |
| --- | --- | ---: | ---: | ---: | ---: |
| 18 Mar 2025 | 19 Mar 2013 | 10 | 4.772 | 3.928 | 3.924 |
| 6 Nov 2025 | 7 Nov 2013 | 10 | 2.632 | 2.574 | 2.234 |
| 1 Dec 2023 | 6 Dec 2013 | 15 | 6.382 | 5.528 | 4.914 |
| 11 Jan 2026 | 13 Jan 2013 | 20 | 9.839 | 9.515 | 8.485 |
| 2 Feb 2025 | 3 Feb 2013 | 30 | 10.150 | 9.518 | 9.066 |

On 18 March, each method forecast-planned 4.416 kWh of event flexibility. With export disabled,
demand and the grid import floor cap reduction. The realised optimisation trajectories also
encountered battery energy limits. Export was zero for all three. Values below are realised.

| Controller | Delivery kWh | Shortfall kWh | Electricity cost £ | Savings £ | Evaluated objective £ |
| --- | ---: | ---: | ---: | ---: | ---: |
| RBC | 4.772 | 5.228 | 16.222 | 0.007 | 120.972 |
| MPC | 3.928 | 6.072 | 10.668 | 5.561 | 133.919 |
| MILP | 3.924 | 6.076 | 11.070 | 5.159 | 134.052 |

| Battery | Initial kWh | RBC event kWh / final kWh | MPC event kWh / final kWh | MILP event kWh / final kWh |
| --- | ---: | ---: | ---: | ---: |
| MAC001391 | 8.000 | 0.194 / 7.796 | 0.194 / 4.704 | 0.194 / 5.143 |
| MAC003288 | 6.500 | 0.481 / 7.493 | 0.481 / 2.000 | 0.481 / 2.567 |
| MAC000143 | 9.000 | 0.892 / 8.060 | 0.746 / 2.000 | 0.742 / 2.227 |
| MAC001534 | 5.500 | 0.781 / 7.177 | 0.781 / 2.000 | 0.781 / 2.673 |
| MAC001395 | 7.500 | 2.424 / 5.445 | 1.725 / 2.000 | 1.725 / 2.138 |

## Storage and reproducibility

A deterministic fingerprint includes scenario batteries and settings, replay mode, event mapping
and source, exact forecast references, engine namespace and SciPy version when applicable.
Turso indexes dispatch runs in a Task 06 namespace in the existing key/value registry. This
avoids changing the existing simulation tables whose forecast foreign key points to the legacy
forecast registry. The run bundle is verified and content-addressed in R2. Lease-based
registration prevents concurrent runs of the same fingerprint and leaves previous completed runs
addressable. Publication uses conditional object creation and transactional metadata inserts.
A saved-result lookup happens before optimisation or upload. Storage connection and app startup
perform no Task 06 writes. No schema migration or deployment was required.

All 15 live runs wrote only new Task 06 results, their object references and temporary leases.
The verification wrapper blocked other writes. The first event's three methods were retrieved by
a separate process using an empty object cache with optimisation, uploads and writes blocked.
All 27 pre-existing cloud tables matched the prior Task 05 snapshot after excluding the 15
new run indexes and their object references. All 55 protected Task 05 file hashes matched.
Per-run results, solver details, UI snapshots and audit evidence are in `outputs/task06/`.

## UI verification

Two fresh local Streamlit processes with separate empty disk caches used dedicated Turso/R2
read-only. In each process, the normal Simulation Lab route restored the same first-event RBC,
MPC and MILP results through the Run Optimisation buttons. The first process rendered five
dispatch charts per method, execution and solver traces, the five-battery table, 48-step
downloadable dispatch and interval-by-interval fulfilment. It also restored the complete
five-event MILP batch and loaded the alternate saved Ridge Regression and Seasonal Naive
forecasts. The runs attempted no optimisation, cloud writes or uploads in either process.
Evidence includes `streamlit-phase-1-{RBC,MPC,MILP}.json`, the corresponding phase 2
snapshots, `streamlit-batch.json` and `preservation.json`. Both local servers were stopped.

## Tests

- Full regression suite on Windows with localhost sockets enabled. **334 passed in 355.69 s.**
- Nine dispatch tests cover energy conservation, operating limits, grid aggregation and export,
  interval and aggregate goals, RBC priorities, causal MPC windows, MILP status and numerical
  objective agreement, invalid inputs and immutable reuse across repository instances.
- Ruff lint, Ruff format verification and source/script type checks passed.

## Limitations and follow-up

The simulator has flat scalar tariffs, an uncontrolled-demand baseline, individual connection
limits and no PV, feeder constraints, uncertainty reserve or market settlement model. The MPC
look-ahead is finite. Nominal future charging capacity is a reachability approximation and does
not guarantee that an unforeseen realised connection restriction can be satisfied. Replay
reoptimises MPC against only presently revealed actual load and assesses a fixed day-ahead
MILP schedule under realised limits. This is a five-home historical simulation.
Electricity savings compare simulated bills. A controller can realise bill savings by drawing
down the configured starting energy. The objective accounts for terminal energy via its hard
reserve and soft deficit cost.

For the next task, compare exact compatible runs using the immutable provenance, and evaluate
trade-offs across shortfall, electricity costs, terminal energy and forecast errors. A study
that claims settlement eligibility also needs separately verified participant-specific rules,
baselines, metering and award data.
