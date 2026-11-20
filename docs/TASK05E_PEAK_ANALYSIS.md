# Task 05E — Forecast UI simplification and peak error analysis

18 November 2026. Branch `codex/task05e-forecast-ui-peak-analysis`, based on Task 05D. This task changes presentation and adds read-only diagnostics. No saved model is retrained or activated, no fingerprints or cloud artifacts are changed, and no migration, Task 06, commit, merge or deployment is performed.

## UI changes

Forecast Model Development opens Event-aligned forecasting directly. The workflow selector and visible Benchmark development path are removed. Legacy benchmark code remains available for isolated regression tests; its data, saved models and records remain intact. The other two Simulation Lab tabs are unchanged. All five NESO events and replay mappings are preserved.

Immediately selecting an event shows a four-row date table with exact saved inclusive calendar bounds and the count of complete daily origins shared by all five households. A household expander shows configured bounds, first/last actually usable dates, usable origin counts and half-hour sample counts. Dates come from the saved Task 05D request/model metadata; admitted origins are reconstructed from the pinned dataset using its unchanged feature/target admission logic and checked against saved per-household counts. First/last usable dates can contain excluded days between them, so they are not presented as continuous coverage. Historical holdout and the final event day are explicitly distinct.

One Full-Day Forecast chart shows the selected household or Portfolio (default), with Actual, LightGBM, Ridge and Seasonal Naive, legend selection and zoom. Amber shading marks the exact existing replay event window. Curves retain 48 half-hour interval starts in GMT, with average demand in kW. A single full-day RMSE chart remains; the three-mode comparison control is removed. All full-day, event-window and broader-holdout MAE/RMSE and sample counts remain in an expandable evaluation table and downloadable metrics. Validation portfolio RMSE still determines recommendations; activation remains explicit and event-specific.

Peak comparison shows the selected series and all three methods; an expander and CSV expose all six series. Provenance/version display remains available. Run Event Models retains exact saved-result-first behavior and automatic persistence for genuinely missing requests; this task did not create any such requests.

## Exact persisted date ranges

Usable Days below means the actual intersection of complete admitted daily origins across all five homes, not the nominal calendar length or the minimum household count. Event Forecast has one complete measured day for every household. The household appendix gives exact per-home admitted endpoints and sample counts.

| Dataset | Start Date | End Date | Usable Days | event |
| --- | --- | --- | --- | --- |
| Training | 2012-11-21 | 2013-02-18 | 83 | 2025-03-18 |
| Validation | 2013-02-19 | 2013-03-04 | 14 | 2025-03-18 |
| Testing / Holdout | 2013-03-05 | 2013-03-18 | 11 | 2025-03-18 |
| Event Forecast | 2013-03-19 | 2013-03-19 | 1 | 2025-03-18 |
| Training | 2013-07-12 | 2013-10-09 | 84 | 2025-11-06 |
| Validation | 2013-10-10 | 2013-10-23 | 14 | 2025-11-06 |
| Testing / Holdout | 2013-10-24 | 2013-11-06 | 12 | 2025-11-06 |
| Event Forecast | 2013-11-07 | 2013-11-07 | 1 | 2025-11-06 |
| Training | 2013-08-10 | 2013-11-07 | 85 | 2023-12-01 |
| Validation | 2013-11-08 | 2013-11-21 | 12 | 2023-12-01 |
| Testing / Holdout | 2013-11-22 | 2013-12-05 | 12 | 2023-12-01 |
| Event Forecast | 2013-12-06 | 2013-12-06 | 1 | 2023-12-01 |
| Training | 2012-09-17 | 2012-12-15 | 65 | 2026-01-11 |
| Validation | 2012-12-16 | 2012-12-29 | 11 | 2026-01-11 |
| Testing / Holdout | 2012-12-30 | 2013-01-12 | 12 | 2026-01-11 |
| Event Forecast | 2013-01-13 | 2013-01-13 | 1 | 2026-01-11 |
| Training | 2012-10-08 | 2013-01-05 | 74 | 2025-02-02 |
| Validation | 2013-01-06 | 2013-01-19 | 11 | 2025-02-02 |
| Testing / Holdout | 2013-01-20 | 2013-02-02 | 14 | 2025-02-02 |
| Event Forecast | 2013-02-03 | 2013-02-03 | 1 | 2025-02-02 |

## Peak definitions and information boundaries

- Peak magnitude error = predicted daily maximum minus actual daily maximum (kW); negative means underestimation. This compares each series' own maximum, not predicted demand at the actual peak time.
- Peak timing error = absolute clock-time difference between the two maxima (minutes), with the earliest interval chosen for ties. Resolution is 30 minutes; this is not a circular distance across midnight and does not measure instantaneous power spikes.
- High-demand interval MAE uses actual final-day intervals strictly exceeding the linear-interpolated 90th percentile of that household's admitted **training targets only**. Portfolio Q90 comes from coincident five-household training sums on common complete origins, not the sum of household quantiles. Thresholds differ legitimately by event/household. Zero qualifying intervals yields unavailable MAE and a zero sample count.

Thresholds were not a persisted Task 05D metric: they are now reproducibly derived from its pinned dataset, saved calendar bounds and checked admission counts, without changing any saved records. Validation, holdout and event-day targets never enter a threshold. Future actuals are used only for post-hoc evaluation, never for model selection, fitting or inputs.

## Evidence across the five event forecast days

These are 25 household-days and five portfolio-days per method, not evidence of universal bias on all households or future days. Mean peak bias and mean timing error are unweighted daily means. High-demand MAE below is pooled by the actual number of qualifying intervals (162 household intervals or 45 portfolio intervals per method); it can rank methods differently from an unweighted average of daily MAEs.

| Series | Method | Daily cases | Underestimated peaks | Mean peak bias kW | Mean timing error min | Pooled high-demand MAE kW | High-demand intervals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Households | LightGBM | 25 | 22 | -0.7809 | 261.6000 | 0.5917 | 162 |
| Households | Ridge Regression | 25 | 25 | -0.8261 | 336.0000 | 0.6081 | 162 |
| Households | Seasonal Naive | 25 | 11 | 0.1274 | 285.6000 | 0.5831 | 162 |
| Portfolio | LightGBM | 5 | 5 | -1.7941 | 366.0000 | 1.3416 | 45 |
| Portfolio | Ridge Regression | 5 | 5 | -2.2461 | 276.0000 | 1.5947 | 45 |
| Portfolio | Seasonal Naive | 5 | 3 | -0.6848 | 282.0000 | 1.3384 | 45 |

Ridge underestimated every household daily maximum and all five portfolio maxima. LightGBM underestimated 22/25 household maxima and all five portfolio maxima, with less negative average peak bias than Ridge. Seasonal Naive did not show consistent household underestimation (11/25; positive mean bias), although its peak timing and event errors can still be large. LightGBM has the lowest mean household timing error; Ridge has the lowest portfolio timing error. There is no method that wins every peak measure. Seasonal Naive is slightly best on pooled high-demand MAE here (households 0.5831 kW versus LightGBM 0.5917 and Ridge 0.6081; portfolio 1.3384 versus 1.3416 and 1.5947). These diagnostic comparisons do not change recommendations or activation.

The saved Ridge/LightGBM point forecasts and their limited previous-day/week input profiles can smooth unpredictable appliance-driven demand changes. Squared-error objectives favor conditional means, which need not preserve daily maxima. This is a plausible explanation, not a causal result established by five days. Seasonal Naive copies a previous measured shape, so it can preserve a sharp peak magnitude while placing it at the wrong time.

## Event relevance and battery implications

None of the five portfolio actual daily maxima occurs inside its NESO replay window. Therefore daily maximum underestimation alone does not establish event-period battery insufficiency. We separately measure **positive event underforecast energy**: sum(max(actual − forecast, 0) × 0.5 hours) across event intervals. It does not cancel underforecast with overforecast and is not a net energy error, reserve prescription, dispatch result or commitment feasibility calculation.

