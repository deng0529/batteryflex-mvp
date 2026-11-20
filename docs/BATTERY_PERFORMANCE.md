# Task 04C — final battery performance and explainable capability

17 November 2026 · Branch `codex/task04c-battery-performance` · Complete; review pending.
This is a focused Task 04/04B refinement. Task 05 has not begun.

## 1. Files modified

- `src/batteryflex/battery_demo.py`: replaces the duration/idle/curtailment adapter with constant
  rated-power performance to the SOC boundary, automatic time and a shorter exact final step.
- `src/batteryflex/portfolio.py`: adds typed commitment explanations around existing capability/
  assessment functions; original aggregation and feasibility calculations remain unchanged.
- `src/batteryflex/ui/portfolio.py`: tooltips, separate model explanations, three performance
  inputs, one explained commitment table, dynamic equations and working-based scenario defaults.
- `tests/test_battery_demo.py`, `tests/test_portfolio.py`, `tests/test_portfolio_ui.py`,
  `tests/test_app.py`: analytical, constraint-diagnosis and current UI regressions.
- `README.md`, `docs/CURRENT_HANDOFF.md`, `docs/DEVELOPMENT_PLAN.md`, `docs/DATA_CONTRACTS.md`,
  `docs/PORTFOLIO_CONFIGURATION.md`, `docs/UI_ARCHITECTURE.md`: current behavior and supersession notes.
- `docs/BATTERY_PERFORMANCE.md`: this new completion report.

No changes to strict `battery.py`, configuration serialization, saved-active/working separation,
source NESO/LCL observations/validation or replay mappings. No dependencies added, staging or commits.
Unrelated parent-repository work is preserved.

## 2. Final Portfolio Configuration layout

Exactly three app pages remain. Portfolio Configuration contains these four sections in order:

1. **A. Battery Configuration** — one editable table containing all five batteries and only
   Save Configuration / Restore Defaults actions. No duplicate editor or editable round-trip input.
2. **B. Battery and Household Power Models** — identified Battery Energy/SOC Model and Household
   Grid Power Balance subsections with separate LaTeX equations and concise assumptions.
3. **C. Battery Charge/Discharge Performance** — household, Charge/Discharge and Operating Power;
   one interactive SOC chart and five metrics. No user duration, Idle or Requested Power control.
4. **D. Battery Availability & Commitment Check** — selected event, explicit local kW commitment,
   five temporary participation checkboxes, one explained results table and calculated equations.

The configuration table retains capacity, charge/discharge powers, initial/minimum/maximum SOC,
separate efficiencies, export permission, nullable export cap and participation. Household ID and
calculated round-trip efficiency are read-only. All five rows remain visible with horizontal
scrolling and pinned IDs. SOC/efficiency display percentages convert to internal fractions.
The global simulation interval remains fixed at 30 minutes (0.5 h), without a per-household column.

Header tooltips define initial/min/max SOC, charging/discharging efficiency, export permission and
participation. The round-trip tooltip explains recovered electrical energy, the efficiency product
and read-only status. The export-cap tooltip uses the requested 3.68 kW versus 5 kW example and
explains that blank means no additional cap. A cap is NET household grid export, not the battery
discharge rating; a zero cap remains distinct from blank.

Save validates all five rows, activates the session portfolio and offers the matching versioned
JSON download. It does not claim permanent server storage or a completed local file save. Retain
the downloaded file beyond session expiry. Restore Defaults resets only working values and requires
Save to replace active settings. Demo/check inputs and working edits cannot silently enter the
saved battery snapshot consumed by Simulation Lab. Existing invalid/stale save protections remain.

## 3. Mathematical model and assumptions

The unchanged Task 04 physics are:

```text
E_next = E + eta_c * P_charge * dt - P_discharge * dt / eta_d
SOC = E / C
SOC_min <= SOC <= SOC_max
0 <= P_charge <= P_charge_max
0 <= P_discharge <= P_discharge_max
P_charge * P_discharge = 0
```

This is a discrete-time battery energy-balance model for scheduling/optimisation, appropriate for
the declared 30-minute residential aggregator research simulation. Stored energy/capacity are kWh,
AC charge/discharge power is kW, time is hours and internal SOC/efficiencies are fractional.
Efficiencies are constant and round-trip efficiency is `eta_c * eta_d`. Default charging and
discharging efficiencies are each sqrt(0.90), giving 90% round-trip electrical recovery.

