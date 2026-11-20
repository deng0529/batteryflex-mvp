> Cloud completion update — 18 November 2026: dedicated Turso/R2 connections now pass.
> Migration 001 and bootstrap completed; three five-home model bundles and 36 metric rows were
> automatically persisted. A fresh-cache second request reused all three with fitting/uploads/
> SQL mutations prohibited. All 15 R2 object hashes matched. Earlier credential-block findings
> below are historical. See [cloud completion report](TASK05C_CLOUD_COMPLETION.md).

# Task 05C — database-first storage and automatic model reuse

18 November 2026. Branch `codex/task05c-database-persistence`.
Implementation, local integration and dedicated cloud deployment are verified. The earlier
credential block is resolved; the completion report contains live migration/reuse evidence.

## Original credential findings and setup reference (block resolved)

The existing local `.env` contains the previous MVP's SQL URL/database token and R2 account/S3
keys. Secret values were not printed, committed or changed. No SQL request was made to the
previous MVP's database, and no previous-MVP objects were modified or migrated.

- **Turso `batteryflex-mvp`: existence unverified.** The available database JWT is not a usable
  platform-management credential; the account API returned HTTP 401. No platform token or
  organisation slug was found in the inspected project/environment/tool configuration.
- **R2 `batteryflex-mvp`: existence unverified.** Dedicated-bucket HEAD returned HTTP 403.
  Account bucket-list and dedicated-bucket creation attempts returned `AccessDenied`.
- No new account or OpenAI API key is needed. The existing OpenAI key remains untouched and is
  unused by forecasting/storage. Existing R2 keys can be reused if their permissions are extended.

Provide either a manually created dedicated Turso database's URL/read-write SQL token, or an
existing platform-management token and organisation slug with database read/create/token-mint
permissions. Never use the previous database JWT as a platform token. Configure secrets locally:

```dotenv
BATTERYFLEX_STORAGE_MODE=cloud
BATTERYFLEX_TURSO_DATABASE_URL=libsql://batteryflex-mvp-your-org.turso.io
BATTERYFLEX_TURSO_AUTH_TOKEN=<dedicated database token>
# Existing R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY are reused.
```

In Cloudflare, create the **batteryflex-mvp** bucket and grant the existing credential object
read/write access to this bucket and the bucket access needed for verification. If the old key
cannot be extended, supply bucket-scoped overrides `BATTERYFLEX_R2_ACCESS_KEY_ID` and
`BATTERYFLEX_R2_SECRET_ACCESS_KEY`. Never point `R2_BUCKET_NAME` at the old bucket as a workaround:
the application deliberately ignores that variable and pins the dedicated name.

For optional automated provisioning, configure `BATTERYFLEX_TURSO_PLATFORM_TOKEN` (or
`TURSO_API_TOKEN`) plus `BATTERYFLEX_TURSO_ORGANIZATION` (or `TURSO_ORGANIZATION`), and an optional
`TURSO_GROUP` (default `default`). Then run:

```powershell
.\.venv\Scripts\python.exe scripts/provision_storage.py
.\.venv\Scripts\python.exe scripts/storage_admin.py verify
.\.venv\Scripts\python.exe scripts/storage_admin.py bootstrap
```

Provisioning checks before creation, reuses an already configured dedicated SQL token, and
mints a dedicated token only when needed. It never uses `TURSO_AUTH_TOKEN` for platform calls.
The existing `.env` is backed up to ignored `.env.task05c.backup` before an atomic update of only
BatteryFlex keys, after both dedicated connections are verified. No secrets are printed.
Bootstrap performs no source downloads or model training. Provisioning and migrations never run
from a Streamlit page or normal startup. Keep `.env`, its backup and outputs outside Git.

## Storage architecture and tables

Versioned SQL: `src/batteryflex/storage/migrations/001_initial.sql`. SQLite is the local
reference/test backend; Turso uses parameterized Hrana HTTP batches. Transactions condition every
statement/COMMIT on earlier success, and close the stream to roll back failed batches. Migrations
record checksums; ordinary startup verifies the exact applied version/checksum without migrations.

| Tables | Purpose |
| --- | --- |
| schema_migrations | Applied version and immutable SQL checksum |
| households, household_selections, selection_members | Household identity and ordered selection versions |
| objects | Content SHA-256, confined R2 key, byte size and artifact kind |
| datasets, dataset_assets | Dataset versions, original provenance/coverage and prepared-object references |
| neso_events, replay_mappings | Original source events/hashes and separate explicit 2013 replay mapping |
| portfolios, batteries | Immutable content-based portfolio and per-household configurations |
| feature_schemas, forecast_configs | Feature order and source/selection/model/split configuration |
| forecast_models | Immutable method/version, exact fingerprint, artifact and optional result references |
| forecast_metrics | Per-household/portfolio validation/test MAE, RMSE and observation counts |
| evaluation_archives | Verified pre-existing results that have no matching saved fitted model |
| model_leases | Expiring, owner-scoped claims for concurrent forecast requests |
| active_selections, system_settings | Explicit active references and extensible settings |
| simulation_runs, simulation_metrics, simulation_artifacts | Future typed relational run references, scalar metrics and trajectories/artifact pointers |

