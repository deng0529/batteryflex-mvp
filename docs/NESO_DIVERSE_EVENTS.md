# Task 02C — diverse historical review and interval view

Analysis date: 2026-11-16. Supported by National Energy SO Open Data. This review supersedes the five-event recommendation in Task 02B; previous analysis remains as a historical report. No final selection or scenario is persisted.

## Evidence and event identity

Official NESO service history confirms that DFS originally reduced demand and became bidirectional on 9 April 2026: https://www.neso.energy/industry-information/balancing-services/demand-flexibility-service-dfs . The official 2023/24 guidance explicitly describes delivered demand reduction: https://www.neso.energy/document/286981/download . Current DFS direction convention remains Downwards = demand reduction/generation increase; Upwards = demand increase/generation reduction (https://www.neso.energy/document/379391/download).

New evidence permits a **separate contextual demand-reduction annotation** for the two allowlisted pre-bidirectional archives. Their raw direction is still absent; it is never replaced with Downwards. Original event IDs are also absent. A continuous source/date window group is a provisional historical event proxy, not proof of an official unique event identity. Counts below distinguish identified events from these date groups. Gapped dates are not joined into continuous events.

## Complete resources examined

### DFS Service Requirement

Resource ID `3635fd80-49d7-4d02-964d-cc8c08d50302`; 2004 complete rows; 216 identified-event/date groups. Retrieved `2026-11-16T14:59:12.575069+00:00`; complete `2026-11-16T14:59:12.951336+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=1000&offset=0&sort=_id+asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=1000&offset=1000&sort=_id+asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=1000&offset=2000&sort=_id+asc

### DFS Service Requirement (Archive 2025/2026)

Resource ID `f5605e2b-b677-424c-8df7-d0ce4ee03cef`; 1132 complete rows; 190 identified-event/date groups. Retrieved `2026-11-16T14:59:13.190568+00:00`; complete `2026-11-16T14:59:13.374369+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=1000&offset=0&sort=_id+asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=1000&offset=1000&sort=_id+asc

### DFS Service Requirements (2023/2024)

