> Final Task 05 UI cleanup removes recommendation/version information from Forecast Model Development. The resolver and planning integration described here remain unchanged; earlier descriptions of the development-page displays below are historical. [Cleanup report](TASK05_FINAL_UI_CLEANUP.md).

# Activation-free event forecast resolution

The event forecasting UI has no Activate Event Model button, activation selector or active-model status. It shows the automatically recommended algorithm and full immutable model version immediately for the selected event, independently of chart checkboxes or unsaved experimental parameters. Run Event Models still loads exact saved results first and automatically persists only missing configurations; this change never requests retraining of existing models.

## Selection contract

`resolve_event_forecast(repo, event_id, *, algorithm=None)` reads the stored NESO event and replay mapping, checks them against the reviewed source, and uses the existing SHA-256/fingerprint-verified Task 05D lookup. The event ID is the existing internal scenario ID used by the event selector, not an invented official NESO identifier. Unknown IDs, missing/mismatched mappings, missing/incompatible artifacts, invalid validation metrics and missing required forecasts fail explicitly. There is no fallback to another event, model configuration, dataset, activation pointer or retraining.

Automatic selection compares **saved validation portfolio RMSE only**, with Ridge Regression and LightGBM as candidates. Exact ties select Ridge deterministically. Both candidates must exist for an automatic comparison; one missing candidate fails explicitly rather than silently recommending from an incomplete comparison. Seasonal Naive remains a benchmark and never becomes the automatic recommendation, even if its validation RMSE is lower. Full-day/event-day/holdout errors and peak diagnostics do not select the model.

The canonical request uses the current persisted event dataset, shared Task 05D chronology/features and saved default configurations (Ridge alpha 1; LightGBM 200 trees, rate .05, 15 leaves, max depth -1, seed 42). Explicitly trained experimental hyperparameters remain preserved but do not silently change the canonical recommendation. Matching fingerprints must exist; this resolver never builds them. The existing event/legacy activation schema and compatibility methods remain intact and are not consulted by resolution.

## Future Task 06 caller

```python
from batteryflex.storage.forecast_resolver import resolve_event_forecast

forecast = resolve_event_forecast(repo, selected_event_id)
households = forecast.household_forecasts  # five households x 48 = 240 rows
portfolio = forecast.portfolio_forecast  # 48 rows, verified household sum

# Explicit algorithm comparison; does not save a preference or alter recommendation.
comparison = resolve_event_forecast(repo, selected_event_id, algorithm="Ridge Regression")
# LightGBM and Seasonal Naive (explicit benchmark only) are also valid overrides.
```

The returned `ResolvedEventForecast` includes event ID, replay date, forecast origin, immutable dataset/request IDs, exact model version, algorithm, validation portfolio RMSE and whether an override was requested. Forecast tables contain household ID, forecast origin, interval start/end, horizon steps 1–48 and nonnegative predicted interval-average demand in kW. They exclude actual target consumption and post-hoc metrics. Tables are defensive copies; the portfolio is the complete coincident sum verified by the existing storage reader.

Visible Simulation Lab connects event storage without reading the legacy activation registry. The planning-only Run Simulation & Results view now resolves the selected event directly and attaches its exact saved reference/provenance to the plan. It no longer requires or displays a legacy active forecasting model. `ActiveModelReference` is retained solely as the old plan's name/version value type; constructing it does not create an activation record. Run Simulation stays disabled. No optimisation, dispatch, battery feasibility or Task 06 engine is implemented.

A future optimiser must call this resolver rather than a legacy activation registry. An unavailable saved forecast must stop that request with the returned error; users can explicitly prepare missing event results via Run Event Models outside optimisation. Explicit overrides can use any saved algorithm, including Seasonal Naive for benchmark experiments, and require that exact saved forecast without needing the other candidates.

## Verified saved recommendations

| Original NESO date | Replay date | Recommended algorithm | Validation portfolio RMSE (kW) | Exact saved model version |
| --- | --- | --- | --- | --- |
| 2025-03-18 | 2013-03-19 | LightGBM | 0.890148617 | event-d18e6dfbff45fff3109dea45acf8f4aa8787c8b33019886c4d4b429c8d9baace |
| 2025-11-06 | 2013-11-07 | LightGBM | 0.834207135 | event-3d896138c769ed80bbe5fff93da2a34932fb1b4c8d19b8bf8a0d579187848a4a |
| 2023-12-01 | 2013-12-06 | Ridge Regression | 0.830432977 | event-505a27e4670a92bb5e1bc3765e04a9bb4802502d95d61eb3a1c4f0ddc13a2b50 |
| 2026-01-11 | 2013-01-13 | LightGBM | 0.868980349 | event-ba46758b9103b7f34b865c5fa209acdfdbe98ad6292428ee6fe3731c71e902d9 |
| 2025-02-02 | 2013-02-03 | LightGBM | 0.957126247 | event-c13b10249e432c094a4a1a4539b98f0a02c92add972821b9a05607b3cbd8ecba |

## Verification and preservation

Fresh-cache live resolution restored all five requests and all three explicit algorithm overrides, producing 240 household and 48 portfolio rows each with correct aggregation. Training, uploads, non-SELECT SQL and activation-table reads during resolution were blocked. All rows in all 27 cloud tables matched before/after snapshots; original estimator, feature, persistence and source-data hashes remained unchanged. There are no database migrations, deleted artifacts, activation writes or new cloud resources. Evidence is in ignored `outputs/forecast-resolver/report.json` and `cloud-before.json`.

Tests cover validation-only ranking with a deliberately superior Naive benchmark, exact ties, invalid metrics, mixed requests, missing candidates, overrides, replay integrity, unknown events, read-only saved retrieval, absent and populated legacy activation state, full horizon/aggregation, no target actuals in returned forecasts, UI controls/status removal and resolver-based planning without execution. The full regression suite passed **322 tests in 161.90 seconds**; Ruff check/format and source/script type checks pass. The final added UI assertion also passed, proving an unsaved alpha change leaves the recommended saved version visible and unchanged. The running cloud-backed app verified all five event selections with exact model versions, no activation controls/status, saved-result reuse (3 reused / 0 trained each), and resolver-based planning with execution disabled. Existing populated activation records and model timestamps/versions remained unchanged. The temporary verification server was stopped; logs contained no exceptions or deprecation warnings.

All Task 05B/05C/05D/05E artifacts and historical mappings are preserved. Work is uncommitted; no merge or deployment was performed.

A final fresh-server check of Forecast Model Development and the selected-event planning view also prohibited reads of event activation records and the legacy global forecast-model pointer. Both views restored the recommendation successfully; unsaved experimental settings left it visible. All verification servers were stopped. Evidence: `outputs/forecast-resolver/ui-verification/` and the guarded verification scripts in its parent folder.
