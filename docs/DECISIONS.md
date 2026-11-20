# Decisions

## D001 — Isolated foundation (2026-11-16)

The parent workspace is an unrelated, dirty repository on main with many pre-existing
tracked deletions and untracked projects. Create the new project in `batteryflex/`;
do not restore, stage, commit or otherwise change those existing files or Git state.
No separate nested repository is created. Review project placement before the first commit.

## D002 — Minimal Python and Streamlit

Use Python 3.12+, setuptools src packaging, Streamlit native navigation, pytest AppTest
and Ruff. Keep UI separate from future data/domain modules. No unused solver or
database libraries until those tasks. Dependency ranges are in pyproject.toml;
a deployment lock/pinning policy will be selected before deployment.

## D003 — Saved data first

Turso will serve application reads. Imports are explicit, validated, provenance-bearing
operations. Task 01 has no database adapter and makes no database connections.

## D004 — Historical chronology and simulation

NESO history and 2013 Low Carbon London consumption are not contemporaneous.
Preserve raw times; represent cross-period alignment as a separately versioned scenario
assumption. Simulated batteries and run outputs are separate from historical data.

## D005 — Foundation scope

Show a truthful Data Explorer empty state and disabled planned navigation. No sample
datasets, fake records, import controls or placeholder optimisation implementations.

## D006 — Explicit session-only NESO sample (2026-11-16)

The Task 02 request authorizes public source reads and extends exploration to the existing
UI. Use bounded CKAN samples from current and archive resources, fetched only by an
explicit developer action. Preserve raw data and expose a separate nullable mapping.
No permanent import, five-event persistence, Turso, household integration or model work.

## D007 — Complete NESO exploration and source direction (2026-11-16)

Task 02B authorizes complete public history retrieval and provisional analysis only.
Retain the sample button and add explicit stable-ID pagination, fail closed on detectable
incomplete/changing data, and preserve all raw records. Do not deduplicate coincident
windows across distinct event IDs/directions/tags. Per DFS Procurement Rules v5, Downwards
is the demand-reduction direction; Upwards is demand increase. Rank Downwards for this
residential reduction objective while supporting both raw labels in the explorer. Archive
IDs/direction remain unknown; no fabricated identity or inferred final event selection.

## D008 — Historical event proxies and explicit interval provenance (2026-11-16)

Task 02C requests diversity over recency. Official service history establishes the
pre-9-Apr-2026 reduction-only regime for known requirement archives. Preserve absent raw
ID/direction and annotate that evidence separately. Historical date groups remain
provisional event proxies, not newly minted NESO identifiers. Prefer complete winter
windows across months/years with the requested duration mixture over arbitrary subevents.
Use aware UTC elapsed time and original local/UTC evidence for interval chronology;
reject ambiguity/gaps and preserve partial boundaries and source-varying MW. National
requirements remain separate from future portfolio commitments. No scenario persistence.

## D009 — Reviewed Live-only scenario inputs (2026-11-16)

Task 02D makes verified Live status, direction, source chronology and valid MW/window
mandatory, ahead of diversity preferences. Enforce this with an all-PASS eligibility gate
before ranking. For archive direction, cite applicable original DFS definitions (2024 v3
service terms clause 5.2; 2023/24 guidance), rather than rely solely on later service-history
context. Do not fill absent raw direction or official Event IDs. Assign clearly internal
BatteryFlex scenario IDs; preserve row references and content fingerprints. Independently
cross-check the five chosen input series against original official CSVs. Keep every Test
record available for inspection, but never permit it into final recommendations.

## D010 — Reviewed public-selection snapshot (2026-11-16)

Task 02E explicitly authorises a small versioned local manifest for immediate offline
availability. Generate it from the Task 02D reviewed full snapshots using existing logic,
and fail generation if scenario IDs or source-record hashes differ from the review report.
Keep only 17 selected original rows plus provenance and reviewed validation output in the
package asset. Do not re-run discovery, selection or validation on public-view reruns.
This narrow manifest exception does not authorise other dataset commits or persistence.
Default to no selected event, collapsed audit information and closed advanced exploration.

## D011 — Explicit local LCL exploration and replay (2026-11-16)

Task 03 requests saved local exploration without Turso. Use checksum-verified one-time
public acquisition and a streaming audit; preserve raw timestamps and kWh text. Fixed-GMT
labels mark interval ends. Derive starts and average kW separately; never fill missing demand.
Retain a deterministic hash sample, 90 Jan–Mar heating-season days and two extra replay days.

Screen quality/event load availability before five evenly spaced daily-energy representatives;
never rank on extreme peaks or infer batteries. Map frozen NESO windows to nearest same-month,
exact-weekday 2013 dates, preserving both time references. Calendar mapping does not maximise
demand. Local artifacts/cache are a narrow Task 03 exception to the future Turso default.
No database, dispatch, commitment or feasibility result. See LCL_DATA_LAB.md; stop for review.
