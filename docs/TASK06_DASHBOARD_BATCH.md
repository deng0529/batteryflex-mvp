# Task 06 explanatory dashboard and five-event batch

Implemented on the existing `codex/task06a-rbc-export-replay` development branch.

## Results dashboard

The first section presents NESO fulfilment, event date and window, controller, participation,
request, delivered energy, credited fulfilment and shortfall. Historical Replay is the default.
The chart shows requested and delivered kW for the selected trajectory and highlights a failed
power interval. The energy table reports the missed intervals and first miss. A plain-language
explanation follows, with worked shortfall equations under an expander. The paired performance,
interval delivery, battery contributions, costs, constraints and compact MPC detail remain available.

For interval targets, gross event delivery integrates the saved signed flexibility. Positive
shortfalls are added interval by interval. Credited delivery is capped and excludes surplus
that would otherwise hide a missed interval. Every required half-hour must meet its kW
minimum within the simulation tolerance. Whole-event energy targets use total energy delivery
as the pass criterion. In that mode the chart's kW series is a reference and missing a
particular half-hour does not constitute a failed interval. These presentation calculations
reconcile with the existing objective evaluation.

The shortfall diagnostic reads each battery's recorded starting energy and household load.
It calculates an instantaneous upper bound from usable energy, discharge power and net
export allowance. Raising each constraint in turn establishes which limits reduced headroom.
The dashboard reports trace corrections, participation and skipped preparation as observations.
Their causal effects require additional evidence. If the trace and headroom cannot establish
a cause, it reports that explicitly. When the measured dispatch already reaches the bound and
additional energy could cover the deficit, the calculation allocates feasible headroom using
the individual discharge efficiencies. This is an estimate at the interval boundary. It does
not establish the feasibility of a different schedule across the whole day.

## Batch and saved comparisons

Below a single result, **Run This Method Across Five Events** applies the chosen controller and
the current portfolio target, tariffs and battery settings to the five existing event
definitions. Each event keeps its own time window, saved forecast, and mapped historical
replay. The batch reports progress separately for each event and continues if one fails.
Successful runs immediately use the existing saved-first persistence. A repeat can restore
all saved events, even in a fresh process, and calculate only the genuinely missing cases.

The summary reports status, kWh delivery, shortfall, electricity cost and four-term objective
information. Its totals are over completed events. It does not rank costs across different
event scenarios. The saved **Comparison & Evaluation** tab has scopes for a single event and
across five events. The latter groups shared battery, tariff, target and replay settings,
and matches methods within each event using the same immutable forecast artifact. An event
with different forecast versions can be inspected by choosing its compatible group.
The comparison only reads saved results.

## Storage and cache

There is no SQL migration or new R2 object format. Each successful event uses the existing
full result bundle and namespaced Turso index. Solver and replay trajectories, constraint
traces and objective values stay at full stored precision. The dashboard derives its
diagnostic fields from saved arrays and leaves the numerical fingerprint and engine
version unchanged. Changed numerical scenarios retain separate fingerprints. Invalid
cached objects follow the existing verified recomputation and append-only repair route.

## Local preview

From `the BatteryFlex repository root`, run `..venvScriptspython.exe -m streamlit run app.py`.
Open **Simulation Lab → Run Simulation & Results**, choose the event and controller, then
select **Run Optimisation**. Use the trajectory selector, or choose **Run This Method
Across Five Events** below the result. The saved review is under **Comparison & Evaluation →
Across five events**.

## Verification

- **350 regression tests passed**. The focused tests cover a one-hour success, a
  three-hour final-interval miss, interval credit versus whole-event delivery,
  energy, grid and discharge rating constraints, heterogeneous efficiencies, and
  recovery of a partially failed batch using a fresh repository.
- Dedicated Turso/R2 restored all five saved RBC results and all five saved MPC
  results in a fresh, read-only Streamlit process. RBC met four events and delivered
  84.41 of 85.00 kWh across the five events. MPC met all five and delivered 85.00 kWh.
- The recorded 2 February 2025 RBC replay reached 8.818 kW of a 10.000 kW request in
  its last half-hour, leaving 0.591 kWh short. At the recorded starting SoCs and
  demand, 8.818 kW was the instantaneous battery ceiling. The evidence identified
  energy availability and estimated 0.623 kWh of additional stored energy at the
  interval boundary using available headroom and recorded efficiencies.
- A fresh read-only Streamlit process verified both trajectory views of the three-hour
  case and loaded all 15 controller/event rows in the five-event comparison. All 32
  existing cloud bundles matched before and after verification.
- Streamlit UI snapshots and the numerical diagnostic are in `outputs/task06-dashboard/`.
  Ruff lint, formatting and type checks passed.

## Files changed

- `src/batteryflex/dispatch_dashboard.py` adds event outcome and evidence calculations.
- `src/batteryflex/ui/dispatch_results.py` renders the new dashboard.
- `src/batteryflex/ui/dispatch.py` and `src/batteryflex/ui/dispatch_batch.py` add batch progress and reporting.
- `src/batteryflex/ui/dispatch_benchmark.py` and `src/batteryflex/storage/dispatch_runs.py` group saved comparisons.
- `tests/test_dispatch_dashboard.py` and `tests/test_forecast_resolver.py` cover reporting, batch and UI behaviour.
- `docs/TASK06_DASHBOARD_BATCH.md` and `docs/CURRENT_HANDOFF.md` describe the handoff.
