> Historical Task 04B report. Task 04C supersedes section names, duration/idle demo controls,
> half-hour-average curtailment and all-True scenario participation defaults. Current behavior
> uses exact SOC-boundary completion times and an explained results table; see
> [BATTERY_PERFORMANCE.md](BATTERY_PERFORMANCE.md). Save/Restore and working/saved separation remain.

# Task 04B — simplified portfolio workspace and battery demonstration

17 November 2026 · Branch `codex/task04b-portfolio-demo` · Complete; review pending.
This refines Task 04. Task 05 forecasting, optimisation and full event simulation have not begun.

## 1. Files changed

Created:

- `src/batteryflex/battery_demo.py`: immutable interval results and the single-battery demo adapter.
- `src/batteryflex/portfolio_editor.py`: percentage/table conversion and per-household validation.
- `tests/test_battery_demo.py`, `tests/test_portfolio_editor.py`: analytical and validation tests.
- `docs/PORTFOLIO_CONFIGURATION.md`: this completion report and current UI guide.

Updated:

- `src/batteryflex/ui/portfolio.py`: replaces the per-household controls with the four sections below.
- `src/batteryflex/ui/planned.py`: explicitly identifies the saved active portfolio as simulation input.
- `tests/test_portfolio_ui.py`, `tests/test_app.py`: current UI, state isolation and navigation checks.
- `pyproject.toml`: minimum Streamlit 1.67, matching the installed/tested fixed-row keyed-editor
  behavior that preserves edits while input values change. No package was installed and no new
  dependency was added.
- `README.md`, `config/README.md`, `docs/CURRENT_HANDOFF.md`, `docs/DEVELOPMENT_PLAN.md`,
  `docs/DATA_CONTRACTS.md`, `docs/UI_ARCHITECTURE.md`, `docs/BATTERY_MODEL.md`.

The Task 04 strict physics, portfolio capability and JSON persistence modules are unchanged.
Validated NESO/LCL data, source validation and historical replay mappings are preserved.
No staging or commits; unrelated parent-repository work remains untouched.

## 2. Final UI sections

The three-page navigation remains Data Explorer, Portfolio Configuration and Simulation Lab.
Portfolio Configuration contains exactly, in order:

1. **A. Battery Configuration**: one five-row editable table and two actions.
2. **B. Battery Mathematical Model**: matching state/SOC equations, constraints and grid balance.
3. **C. Battery Charge/Discharge Demonstration**: compact controls and one interactive SOC chart.
4. **D. Battery Availability & Commitment Check**: one event, one local request and five checkboxes.

No separate household editor, apply-all, load control, household contribution table, selected-battery
capability table or all-events capability table remains on the page. All five table rows fit in the
editor; household ID is pinned while the wide table scrolls horizontally.

## 3. Editable parameters and validation

The table includes household ID (read-only), capacity kWh, maximum charging/discharging kW,
initial/minimum/maximum SOC %, charging/discharging efficiency %, calculated round-trip efficiency %
(read-only), export permission checkbox, nullable net export cap kW and participation checkbox.
Blank export cap means no additional limit; zero is distinct and means no permitted net export.

Display percentages convert to fractional model values. Round-trip percent is the product of the
two efficiency percentages divided by 100. It cannot be independently edited. Household IDs/order
are checked server-side. Numeric column constraints help editing; BatteryConfig validation remains
authoritative for positive capacity, nonnegative powers/caps, bounded SOC and positive efficiencies.
Invalid rows report the household and parameter/physical constraint. All five rows must be valid;
there is no partial save, silent correction or automatic SOC increase. Valid low SOC is accepted.

The global setting is displayed as **Simulation interval: 30 minutes (0.5 hours)**. Every validated
table configuration uses this interval; it is not repeated or editable per household. The underlying
Task 04 model/JSON field remains compatible for other integrations.

Established defaults are unchanged: 10 kWh, 5 kW charge/discharge, 20–100% SOC, 90% round-trip
efficiency split equally as sqrt(0.90), export enabled with no additional cap and participation on.
Initial SOC is MAC001391 80%, MAC003288 65%, MAC000143 90%, MAC001534 55%, MAC001395 75%.
These are research assumptions, not historical installations or measured SOC.

## 4. Save, Restore and persistence

Working table rows persist separately from the saved active Portfolio. Table changes immediately
update the demonstration and commitment check, but cannot alter Simulation Lab's battery snapshot.
The initial active portfolio is the declared default; later changes require explicit Save.

**Save Configuration** is a download action with a validation/commit callback. It revalidates all
rows, verifies the reviewed JSON payload, activates that portfolio for this session and offers the
same schema-v1 JSON as a browser download. The success message claims session saving and a download
request, not a completed permanent local write. Keep the downloaded file for durability beyond
session expiry. No server configuration file, shared public file or database is written. Strict
JSON import/export helpers remain available and tested; separate upload/load is removed from the
primary UI as requested.

If a new cell edit arrives with Save, the older rendered download payload is not silently committed
as the new table. Review the updated table and save again. Invalid rows disable Save and suppress
demo/feasibility outputs. Callback validation also protects against stale or malformed save requests.

**Restore Defaults** immediately replaces only working rows and refreshes the editor. Previously
saved active settings remain unchanged until Save Configuration is clicked again. Demo inputs and
scenario participation choices are independent and are not reset by Restore Defaults.

The fixed-row editor keeps a stable key during edits, retains the complete working table across
reruns/page switches, and refreshes the computed efficiency in the same table. Only an explicit
Restore Defaults changes editor revision. There is no duplicate parameter form.

## 5. Battery demonstration and physical constraints

