# Task 06 five-event batch verification

## Production finding

A read-only audit on 20 November 2026 used the application's Dedicated Turso + R2 configuration. It found 47 completed result indexes, including 32 legacy full-day runs and all 15 expected default STANDARD event-only runs. Every result object reopened from R2 and passed the content hash and numerical validation. There were no invalid result references or active dispatch leases at the time of the audit.

| Event (GMT) | Duration | RBC | MPC | Standalone MILP |
| --- | ---: | --- | --- | --- |
| 18 March 2025, 18:00–19:00 | 1 h | Saved | Saved | Saved |
| 6 November 2025, 17:00–18:00 | 1 h | Saved | Saved | Saved |
| 1 December 2023, 16:30–18:00 | 1.5 h | Saved | Saved | Saved |
| 11 January 2026, 17:00–19:00 | 2 h | Saved | Saved | Saved |
| 2 February 2025, 16:00–19:00 | 3 h | Saved | Saved | Saved |

Each controller's publication timestamps show an initial single result followed by four more. RBC first saved 18 March, and both optimisers first saved 2 February. The batch was completing all five events, using one stored scenario and filling the other four. The previous UI made that sequence easy to misread because the batch depended on first running a single event, and selecting a new event did not itself load that event's result. Comparison had a separate defect. Its grouping key retained event-specific evaluation length, splitting otherwise compatible scenarios by duration.

All 15 event-only production records use the current deterministic explanation schema (version 2). Older explanation versions can still be rendered by rebuilding the explanation in memory from the stored numerical records.

## Fixes

- Single-event and batch actions now use the same event-window and reference construction. Event selection checks the exact persistent result and can show it immediately. The batch can start without a single-event execution and remains available when the selected event's forecast is missing.
- Batch feedback reports pending, running, saved, database hit and failed states. Success requires verified persistent availability, and one failed event leaves the successful events available for a retry. The status identifies the current storage backend.
- Retrieval verifies both event-only trajectories and their executed traces. Temporary R2 availability errors are distinct from missing or corrupt objects and do not automatically trigger a replacement controller execution.
- Comparison defaults to All Five Events and Historical Replay. It shows compatible coverage, interval checks, signed objective and objective components, battery energy allocation, and stored computational effort. Individual Event retains trajectories and expandable technical details. Event-specific evaluation length is excluded from cross-event grouping while remaining in exact numerical identity.

Changed modules are `storage/objects.py`, `storage/dispatch_runs.py`, `ui/dispatch.py`, `ui/dispatch_batch.py`, `ui/dispatch_benchmark.py` and `ui/dispatch_overview.py` under `src/batteryflex/`. No database migration, controller, objective, forecast model, physical constraint, or experimental input was changed. No production result was written. The regression updates are in `tests/test_dispatch_dashboard.py` and `tests/test_forecast_resolver.py`. The batch fixture uses unequal event durations, and the Streamlit test asserts the exact saved-first fingerprint. The handoff is in `docs/CURRENT_HANDOFF.md`.

## Isolated application verification

The test started the real Streamlit Simulation Lab against a fresh local SQLite and object store. It copied the immutable source catalog and 55 verified input objects into that store and copied zero dispatch results. A test wrapper counted controller executions and blocked forecast training.

| Controller | First batch | Recovery | Repeat batch | After Streamlit restart |
| --- | --- | --- | --- | --- |
| RBC | 4 saved, 1 injected failure (1 December 2023) | 4 database hits, 1 newly saved | 5 database hits | 5 database hits |
| MPC | 5 newly saved | — | 5 database hits | 5 database hits |
| Standalone MILP | 5 newly saved | — | 5 database hits | 5 database hits |

All 15 individual event selections and explicit Run actions reopened the same saved results before and after restart. The complete sequence attempted 16 controller executions, including the injected failure, and produced 15 unique completed fingerprints. Each fingerprint matched the corresponding production default. The comparison opened both views without any controller calls. The final restart check also made the selected 1 December forecast temporarily unavailable. The RBC batch loaded four results, reported the one forecast failure and made zero controller calls. Existing persistence tests exercise changed inputs, corrupt-result repair, and retry after an interruption at index publication. The UI check injected a recoverable event failure and did not terminate the process mid-solve.

The saved comparison showed 15/15 compatible results, and the data backing all six aggregate-view charts and the stored timing table matched the verified bundles before and after restart. Switching to Forecast Planned reproduced its three objective sums without executing a controller. The table below sums the independent events. Timings are local stored original controller executions, so they vary between hosts.

| Method | Events MET | Delivered (kWh) | Forecast Planned objective (£) | Historical Replay objective (£) | Replay optimisation solves |
| --- | ---: | ---: | ---: | ---: | ---: |
| RBC | 5/5 | 85 | 0.5513 | 0.8458 | 0 |
| MPC | 5/5 | 85 | 0.4925 | 1.3228 | 17 |
| Standalone MILP | 5/5 | 85 | 0.4925 | 1.2825 | 5 shared solves |

The largest difference between five-event replay totals was £0.4770 between MPC and RBC. MPC's weighted electricity cost was £0.5053 higher, partly offset by a £0.0284 lower weighted terminal deficit. Shortfall and degradation matched at displayed precision.

Production storage verification was read-only. Interruption was tested at index publication and partial recovery was tested in the isolated app. Production restart and simulated network failures were outside those checks.

## Automated checks

The final full suite passed all 359 tests. Ruff lint and formatting checks and the `ty` check for `src` and `scripts` passed. Earlier runs caught the session-state assertion, the registry duration type and the missing-forecast error wording. The final implementation and regression assertions include those corrections.

## Evidence

- [All Five Events screenshot](../outputs/task06-batch-verification/all-five-events.png)
- [Individual Event screenshot, 2 February 2025](../outputs/task06-batch-verification/individual-event.png)
- [Read-only production audit and exact fingerprints](../outputs/task06-batch-verification/production-audit.json)
- [Publication timestamps](../outputs/task06-batch-verification/publication-times.json)
- [Isolated execution evidence](../outputs/task06-batch-verification/local-verification.json)
- [Stored comparison totals for both trajectories](../outputs/task06-batch-verification/comparison-totals.json)