Resource ID `7914dd99-fe1c-41ba-9989-5784531c58bb`; 32 complete rows; 16 identified-event/date groups. Retrieved `2026-11-16T15:03:30.253349+00:00`; complete `2026-11-16T15:03:30.253349+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=7914dd99-fe1c-41ba-9989-5784531c58bb&limit=1000&offset=0&sort=_id+asc

Official source: https://www.neso.energy/data-portal/demand-flexibility-service/dfs_service_requirements . All 32 records retrieved; source dates 2023-11-16 through 2024-03-21, 6 Live and 26 Test rows, grouped into 2 Live and 14 Test dates. Raw clocks include seconds; DFS Required MW and Despatch Type map without renaming raw fields. All 9 original columns have zero missing values.

## Year/month demand-reduction availability

Current counts are source Event ID + delivery date groups. Archive counts are source/date groups, not confirmed unique NESO event counts. Live/Test below refer only to demand-reduction events/groups. Main resource also contains 72 non-reduction Upwards events (70 Live, 2 Test), excluded from reduction counts.

| Resource | Year-month | Identified reduction events | Reduction date groups (ID absent) | Live | Test | Gapped/invalid duration |
| --- | --- | --- | --- | --- | --- | --- |
| DFS Service Requirement | 2026-04 | 7 | 0 | 7 | 0 | 0 |
| DFS Service Requirement | 2026-05 | 13 | 0 | 13 | 0 | 0 |
| DFS Service Requirement | 2026-06 | 17 | 0 | 17 | 0 | 0 |
| DFS Service Requirement | 2026-07 | 14 | 0 | 14 | 0 | 0 |
| DFS Service Requirement | 2026-08 | 20 | 0 | 20 | 0 | 0 |
| DFS Service Requirement | 2026-09 | 28 | 0 | 27 | 1 | 0 |
| DFS Service Requirement | 2026-10 | 22 | 0 | 22 | 0 | 0 |
| DFS Service Requirement | 2026-11 | 23 | 0 | 23 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2024-11 | 0 | 1 | 1 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2024-12 | 0 | 12 | 12 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-01 | 0 | 10 | 10 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-02 | 0 | 16 | 16 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-03 | 0 | 18 | 18 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-04 | 0 | 13 | 13 | 0 | 1 |
| DFS Service Requirement (Archive 2025/2026) | 2025-05 | 0 | 12 | 12 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-06 | 0 | 15 | 15 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-07 | 0 | 18 | 18 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-08 | 0 | 13 | 13 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-09 | 0 | 12 | 12 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-10 | 0 | 11 | 11 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-11 | 0 | 7 | 7 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2025-12 | 0 | 6 | 6 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2026-01 | 0 | 15 | 15 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2026-02 | 0 | 3 | 3 | 0 | 0 |
| DFS Service Requirement (Archive 2025/2026) | 2026-03 | 0 | 8 | 8 | 0 | 0 |
| DFS Service Requirements (2023/2024) | 2023-11 | 0 | 2 | 1 | 1 | 0 |
| DFS Service Requirements (2023/2024) | 2023-12 | 0 | 6 | 1 | 5 | 0 |
| DFS Service Requirements (2023/2024) | 2024-01 | 0 | 1 | 0 | 1 | 0 |
| DFS Service Requirements (2023/2024) | 2024-02 | 0 | 3 | 0 | 3 | 0 |
| DFS Service Requirements (2023/2024) | 2024-03 | 0 | 4 | 0 | 4 | 1 |


Available years: 2023, 2024, 2025, 2026. Legacy months: November/December 2023 and January–March 2024. Archive: November 2024–March 2026 (every intervening month has records). Current: April–November 2026. Exact available dates for the first two resources remain in NESO_HISTORY_ANALYSIS.md. Legacy dates: 2023-11-16, 2023-11-29, 2023-12-01, 2023-12-05, 2023-12-12, 2023-12-14, 2023-12-15, 2023-12-19, 2024-01-17, 2024-02-02, 2024-02-08, 2024-02-29, 2024-03-01, 2024-03-02, 2024-03-14, 2024-03-21.

## All-direction Live/Test availability

| Resource | Live rows | Test rows | Live events/date groups | Test events/date groups |
| --- | --- | --- | --- | --- |
| DFS Service Requirement | 1998 | 6 | 213 | 3 |
| DFS Service Requirement (Archive 2025/2026) | 1132 | 0 | 190 | 0 |
| DFS Service Requirements (2023/2024) | 6 | 26 | 2 | 14 |

Counts are published requirement classifications, not proof of activation or delivered response.

## Duration distribution and Live/Test availability

| Resource | Live/Test | Elapsed duration (minutes) | Events/date groups |
| --- | --- | --- | --- |
| DFS Service Requirement (Archive 2025/2026) | Live | 120.0 | 47 |
| DFS Service Requirement (Archive 2025/2026) | Live | 180.0 | 80 |
| DFS Service Requirement (Archive 2025/2026) | Live | 240.0 | 31 |
| DFS Service Requirement (Archive 2025/2026) | Live | 300.0 | 9 |
| DFS Service Requirement (Archive 2025/2026) | Live | 360.0 | 3 |
| DFS Service Requirement (Archive 2025/2026) | Live | 420.0 | 4 |
| DFS Service Requirement (Archive 2025/2026) | Live | 60.0 | 15 |
| DFS Service Requirement (Archive 2025/2026) | Live | Unresolved: disjoint | 1 |
| DFS Service Requirement | Live | 120.0 | 6 |
| DFS Service Requirement | Live | 180.0 | 24 |
| DFS Service Requirement | Live | 240.0 | 27 |
| DFS Service Requirement | Live | 300.0 | 46 |
| DFS Service Requirement | Live | 360.0 | 17 |
| DFS Service Requirement | Live | 420.0 | 19 |
| DFS Service Requirement | Live | 60.0 | 4 |
| DFS Service Requirement | Test | 60.0 | 1 |
| DFS Service Requirements (2023/2024) | Live | 90.0 | 2 |
| DFS Service Requirements (2023/2024) | Test | 30.0 | 4 |
| DFS Service Requirements (2023/2024) | Test | 60.0 | 7 |
| DFS Service Requirements (2023/2024) | Test | 90.0 | 2 |
| DFS Service Requirements (2023/2024) | Test | Unresolved: disjoint | 1 |


Totals: 144 identified demand-reduction events (143 Live, 1 Test), plus 206 contextually supported archive date groups (192 Live, 14 Test). Combined: 335 Live and 15 Test events/date groups, with two disjoint groups lacking a single continuous duration. Archive 2025-04-16 has 19:00–20:00 and 21:00–22:00 GMT requirements, not one uninterrupted 3-hour event. Legacy test date 2024-03-21 has 17:30–18:00 and 18:30–19:00 GMT, not one uninterrupted 90-minute event. Neither is eligible for the continuous-event shortlist.

## Overlap and duplicates

No delivery dates overlap across these three resources, so there are no cross-resource event/window overlaps or complete signature matches. Exact raw business-row duplicate counts (excluding only CKAN _id): DFS Service Requirement: 0, DFS Service Requirement (Archive 2025/2026): 0, DFS Service Requirements (2023/2024): 0. Current has 162 coincident half-hour window pairs belonging to different source event IDs; direction, tag and zonal eligibility remain separate and are never netted or deduplicated by time alone. The 2023/24 and 2025/26 archives have no overlapping windows within a date.

## Five diverse provisional historical delivery groups

All five are genuine published **Live** requirement records. The absent original event IDs and raw directions are explicit limitations. The recommendation is conditional on accepting source/date window groups as event proxies, with row-level traceability. If original NESO Event ID is mandatory, use the current-resource browser instead; do not claim these five possess IDs. No final five-house commitment is set.

| Original event ID | Date | Window GMT/UTC (= UK local on these dates) | Duration | National MW per source window | Direction evidence | Live/Test | Resource | CKAN row IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Absent | 2025-03-18 | 18:00–19:00 | 1h | 300.0 | Pre-bidirectional demand reduction; raw direction absent | Live | DFS Service Requirement (Archive 2025/2026) | 847, 848 |
| Absent | 2025-11-06 | 17:00–18:00 | 1h | 200.0 | Pre-bidirectional demand reduction; raw direction absent | Live | DFS Service Requirement (Archive 2025/2026) | 237, 238 |
| Absent | 2023-12-01 | 16:30:00–18:00:00 | 1.5h | 550.0 | Pre-bidirectional demand reduction; raw direction absent | Live | DFS Service Requirements (2023/2024) | 24, 25, 26 |
| Absent | 2026-01-11 | 17:00–19:00 | 2h | 500.0 | Pre-bidirectional demand reduction; raw direction absent | Live | DFS Service Requirement (Archive 2025/2026) | 125, 126, 127, 128 |
| Absent | 2025-02-02 | 16:00–19:00 | 3h | 500.0 | Pre-bidirectional demand reduction; raw direction absent | Live | DFS Service Requirement (Archive 2025/2026) | 999, 1000, 1001, 1002, 1003, 1004 |


- **2025-03-18**: Whole 1h Live demand-reduction requirement; winter month/year/season and evening diversity, subject to source-ID limitations. Source resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Starts/ends `2025-03-18T18:00:00+00:00` / `2025-03-18T19:00:00+00:00`.

- **2025-11-06**: Whole 1h Live demand-reduction requirement; winter month/year/season and evening diversity, subject to source-ID limitations. Source resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Starts/ends `2025-11-06T17:00:00+00:00` / `2025-11-06T18:00:00+00:00`.

- **2023-12-01**: Whole 1.5h Live demand-reduction requirement; winter month/year/season and evening diversity, subject to source-ID limitations. Source resource `7914dd99-fe1c-41ba-9989-5784531c58bb`. Starts/ends `2023-12-01T16:30:00+00:00` / `2023-12-01T18:00:00+00:00`.

- **2026-01-11**: Whole 2h Live demand-reduction requirement; winter month/year/season and evening diversity, subject to source-ID limitations. Source resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Starts/ends `2026-01-11T17:00:00+00:00` / `2026-01-11T19:00:00+00:00`.

- **2025-02-02**: Whole 3h Live demand-reduction requirement; winter month/year/season and evening diversity, subject to source-ID limitations. Source resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Starts/ends `2025-02-02T16:00:00+00:00` / `2025-02-02T19:00:00+00:00`.

## Comparison with original selection

| Measure | Original: 218, 217, 216, 215, 211 | New provisional delivery groups |
| --- | --- | --- |
| Dates | 11–15 November 2026 | 1 December 2023; 2 February 2025; 18 March 2025; 6 November 2025; 11 January 2026 |
| Calendar months / year-months | 1 / 1 | 5 / 5 (November, December, January, February, March) |
| Years / winter seasons | 1 / 1 | 3 / 3 (2023/24, 2024/25, 2025/26) |
| Whole-event durations | 2, 3, 5, 7, 5 hours | 1, 1, 1.5, 2, 3 hours |
| Residential overlap | Late afternoon/evening | All late afternoon/evening |
| Identity/direction | Explicit source IDs and Downwards labels | IDs absent; source/date groups and documented historical service meaning |
| MW variation across selected events | 500 MW throughout | 200, 300, 500, 550 MW across events (not a household target) |


The new set meets the preferred duration mixture without clipping whole events into invented shorter events. It offers temporal and requirement diversity and shorter horizons for later battery feasibility work. Its tradeoff is weaker original event identity and contextual rather than row-explicit direction. No claim that Live requirements were actually activated or delivered is made. Ranking is deterministic, prioritises the duration slots, winter months, unused calendar months, evening overlap, new years/seasons and target duration, and never repeats a date. No sources/dates/requirements are hardcoded in the selection algorithm.

## Interval example — 11 January 2026

| Interval | UTC/UK start | UTC/UK end | Hours | National MW | Original event ID | CKAN row ID | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-01-11T17:00:00+00:00 | 2026-01-11T17:30:00+00:00 | 0.5 | 500.0 | Absent | 125 | Directly reported source window |
| 2 | 2026-01-11T17:30:00+00:00 | 2026-01-11T18:00:00+00:00 | 0.5 | 500.0 | Absent | 126 | Directly reported source window |
| 3 | 2026-01-11T18:00:00+00:00 | 2026-01-11T18:30:00+00:00 | 0.5 | 500.0 | Absent | 127 | Directly reported source window |
| 4 | 2026-01-11T18:30:00+00:00 | 2026-01-11T19:00:00+00:00 | 0.5 | 500.0 | Absent | 128 | Directly reported source window |


All four requirements are directly reported original half-hours, not four invented independent NESO requests. Source rows 125–128 already report 500 MW each. Every other selected interval is also directly reported. When an event-wide constant source window is split, the UI explicitly labels repetition as **Derived: constant within source window (simulation assumption)**. A source-varying requirement is preserved at every boundary, with no averaging or interpolation.

## Time boundaries and safeguards

Intervals are at most 30 elapsed minutes, anchored to event start. Original requirement boundaries also split intervals, so partial source/grid boundaries remain partial and explicitly flagged. Source windows must be contiguous, positive in elapsed duration and non-overlapping; gaps, duplicates and unresolved local clocks reject interval generation. Original source texts remain unchanged.

Archive From/To are GMT according to official metadata and become UTC instants separately; displayed UK clocks use Europe/London (including BST when applicable). Dual-clock current records use the original UK delivery date and local clocks, checked against original UTC clocks to resolve date alignment and autumn folds. Nonexistent spring local times and ambiguous autumn times without fold/UTC evidence are rejected. UTC stepping handles the spring skipped hour and autumn repeated hour correctly. An earlier end clock can cross midnight after same-day DST resolution is checked; equal clocks are not silently interpreted as 24 hours. Derived instants are an exploration representation, not a final simulation mapping or import contract.

## Remaining limitations

- Date groups cannot establish whether two separate official auctions occurred on the same historical date; source IDs are absent. Final event identity needs review or authoritative cross-reference.
- Contextual reduction evidence applies only to the two known archive resources before 9 April 2026, never arbitrary directionless datasets.
- Published requirement MW is national procurement power, not measured response, household consumption or five-house commitment. A future portfolio commitment must be separately chosen in kW.
- Whole-day disjoint groups remain unresolved, not split into fabricated event IDs.
- No snapshot isolation is available during pagination; totals, schemas and unique row IDs are checked.
- No household dataset, Turso, optimiser, MPC or final scenario persistence is implemented.

## Task 02D — final Live-only validation

The replacement shortlist has been validated against fresh complete CKAN records and
independent original CSV downloads. See NESO_FINAL_VALIDATION.md for the per-event
PASS/FAIL/UNVERIFIED matrix, definition evidence, archive attribution investigation,
internal scenario IDs and all 17 half-hour rows. This final audit supersedes the pending
validation status of this Task 02C report; raw official Event IDs remain absent.
