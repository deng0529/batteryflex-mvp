# Current handoff — BatteryFlex MVP v1.0

20 November 2026. [Streamlit deployment instructions](STREAMLIT_DEPLOYMENT.md).

- The release uses a standalone Git snapshot. The unrelated development
  repository and its history remain outside the release.
- Community Cloud uses root `app.py`, Python 3.12, pinned dependencies and
  `libgomp1` for the Linux LightGBM wheel. A clean Ubuntu WSL install started
  Streamlit and verified both LightGBM import and a SciPy HiGHS solve.
- Cloud defaults to saved-only demo mode. Use a separate authorised operator
  instance with `BATTERYFLEX_ACCESS_MODE=owner` for writes and new computation.
- The production audit verified 15/15 compatible event-only runs, 15 event
  forecasts and 32 archived full-day bundles. The active portfolio matches
  the defaults. The audit made no production changes.
- The Community Cloud deployment still needs the owner's sign-in, GitHub
  authorisation and scoped storage secrets. Verify the hosted app using the
  deployment guide before sharing it.

---

# Current handoff — BatteryFlex product refinement

20 November 2026. Existing branch `codex/task06a-rbc-export-replay`. Ready for local review.
[Product refinement report, release findings and screenshot index](PRODUCT_REFINEMENT.md).

- Overview is the default landing page. Data Explorer, Portfolio & Configuration and
  Simulation Lab retain the validated workflows under a common Streamlit theme.
- The packaged architecture SVG adapts the original three-layer diagram. Four validated
  YAML-subset defaults files centralise presentation and scenario controls. The event
  registry preserves the original hashed snapshot.
- The previous 15 Experiment A fingerprints match. The isolated rerun matched all
  30 trajectory outputs within 1e-6 with a maximum numerical difference of zero.
  Restart, missing-forecast isolation, batch recovery and read-only comparisons passed.
- All 364 tests passed. Ruff, formatting, type and compile checks passed. Screenshots
  were captured from the actual app on isolated saved data.
- Git currently sees BatteryFlex as untracked under the parent repository. Review the
  release boundary and hosted access policy before publication. No production writes
  or Git publication actions were performed.

---

# Current handoff — Task 06 five-event batch verification

20 November 2026. Existing branch `codex/task06a-rbc-export-replay`.
[Technical report and verification evidence](TASK06_BATCH_VERIFICATION.md).

- The read-only production audit verified all 15 default event-only Turso/R2 bundles,
  plus 32 legacy full-day runs. Each method had one existing result before the batch
  saved its other four.
- Event selection loads its exact saved scenario. Batch progress identifies stored,
  newly saved and failed events. One unavailable event does not block the other four.
- Comparison defaults to All Five Events and Historical Replay. It counts verified
  compatible results together across unequal event durations and retains the individual
  comparison and technical evidence.
- The isolated Streamlit run verified all 15 persistent scenarios across restart and
  recovery. All 359 automated tests passed, along with Ruff and type checks.
- No production writes, mathematical model changes, additional experiments or deployment.

---


# Current handoff — Task 06 Experiment A event-only dispatch

20 November 2026. Existing branch `codex/task06a-rbc-export-replay`. Ready for review.
[Implementation, screenshots and verification](TASK06_EVENT_ONLY.md).

- The five registry events execute 2, 2, 3, 4 and 6 half-hours. All methods start from
  the same configurable synthetic event-start SoCs and qualify against the same
  zero-shortfall forecast model. Completed actual averages are used in replay safety
  checks and scoring after the decision.
- All 15 isolated method/event scenarios met the request. The three-hour case delivered
  30 kWh with 0 RBC solves, 6 MPC solves per trajectory and 1 shared standalone MILP solve.
  Event-only fingerprints remain distinct from the legacy full-day records.
- All 15 cache hits were verified with new repository instances. The cloud audit was
  read-only and matched all 32 existing full-day fingerprints. There is no SQL migration.
- The dashboard, one-event comparison and five-event comparison were captured in
  `outputs/task06-event-only/`. The full suite passed with 359 tests. Ruff and type checks passed.

---

Previous handoff retained for context:

# Current handoff — Task 06 explanatory dashboard and five-event batch

19 November 2026. Existing branch `codex/task06a-rbc-export-replay`. Ready for review.
[Implementation, local preview and verification](TASK06_DASHBOARD_BATCH.md).

- The results-first dashboard defaults to Historical Replay and keeps Forecast Planned
  selectable. Interval targets report each miss, capped credited delivery and evidence-based
  shortfall explanations. Energy-only targets use the event total.
- Each controller can independently run the five configured events with per-event
  progress, saved-first reuse, failure isolation and an energy/status summary. The saved
  comparison supports both one-event and five-event scopes and matches methods within
  each event by forecast artifact and shared numerical inputs.
- The default replay targets totalled 85.00 kWh. RBC met four events and delivered
  84.41 kWh. MPC met all five and delivered 85.00 kWh. The final RBC miss was
  8.818 kW against 10.000 kW at 18:30 GMT on 2 February 2025, with energy availability
  binding at the recorded states.
- Full regression suite passed with 350 tests and the final targeted run passed six.
  Ruff and type checks passed. Read-only Streamlit restored the batch, showed 15
  comparison rows and verified all 32 saved bundles. Evidence is in
  `outputs/task06-dashboard/`.

---

Previous handoff retained for context:

# Current handoff — Task 06 MPC results, comparison and saved-first caching

19 November 2026. Existing branch `codex/task06a-rbc-export-replay`. Ready for review.
[Implementation, preview and verification](TASK06_MPC_COMPARISON.md).

- The MPC expander shows both trajectories' event solves, five battery actions and an
  executed-cost ledger. The 18 March replay has 48 daily solves and two event intervals.
  Its event horizons are 12 and 11 steps because the forecast horizon ends at midnight.
- Comparison & Evaluation discovers saved compatible runs and shows objective, event
  power, final SoC and paired metrics. Default three-method and separate two-method
  £0.25/kWh groups were verified. The £0.10/kWh default is retained.
- Existing SQL tables and R2 bucket support v2 bundles, versioned fingerprints, completed
  summaries, locks, staged recovery and append-only object repair. Cold reads restored
  new and legacy runs with compute and writes blocked. All 18 prior results matched.
- Full suite passed with 345 tests. Focused dispatch and persistence, Ruff and type
  checks passed. Live evidence is in `outputs/task06-comparison/`.

---

Previous handoff retained for context:

# Current handoff — Task 06 results-first UI refactor

19 November 2026. Existing branch `codex/task06a-rbc-export-replay`. Ready for review.
[Changes, local preview and verification](TASK06_UI_REFACTOR.md).

- Each method opens with NESO fulfilment, a grouped half-hour power chart and a short
  conclusion. The shared layout retains paired performance, event intervals, the
  five-battery table, objective contributions and method explanations.
- The headline checks each event half-hour. A saved whole-event energy result may still
  show MET even when a power interval is missed. The UI labels these separately.
- Visible technical identifiers, forecast provenance, all-day charts and schedules, CSV
  actions and technical trace sections were removed from the results presentation.
- Read-only Streamlit verification restored RBC, MPC and MILP with all 18 run indexes
  matching. The battery, grid, flexibility and objective values reconciled for all
  six trajectories. Full suite passed with 340 tests. Ruff and type checks passed.

---

Previous handoff retained for context:

# Current handoff — Task 06A export and paired forecast–replay evaluation

18 November 2026. Branch `codex/task06a-rbc-export-replay`. Complete and ready for review.
[Implementation, example results and verification](TASK06A_EXPORT_REPLAY.md).

- Participating batteries automatically receive target-serving event export permission in
  RBC, MPC and MILP, with explicit or labelled assumed connection caps. The effective limits
  and export policy are part of the run fingerprint.
- One run shows both trajectories, starting with side-by-side NESO fulfilment. The page
  follows with five-battery and portfolio results, trace-based attribution, the five RBC
  rules, objective and tariff comparisons, paired charts and both dispatch CSVs.
- The 18 March 2025 replay met both 10 kW intervals for all three methods. RBC delivered
  10.000 kWh on both trajectories and exported 5.584 kWh planned and 5.652 kWh replay.
  Its event actions matched. Demand changed the local-use and export split.
- Dedicated Turso/R2 saved three paired runs. Cold-cache Streamlit processes restored them
  with optimisation and writes blocked. Prior 15 run indexes, 27 pre-existing cloud tables
  and 55 protected Task 05 file hashes were verified. Evidence is in `outputs/task06a/`.
- Full regression suite passed with 339 tests. The final 14 dispatch tests, Ruff and type
  checks passed. Verification servers were stopped.

---

Previous handoff retained for context:

# Current handoff — Task 06 battery dispatch optimisation and simulation

18 November 2026. Branch `codex/task06-battery-dispatch-optimisation`. Complete and ready for
review. [Implementation, case results and verification](TASK06_DISPATCH.md).

- Simulation Lab → Run Simulation & Results now runs RBC, rolling mixed-integer MPC and
  full-day HiGHS MILP using the exact saved event forecast and the saved five-battery portfolio.
  Scenario edits apply to individual runs. The UI includes equations, dispatch charts and CSV,
  objective contributions, execution traces and interval-by-interval fulfilment.
- All 15 example method/event runs completed and were saved to dedicated Turso/R2.
  The 10 kW scenario target with export disabled was NOT MET in all 15 historical replays.
  Two fresh Streamlit processes restored the first event's three saved methods read-only.
  Live verification also exercised the five-event MILP batch and all saved forecast selections.
