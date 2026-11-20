# Task 05C — cloud completion report

Date: 18 November 2026. Branch: `codex/task05c-database-persistence`.
Status: dedicated cloud connections, migration, bootstrap and forecast reuse verified.
Task 06 has not started. No previous-MVP resources were queried, modified or used for migration.

## Connections and isolation

The user configured dedicated credentials in the local `.env`. The application loaded them
without printing secret values. Cloud mode and the dedicated Turso hostname guard were verified
before any writes. `SELECT 1` succeeded on the dedicated **batteryflex-mvp** database and R2 HEAD
succeeded on the **batteryflex-mvp** bucket. The SQL database had zero tables before migration.
The agent did not edit `.env`, mint extra credentials, create accounts or call OpenAI.

All SQL went through the dedicated URL guard. Every R2 operation used the dedicated bucket and
content-addressed project keys. No previous-MVP database or objects were accessed or modified.

## Migration and bootstrap

Applied schema migration 001, with its recorded checksum. All **22 tables** are present and
runtime schema verification passes. The live SQL foreign-key check returned no violations.
Bootstrap consumed existing validated local project artifacts; no LCL/NESO downloads occurred.

| Imported entity | Result |
| --- | ---: |
| Reviewed households | 5 |
| Ordered household selections / members | 1 / 5 |
| Dataset versions / prepared assets | 1 / 5 |
| Original prepared observation rows | 441,600 across 100 candidates |
| Reviewed-household retained intervals | 4,416 each; 22,080 total |
| Known missing reviewed-household cells | 2, preserved |
| NESO events / explicit replay mappings | 5 / 5 |
| Portfolio versions / battery configurations | 1 / 5 |
| Initial forecast configurations / feature schemas | 3 / 1 |
| Verified Task 05B evaluation archives | 1 |
| Pre-existing production model bundles imported | 0; no such bundles existed |

The bootstrap portfolio uses the five existing research defaults; prior browser-only edits
were not fabricated as durable configurations. Original measured timestamps, energy/power units,
quality markers, source SHA-256 references and explicit historical replay semantics are preserved.
The observation content hash remains
`b31e7c088a3fa3ec7cdffa448361777cbbcefddc72b59df2c39a043f761d858c`.
All 19 preserved Task 03E source/data hashes match.

Bootstrap was repeated against the live dedicated resources. It reused the same data/configuration
versions and archive, imported no extra model bundle, and left all fitted-model versions and
creation timestamps unchanged. It did not retrain models.

## First cloud forecasting request

No exact fitted models existed in the cloud registry after bootstrap. The explicitly authorised
forecast request trained/evaluated Seasonal Naive, Ridge Regression and LightGBM using the
unchanged Task 05B split, features, hyperparameters and 48-step conventions.

Each algorithm was automatically persisted as one complete five-household bundle. Artifacts and
detailed validation/test predictions were uploaded to R2, remotely verified and transactionally
registered with structured metrics in Turso, then reloaded successfully.

| Cloud output | Count |
| --- | ---: |
| Immutable method bundles | 3 (15 household algorithm members) |
| Structured validation/test metric records | 36 |
| Detailed evaluated prediction rows across all methods | 24,480 |
| Registered R2 objects including datasets/archives/models/results | 15 |
| Completed-request leases remaining | 0 |
| Simulation runs / metrics / artifacts | 0 / 0 / 0 |

There are six forecast configuration records: three initial configurations plus three exact
fingerprinted execution configurations. They reference the same validated dataset/selection.
No executable pickle artifacts were used.

All 15 registered R2 objects were fetched directly and their byte lengths/SHA-256 values checked
against the independent SQL references. All matched.

## Second identical request — proven reuse

A new repository connection used a **fresh, empty local cache directory**. It loaded the dataset
and artifacts from the dedicated R2 bucket and metadata from Turso. During the second request:

- Both the training entry point and estimator fit function were replaced with failure guards.
- R2 uploads were prohibited.
- SQL mutations were prohibited; 20 metadata queries were SELECT-only.
- Seasonal Naive, Ridge and LightGBM were all reported reused; **zero methods trained**.
- Predictions and metrics exactly matched the first request.
- Model fingerprints, artifact/result references and creation timestamps stayed unchanged.

This confirms actual cloud reuse rather than an in-memory or first-run disk-cache shortcut.

## Forecast accuracy and selection

The cloud results match the complete existing Task 05B measured benchmark, including every
household and both partitions. Portfolio scores are:

| Algorithm | Validation RMSE kW | Test MAE kW | Test RMSE kW |
| --- | ---: | ---: | ---: |
| Seasonal Naive | 1.005976 | 0.823539 | 1.159441 |
| Ridge Regression | 0.922735 | 0.736022 | 0.977148 |
| LightGBM | 0.829418 | 0.684537 | 0.946907 |

LightGBM is the current **validation-based recommendation**. Active model selection was not changed:
there was no prior cloud active reference, so activation remains an explicit user choice in A4.
All three bundles/results are already durable and reusable without activation or retraining.
Choosing Activate Model persists the selected reference for future simulation interfaces.
The existing information-cutoff and history-availability restrictions remain enforced; this task
does not make earlier March or incomplete-history replay origins valid.

## Live application verification

A temporary localhost Streamlit instance used cloud mode and the dedicated credentials, with a
separate local cache. It restored five household figures on opening Simulation Lab, before clicking
Run Models. No Save Model control was present. The default request reported **2 reused / 0 trained**;
adding Ridge reported **3 reused / 0 trained**. Changing the test day used stored predictions.

A new session restored the cloud-backed results. Model versions/timestamps stayed unchanged;
no activation choice was changed. Run Simulation & Results and Comparison & Evaluation remained
non-executing. The temporary server was stopped and logged no new warnings/tracebacks.

## Tests, artifacts and handoff

- **294 tests passed in 66.53 seconds**, with routine tests isolated from live credentials.
- Ruff lint and format checks and ty (`src app.py`) passed.
- Live connection, migration checksum, bootstrap idempotency, foreign keys, all-object integrity,
  first-fit persistence, cold-cache reuse and cloud-backed Streamlit checks passed.
- Existing algorithms/data hashes and Tasks 01–05B regression behavior are preserved.
- Credentials and generated artifacts remain ignored by Git. No staging/commits were performed.

Ignored detailed verification outputs are in `outputs/task05c/cloud-verification/`: `report.json`,
`bootstrap-idempotency.json`, metrics/counts CSVs, predictions Parquet and smoke logs/snapshot.
The report contains resource names, hashes and counts, never tokens or secret access keys.
Current cloud setup and architecture: [STORAGE.md](STORAGE.md).

Task 05C is complete for this authorised cloud deployment. No Task 06, dispatch optimisation,
MILP, MPC, tariff optimisation or full simulation execution was started.
