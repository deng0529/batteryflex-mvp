> Task 04B refines the configuration UI/state semantics and adds a single-battery physics
> demonstration. This Task 04 report remains the record of the original implementation;
> current UI, Save/Restore and working/saved behavior are in
> [PORTFOLIO_CONFIGURATION.md](PORTFOLIO_CONFIGURATION.md). Core battery equations/defaults
> and portfolio capability calculations below remain valid.

# Task 04 — battery model and completion report

Date: 17 November 2026. Branch: `codex/task04-battery-portfolio`.
Task 04 complete; review pending. Task 05 has not begun.

## 1. Files created or modified

Created:

- `src/batteryflex/battery.py`: typed configuration, state/action, validation, energy transition,
  household grid power, availability and expected final SOC.
- `src/batteryflex/portfolio.py`: five defaults, immutable portfolio edits, participation,
  aggregation, commitment assessment, reviewed-event capability table and scenario snapshots.
- `src/batteryflex/portfolio_storage.py`: validated versioned JSON export/import.
- `src/batteryflex/ui/portfolio.py`: functional configuration, energy/capability and commitment UI.
- `tests/test_battery.py`, `tests/test_portfolio.py`, `tests/test_portfolio_ui.py`.
- `docs/BATTERY_MODEL.md`: this completion report.

Modified:

- `src/batteryflex/ui/planned.py`: preserves simulation placeholder, re-exports portfolio renderer
  for existing navigation and exposes the current validated portfolio to Simulation Lab.
- `tests/test_app.py`: replaces the superseded planned-portfolio assertion with configured UI checks.
- `README.md`, `config/README.md`, `docs/DEVELOPMENT_PLAN.md`, `docs/CURRENT_HANDOFF.md`,
  `docs/DATA_CONTRACTS.md`, `docs/UI_ARCHITECTURE.md`.

No dependencies, source measurements, replay mappings or NESO validation logic changed.
No staging or commits; pre-existing parent-repository work remains untouched.

## 2. Model architecture

Physics and portfolio calculations have no Streamlit imports. Frozen dataclasses describe
configuration, state, action, availability, portfolio capability, commitment assessment and
future scenario snapshots. New portfolios are constructed and validated atomically; applying
common bounds that conflict with preserved individual SOC fails without partially updating
the other assets. Pure portfolio logic can support additional unique household IDs; the public
configuration page deliberately requires exactly the reviewed five.

The UI stores the last valid portfolio per session. Invalid draft fields display an error
and suppress capability/commitment results and configuration download until corrected. There
is no SOC repair, automatic subset selection or silent adjustment to force feasibility.

## 3. Equations, units and constraints

All powers are AC-side kW, stored energy is DC-side kWh, time is hours and internal SOC is a
fraction. UI SOC/efficiency values are percentages. Configuration defaults to `dt = 0.5 h`.

```text
E_next = E + eta_c * P_charge * dt - P_discharge * dt / eta_d
SOC = E / C
SOC_min * C <= E <= SOC_max * C
0 <= P_charge <= P_charge_max
0 <= P_discharge <= P_discharge_max
P_charge * P_discharge = 0
P_grid = P_load + P_charge - P_discharge
```

Positive grid power is import; negative is export. No-export enforces `P_grid >= 0`.
An optional permitted net export cap enforces `P_grid >= -P_export_max`; it does not replace
the discharge rating. When export is disabled its zero limit takes precedence over any cap.
The load is explicit, finite and nonnegative; PV is out of scope. State transitions enforce
both grid restrictions and physical constraints and reject infeasible actions with ValueError.
Floating-point state/grid bounds use 1e-10 tolerance; numerical zero round-off is handled without
clipping control requests. Capacity/time must be positive, powers/caps nonnegative, efficiencies
in `(0,1]`, all SOC in `[0,1]`, and `SOC_min <= SOC_initial <= SOC_max`. NaN/infinity and invalid
boolean fields are rejected. Zero power ratings and physically valid low SOC are accepted.

Availability at initial state:

```text
E_initial = SOC_initial * C
E_usable = (SOC_initial - SOC_min) * C
E_deliverable = eta_d * E_usable
P_available(T) = min(P_discharge_max, E_deliverable / T)
SOC_final = SOC_initial - P_discharge * T / (eta_d * C)
P_portfolio(T) = sum(P_available_i(T), participating i)
margin = P_portfolio(T) - local_commitment
```

