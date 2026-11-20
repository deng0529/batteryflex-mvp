# Task 05D — Event-aligned forecasting completion

18 November 2026. Branch `codex/task05d-event-aligned-forecasting`. All five unchanged NESO replays support leakage-free Ridge and LightGBM forecasts. No model has been automatically activated. No Task 06, commit, merge or deployment was performed.

## Sources, coverage and quality

[Phase A investigation](TASK05D_PHASE_A.md) was completed before fitting. It records the unchanged event mappings, source integrity checks and the coverage-driven feature decision. The annual [4TU release](https://doi.org/10.4121/fbbe775b-48d8-469f-a39b-b64488bfd6fd.v1) supplies all 17,520 half-hours of 2013 for each household. Earlier measurements came from the original [UKPN/London Datastore release](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d), not substituted households or synthetic data.

Annual ZIP SHA-256: `bce91566326674d82ad3afd1b8cf73f5852f4fdbc0a1bbbfc5120b0ecf22b919`.
Original ZIP SHA-256: `149a6a9c43c622fd0a14b7d11be055665317d3018d9fb7e1043bd51420bfaea5` (795,722,689 bytes). No independent publisher checksum was supplied for the original ZIP; local SHA-256, HTTP acquisition metadata and all 168 CSV member CRCs were verified and retained. All 87,531 valid overlapping 2013 readings agreed. Five off-grid and 216 duplicate-key raw rows were quarantined with provenance. Original source ends at 2014-02-28 00:00 GMT; this dataset deliberately uses original pre-2013 observations plus unchanged curated 2013 readings only.

Expanded dataset `35cc1d8478f61322117e98bef0d0bbb85a1cb02d55f43f069417729e064327fd` contains 143,299 retained unique rows: 143,252 valid, 38 duplicate-quality placeholders and 9 explicitly missing values. Absent calendar slots remain missing. No interpolation, averaging of duplicates, zero-fill or timestamp rounding was used. Interval-end source labels and fixed GMT semantics are preserved; model curves display interval starts and average kW (kWh / 0.5).

Exact expanded coverage, including absent grid slots between each household's retained endpoints:

| Household | First start GMT | Last end GMT | Retained | Numeric | Absent grid slots | Missing/duplicate cells |
| --- | --- | --- | --- | --- | --- | --- |
| MAC001391 | 2012-05-17 12:30:00+00:00 | 2014-01-01 00:00:00+00:00 | 28340 | 28330 | 147 | 10 |
| MAC003288 | 2012-09-21 11:00:00+00:00 | 2014-01-01 00:00:00+00:00 | 22394 | 22390 | 0 | 4 |
| MAC000143 | 2011-12-16 09:30:00+00:00 | 2014-01-01 00:00:00+00:00 | 35831 | 35818 | 6 | 13 |
| MAC001534 | 2012-05-22 10:30:00+00:00 | 2014-01-01 00:00:00+00:00 | 28249 | 28239 | 2 | 10 |
| MAC001395 | 2012-05-17 13:00:00+00:00 | 2014-01-01 00:00:00+00:00 | 28485 | 28475 | 1 | 10 |

## Feasibility and reproducible chronology

All 25 household/event combinations have complete previous-day and previous-weekday profiles, 48 measured event-day targets and complete event-window targets. Original NESO records and the five historical replay dates/windows remain unchanged. These are historical replays, not contemporaneous measurements from the original NESO delivery dates. Internal `BF-SCENARIO-*` identifiers are not official NESO event identifiers.

Forecast origin is replay-date midnight GMT; horizon is 48 half-hours. A common policy uses up to 90 training calendar days, then 14 validation days, then 14 broader holdout days ending before the origin. At least 28 usable training and seven validation/holdout origins per household are required. Incomplete feature/target days are excluded; portfolio holdout scoring uses only days complete across all five homes. The full coverage matrix, including missing historical interval counts, is stored in the dataset's coverage artifact and locally in `outputs/task05d/coverage-matrix.csv`.

The event schema `load-event-dayweek-v1` uses calendar/horizon, previous-day/week lags and complete day/weekday profile mean/std. It excludes intervening-week rolling statistics: the legacy 336-step requirement would unnecessarily block January/MAC001395 and November/MAC001391. This new schema was chosen from coverage before examining forecast errors; legacy schema and benchmark fingerprints remain intact.

Ridge alpha 1; LightGBM 200 estimators, learning rate 0.05, 15 leaves, max depth -1, seed 42. Estimators and Ridge scaling fit training only. Validation portfolio RMSE supplies the recommendation. Parameters are frozen before the broader holdout. Each holdout day can use measurements available before that day's origin; final-day actuals never feed fitting or features. Event-day actuals and errors live in a separate evaluation artifact, beyond the model information cutoff. No automatic model activation occurs.

| original_neso_date | replay_date | event_window | duration_minutes |
| --- | --- | --- | --- |
| 2025-03-18 | 2013-03-19 | 18:00–19:00 | 60.0000 |
| 2025-11-06 | 2013-11-07 | 17:00–18:00 | 60.0000 |
| 2023-12-01 | 2013-12-06 | 16:30–18:00 | 90.0000 |
| 2026-01-11 | 2013-01-13 | 17:00–19:00 | 120.0000 |
| 2025-02-02 | 2013-02-03 | 16:00–19:00 | 180.0000 |

Historical admission details (usable complete daily origins; missing intervals cover the training/validation/holdout calendar span plus seven days of required lookback):

| Household | Replay date | Training | Validation | Holdout | Missing history intervals |
| --- | --- | --- | --- | --- | --- |
| MAC001391 | 2013-03-19 | 86 | 14 | 14 | 2 |
| MAC003288 | 2013-03-19 | 86 | 14 | 14 | 2 |
| MAC000143 | 2013-03-19 | 86 | 14 | 14 | 2 |
| MAC001534 | 2013-03-19 | 86 | 14 | 11 | 3 |
| MAC001395 | 2013-03-19 | 83 | 14 | 14 | 3 |
| MAC001391 | 2013-11-07 | 90 | 14 | 12 | 1 |
| MAC003288 | 2013-11-07 | 87 | 14 | 14 | 1 |
| MAC000143 | 2013-11-07 | 90 | 14 | 14 | 0 |
| MAC001534 | 2013-11-07 | 87 | 14 | 14 | 1 |
| MAC001395 | 2013-11-07 | 90 | 14 | 14 | 0 |
| MAC001391 | 2013-12-06 | 88 | 13 | 14 | 1 |
| MAC003288 | 2013-12-06 | 90 | 14 | 14 | 0 |
| MAC000143 | 2013-12-06 | 90 | 13 | 12 | 1 |
| MAC001534 | 2013-12-06 | 87 | 14 | 14 | 1 |
| MAC001395 | 2013-12-06 | 90 | 14 | 14 | 0 |
| MAC001391 | 2013-01-13 | 79 | 11 | 14 | 5 |
| MAC003288 | 2013-01-13 | 72 | 11 | 14 | 553 |
| MAC000143 | 2013-01-13 | 79 | 11 | 14 | 5 |
| MAC001534 | 2013-01-13 | 77 | 11 | 14 | 6 |
| MAC001395 | 2013-01-13 | 79 | 11 | 12 | 6 |
| MAC001391 | 2013-02-03 | 79 | 14 | 14 | 4 |
| MAC003288 | 2013-02-03 | 81 | 14 | 14 | 3 |
| MAC000143 | 2013-02-03 | 81 | 14 | 14 | 3 |
| MAC001534 | 2013-02-03 | 78 | 14 | 14 | 4 |
| MAC001395 | 2013-02-03 | 79 | 11 | 14 | 5 |

## Forecast results

Errors are average-power kW. Each replay has only 2–6 event intervals, so event scores have limited statistical strength. Broader holdout results are separate and cannot be replaced by a favorable short event score.

Portfolio full-day and event-window errors:

| original_date | replay_date | method | mae_kw / event_window | mae_kw / full_day | rmse_kw / event_window | rmse_kw / full_day |
| --- | --- | --- | --- | --- | --- | --- |
| 2023-12-01 | 2013-12-06 | LightGBM | 0.5313 | 0.7960 | 0.6854 | 1.2146 |
| 2023-12-01 | 2013-12-06 | Ridge Regression | 1.1895 | 0.9093 | 1.2599 | 1.2380 |
| 2023-12-01 | 2013-12-06 | Seasonal Naive | 1.2187 | 0.9587 | 1.4109 | 1.3541 |
| 2025-02-02 | 2013-02-03 | LightGBM | 0.2944 | 0.6246 | 0.3326 | 0.7984 |
| 2025-02-02 | 2013-02-03 | Ridge Regression | 0.3527 | 0.6971 | 0.4581 | 0.9170 |
| 2025-02-02 | 2013-02-03 | Seasonal Naive | 0.6710 | 0.7957 | 0.7238 | 0.9985 |
| 2025-03-18 | 2013-03-19 | LightGBM | 0.3562 | 0.4440 | 0.3864 | 0.6339 |
| 2025-03-18 | 2013-03-19 | Ridge Regression | 0.7654 | 0.5734 | 0.7689 | 0.7530 |
| 2025-03-18 | 2013-03-19 | Seasonal Naive | 0.1550 | 0.5883 | 0.2150 | 0.8040 |
| 2025-11-06 | 2013-11-07 | LightGBM | 0.2559 | 0.4730 | 0.3104 | 0.7511 |
| 2025-11-06 | 2013-11-07 | Ridge Regression | 0.2778 | 0.5034 | 0.2812 | 0.8388 |
| 2025-11-06 | 2013-11-07 | Seasonal Naive | 1.7270 | 0.6161 | 1.8428 | 1.0724 |
| 2026-01-11 | 2013-01-13 | LightGBM | 0.6164 | 0.5644 | 0.7632 | 0.9073 |
| 2026-01-11 | 2013-01-13 | Ridge Regression | 1.1748 | 0.7537 | 1.4034 | 1.0313 |
| 2026-01-11 | 2013-01-13 | Seasonal Naive | 0.8450 | 0.6632 | 0.9939 | 0.9612 |

Pooled broader holdout errors (non-overlapping replay-specific evaluation windows; household availability can differ):

| household | method | mae_kw | rmse_kw | observations |
| --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 0.1873 | 0.2996 | 3264 |
| MAC000143 | Ridge Regression | 0.1819 | 0.2953 | 3264 |
| MAC000143 | Seasonal Naive | 0.2249 | 0.3747 | 3264 |
| MAC001391 | LightGBM | 0.0746 | 0.1311 | 3264 |
| MAC001391 | Ridge Regression | 0.0762 | 0.1319 | 3264 |
| MAC001391 | Seasonal Naive | 0.0962 | 0.1737 | 3264 |
| MAC001395 | LightGBM | 0.3787 | 0.5624 | 3264 |
| MAC001395 | Ridge Regression | 0.3807 | 0.5735 | 3264 |
| MAC001395 | Seasonal Naive | 0.4308 | 0.6991 | 3264 |
| MAC001534 | LightGBM | 0.2397 | 0.3635 | 3216 |
| MAC001534 | Ridge Regression | 0.2371 | 0.3629 | 3216 |
| MAC001534 | Seasonal Naive | 0.2949 | 0.4604 | 3216 |
| MAC003288 | LightGBM | 0.1781 | 0.2883 | 3360 |
| MAC003288 | Ridge Regression | 0.1782 | 0.2855 | 3360 |
| MAC003288 | Seasonal Naive | 0.2046 | 0.3684 | 3360 |
| Portfolio | LightGBM | 0.5957 | 0.8256 | 2928 |
| Portfolio | Ridge Regression | 0.6303 | 0.8680 | 2928 |
| Portfolio | Seasonal Naive | 0.7016 | 0.9978 | 2928 |

## Persistence and reuse evidence

Dedicated `batteryflex-mvp` Turso/R2 connections were verified. Additive migration 002 installed five event tables (27 total); migration 001 remains unchanged. Four dataset assets and 15 event model bundles were saved automatically using Task 05C content-addressed objects and SHA-256 verification. Ten Ridge/LightGBM bundles contain 50 household estimators; five Seasonal Naive bundles provide a paired baseline. Each bundle has immutable model JSON, detailed forecasts Parquet and separate evaluation JSON. Structured SQL holds exact configurations/fingerprints, feature schema, household selection, source/mapping references, training/validation/holdout windows, origins/horizons and 360 metrics. There are 118,962 detailed prediction rows across all scopes.

Cold-cache verification used a new local directory, prohibited fitting, R2 uploads and every non-SELECT SQL statement, and restored all 15 exact requests with identical predictions (91 SELECTs; zero training and mutations). Saved inference also returned five household 48-step forecasts for every event. All 64 total registered R2 objects passed remote size/SHA-256 checks. Foreign keys passed. Every snapshotted Task 05C row remains unchanged, and all three legacy benchmark cache entries still restore. Event activations and simulations remain zero. Evidence: `outputs/task05d/cloud-report.json`; before-state: `outputs/task05d/task05c-before.json`.

Exact saved model versions:

| original_date | replay_date | method | model_version |
| --- | --- | --- | --- |
| 2026-01-11 | 2013-01-13 | LightGBM | event-ba46758b9103b7f34b865c5fa209acdfdbe98ad6292428ee6fe3731c71e902d9 |
| 2026-01-11 | 2013-01-13 | Ridge Regression | event-43ede2f2957ac1a2ce0b47d9523c14f16009d34b1d2c4772deb553c69925bd09 |
| 2026-01-11 | 2013-01-13 | Seasonal Naive | event-67b8f467826b2182242e895136c4256ffe30d887f89569be8b7fed8f4412a420 |
| 2025-02-02 | 2013-02-03 | LightGBM | event-c13b10249e432c094a4a1a4539b98f0a02c92add972821b9a05607b3cbd8ecba |
| 2025-02-02 | 2013-02-03 | Ridge Regression | event-5588d10706c317ec4ef90f8288098010ce827a642194fe602bd9dc2fe8f868fa |
| 2025-02-02 | 2013-02-03 | Seasonal Naive | event-19b2c164853bab74d1e272ef5a8c5ae0c5a7f039a1baf2f8b06b60075c96558e |
| 2025-03-18 | 2013-03-19 | LightGBM | event-d18e6dfbff45fff3109dea45acf8f4aa8787c8b33019886c4d4b429c8d9baace |
| 2025-03-18 | 2013-03-19 | Ridge Regression | event-105c51e8376a6947fc824483b7d70672a95d97820c6a5c882246e890595686f1 |
| 2025-03-18 | 2013-03-19 | Seasonal Naive | event-af8b7dabdeeed115170aea27511c7bffc24b5b7600b1d383f5727f3b83fa3df5 |
| 2025-11-06 | 2013-11-07 | LightGBM | event-3d896138c769ed80bbe5fff93da2a34932fb1b4c8d19b8bf8a0d579187848a4a |
| 2025-11-06 | 2013-11-07 | Ridge Regression | event-b799fe5beb020699d36ba73228ee147fc39e35d24b9bcf77722b9350e1c4a6b3 |
| 2025-11-06 | 2013-11-07 | Seasonal Naive | event-22eae9ae3d8daed4b71519bf3663a5082522c3c5dfd713c05d63f9585890f0d2 |
| 2023-12-01 | 2013-12-06 | LightGBM | event-006f2fcc04122cf989695062e01f986ec09c178fb1bd265b84f7e099b456eaea |
| 2023-12-01 | 2013-12-06 | Ridge Regression | event-505a27e4670a92bb5e1bc3765e04a9bb4802502d95d61eb3a1c4f0ddc13a2b50 |
| 2023-12-01 | 2013-12-06 | Seasonal Naive | event-46a93f158487d55e498c7dc9609be512682e05e073e9869ec5b8c03a1681d063 |

## Streamlit and reproduction

Simulation Lab retains Forecast Model Development, Run Simulation & Results, and Comparison & Evaluation. Forecast Model Development now offers Benchmark development or Event-aligned forecasting. The event view provides the original/replay dates, duration/window, household feasibility, six zoomable GMT curves (five homes plus portfolio), one interactive RMSE comparison with full-day/event error hover, broader holdout comparison, validation recommendation and saved version/provenance. Opening a saved request restores results without fitting. Run Event Models automatically persists/reuses; Activate Event Model is explicit and event-specific. There is no Save Model button. No dispatch or simulation execution is implemented.

Explicit commands, run from the project with the existing environment and dedicated `.env`:

```powershell
.venv/Scripts/python.exe scripts/acquire_event_source.py
.venv/Scripts/python.exe scripts/prepare_event_history.py
.venv/Scripts/python.exe scripts/run_event_forecasts.py --migrate --history data/lcl/event_history_v1
.venv/Scripts/python.exe scripts/run_event_forecasts.py
.venv/Scripts/python.exe -m streamlit run app.py
```

Acquisition is explicit and pinned to the reviewed archive SHA; startup performs no download or migration. History preparation refuses to overwrite incompatible existing artifacts. The default run evaluates all five events, automatically reusing exact saved configurations. Source archives, project data, outputs and `.env` remain excluded from Git. No previous-MVP resources or existing model versions were modified.

## Verification and limitations

The full regression suite passed: **305 tests in 188.88 seconds**. Ruff check and format checks passed for all 112 Python files; `ty check src scripts` passed. The explicit acquisition helper also verified the existing pinned source without a network download. A fresh-cache, cloud-backed Streamlit agent-API smoke check restored all five event selections with seven charts each, exercised full-day/event/holdout comparison controls, and clicked Run Event Models for every event: each reported three reused and zero trained. The other two Simulation Lab tabs remained available; all saved model versions/timestamps were unchanged, no event model was activated, and server logs contained no exceptions or deprecation warnings. The temporary local verification server was stopped. Evidence: `outputs/task05d/ui-verification/smoke-final.json` and `smoke-server.log`. Phase A source integrity and all 19 preserved local source/data hashes were verified. New tests cover exact mappings, chronological boundaries, future perturbation, missing features, 48-step output, aggregation/scoring, immutable versions, concurrent leases/upload failure, cold-cache read-only reuse and Streamlit restoration/explicit activation.

This is a five-household historical evaluation with modest event-window sample sizes. Models do not establish general performance across unseen homes/events, weather or behavioral changes. No exhaustive hyperparameter search was performed. Missing observations remain missing, excluded days reduce effective samples, and unavailable future requests fail explicitly rather than alter replay dates. Historical event actuals are used for post-hoc evaluation only. Model activation remains a user decision; Task 06 is not started.

## Household and portfolio full-day/event errors

The complete machine-readable 360-row file is `outputs/task05d/event-metrics.csv`, and the same results are immutable cloud artifacts. Per-event values below include all five homes and portfolio; errors are kW.


### Replay 2013-01-13

| household | method | mae_kw / event_window | mae_kw / full_day | rmse_kw / event_window | rmse_kw / full_day |
| --- | --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 0.1583 | 0.1746 | 0.1726 | 0.3214 |
| MAC000143 | Ridge Regression | 0.1943 | 0.1770 | 0.2374 | 0.3254 |
| MAC000143 | Seasonal Naive | 0.5580 | 0.2913 | 0.5683 | 0.4205 |
| MAC001391 | LightGBM | 0.1373 | 0.0504 | 0.1577 | 0.0740 |
| MAC001391 | Ridge Regression | 0.1497 | 0.0588 | 0.1795 | 0.0823 |
| MAC001391 | Seasonal Naive | 0.2205 | 0.0820 | 0.2306 | 0.1132 |
| MAC001395 | LightGBM | 0.7343 | 0.4604 | 0.8778 | 0.7972 |
| MAC001395 | Ridge Regression | 0.5328 | 0.5028 | 0.9072 | 0.8560 |
| MAC001395 | Seasonal Naive | 0.4690 | 0.6092 | 0.5602 | 0.9940 |
| MAC001534 | LightGBM | 0.1315 | 0.1983 | 0.1495 | 0.2817 |
| MAC001534 | Ridge Regression | 0.1922 | 0.2340 | 0.2137 | 0.2952 |
| MAC001534 | Seasonal Naive | 0.4285 | 0.2565 | 0.5728 | 0.4772 |
| MAC003288 | LightGBM | 0.1570 | 0.1642 | 0.2195 | 0.2482 |
| MAC003288 | Ridge Regression | 0.2140 | 0.1852 | 0.2505 | 0.2743 |
| MAC003288 | Seasonal Naive | 0.1820 | 0.2090 | 0.2312 | 0.3262 |
| Portfolio | LightGBM | 0.6164 | 0.5644 | 0.7632 | 0.9073 |
| Portfolio | Ridge Regression | 1.1748 | 0.7537 | 1.4034 | 1.0313 |
| Portfolio | Seasonal Naive | 0.8450 | 0.6632 | 0.9939 | 0.9612 |

### Replay 2013-02-03

| household | method | mae_kw / event_window | mae_kw / full_day | rmse_kw / event_window | rmse_kw / full_day |
| --- | --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 0.2956 | 0.2505 | 0.3371 | 0.3048 |
| MAC000143 | Ridge Regression | 0.2751 | 0.2072 | 0.3207 | 0.2584 |
| MAC000143 | Seasonal Naive | 0.2203 | 0.1303 | 0.3409 | 0.2280 |
| MAC001391 | LightGBM | 0.1030 | 0.0610 | 0.1226 | 0.0788 |
| MAC001391 | Ridge Regression | 0.0456 | 0.0776 | 0.0508 | 0.1014 |
| MAC001391 | Seasonal Naive | 0.0587 | 0.0516 | 0.0880 | 0.0722 |
| MAC001395 | LightGBM | 0.1978 | 0.4134 | 0.2381 | 0.7122 |
| MAC001395 | Ridge Regression | 0.3370 | 0.4446 | 0.4097 | 0.6627 |
| MAC001395 | Seasonal Naive | 0.2160 | 0.4254 | 0.2724 | 0.7325 |
| MAC001534 | LightGBM | 0.0992 | 0.2672 | 0.1118 | 0.3135 |
| MAC001534 | Ridge Regression | 0.0865 | 0.1597 | 0.1083 | 0.2015 |
| MAC001534 | Seasonal Naive | 0.1603 | 0.3981 | 0.1748 | 0.5605 |
| MAC003288 | LightGBM | 0.2270 | 0.1518 | 0.3113 | 0.2330 |
| MAC003288 | Ridge Regression | 0.2432 | 0.1755 | 0.3545 | 0.2517 |
| MAC003288 | Seasonal Naive | 0.3403 | 0.2129 | 0.4676 | 0.3549 |
| Portfolio | LightGBM | 0.2944 | 0.6246 | 0.3326 | 0.7984 |
| Portfolio | Ridge Regression | 0.3527 | 0.6971 | 0.4581 | 0.9170 |
| Portfolio | Seasonal Naive | 0.6710 | 0.7957 | 0.7238 | 0.9985 |

### Replay 2013-03-19

| household | method | mae_kw / event_window | mae_kw / full_day | rmse_kw / event_window | rmse_kw / full_day |
| --- | --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 0.1499 | 0.1252 | 0.1506 | 0.1871 |
| MAC000143 | Ridge Regression | 0.2747 | 0.1371 | 0.2833 | 0.2311 |
| MAC000143 | Seasonal Naive | 0.2260 | 0.1961 | 0.2262 | 0.2813 |
| MAC001391 | LightGBM | 0.1390 | 0.0562 | 0.1415 | 0.0801 |
| MAC001391 | Ridge Regression | 0.0605 | 0.0528 | 0.0606 | 0.0734 |
| MAC001391 | Seasonal Naive | 0.0260 | 0.0709 | 0.0341 | 0.1202 |
| MAC001395 | LightGBM | 0.6986 | 0.3458 | 0.7275 | 0.5474 |
| MAC001395 | Ridge Regression | 0.6758 | 0.4410 | 0.7032 | 0.5918 |
| MAC001395 | Seasonal Naive | 0.1260 | 0.4875 | 0.1310 | 0.8036 |
| MAC001534 | LightGBM | 0.1962 | 0.2179 | 0.2216 | 0.2609 |
| MAC001534 | Ridge Regression | 0.1123 | 0.1933 | 0.1275 | 0.2338 |
| MAC001534 | Seasonal Naive | 0.2400 | 0.1855 | 0.2720 | 0.2290 |
| MAC003288 | LightGBM | 0.1571 | 0.0993 | 0.1615 | 0.1364 |
| MAC003288 | Ridge Regression | 0.0642 | 0.0865 | 0.0871 | 0.1170 |
| MAC003288 | Seasonal Naive | 0.3990 | 0.1789 | 0.5448 | 0.3145 |
| Portfolio | LightGBM | 0.3562 | 0.4440 | 0.3864 | 0.6339 |
| Portfolio | Ridge Regression | 0.7654 | 0.5734 | 0.7689 | 0.7530 |
| Portfolio | Seasonal Naive | 0.1550 | 0.5883 | 0.2150 | 0.8040 |

### Replay 2013-11-07

| household | method | mae_kw / event_window | mae_kw / full_day | rmse_kw / event_window | rmse_kw / full_day |
| --- | --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 0.0576 | 0.2037 | 0.0711 | 0.3157 |
| MAC000143 | Ridge Regression | 0.0391 | 0.1646 | 0.0396 | 0.2759 |
| MAC000143 | Seasonal Naive | 0.0490 | 0.1595 | 0.0490 | 0.3034 |
| MAC001391 | LightGBM | 0.0863 | 0.0736 | 0.0863 | 0.1660 |
| MAC001391 | Ridge Regression | 0.0868 | 0.0770 | 0.1003 | 0.1897 |
| MAC001391 | Seasonal Naive | 0.1280 | 0.0920 | 0.1782 | 0.1904 |
| MAC001395 | LightGBM | 0.4314 | 0.3799 | 0.4316 | 0.5558 |
| MAC001395 | Ridge Regression | 0.6573 | 0.3352 | 0.6638 | 0.5810 |
| MAC001395 | Seasonal Naive | 1.9780 | 0.4623 | 2.0942 | 0.8039 |
| MAC001534 | LightGBM | 0.1787 | 0.1434 | 0.2058 | 0.1677 |
| MAC001534 | Ridge Regression | 0.0657 | 0.1262 | 0.0735 | 0.1618 |
| MAC001534 | Seasonal Naive | 0.2060 | 0.1975 | 0.2225 | 0.3594 |
| MAC003288 | LightGBM | 0.2972 | 0.1370 | 0.2999 | 0.1668 |
| MAC003288 | Ridge Regression | 0.3520 | 0.1513 | 0.3640 | 0.1867 |
| MAC003288 | Seasonal Naive | 0.3320 | 0.1620 | 0.3918 | 0.2624 |
| Portfolio | LightGBM | 0.2559 | 0.4730 | 0.3104 | 0.7511 |
| Portfolio | Ridge Regression | 0.2778 | 0.5034 | 0.2812 | 0.8388 |
| Portfolio | Seasonal Naive | 1.7270 | 0.6161 | 1.8428 | 1.0724 |

### Replay 2013-12-06

| household | method | mae_kw / event_window | mae_kw / full_day | rmse_kw / event_window | rmse_kw / full_day |
| --- | --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 0.0695 | 0.1448 | 0.0899 | 0.2605 |
| MAC000143 | Ridge Regression | 0.1184 | 0.1397 | 0.1199 | 0.2367 |
| MAC000143 | Seasonal Naive | 0.1267 | 0.1641 | 0.1288 | 0.2745 |
| MAC001391 | LightGBM | 0.2150 | 0.0987 | 0.2170 | 0.1293 |
| MAC001391 | Ridge Regression | 0.2854 | 0.0844 | 0.2883 | 0.1159 |
| MAC001391 | Seasonal Naive | 0.3180 | 0.1135 | 0.3212 | 0.2075 |
| MAC001395 | LightGBM | 0.6072 | 0.3729 | 0.8759 | 0.6433 |
| MAC001395 | Ridge Regression | 0.6164 | 0.4104 | 0.9955 | 0.6488 |
| MAC001395 | Seasonal Naive | 1.0040 | 0.4975 | 1.2610 | 0.8135 |
| MAC001534 | LightGBM | 0.2266 | 0.1668 | 0.2714 | 0.2253 |
| MAC001534 | Ridge Regression | 0.1342 | 0.2010 | 0.1432 | 0.2614 |
| MAC001534 | Seasonal Naive | 0.1620 | 0.2883 | 0.1742 | 0.4400 |
| MAC003288 | LightGBM | 0.3305 | 0.5425 | 0.3456 | 0.9575 |
| MAC003288 | Ridge Regression | 0.3840 | 0.5361 | 0.4097 | 0.9020 |
| MAC003288 | Seasonal Naive | 0.4000 | 0.5580 | 0.4311 | 0.8950 |
| Portfolio | LightGBM | 0.5313 | 0.7960 | 0.6854 | 1.2146 |
| Portfolio | Ridge Regression | 1.1895 | 0.9093 | 1.2599 | 1.2380 |
| Portfolio | Seasonal Naive | 1.2187 | 0.9587 | 1.4109 | 1.3541 |
