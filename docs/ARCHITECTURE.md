> Task 05A current architecture: three pages via ui.app; validated read-only NESO/LCL explorer,
> configured battery portfolio, and three-tab Simulation Lab. New forecast_data/contracts/registry/
> simulation modules provide read-only history analysis, typed future forecasting and orchestration
> contracts, and explicit owner-only metadata persistence. No fit/predict/dispatch implementation.
> See [FORECASTING_FOUNDATION.md](FORECASTING_FOUNDATION.md). Earlier stage descriptions below are historical.

# Architecture

## Implemented foundation

`app.py` → `batteryflex.ui.app` → `batteryflex.ui.data_explorer`.
The shell provides the permanent Data Explorer and disabled future-stage navigation.
A read-only NESO client and pure exploration analysis now support explicit UI retrieval.
There is no importer, solver or persistence implementation yet.

## Intended boundaries

- UI: display saved records and collect explicit user actions; no SQL or model equations.
- Data access: future Turso repositories serve application reads by default.
- Import tools: separate explicit acquisition, validation and transactional persistence;
  no external acquisition during page rendering.
- Domain: household/battery/scenario contracts and feasibility checks, independent of UI.
- Forecasting and optimisation: pure inputs/outputs where practical, separate from storage.
- Simulation: closed-loop orchestration calls forecasts and MILP, applies only the first
  action, updates state and records a reproducible run.
- Evaluation: compare saved outputs against declared baselines and constraints.

Add these modules when their tasks start, rather than creating empty abstractions now.
Historical observations, simulated configurations and results have separate identifiers
and persistence tables. A scenario links them using an explicit time-mapping policy.
The eventual Data Explorer supports development investigation and read-only final use;
import tooling remains a separate explicit workflow.

## Safety and reproducibility

No startup database writes, migrations or remote downloads. Secrets enter through the
environment. Future run manifests record input versions, scenario mapping, seed, solver
settings/status and software version. Store energy in kWh and power in kW with interval
duration explicit. Never silently reinterpret raw source dates, time zones or units.

## Task 02 — explicit NESO investigation

`batteryflex.neso` uses the standard-library public CKAN client and holds a provenance-bearing
sample. Schema discovery, standardisation and inclusive filtering are independent of UI.
The existing Data Explorer adds a developer fetch button; it is the sole acquisition trigger.
Session state retains the fetched sample across filters, without downloads during reruns.
The saved-data empty state and disabled navigation remain. No persistence or Turso adapter
is implemented. See NESO_SOURCE_DISCOVERY.md for observed schemas and temporal semantics.

## Task 02B — full-history acquisition and screening

`neso.fetch_all` performs explicit ordered CKAN pagination, rejects changing totals/schema,
repeated/missing IDs and incomplete results, and keeps all raw business rows plus request
URLs/start/completion times. A 100,000-row bound prevents unbounded explorer acquisitions.
It cannot guarantee an atomic upstream snapshot. The UI stores complete results in session
state and performs no automatic refetch on filters. It does not read ignored analysis files.

`neso_analysis` owns pure coverage summaries, exact-business-duplicate comparison and
source-ID event grouping. Archive date groups have unknown event identity. Candidate
screening validates positive MW, Live status and contiguous half-hour intervals, and
supports either observed DFS direction. Recommendations default to Downwards for demand
reduction. National requirements, eligibility and simulation suitability remain separate.

## Task 02C — diverse historical review

`neso_intervals` resolves original source windows into separate aware UTC instants and
Europe/London display clocks. It validates source local/UTC pairs, daylight-saving folds,
nonexistent times, midnight rollover, gaps and overlaps. Interval generation splits at
both the elapsed 30-minute grid and actual requirement boundaries, retaining partial
pieces and direct/derived requirement provenance.

`neso_selection` adds source-regime evidence separately from absent raw directions/IDs,
monthly identified-event versus archive-date-group counts, elapsed duration distribution,
complete-signature duplicate checks and deterministic diverse recommendations. No
speculative final event identity is created. The existing per-source explorer remains;
`ui.neso_history` adds explicit three-resource retrieval and cross-resource review.

