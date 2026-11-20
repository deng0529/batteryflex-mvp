# Task 02D — final Live-only NESO event validation

Validated 2026-11-16 against fresh complete official CKAN responses and independent complete CSV downloads. Supported by National Energy SO Open Data. All five original candidates pass. No replacement is necessary. These are final recommended historical scenario inputs for review; no database scenario or household commitment is persisted.

## Mandatory criterion matrix

PASS requires explicit evidence; any FAIL or UNVERIFIED blocks the final shortlist. Live is checked in **every original** Service Requirement Type value, independently of direction, date, dispatch eligibility and price. Direction is verified from applicable official product definitions, not inferred from unrelated row values.

| Candidate date | live | direction | historical_date | original_records | source_resource | complete_retrieval | requirement_mw | valid_times | continuous_window | CSV/API match | Original proposal match | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-03-18 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 2025-11-06 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 2023-12-01 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 2026-01-11 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 2025-02-02 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |


Criterion meanings: live = all raw rows explicitly Live; direction = applicable official demand-reduction definition; historical_date = one valid past date; original_records = unique original CKAN row references; source_resource = known official UUID/API provenance; complete_retrieval = all source rows retrieved; requirement_mw = finite positive source MW; valid_times = source clocks resolve with GMT/BST evidence; continuous_window = no gaps, overlap or duplicate windows. Original Event ID absence is permitted by this task; an internal ID is assigned separately.

## Applicable direction definitions

- Four 2025/2026-date archive candidates: DFS Service Terms **v3**, published 26 November 2024 and effective **27 November 2024**, clause **5.2**, require demand below the operational baseline. Source: https://www.neso.energy/document/348106/download . The service history dates the later bidirectional change to 9 April 2026. These chosen dates are within the earlier demand-reduction service.

- 1 December 2023: official **winter 2023/24 Participation Guidance v11**, section **3.1**, describes providers arranging demand reduction and consumers delivering the reduction volume. Source: https://www.neso.energy/document/286981/download . The **Winter 2023/24 End of Year Report, Table 6, page 16**, independently lists 1 December at 16:30, 17:00 and 17:30 as Live event intervals: https://www.neso.energy/document/319911/download .

- Current DFS terminology is **Downwards = demand reduction/generation increase**, while Upwards means demand increase/generation reduction: https://www.neso.energy/document/379391/download . Historical candidates have no original Event Type value. We retain null raw direction, record the verified semantic meaning separately and do not retroactively assign a direction label.

## Exact source resources and transport verification

### DFS Service Requirement (Archive 2025/2026)

Resource UUID `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Complete CKAN rows: 1132. First-page retrieval UTC `2026-11-16T16:59:24.836470+00:00`; completion `2026-11-16T16:59:25.012684+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=1000&offset=0&sort=_id+asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=1000&offset=1000&sort=_id+asc

Original complete CSV: https://api.neso.energy/dataset/829e325f-8926-40ab-9dd6-8b7aea6cb244/resource/f5605e2b-b677-424c-8df7-d0ce4ee03cef/download/dfs-service-requirement.csv

CSV retrieval UTC `2026-11-16T17:05:42.901564+00:00`; 1132 rows.

### DFS Service Requirements (2023/2024)

Resource UUID `7914dd99-fe1c-41ba-9989-5784531c58bb`. Complete CKAN rows: 32. First-page retrieval UTC `2026-11-16T16:59:25.163530+00:00`; completion `2026-11-16T16:59:25.163530+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=7914dd99-fe1c-41ba-9989-5784531c58bb&limit=1000&offset=0&sort=_id+asc

Original complete CSV: https://api.neso.energy/dataset/e5277fca-2a2b-4836-933b-f24a676b9ed8/resource/7914dd99-fe1c-41ba-9989-5784531c58bb/download/dfs-service-requirements.csv

CSV retrieval UTC `2026-11-16T17:05:44.876665+00:00`; 32 rows.

The original CSV dates are **DD/MM/YYYY**, while CKAN returns **YYYY-MM-DD**. Legacy CSV clocks are HH:MM while CKAN returns HH:MM:SS. Comparison parsed these representations separately; raw source text was not overwritten. Every chosen date/start/end/MW/Live value matches in CSV and API: 17 of 17 rows. CKAN _id values are resource-scoped row identifiers, not official Event IDs. CSV data-row ordinals below are separate physical-file lookup aids.

## Why February/March 2025 appear in the 2025/26 archive

The exact source is genuinely the resource currently titled **DFS Service Requirement (Archive 2025/2026)**, UUID `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Its resource_show metadata reports created `2024-09-11T08:50:39.439908`, last modified `2026-03-27T10:45:09.034050`, and describes year 2025/2026. Actual CSV/API contents span **29 November 2024–27 March 2026**. Thus the title/description is not a reliable season partition.