| event | method | peak_magnitude_error_kw | peak_timing_error_minutes | high_demand_mae_kw | event_underforecast_kwh | actual_peak_in_event |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-03-18 | LightGBM | -0.7585 | 30.0000 | 0.3421 | 0.1499 | False |
| 2025-03-18 | Ridge Regression | -1.0256 | 30.0000 | 0.5516 | 0.2747 | False |
| 2025-03-18 | Seasonal Naive | -0.5660 | 90.0000 | 0.4356 | 0.2260 | False |
| 2025-03-18 | LightGBM | -0.1549 | 60.0000 | 0.0900 | 0.0000 | False |
| 2025-03-18 | Ridge Regression | -0.2235 | 60.0000 | 0.1366 | 0.0000 | False |
| 2025-03-18 | Seasonal Naive | 0.3700 | 60.0000 | 0.3000 | 0.0260 | False |
| 2025-03-18 | LightGBM | -1.0500 | 90.0000 | 1.0617 | 0.6986 | False |
| 2025-03-18 | Ridge Regression | -0.3520 | 60.0000 | 1.1025 | 0.6758 | False |
| 2025-03-18 | Seasonal Naive | 0.8540 | 60.0000 | 0.7815 | 0.1260 | False |
| 2025-03-18 | LightGBM | -0.1988 | 690.0000 | 0.6008 | 0.0000 | False |
| 2025-03-18 | Ridge Regression | -0.3137 | 990.0000 | 0.6199 | 0.0259 | False |
| 2025-03-18 | Seasonal Naive | 0.0340 | 720.0000 | 0.6520 | 0.0560 | False |
| 2025-03-18 | LightGBM | 0.0126 | 420.0000 | 0.4154 | 0.0000 | False |
| 2025-03-18 | Ridge Regression | -0.0590 | 420.0000 | 0.1327 | 0.0000 | False |
| 2025-03-18 | Seasonal Naive | 1.0320 | 210.0000 | 0.4700 | 0.0000 | False |
| 2025-03-18 | LightGBM | -0.4867 | 630.0000 | 0.8783 | 0.3562 | False |
| 2025-03-18 | Ridge Regression | -0.5932 | 480.0000 | 1.2634 | 0.7654 | False |
| 2025-03-18 | Seasonal Naive | 0.3300 | 480.0000 | 0.8472 | 0.0030 | False |
| 2025-11-06 | LightGBM | -1.2706 | 90.0000 | 0.3428 | 0.0576 | False |
| 2025-11-06 | Ridge Regression | -1.2064 | 30.0000 | 0.3005 | 0.0227 | False |
| 2025-11-06 | Seasonal Naive | -0.2760 | 300.0000 | 0.2488 | 0.0250 | False |
| 2025-11-06 | LightGBM | -0.8648 | 30.0000 | 0.2206 | 0.0428 | False |
| 2025-11-06 | Ridge Regression | -1.0255 | 180.0000 | 0.2458 | 0.0868 | False |
| 2025-11-06 | Seasonal Naive | -0.9080 | 60.0000 | 0.2622 | 0.1260 | False |
| 2025-11-06 | LightGBM | -1.6655 | 330.0000 | 1.8208 | 0.0000 | False |
| 2025-11-06 | Ridge Regression | -1.1764 | 300.0000 | 1.8251 | 0.0000 | False |
| 2025-11-06 | Seasonal Naive | 0.4400 | 300.0000 | 1.8040 | 0.0000 | False |
| 2025-11-06 | LightGBM | 0.0882 | 0.0000 | unavailable | 0.0000 | False |
| 2025-11-06 | Ridge Regression | -0.0522 | 270.0000 | unavailable | 0.0000 | False |
| 2025-11-06 | Seasonal Naive | 1.2900 | 270.0000 | unavailable | 0.0000 | False |
| 2025-11-06 | LightGBM | -0.2797 | 90.0000 | 0.2622 | 0.2972 | True |
| 2025-11-06 | Ridge Regression | -0.2967 | 600.0000 | 0.3016 | 0.3520 | True |
| 2025-11-06 | Seasonal Naive | 0.5100 | 600.0000 | 0.4233 | 0.3320 | True |
| 2025-11-06 | LightGBM | -3.6101 | 30.0000 | 1.6356 | 0.0000 | False |
| 2025-11-06 | Ridge Regression | -3.8044 | 60.0000 | 1.9272 | 0.0000 | False |
| 2025-11-06 | Seasonal Naive | -1.7560 | 60.0000 | 1.7024 | 0.0000 | False |
| 2023-12-01 | LightGBM | -0.8656 | 330.0000 | 0.2485 | 0.0310 | False |
| 2023-12-01 | Ridge Regression | -1.1090 | 30.0000 | 0.2105 | 0.1776 | False |
| 2023-12-01 | Seasonal Naive | -0.8540 | 420.0000 | 0.2521 | 0.1900 | False |
| 2023-12-01 | LightGBM | 0.0610 | 60.0000 | 0.1861 | 0.3225 | True |
| 2023-12-01 | Ridge Regression | -0.1453 | 60.0000 | 0.2042 | 0.4281 | True |
| 2023-12-01 | Seasonal Naive | 0.7220 | 60.0000 | 0.2562 | 0.4770 | True |
| 2023-12-01 | LightGBM | -1.2974 | 690.0000 | 1.5398 | 0.7436 | False |
| 2023-12-01 | Ridge Regression | -1.5566 | 570.0000 | 1.5363 | 0.8600 | False |
| 2023-12-01 | Seasonal Naive | -0.4880 | 360.0000 | 1.6417 | 1.1470 | False |
| 2023-12-01 | LightGBM | -0.2267 | 150.0000 | 0.3483 | 0.0000 | False |
| 2023-12-01 | Ridge Regression | -0.2893 | 210.0000 | 0.5989 | 0.1050 | False |
| 2023-12-01 | Seasonal Naive | 0.8780 | 210.0000 | 0.8480 | 0.1350 | False |
| 2023-12-01 | LightGBM | -2.9163 | 270.0000 | 1.1061 | 0.3711 | False |
| 2023-12-01 | Ridge Regression | -3.0079 | 510.0000 | 1.0840 | 0.4752 | False |
| 2023-12-01 | Seasonal Naive | -1.6600 | 510.0000 | 1.0899 | 0.4730 | False |
| 2023-12-01 | LightGBM | -1.5619 | 390.0000 | 1.4984 | 0.7800 | False |
| 2023-12-01 | Ridge Regression | -2.8399 | 270.0000 | 1.7109 | 1.7843 | False |
| 2023-12-01 | Seasonal Naive | -1.3100 | 540.0000 | 1.7252 | 1.8280 | False |
| 2026-01-11 | LightGBM | -1.0385 | 510.0000 | 0.3975 | 0.0385 | False |
| 2026-01-11 | Ridge Regression | -1.3193 | 630.0000 | 0.5224 | 0.3885 | False |
| 2026-01-11 | Seasonal Naive | -0.1280 | 630.0000 | 0.6886 | 1.1160 | False |
| 2026-01-11 | LightGBM | -0.1345 | 210.0000 | 0.0968 | 0.2319 | False |
| 2026-01-11 | Ridge Regression | -0.1496 | 150.0000 | 0.0963 | 0.2832 | False |
| 2026-01-11 | Seasonal Naive | -0.0440 | 210.0000 | 0.1287 | 0.3530 | False |
| 2026-01-11 | LightGBM | -3.1371 | 90.0000 | 1.5743 | 0.7650 | False |
| 2026-01-11 | Ridge Regression | -3.0759 | 390.0000 | 1.7650 | 0.9957 | False |
| 2026-01-11 | Seasonal Naive | -1.3380 | 450.0000 | 1.0860 | 0.5410 | False |
| 2026-01-11 | LightGBM | -0.6699 | 180.0000 | 0.4949 | 0.0613 | False |
| 2026-01-11 | Ridge Regression | -0.8207 | 300.0000 | 0.4694 | 0.3844 | False |
| 2026-01-11 | Seasonal Naive | 1.6880 | 300.0000 | 0.4030 | 0.2230 | False |
| 2026-01-11 | LightGBM | -0.4616 | 90.0000 | 0.3746 | 0.2577 | False |
| 2026-01-11 | Ridge Regression | -0.3453 | 240.0000 | 0.4429 | 0.4059 | False |
| 2026-01-11 | Seasonal Naive | 0.3140 | 330.0000 | 0.5287 | 0.3020 | False |
| 2026-01-11 | LightGBM | -2.0968 | 120.0000 | 1.0764 | 0.6525 | False |
| 2026-01-11 | Ridge Regression | -2.9149 | 60.0000 | 1.3921 | 2.3497 | False |
| 2026-01-11 | Seasonal Naive | -0.6920 | 330.0000 | 0.9292 | 1.5220 | False |
| 2025-02-02 | LightGBM | -0.1050 | 810.0000 | 0.5548 | 0.0293 | False |
| 2025-02-02 | Ridge Regression | -0.1824 | 660.0000 | 0.4943 | 0.0000 | False |
| 2025-02-02 | Seasonal Naive | 0.6940 | 0.0000 | 0.5700 | 0.0010 | False |
| 2025-02-02 | LightGBM | -0.0536 | 0.0000 | 0.0471 | 0.0000 | False |
| 2025-02-02 | Ridge Regression | -0.1925 | 210.0000 | 0.0875 | 0.0233 | False |
| 2025-02-02 | Seasonal Naive | -0.0820 | 150.0000 | 0.1133 | 0.0490 | False |
| 2025-02-02 | LightGBM | -1.8983 | 90.0000 | 1.6509 | 0.5797 | False |
| 2025-02-02 | Ridge Regression | -1.7446 | 330.0000 | 1.4214 | 0.2221 | False |
| 2025-02-02 | Seasonal Naive | -0.6700 | 330.0000 | 0.9693 | 0.3950 | False |
| 2025-02-02 | LightGBM | -0.1606 | 600.0000 | 0.2825 | 0.1010 | False |
| 2025-02-02 | Ridge Regression | -0.3233 | 570.0000 | 0.6433 | 0.2596 | False |
| 2025-02-02 | Seasonal Naive | 1.2720 | 480.0000 | 0.5940 | 0.2270 | False |
| 2025-02-02 | LightGBM | -0.4753 | 630.0000 | 0.3298 | 0.3737 | False |
| 2025-02-02 | Ridge Regression | -0.6596 | 600.0000 | 0.4121 | 0.5741 | False |
| 2025-02-02 | Seasonal Naive | 0.1000 | 30.0000 | 0.4723 | 0.7800 | False |
| 2025-02-02 | LightGBM | -1.2149 | 660.0000 | 1.7099 | 0.1413 | False |
| 2025-02-02 | Ridge Regression | -1.0779 | 510.0000 | 1.7280 | 0.1271 | False |
| 2025-02-02 | Seasonal Naive | 0.0040 | 0.0000 | 1.0870 | 0.9650 | False |

