# NESO complete-history analysis — Task 02B

Analysed 2026-11-16. Supported by National Energy SO Open Data. These are procurement/service requirements, not evidence of actual activation or delivered demand reduction. Counts are rows unless explicitly labelled events. Raw downloads are local ignored analysis files; no database import.

## Resource comparison

Official catalogue: https://www.neso.energy/data-portal/demand-flexibility

Licence: https://www.neso.energy/data-portal/neso-open-licence

| Resource | Complete rows | Delivery date range | Distinct dates | Identified source events | Direction rows | Status rows |
| --- | --- | --- | --- | --- | --- | --- |
| DFS Service Requirement | 2004 | 2026-04-14 to 2026-11-15 | 169 | 216 | {'Downwards': 1324, 'Upwards': 680} | {'Live': 1998, 'Test': 6} |
| DFS Service Requirement (Archive 2025/2026) | 1132 | 2024-11-29 to 2026-03-27 | 190 | 0 | {None: 1132} | {'Live': 1132} |


The main resource contains later 2026 records and a richer event schema: explicit IDs, direction, tags, local and UTC clocks and zonal caps. The archive contains earlier history through March 2026, including 2024 despite its 2025/2026 label. Its event identity and direction are absent, rather than null source columns. No common delivery dates or cross-resource event-window matches exist in these complete downloads. Never join on `_id`: it is scoped to a resource and reused between them.

## Retrieval provenance and complete schemas

Pagination uses `limit=1000`, offsets 0/1000/2000 as applicable and `sort=_id asc`. Complete means the number of retrieved rows equals a stable reported total with unique CKAN IDs. The source does not offer snapshot isolation; same-total edits during acquisition remain possible. Each runtime fetch records its first request UTC timestamp, completion timestamp and every page URL.

### DFS Service Requirement