Select one household, Charge/Discharge/Idle, requested constant kW and duration in 0.5-hour steps
(0.5–24 hours). Idle explicitly commands zero power. Valid working table values are used even before
saving; the caption states this and explains that household demand/grid restrictions are excluded.

Each half-hour uses the existing Task 04 transition:

```text
E_next = E + eta_charge * P_charge * 0.5 - P_discharge * 0.5 / eta_discharge
SOC = E / Capacity
```

Only the demo adapter permits explicit feasible-power reduction:

```text
actual_charge = min(request, charge_rating, (E_max - E) / (eta_charge * 0.5))
actual_discharge = min(request, discharge_rating, (E - E_min) * eta_discharge / 0.5)
curtailed_power = request - actual_power
```

The feasible action is then validated by the unchanged strict transition. There is no simultaneous
charging/discharging, no SOC violation and no bypass of physical power limits. To exclude grid
restrictions, a temporary export-unrestricted copy is used; the original export settings are not
changed. The demo is not a household grid assessment or NESO event dispatch.

Immutable per-interval results record elapsed end time, stored energy, SOC, requested power, actual
charge/discharge power, curtailed power and reasons. The single SOC line includes the initial time
zero and every half-hour state. Summary metrics show initial/final SOC, requested kW and actual AC
electrical kWh charged/discharged. Limit warnings name the power/SOC constraint and curtailed energy;
a caption gives actual power range and maximum curtailed kW. Near an SOC bound, recorded actual power
is a feasible constant half-hour average; no within-interval stop time is inferred.

For example, the default MAC001534 discharging at a requested 5 kW for three hours delivers 3.320392
kWh and ends at 20% SOC. At 21% initial SOC, a 10 kWh battery can deliver only 0.094868 kWh before
its 20% reserve, so the first interval's average power reduces to 0.189737 kW and later intervals
stop. The configured initial SOC and saved portfolio remain unchanged after either demonstration.

## 6. Feasibility check

The requested explanatory sentence appears directly beneath the heading. Inputs are one reviewed
historical NESO event, a separate local kW commitment and five temporary household checkboxes, all
initially checked. The check uses valid working parameters, overriding participation only in its
temporary scenario. Neither table participation nor saved participation is overwritten.

The unchanged battery capability model aggregates usable/deliverable energy and each selected home's
minimum of discharge rating and deliverable energy divided by event duration. Output is limited to
duration, participating count, usable/deliverable energy, maximum constant portfolio kW, commitment,
margin and preliminary pass/shortfall. No household contribution or all-events table is shown.

Default capability remains 22.589466 kW for both one-hour events, 16.760072 kW for 1.5 h,
12.570054 kW for 2 h and 8.380036 kW for 3 h. A 10 kW proposal passes the first four events and
has a 1.619964 kW shortfall over three hours. Selecting only MAC001391 for one hour provides 5 kW;
a 10 kW proposal then has a 5 kW shortfall. SOC and commitment are never modified to force a pass.

The qualification states that this is battery-only preliminary capability. Official NESO delivery,
baseline-relative flexibility, household demand, export restrictions and time-varying control are
not established. National MW stays context only and is never scaled into local kW.

## 7. Tests and validation

- `python -m pytest -q`: **216 passed**, including existing battery, NESO and LCL regressions.
- `python -m ruff check .` and `python -m ruff format --check .`: passed.
- `.venv/Scripts/ty.exe check src app.py`: passed.
- Analytical tests cover charge/discharge/idle curves, efficiency losses, rating limits, SOC
  boundaries, partial feasible power, curtailment energy/power/reasons, input validation,
  unchanged strict transition behavior and no mutation of configured SOC/export settings.
- Table/UI tests cover all editable parameters, read-only calculated efficiency, percentage
  conversion, invalid rows, multiple household errors, nullable caps, low SOC, Save/Restore,
  JSON round trips, working versus saved state, accumulated edits/reruns/page switches,
  simultaneous new edit/save handling, scenario participation, aggregation and shortfalls.
- Simulation Lab tests prove unsaved SOC/participation and temporary scenario choices stay out
  of the saved battery snapshot; an explicit save updates that snapshot. Run/Clear stay disabled.
- Temporary localhost Streamlit health/agent API passed: exact four sections; one five-row,
  13-column editor; equations; actual SOC chart; charge/discharge/idle/limit reporting; Save
  confirmation and fetched JSON download; all five events; independent scenario checkboxes;
  saved simulation input; defaults; unchanged NESO/LCL navigation. No server traceback/warning.
- The agent API marks grid editing `action_unsupported`; AppTest drives real data-editor state
  for edit/save tests. Browser visual/grid interaction QA was not performed.
- All **19** source/data SHA-256 values match the Task 03E preserved baseline. No acquisition,
  preparation, source validation or replay mapping changes occurred. Ignored smoke evidence
  is in `outputs/task04b-*`; the temporary server was stopped after checks.

Streamlit tests/localhost requests used approved escalated execution because sandbox restrictions
previously stalled Streamlit or denied sockets. Checks did not mutate external services.

## 8. Remaining limitations and stopping point

Persistence is session activation plus browser-owned JSON, with no durable shared backend. A new
session starts from defaults, and there is no primary upload/load control in the simplified page.
The demo is deterministic half-hour single-battery physics, with a 24-hour UI bound and average
boundary-interval curtailment. It ignores demand/export restrictions explicitly, while the original
strict grid model still enforces them for supplied-load transitions. Feasibility remains battery-only.

There is no forecasting, ML, MILP, MPC, full event dispatch, official baseline/settlement, PV,
degradation, DNO power flow, real battery communication or live market integration. Simulation
execution and result persistence remain unavailable. Stop after Task 04B for review.
