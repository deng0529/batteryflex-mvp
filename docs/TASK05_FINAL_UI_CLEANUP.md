# Task 05 — Final forecasting UI cleanup

Branch `codex/task05-final-ui-cleanup`. This is a presentation-only cleanup. Forecast algorithms, feature schemas, source data, event mappings, immutable model versions, saved predictions/metrics, resolver and peak-analysis code, and SQL schemas are unchanged.

## Visible interface

Forecast Model Development retains:

- All five NESO event selections and their original replay dates/windows.
- The main four-row table of exact Training, Validation, Testing / Holdout and Event Forecast dates (YYYY-MM-DD), including the existing usable-day counts.
- Ridge and LightGBM configuration controls, with Seasonal Naive as the paired reference, and household/portfolio MAE/RMSE evaluation information.
- Run Event Models and a concise status message describing actual reuse or training.
- A selectable full-day chart for the five households and portfolio, including Actual and the selected saved Ridge, LightGBM and Seasonal Naive curves, legend selection, zoom and event shading.
- The existing full-day RMSE bar chart and a directly visible full-day accuracy table (MAE, RMSE and half-hour sample counts for all five homes plus portfolio). The accuracy CSV contains the same visible full-day results.

Removed from this page: household-specific dates/samples, historical quality section, inclusive-calendar/usable-day explanations, recommendation/version displays and explanations, saved provenance expander, the extra event-window/holdout comparison expander, and all peak diagnostics/analysis/download controls. There are no evaluation mode selectors or extra expanders below the main results. The backend resolver, diagnostic exporter and historical evaluation artifacts remain available for future research. Other Simulation Lab planning behavior is unchanged; optimisation remains disabled.

## Saved-data-first behavior and safe recovery

The existing EventForecasts lookup/run implementation is byte-for-byte unchanged. Opening a saved event, refreshing the browser, restarting Streamlit or clicking Run Event Models loads matching model references, forecasts and evaluation data from the dedicated Turso/R2 store. Storage reads verify SHA-256, exact configuration/fingerprint, event/replay identity, horizon, aggregation and stored metrics. Integrity verification can recompute scores from saved prediction rows; it does not generate new predictions.

If no exact model record exists, an explicit Run Event Models request trains only missing configurations, generates predictions/evaluation, automatically writes immutable content-addressed artifacts and metadata, and performs verified readback. No manual save or activation step is introduced. This first-run path is tested using isolated SQLite/fake-R2 fixtures, without creating or retraining cloud models.

Successful saved loads show **Saved forecasting results loaded**, including automatic restoration when the page opens. A request that actually trains missing models shows **Models trained and saved**. A mixture of reused and newly trained models uses the latter because training actually occurred.

A damaged local cache is repaired only by retrieving the same verified immutable object from R2. Missing/corrupt remote artifacts or incompatible bundles fail clearly; they do not silently train, overwrite an existing saved version or substitute another model. Restoring access/the exact valid artifact is required, following the existing storage policy. New UI failure-path tests cover missing remote objects, remote SHA mismatch and an integrity-valid but schema-incompatible saved model; each reports an error without implicit training/writes or forecast display.

## Verification

The regression suite passed **325 tests in 307.08 seconds**, including the three new missing/corrupt/incompatible saved-artifact cases. Ruff check/format and source/script type checks pass. The final targeted UI rerun passed **4 tests in 91.19 seconds**, verifying fresh-session status, no prediction regeneration on reuse and the artifact failure paths.

Live verification used two separate Streamlit processes with two new empty disk caches. All five events restored in each process, their exact four-row date tables matched the saved metadata exports, and the retained chart/accuracy table data were present. Twenty repeated Run Event Models clicks loaded saved results. Two additional new browser sessions restored results without clicking Run. Fitting, prediction generation, R2 uploads and every non-SELECT SQL statement were blocked throughout. No such operation occurred. All rows in all **27 cloud tables** matched the before-state snapshot, and **55 protected code/data files** retained their SHA-256 hashes. Both temporary servers were stopped; logs had no exceptions or deprecation warnings. Evidence is stored locally under ignored `outputs/task05-final/`.

No additional algorithms/features, peak improvements, migrations, cloud resources or battery optimisation are implemented. No staging, commit, merge or deployment is performed.
