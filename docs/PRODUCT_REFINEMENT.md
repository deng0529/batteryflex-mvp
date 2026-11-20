# BatteryFlex product refinement

20 November 2026 · `codex/task06a-rbc-export-replay` · Local review

## Audit and implementation

The review followed the application entry point through event and demand exploration,
portfolio editing, forecast retrieval, each controller, batch recovery and evaluation.
It also checked numerical identity, persistent storage, packaging and documentation.
The changes prioritised the public workflow, duplicated presentation defaults and
saved-result reads. The numerical engine, physical models, forecast fitting, compatibility
checks, persistence format and legacy full-day runner retain their existing contracts.

| Finding | Change |
| --- | --- |
| The global title competed with page headings, and the landing view opened inside data exploration. | Overview now introduces the product, configured assets, architecture and verified Experiment A. The sidebar contains four workspaces and a version. |
| National MW, local kW and delivery outcomes appeared in separate parts of the workflow. | Data Explorer shows the portfolio obligation and source date mapping next to the reviewed event. Simulation Lab uses portfolio delivery and weighted objective terminology. |
| Portfolio modelling and checks made the main editor longer. | Active portfolio metrics and qualification stay visible. Battery equations, the execution demonstration and default economics have expandable panels. Original household readings are also expandable. |
| Tariffs, reserve and solver widget defaults were embedded in presentation code. | Validated package YAML files define application, portfolio, event dispatch and forecasting defaults. Effective runtime values continue into the existing scenario snapshots. |
| Opening several views could repeat saved bundle discovery. | Overview and evaluation share a session-scoped 30-second read cache. Dispatch invalidates it after new saved results and batch requests. Turso/R2 or explicitly configured local storage remains authoritative. |
| The README described the original research scaffold. | The README now documents the current workflows, attribution, benchmark, installation and reproducibility. |

The three-layer [architecture SVG](../src/batteryflex/resources/architecture.svg) redraws
the earlier architecture figure found inside the local architecture document. The electric
network connects directly to homes. The aggregator receives historical requirements and
demand evidence, models dispatch commands, and stores results. Conceptual live market and
asset interfaces have distinct flow labels.

Forecast editing remains in Simulation Lab, with one set of controls. Overview uses the
published default Experiment A family and labels it accordingly. Its portfolio indicators
describe the active configuration. Overview withholds five-event totals until it discovers
all controllers for all registered events in one compatible family. The event manifest
stays in its original hashed JSON form to preserve source provenance. The new YAML files
use JSON-compatible syntax to avoid a parser dependency.

## Verification

- The pre-refinement test baseline was 359 passing tests. Existing UI assertions were
  moved to their new page or expanded panel. Domain and persistence assertions were
  retained. The final suite passed **364 tests**. Ruff lint, Ruff formatting, `ty`
  and compile checks passed. New tests cover configuration validation, override
  isolation, fingerprint equivalence, read-only Overview and partial coverage. An
  offline wheel build verified that the SVG, YAML defaults and registry are packaged.
- An isolated Streamlit workflow executed 15 successful event-only runs. A deliberately
  failed RBC event recovered independently, reusing its four saved neighbours.
  All 15 exact single-event runs and the three five-event batches were saved-first
  before and after restart. Both comparison scopes opened without controller execution.
- All 15 identities matched the previous verified production audit. Across 30 planned
  and replay trajectories, dispatch powers, battery state, demand, exports, delivery,
  shortfall and weighted objective values matched the isolated pre-refinement baseline
  with a maximum absolute difference of zero at a tolerance of 0.000001.
- The prior read-only cloud audit also verified 32 full-day records. This pass used isolated
  storage and the existing legacy regression tests. No production backfill or write was
  required.
- The real app was inspected in Chromium at desktop, laptop and tablet widths. The
  review screenshots use the development fixture with saved forecasts and results.
  The full capture set is local. The README includes two publication copies.
  All four workspaces rendered with zero page-level horizontal overflow during capture.
  The wide asset editor scrolls within its table.

### Review screenshots

| View | Local capture |
| --- | --- |
| Overview and architecture | [Overview](../outputs/product-refinement/01-overview.png) · [Architecture](../outputs/product-refinement/02-architecture.png) · [Experiment A](../outputs/product-refinement/13-experiment-a.png) |
| Data and forecasting | [Historical events](../outputs/product-refinement/03-flexibility-events.png) · [Household demand](../outputs/product-refinement/04-household-demand.png) · [Demand forecasting](../outputs/product-refinement/11-demand-forecasting.png) |
| Portfolio | [Portfolio & Configuration](../outputs/product-refinement/05-portfolio.png) |
| Controller results | [RBC](../outputs/product-refinement/06-rbc.png) · [MPC](../outputs/product-refinement/07-mpc.png) · [Standalone MILP](../outputs/product-refinement/08-milp.png) |
| Saved evaluation | [Five events](../outputs/product-refinement/09-five-events.png) · [Individual event](../outputs/product-refinement/10-individual-event.png) |
| Responsive review | [Tablet Overview](../outputs/product-refinement/12-overview-tablet.png) |

## Publication review

- Git currently sees BatteryFlex as an untracked directory within a parent repository
  that contains unrelated tracked files and deletions. A public release needs a
  BatteryFlex-scoped staging review or dedicated checkout. The existing branch was
  used for the edits. Nothing was staged, committed, pushed, merged or deployed.
- `.env`, Streamlit secrets, local databases, caches, datasets, model artifacts and
  generated verification output are ignored. A pattern scan of publication source
  and text configuration found no obvious credential values. Historical notes
  contain machine-specific file paths. Review these notes and the existing local
  architecture document and analysis PDF before staging them. Both reports are
  optional for the application.
- The packaged historical NESO subset uses the attributed DFS datasets. The Low
  Carbon London source is attributed separately, and raw and prepared copies stay
  outside Git. Keep the packaged manifest and avoid republishing development
  datasets. [NESO licence](https://www.neso.energy/data-portal/neso-open-licence) ·
  [4TU dataset](https://doi.org/10.4121/fbbe775b-48d8-469f-a39b-b64488bfd6fd.v1)
- Access to a write-enabled hosted app would let anyone with browser access start
  dispatch and training or save shared portfolio changes. Approve an access policy
  before hosting. A protected operator instance or an explicitly read-only public
  demo with separate storage credentials would address that exposure.
- A clean release checkout should verify packaging and the explicit data preparation
  instructions, review the staged diff for secrets and large binaries, and resolve
  the repository licence separately with the owner.

## Changed areas

- `src/batteryflex/defaults.py`, packaged configuration, portfolio default construction
  and event scenario initialisation.
- Streamlit shell and theme, Overview, Explorer, Portfolio, Forecasting and Simulation Lab
  presentation, and shared saved comparison reads.
- README, configuration guide, packaging metadata, ignore rules, release screenshots
  and engineering handoff.
- Targeted configuration tests and updates for the new navigation, expandable detail
  and user-facing result labels.

Launch locally from the BatteryFlex directory.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