First-order and second-order RC equivalent-circuit models describe voltage and transient electrical
dynamics. Those are different models and were not substituted here. This energy model is not a
specific manufacturer's BMS, and no validation against measured battery installations is claimed.

The household equation is displayed separately:

```text
P_grid = P_load + P_charge - P_discharge
```

Positive grid power is import; negative is export. This is a household power balance rather than
an internal battery state equation. Future aggregator optimisation can combine the two. Existing
strict grid transitions still enforce no-export and optional net caps when household load is
supplied; the standalone performance illustration deliberately excludes these grid restrictions.

## 4. Charge/discharge performance

Valid working table values are used immediately, including unsaved edits. Operating power defaults
to the selected battery/mode's rating whenever that household, mode or rating changes. The user can
reduce it, but it must remain finite, positive and within the corresponding rating. A zero rating
has no positive operating point and produces a clear message. There is no power clipping.

Automatic completion equations:

```text
T_charge = (SOC_max - SOC_initial) * C / (eta_c * operating_power)
T_discharge = (SOC_initial - SOC_min) * C * eta_d / operating_power
```

The integrator calls the existing strict state transition at 0.5-hour steps. Its final step is
shortened to the actual completion time while power stays constant. It does not average power
over a padded half-hour or round completion up. Only final stored-energy floating-point round-off
within 1e-9 kWh is normalized to the known boundary. Initial SOC already at the selected boundary
returns zero time/energy and no transitions; the chart still shows the initial point.

Immutable results record every actual interval duration, end time, energy, SOC and AC powers.
Electrical energy sums actual kW times actual interval hours. The chart includes time zero and
the exact final point, with hover and horizontal zoom. Only initial SOC, final SOC, operating
power, total time and electrical energy are displayed as metrics. Neither saved nor working
configured initial SOC is mutated. No NESO commitment or dispatch result appears in this section.

For default MAC001391 (10 kWh, initial 80%, permitted 20–100%, eta_c=eta_d=sqrt(0.90)):

| Operation | Power kW | Final SOC | Total time h | Electrical energy kWh | Interval durations h |
| --- | ---: | ---: | ---: | ---: | --- |
| Charge | 5 | 100% | 0.421637 | 2.108185 drawn | 0.421637 |
| Discharge | 5 | 20% | 1.138420 | 5.692100 delivered | 0.5, 0.5, 0.138420 |
| Discharge | 1 | 20% | 5.692100 | 5.692100 delivered | eleven 0.5 steps, then 0.192100 |

Charging adds 2 kWh stored energy using more electrical energy because of charge losses;
discharging withdraws 6 kWh stored energy and delivers less because of discharge losses.
At 100% initial SOC, charge has zero remaining time; at 20%, discharge has zero remaining time.

The former 24-hour duration cap is removed. To avoid an unbounded interactive workload, a curve
requiring more than 100,000 half-hour steps fails explicitly and asks for increased operating
power; completion is not truncated or rounded and no artificial curve is returned.

## 5. Explainable local commitment examples

The check uses valid working battery parameters and temporary scenario participation. Checkboxes
default from working participation. Changing a working participation field rebases only that
household's default; unrelated edits preserve intentional scenario overrides. Checkbox changes
never overwrite table or saved participation. National NESO MW is context only, not a local target.

For each included battery, the unchanged calculation is:

```text
usable_energy = (SOC_initial - SOC_min) * C
deliverable_energy = usable_energy * eta_d
sustainable_power = min(discharge_rating, deliverable_energy / event_hours)
portfolio_power = sum(sustainable_power_i)
required_commitment_energy = local_commitment * event_hours
margin = portfolio_power - local_commitment
shortfall_kw = max(0, local_commitment - portfolio_power)
shortfall_kwh = shortfall_kw * event_hours
```

One Quantity/Value/Unit/Explanation table shows duration, count, usable/deliverable energy,
sustainable discharge, local commitment, required energy and margin. Insufficient cases add
shortfall kW and equivalent constant-power shortfall kWh. Actual contribution-sum, margin,
required-energy and shortfall equations appear below it. There is no extra contribution or
all-events table. Status is exactly Preliminary battery capability sufficient or Insufficient
battery capability, with explicit battery-only qualifications.

Default all-five capability remains:

| Event | Hours | Sustainable portfolio kW |
| --- | ---: | ---: |
| 18 March 2025 | 1 | 22.589466 |
| 6 November 2025 | 1 | 22.589466 |
| 1 December 2023 | 1.5 | 16.760072 |
| 11 January 2026 | 2 | 12.570054 |
| 2 February 2025 | 3 | 8.380036 |

**Feasible example:** 10 kW over the one-hour 18 March event requires 10 kWh. Usable energy
is 26.5 kWh and deliverable energy is 25.140107 kWh. Available power is 22.589466 kW, so the
margin is +12.589466 kW and preliminary capability is sufficient.

**Infeasible example:** 10 kW over the three-hour 2 February event requires 30 kWh. Available
power is 8.380036 kW; margin is -1.619964 kW. Shortfall is 1.619964 kW, equivalent to
4.859893 kWh over three hours. All selected batteries are energy-limited for that duration.

**Mixed-constraint example:** 24 kW for one hour also fails: aggregate deliverable energy is
25.140107 kWh and aggregate rating is 25 kW, yet the sum of the individual sustainable powers
is only 22.589466 kW. The shortfall is 1.410534 kW. Some batteries reach their own power rating
while others lack sufficient energy; energy-rich batteries cannot transfer their unused energy
through another household's spare discharge rating. This is correctly explained as a combination.

Diagnosis examines each asset's energy-only power versus its rating and also checks whether each
independent aggregate ceiling falls below the request. It distinguishes energy, power and combined
limitations, with a separate explanation for no selected households. It never infers sufficiency or
cause from aggregate stored/deliverable energy alone. Equality passes; no SOC/commitment repair occurs.

## 6. Tests and validation

- Full suite: **225 passed**, including existing NESO/LCL, strict battery physics, portfolio,
  persistence, save/restore, state isolation and navigation regressions.
- Ruff lint and format checks passed; `ty check src app.py` passed.
- Analytical performance tests cover both modes, automatic time, correct loss/energy orientation,
  every SOC point, short final steps before/after full intervals, exact half-hour completion,
  zero-time boundaries, reduced power, rated/positive power validation and unchanged configured
  SOC/export settings. Strict grid/rating rejection outside this adapter remains verified.
- Explainability tests cover energy-only, power-only, combined, equality, exclusion and no
  participants. A heterogeneous two-battery case proves combined failure despite both independent
  aggregate ceilings exceeding the commitment. All five actual NESO durations remain covered.
- UI tests verify exact tooltip text/units, calculated efficiency, separate model explanations,
  final controls/metrics, no duration/Idle inputs, zero-time chart, current working defaults,
  independent checkbox overrides, one result table, dynamic equations, shortfall energy and
  unchanged save/restore/Simulation Lab snapshot separation.
- Fresh-runtime localhost health/agent-API smoke checks passed: final four sections/tooltips,
  default and reduced-power boundary times, operating-power validation, five events and actual
  durations, one results table, energy/combined explanations, independent scenario participation,
  Save confirmation with actual JSON download, defaults and all three routes/NESO/LCL navigation.
- An initial duplicate widget-default warning was corrected; checks were repeated on a fresh
  server. No new warnings/tracebacks remained. The temporary instance was stopped afterward.
- The agent API cannot edit grid cells; AppTest drives actual editor state for working-value,
  zero-boundary, participation and save/restore tests. Browser visual QA was not performed.
- All **19** source/data SHA-256 hashes match the preserved Task 03E baseline. There were no
  acquisition/preparation/source-validation/replay modifications. Ignored runtime evidence is
  in `outputs/task04c-*`.

Streamlit tests/localhost checks used approved escalated execution due to sandbox restrictions.
No external service/database write was performed.

## 7. Remaining limitations and review boundary

The model assumes constant efficiencies and power over each performance interval, without voltage,
RC transients, degradation, PV or measured BMS validation. Performance deliberately excludes household
load/export restrictions; the strict household transition still supports those with supplied load.
The commitment check assumes constant discharge, no recharge and no additional grid-side constraints.
It is not official baseline-relative NESO delivery feasibility or actual dispatch.

Persistence remains session activation plus browser-owned JSON; retain downloads beyond session
expiry. No primary configuration import or shared durable backend was added. Simulation Run/Clear
remain disabled. No Task 05 forecasting, ML, MILP, MPC, full event dispatch, official settlement,
live market integration or real battery communication was implemented. Stop after Task 04C for review.