Observed portfolio positive underforecast ranges from 0 to 0.7800 kWh for LightGBM, 0 to 2.3497 kWh for Ridge, and 0 to 1.8280 kWh for Seasonal Naive across these windows. All three are zero on the November event despite substantial daily peak underestimation outside the event. Conditional on a future optimiser relying on these forecasts, overlapping errors could understate battery power/energy needs or demand uncertainty, so they merit explicit reserve/uncertainty treatment before commitment. Material feasibility cannot be concluded without battery state, headroom, network constraints and an optimisation run; Task 06 was not implemented.

## Improvement options — not implemented

1. Retain Seasonal Naive as a peak-risk comparator and examine interval-specific residuals rather than choosing from full-day RMSE alone. Choose any changed selection rule on chronological validation, never the five final days reported here.
2. Test quantile forecasts or peak-weighted objectives as separate future model versions. Evaluate calibration, underforecast energy, mean demand accuracy and overforecast penalties; stronger predicted peaks can introduce false alarms and do not guarantee better dispatch.
3. Investigate additional signals available before the forecast origin, such as known calendar patterns, weather forecasts and reliable appliance/occupancy schedules. Future observed weather or same-day actual load would leak information into a day-ahead forecast. Availability and acquisition need review first.
4. Consider calibrated uncertainty bands or reserves in later optimisation work. Backtest with longer rolling holdouts, more events and households before deciding operating margins. No reserve quantity or dispatch is proposed as a verified result here.

## Persistence and verification

The full regression suite passed **313 tests in 209.89 seconds**. A pandas timestamp-sort deprecation found during that run was corrected explicitly; the final targeted peak/UI run passed **9 tests** with no warnings, including the final exact-date assertions. Ruff check/format and `ty check src scripts` pass. The layered GMT chart passes Vega-Lite schema validation.

A fresh-cache live check restored all 15 bundles with zero training, uploads or SQL mutations (146 SELECTs); all **27 cloud tables** matched the complete before snapshot. All protected model/feature/storage/migration hashes and 19 preserved source/data hashes match. A cloud-backed local Streamlit server enforced the same read-only/training guards: all five events restored two charts, each Run Event Models reported 3 reused / 0 trained, and both other tabs remained available. Expanded date tables matched all saved-metadata export rows exactly; each curve had 192 rows (48 steps × four series), evaluations 54 rows and all-series peak diagnostics 18 rows per event. Model versions/timestamps and activation state were unchanged, and server logs had no exceptions or deprecation warnings. The temporary server was stopped. No schema migration was needed. All five saved requests restore from dedicated `batteryflex-mvp` Turso/R2, with fitting, R2 uploads and non-SELECT SQL blocked during the cold-cache acceptance check. Every table row is snapshotted before and compared afterward; protected estimator, feature, persistence and migration code hashes and all 19 preserved source/data hashes are checked. Existing SHA-256 object reads remain in force. No source acquisition or previous-MVP access occurs.

Peak exports are local derived diagnostics; they do not overwrite or append saved cloud evaluation metrics. Reproduce them without training:

```powershell
.venv/Scripts/python.exe scripts/analyse_event_peaks.py --output outputs/event-peaks
```

Evidence files: `outputs/task05e/peak-diagnostics.csv` (90 rows), `dataset-ranges.csv` (20), `household-ranges.csv` (75), `cloud-before.json`, `cloud-report.json`, and `ui-verification/`. The exporter fails if exact saved forecasts are missing and never trains, migrates or activates. Its live read-only verification reproduced all 90 diagnostic rows exactly.

Limitations: a small selected sample; 30-minute averages hide instantaneous peaks; ties use an explicit earliest-time convention; peak timing can be unstable for nearly equal peaks; missing historical days are excluded rather than filled; high-demand intervals may be absent on some days. No new models, features or losses were implemented.

## Household-specific admitted date ranges