Foreign keys, unique constraints, checks and lookup indexes protect these relationships. No
simulation rows, dispatch trajectories, optimisation or fake run results are generated.

Large prepared datasets, model bundles and detailed prediction time series belong in R2;
metadata/configuration/metrics/reference state belong in SQL. Object keys are content-addressed
`objects/<sha256>` inside the dedicated bucket. Uploads use create-only conditional requests and
verify remote bytes before metadata publication. A verified local object cache is keyed by the
same SHA-256. Bad local cache entries can be repaired from verified R2 objects; missing/corrupt
remote artifacts produce clear errors. Unreferenced uploads after a failure/crash are not cache hits.
No automatic deletion or unsafe object cleanup is performed.

Models retain the trusted Task 05B JSON/native-LightGBM format, numeric Ridge scaling/coefficient
arrays and configuration-only Naive state. There is no executable pickle/joblib loading. SQL
object hashes independently pin artifacts in addition to each bundle's internal checksum.

## Controlled bootstrap and existing data

The explicit bootstrap verifies original prepared audit hashes, schema version, row counts,
coverage, duplicates and valid measured kW semantics before publication. It copies existing
prepared bytes, never downloads or reparses annual raw LCL/NESO files. Original observation
energy/timestamps/quality and event provenance remain unchanged.

The isolated **local verification** bootstrap imported:

- Five household records and the reviewed ordered selection.
- Five exact prepared assets: audit JSON, observations Parquet, candidates, recommendations and
  replay CSVs. The original Parquet retains 441,600 rows for 100 candidates; application forecasts
  still use the five reviewed homes. Each reviewed home retains 4,416 original intervals over
  92 dates; the Jan–Mar forecast period has 4,320 expected intervals and two known missing cells.
- Five NESO historical events, their verified manifest object and original-to-2013 replay mappings.
- The five default simulated battery configurations in one content-based portfolio version.
  Prior browser-only edits have no durable file to migrate; they are not invented as saved assets.
- Three forecast configuration records and the existing feature schema.
- Existing Task 05B evaluation CSV/Parquet files: source reference verified, actuals checked
  against measured source and metrics independently recomputed. These remain an archive rather
  than a fitted-model cache entry.
- **Zero pre-existing saved model bundles:** none existed in the production local registry.
  Missing models were reported, not trained by bootstrap.

If legacy saved bundles exist, import verifies their completeness/source/hash/schema, preserves
immutable versions and any active reference, and imports their structured metrics. A legacy model
without matching exact prediction series has a null result reference: it can serve compatible
inference, but cannot masquerade as an exact reusable evaluation cache hit. Repeated bootstrap
reuses existing rows/object identities and never overwrites historical versions or active choices.

The dedicated cloud database/bucket now contain the validated bootstrap and three generated model
bundles/results. The initial credential-blocked local verification preceded this cloud migration.

## Startup, forecast requests and model selection

Normal startup reads active dataset, portfolio and model metadata, validates schema/provenance and
loads verified cached/R2 assets. It performs no schema migrations, external source downloads or
model fitting. On Forecast Model Development opening, complete exact stored results are restored
without Run Models. Configured cloud failures are reported, not silently replaced by another
project or newly trained data.

Without dedicated cloud credentials, reviewed local project files stay available for read-only
exploration. Explicit local development is available with the same SQL/object contracts:

```powershell
.\.venv\Scripts\python.exe scripts/storage_admin.py bootstrap --local
$env:BATTERYFLEX_STORAGE_MODE = 'local'
.\.venv\Scripts\python.exe -m streamlit run app.py
```

A previously bootstrapped default local database can also be reused as a visibly labelled
development fallback when dedicated cloud URL configuration is absent. An unconfigured/missing
persistent store is never created by opening the app; Run Models explains that bootstrap is needed.
Local disks must be retained/backed up; ephemeral hosting is not durable storage.

Run Models is an explicit **load existing or train missing** request. Per-algorithm fingerprints
include dataset content hash, ordered selected IDs, normalized effective exposed parameters,
feature schema/version, split boundaries/missing policy, 48-step horizon, relevant implementation
hashes, cache format and numerical library versions. Battery settings and event/replay choices
are deliberately excluded. Complete existing models/results are verified and reused; only missing
methods are fitted. Seasonal Naive remains the mandatory reference.

A lease claim serializes each fingerprint across workers. Another in-flight request gets a clear
retry message, not duplicate fitting. Leases expire after ten minutes; this MVP's fits are much
shorter. Uploads and integrity checks precede one transactional publication of model, configuration,
metrics and result pointers. Publication failure cannot create a ready model/result record; valid
methods from an earlier successful part of a multi-method request remain reusable on retry.
Success is displayed only after persistence and reload verification. Crashed/unreferenced objects
may consume space and need a future explicitly reviewed retention policy.