- All 27 pre-existing cloud tables and 55 protected Task 05 file hashes matched the prior
  verification baseline after accounting for the new run references. Evidence is in
  `outputs/task06/`. Both verification servers were stopped.
- Full regression suite passed with 334 tests. Ruff lint, Ruff formatting and source/script
  type checks passed. Changes are available in the workspace. The parent Git repository lists
  BatteryFlex as untracked.

---

Previous handoff retained for context:

# Current handoff — Task 05 final UI cleanup

18 November 2026. Branch `codex/task05-final-ui-cleanup`. Complete and ready for review. [Cleanup report](TASK05_FINAL_UI_CLEANUP.md).

- Forecast Model Development retains the five NESO events, main exact historical date table with usable-day counts, model controls and portfolio evaluation configuration, saved-data-first Run Event Models, household/portfolio full-day curves, accuracy bar chart and a visible full-day MAE/RMSE table/download.
- Removed from this page: detailed household dates, historical quality, calendar/coverage explanation, recommendation/version/provenance display, extra event/holdout comparison and all peak sections. Supporting resolver/diagnostic/storage code and historical artifacts remain intact.
- Restored saved results show “Saved forecasting results loaded”; genuinely missing models trained by an explicit request show “Models trained and saved”. No manual save or activation added. Invalid saved artifacts fail clearly, with no implicit regeneration/overwrite.
- Full regression suite: 325 passed in 307.08 seconds. Final UI/failure-path subset: 4 passed in 91.19 seconds. Ruff check/format and source/script type checks pass.
- Live verification: two separate Streamlit processes, each with a fresh disk cache; all five events restored in both; 20 repeated Run Event Models clicks; two fresh browser sessions. Training, prediction generation, uploads and SQL mutations prohibited and none attempted. All 27 cloud tables and 55 protected code/data hashes unchanged. Temporary servers stopped.
- No model, source, event mapping, schema, saved forecast/metric, or previous-MVP resource changed. No new forecasting algorithm/peak improvement or Task 06 optimisation. No staging, commit, merge or deployment. Unrelated parent-project changes untouched.
- Evidence is in ignored `outputs/task05-final/` (`report.json`, before-state snapshot, protected hashes, per-process/event UI snapshots and server logs).

---

Previous handoff retained for context:

# Current handoff — Automatic saved event forecast resolution

18 November 2026. Branch `codex/automatic-event-forecast-resolver`. Requested removal of manual forecast activation implemented; [contract, verified versions and integration example](FORECAST_RESOLVER.md).

- Event forecasting has no activation button, selector or active-model status. The canonical recommendation and exact saved version remain visible even when chart/model controls or unsaved experimental settings change.
- Ridge/LightGBM automatic selection uses saved validation portfolio RMSE only; exact ties select Ridge. Seasonal Naive is benchmark-only for automatic selection. Explicit overrides support Ridge, LightGBM and Seasonal Naive without saving a preference.
- `resolve_event_forecast(repo, event_id, algorithm=...)` checks the stored NESO/replay mapping and existing SHA-256/fingerprint-verified bundles. It returns 240 household and 48 portfolio forecast rows, exact version, dataset/request IDs and origin metadata, excluding actual targets. Missing saved candidates fail explicitly; automatic mode requires both ML candidates and override mode only the requested method. No fit/run/activation lookup is performed.
- The planning-only Run Simulation & Results view resolves the selected event directly, removing its old activation gate. Execution remains disabled. The legacy plan name/version value type remains for compatibility without activation writes.
- Fresh-cache live checks passed for all five automatic recommendations and all algorithm overrides with training, uploads, SQL mutations and activation-table reads during resolution blocked. All 27 cloud tables and all protected source/model hashes unchanged. Existing populated activation records were preserved, not cleared. No migration, artifact overwrite/deletion, new cloud resource or previous-MVP access.
- Full regression suite: 322 passed in 161.90 seconds. Live UI verified all five saved recommendations and Run Event Models reuse with no activation controls/status. A final entry-point/planning check also blocked legacy activation reads and succeeded; unsaved configuration changes preserve the recommendation. Ruff check/format, source/script type checks and protected hashes pass. All temporary verification servers stopped. Final evidence is recorded in the resolver report. No Task 06 optimisation, staging, commit, merge or deployment.

---

Previous handoff retained for context:

# Current handoff — Task 05E UI and peak diagnostics

18 November 2026. Branch `codex/task05e-forecast-ui-peak-analysis`, from Task 05D. Complete and ready for review; no staging, commit, merge or deployment. [Completion report](TASK05E_PEAK_ANALYSIS.md).

- Visible development is event-only; the legacy benchmark remains intact and regression-tested outside navigation. Other Simulation Lab tabs are unchanged.
- Exact persisted training/validation/holdout/event calendar dates appear immediately. Expandable household rows show admitted first/last dates, usable days and target sample counts; counts are verified against saved artifacts.
- One selectable household/portfolio full-day chart (48 half-hours, all four curves, event shading and legend selection); one full-day RMSE chart. Other errors remain in a compact expander/download.
- Read-only daily peak bias/timing and training-Q90 high-demand MAE for all five homes and portfolio. Ridge underestimates 25/25 household maxima, LightGBM 22/25 on the selected sample. Recommendations remain validation-based; no automatic activation.
- All 15 cloud bundles reused with fitting, uploads and non-SELECT SQL blocked. Every row in all 27 Turso tables and all protected source/model hashes unchanged. UI restored all five events and three methods; no model activated. No migrations, new cloud objects/resources or previous-MVP access.
- Full suite: 313 passed. Final peak/UI subset: 9 passed with no warnings after explicit pandas sort fix. Ruff and source/script type checks pass. Evidence and exact dates/peak results in report and ignored `outputs/task05e/`.
- Reproduce diagnostics: `.venv/Scripts/python.exe scripts/analyse_event_peaks.py`. This fails if saved models are absent and never trains, migrates or writes to cloud.
- Task 06 remains unstarted. Temporary verification server stopped. Work remains uncommitted as requested; unrelated parent-project changes untouched.

---

Previous handoff retained for context:

# Current handoff — Task 05D event forecasts

18 November 2026. Branch `codex/task05d-event-aligned-forecasting`. All phases completed; see [full report](TASK05D_EVENT_FORECASTING.md) and [Phase A investigation](TASK05D_PHASE_A.md). Dedicated cloud dataset plus 15 bundles/360 metrics persisted; cold-cache requests reused all 15 with zero training or mutations. Original Task 05B/05C records and all five mappings preserved. No activation, Task 06, staging, commit, merge or deployment. Checks: 305 tests passed; Ruff check/format passed (112 files); source/script type checking passed; all 19 preserved source/data hashes match. Live cloud UI verified all five selections (seven charts each), all three error scopes and Run Event Models reuse (3 reused / 0 trained each); versions unchanged and no activation. Temporary verification server stopped. Detailed evidence and limitations are in the full report.

---

Previous handoff retained for context:

# Current handoff — Task 05C cloud completion

Date: 2026-11-18. Branch: `codex/task05c-database-persistence`.
**Dedicated Turso/R2 migration, automatic model persistence and cold-cache reuse verified.**
No Task 06 work, staging or commits. Previous-MVP resources remain untouched.

## Completed cloud deployment

- User-provided dedicated credentials loaded securely from `.env`; the agent did not change
  the secret file or print credential values. Cloud mode and dedicated SQL/bucket guards passed.
- `batteryflex-mvp` Turso SELECT and R2 bucket connection checks succeeded. SQL was empty initially.
- Migration 001 applied: 22 tables, matching schema checksum and no foreign-key violations.
- Bootstrapped five households, five original prepared assets (441,600 candidate observations),
  five NESO events/replay mappings, one five-battery default portfolio, forecast configuration
  and feature schema, and one verified existing evaluation archive. Both missing cells preserved.
- Zero production fitted model bundles existed to migrate. The authorised forecast run trained
  and automatically persisted Seasonal Naive, Ridge and LightGBM: three complete five-home
  bundles, 36 structured metric records and 24,480 evaluated prediction rows.
- All 15 registered R2 objects were read directly and matched SQL-pinned byte sizes/SHA-256 values.
- A second identical request used a fresh local cache with fitting, uploads and SQL mutations
  prohibited: all three methods reused, zero trained, identical outputs, unchanged versions/times.
- Repeated live bootstrap was idempotent and did not retrain or change model versions.
- All 19 preserved Task 03E source/data hashes match; all cloud metrics match Task 05B.

Portfolio test RMSE: Naive **1.159441 kW**, Ridge **0.977148 kW**, LightGBM **0.946907 kW**.
Validation portfolio RMSE recommends LightGBM (0.829418 kW). No cloud activation was changed:
all bundles/results are reusable already; Activate Model remains an explicit selection in A4.
Historical information-cutoff and missing-history restrictions are unchanged.

## Verification and report

- Full suite: **294 passed in 66.53 seconds**; Ruff lint/format and ty pass.
- Real cloud-backed localhost smoke restored five curves without Run Models, reported default
  2 reused/0 trained and all-method 3 reused/0 trained, changed the display day and restored results
  in a new session. Model timestamps/versions were unchanged. Tabs B/C remained non-executing.
  The temporary server stopped with no new warnings/tracebacks.
- [Full completion report](TASK05C_CLOUD_COMPLETION.md) records cloud row/object counts, first/second
  request evidence, metrics and limitations. Ignored evidence: `outputs/task05c/cloud-verification/`.
