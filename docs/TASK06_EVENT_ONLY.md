# Task 06 Experiment A — Event-only flexibility dispatch

Implemented locally on the existing development branch. The only new simulation protocol
is STANDARD event-only execution. Full-day results retain their provenance and fingerprints.
The legacy full-day runner remains callable separately. The new comparison accepts only
event-only results.

## Boundaries and qualification

The former runner executed all 48 half-hours of the replay day, beginning at midnight and
including preparation and later recovery. Task 06 now slices the immutable saved forecast
and measured replay to the event's original GMT clock window. Battery states reset at the
first event boundary for each method and each independent event.

| Registry event | GMT window | Half-hours | Portfolio energy at 10 kW |
| --- | --- | ---: | ---: |
| 18 March 2025 | 18:00–19:00 | 2 | 10 kWh |
| 6 November 2025 | 17:00–18:00 | 2 | 10 kWh |
| 1 December 2023 | 16:30–18:00 | 3 | 15 kWh |
| 11 January 2026 | 17:00–19:00 | 4 | 20 kWh |
| 2 February 2025 | 16:00–19:00 | 6 | 30 kWh |

These dates and windows match the reviewed registry. The 10 kW setting is a portfolio
simulation assumption. It is separate from the national NESO requirement.

The verified saved battery configuration has five 10 kWh batteries, 5 kW limits per
battery in each direction, 20–100% SoC bounds, and approximately 0.9487 charge/discharge
efficiencies. The editor has the requested synthetic 95%, 90%, 85%, 85%, and 90% starting
states for MAC000143, MAC001391, MAC001395, MAC001534, and MAC003288 respectively.
The five batteries had 50.00 kWh installed, 44.50 kWh initially stored, 10.00 kWh reserved,
32.7296 kWh available for discharge and 25 kW rated discharge. Against the longest
30.00 kWh request, the usable energy margin was 2.7296 kWh.

A shared zero-shortfall feasibility solve checks the forecast, participation, export/import
limits, individual power and energy bounds, and the hard final reserve. It reports a
separate runtime and provides no schedule to the controllers. Infeasible or unconfirmed
portfolios stop before control. Forecast qualification does not promise realised delivery.

## Control and accounting

The existing physical equations, power limits, energy constraints, export policy and
four objective coefficients apply. Running costs cover only executed half-hours, and
the terminal cost applies once at the event end. The 50% terminal SoC remains a soft
preference. The configurable hard reserve is enforced.

RBC uses only its event allocation. MPC uses the saved forecasts and battery state at each
boundary, with its horizon truncated by the event end. Standalone MILP solves the complete
forecast event once and uses that schedule throughout replay. At execution, all controllers
pass through the same safety and export checks. The completed actual half-hour average
is used only for the replay's execution limits and accounting. It is unavailable to the
controller at the initial decision boundary. No new rolling forecast model or observed
intra-interval telemetry was introduced.

For the three-hour example, MPC's replay executes six solves with horizons 6, 5, 4, 3,
2 and 1. Forecast Planned is a separate counterfactual and has six of its own solves.
RBC has zero numerical solves. Standalone MILP has one shared event solve and six replay
execution steps, with zero reoptimisations. Event qualification is timed separately
from these controller counts.

| 2 February 2025 replay | Delivered | Weighted objective | Controller solves in replay workflow |
| --- | ---: | ---: | ---: |
| RBC | 30.00 kWh | £0.8198 | 0 |
| MPC | 30.00 kWh | £1.0088 | 6 |
| Standalone MILP | 30.00 kWh | £0.9682 | 1 shared initial solve |

MPC's objective reconciles as −£0.803496 electricity + £0.000000 shortfall + £0.600000
degradation + £1.212278 terminal deficit = £1.008782 after rounding. Overlapping MPC
forecast objectives are never added into this figure. Simulation intervals, proposed and
executed actions, predicted states and terms, actual terms and cumulative running costs
are retained. The interface offers interval and household drill-down.

The three-hour replay had zero charging and 30 kWh of AC discharge. At the common
discharge efficiency, that withdrew 31.6228 kWh from storage, including 1.6228 kWh of
conversion loss. Final stored energy was approximately 12.8772 kWh. The 50% preference
corresponds to 25 kWh, giving a 12.1228 kWh soft deficit at £0.10/kWh.

## Persistence, comparison and limitations

The existing SQL tables, leases and content-addressed bundle infrastructure are reused.
Event-only fingerprints specify EVENT_ONLY, STANDARD, event-window-v1 and the forecast-at-
boundary protocol in addition to the event, source artifacts, solver settings and battery
scenario. The legacy numerical fingerprint path omits the new default mode field.
Raw event execution records and versioned Python evidence are inside the saved bundle.
Older explanation versions can be regenerated from saved trajectories without solving.
The comparison groups matching inputs while keeping controller settings distinct. It
includes one-event and five-event views, missing runs, cost components, battery traces
and computation totals. It does not initiate execution.

Verification used saved LightGBM forecasts and measured replay inputs read through a
guarded cloud connection. All 15 event-only simulations ran and persisted exclusively in
isolated local SQLite and filesystem object storage. All recorded trajectories met their
requests in this sample. Every scenario was reopened through a new repository instance.
All 15 second calls were verified cache hits and skipped the replay loader. No new
production runs were executed. The local outputs are in outputs/task06-event-only/.
A separate read-only audit confirmed all 32 existing cloud bundles retained valid
full-day fingerprints.

- [Event dashboard screenshot](../outputs/task06-event-only/task06-event-results.png)
- [Comparison screenshot](../outputs/task06-event-only/task06-event-comparison.png)
- [Five-event summary screenshot](../outputs/task06-event-only/task06-five-events.png)
- [Three-hour control-step records](../outputs/task06-event-only/three-hour-control-records.json)

## Automated verification

**359 tests passed** in the final full run. Ruff lint and format checks and source type
checks passed. The first full run surfaced an outdated chart-count assertion in the
Streamlit integration test. The expectation was updated for the new plots, and the focused
rerun and final suite passed. Structural checks cover the five registry windows, causal
decisions, numerical reconciliation, the three solver-count patterns, partial batch
recovery, saved-first reuse and explanation regeneration.

## Files and preview

- \`dispatch.py\` and \`dispatch_evaluation.py\` parameterise the existing model and validation.
- \`dispatch_event.py\` adds qualification and versioned execution evidence.
- \`storage/dispatch_runs.py\` isolates event-only saved runs and supplies qualification/evidence.
- \`ui/dispatch.py\`, \`ui/dispatch_results.py\` and \`ui/dispatch_benchmark.py\` provide the revised views.
- \`tests/test_dispatch_event.py\`, \`tests/test_dispatch_dashboard.py\` and
  \`tests/test_forecast_resolver.py\` cover event boundaries, causality, accounting, caching and UI.
- \`docs/CURRENT_HANDOFF.md\` and this report document the update.

Start the normal app with \`.\.venv\Scripts\python.exe -m streamlit run app.py\` from BatteryFlex.
For an already-completed isolated preview, run
\`.\.venv\Scripts\python.exe -m streamlit run outputs/task06-event-only/preview.py\`
with PYTHONPATH set to src. Add \`?view=comparison\` to the URL for the comparison view.