Metadata request: https://api.neso.energy/api/3/action/resource_show?id=f5605e2b-b677-424c-8df7-d0ce4ee03cef . The official winter overview covers 27 November 2024–28 March 2025: https://www.neso.energy/document/363911/download . **2 February and 18 March 2025 are winter 2024/25 events stored in this later-titled archive**, not winter 2025/26 observations. Original attribution was a storage-resource reference; using it as an event-season label would be incorrect. The publisher does not document why this mixed-history resource was given its current title; no renaming history is asserted. Source name, raw date and separately derived winter season remain distinct.

## Final five recommended Live demand-reduction scenarios

Original Event IDs are absent in all five chosen records. The following **internal BatteryFlex scenario IDs are not official NESO Event IDs** and do not change the underlying source identity. All windows are entire continuous original date-based service windows, not shortened source events.

| Internal scenario ID (not NESO ID) | Original Event ID | Date | UTC/GMT and UK-local window | Hours | National MW per interval | Raw status | Verified direction | Winter | Resource | CKAN rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BF-SCENARIO-20250318-d83173d115 | Absent | 2025-03-18 | 18:00–19:00 | 1.0 | 300.0 | Live | Demand reduction (historical definition) | 2024/25 | DFS Service Requirement (Archive 2025/2026) | 847, 848 |
| BF-SCENARIO-20251106-ae30cf8298 | Absent | 2025-11-06 | 17:00–18:00 | 1.0 | 200.0 | Live | Demand reduction (historical definition) | 2025/26 | DFS Service Requirement (Archive 2025/2026) | 237, 238 |
| BF-SCENARIO-20231201-11bed40350 | Absent | 2023-12-01 | 16:30:00–18:00:00 | 1.5 | 550.0 | Live | Demand reduction (historical definition) | 2023/24 | DFS Service Requirements (2023/2024) | 24, 25, 26 |
| BF-SCENARIO-20260111-928f24c1e7 | Absent | 2026-01-11 | 17:00–19:00 | 2.0 | 500.0 | Live | Demand reduction (historical definition) | 2025/26 | DFS Service Requirement (Archive 2025/2026) | 125, 126, 127, 128 |
| BF-SCENARIO-20250202-5bc3052ad5 | Absent | 2025-02-02 | 16:00–19:00 | 3.0 | 500.0 | Live | Demand reduction (historical definition) | 2024/25 | DFS Service Requirement (Archive 2025/2026) | 999, 1000, 1001, 1002, 1003, 1004 |


No original candidate was rejected. The five retain five calendar months, three years, three winter seasons and the preferred 1/1/1.5/2/3-hour durations. Test, missing-status, unknown-definition, invalid-MW, incomplete-source and disjoint-window records are excluded by the final gate; their original records remain available in raw exploration.

## Full 30-minute interval tables

All 17 selected intervals are **directly published source windows**, each 0.5 hours. Constant MW across consecutive source rows does not make those values derived. If a longer single source record were split, the existing interval generator would explicitly label the repeated constant MW as a derived simulation representation. Published changes are never averaged or flattened. All selected dates are GMT, so UTC and Europe/London clocks coincide at offset +00:00.

### 2025-03-18 — BF-SCENARIO-20250318-d83173d115

Original NESO Event ID: absent. Resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Original record-set SHA-256: `9678c37bc74fe6fa13fa5ec0b43a3eebf192a64664c2103e89081d8b51c00251`.

| Interval | Start GMT/UK | End GMT/UK | Hours | Original MW | CKAN _id | CSV data row | Requirement basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 18:00 | 18:30 | 0.5 | 300.0 | 847 | 847 | Directly published |
| 2 | 18:30 | 19:00 | 0.5 | 300.0 | 848 | 848 | Directly published |


Direction criterion: **PASS**. DFS Service Terms v3, clause 5.2: demand below operational baseline; raw direction absent. Official definition: https://www.neso.energy/document/348106/download . Every above source row explicitly says **Live**.

### 2025-11-06 — BF-SCENARIO-20251106-ae30cf8298

Original NESO Event ID: absent. Resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Original record-set SHA-256: `6f6c3d4952818d4ea512977f6129c0fedb6e3396c108f9f4344d49bb7322bdf7`.

| Interval | Start GMT/UK | End GMT/UK | Hours | Original MW | CKAN _id | CSV data row | Requirement basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 17:00 | 17:30 | 0.5 | 200.0 | 237 | 237 | Directly published |
| 2 | 17:30 | 18:00 | 0.5 | 200.0 | 238 | 238 | Directly published |