- [Storage architecture and operations](STORAGE.md). No cloud credential limitation remains for
  the verified database/bucket operations. No previous-MVP database or objects were modified.

Stop after Task 05C. Do not start Task 06/control/optimisation/simulation execution without its task.

---

# Historical Task 05C handoff (credential block resolved above)

# Current handoff — Task 05C persistence and automatic reuse

Date: 2026-11-18. Branch: `codex/task05c-database-persistence`.
**Implementation/local integration verified. Cloud provisioning and migration are pending
credential permissions, so Task 05C is not claimed fully deployed or cloud-complete.**
No staging/commits. Unrelated parent-project working-tree changes preserved.

## Resource status / required user setup

- Dedicated Turso `batteryflex-mvp`: existence unverified; only the previous MVP's database JWT
  was available, and its account API authentication returned HTTP 401. No usable platform token
  or organisation slug was found. The old database was never queried or modified.
- Dedicated R2 `batteryflex-mvp`: existence unverified; HEAD returned 403, list/create returned
  `AccessDenied`. No previous-MVP objects were changed.
- Original `.env` was inspected without displaying values and remains unchanged/ignored by Git.
  Existing R2 credentials are supported; no new accounts or OpenAI keys are required. No OpenAI
  calls were made. Cloud migration has not run, and no cloud durability is claimed.

To complete setup, supply either dedicated BatteryFlex SQL URL/token, or an existing Turso
platform token (database read/create/token-mint permissions) plus organisation slug. In Cloudflare,
create `batteryflex-mvp` and grant existing keys access to this bucket; use scoped overrides only
if those permissions cannot be extended. Exact variables, safe provisioning/verification/bootstrap
commands and manual alternatives are in [STORAGE.md](STORAGE.md). Keep credentials in `.env`,
not chat. Never substitute the previous MVP's database/bucket.

## Implemented

- Versioned relational metadata with FK/unique/check/index constraints; explicit migrations and
  startup schema checksum validation. Shared SQLite/Turso parameterized transaction interface.
- Dedicated-resource guards; content-addressed R2 artifacts with remote verification and a
  verified local cache. No executable pickle, implicit source downloads or startup migrations.
- Explicit idempotent bootstrap of reviewed data/configuration, legacy bundles and trustworthy
  evaluation archives. Missing estimators are reported rather than trained by bootstrap.
- Per-algorithm exact fingerprints, distributed owner/expiry leases, automatic missing-model
  training/persistence and atomic registry/metric/result publication. Corrupt/incomplete results
  cannot be successful cache hits; repeated requests reuse existing versions.
- A4 Run Models is load-or-train; no Save Model/version-entry control. Existing five household
  figures, interactive grouped RMSE and generated comparison remain. The exact current model
  recommendation uses validation portfolio RMSE. Explicit activation persists in SQL.
- Stored exact results restore on tab opening without fitting. Active models restore in new
  sessions and retain the historical information cutoff and missing-history restrictions.
- Portfolio confirmation creates immutable content-based versions; unchanged values reuse the
  same version. New sessions load the SQL active portfolio. Battery/event changes do not cause
  load-model retraining. Selected registered household subsets have independent complete bundles.
- Future simulation run/metric/artifact relational references are prepared. Existing immutable
  run/input contracts remain; no dispatch, MILP, MPC, tariffs or simulation execution is added.

## Local migration / measured verification

Only an isolated local verification database/object store was bootstrapped, under
`outputs/task05c/local-verification/`. The normal app's default production storage was not
silently replaced. It imported five households, five prepared assets, five NESO events/replay
mappings, default five-battery portfolio, three forecast configurations and one feature schema.
The Parquet copy retains 441,600 original candidate rows; the reviewed homes retain 4,416 rows
per home with the original two missing cells. Original source/artifact hashes and timestamps stay
unchanged. Prior browser-only battery edits have no durable file and were not invented as saved assets.

No pre-existing saved model bundles were present: **0 migrated**. Existing Task 05B metrics/counts/
predictions were verified against source actuals/recomputed metrics and archived without training;
unmatched evaluations are not registered as fitted-model cache hits.

An explicitly requested local verification forecasting run then persisted three new method bundles
and 36 metric records. Its second request reused all three with fitting disabled. Per-household
and portfolio metrics match Task 05B. Portfolio test RMSE: Naive 1.159441 kW, Ridge 0.977148 kW,
LightGBM 0.946907 kW. These are forecasting results, not dispatch performance.

The localhost smoke restored five cached curves on opening A4, then reported 2 reused/0 trained
(default algorithms) and 3 reused/0 trained (with Ridge). It changed the display day, explicitly
activated the recommended model in the isolated store, restored activation in a new session and
confirmed unchanged model versions/timestamps. Tabs B/C remained non-executing. The temporary server
stopped without new warnings/tracebacks. This verification store's active model is LightGBM;
there is no active cloud model.

## Changed files / dependencies

- `src/batteryflex/storage/`: SQL adapter/migrations, objects, repository/settings, bootstrap,
  legacy import, database-backed registry, forecast cache and explicit provisioning helpers.
- `scripts/storage_admin.py`, `scripts/provision_storage.py`: explicit owner operations.
- `forecast_training.py`, `forecast_persistence.py`: preserve numerical algorithms while allowing
  complete bundles/aggregation for explicitly selected registered households.
- `ui/app.py`, `ui/explorer.py`, `ui/lcl_lab.py`, `ui/neso_events.py`, `ui/portfolio.py`,
  `ui/forecasting.py`, `ui/forecast_results.py`: database-first reads, immutable portfolio save,
  automatic model/results persistence and restore. Original validated NESO reader is unchanged.
- `tests/conftest.py`, `tests/test_storage.py`, `tests/test_forecast_ui.py`,
  `tests/test_portfolio_ui.py`: isolated credentials/state and storage/UI acceptance coverage.
- `pyproject.toml`, `.env.example`, README/config documentation and current architecture reports.
- Added boto3 >=1.35,<2 and python-dotenv >=1,<2 (verified installed 1.44.5 / 1.2.4).

## Verification / limits

- Full suite: **294 passed in 63.97 seconds**. Includes existing Tasks 01–05B regressions and
  bootstrap idempotency, no-refit reuse, household/source/config dependency changes, portfolio
  confirmation/versioning, corruption, upload/SQL failure rollback, concurrent claims, legacy
  imports, information cutoffs, provisioning guards and secret-preserving `.env` updates in fixtures.
- Ruff lint and format checks, plus ty (`src app.py`), pass.
- Actual measured-data local benchmark/reuse and real localhost smoke pass. Cloud transports use
  mocks in routine tests; successful live dedicated-resource integration remains unverified.
- All 19 preserved Task 03E source/data hashes match; `.env` and outputs are ignored by Git.
- Public UI continues the five reviewed households. Additional households/datasets require explicit
  validated registration; new feature/algorithm/manifest versions require implementation/review.
- Ten-minute model leases are suitable for current short fits; orphaned uploaded objects need a
  future reviewed retention policy. Local/ephemeral hosting is not a substitute for cloud durability.

Next action is dedicated-resource access, safe verify/bootstrap, then a real cloud reuse check.
Stop after Task 05C scope; do not start control/optimisation/simulation execution.

---

# Historical Task 05B handoffs (superseded where noted above)

# Current handoff — Task 05B final A4 UI refinement

Date: 2026-11-18. Complete; stop for review. Branch: `codex/task05b-household-forecasting`.
No staging or commits. Existing unrelated parent working-tree changes preserved.

## Final A4 layout

1. Run Models and common held-out test-day selector.
2. Exactly five main household actual-versus-predicted curves, one common midnight GMT
   origin/date and all 48 half-hours. Baseline is always shown, LightGBM/Ridge when evaluated.
3. One interactive Vega-Lite grouped RMSE bar chart: household x-axis, full-test RMSE kW y-axis,
   adjacent algorithm bars, legend and household/algorithm/RMSE-kW hover details (four decimals).
4. One automatic comparison paragraph grouping household wins and identifying portfolio winner.
5. Validation-based recommendation, algorithm/version selection, Save Model, saved-version
   selection, Activate Model and active-model information.

No A4 accuracy, daily-metric, configuration, counts, improvement or registry tables. The main
portfolio prediction curve is removed; aggregate metrics remain unchanged internally. A3 keeps
training/validation/test date configuration and missing-data information.

## Selection and persistence

Comparison derives from actual full-test RMSE; no algorithm is assumed to win. Methods share
valid dates within each household. Ties use relative tolerance 1e-9 / absolute 1e-12, count for
all tied algorithms and are stated explicitly. Missing, invalid or incomparable result sets
are marked unavailable. Conclusions apply to the evaluated periods, not universal superiority.

Default save algorithm is the lowest available validation portfolio RMSE, never a test winner.
Validation ties are stated; recorded run order breaks the default tie. User overrides persist
across date changes. New successful Run Models resets the default to the current recommendation.
The plots show the recorded run; changed A2 settings require Run Models and show a stale notice.
Changing the day filters stored predictions only; full-test bars and fitted models are unchanged.

Save/activation still require explicit buttons, one whole five-home method per immutable version.
No mixing algorithms across homes, automatic saving or activation. Trusted artifacts, complete
metrics/metadata, registry, source hashes and information cutoffs are unchanged. No production
model was saved/activated for this refinement. Three Simulation Lab tabs are preserved;
Tabs B/C and simulation execution remain unchanged and disabled as appropriate.

