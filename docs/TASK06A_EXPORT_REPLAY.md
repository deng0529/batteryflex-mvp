# Task 06A export and paired forecast–replay evaluation

Simulation Lab → Run Simulation & Results now executes two trajectories from a single action in
each of the three method tabs. The result opens with NESO Request Fulfilment and places Forecast
Planned beside Historical Replay. It then shows paired battery and portfolio totals, signed
replay differences, the controller rules and model, objective contributions and tariff economics,
overlaid interactive charts, a 48-step CSV for each trajectory, and an evidence-based conclusion.

## Export and RBC

The scenario enables export automatically for participants. A configured export connection cap
is retained. A blank cap uses the battery's discharge rating as a finite simulation assumption.
The UI identifies those assumed caps and writes them to run provenance. Edits are applied to
scenario copies of the database portfolio. Export is available in event intervals and restricted
to serving the interval target or outstanding event energy target. The optimisation models use
a binary implication to enforce this condition. Replay can trim a scheduled export after
applying local battery and connection bounds. Discretionary behind-the-meter discharge may
still reduce import beyond the target. Grid export, battery supply to the home, net import
reduction and battery discharge are measured separately.

RBC enforces feasible signed action bounds first. It protects the hard reserve before
discretionary discharge, prepares towards the pre-event target when the tariff permits, then
allocates incremental event discharge by each battery's share of feasible availability above
reserve. Grid export raises the feasible discharge ceiling to load plus permitted export.
Outside the event RBC recovers the hard reserve or idles unless a connection bound requires an
action. The soft final energy target affects the score. It does not schedule RBC actions.
The trace records the triggered rule, precharge/reserve or event allocation inputs, requested
and applied action, feasible bounds and physical or export-policy adjustments.

## Comparison and causality

The existing Task 06 replay was already causal. RBC runs the same rules with current measured
load. MPC replaces only the current row in the rolling forecast window. MILP keeps the original
forecast plan and projects actions into the realised feasible envelope. Task 06A retains this
information order and makes replay mandatory in the interface. Forecast Planned and Historical
Replay share event steps, rates, battery parameters, reserve, target and connection policy.
Historical Replay is the primary simulated result.

With the same uncontrolled-demand baseline definition in both trajectories, calculated
flexibility equals aggregate battery discharge less charge. If event actions match, the load
forecast difference can change import, export or cost while leaving flexibility unchanged.
If the actions differ, the comparison decomposes the event flexibility difference into
requested-action differences and subsequent replay corrections. It reports observed constraint
boundaries and separates physical adjustments from export-policy adjustments. The attribution
does not isolate a forecast-error counterfactual where demand and battery state interact.
When trace data are insufficient the app reports that the cause of the action change cannot be
established. The power-window result reads each interval independently.

## Persistence and scope

Both evaluations and the exact forecasts, rates, effective caps, source assumptions, settings
and traces share one immutable run ID. The export policy and effective limits are in the
fingerprint. Legacy run fingerprints remain addressable through the existing persistence
path, and past no-export records stay available. The original national NESO requirements are
displayed separately from the configured portfolio target. The model evaluates historical
replay, with no settlement certification.

## Example and live verification

Original event **18 March 2025, 18:00–19:00 GMT**, using **19 March 2013** measured demand
and the saved LightGBM forecast. The scenario set a 10 kW target for each half-hour, for
10 kWh total, and used the individual simulated 5 kW export caps derived from discharge
ratings. Import was £0.25/kWh and export credit £0.05/kWh. All three methods met both
intervals on both trajectories with zero shortfall.

| Method | Event delivery planned / replay (kWh) | Event export planned / replay (kWh) | Net bill planned / replay (£) | Objective planned / replay (£) |
| --- | ---: | ---: | ---: | ---: |
| RBC | 10.000 / 10.000 | 5.584 / 5.652 | 16.332 / 16.045 | 16.627 / 16.340 |
| MPC | 10.000 / 10.000 | 5.584 / 5.927 | 11.436 / 11.213 | 13.553 / 13.344 |
| MILP | 10.000 / 10.000 | 5.584 / 5.927 | 11.361 / 11.443 | 13.364 / 13.288 |

Event demand MAE was **0.268 kW per home per half-hour** and measured event consumption
was **0.356 kWh higher**. RBC and MILP applied identical event actions across both trajectories.
RBC's higher replay export despite higher aggregate measured demand reflects the differences
in demand across homes and intervals. Export is calculated separately for each home before
aggregation. MPC changed household actions in both intervals, with zero net effect on event
delivery. No event action was corrected for physical or export-policy limits in this example.
Across the full day, measured load was 1.201 kWh below the forecast. RBC actions were
unchanged all day and MPC actions differed at 37 intervals. The MILP schedule was corrected
in 22 intervals outside the event to prevent export when measured demand was lower than the
scheduled discharge. Its final stored energy rose from 10.000 to 11.324 kWh.

| RBC battery | Event discharge planned / replay (kWh) | Event export planned / replay (kWh) | Final stored planned / replay (kWh) |
| --- | ---: | ---: | ---: |
| MAC001391 | 2.000 / 2.000 | 1.667 / 1.806 | 5.892 / 5.892 |
| MAC003288 | 2.000 / 2.000 | 1.362 / 1.519 | 5.892 / 5.892 |
| MAC000143 | 2.000 / 2.000 | 1.258 / 1.108 | 6.892 / 6.892 |
| MAC001534 | 2.000 / 2.000 | 1.023 / 1.219 | 5.892 / 5.892 |
| MAC001395 | 2.000 / 2.000 | 0.275 / 0.000 | 5.892 / 5.892 |
| Portfolio | 10.000 / 10.000 | 5.584 / 5.652 | 30.459 / 30.459 |

The live Streamlit run verified the primary summary order, paired tables, both 48-step
schedules, all five charts per method and expandable controller traces. A second server with
an empty disk cache restored the same three paired results with all writes, optimisation
and uploads blocked. Both servers were stopped. The 15 prior run indexes remained intact.
All 27 pre-existing tables and 55 protected Task 05 file hashes matched the established
baseline after accounting for Task 06 and 06A result indexes and objects.
See `outputs/task06a/` for the example data, audit and both sets of UI snapshots.

## Tests

The full regression suite passed with **339 tests**. Dispatch coverage includes automatic
capped export for each controller, energy conservation, proportional allocation, tariff
decomposition, causal inputs, paired aggregation, trace attribution and compatibility with
saved results. Ruff lint, Ruff format verification and source/script type checks passed.

## Limitations and next steps

The assumed connection cap is a scenario input. Use verified per-home export caps when
available for a connection-specific study. No feeder-level constraint, PV, inverter response
model, or settlement rule is applied. Tariffs are flat scenario values. The replay trace
shows where constraints bind but cannot measure the value of relaxing an individual constraint
without a counterfactual. Future work can test several forecast-error and connection-cap
scenarios before comparing policy robustness.