Direction criterion: **PASS**. DFS Service Terms v3, clause 5.2: demand below operational baseline; raw direction absent. Official definition: https://www.neso.energy/document/348106/download . Every above source row explicitly says **Live**.

### 2023-12-01 — BF-SCENARIO-20231201-11bed40350

Original NESO Event ID: absent. Resource `7914dd99-fe1c-41ba-9989-5784531c58bb`. Original record-set SHA-256: `2e6f4e645e226cea6c7b587bf2e66a998a8795df4a05d756798e392ae805af13`.

| Interval | Start GMT/UK | End GMT/UK | Hours | Original MW | CKAN _id | CSV data row | Requirement basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 16:30 | 17:00 | 0.5 | 550.0 | 24 | 24 | Directly published |
| 2 | 17:00 | 17:30 | 0.5 | 550.0 | 25 | 25 | Directly published |
| 3 | 17:30 | 18:00 | 0.5 | 550.0 | 26 | 26 | Directly published |


Direction criterion: **PASS**. Winter 2023/24 participation guidance: service delivery is demand reduction; raw direction absent. Official definition: https://www.neso.energy/document/286981/download . Every above source row explicitly says **Live**.

### 2026-01-11 — BF-SCENARIO-20260111-928f24c1e7

Original NESO Event ID: absent. Resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Original record-set SHA-256: `f975ae16c8629e16340564459d18a7e354611ff83d179f3a916e091ead9ff0ea`.

| Interval | Start GMT/UK | End GMT/UK | Hours | Original MW | CKAN _id | CSV data row | Requirement basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 17:00 | 17:30 | 0.5 | 500.0 | 125 | 125 | Directly published |
| 2 | 17:30 | 18:00 | 0.5 | 500.0 | 126 | 126 | Directly published |
| 3 | 18:00 | 18:30 | 0.5 | 500.0 | 127 | 127 | Directly published |
| 4 | 18:30 | 19:00 | 0.5 | 500.0 | 128 | 128 | Directly published |


Direction criterion: **PASS**. DFS Service Terms v3, clause 5.2: demand below operational baseline; raw direction absent. Official definition: https://www.neso.energy/document/348106/download . Every above source row explicitly says **Live**.

### 2025-02-02 — BF-SCENARIO-20250202-5bc3052ad5

Original NESO Event ID: absent. Resource `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Original record-set SHA-256: `5e1a01dee15bc7de0b3b70565d4ff405c521edb8c70bbe2724834ccad61a4070`.

| Interval | Start GMT/UK | End GMT/UK | Hours | Original MW | CKAN _id | CSV data row | Requirement basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 16:00 | 16:30 | 0.5 | 500.0 | 999 | 999 | Directly published |
| 2 | 16:30 | 17:00 | 0.5 | 500.0 | 1000 | 1000 | Directly published |
| 3 | 17:00 | 17:30 | 0.5 | 500.0 | 1001 | 1001 | Directly published |
| 4 | 17:30 | 18:00 | 0.5 | 500.0 | 1002 | 1002 | Directly published |
| 5 | 18:00 | 18:30 | 0.5 | 500.0 | 1003 | 1003 | Directly published |
| 6 | 18:30 | 19:00 | 0.5 | 500.0 | 1004 | 1004 | Directly published |


Direction criterion: **PASS**. DFS Service Terms v3, clause 5.2: demand below operational baseline; raw direction absent. Official definition: https://www.neso.energy/document/348106/download . Every above source row explicitly says **Live**.

## UI and validation safeguards

- Final five-event comparison and criterion matrix admit **PASS only** and always contain **Live only**. Internal IDs and absent official IDs are explicit.
- Detail view defaults to Live. Switch to All historical groups and Test to inspect excluded tests. Year/month/date/duration filters are available; the raw explorer keeps every source record.
- Selected detail shows criterion statuses/reasons, the applicable definition link, original JSON, source provenance, full interval table and national-MW chart.
- MW denotes the NESO national requirement; no five-house kW commitment is assigned or scaled.
- No Turso, household, optimisation, MPC or final run/scenario persistence is implemented.

## Remaining limitations

Official source event IDs are unavailable in these archives; internal IDs are transparent scenario handles only. A requirement series does not alone prove accepted bids, achieved delivery or market eligibility; those are separate utilisation/settlement questions. The 2023 winter review corroborates its Live event, but its procured/delivered MW are distinct from the original 550 MW requirement. Archive naming policy is undocumented. Raw API and CSV formats differ; original values remain separately preserved. Public sources can be revised and lack snapshot isolation, so retrieval timestamps, row references and content fingerprints identify this review.