## Files changed for this refinement

- `src/batteryflex/ui/forecast_results.py`: simplified A4 rendering and validation-based default.
- `src/batteryflex/ui/forecast_comparison.py` (new): chart specification/data, winners/recommendation.
- `tests/test_forecast_ui.py`: same-day 48-step curves, table absence, validation default,
  manual override, no retraining/date-independent RMSE, preserved Save/Activate acceptance.
- `tests/test_forecast_comparison.py` (new): RMSE values/hover units/grouping, optional Ridge,
  calculated winners, counts, ties, unavailable/incomparable scores and validation-only choice.
- `README.md`, `docs/FORECASTING_MODELS.md`, `docs/UI_ARCHITECTURE.md`, this handoff.

No dependencies added. No forecasting mathematics, source pipeline, artifact or registry changes.

## Verification

- Full suite: **276 passed in 29.93 seconds**; focused UI/comparison suite: 12 passed.
- Ruff lint, Ruff format check (84 files) and ty (`src app.py`) pass.
- Real localhost smoke: actual LCL default training, optional Ridge training, five curves,
  grouped RMSE chart, validation-based save default, second display date and both remaining tabs.
  No new warnings/tracebacks; temporary server stopped. One initial smoke-script count assertion
  was corrected because the agent API reports line_chart separately from vega_lite_chart;
  the corrected smoke completed successfully.
- All **19/19** preserved Task 03E source/data SHA-256 references still match.
- Training/persistence numerical regression tests and explicit Save/Activate UI tests pass.

Stop after this UI refinement. No Turso, dispatch, optimisation, MILP, MPC or full simulation.

---

# Historical Task 05B handoff (UI sections superseded above)

# Current handoff — Task 05B

Date: 2026-11-18. Status: real multi-model forecasting complete; stop for review.
Branch: `codex/task05b-household-forecasting`. No staging or commits; unrelated parent work preserved.

## Delivered

Seasonal Naive reference, StandardScaler + Ridge (alpha 1), household-specific LightGBM
(200 trees / .05 rate / 15 leaves, seed 42). Eleven origin-safe calendar/day/week features;
midnight GMT, 48 half-hours, nonnegative clipping, complete seven-day history and target windows.
Existing audit-verified LCL pipeline and five households unchanged; no source reprocessing.

A2 supports algorithm checkboxes, defaults Naive + LightGBM. A4 explicitly runs all selected
models, reports usable counts, separate validation/test metrics and baseline improvements,
shows five same-day household charts plus complete-member portfolio chart, and supports
explicit Save Model then Activate Model. Visible A5 removed. Training has no durable side effects.
Saved five-household bundles use numeric JSON/native LightGBM text, no pickle. Read-back verification,
immutable versions, exclusive writer locking, corruption/schema/completeness checks and provenance
are implemented. Registry metadata retains all evaluation metrics, features, counts, effective
settings and versions. Inference loads once with `SavedForecaster` and never retrains.

## Actual measured-data benchmark

Default chronological split: Jan 1–Feb 28 / Mar 1–15 / Mar 16–31, 2013.
Usable train/validation/test origins: MAC001391 52/15/16; MAC003288 52/15/16;
MAC000143 52/15/16; MAC001534 52/8/15; MAC001395 44/15/16. Each origin has 48 targets.
Portfolio evaluation uses 8 validation and 15 test common complete days.

| Algorithm | Portfolio test MAE kW | RMSE kW | MAE improvement |
| --- | ---: | ---: | ---: |
| Seasonal Naive | 0.823539 | 1.159441 | 0% |
| Ridge Regression | 0.736022 | 0.977148 | 10.63% |
| LightGBM | 0.684537 | 0.946907 | 16.88% |

Per-home/validation scores, features, files changed, dependencies and detailed lifecycle are in
[FORECASTING_MODELS.md](FORECASTING_MODELS.md). Reproduce with
`.venv/Scripts/python.exe scripts/benchmark_forecasts.py`; ignored outputs are in `outputs/task05b/`.

## Storage and replay

No production bundle was saved or activated during implementation. Choose after inspecting results.
Explicit UI saves use ignored local `outputs/forecast_models`; local disks persist across restarts,
ephemeral hosting requires a durable volume. Registry JSON is separate from artifacts and active ref.
The source SHA-256 references the existing verified observations artifact, including retained dates;
it is not a newly created training-only dataset. Only trust artifacts written by the local owner.
A crashed exclusive writer may leave `.writer.lock`; inspect writer state before manually removing it.

Evaluated model cutoff is Apr 1 2013 00:00 GMT. Earlier replay origins are rejected. Isolated
Nov/Dec retained days cannot serve forecasts without prior seven-day history. April 1 may use
March history; no future observations are invented. Tab B displays active saved-model metadata and
reports incompatible replay origins; Run Simulation stays disabled. Tab C stays an empty foundation.
No dispatch, MILP, MPC, tariffs, settlement, simulation results, cloud infrastructure or Turso changes.

## Verification

- Full pytest: **271 passed in 28.49 seconds** (including all Tasks 01–05A regressions).
- Ruff lint and format check, and ty (`src app.py`) pass.
- Real localhost agent-API smoke: health/protocol, three-page navigation, Run Models using actual
  LCL data, both remaining tabs. No new server warnings/tracebacks; temporary server stopped.
- AppTest: checkbox/defaults, six forecast figures, train/save/activate, active model in Tab B,
  failure clears stale results, missing/corrupt data states, and prior UI regressions.
- Numerical tests: all algorithms, future-value perturbation, warm-up/missing/boundaries, 48-step
  completeness, metrics/improvements, aggregation, safe round trips, immutable versions, cutoff,
  incompatible/missing artifacts, inference without fit, failed writes and missing origin history.
- All 19 preserved Task 03E source/data SHA-256 values match; prepared audit independently verified.

Stop after Task 05B. Next work requires review; do not start control or simulation execution.

---

# Historical handoff records (superseded by Task 05B above)

# Current handoff — Task 05A

Date: 2026-11-17. Status: forecasting foundation and Simulation Lab restructuring complete;
stopped for review before Task 05B. Branch: codex/task05a-forecast-foundation. No staging/commits.
No model training, predictions, dispatch or fake results. Unrelated parent work preserved.

## Verified household data

The same five LCL IDs remain. Every household has 4,416 retained half-hours over 92 dates:
Jan 1–Mar 31 plus isolated Nov 7/Dec 6, 2013. Earliest interval start Jan 1 00:00 GMT;
latest interval end Dec 7 00:00 GMT. This is not continuous annual coverage.

| Household | Valid / retained | Missing | Complete retained days | Jan–Mar valid / expected |
| --- | ---: | ---: | ---: | ---: |
| MAC001391 | 4416 / 4416 | 0 | 92 | 4320 / 4320 |
| MAC003288 | 4416 / 4416 | 0 | 92 | 4320 / 4320 |
| MAC000143 | 4416 / 4416 | 0 | 92 | 4320 / 4320 |
| MAC001534 | 4415 / 4416 | 1 | 91 | 4319 / 4320 |
| MAC001395 | 4415 / 4416 | 1 | 91 | 4319 / 4320 |

Missing source interval ENDs: MAC001534 Mar 9 21:30 GMT; MAC001395 Jan 10 22:30 GMT.
Longest valid runs are 4,320 half-hours for the first three, 3,258 for MAC001534 and 3,843
for MAC001395. Additional prepared replay days are valid for all five. The audited annual raw
archive exists but was not expanded into a new forecast-ready series or reprocessed here.

Chronological default split: Jan 1–Feb 28 training (2,832 expected rows/home), Mar 1–15
validation (720), Mar 16–31 test (768). MAC001395 has one missing training cell; MAC001534
one missing validation cell; all test cells valid. Calendar coverage supports these proposed
boundaries, with gaps explicit. These are observation counts, not origin/example counts.
No imputation. Future warm-up and incomplete origin/48-step target exclusions remain required.

## Current UI

Exactly three main pages remain. Portfolio Configuration/battery physics/save/restore/status
text are preserved. Data Explorer still shows validated NESO events and original LCL readings.
LCL now distinguishes Full Study-Period Summary (all retained dates, not only Jan–Mar) from
Selected Observation-Range Summary, updated with selected dates. Original END/GMT/kWh, derived
average kW and quality remain in the detailed readings. Mean/peak/energy use valid observations;
unretained calendar slots are explicit and never silently treated as zero.

Simulation Lab has exactly three lazy tabs:

1. Forecast Model Development: A1 history (five households + aggregate, inspection dates,
   kW/kWh selector, measured curve, summary/details/coverage); A2 method/mathematics and editable
   hyperparameters; A3 chronological split/counts/gaps and Not trained; A4 No trained forecast
   available; A5 empty actual-record registry and future lifecycle workflow.
2. Run Simulation & Results: NESO event, local kW proposal, saved battery snapshot, active-model
   information and unavailable Rule-based/MILP/Rolling MPC strategy choice. Explicit original
   NESO date, synthetic 2013 replay date and midnight GMT forecast origin. Future Run once ->
   automatic forecasts/feasibility/control/simulation/evaluation/save -> results directly below.
   Run remains disabled; no standalone Results or redundant Experiment Setup tab.
3. Comparison & Evaluation: honest empty state, compatible-input requirements and planned
   metrics; Clear remains disabled. No made-up run tables, curves or comparisons.