| Dataset | Household | Configured Start | Configured End | First Usable Date | Last Usable Date | Usable Days | Samples | event |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Training | MAC001391 | 2012-11-21 | 2013-02-18 | 2012-11-21 | 2013-02-18 | 86 | 4128 | 2025-03-18 |
| Training | MAC003288 | 2012-11-21 | 2013-02-18 | 2012-11-21 | 2013-02-18 | 86 | 4128 | 2025-03-18 |
| Training | MAC000143 | 2012-11-21 | 2013-02-18 | 2012-11-21 | 2013-02-18 | 86 | 4128 | 2025-03-18 |
| Training | MAC001534 | 2012-11-21 | 2013-02-18 | 2012-11-21 | 2013-02-18 | 86 | 4128 | 2025-03-18 |
| Training | MAC001395 | 2012-11-21 | 2013-02-18 | 2012-11-21 | 2013-02-18 | 83 | 3984 | 2025-03-18 |
| Validation | MAC001391 | 2013-02-19 | 2013-03-04 | 2013-02-19 | 2013-03-04 | 14 | 672 | 2025-03-18 |
| Validation | MAC003288 | 2013-02-19 | 2013-03-04 | 2013-02-19 | 2013-03-04 | 14 | 672 | 2025-03-18 |
| Validation | MAC000143 | 2013-02-19 | 2013-03-04 | 2013-02-19 | 2013-03-04 | 14 | 672 | 2025-03-18 |
| Validation | MAC001534 | 2013-02-19 | 2013-03-04 | 2013-02-19 | 2013-03-04 | 14 | 672 | 2025-03-18 |
| Validation | MAC001395 | 2013-02-19 | 2013-03-04 | 2013-02-19 | 2013-03-04 | 14 | 672 | 2025-03-18 |
| Testing / Holdout | MAC001391 | 2013-03-05 | 2013-03-18 | 2013-03-05 | 2013-03-18 | 14 | 672 | 2025-03-18 |
| Testing / Holdout | MAC003288 | 2013-03-05 | 2013-03-18 | 2013-03-05 | 2013-03-18 | 14 | 672 | 2025-03-18 |
| Testing / Holdout | MAC000143 | 2013-03-05 | 2013-03-18 | 2013-03-05 | 2013-03-18 | 14 | 672 | 2025-03-18 |
| Testing / Holdout | MAC001534 | 2013-03-05 | 2013-03-18 | 2013-03-05 | 2013-03-18 | 11 | 528 | 2025-03-18 |
| Testing / Holdout | MAC001395 | 2013-03-05 | 2013-03-18 | 2013-03-05 | 2013-03-18 | 14 | 672 | 2025-03-18 |
| Training | MAC001391 | 2013-07-12 | 2013-10-09 | 2013-07-12 | 2013-10-09 | 90 | 4320 | 2025-11-06 |
| Training | MAC003288 | 2013-07-12 | 2013-10-09 | 2013-07-12 | 2013-10-09 | 87 | 4176 | 2025-11-06 |
| Training | MAC000143 | 2013-07-12 | 2013-10-09 | 2013-07-12 | 2013-10-09 | 90 | 4320 | 2025-11-06 |
| Training | MAC001534 | 2013-07-12 | 2013-10-09 | 2013-07-12 | 2013-10-09 | 87 | 4176 | 2025-11-06 |
| Training | MAC001395 | 2013-07-12 | 2013-10-09 | 2013-07-12 | 2013-10-09 | 90 | 4320 | 2025-11-06 |
| Validation | MAC001391 | 2013-10-10 | 2013-10-23 | 2013-10-10 | 2013-10-23 | 14 | 672 | 2025-11-06 |
| Validation | MAC003288 | 2013-10-10 | 2013-10-23 | 2013-10-10 | 2013-10-23 | 14 | 672 | 2025-11-06 |
| Validation | MAC000143 | 2013-10-10 | 2013-10-23 | 2013-10-10 | 2013-10-23 | 14 | 672 | 2025-11-06 |
| Validation | MAC001534 | 2013-10-10 | 2013-10-23 | 2013-10-10 | 2013-10-23 | 14 | 672 | 2025-11-06 |
| Validation | MAC001395 | 2013-10-10 | 2013-10-23 | 2013-10-10 | 2013-10-23 | 14 | 672 | 2025-11-06 |
| Testing / Holdout | MAC001391 | 2013-10-24 | 2013-11-06 | 2013-10-24 | 2013-11-04 | 12 | 576 | 2025-11-06 |
| Testing / Holdout | MAC003288 | 2013-10-24 | 2013-11-06 | 2013-10-24 | 2013-11-06 | 14 | 672 | 2025-11-06 |
| Testing / Holdout | MAC000143 | 2013-10-24 | 2013-11-06 | 2013-10-24 | 2013-11-06 | 14 | 672 | 2025-11-06 |
| Testing / Holdout | MAC001534 | 2013-10-24 | 2013-11-06 | 2013-10-24 | 2013-11-06 | 14 | 672 | 2025-11-06 |
| Testing / Holdout | MAC001395 | 2013-10-24 | 2013-11-06 | 2013-10-24 | 2013-11-06 | 14 | 672 | 2025-11-06 |
| Training | MAC001391 | 2013-08-10 | 2013-11-07 | 2013-08-10 | 2013-11-07 | 88 | 4224 | 2023-12-01 |
| Training | MAC003288 | 2013-08-10 | 2013-11-07 | 2013-08-10 | 2013-11-07 | 90 | 4320 | 2023-12-01 |
| Training | MAC000143 | 2013-08-10 | 2013-11-07 | 2013-08-10 | 2013-11-07 | 90 | 4320 | 2023-12-01 |
| Training | MAC001534 | 2013-08-10 | 2013-11-07 | 2013-08-10 | 2013-11-07 | 87 | 4176 | 2023-12-01 |
| Training | MAC001395 | 2013-08-10 | 2013-11-07 | 2013-08-10 | 2013-11-07 | 90 | 4320 | 2023-12-01 |
| Validation | MAC001391 | 2013-11-08 | 2013-11-21 | 2013-11-08 | 2013-11-21 | 13 | 624 | 2023-12-01 |
| Validation | MAC003288 | 2013-11-08 | 2013-11-21 | 2013-11-08 | 2013-11-21 | 14 | 672 | 2023-12-01 |
| Validation | MAC000143 | 2013-11-08 | 2013-11-21 | 2013-11-08 | 2013-11-20 | 13 | 624 | 2023-12-01 |
| Validation | MAC001534 | 2013-11-08 | 2013-11-21 | 2013-11-08 | 2013-11-21 | 14 | 672 | 2023-12-01 |
| Validation | MAC001395 | 2013-11-08 | 2013-11-21 | 2013-11-08 | 2013-11-21 | 14 | 672 | 2023-12-01 |
| Testing / Holdout | MAC001391 | 2013-11-22 | 2013-12-05 | 2013-11-22 | 2013-12-05 | 14 | 672 | 2023-12-01 |
| Testing / Holdout | MAC003288 | 2013-11-22 | 2013-12-05 | 2013-11-22 | 2013-12-05 | 14 | 672 | 2023-12-01 |
| Testing / Holdout | MAC000143 | 2013-11-22 | 2013-12-05 | 2013-11-23 | 2013-12-05 | 12 | 576 | 2023-12-01 |
| Testing / Holdout | MAC001534 | 2013-11-22 | 2013-12-05 | 2013-11-22 | 2013-12-05 | 14 | 672 | 2023-12-01 |
| Testing / Holdout | MAC001395 | 2013-11-22 | 2013-12-05 | 2013-11-22 | 2013-12-05 | 14 | 672 | 2023-12-01 |
| Training | MAC001391 | 2012-09-17 | 2012-12-15 | 2012-09-17 | 2012-12-15 | 79 | 3792 | 2026-01-11 |
| Training | MAC003288 | 2012-09-17 | 2012-12-15 | 2012-09-29 | 2012-12-15 | 72 | 3456 | 2026-01-11 |
| Training | MAC000143 | 2012-09-17 | 2012-12-15 | 2012-09-17 | 2012-12-15 | 79 | 3792 | 2026-01-11 |
| Training | MAC001534 | 2012-09-17 | 2012-12-15 | 2012-09-17 | 2012-12-15 | 77 | 3696 | 2026-01-11 |
| Training | MAC001395 | 2012-09-17 | 2012-12-15 | 2012-09-17 | 2012-12-15 | 79 | 3792 | 2026-01-11 |
| Validation | MAC001391 | 2012-12-16 | 2012-12-29 | 2012-12-16 | 2012-12-29 | 11 | 528 | 2026-01-11 |
| Validation | MAC003288 | 2012-12-16 | 2012-12-29 | 2012-12-16 | 2012-12-29 | 11 | 528 | 2026-01-11 |
| Validation | MAC000143 | 2012-12-16 | 2012-12-29 | 2012-12-16 | 2012-12-29 | 11 | 528 | 2026-01-11 |
| Validation | MAC001534 | 2012-12-16 | 2012-12-29 | 2012-12-16 | 2012-12-29 | 11 | 528 | 2026-01-11 |
| Validation | MAC001395 | 2012-12-16 | 2012-12-29 | 2012-12-16 | 2012-12-29 | 11 | 528 | 2026-01-11 |
| Testing / Holdout | MAC001391 | 2012-12-30 | 2013-01-12 | 2012-12-30 | 2013-01-12 | 14 | 672 | 2026-01-11 |
| Testing / Holdout | MAC003288 | 2012-12-30 | 2013-01-12 | 2012-12-30 | 2013-01-12 | 14 | 672 | 2026-01-11 |
| Testing / Holdout | MAC000143 | 2012-12-30 | 2013-01-12 | 2012-12-30 | 2013-01-12 | 14 | 672 | 2026-01-11 |
| Testing / Holdout | MAC001534 | 2012-12-30 | 2013-01-12 | 2012-12-30 | 2013-01-12 | 14 | 672 | 2026-01-11 |
| Testing / Holdout | MAC001395 | 2012-12-30 | 2013-01-12 | 2012-12-30 | 2013-01-12 | 12 | 576 | 2026-01-11 |
| Training | MAC001391 | 2012-10-08 | 2013-01-05 | 2012-10-08 | 2013-01-05 | 79 | 3792 | 2025-02-02 |
| Training | MAC003288 | 2012-10-08 | 2013-01-05 | 2012-10-08 | 2013-01-05 | 81 | 3888 | 2025-02-02 |
| Training | MAC000143 | 2012-10-08 | 2013-01-05 | 2012-10-08 | 2013-01-05 | 81 | 3888 | 2025-02-02 |
| Training | MAC001534 | 2012-10-08 | 2013-01-05 | 2012-10-08 | 2013-01-05 | 78 | 3744 | 2025-02-02 |
| Training | MAC001395 | 2012-10-08 | 2013-01-05 | 2012-10-08 | 2013-01-05 | 79 | 3792 | 2025-02-02 |
| Validation | MAC001391 | 2013-01-06 | 2013-01-19 | 2013-01-06 | 2013-01-19 | 14 | 672 | 2025-02-02 |
| Validation | MAC003288 | 2013-01-06 | 2013-01-19 | 2013-01-06 | 2013-01-19 | 14 | 672 | 2025-02-02 |
| Validation | MAC000143 | 2013-01-06 | 2013-01-19 | 2013-01-06 | 2013-01-19 | 14 | 672 | 2025-02-02 |
| Validation | MAC001534 | 2013-01-06 | 2013-01-19 | 2013-01-06 | 2013-01-19 | 14 | 672 | 2025-02-02 |
| Validation | MAC001395 | 2013-01-06 | 2013-01-19 | 2013-01-06 | 2013-01-19 | 11 | 528 | 2025-02-02 |
| Testing / Holdout | MAC001391 | 2013-01-20 | 2013-02-02 | 2013-01-20 | 2013-02-02 | 14 | 672 | 2025-02-02 |
| Testing / Holdout | MAC003288 | 2013-01-20 | 2013-02-02 | 2013-01-20 | 2013-02-02 | 14 | 672 | 2025-02-02 |
| Testing / Holdout | MAC000143 | 2013-01-20 | 2013-02-02 | 2013-01-20 | 2013-02-02 | 14 | 672 | 2025-02-02 |
| Testing / Holdout | MAC001534 | 2013-01-20 | 2013-02-02 | 2013-01-20 | 2013-02-02 | 14 | 672 | 2025-02-02 |
| Testing / Holdout | MAC001395 | 2013-01-20 | 2013-02-02 | 2013-01-20 | 2013-02-02 | 14 | 672 | 2025-02-02 |