Resource ID: `3635fd80-49d7-4d02-964d-cc8c08d50302`. Retrieved by paginated discovery: `2026-11-16T14:36:16.593700+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=1000&offset=0&sort=_id%20asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=1000&offset=1000&sort=_id%20asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=1000&offset=2000&sort=_id%20asc

| Column | API type | Observed Python type | Missing (null / blank / absent) |
| --- | --- | --- | --- |
| _id | int | int | 0 |
| Event ID | numeric | int | 0 |
| DFS Submission Time_Local | text | str | 0 |
| Event Type | text | str | 0 |
| Event Tag | text | str | 0 |
| Delivery Date | date | str | 0 |
| From_Local | text | str | 0 |
| To_Local | text | str | 0 |
| From_UTC | text | str | 0 |
| To_UTC | text | str | 0 |
| Service Requirement MW | int4 | int | 0 |
| Service Requirement Type | text | str | 0 |
| Guaranteed Acceptance Price GBP per MWh | numeric | int | 0 |
| Dispatch Type | text | str | 0 |
| Participant Bids Eligible | text | str | 0 |
| Zonal Cap | text | str | 0 |


All 2004 delivery dates parse successfully; all 2004 windows are 30 minutes on half-hour boundaries. Exact business duplicates, ignoring only `_id`: 0. Repeated date/start/end keys: 162 (162 excess rows).

| Delivery month | Rows | Distinct dates |
| --- | --- | --- |
| 2026-04 | 136 | 13 |
| 2026-05 | 186 | 22 |
| 2026-06 | 222 | 23 |
| 2026-07 | 174 | 18 |
| 2026-08 | 194 | 23 |
| 2026-09 | 264 | 27 |
| 2026-10 | 576 | 28 |
| 2026-11 | 252 | 15 |


### DFS Service Requirement (Archive 2025/2026)

Resource ID: `f5605e2b-b677-424c-8df7-d0ce4ee03cef`. Retrieved by paginated discovery: `2026-11-16T14:36:36.115202+00:00`.

- https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=1000&offset=0&sort=_id%20asc
- https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=1000&offset=1000&sort=_id%20asc

| Column | API type | Observed Python type | Missing (null / blank / absent) |
| --- | --- | --- | --- |
| _id | int | int | 0 |
| Delivery Date | date | str | 0 |
| From | text | str | 0 |
| To | text | str | 0 |
| Service Requirement MW | int4 | int | 0 |
| Service Requirement Type | text | str | 0 |
| Guaranteed Acceptance Price GBP per MWh | numeric | int | 0 |
| Dispatch Type | text | str | 0 |
| Participant Bids Eligible | text | str | 0 |


All 1132 delivery dates parse successfully; all 1132 windows are 30 minutes on half-hour boundaries. Exact business duplicates, ignoring only `_id`: 0. Repeated date/start/end keys: 0 (0 excess rows).

| Delivery month | Rows | Distinct dates |
| --- | --- | --- |
| 2024-11 | 6 | 1 |
| 2024-12 | 68 | 12 |
| 2025-01 | 54 | 10 |
| 2025-02 | 90 | 16 |
| 2025-03 | 92 | 18 |
| 2025-04 | 66 | 13 |
| 2025-05 | 72 | 12 |
| 2025-06 | 76 | 15 |
| 2025-07 | 124 | 18 |
| 2025-08 | 88 | 13 |
| 2025-09 | 86 | 12 |
| 2025-10 | 72 | 11 |
| 2025-11 | 56 | 7 |
| 2025-12 | 28 | 6 |
| 2026-01 | 90 | 15 |
| 2026-02 | 24 | 3 |
| 2026-03 | 40 | 8 |


## Overlaps and duplicate interpretation

No exact business-row duplicates were found within either resource. The main resource has 162 overlapping row pairs (162 coincident date/start/end keys), all with different Event IDs. The archive has no overlapping windows. Adjacent windows use half-open interval comparison and are not overlaps.

Example: on 2026-11-12, Event 214 (Upwards, System) and Event 215 (Downwards, Energy) both have 16:00–16:30 UTC requirements. These are separate procurement events, not duplicates to delete or net together. Repeated source IDs across adjacent windows likewise represent one multi-window event, not duplicate events. Deduplication retains direction, event ID, tag, eligibility and every unknown field in its comparison key; raw UI records are never dropped.

## Available historical delivery dates

Every available date is listed below, grouped by year-month. These are dates with records, not a continuous calendar or proof of delivery.

### DFS Service Requirement

- **2026-04**: 2026-04-14, 2026-04-15, 2026-04-16, 2026-04-17, 2026-04-18, 2026-04-19, 2026-04-22, 2026-04-24, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-29, 2026-04-30

- **2026-05**: 2026-05-01, 2026-05-02, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09, 2026-05-10, 2026-05-11, 2026-05-13, 2026-05-15, 2026-05-17, 2026-05-18, 2026-05-19, 2026-05-21, 2026-05-23, 2026-05-24, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-29, 2026-05-30, 2026-05-31

- **2026-06**: 2026-06-02, 2026-06-04, 2026-06-05, 2026-06-06, 2026-06-07, 2026-06-08, 2026-06-09, 2026-06-10, 2026-06-11, 2026-06-13, 2026-06-14, 2026-06-16, 2026-06-17, 2026-06-18, 2026-06-20, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25, 2026-06-26, 2026-06-27, 2026-06-28, 2026-06-29

- **2026-07**: 2026-07-03, 2026-07-04, 2026-07-05, 2026-07-06, 2026-07-08, 2026-07-09, 2026-07-11, 2026-07-12, 2026-07-13, 2026-07-14, 2026-07-17, 2026-07-24, 2026-07-25, 2026-07-26, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30

- **2026-08**: 2026-08-03, 2026-08-04, 2026-08-05, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13, 2026-08-14, 2026-08-15, 2026-08-16, 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-22, 2026-08-23, 2026-08-24, 2026-08-26, 2026-08-27, 2026-08-30, 2026-08-31

- **2026-09**: 2026-09-01, 2026-09-02, 2026-09-03, 2026-09-05, 2026-09-06, 2026-09-07, 2026-09-08, 2026-09-09, 2026-09-10, 2026-09-11, 2026-09-13, 2026-09-14, 2026-09-15, 2026-09-16, 2026-09-17, 2026-09-18, 2026-09-19, 2026-09-20, 2026-09-21, 2026-09-22, 2026-09-24, 2026-09-25, 2026-09-26, 2026-09-27, 2026-09-28, 2026-09-29, 2026-09-30

- **2026-10**: 2026-10-01, 2026-10-03, 2026-10-04, 2026-10-05, 2026-10-06, 2026-10-08, 2026-10-09, 2026-10-10, 2026-10-11, 2026-10-12, 2026-10-13, 2026-10-14, 2026-10-15, 2026-10-16, 2026-10-17, 2026-10-18, 2026-10-19, 2026-10-20, 2026-10-22, 2026-10-23, 2026-10-24, 2026-10-25, 2026-10-26, 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30, 2026-10-31

- **2026-11**: 2026-11-01, 2026-11-02, 2026-11-03, 2026-11-04, 2026-11-05, 2026-11-06, 2026-11-07, 2026-11-08, 2026-11-09, 2026-11-10, 2026-11-11, 2026-11-12, 2026-11-13, 2026-11-14, 2026-11-15

### DFS Service Requirement (Archive 2025/2026)

- **2024-11**: 2024-11-29

- **2024-12**: 2024-12-02, 2024-12-03, 2024-12-04, 2024-12-06, 2024-12-09, 2024-12-10, 2024-12-11, 2024-12-12, 2024-12-13, 2024-12-27, 2024-12-29, 2024-12-30

- **2025-01**: 2025-01-05, 2025-01-08, 2025-01-10, 2025-01-14, 2025-01-17, 2025-01-20, 2025-01-21, 2025-01-22, 2025-01-23, 2025-01-29

- **2025-02**: 2025-02-02, 2025-02-03, 2025-02-05, 2025-02-06, 2025-02-09, 2025-02-11, 2025-02-12, 2025-02-14, 2025-02-17, 2025-02-18, 2025-02-19, 2025-02-20, 2025-02-23, 2025-02-24, 2025-02-25, 2025-02-28

- **2025-03**: 2025-03-02, 2025-03-03, 2025-03-04, 2025-03-05, 2025-03-06, 2025-03-07, 2025-03-10, 2025-03-11, 2025-03-12, 2025-03-13, 2025-03-14, 2025-03-17, 2025-03-18, 2025-03-19, 2025-03-25, 2025-03-26, 2025-03-28, 2025-03-31

- **2025-04**: 2025-04-01, 2025-04-04, 2025-04-07, 2025-04-09, 2025-04-10, 2025-04-14, 2025-04-15, 2025-04-16, 2025-04-18, 2025-04-22, 2025-04-23, 2025-04-28, 2025-04-29

- **2025-05**: 2025-05-06, 2025-05-07, 2025-05-08, 2025-05-09, 2025-05-10, 2025-05-11, 2025-05-15, 2025-05-16, 2025-05-19, 2025-05-20, 2025-05-26, 2025-05-28

- **2025-06**: 2025-06-04, 2025-06-05, 2025-06-07, 2025-06-09, 2025-06-10, 2025-06-13, 2025-06-17, 2025-06-21, 2025-06-22, 2025-06-23, 2025-06-24, 2025-06-25, 2025-06-26, 2025-06-27, 2025-06-30

- **2025-07**: 2025-07-01, 2025-07-04, 2025-07-07, 2025-07-08, 2025-07-09, 2025-07-10, 2025-07-14, 2025-07-16, 2025-07-18, 2025-07-20, 2025-07-21, 2025-07-22, 2025-07-24, 2025-07-26, 2025-07-27, 2025-07-28, 2025-07-29, 2025-07-31

- **2025-08**: 2025-08-01, 2025-08-02, 2025-08-04, 2025-08-06, 2025-08-07, 2025-08-08, 2025-08-10, 2025-08-11, 2025-08-14, 2025-08-15, 2025-08-18, 2025-08-20, 2025-08-26

- **2025-09**: 2025-09-01, 2025-09-02, 2025-09-03, 2025-09-04, 2025-09-05, 2025-09-08, 2025-09-19, 2025-09-22, 2025-09-23, 2025-09-24, 2025-09-29, 2025-09-30

- **2025-10**: 2025-10-01, 2025-10-02, 2025-10-07, 2025-10-08, 2025-10-13, 2025-10-14, 2025-10-15, 2025-10-18, 2025-10-22, 2025-10-27, 2025-10-29

- **2025-11**: 2025-11-06, 2025-11-18, 2025-11-19, 2025-11-20, 2025-11-21, 2025-11-25, 2025-11-26

- **2025-12**: 2025-12-01, 2025-12-03, 2025-12-26, 2025-12-29, 2025-12-30, 2025-12-31

- **2026-01**: 2026-01-04, 2026-01-05, 2026-01-06, 2026-01-08, 2026-01-11, 2026-01-14, 2026-01-16, 2026-01-19, 2026-01-20, 2026-01-22, 2026-01-23, 2026-01-26, 2026-01-28, 2026-01-29, 2026-01-30

- **2026-02**: 2026-02-04, 2026-02-14, 2026-02-19

- **2026-03**: 2026-03-09, 2026-03-10, 2026-03-11, 2026-03-16, 2026-03-20, 2026-03-22, 2026-03-23, 2026-03-27

## Requested winter 2025/26 investigation

The archive has 238 Live service-window rows on 39 delivery dates from November 2025 through March 2026. Neither source supplies an identified, explicitly directed event within that period: the main resource starts later, and the archive omits both fields. Live denotes an operational requirement; it does not prove utilisation. The following useful winter alternatives remain unconfirmed date-based groups, not five identified NESO events:

| Date | Original Event ID | Window GMT | Duration | Requirement MW per window | Direction | Status | CKAN record IDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-11-18 | Absent | 16:00–20:00 | 240 minutes | 500.0 | Absent | Live | 229, 230, 231, 232, 233, 234, 235, 236 |
| 2025-12-01 | Absent | 16:00–18:00 | 120 minutes | 500.0 | Absent | Live | 179, 180, 181, 182 |
| 2026-01-06 | Absent | 16:00–19:00 | 180 minutes | 500.0 | Absent | Live | 137, 138, 139, 140, 141, 142 |
| 2026-02-19 | Absent | 16:00–20:00 | 240 minutes | 500.0 | Absent | Live | 41, 42, 43, 44, 45, 46, 47, 48 |
| 2026-03-09 | Absent | 16:00–20:00 | 240 minutes | 500.0 | Absent | Live | 33, 34, 35, 36, 37, 38, 39, 40 |


## Five provisional candidates

Direction semantics follow [NESO DFS Procurement Rules v5, effective 18 May 2026](https://www.neso.energy/document/379391/download): Downwards is demand reduction/generation increase; Upwards is demand increase/generation reduction. Recommendations use the demand-reduction branch of the request, while preserving the original Downwards label.

**All five are provisional candidates, not saved or final selections.** To use observed IDs and explicit Downwards values for demand reduction, the recommended period moves to November 2026. All five choices are in November and include evening windows. Prefer the requested winter period if an authoritative archive cross-reference can establish ID and direction.

Ranking: explicit Event ID, all windows Live and Downwards, positive MW, valid contiguous half-hour windows; then requested winter period, evening overlap (17:00–20:00), winter months, recent distinct delivery dates. Whole original events are shown, not arbitrary half-hour slices. Their multi-hour durations are stress cases and have **not** been shown feasible for five household batteries.

| Status | Original Event ID | Date | Start–end UTC / local | Duration | Intervals | Original requirement MW | Direction | Live/test | Source | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Provisional candidate | 218 | 2026-11-15 | 17:00–19:00 | 2 hours | 4 | 500.0 | Downwards | Live | Current | November evening, explicit direction/ID |
| Provisional candidate | 217 | 2026-11-14 | 16:00–19:00 | 3 hours | 6 | 500.0 | Downwards | Live | Current | November evening, explicit direction/ID |
| Provisional candidate | 216 | 2026-11-13 | 16:00–21:00 | 5 hours | 10 | 500.0 | Downwards | Live | Current | November evening, explicit direction/ID |
| Provisional candidate | 215 | 2026-11-12 | 16:00–23:00 | 7 hours | 14 | 500.0 | Downwards | Live | Current | November evening, explicit direction/ID |
| Provisional candidate | 211 | 2026-11-11 | 16:00–21:00 | 5 hours | 10 | 500.0 | Downwards | Live | Current | November evening, explicit direction/ID |


### Provisional candidate — Event 218

Current resource `3635fd80-49d7-4d02-964d-cc8c08d50302`; CKAN record IDs: 1, 2, 3, 4. Event tag: Energy. Dispatch: All Participants. All listed windows have original 500 MW requirement; it is not summed over time. At these dates the source local and UTC clock fields are identical.

Original zonal cap string: `Z1:500,Z2:500,Z3:500,Z4:500,Z5:500,Z6:500,Z7:500,Z8:500,Z9:500,Z10:500,Z11:500,Z12:500`.

Original eligible-bidder list: CUB (UK) LTD,ENGIE POWER LIMITED,AXLE ENERGY LIMITED,GRIDIMP LIMITED,INFINIS LIMITED,EQUIWATT LIMITED,HILDEBRAND TECHNOLOGY LIMITED,OCTOPUS ENERGY LIMITED,DRAX ENERGY SOLUTIONS LIMITED,ELECTRYONE AI LIMITED,OAKTREE POWER LIMITED,Shuffle Energy Limited,U ENERGY GROUP LIMITED,Edgware Energy Limited,Electric Miles Limited,AmpVerve Ltd,Bryt Energy Limited,GRIDVOLT UK LIMITED,Goonhilly Limited,Sancton Hill Limited,St Breock Limited,South Sharpley Limited.

### Provisional candidate — Event 217

Current resource `3635fd80-49d7-4d02-964d-cc8c08d50302`; CKAN record IDs: 5, 6, 7, 8, 9, 10. Event tag: Energy. Dispatch: All Participants. All listed windows have original 500 MW requirement; it is not summed over time. At these dates the source local and UTC clock fields are identical.

Original zonal cap string: `Z1:0,Z2:0,Z3:0,Z4:500,Z5:500,Z6:500,Z7:500,Z8:500,Z9:500,Z10:500,Z11:500,Z12:500`.

Original eligible-bidder list: CUB (UK) LTD,ENGIE POWER LIMITED,AXLE ENERGY LIMITED,GRIDIMP LIMITED,INFINIS LIMITED,EQUIWATT LIMITED,HILDEBRAND TECHNOLOGY LIMITED,OCTOPUS ENERGY LIMITED,DRAX ENERGY SOLUTIONS LIMITED,ELECTRYONE AI LIMITED,OAKTREE POWER LIMITED,Shuffle Energy Limited,U ENERGY GROUP LIMITED,Edgware Energy Limited,Electric Miles Limited,AmpVerve Ltd,Bryt Energy Limited,GRIDVOLT UK LIMITED,Goonhilly Limited,Sancton Hill Limited,St Breock Limited,South Sharpley Limited.

### Provisional candidate — Event 216

Current resource `3635fd80-49d7-4d02-964d-cc8c08d50302`; CKAN record IDs: 11, 12, 13, 14, 15, 16, 17, 18, 19, 20. Event tag: Energy. Dispatch: All Participants. All listed windows have original 500 MW requirement; it is not summed over time. At these dates the source local and UTC clock fields are identical.

Original zonal cap string: `Z1:0,Z2:0,Z3:0,Z4:500,Z5:500,Z6:500,Z7:500,Z8:500,Z9:500,Z10:500,Z11:500,Z12:500`.

Original eligible-bidder list: CUB (UK) LTD,ENGIE POWER LIMITED,AXLE ENERGY LIMITED,GRIDIMP LIMITED,INFINIS LIMITED,EQUIWATT LIMITED,HILDEBRAND TECHNOLOGY LIMITED,OCTOPUS ENERGY LIMITED,DRAX ENERGY SOLUTIONS LIMITED,ELECTRYONE AI LIMITED,OAKTREE POWER LIMITED,Shuffle Energy Limited,U ENERGY GROUP LIMITED,Edgware Energy Limited,Electric Miles Limited,AmpVerve Ltd,Bryt Energy Limited,GRIDVOLT UK LIMITED,Goonhilly Limited,Sancton Hill Limited,St Breock Limited,South Sharpley Limited.

### Provisional candidate — Event 215

Current resource `3635fd80-49d7-4d02-964d-cc8c08d50302`; CKAN record IDs: 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34. Event tag: Energy. Dispatch: All Participants. All listed windows have original 500 MW requirement; it is not summed over time. At these dates the source local and UTC clock fields are identical.

Original zonal cap string: `Z1:0,Z2:0,Z3:0,Z4:0,Z5:500,Z6:500,Z7:500,Z8:500,Z9:500,Z10:500,Z11:500,Z12:500`.

Original eligible-bidder list: CUB (UK) LTD,ENGIE POWER LIMITED,AXLE ENERGY LIMITED,GRIDIMP LIMITED,INFINIS LIMITED,EQUIWATT LIMITED,HILDEBRAND TECHNOLOGY LIMITED,OCTOPUS ENERGY LIMITED,DRAX ENERGY SOLUTIONS LIMITED,ELECTRYONE AI LIMITED,OAKTREE POWER LIMITED,Shuffle Energy Limited,U ENERGY GROUP LIMITED,Edgware Energy Limited,Electric Miles Limited,AmpVerve Ltd,Bryt Energy Limited,GRIDVOLT UK LIMITED,Goonhilly Limited,Sancton Hill Limited,St Breock Limited,South Sharpley Limited.

### Provisional candidate — Event 211

Current resource `3635fd80-49d7-4d02-964d-cc8c08d50302`; CKAN record IDs: 69, 70, 71, 72, 73, 74, 75, 76, 77, 78. Event tag: System. Dispatch: All Participants. All listed windows have original 500 MW requirement; it is not summed over time. At these dates the source local and UTC clock fields are identical.

Original zonal cap string: `Z1:0,Z2:0,Z3:0,Z4:0,Z5:0,Z6:0,Z7:0,Z8:0,Z9:0,Z10:0,Z11:0,Z12:500`.

Original eligible-bidder list: CUB (UK) LTD,ENGIE POWER LIMITED,AXLE ENERGY LIMITED,GRIDIMP LIMITED,INFINIS LIMITED,EQUIWATT LIMITED,HILDEBRAND TECHNOLOGY LIMITED,OCTOPUS ENERGY LIMITED,DRAX ENERGY SOLUTIONS LIMITED,ELECTRYONE AI LIMITED,OAKTREE POWER LIMITED,Shuffle Energy Limited,U ENERGY GROUP LIMITED,Edgware Energy Limited,Electric Miles Limited,AmpVerve Ltd,Bryt Energy Limited,GRIDVOLT UK LIMITED,Goonhilly Limited,Sancton Hill Limited,St Breock Limited,South Sharpley Limited.

## Remaining questions before final event selection

- Retain winter 2025/26 and obtain authoritative ID/direction cross-references, or accept the explicit late-2026 fallback events?
- Simulate complete 2–7-hour events or explicitly defined subwindows? A subwindow must preserve its parent source event and cannot be presented as the whole event.
- What geographic zone and registered aggregator would represent the portfolio? Nonzero zonal caps and named-provider eligibility must be checked; “All Participants” does not mean every household is eligible.
- Which utilisation/results records confirm activation and delivered performance? Service requirements alone cannot establish that.
- What separately justified scaled household commitment is appropriate after consumption and battery feasibility data exist? National 500 MW is not a five-house commitment. No final commitment or time mapping is assigned here.
- Confirm archive GMT and current UTC/local chronology before creating complete timestamps, particularly overnight events and daylight-saving transitions. Current code rejects ambiguous/non-contiguous intervals for candidate screening rather than guessing.