Target is 30-minute average household power kW = original interval energy kWh / 0.5 h = 2E;
not instantaneous power. Fixed GMT interval START/END semantics remain unchanged. Aggregate
history requires all five aligned valid members. Inspection dates never mutate training dates.

## Forecasting and storage interfaces

New pure modules: forecast_data.py, forecast_contracts.py, forecast_registry.py and
forecast_simulation.py; UI development components in ui/forecasting.py. Full inventory/API details
are in [FORECASTING_FOUNDATION.md](FORECASTING_FOUNDATION.md) and DATA_CONTRACTS.md.

Methods: Seasonal Naive baseline, Ridge linear/L2 benchmark and LightGBM nonlinear tree ensemble.
All have 48-step/24-hour horizon and average-kW output. Planned origin-safe household/calendar,
48/336-step lag and rolling features are declared, not constructed/trained. Editable hyperparameters
are configured values, not fitted parameters. No ML packages were installed/imported.

Typed frozen contracts cover source observations, dataset/model configuration, metrics/metadata,
active reference, forecast request/output/batch validation and future one-click simulation inputs.
SimulationPlan captures replay/origin, saved assets, commitment, model version, demand/tariff/
baseline assumptions and actual source hashes for comparison compatibility. Existing immutable
run IDs/grouping remain unchanged; strategy may differ within equivalent full input snapshots.

Registry schema-v1 JSON is separate from versioned artifact files under ignored
outputs/forecast_models/. Reads create no files/directories. Explicit local-owner methods support
atomic metadata writes and active-reference selection; public UI exposes neither mutation path.
No production model records, registry files, artifacts or active model were created. Artifact paths
are confined; no artifact deserialisation occurs. Missing/bad/incompatible records are not fabricated.

Saved/evaluated model admission requires its information cutoff <= replay forecast origin,
compatible households and horizon. Cutoff conservatively includes recorded evaluation/selection.
A model using later Jan–Mar data cannot be represented as a historically valid earlier forecast.
NESO 2023–2026 dates never overwrite LCL 2013 observations. Isolated Nov/Dec replay days lack
preceding lag/week context in the current prepared subset, so future feature admission must fail
or use explicitly reviewed additional retention/model policy; no silent future-data leakage.

## Validation and next step

- 262 tests pass, including existing Tasks 01–04/NESO/LCL/physics/persistence/UI regressions.
- Ruff lint/format and ty check src app.py pass.
- New tests cover conversion, GMT/date alignment, ranges/summaries, missing/duplicate/categorical
  handling, aggregation/coverage, chronological splits, forecast/model metadata, registry lifecycle,
  active/missing artifacts, owner writes/path safety, replay cutoff admission, forecast batch
  validation, changed experiment metadata and UI/configuration/empty-state separation.
- Real localhost health/agent-API checks passed: three pages/tabs; six real historical series;
  actual split counts/known aggregate gap; inspection/training independence; all model choices;
  five replay contexts; saved assets; disabled execution/empty comparison; unchanged NESO/LCL routes.
  No new server warnings/tracebacks. Production registry directory/file was not created.
- All 19 source/data SHA-256 hashes match the preserved Task 03E baseline. No acquisition,
  re-preparation, source validation or replay change. Temporary server stopped after checks.
- Agent-API smoke completed; browser visual QA was not performed. Ignored evidence outputs/task05a-*.
  Streamlit tests/localhost access used approved escalated execution; no external service writes.

Launch from the BatteryFlex repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Task 05B still needs real origin-safe feature/examples, fitting/evaluation, actual metrics,
trusted artifact formats/loading, model versions/activation and complete forecast output validation.
Historical model selection/cutoffs and missing replay lookback context must be resolved explicitly.
No Task 05B, rule-based dispatch, MILP, MPC or full simulation execution started. Stop for review.

---

# Historical handoffs

> Task 04 final text refinement (17 November 2026): only commitment-check status copy was
> refined in ui/portfolio.py. One titled warning now reports dynamic capability, kW/kWh
> shortfalls and coverage; sufficient scenarios use the requested success copy. Zero commitments
> are safe and surplus capability is not displayed as delivery percentage. Existing equations,
> table, physics/configuration/persistence and other UI sections are preserved. UI regressions
> updated: 226 tests pass; Ruff lint/format, ty and localhost insufficient/feasible/zero checks
> pass. No Task 05 work. This note supersedes earlier status wording below.

# Current handoff — Task 04C

Date: 2026-11-17. Status: final battery models, charge/discharge performance and explainable
commitment check complete; stopped for review. Branch: codex/task04c-battery-performance.
No staging/commits; unrelated parent work preserved. Task 05 has not begun.

## Current product

The app still has exactly Data Explorer, Portfolio Configuration and Simulation Lab. NESO/LCL
observations, validated event choices, household selection and historical replay are unchanged.
Portfolio Configuration has these four final sections:

A. Battery Configuration: one editable five-household table, Save Configuration and Restore
Defaults. Header tooltips define SOC, efficiency, participation and export permission. Round-trip
efficiency is read-only eta_charge*eta_discharge. Net export cap explains permitted NET grid export
with the 3.68 kW cap / 5 kW discharge example; blank means no additional cap. Global interval 0.5 h.

B. Battery and Household Power Models: separate Battery Energy/SOC Model and Household Grid Power
Balance subsections. LaTeX matches the unchanged discrete-time energy model, SOC/power bounds,
mutual charge/discharge exclusion and positive-import/negative-export grid balance. Text distinguishes
energy scheduling from RC voltage/transient models, with no manufacturer BMS or measured validation
claim. Future optimisation may combine these separate equations.

C. Battery Charge/Discharge Performance: only household, Charge/Discharge and positive Operating
Power controls. Power defaults to the corresponding selected battery/mode rating, can be reduced,
and cannot exceed that rating. Completion time to SOC_max/min is calculated automatically. Strict
Task 04 transitions use normal 0.5 h steps plus the exact shorter final interval. No duration/Idle/
Requested Power control or power clipping. One SOC chart includes time zero and final boundary;
five metrics show initial/final SOC, power, total time and AC electrical energy. Initial boundary
means zero time/energy. Demand/export restrictions are excluded explicitly; saved SOC is unchanged.

D. Battery Availability & Commitment Check: one event/local kW proposal, working-participation-based
scenario checkboxes and one Quantity/Value/Unit/Explanation results table. Table adds required
commitment energy and any kW/kWh shortfall. Actual power-sum, margin, required-energy and shortfall
equations plus per-battery constraint diagnosis explain energy, power and combined limitations.
No contribution/all-events table. Aggregate energy alone never determines cause/sufficiency.
Status is Preliminary battery capability sufficient or Insufficient battery capability.

Scenario checkboxes initialize from working participation. A changed working participation field
rebases only that household; unrelated edits preserve scenario overrides. Check-specific choices
never write to table or saved active assets. Save validates/activates session settings and offers
matching JSON download; Restore Defaults changes only working settings until saved. Durable storage
still means retaining browser-owned JSON, not shared server persistence. Simulation Lab continues
to read saved assets only, with Run/Clear disabled and no artificial outputs.

## Examples

Default MAC001391 at 5 kW: 80% to 100% takes 0.421637 h and draws 2.108185 electrical kWh;
80% to 20% takes 1.138420 h and delivers 5.692100 kWh, using 0.5/0.5/0.138420 h intervals.

Default all-five 10 kW commitment passes a one-hour event (22.589466 kW available; +12.589466 kW
margin). The three-hour event has 8.380036 kW available, a 1.619964 kW shortfall / 4.859893 kWh.
At one hour, even a 24 kW request fails despite 25.140107 kWh deliverable energy and 25 kW aggregate
rating: individual mixed energy/power limits reduce sustainable capability to 22.589466 kW.

## Validation

- 225 tests pass, including existing NESO/LCL, physics, aggregation, persistence, save/restore,
  working/saved/scenario isolation and navigation tests.
- Ruff lint/format and ty check src app.py pass.
- New tests cover exact tooltip definitions, model separation, charge/discharge curves, automatic
  time, shorter final intervals, zero-time cases, operating-power validation, no initial-SOC
  mutation, current working participation defaults, one results table, equations, required/
  shortfall energy and individual energy/power/combined explanations.
- Fresh-runtime localhost health/agent API passed: final sections/tooltips, exact default and
  reduced-power times, positive-power validation, five events/durations, one explained table,
  energy/combined warnings, scenario isolation, save/download, defaults and NESO/LCL/navigation.
- An initial duplicate widget-default warning was fixed and checks repeated on a fresh process;
  no new warnings/tracebacks remained. Temporary server stopped after verification.
- Grid edits are action_unsupported in the agent API; AppTest drives actual editor state for
  working edits/defaults/zero-time/save tests. Browser visual QA was not performed.
- All 19 source/data SHA-256 hashes match the preserved Task 03E baseline. No acquisition,
  preparation, source validation or replay changes. Strict battery.py remains unchanged.
- Streamlit tests/localhost requests used approved escalated execution; no external service writes.
  Ignored evidence: outputs/task04c-*.

## Files, limits and next step

See [BATTERY_PERFORMANCE.md](BATTERY_PERFORMANCE.md) for all changed files, current UI guide,
mathematical assumptions, examples, test evidence and limits. README, DEVELOPMENT_PLAN and
DATA_CONTRACTS are updated; older Task 04B UI/demo documentation is marked superseded.

