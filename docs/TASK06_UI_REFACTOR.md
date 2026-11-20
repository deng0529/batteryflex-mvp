# Task 06 results-first UI refactor

19 November 2026. Existing development branch `codex/task06a-rbc-export-replay`.

## Results layout

All three controllers use the same result order. NESO fulfilment shows the event window,
required power and energy, the forecast-planned and replay statuses, and a grouped kW chart
for the event half-hours. A short conclusion reports any interval deficit in kWh. The paired
summary shows delivered flexibility, configured target fulfilment, event export, net electricity
cost, objective and final portfolio SoC. The interval table shows each power check. The
five-battery table pairs the initial and final SoC, daily charge and discharge, event
contribution, event export and demand supplied by the battery. The objective table shows the
four weighted terms and total. Method-specific constraints, RBC rules and MPC/MILP procedures
remain in an expander. The cost explanation identifies the shortfall coefficient as a model
assumption.

Scenario, battery, forecast and controller controls, defaults, event choice, and saved-first
run and batch actions are retained. The results no longer display provenance, technical IDs,
the saved model's loaded-event announcement, the standalone replay explanation, execution and
solver traces, all-day charts, all-day schedules or dispatch CSV controls. Their source data
remain available internally. The battery summary retains a short account of measured action
changes and corrections.

## Calculation and terminology checks

- The primary power badge is MET only when every positive-target interval reaches its kW
  minimum. Any missed interval is NOT MET. With a zero target, the status is NOT ASSESSABLE.
  Power shortfall energy sums the missed kW of each half-hour multiplied by 0.5 h.
- The existing whole-event energy mode can return a saved MET when surplus in one interval
  offsets a miss in another. The results show this separately as configured target fulfilment.
  The saved interval-mode evaluation can also report PARTIALLY MET when only some intervals
  pass. The headline answers the stricter all-interval question. Both existing evaluations
  and their objective calculations are preserved.
- The live comparison labels reflect the implementation. Forecast Planned uses saved
  household forecasts. RBC replay applies the rules to current measured demand and battery
  state. MPC updates the rolling plan with current measurements. MILP applies its saved
  day-ahead schedule subject to battery, grid and export corrections.
- Minimum SoC remains battery-specific throughout the day. The default final hard reserve is
  20%, the preferred soft terminal target is 50%, and the 80% preparation target is an RBC
  heuristic subject to its tariff rule. MPC and MILP retain their existing procedures.

## Local preview

From `the BatteryFlex repository root`, run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **Simulation Lab → Run Simulation & Results**. With the existing dedicated storage
configured, select 18 March 2025 and leave LightGBM and the default scenario selected. Press
**Run Optimisation** in any method tab to see the previously saved result. This example displays
MET for both trajectories and 10 kWh delivered in each.

Read-only UI snapshots for RBC, MPC and MILP are in `outputs/task06-ui/`. Verification used a
fresh disk cache with solver execution, uploads and database writes blocked. The stored arrays
reconciled battery energy transitions, portfolio import and export, event flexibility and
the weighted objective for both trajectories in all three methods.

## Verification

The full suite passed with **340 tests in 382.49 seconds**. Ruff lint, Ruff format and
source/script type checks passed. The fresh read-only Streamlit process restored the
three saved controller results and verified the simplified UI. All 18 run indexes
matched before and after verification.

## Files changed

- `src/batteryflex/ui/dispatch.py` removes visible identifiers and retains setup and explanations.
- `src/batteryflex/ui/dispatch_results.py` implements the shared results-first view.
- `tests/test_dispatch.py` tests the strict interval check even when event totals match.
- `tests/test_forecast_resolver.py` verifies results order, hidden identifiers, paired data and reuse.
- `docs/TASK06_UI_REFACTOR.md` and `docs/CURRENT_HANDOFF.md` document the change and verification.
