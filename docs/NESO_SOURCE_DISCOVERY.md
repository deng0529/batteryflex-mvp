# NESO source discovery — Task 02

This section records the original sample-only Task 02 findings. For current full-history
behaviour and coverage, see the Task 02B update below and NESO_HISTORY_ANALYSIS.md.

Verified 2026-11-16 through the implemented client. No credentials, database access,
permanent dataset files or additional dependencies. Supported by National Energy SO Open Data.

Official catalogue: https://www.neso.energy/data-portal/demand-flexibility
Licence: https://www.neso.energy/data-portal/neso-open-licence (NESO Open Data Licence v1.0).

## Verified public requests

- Current: https://api.neso.energy/api/3/action/datastore_search?resource_id=3635fd80-49d7-4d02-964d-cc8c08d50302&limit=100
  Retrieved 2026-11-16T13:41:57.859576+00:00: 100 rows of 2004; sample delivery
  dates 2026-11-10 through 2026-11-15.
- Archive: https://api.neso.energy/api/3/action/datastore_search?resource_id=f5605e2b-b677-424c-8df7-d0ce4ee03cef&limit=100
  Retrieved 2026-11-16T13:41:58.030459+00:00: 100 rows of 1132; sample dates
  2024-11-29 through 2026-03-27 (not continuous). Despite the archive's 2025/2026
  label, actual records include 2024. Filters use returned values, never the label.

The API's default sample order is not chronological; no full coverage is claimed.
No pagination or full historical acquisition is implemented. Each UI fetch records
its own exact request URL, resource ID and UTC acquisition timestamp.

## Discovered columns

Current: `_id`, `Event ID`, `DFS Submission Time_Local`, `Event Type`, `Event Tag`,
`Delivery Date`, `From_Local`, `To_Local`, `From_UTC`, `To_UTC`,
`Service Requirement MW`, `Service Requirement Type`,
`Guaranteed Acceptance Price GBP per MWh`, `Dispatch Type`,
`Participant Bids Eligible`, `Zonal Cap`.

Archive: `_id`, `Delivery Date`, `From`, `To`, `Service Requirement MW`,
`Service Requirement Type`, `Guaranteed Acceptance Price GBP per MWh`,
`Dispatch Type`, `Participant Bids Eligible`.

Discovery unions API field metadata with keys from every returned row, reporting
source types, observed Python types and null/blank/absent counts. Raw objects remain
unchanged. Unknown columns remain visible; unknown envelope shapes fail clearly.

## Mapping and limits

A separate representation maps Event ID, Delivery Date, From_UTC/From/From_Local,
To_UTC/To/To_Local, Service Requirement MW, Event Type and Service Requirement Type.
The UI displays the exact mapping. Unavailable values stay null. The API `_id` is a
record identifier, not an event ID; `source_row` is a sample-local lookup index only.
Source events can contain multiple service windows; selecting a row previews the
complete original record and does not select or save five events.

Delivery dates parse separately (ISO or day/month/year). Source time strings and
local/UTC fields remain untouched. Current normalised times prefer the explicit
UTC columns; archive From/To are GMT per official archive table metadata. Local
fallbacks carry a local label without assigning an offset. No combined instants,
DST resolution, inferred midnight rollover or simulation time mapping is performed.
Required power remains MW, separate from later kW domain contracts. Invalid numeric
values become null in the derived table only. Dates that cannot be parsed are
reported and excluded by date filters, but retained in unfiltered raw records.

Service Requirement Type describes Live/Test; current Event Type describes
Upwards/Downwards. These are separate filters populated from actual sample values.
The archive has neither event ID nor direction; no grouping or direction is inferred.
No claim about delivered flexibility can be made from procurement requirements alone.

Official field semantics:
https://www.neso.energy/data-portal/demand-flexibility/dfs_service_requirement
https://www.neso.energy/data-portal/demand-flexibility/dfs_service_requirement_archive_20252026

## Task 02B — complete history and provisional screening

Task 02's 100-row observations above are superseded for historical coverage by
[NESO_HISTORY_ANALYSIS.md](NESO_HISTORY_ANALYSIS.md). The complete current resource has
2004 rows across 169 dates; archive has 1132 across 190 dates. See the complete analysis
for all dates, types/missingness and overlaps, and [NESO_DATA_DICTIONARY.md](NESO_DATA_DICTIONARY.md)
for every original field and provenance mapping. The sample control remains available;
a separate explicit full-history button now retrieves every sorted API page.

Important DFS convention verified in Procurement Rules v5 (18 May 2026): **Downwards
means demand reduction/generation increase; Upwards means demand increase/generation
reduction**. Do not apply generic reserve direction terminology to these DFS labels.
Primary provisional recommendations use Downwards for the residential reduction objective.
The archive direction remains absent. Source: https://www.neso.energy/document/379391/download .