Launch from the BatteryFlex repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Performance is constant-efficiency battery-only physics, not RC/BMS validation or household-grid
operation. Extreme curves exceeding 100,000 half-hour steps fail explicitly without artificial
time rounding/truncation. The capability check assumes constant discharge, no recharge and no
additional grid-side restrictions; it does not confirm official baseline-relative NESO delivery.
Actual demand, export limits, baseline and dispatch optimisation remain future work. No forecasting,
MILP, MPC, full event dispatch, settlement, real battery communications or live NESO integration.
Stop after Task 04C and wait for review; do not begin Task 05.

---

# Historical handoffs

# Current handoff — Task 04B

Date: 2026-11-17. Status: simplified portfolio configuration and battery demonstration complete;
stopped for review. Branch: codex/task04b-portfolio-demo. No staging/commits. Task 05 has not begun.

## Current product

The three-page navigation and Data Explorer are unchanged. Portfolio Configuration now has
exactly four sections in order: A. Battery Configuration; B. Battery Mathematical Model;
C. Battery Charge/Discharge Demonstration; D. Battery Availability & Commitment Check.

One editable table keeps all five reviewed households visible. Editable values are capacity,
charge/discharge power, initial/min/max SOC, separate charge/discharge efficiencies, export
permission, optional nullable net export cap and participation. Household ID and calculated
round-trip efficiency are read-only. Percentages convert to model fractions; the global
simulation interval is fixed/displayed at 30 minutes, without a per-row interval column.
Invalid rows identify household/parameter and block saving/model outputs without SOC repair.

The only configuration actions are Save Configuration and Restore Defaults. Save validates
all five rows, activates the session portfolio and offers matching schema-v1 JSON download.
Success explicitly distinguishes session activation from durable storage: users must retain
the downloaded file. No shared file/database/startup writes. Restore Defaults updates only
the working table; Save is required to replace saved active settings. Separate Load/Apply-All
controls and redundant summary/capability tables are removed from the UI; core APIs remain.
The fixed-row editor preserves accumulated edits across reruns/page switches and refreshes
calculated efficiency. Minimum Streamlit is now 1.67, matching this installed/tested behavior.

The demonstration uses valid working table values (including unsaved edits), one household,
Charge/Discharge/Idle, requested kW and half-hour duration controls. The actual Task 04 strict
state transition runs every 0.5 h, with explicit feasible-power reduction only in the demo
adapter. Results record actual power, SOC, energy, curtailed power and reasons. One SOC chart
includes time zero; concise metrics/warnings show actual AC energy and reached limits. Demand
and grid/export restrictions are explicitly excluded, and configured/saved initial SOC never
changes. This is a standalone battery physics demonstration, not NESO event dispatch.

The commitment check uses valid working parameters and five independent scenario participation
checkboxes (initially all checked). These do not overwrite table or saved participation. It
shows one event's duration/count/usable/deliverable energy/capability/commitment/margin and
preliminary pass/shortfall. No contribution/all-events tables or duplicated event detail view.
Actual baseline-relative flexibility, household demand, export restrictions and time-varying
dispatch remain deferred. National MW is context only, with no local commitment scaling.

Simulation Lab reads only the saved active battery portfolio. Unsaved table edits, temporary
demonstration inputs and scenario participation do not alter that snapshot. Existing event/
commitment planning inputs remain explicit. Simulation Run/Clear remain disabled; no fake results.

## Validation

- 216 tests pass, including original NESO/LCL and Task 04 physics/capability/persistence regressions.
- Ruff lint/format and ty check src app.py pass.
- New analytical/UI tests cover all fields, efficiency/percentage conversion, SOC curves/losses,
  rating/SOC bounds, partial feasible power/curtailment, charge/discharge/idle, no SOC mutation,
  validation, save/restore, saved/working isolation, reruns/page retention, concurrent edit/save,
  scenario selection, aggregation, shortfalls and saved Simulation Lab snapshots.
- Real localhost Streamlit health/agent API passed: exact four sections, one five-row/13-column
  editor, equations/chart, charge/discharge/idle and limits, save confirmation plus actual JSON
  download, all five events, scenario participation, defaults, simulation and NESO/LCL navigation.
- Grid editing is action_unsupported in the agent API; AppTest drives data-editor state for
  real edit/save behavior. Browser visual QA was not performed. No new server warnings/tracebacks.
- All 19 source/data SHA-256 hashes match the Task 03E baseline. No measured-data/source-validation/
  historical-replay changes. Pure strict battery physics modules are unchanged.
- Streamlit tests/localhost requests used approved escalated execution; no external service writes.
  Temporary server stopped after verification. Ignored evidence: outputs/task04b-*.

## Files, review and limitations

See [PORTFOLIO_CONFIGURATION.md](PORTFOLIO_CONFIGURATION.md) for the full changed-file inventory,
UI guide, state/save semantics, demonstration equations, examples, tests and limitations.
README, DEVELOPMENT_PLAN and DATA_CONTRACTS describe the current behavior. Task 04's model
report is retained with a Task 04B supersession note for UI/state semantics.

Launch from the BatteryFlex repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Session state is not durable storage; retain downloaded JSON beyond session expiry. No primary
upload/load control remains. The demo has a 24-hour UI bound and feasible half-hour average
power near SOC limits. It is battery-only, as is the commitment check. No forecasting, MILP,
MPC, full event dispatch, official baseline/settlement, real battery IO or live NESO integration.
Stop after Task 04B and wait for review; do not begin Task 05.

---

# Historical handoffs

# Current handoff — Task 04

Date: 2026-11-17. Status: battery physics, five-household configuration and preliminary
battery-only commitment check complete; stopped for review before Task 05 forecasting.
Branch: codex/task04-battery-portfolio. No staging/commits; unrelated parent work preserved.

## Current product

Exactly three pages remain. Data Explorer and its validated NESO/LCL observations/replay are
unchanged. Portfolio Configuration now edits five simulated research batteries, independently
configurable capacity/powers/SOC/efficiencies/interval/export/participation. All default to
10 kWh, 5 kW charge/discharge, 20–100% SOC, 90% round-trip efficiency, 30-minute intervals,
export permitted and no additional cap. Initial SOC is 80/65/90/55/75% in the reviewed ID order.
No historical battery installation or measured SOC claim is made.

Pure typed modules implement physical state transitions, energy conservation/losses, power/SOC
bounds, simultaneous-action rejection, grid import/export and optional net export limits.
Requests fail explicitly; SOC is never raised to meet a commitment. Portfolio aggregation
includes only participating batteries. Installed capacity includes all configured batteries.

Battery Availability & Commitment Check uses the five reviewed event durations and a separate
local kW proposal, showing margin, pass/shortfall and household maximum contributions. Default
usable energy is 26.5 kWh, deliverable energy 25.140107 kWh, and 1/1.5/2/3-hour sustainable
power is 22.589466/16.760072/12.570054/8.380036 kW. A 10 kW commitment passes the first four
events and fails the three-hour event by 1.619964 kW. This is battery-only preliminary capability,
not actual baseline-relative NESO delivery. Export restrictions show an explicit load-needed
warning and remain enforced in state transitions with supplied household load.

Apply-to-all preserves individual initial SOC and participation unless explicitly copied;
invalid preserved states reject the common update atomically. Restore Defaults reinstates
all five battery defaults. Validated JSON save/download and load/upload provide browser-owned
durable settings without shared server-file writes. Session edits alone are not durable.
Simulation Lab reads the current valid portfolio, event/commitment and immutable input snapshot;
its execution/results/clear placeholders remain disabled. No simulation runs or fake outputs.

## Validation

- 178 tests pass, including all existing NESO/LCL tests and 68 additional model/portfolio/UI tests.
- Ruff lint and format pass; ty check src app.py passes.
- Real localhost Streamlit health and agent API ready; all three pages, five event checks,
  sufficient/insufficient commitments, low/invalid SOC, participation, apply-all/defaults,
  export warning and page-switch retention passed. No new server warnings/tracebacks.
- All 19 source/data hashes match the preserved Task 03E baseline. No raw/prepared data,
  NESO source validation or historical replay mappings changed.
- Streamlit tests and localhost checks required approved escalated execution because the
  sandbox stalled imports or denied sockets. No external service/database mutation.
- Agent-API smoke checks completed; browser visual QA was not performed. Temporary server
  stopped after verification. Ignored evidence: outputs/task04-*.

## Review and next task

See [BATTERY_MODEL.md](BATTERY_MODEL.md) for all changed files, architecture, mathematical
constraints, household defaults, event capability table, persistence, test evidence and limits.
README and DATA_CONTRACTS document the implemented API/JSON/snapshot contracts. The development
plan clarifies that the explicit user Task 04/05 sequence supersedes older table numbering.

Launch locally from the BatteryFlex repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Stop for Task 04 review. Task 05 forecasting, optimisation, dispatch, official delivery/baseline
calculations and durable run storage have not begun. Current interfaces are ready to receive
future demand/forecast/source-reference inputs after approval.

---

# Historical handoffs

# Current handoff — Task 03E

Date: 2026-11-17. Status: final three-page UI and future retained-run contracts complete;
stopped for review before Task 04. Branch: codex/task03-lcl-data-lab. No commits or staging.

## Current product

Exactly three Streamlit pages: Data Explorer (default /), Portfolio Configuration (/portfolio),
Simulation Lab (/simulation). Banner: BatteryFlex — Automated VPP Flexibility Optimisation &
Control. Historical simulation/research MVP for flexibility aggregators; explanatory workflow
NESO Request → Forecast → Feasibility → Optimisation → Simulated Dispatch → Evaluation.
No separate Operations Dashboard, Results & Evaluation or individual modelling pages.

