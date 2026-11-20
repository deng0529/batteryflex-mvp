# NESO data dictionary — Task 02B

Examples below are actual values from complete public API retrievals on 2026-11-16, not documentation examples. Supported by National Energy SO Open Data. Source types and complete missing counts are reported in NESO_HISTORY_ANALYSIS.md.

Official meanings: https://www.neso.energy/data-portal/demand-flexibility/dfs_service_requirement and https://www.neso.energy/data-portal/demand-flexibility/dfs_service_requirement_archive_20252026

| Original column | Plain-English meaning | Unit | Actual example | BatteryFlex need | Standardised mapping |
| --- | --- | --- | --- | --- | --- |
| _id | CKAN row identifier, scoped to this resource; not a flexibility event identifier | none | 1 | Traceability | source_record_id |
| Event ID | Original NESO event identifier; repeats across that event's service windows | none | 218 | Essential when supplied | event_id |
| DFS Submission Time_Local | Auction bid submission close, in source local time; not delivery start | local date/time text | 15-11-2026 12:45 | Context | Raw only |
| Event Type | Original DFS direction: Downwards = demand reduction / generation increase; Upwards = demand increase / generation reduction. Missing in archive | category | Downwards | Essential to confirm reduction preference | direction |
| Event Tag | Energy or System procurement classification | category | Energy | Context / eligibility review | event_tag |
| Delivery Date | Original date of the service requirement | calendar date | 2026-11-15 | Essential | delivery_date (parsed separately; raw retained) |
| From_Local | Delivery-window start in source local clock | HH:MM local | 17:00 | Essential context for local simulation | start_local; start_time only if no UTC/GMT field exists |
| To_Local | Delivery-window end in source local clock | HH:MM local | 17:30 | Essential context for local simulation | end_local; end_time only if no UTC/GMT field exists |
| From_UTC | Delivery-window start clock labelled UTC by source | HH:MM UTC | 17:00 | Essential | start_time (preferred) |
| To_UTC | Delivery-window end clock labelled UTC by source | HH:MM UTC | 17:30 | Essential | end_time (preferred) |
| From | Archive delivery-window start, GMT per official metadata | HH:MM GMT | 16:00 | Essential | start_time (archive) |
| To | Archive delivery-window end, GMT per official metadata | HH:MM GMT | 16:30 | Essential | end_time (archive) |
| Service Requirement MW | Published requirement for this service window; not delivered flexibility or a household target | MW | 500 | Essential | required_mw (finite numeric; original retained) |
| Service Requirement Type | Live operational procurement requirement or Test requirement | category | Live | Essential | requirement_type |
| Guaranteed Acceptance Price GBP per MWh | Guaranteed acceptance threshold for qualifying bids; not an observed clearing price, tariff or revenue | GBP/MWh | 0 | Optional context | Raw only |
| Dispatch Type | Whether all registered providers or a subgroup may bid | category | All Participants | Eligibility review required | dispatch_type |
| Participant Bids Eligible | Names of providers permitted to bid; not household IDs | comma-separated provider names | CUB (UK) LTD (first name from actual list; full lists in analysis) | Eligibility review required | eligible_participants |
| Zonal Cap | Maximum procurement by named zone; zero caps restrict procurement despite a positive overall MW requirement | MW per zone, string map | Z1:500,Z2:500,Z3:500,Z4:500,Z5:500,Z6:500,Z7:500,Z8:500,Z9:500,Z10:500,Z11:500,Z12:500 | Eligibility review required where present | zonal_cap (raw string; no allocation inferred) |


## Essential provenance and derived fields