## All household and portfolio peak diagnostics

| household | method | actual_peak_kw | predicted_peak_kw | peak_magnitude_error_kw | actual_peak_time | predicted_peak_time | peak_timing_error_minutes | training_q90_kw | high_demand_intervals | high_demand_mae_kw | event_underforecast_kwh | event_intervals | actual_peak_in_event | event |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAC000143 | LightGBM | 1.7920 | 1.0335 | -0.7585 | 2013-03-19T19:30:00+00:00 | 2013-03-19T20:00:00+00:00 | 30.0000 | 0.8220 | 5 | 0.3421 | 0.1499 | 2 | False | 2025-03-18 |
| MAC000143 | Ridge Regression | 1.7920 | 0.7664 | -1.0256 | 2013-03-19T19:30:00+00:00 | 2013-03-19T20:00:00+00:00 | 30.0000 | 0.8220 | 5 | 0.5516 | 0.2747 | 2 | False | 2025-03-18 |
| MAC000143 | Seasonal Naive | 1.7920 | 1.2260 | -0.5660 | 2013-03-19T19:30:00+00:00 | 2013-03-19T21:00:00+00:00 | 90.0000 | 0.8220 | 5 | 0.4356 | 0.2260 | 2 | False | 2025-03-18 |
| MAC001391 | LightGBM | 0.5620 | 0.4071 | -0.1549 | 2013-03-19T20:00:00+00:00 | 2013-03-19T19:00:00+00:00 | 60.0000 | 0.3460 | 3 | 0.0900 | 0.0000 | 2 | False | 2025-03-18 |
| MAC001391 | Ridge Regression | 0.5620 | 0.3385 | -0.2235 | 2013-03-19T20:00:00+00:00 | 2013-03-19T19:00:00+00:00 | 60.0000 | 0.3460 | 3 | 0.1366 | 0.0000 | 2 | False | 2025-03-18 |
| MAC001391 | Seasonal Naive | 0.5620 | 0.9320 | 0.3700 | 2013-03-19T20:00:00+00:00 | 2013-03-19T19:00:00+00:00 | 60.0000 | 0.3460 | 3 | 0.3000 | 0.0260 | 2 | False | 2025-03-18 |
| MAC001395 | LightGBM | 3.4040 | 2.3540 | -1.0500 | 2013-03-19T08:00:00+00:00 | 2013-03-19T06:30:00+00:00 | 90.0000 | 2.3640 | 4 | 1.0617 | 0.6986 | 2 | False | 2025-03-18 |
| MAC001395 | Ridge Regression | 3.4040 | 3.0520 | -0.3520 | 2013-03-19T08:00:00+00:00 | 2013-03-19T07:00:00+00:00 | 60.0000 | 2.3640 | 4 | 1.1025 | 0.6758 | 2 | False | 2025-03-18 |
| MAC001395 | Seasonal Naive | 3.4040 | 4.2580 | 0.8540 | 2013-03-19T08:00:00+00:00 | 2013-03-19T07:00:00+00:00 | 60.0000 | 2.3640 | 4 | 0.7815 | 0.1260 | 2 | False | 2025-03-18 |
| MAC001534 | LightGBM | 1.1860 | 0.9872 | -0.1988 | 2013-03-19T07:00:00+00:00 | 2013-03-19T18:30:00+00:00 | 690.0000 | 1.1686 | 1 | 0.6008 | 0.0000 | 2 | False | 2025-03-18 |
| MAC001534 | Ridge Regression | 1.1860 | 0.8723 | -0.3137 | 2013-03-19T07:00:00+00:00 | 2013-03-19T23:30:00+00:00 | 990.0000 | 1.1686 | 1 | 0.6199 | 0.0259 | 2 | False | 2025-03-18 |
| MAC001534 | Seasonal Naive | 1.1860 | 1.2200 | 0.0340 | 2013-03-19T07:00:00+00:00 | 2013-03-19T19:00:00+00:00 | 720.0000 | 1.1686 | 1 | 0.6520 | 0.0560 | 2 | False | 2025-03-18 |
| MAC003288 | LightGBM | 0.7160 | 0.7286 | 0.0126 | 2013-03-19T11:30:00+00:00 | 2013-03-19T18:30:00+00:00 | 420.0000 | 0.6960 | 1 | 0.4154 | 0.0000 | 2 | False | 2025-03-18 |
| MAC003288 | Ridge Regression | 0.7160 | 0.6570 | -0.0590 | 2013-03-19T11:30:00+00:00 | 2013-03-19T18:30:00+00:00 | 420.0000 | 0.6960 | 1 | 0.1327 | 0.0000 | 2 | False | 2025-03-18 |
| MAC003288 | Seasonal Naive | 0.7160 | 1.7480 | 1.0320 | 2013-03-19T11:30:00+00:00 | 2013-03-19T15:00:00+00:00 | 210.0000 | 0.6960 | 1 | 0.4700 | 0.0000 | 2 | False | 2025-03-18 |
| Portfolio | LightGBM | 5.1220 | 4.6353 | -0.4867 | 2013-03-19T08:00:00+00:00 | 2013-03-19T18:30:00+00:00 | 630.0000 | 4.5134 | 5 | 0.8783 | 0.3562 | 2 | False | 2025-03-18 |
| Portfolio | Ridge Regression | 5.1220 | 4.5288 | -0.5932 | 2013-03-19T08:00:00+00:00 | 2013-03-19T16:00:00+00:00 | 480.0000 | 4.5134 | 5 | 1.2634 | 0.7654 | 2 | False | 2025-03-18 |
| Portfolio | Seasonal Naive | 5.1220 | 5.4520 | 0.3300 | 2013-03-19T08:00:00+00:00 | 2013-03-19T16:00:00+00:00 | 480.0000 | 4.5134 | 5 | 0.8472 | 0.0030 | 2 | False | 2025-03-18 |
| MAC000143 | LightGBM | 1.9640 | 0.6934 | -1.2706 | 2013-11-07T18:30:00+00:00 | 2013-11-07T20:00:00+00:00 | 90.0000 | 0.5460 | 20 | 0.3428 | 0.0576 | 2 | False | 2025-11-06 |
| MAC000143 | Ridge Regression | 1.9640 | 0.7576 | -1.2064 | 2013-11-07T18:30:00+00:00 | 2013-11-07T19:00:00+00:00 | 30.0000 | 0.5460 | 20 | 0.3005 | 0.0227 | 2 | False | 2025-11-06 |
| MAC000143 | Seasonal Naive | 1.9640 | 1.6880 | -0.2760 | 2013-11-07T18:30:00+00:00 | 2013-11-07T13:30:00+00:00 | 300.0000 | 0.5460 | 20 | 0.2488 | 0.0250 | 2 | False | 2025-11-06 |
| MAC001391 | LightGBM | 1.3100 | 0.4452 | -0.8648 | 2013-11-07T18:00:00+00:00 | 2013-11-07T18:30:00+00:00 | 30.0000 | 0.2720 | 9 | 0.2206 | 0.0428 | 2 | False | 2025-11-06 |
| MAC001391 | Ridge Regression | 1.3100 | 0.2845 | -1.0255 | 2013-11-07T18:00:00+00:00 | 2013-11-07T21:00:00+00:00 | 180.0000 | 0.2720 | 9 | 0.2458 | 0.0868 | 2 | False | 2025-11-06 |
| MAC001391 | Seasonal Naive | 1.3100 | 0.4020 | -0.9080 | 2013-11-07T18:00:00+00:00 | 2013-11-07T19:00:00+00:00 | 60.0000 | 0.2720 | 9 | 0.2622 | 0.1260 | 2 | False | 2025-11-06 |
| MAC001395 | LightGBM | 3.0000 | 1.3345 | -1.6655 | 2013-11-07T12:30:00+00:00 | 2013-11-07T18:00:00+00:00 | 330.0000 | 1.7242 | 3 | 1.8208 | 0.0000 | 2 | False | 2025-11-06 |
| MAC001395 | Ridge Regression | 3.0000 | 1.8236 | -1.1764 | 2013-11-07T12:30:00+00:00 | 2013-11-07T07:30:00+00:00 | 300.0000 | 1.7242 | 3 | 1.8251 | 0.0000 | 2 | False | 2025-11-06 |
| MAC001395 | Seasonal Naive | 3.0000 | 3.4400 | 0.4400 | 2013-11-07T12:30:00+00:00 | 2013-11-07T17:30:00+00:00 | 300.0000 | 1.7242 | 3 | 1.8040 | 0.0000 | 2 | False | 2025-11-06 |
| MAC001534 | LightGBM | 0.7720 | 0.8602 | 0.0882 | 2013-11-07T18:00:00+00:00 | 2013-11-07T18:00:00+00:00 | 0.0000 | 0.8670 | 0 | unavailable | 0.0000 | 2 | False | 2025-11-06 |
| MAC001534 | Ridge Regression | 0.7720 | 0.7198 | -0.0522 | 2013-11-07T18:00:00+00:00 | 2013-11-07T13:30:00+00:00 | 270.0000 | 0.8670 | 0 | unavailable | 0.0000 | 2 | False | 2025-11-06 |
| MAC001534 | Seasonal Naive | 0.7720 | 2.0620 | 1.2900 | 2013-11-07T18:00:00+00:00 | 2013-11-07T13:30:00+00:00 | 270.0000 | 0.8670 | 0 | unavailable | 0.0000 | 2 | False | 2025-11-06 |
| MAC003288 | LightGBM | 0.7860 | 0.5063 | -0.2797 | 2013-11-07T17:30:00+00:00 | 2013-11-07T19:00:00+00:00 | 90.0000 | 0.5680 | 3 | 0.2622 | 0.2972 | 2 | True | 2025-11-06 |
| MAC003288 | Ridge Regression | 0.7860 | 0.4893 | -0.2967 | 2013-11-07T17:30:00+00:00 | 2013-11-07T07:30:00+00:00 | 600.0000 | 0.5680 | 3 | 0.3016 | 0.3520 | 2 | True | 2025-11-06 |
| MAC003288 | Seasonal Naive | 0.7860 | 1.2960 | 0.5100 | 2013-11-07T17:30:00+00:00 | 2013-11-07T07:30:00+00:00 | 600.0000 | 0.5680 | 3 | 0.4233 | 0.3320 | 2 | True | 2025-11-06 |
| Portfolio | LightGBM | 7.0360 | 3.4259 | -3.6101 | 2013-11-07T18:30:00+00:00 | 2013-11-07T18:00:00+00:00 | 30.0000 | 3.4578 | 5 | 1.6356 | 0.0000 | 2 | False | 2025-11-06 |
| Portfolio | Ridge Regression | 7.0360 | 3.2316 | -3.8044 | 2013-11-07T18:30:00+00:00 | 2013-11-07T17:30:00+00:00 | 60.0000 | 3.4578 | 5 | 1.9272 | 0.0000 | 2 | False | 2025-11-06 |
| Portfolio | Seasonal Naive | 7.0360 | 5.2800 | -1.7560 | 2013-11-07T18:30:00+00:00 | 2013-11-07T17:30:00+00:00 | 60.0000 | 3.4578 | 5 | 1.7024 | 0.0000 | 2 | False | 2025-11-06 |
| MAC000143 | LightGBM | 1.9820 | 1.1164 | -0.8656 | 2013-12-06T14:00:00+00:00 | 2013-12-06T19:30:00+00:00 | 330.0000 | 0.6360 | 15 | 0.2485 | 0.0310 | 3 | False | 2023-12-01 |
| MAC000143 | Ridge Regression | 1.9820 | 0.8730 | -1.1090 | 2013-12-06T14:00:00+00:00 | 2013-12-06T13:30:00+00:00 | 30.0000 | 0.6360 | 15 | 0.2105 | 0.1776 | 3 | False | 2023-12-01 |
| MAC000143 | Seasonal Naive | 1.9820 | 1.1280 | -0.8540 | 2013-12-06T14:00:00+00:00 | 2013-12-06T21:00:00+00:00 | 420.0000 | 0.6360 | 15 | 0.2521 | 0.1900 | 3 | False | 2023-12-01 |
| MAC001391 | LightGBM | 0.5580 | 0.6190 | 0.0610 | 2013-12-06T17:30:00+00:00 | 2013-12-06T18:30:00+00:00 | 60.0000 | 0.2980 | 8 | 0.1861 | 0.3225 | 3 | True | 2023-12-01 |
| MAC001391 | Ridge Regression | 0.5580 | 0.4127 | -0.1453 | 2013-12-06T17:30:00+00:00 | 2013-12-06T18:30:00+00:00 | 60.0000 | 0.2980 | 8 | 0.2042 | 0.4281 | 3 | True | 2023-12-01 |
| MAC001391 | Seasonal Naive | 0.5580 | 1.2800 | 0.7220 | 2013-12-06T17:30:00+00:00 | 2013-12-06T18:30:00+00:00 | 60.0000 | 0.2980 | 8 | 0.2562 | 0.4770 | 3 | True | 2023-12-01 |
| MAC001395 | LightGBM | 3.0840 | 1.7866 | -1.2974 | 2013-12-06T06:30:00+00:00 | 2013-12-06T18:00:00+00:00 | 690.0000 | 1.8380 | 6 | 1.5398 | 0.7436 | 3 | False | 2023-12-01 |
| MAC001395 | Ridge Regression | 3.0840 | 1.5274 | -1.5566 | 2013-12-06T06:30:00+00:00 | 2013-12-06T16:00:00+00:00 | 570.0000 | 1.8380 | 6 | 1.5363 | 0.8600 | 3 | False | 2023-12-01 |
| MAC001395 | Seasonal Naive | 3.0840 | 2.5960 | -0.4880 | 2013-12-06T06:30:00+00:00 | 2013-12-06T12:30:00+00:00 | 360.0000 | 1.8380 | 6 | 1.6417 | 1.1470 | 3 | False | 2023-12-01 |
| MAC001534 | LightGBM | 1.0800 | 0.8533 | -0.2267 | 2013-12-06T19:00:00+00:00 | 2013-12-06T16:30:00+00:00 | 150.0000 | 0.8690 | 1 | 0.3483 | 0.0000 | 3 | False | 2023-12-01 |
| MAC001534 | Ridge Regression | 1.0800 | 0.7907 | -0.2893 | 2013-12-06T19:00:00+00:00 | 2013-12-06T15:30:00+00:00 | 210.0000 | 0.8690 | 1 | 0.5989 | 0.1050 | 3 | False | 2023-12-01 |
| MAC001534 | Seasonal Naive | 1.0800 | 1.9580 | 0.8780 | 2013-12-06T19:00:00+00:00 | 2013-12-06T15:30:00+00:00 | 210.0000 | 0.8690 | 1 | 0.8480 | 0.1350 | 3 | False | 2023-12-01 |
| MAC003288 | LightGBM | 3.6940 | 0.7777 | -2.9163 | 2013-12-06T11:30:00+00:00 | 2013-12-06T07:00:00+00:00 | 270.0000 | 0.6240 | 19 | 1.1061 | 0.3711 | 3 | False | 2023-12-01 |
| MAC003288 | Ridge Regression | 3.6940 | 0.6861 | -3.0079 | 2013-12-06T11:30:00+00:00 | 2013-12-06T20:00:00+00:00 | 510.0000 | 0.6240 | 19 | 1.0840 | 0.4752 | 3 | False | 2023-12-01 |
| MAC003288 | Seasonal Naive | 3.6940 | 2.0340 | -1.6600 | 2013-12-06T11:30:00+00:00 | 2013-12-06T20:00:00+00:00 | 510.0000 | 0.6240 | 19 | 1.0899 | 0.4730 | 3 | False | 2023-12-01 |
| Portfolio | LightGBM | 6.2820 | 4.7201 | -1.5619 | 2013-12-06T11:30:00+00:00 | 2013-12-06T18:00:00+00:00 | 390.0000 | 3.7148 | 18 | 1.4984 | 0.7800 | 3 | False | 2023-12-01 |
| Portfolio | Ridge Regression | 6.2820 | 3.4421 | -2.8399 | 2013-12-06T11:30:00+00:00 | 2013-12-06T16:00:00+00:00 | 270.0000 | 3.7148 | 18 | 1.7109 | 1.7843 | 3 | False | 2023-12-01 |
| Portfolio | Seasonal Naive | 6.2820 | 4.9720 | -1.3100 | 2013-12-06T11:30:00+00:00 | 2013-12-06T20:30:00+00:00 | 540.0000 | 3.7148 | 18 | 1.7252 | 1.8280 | 3 | False | 2023-12-01 |
| MAC000143 | LightGBM | 2.0440 | 1.0055 | -1.0385 | 2013-01-13T09:00:00+00:00 | 2013-01-13T17:30:00+00:00 | 510.0000 | 0.7578 | 10 | 0.3975 | 0.0385 | 4 | False | 2026-01-11 |
| MAC000143 | Ridge Regression | 2.0440 | 0.7247 | -1.3193 | 2013-01-13T09:00:00+00:00 | 2013-01-13T19:30:00+00:00 | 630.0000 | 0.7578 | 10 | 0.5224 | 0.3885 | 4 | False | 2026-01-11 |
| MAC000143 | Seasonal Naive | 2.0440 | 1.9160 | -0.1280 | 2013-01-13T09:00:00+00:00 | 2013-01-13T19:30:00+00:00 | 630.0000 | 0.7578 | 10 | 0.6886 | 1.1160 | 4 | False | 2026-01-11 |
| MAC001391 | LightGBM | 0.4700 | 0.3355 | -0.1345 | 2013-01-13T22:00:00+00:00 | 2013-01-13T18:30:00+00:00 | 210.0000 | 0.2740 | 9 | 0.0968 | 0.2319 | 4 | False | 2026-01-11 |
| MAC001391 | Ridge Regression | 0.4700 | 0.3204 | -0.1496 | 2013-01-13T22:00:00+00:00 | 2013-01-13T19:30:00+00:00 | 150.0000 | 0.2740 | 9 | 0.0963 | 0.2832 | 4 | False | 2026-01-11 |
| MAC001391 | Seasonal Naive | 0.4700 | 0.4260 | -0.0440 | 2013-01-13T22:00:00+00:00 | 2013-01-13T18:30:00+00:00 | 210.0000 | 0.2740 | 9 | 0.1287 | 0.3530 | 4 | False | 2026-01-11 |
| MAC001395 | LightGBM | 5.3340 | 2.1969 | -3.1371 | 2013-01-13T15:30:00+00:00 | 2013-01-13T17:00:00+00:00 | 90.0000 | 2.3434 | 7 | 1.5743 | 0.7650 | 4 | False | 2026-01-11 |
| MAC001395 | Ridge Regression | 5.3340 | 2.2581 | -3.0759 | 2013-01-13T15:30:00+00:00 | 2013-01-13T09:00:00+00:00 | 390.0000 | 2.3434 | 7 | 1.7650 | 0.9957 | 4 | False | 2026-01-11 |
| MAC001395 | Seasonal Naive | 5.3340 | 3.9960 | -1.3380 | 2013-01-13T15:30:00+00:00 | 2013-01-13T08:00:00+00:00 | 450.0000 | 2.3434 | 7 | 1.0860 | 0.5410 | 4 | False | 2026-01-11 |
| MAC001534 | LightGBM | 1.7880 | 1.1181 | -0.6699 | 2013-01-13T20:30:00+00:00 | 2013-01-13T17:30:00+00:00 | 180.0000 | 0.9950 | 8 | 0.4949 | 0.0613 | 4 | False | 2026-01-11 |
| MAC001534 | Ridge Regression | 1.7880 | 0.9673 | -0.8207 | 2013-01-13T20:30:00+00:00 | 2013-01-13T15:30:00+00:00 | 300.0000 | 0.9950 | 8 | 0.4694 | 0.3844 | 4 | False | 2026-01-11 |
| MAC001534 | Seasonal Naive | 1.7880 | 3.4760 | 1.6880 | 2013-01-13T20:30:00+00:00 | 2013-01-13T15:30:00+00:00 | 300.0000 | 0.9950 | 8 | 0.4030 | 0.2230 | 4 | False | 2026-01-11 |
| MAC003288 | LightGBM | 1.2140 | 0.7524 | -0.4616 | 2013-01-13T15:00:00+00:00 | 2013-01-13T16:30:00+00:00 | 90.0000 | 0.6370 | 11 | 0.3746 | 0.2577 | 4 | False | 2026-01-11 |
| MAC003288 | Ridge Regression | 1.2140 | 0.8687 | -0.3453 | 2013-01-13T15:00:00+00:00 | 2013-01-13T19:00:00+00:00 | 240.0000 | 0.6370 | 11 | 0.4429 | 0.4059 | 4 | False | 2026-01-11 |
| MAC003288 | Seasonal Naive | 1.2140 | 1.5280 | 0.3140 | 2013-01-13T15:00:00+00:00 | 2013-01-13T20:30:00+00:00 | 330.0000 | 0.6370 | 11 | 0.5287 | 0.3020 | 4 | False | 2026-01-11 |
| Portfolio | LightGBM | 7.1900 | 5.0932 | -2.0968 | 2013-01-13T15:30:00+00:00 | 2013-01-13T17:30:00+00:00 | 120.0000 | 4.2282 | 13 | 1.0764 | 0.6525 | 4 | False | 2026-01-11 |
| Portfolio | Ridge Regression | 7.1900 | 4.2751 | -2.9149 | 2013-01-13T15:30:00+00:00 | 2013-01-13T16:30:00+00:00 | 60.0000 | 4.2282 | 13 | 1.3921 | 2.3497 | 4 | False | 2026-01-11 |
| Portfolio | Seasonal Naive | 7.1900 | 6.4980 | -0.6920 | 2013-01-13T15:30:00+00:00 | 2013-01-13T21:00:00+00:00 | 330.0000 | 4.2282 | 13 | 0.9292 | 1.5220 | 4 | False | 2026-01-11 |
| MAC000143 | LightGBM | 0.8420 | 0.7370 | -0.1050 | 2013-02-03T06:00:00+00:00 | 2013-02-03T19:30:00+00:00 | 810.0000 | 0.7800 | 2 | 0.5548 | 0.0293 | 6 | False | 2025-02-02 |
| MAC000143 | Ridge Regression | 0.8420 | 0.6596 | -0.1824 | 2013-02-03T06:00:00+00:00 | 2013-02-03T17:00:00+00:00 | 660.0000 | 0.7800 | 2 | 0.4943 | 0.0000 | 6 | False | 2025-02-02 |
| MAC000143 | Seasonal Naive | 0.8420 | 1.5360 | 0.6940 | 2013-02-03T06:00:00+00:00 | 2013-02-03T06:00:00+00:00 | 0.0000 | 0.7800 | 2 | 0.5700 | 0.0010 | 6 | False | 2025-02-02 |
| MAC001391 | LightGBM | 0.5180 | 0.4644 | -0.0536 | 2013-02-03T19:00:00+00:00 | 2013-02-03T19:00:00+00:00 | 0.0000 | 0.3160 | 3 | 0.0471 | 0.0000 | 6 | False | 2025-02-02 |
| MAC001391 | Ridge Regression | 0.5180 | 0.3255 | -0.1925 | 2013-02-03T19:00:00+00:00 | 2013-02-03T22:30:00+00:00 | 210.0000 | 0.3160 | 3 | 0.0875 | 0.0233 | 6 | False | 2025-02-02 |
| MAC001391 | Seasonal Naive | 0.5180 | 0.4360 | -0.0820 | 2013-02-03T19:00:00+00:00 | 2013-02-03T16:30:00+00:00 | 150.0000 | 0.3160 | 3 | 0.1133 | 0.0490 | 6 | False | 2025-02-02 |
| MAC001395 | LightGBM | 3.9880 | 2.0897 | -1.8983 | 2013-02-03T08:00:00+00:00 | 2013-02-03T06:30:00+00:00 | 90.0000 | 2.2960 | 6 | 1.6509 | 0.5797 | 6 | False | 2025-02-02 |
| MAC001395 | Ridge Regression | 3.9880 | 2.2434 | -1.7446 | 2013-02-03T08:00:00+00:00 | 2013-02-03T13:30:00+00:00 | 330.0000 | 2.2960 | 6 | 1.4214 | 0.2221 | 6 | False | 2025-02-02 |
| MAC001395 | Seasonal Naive | 3.9880 | 3.3180 | -0.6700 | 2013-02-03T08:00:00+00:00 | 2013-02-03T13:30:00+00:00 | 330.0000 | 2.2960 | 6 | 0.9693 | 0.3950 | 6 | False | 2025-02-02 |
| MAC001534 | LightGBM | 1.0660 | 0.9054 | -0.1606 | 2013-02-03T08:30:00+00:00 | 2013-02-03T18:30:00+00:00 | 600.0000 | 1.0274 | 1 | 0.2825 | 0.1010 | 6 | False | 2025-02-02 |
| MAC001534 | Ridge Regression | 1.0660 | 0.7427 | -0.3233 | 2013-02-03T08:30:00+00:00 | 2013-02-03T18:00:00+00:00 | 570.0000 | 1.0274 | 1 | 0.6433 | 0.2596 | 6 | False | 2025-02-02 |
| MAC001534 | Seasonal Naive | 1.0660 | 2.3380 | 1.2720 | 2013-02-03T08:30:00+00:00 | 2013-02-03T00:30:00+00:00 | 480.0000 | 1.0274 | 1 | 0.5940 | 0.2270 | 6 | False | 2025-02-02 |
| MAC003288 | LightGBM | 1.3960 | 0.9207 | -0.4753 | 2013-02-03T09:00:00+00:00 | 2013-02-03T19:30:00+00:00 | 630.0000 | 0.6766 | 7 | 0.3298 | 0.3737 | 6 | False | 2025-02-02 |
| MAC003288 | Ridge Regression | 1.3960 | 0.7364 | -0.6596 | 2013-02-03T09:00:00+00:00 | 2013-02-03T19:00:00+00:00 | 600.0000 | 0.6766 | 7 | 0.4121 | 0.5741 | 6 | False | 2025-02-02 |
| MAC003288 | Seasonal Naive | 1.3960 | 1.4960 | 0.1000 | 2013-02-03T09:00:00+00:00 | 2013-02-03T08:30:00+00:00 | 30.0000 | 0.6766 | 7 | 0.4723 | 0.7800 | 6 | False | 2025-02-02 |
| Portfolio | LightGBM | 5.2720 | 4.0571 | -1.2149 | 2013-02-03T08:30:00+00:00 | 2013-02-03T19:30:00+00:00 | 660.0000 | 4.2956 | 4 | 1.7099 | 0.1413 | 6 | False | 2025-02-02 |
| Portfolio | Ridge Regression | 5.2720 | 4.1941 | -1.0779 | 2013-02-03T08:30:00+00:00 | 2013-02-03T17:00:00+00:00 | 510.0000 | 4.2956 | 4 | 1.7280 | 0.1271 | 6 | False | 2025-02-02 |
| Portfolio | Seasonal Naive | 5.2720 | 5.2760 | 0.0040 | 2013-02-03T08:30:00+00:00 | 2013-02-03T08:30:00+00:00 | 0.0000 | 4.2956 | 4 | 1.0870 | 0.9650 | 6 | False | 2025-02-02 |