Data Explorer has two native lazy tabs: NESO Flexibility Events and Low Carbon London.
NESO starts unselected with five validated Live events. Shows date/window/duration/national
MW/interval count and half-hour requirements plus energy equivalent MWh = sum(MW × hours).
Five totals in reviewed order: 300, 200, 825, 1000, 1500 MWh. No large requirement plot or
technical panels. Source provenance/validation/row hashes remain preserved internally.
National MW/MWh is explicitly distinct from household demand/portfolio commitment kW.

LCL starts unselected with the same recommended five: MAC001391, MAC003288, MAC000143,
MAC001534, MAC001395. London study area, original IDs, source versus retained observation dates,
Jan–Mar summary statistics, date selector, one dated demand line and chronological original
readings. Separate five-house comparison has one typical-profile line chart plus summary.
Original fixed-GMT interval-END/kWh semantics remain; average kW = kWh / 0.5. Missing values
stay missing and chart lines break at gaps. No invented address or complete-annual-profile claim.

Portfolio Configuration is planned pending Task 04: future five-battery capacity, charge/
discharge power, initial/min/max SOC, efficiency, export permission and optional export limit.
Export-enabled is the intended default; no actual batteries or numerical assumptions exist.

Simulation Lab integrates Experiment Setup, Run Simulation, Results, Comparison & Evaluation.
Event/strategy/export planning controls, configuration/commitment explicitly unconfigured.
Rule-based, MILP and Rolling MPC are future strategy choices. Engine-not-implemented message;
Run Simulation and Clear Results disabled. Future results/metrics described without fabricated
values, tables, dispatch, progress or success claims. No models or evaluation logic executed.

## Future persistence contract only

simulation_contracts.py defines frozen ExperimentInputs, EvaluationMetrics and SimulationRun.
Full canonical input snapshots include internal event ID, battery configuration, initial SOC,
export settings, explicit commitment kW, forecast assumptions and source/data references.
Equivalent full inputs produce an experiment fingerprint; strategy is excluded. Any changed
experimental input creates a separate group. Immutable canonical JSON neutralises key order.

Each future successful run gets a new UUID even for repeat strategies. append_run rejects
ID collisions and never upserts by strategy. compatible_runs filters identical fingerprints;
clear_experiment removes only a selected experiment, preserving others. Pure helpers are tested,
not used to create production example runs. No durable storage adapter, database/session run
store or restart persistence is claimed. Later storage must enforce unique IDs, atomic input/
result/metric snapshots, append-only insertion and explicitly scoped deletion.

Metrics contract: fulfilment %, shortfall kWh, cost £, throughput kWh, final SOC per home %, runtime s.
See UI_ARCHITECTURE.md and DATA_CONTRACTS.md for required result payloads and future admission.

## Validation

- python -m pytest -q: 110 passed.
- python -m ruff check .: passed.
- python -m ruff format --check .: passed (53 files).
- .venv/Scripts/ty.exe check src app.py: passed.
- Production tests cover exact page titles/default landing/two tabs, five event selections,
  unchanged interval MW plus MWh, no NESO plot, five public household choices, dependent
  readings/conversion/endpoints, one dated chart and one comparison chart, missing-data state,
  planned export defaults, unavailable simulation and disabled run/clear with no fake outputs.
- Contract tests cover UUIDs/repeated strategies/no overwrite, key-order equivalence/immutable
  snapshots, all seven input changes making runs incompatible, three strategies sharing an
  experiment, and clear preserving other experiments. No model computations in fixtures.
- Existing pure source/validation tests remain unchanged. Prior advanced/LCL component UI
  regressions are retained through tests/fixtures/research_explorer.py rather than exposing
  those old controls in public navigation. test_research_components.py retains the five old
  advanced acquisition/filter/review tests; current public UI tests are in test_app.py and
  updated test_neso_public_view.py / test_lcl_ui.py. No source functionality was removed.
- Real localhost health ok, documented agent API ready. Snapshot reports exactly three pages
  with Data Explorer selected by default. All five events (2/2/3/4/6 rows), five household
  selections, one-chart comparison, both tabs and both planned routes passed smoke checks.
  Run/Clear disabled; no simulation metrics/charts. No new server warnings/tracebacks observed.
- SHA-256 baseline: 19 raw/prepared/LCL/NESO source/data files unchanged. No acquisition,
  reprocessing, household reselection, replay change or NESO data/validation change.
- Evidence ignored: outputs/task03e-preserved-hashes.json, task03e-agent-schema.json,
  task03e-agent-latest.json. data/ and outputs/ remain ignored. Temporary server stopped.
- Browser visual QA was not repeated for Task 03E; actual Streamlit agent-API smoke completed.

## Files changed

New:
- src/batteryflex/ui/explorer.py
- src/batteryflex/ui/planned.py
- src/batteryflex/simulation_contracts.py
- tests/test_simulation_contracts.py
- tests/test_research_components.py
- tests/fixtures/research_explorer.py
- docs/UI_ARCHITECTURE.md

Updated:
- src/batteryflex/ui/app.py
- tests/test_app.py
- tests/test_neso_public_view.py
- tests/test_lcl_ui.py
- README.md
- docs/ARCHITECTURE.md
- docs/DATA_CONTRACTS.md
- docs/DEVELOPMENT_PLAN.md
- docs/LCL_UI_GUIDE.md (historical guide clearly marked superseded)
- docs/CURRENT_HANDOFF.md

## Review locally and stop

From the BatteryFlex repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Choose Data Explorer tabs; select a reviewed event/home or comparison. Sidebar Portfolio
Configuration and Simulation Lab show planned features only. Current navigation is documented
in README.md and UI_ARCHITECTURE.md. No acquisition needed for the existing local artifacts.

Partial household dates, anonymisation, calendar replay and feasibility limitations remain.
No Task 04, simulated batteries, SOC defaults, forecasting, feasibility, export constraints,
MILP/MPC, dispatch, cost/evaluation logic or fabricated outputs. Durable simulation persistence
is future work; only contracts/retention rules are implemented. Stop and wait for review.

Parent Git repository and batteryflex remain in their pre-existing untracked/dirty state;
unrelated work preserved, no staging/commits. This task supersedes the earlier five-page
proposal; it does not authorise starting the engine or storage tasks.

---

# Historical handoffs

# Current handoff — Task 03B

Date: 2026-11-17. Status: LCL UI finalisation complete; stopped for review before Task 04.
Branch: codex/task03-lcl-data-lab. No commits or staging. Existing parent Git state preserved.

## Result

Four progressively rendered views: Household Explorer (default), Five-Household Comparison,
NESO Event Replay, Data Quality & Provenance. Dataset overview explains full 2013 source
versus retained dates, 4,443/100/5 households, publisher, provenance, GMT and energy/power units.

Household Explorer initially shows an unselected searchable selector and concise five-house
summary. Separate all-100 candidate scope marks recommended IDs. Selecting a household shows
headline statistics and expandable information/metric definitions, unavailable anonymised
attributes, original end-label bounds, complete-day/missing counts and January–March metric
periods. Date selector controls chronological original readings and CSV export, zoom/hover
half-hour demand, complete-day energy with coverage strip, and selected-range typical profile.
No interpolation or missing-to-zero conversion. Incomplete and unretained dates are distinct.

Reviewed five unchanged: MAC001391, MAC003288, MAC000143, MAC001534, MAC001395.
Comparison shows the six-column quality/energy/power table, daily-energy/evening-power/
peak-power/completeness bars and typical daily profile overlay. Stable ID colours across
charts, combined replay demand grey/dashed; no statistical-representativeness claim.

NESO Event Replay — Five Households starts unselected with exactly five reviewed Live choices.
Shows original event date/window/duration/national MW/status/interval count, original 2013
LCL date and mapping explanation, both original interval pairs, per-house/combined kW table
and chart. All 17 intervals preserved (2/2/3/4/6). Optional national-MW chart is separate.
The five validated events, mapping and demand values remain unchanged synthetic historical replay.

Provenance has its own view with collapsed advanced source/audit diagnostics. Only existing
local prepared artifacts are read, hash-checked and cached by audit revision; no acquisition,
raw parsing, reprocessing, reselection, database, battery, SOC, export-constraint or model work.
Missing/corrupt local data has a clear message. Existing NESO UI and validation are unchanged.

## Launch and review

From the BatteryFlex repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Data Explorer → enable Low Carbon London Data Lab → Household Explorer → choose household.
Use the Household list control for all 100 candidates; use the section control for comparison,
NESO replay or provenance. The reviewed local data is already present; do not reacquire it.
See docs/LCL_UI_GUIDE.md for full navigation, statistics/aggregation periods and chart controls.

## Verification

- python -m pytest -q: 98 passed, including all existing NESO UI/validation tests.
- python -m ruff check .: passed.
- python -m ruff format --check .: passed, 45 files.
- .venv/Scripts/ty.exe check src scripts/prepare_lcl.py app.py: passed.
- Updated UI tests check unselected five-ID default, separate 100-ID scope, dependent
  household/date views, CSV control, comparison, all five event options and all 17 intervals,
  same IDs, distinct original date pairs, and offline missing/corrupt prepared-data states.
- Added display tests check original text/end-time/kWh→kW/CSV preservation, 48-valid-interval
  totals only, incomplete versus unretained days, missing values, typical-profile sample
  counts and chart line breaks. Existing source/conversion/selection tests preserved.