`availability` optionally accepts a validated current state rather than the initial state.
`final_soc` rejects constant-discharge requests above the battery-only sustainable limit.
Instantaneous nameplate rating and sustainable constant power are separately labelled.
Capability assumes no recharge, constant battery discharge and no grid restrictions. It is
independent of demand, baseline and dispatch allocation. Equality passes the commitment check;
negative margin reports an explicit shortfall. No household must meet the entire request alone.

## 4. Default five-battery configuration

Every battery has 10 kWh capacity; 5 kW charge/discharge rating; 20% minimum, 100% maximum SOC;
90% round-trip efficiency with `eta_c = eta_d = sqrt(0.90)`; 30-minute simulation intervals;
export permission enabled; no additional DNO/net export cap; participation enabled.

| Household | Initial SOC | Stored kWh | Usable kWh | Deliverable kWh |
| --- | ---: | ---: | ---: | ---: |
| MAC001391 | 80% | 8.0 | 6.0 | 5.692100 |
| MAC003288 | 65% | 6.5 | 4.5 | 4.269075 |
| MAC000143 | 90% | 9.0 | 7.0 | 6.640783 |
| MAC001534 | 55% | 5.5 | 3.5 | 3.320392 |
| MAC001395 | 75% | 7.5 | 5.5 | 5.217758 |
| Total | | 36.5 | 26.5 | 25.140107 |

These are simulated research assets and illustrative initial states, not installed batteries
or measured historical SOC. Installed capacity is 50 kWh; combined nameplate discharge is 25 kW.
Installed capacity includes all configured batteries. Participating capacity is separately
available in the model; usable/deliverable energy and capability exclude nonparticipants.

For MAC001391, constant capability is 5.000 / 3.795 / 2.846 / 1.897 kW over
1 / 1.5 / 2 / 3 hours. Discharging 5 kW for one hour leaves about 27.295% SOC.
Its maximum sustainable constant discharge for 1.5–3 hours reaches the 20% reserve boundary.

## 5. Capability for all reviewed NESO events

Computed directly using the existing validated manifest durations. Every row has five
participating households, 26.5 kWh usable and 25.140107 kWh deliverable battery energy.

| Event date | Duration h | National MW (context) | Constant portfolio kW | Margin at 10 kW |
| --- | ---: | ---: | ---: | ---: |
| 18 March 2025 | 1 | 300 | 22.589466 | +12.589466 |
| 6 November 2025 | 1 | 200 | 22.589466 | +12.589466 |
| 1 December 2023 | 1.5 | 550 | 16.760072 | +6.760072 |
| 11 January 2026 | 2 | 500 | 12.570054 | +2.570054 |
| 2 February 2025 | 3 | 500 | 8.380036 | -1.619964 |

National MW is displayed only as context; no national-to-local commitment scaling occurs.
The default 10 kW proposal passes the battery-only test for the first four events and fails
for the three-hour event with 1.619964 kW shortfall. A 30 kW one-hour proposal fails with
7.410534 kW shortfall. Exactly 8.380035799446205 kW for three hours passes when using the
unrounded computed limit. Display rounding must not be used to imply additional capability.

## 6. Portfolio Configuration interface

The same three-page navigation is retained. Portfolio summary shows configured/participating
counts, installed capacity, participating usable energy and participating discharge rating.
The five-house table shows capacity, discharge rating, initial/minimum SOC and participation.

Select a household to edit capacity, charge/discharge powers, initial/minimum/maximum SOC,
separate charging/discharging efficiencies (with computed round-trip efficiency), interval,
export permission, optional net export cap and participation. Valid edits recalculate directly.
Apply to All Batteries copies common settings while preserving individual initial SOC and
participation unless the explicit copy checkboxes are selected. Restore Defaults reinstates
the five reviewed household defaults and participation states; it does not change the user's
event choice or proposed commitment.

Selected-battery metrics distinguish stored, usable and deliverable energy and instantaneous
rating, with a compact 1/1.5/2/3-hour capability table. Battery Availability & Commitment Check
provides event selection, duration/national MW context, explicit local kW commitment, participating
household selection, available power, margin, pass/shortfall and per-household contributions.
A second table covers all five events. There are no redundant charts or debugging panels.
If any participating home has export restrictions, a warning explains that grid-constrained
capability also requires household load; a battery-only pass does not certify those constraints.