## Task 02D — fail-closed final eligibility

`neso_validation` assesses every mandatory criterion separately against original rows:
explicit Live status on every window, applicable official demand-reduction definition,
original historical dates, traceable record IDs, known resource/exact API provenance,
complete retrieval, finite positive MW and valid continuous chronology. FAIL or UNVERIFIED
excludes a group before diversity ranking; the ranking accepts an already validated pool.

Historical direction is verified through audited resource/date applicability and linked
historical definitions, not generic labels or unrelated fields. Internal scenario IDs
are deterministic BatteryFlex handles and never replace official IDs. The existing raw
explorer remains complete; the final detail scope defaults to Live and tests remain
inspectable under All historical groups. No scenario database persistence is implemented.

## Task 02E — public selection versus advanced investigation

`ui.neso_events` presents the frozen reviewed selection using `neso_manifest` and existing
`neso_intervals`. Package resources hold one versioned manifest with exactly five existing
Task 02D IDs and 17 original rows. Read-time checks verify version/count/content integrity;
no acquisition, reranking or duplicated eligibility implementation occurs. Streamlit caches
the local serialisable selection and gives each rerun its own data copy.

The default view is unselected. Summary/table/chart render only after user selection;
audit JSON and matrices render only when provenance is explicitly expanded. The Advanced
Historical Explorer toggle gates the existing source and cross-resource explorers, including
all Test records. No startup network calls, database writes or schema/model changes.

## Task 03 — local Low Carbon London lab

`lcl_source` owns explicit checksum-verified acquisition and source provenance. `lcl` owns
streaming wide-CSV audit, stable hash sampling, fixed-GMT interval-end parsing and quality
quarantine. `lcl_analysis` owns candidate metrics, quality/availability screening, five-house
selection and same-month/weekday replay mapping. It reads the frozen NESO selection and
existing interval generator without modifying either.

`scripts/prepare_lcl.py` is the explicit preparation boundary. It retains 100 columns and
92 dates while auditing every source cell, writing ignored Parquet/CSV and artifact hashes
with provenance JSON. `ui/lcl_lab` reads only these prepared artifacts, cached by audit
revision. The lab is gated separately within Data Explorer. No UI downloads, raw scans,
Turso, battery configuration or optimisation. Both original date pairs remain intact.

## Task 03B — progressive LCL presentation

`ui/lcl_lab` renders only the active explorer/comparison/replay/provenance view, retaining
cached prepared-data reads and integrity checks. `ui/lcl_views` contains display-only
chronological tables, valid-reading typical profiles, gap segmentation and complete-day totals
with separate incomplete/not-retained status. It does not replace Task 03 processing or alter
prepared artifacts. `ui/lcl_charts` owns GMT Vega-Lite charts, hover/zoom and stable ID colours.
The NESO replay uses the existing frozen selection for summaries and optional national MW;
household comparisons remain kW. Existing NESO UI and all source/selection modules are untouched.

## Current public architecture — Task 03E

This section supersedes earlier public-navigation descriptions. app.py → ui.app registers
exactly ui.explorer.render_data_explorer (default), ui.planned.render_portfolio and
ui.planned.render_simulation. Data Explorer uses two lazy native NESO/LCL tabs; old detailed
research UI modules remain internal, with regression harnesses outside product navigation.
Frozen source/household artifacts and all existing processing/validation are preserved.

Simulation Lab integrates experiment setup, future run, empty results and comparison/evaluation
on one page. simulation_contracts holds immutable equivalent-input/run/metric snapshots and
pure append/group/scoped-clear semantics. It is not a persistence adapter or engine. No
startup writes, durable result storage, battery objects, models or fabricated outputs. See
UI_ARCHITECTURE.md for exact contracts, planned automatic pipeline and comparison invariants.