- Actual local app health ok; agent API ready for initial/selected households, all-100/date
  filter, statistics/day-quality details, comparison, all five replay tables, optional national
  MW chart and expanded provenance. Browser rendered default five choices, selected readings/
  charts, comparison profiles/bars and replay date pairs/combined chart. Native narrow-screen
  tables scroll horizontally. Temporary local app stopped.
- Browser logged transient Vega infinite-extent warnings during Arrow data hydration when
  changing views. Settled charts rendered correctly; no browser errors or server warnings/
  tracebacks observed. Details in LCL_UI_GUIDE.md; no data or value changes to suppress logs.
- Before/after SHA-256 comparison: all 20 preserved data/processing/NESO files unchanged,
  including all raw/prepared artifacts, LCL acquisition/parsing/selection/replay modules,
  preparation script, NESO modules and frozen event manifest. No acquisition/reprocessing.
- Ignored evidence: outputs/task03b-preserved-hashes.json, task03b-agent-*.json and browser
  task03b-household-selection.jpg, task03b-comparison.jpg, task03b-replay.jpg. Data/outputs ignored.

## Task 03B changed files

Updated:
- src/batteryflex/ui/lcl_lab.py
- tests/test_lcl_ui.py
- README.md
- docs/ARCHITECTURE.md
- docs/DEVELOPMENT_PLAN.md
- docs/LCL_DATA_LAB.md (historical Task 03 findings preserved; UI finalisation appended)
- docs/CURRENT_HANDOFF.md

New:
- src/batteryflex/ui/lcl_views.py (display-only summaries/tables/quality)
- src/batteryflex/ui/lcl_charts.py (interactive GMT charts and stable ID colours)
- tests/test_lcl_views.py
- docs/LCL_UI_GUIDE.md

## Remaining limitations and scope

Prepared observations cover Jan–Mar plus two replay dates, not all 365 days. Summary statistics
stay on Jan–Mar; explorer charts use the selected range. Anonymised IDs expose no address,
occupancy, property/appliance or installed-battery attributes. Five examples are illustrative,
event-screened and not representative of UK households. Calendar replay does not match
weather/holidays/occupancy and never means simultaneous observations. No battery feasibility
or portfolio commitment is established. Task 03B only: stop and wait for review before Task 04.

---

# Previous Task 03 handoff (historical reference)

# Current handoff — Task 03

Date: 2026-11-16. Status: Low Carbon London Data Lab complete; stopped for review.
Branch: codex/task03-lcl-data-lab. No commits or staging.

## Delivered

Actual 4TU v1 source and README downloaded once; publisher MD5 checks pass, raw SHA-256
and source provenance recorded. 4,443 standard-tariff households, 17,520 interval-end GMT
labels from 2013-01-01 00:30 to 2014-01-01 00:00. UTF-8 wide CSV (587,690,273 bytes)
inside 137,223,875-byte ZIP. 77,841,360 slots: 74,144,435 valid, 3,696,925 blank/missing
(4.7493%), no invalid values, duplicate keys, off-grid labels or absent timestamp rows.
See LCL_DATA_LAB.md for exact URLs, CC BY 4.0 attribution, checksums and full audit.

Streaming audit retains a stable SHA-256 sample of 100 actual IDs across 90 Jan–Mar
heating-season days plus 7 November and 6 December 2013. March is explicitly a shoulder
month. Prepared Parquet: 441,600 rows (436,634 valid, 4,966 missing), about 2.16 MB.
Original timestamp/kWh text retained; source labels mark END of preceding half-hour;
aware fixed GMT starts are derived separately, average kW = kWh × 2. Missing/invalid
readings remain null; duplicates quarantined; complete days require 48 valid intervals.

100 candidate metrics include completeness, full days, daily kWh, peak/evening kW,
standard deviation/CV and all-event load availability. 92 cover every replay interval;
71 pass the documented quality/residential-demand/event-availability gates. Five evenly
spaced daily-energy representatives selected; peak extremes are not the ranking criterion:

| Household | Complete days | Mean daily kWh | Peak kW | Mean evening kW |
| --- | --- | --- | --- | --- |
| MAC001391 | 90 | 3.4949 | 1.438 | 0.2634 |
| MAC003288 | 90 | 8.2387 | 3.076 | 0.5388 |
| MAC000143 | 90 | 10.4509 | 3.286 | 0.6276 |
| MAC001534 | 89 | 15.4507 | 3.898 | 0.9280 |
| MAC001395 | 89 | 29.3130 | 6.328 | 1.6557 |

First three have 100% analysis coverage; last two each miss one of 4,320 intervals.
All five cover every replay interval. Full candidate/recommendation/replay tables, reasons,
thresholds and limitations are in docs/LCL_DATA_LAB.md and ignored data/lcl/prepared/.

## Replay

Policy v1 matches same month and exact weekday in 2013, closest day number, earlier tie.
Calendar mapping is independent of demand. Retain original NESO scenario/date/start/end
and original household date/start/end. Join source energy at mapped interval END.

| Original NESO date | GMT window | Original household day |
| --- | --- | --- |
| 2025-03-18 | 18:00–19:00 | 2013-03-19 |
| 2025-11-06 | 17:00–18:00 | 2013-11-07 |
| 2023-12-01 | 16:30–18:00 | 2013-12-06 |
| 2026-01-11 | 17:00–19:00 | 2013-01-13 |
| 2025-02-02 | 16:00–19:00 | 2013-02-03 |

Same five households in all 17 unchanged original NESO intervals. Combined observed demand
ranges 2.354–6.240 kW. Example: first March interval maps to 2013-03-19 18:00–18:30;
household kW in selection order = 0.182, 0.428, 0.794, 0.668, 2.630; total 4.702 kW.
This is synthetic historical replay, never contemporaneous observations or a commitment.

## App and reproduction

Data Explorer retains the unchanged NESO presentation and advanced explorer. Enable the
separate Low Carbon London Data Lab toggle: source/quality panel, household and date
selectors, original half-hour table, load/daily energy charts, candidate table/scatter,
five recommendations, daily/evening profiles, and event/date/interval/per-house/combined kW.
Prepared local artifacts are integrity-checked and cached by audit modification time.
No full-source load, acquisition or analysis on Streamlit reruns. Missing data gives an
explicit preparation command; corrupt prepared files give an error.

From the BatteryFlex repository root (editable install per README):

```powershell
.\.venv\Scripts\python.exe scripts/prepare_lcl.py --acquire
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Acquisition reuses verified existing files; omit --acquire for local-only processing.
Raw files remain unchanged. data/ and outputs/ are confirmed ignored. Local reproduction
preserved candidate/recommendation CSV and Parquet hashes; replay values agree, with only
floating-point serialization differences after the final typed scalar-sum adjustment.
Audit stores current artifact hashes. No full dataset is committed or embedded in the app.

## Verification

- Final python -m pytest -q: 95 passed (66 previous + 29 new).
- python -m ruff check .: passed.
- python -m ruff format --check .: passed (42 files).
- .venv/Scripts/ty.exe check src scripts/prepare_lcl.py app.py: passed.
- Tests cover schema/IDs, missing/invalid/duplicate values, fixed GMT including DST dates,
  midnight endpoint assignment, kWh→kW, complete-day calculations, deterministic sampling
  and selection, all five calendar mappings, interval-END joins, missing total propagation,
  checksum rejection/reuse, offline UI empty/corrupt/data states and all five event tables.
- Real localhost Streamlit health ok; agent API ready. Saved real subset loaded; event tables
  had 2/2/3/4/6 half-hours, household change/date filter/provenance succeeded, no exceptions.
  No new server warnings/tracebacks observed. Temporary instance stopped. Agent snapshots
  saved only under ignored outputs/lcl-agent-*.json. Browser rendering was not separately tested.
- Sandboxed Streamlit processes stalled; cancelled those and ran UI/regression/server checks
  outside sandbox. Bare-mode cache/context messages occurred in headless test setup only.

## Files changed for Task 03

New:
- src/batteryflex/lcl_source.py
- src/batteryflex/lcl.py
- src/batteryflex/lcl_analysis.py
- src/batteryflex/ui/lcl_lab.py
- scripts/prepare_lcl.py
- tests/test_lcl.py
- tests/test_lcl_ui.py
- docs/LCL_DATA_LAB.md

Updated:
- src/batteryflex/ui/data_explorer.py (separate gated lab)
- pyproject.toml (explicit pandas/numpy/pyarrow dependencies)
- README.md
- docs/ARCHITECTURE.md
- docs/DATA_CONTRACTS.md
- docs/DEVELOPMENT_PLAN.md
- docs/DECISIONS.md
- docs/CURRENT_HANDOFF.md

## Scope and next review

Do not begin later tasks automatically. No NESO events, manifest or Task 02 validation
logic changed. No Turso integration, physical battery assumptions, battery dispatch,
MILP, MPC, economic optimisation or fixed portfolio commitment. Battery capacity, power,
efficiency, initial/minimum SOC and charging/forecast assumptions still require later
configuration and feasibility checks. A load profile alone does not prove deliverability.
Mapping does not match weather/holidays/occupancy; sample is illustrative and event-screened,
not representative of a modern VPP. See the report's limitations before feasibility work.

The parent Git repository already contained unrelated deletions/untracked projects and
batteryflex itself was untracked. Preserved that state, created the required feature branch,
and did not stage or commit anything. Task 03 only; stop for review.