## 7. Configuration persistence

Save Configuration downloads the current validated schema-v1 JSON. Load Configuration
validates the full upload before atomically replacing only the current session's portfolio.
All fields, initial SOC, participation and export settings round-trip. Missing/unknown fields,
unknown versions, nonfinite/invalid physics, duplicate/wrong household IDs and oversized files
are rejected. `None` export cap is distinct from a zero cap. The public page restores canonical
household order after import; the core serializer supports larger portfolios.

No durable application configuration backend existed. Browser-owned JSON is the supported
durable storage path; the user must download it before session expiry. Session state alone
is not durable storage. There are no server configuration writes, database migrations,
startup writes or public-user shared-file overwrite controls. Owner/public protections are
preserved by keeping this interface free of shared mutation.

## 8. Simulation Lab and Task 05 interfaces

`current_portfolio()` reads the session's last valid five-battery configuration from either
page and initializes the declared defaults only when absent. `scenario_snapshot()` captures
all battery fields as canonical immutable JSON plus internal event ID and explicit local kW
commitment. Simulation Lab seeds its event choice from Portfolio Configuration, reads the
current portfolio/commitment, creates this input snapshot and permits configuration download.
Its planned export control does not override the authoritative per-battery export settings.

Later integrations must add demand profiles with original timestamps/replay provenance,
forecast assumptions/data references and chosen control strategy to the existing frozen
ExperimentInputs contract. Forecasts should feed future grid/baseline-aware feasibility and
optimisation; the current battery-only result is not a dispatch schedule or strategy.
Run Simulation and Clear Results remain disabled, with the engine-not-implemented message.
No simulated results, artificial optimisation output or successful run records are generated.

## 9. Validation results

- `python -m pytest -q`: **178 passed**, including all existing NESO/LCL tests.
- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed.
- `.venv/Scripts/ty.exe check src app.py`: passed.
- Model tests cover defaults, SOC/energy conversion, efficiency losses, conservation, idle,
  charge/discharge bounds, simultaneous-action rejection, grid import/export, no-export and
  optional net caps, duration limits, availability/final SOC, valid low SOC and invalid inputs.
- Portfolio tests cover participation/exclusion, no participants, aggregation, all five event
  durations, sufficient/insufficient/exact commitments, atomic apply-all and explicit copy,
  extensibility, persistence failures/round trips and immutable input snapshots.
- UI tests cover navigation, immediate changes, low/invalid SOC, apply-all/default restoration,
  participation consistency, export warnings, valid/invalid configuration upload, page-switch
  retention, current Simulation Lab input snapshots and disabled execution/no fake outputs.
- Real localhost Streamlit health and agent API: ready. Exactly three pages retained. All
  five events, default feasibility states, 30 kW shortfall, low/invalid SOC, participation,
  common-settings copy, defaults, export warnings and cross-page configuration/commitment
  retention passed. No new server warnings or tracebacks. Temporary server stopped afterward.
- SHA-256 matches all **19** source/data files in `outputs/task03e-preserved-hashes.json`.
  No acquisition, data preparation, source validation or replay change was performed.

Sandboxed Streamlit/network operations stalled or were denied; tests and localhost checks
completed under approved escalated execution. Pure tests and lint/type checks ran normally.
Real-app smoke checks use the Streamlit agent API; browser visual QA was not performed.
Ignored smoke evidence is in `outputs/task04-*`, separate from measurements/configuration.

## 10. Remaining limitations and review boundary

This is preliminary battery-only capability, not confirmed NESO delivery feasibility. It
does not include forecast load, baseline consumption, actual delivered flexibility relative
to baseline, prices, detailed interval optimisation or unexpected asset unavailability.
Export restrictions are enforced for explicit state transitions with supplied load, but
the constant capability sum is deliberately battery-only. There is no household selection
optimiser, event dispatch, MILP, MPC, degradation, PV, power-flow model, real communications,
live market integration or official settlement. Durable run storage remains future work.

The model, validated portfolio snapshot and preserved demand/event data are ready for review
and subsequent Task 05 forecasting integration. Stop here; do not begin Task 05 until approved.