| Field | Meaning / handling |
| --- | --- |
| source_name / resource_id | Original source title and UUID; every derived row carries both. |
| source_url / request_urls | Exact public API first-page URL and all sorted page URLs in retrieval metadata. |
| retrieved_at / completed_at | UTC ISO acquisition start (first page response) and completion timestamps. |
| complete / total | Explicit full-retrieval marker and original declared total; partial retrieval cannot silently pass as complete. |
| source_record_id / source_row | Original CKAN _id versus ephemeral row position used to inspect the original object. Neither substitutes for missing Event ID. |
| time_basis | UTC for explicit _UTC columns; GMT for archive From/To per metadata; local fallback is labelled without assigning an offset. |
| duration_minutes / contiguous_30min | Derived only for contiguous same-date positive 30-minute windows on half-hour boundaries. Overnight rollover is not inferred. |
| required_mw_by_window | Unique observed standardised MW levels within event; never sum power over time. Original interval MW remains visible. |
| candidate_status / screening_reason | Provisional screening output, not verified feasibility, activation, persistence or an investment/market eligibility conclusion. |


## Missingness and chronology

Archive event ID, direction, tag, local/UTC dual-clock columns and zonal cap do not exist. No generated ID, assumed Upwards direction or invented zone is substituted. `_id` stays a row key. Raw fields and time strings are immutable; parsed dates are a separate representation. Current local dates and UTC clock fields are not combined into complete UTC instants, because their date relationship around midnight requires explicit verification. No DST localisation, midnight rollover or cross-period household alignment is applied.

NESO DFS Procurement Rules v5 (effective 18 May 2026), Schedule 1, define Downwards as demand reduction / generation increase and Upwards as demand increase / generation reduction. Primary recommendations screen Downwards for the demand-reduction objective; the UI supports either original direction. No direction is assigned to directionless archive records. Source: https://www.neso.energy/document/379391/download . Live refers to the requirement category, not confirmed delivered response. Source eligibility is separate from simulation suitability.

## Task 02C dictionary additions

The official 2023/24 resource (`7914dd99-fe1c-41ba-9989-5784531c58bb`) supplies
`DFS Required MW` → required_mw and `Despatch Type` → dispatch_type. `From` and `To` are
GMT per metadata, with actual `HH:MM:SS` text. ID and direction fields are absent.

| Derived field | Meaning |
| --- | --- |
| demand_reduction / direction_evidence | Explicit Downwards or separately documented pre-bidirectional DFS regime; does not fill raw direction |
| identity_basis | Actual Event ID or explicitly uncertain source/date requirement group |
| start_utc / end_utc | Separate aware instants derived from verified source clocks/date; never replace raw values |
| start_uk / end_uk | Europe/London ISO times including UTC offset, disambiguating repeated autumn clocks |
| duration_hours / duration_minutes | Actual elapsed UTC time, not naive wall-clock subtraction |
| requirement_basis | Direct source-window value versus repeated within-window simulation assumption |
| partial_interval | True when a source/grid boundary piece lasts less than 30 minutes |

See NESO_DIVERSE_EVENTS.md for complete time-zone policy, provisional event references
and available monthly counts. This supersedes Task 02B's conservative refusal to form
complete instants where current local/UTC clock pairs now provide sufficient evidence;
ambiguous clocks without that evidence still reject conversion.

## Task 02D — validation and original CSV representation

| Field | Meaning |
| --- | --- |
| internal_scenario_id | Labelled BatteryFlex scenario handle; never an original NESO ID |
| validation_status | Overall PASS only when every mandatory criterion passes |
| validation_criteria / validation_reasons | Per-criterion PASS, FAIL or UNVERIFIED plus evidence/explanation |
| verified_direction_meaning / direction_definition_url | Meaning established from the applicable official definition; raw Event Type stays unchanged |
| source_records_sha256 | Canonical original API-record-set content fingerprint for this review |
| winter_season | Derived chronology label, separate from the source resource title |

Original CSV delivery dates are DD/MM/YYYY; CKAN dates are YYYY-MM-DD. Legacy CSV clocks
are HH:MM; CKAN clocks are HH:MM:SS. The final audit compared them after separate parsing,
without replacing original strings. CKAN _id and CSV data-row ordinal are source lookup
references, not official Event IDs. See NESO_FINAL_VALIDATION.md for all exact references.