A4 retains five household curves, one grouped interactive full-test RMSE chart (household,
algorithm and RMSE-kW hover) and a computed conclusion, with no redundant accuracy tables.
There is no Save Model button or user-entered version field. Automatic immutable versions use
`auto-<fingerprint>`. The activation selector defaults to the exact current configuration's
lowest validation portfolio RMSE, never a test winner or an older configuration of that algorithm.
Users may explicitly activate another available complete version without retraining. The choice
is persisted in SQL and restored in new sessions. Model data cutoff and feature/history availability
checks remain unchanged; final evaluated models cannot serve earlier March historical origins.

Portfolio confirmation creates a new immutable content-hash version and updates the active
reference; unchanged values reuse the same version. Unsaved edits/restores never change it.
New sessions load the saved portfolio from SQL. Battery changes never invalidate load forecasts.

Changed selection/configuration/dataset versions produce independent fingerprints; unchanged
methods remain reusable. The service supports different valid registered household subsets;
the current public workspace continues to show the reviewed five-home study. New unregistered
households/data require explicit validated registration, not an implicit import at render time.
New NESO event versions do not invalidate load models. The supported frozen manifest is checked
against its stored snapshot and the existing unchanged validator; new event sets require an
explicitly reviewed supported manifest/deployment version. Forecast algorithms/feature versions
must be implemented and reviewed before new choices are exposed; incompatible versions fail.

## Verification and limitations

The isolated verification store is `outputs/task05c/local-verification/`; no default production
store or cloud resource was substituted. An explicit local forecasting verification request
trained/persisted three bundles and 36 metric rows. A second request reused all three with fitting
disabled. Results matched the Task 05B measured benchmark (portfolio test RMSE: Naive 1.159441,
Ridge 0.977148, LightGBM 0.946907 kW). The original training algorithms/features/splits and all
19 preserved source/data hashes remain verified; only support for explicit household selections
was generalized in batch aggregation/serialization, without changing five-home numerical results.

The localhost smoke restored five curves on page open, reused 2/3 methods with zero training on
Run Models, changed the display day, persisted explicit activation and restored it in a new session;
model versions/timestamps stayed unchanged. Tabs B/C remain non-executing. The temporary server
stopped and logged no new warnings/tracebacks. See CURRENT_HANDOFF.md for final test totals.

Routine tests use SQLite and fake R2/HTTP clients, including rollback, partial failures,
concurrency, corruption, source/config/household dependency invalidation, immutable versions,
legacy imports, information cutoffs and UI behavior. Live dedicated-resource integration now passes: connection checks, schema migration, idempotent
bootstrap, all-object integrity, first-fit persistence, fresh-cache reuse and cloud-backed UI smoke.
See TASK05C_CLOUD_COMPLETION.md for the verified results.

Dependencies added: boto3 >=1.35,<2 and python-dotenv >=1,<2. Existing OpenAI credentials are
unused. Future simulation relational storage/interfaces are prepared; no rule-based dispatch,
MILP, MPC, tariff optimisation or full simulation execution is implemented.

## Primary API references

- [Turso platform authentication/scopes](https://docs.turso.tech/api-reference/authentication)
- [Turso database creation](https://docs.turso.tech/api-reference/databases/create)
- [Turso database token generation](https://docs.turso.tech/api-reference/databases/create-token)
- [Turso HTTP SQL](https://docs.turso.tech/sdk/http/reference)
- [Hrana HTTP transaction protocol](https://github.com/tursodatabase/libsql/blob/main/docs/HTTP_V2_SPEC.md)
- [Cloudflare R2 credentials and scope](https://developers.cloudflare.com/r2/api/tokens/)
- [R2 S3 compatibility](https://developers.cloudflare.com/r2/api/s3/api/)


## Task 05D event storage

Migration 002 adds event requests, immutable model references, scoped metrics, feasibility status and explicit event-specific activation. Dataset assets and model/prediction/evaluation objects use the existing SHA-256 content store. The original benchmark schema/fingerprints and active dataset selection remain intact. Event models include a separate feature schema and exact policy/configuration fingerprints; model artifacts contain only pre-origin information, with post-hoc event errors in a separate evaluation object. Startup never migrates or trains. See [event forecasting report](TASK05D_EVENT_FORECASTING.md) for commands, provenance, versions and cold-cache evidence.


## Activation-free forecast resolver

`storage.forecast_resolver.resolve_event_forecast` reads the persisted event/mapping and verifies exact saved default models through the existing immutable reader. Automatic selection uses Ridge/LightGBM validation portfolio RMSE only, with Ridge winning exact ties; an explicit algorithm override can also select the Seasonal Naive benchmark. No active-model pointer is consulted or written. Existing activation tables and compatibility methods are retained unchanged. There are no migrations or artifact/fingerprint changes. See [resolver contract](FORECAST_RESOLVER.md) for shapes, failures and future Task 06 integration.
