# Low Carbon London Data Lab — UI guide (Task 03B)

> Historical Task 03B guide. The current three-page interface is documented in
> [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md); Task 03E supersedes the navigation below.

Finalised 17 November 2026. Presentation only: saved Task 03 measurements, recommendation,
metrics, acquisition/parsing and replay mapping are unchanged. No Task 04 work.

## Launch and navigation

From `the BatteryFlex repository root` with the existing environment:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

In Data Explorer, enable **Low Carbon London Data Lab** below the existing NESO selection.
The prepared local artifacts are already present. No acquisition or reprocessing is needed.
The lab has four views; only the chosen view renders:

1. **Household Explorer** (default): dataset overview, recommended-five selector and concise
   selection table. Nothing is preselected; charts/readings appear only after choosing a home.
   Switch **Household list** to **All prepared candidates** for the separate searchable 100-ID list.
2. **Five-Household Comparison**: reviewed five-house table, typical daily profiles and
   daily-energy, evening-power, peak-power and completeness bars. Colours are stable by ID.
3. **NESO Event Replay**: exactly five reviewed Live events, initially unselected. Selecting one
   opens the original NESO summary and **NESO Event Replay — Five Households** comparison.
4. **Data Quality & Provenance**: source/time/quality explanation. Expand advanced provenance
   for original acquisition metadata, checksum checks, source audit and mapping policy.

## Household exploration

Reviewed households: MAC001391, MAC003288, MAC000143, MAC001534 and MAC001395.
Original dataset: 4,443 standard-tariff households over calendar 2013; prepared sample:
100 households over 1 January–31 March, 7 November and 6 December 2013. January–March is
90 heating-season days; March is a shoulder month. These retained dates do not imply
continuous coverage of the intervening months. All source clocks use fixed GMT.

Select a household to see daily kWh, peak half-hour kW, completeness and complete-day/missing
counts. Open **Household information and statistics** for source timestamp bounds, average
and minimum power, evening demand, standard deviation and coefficient of variation. Summary
statistics use January–March 2013: average/minimum power use valid half-hours, daily energy
uses complete 48-interval days, evening means 16:00–20:00 GMT and standard deviation uses ddof=1.
Average power is not inferred from only complete-day energy. The date selector changes the
readings/charts below it, while these clearly labelled analysis-period summaries stay fixed.

IDs are anonymised. Addresses, postcodes, occupants, property types, appliances and installed
batteries are unavailable; none are inferred. The five examples are not statistically
representative of all UK households and do not establish battery feasibility.

The date range is inclusive by interval START. The chronological table retains original
interval-END timestamp text, derived start/end, original measured kWh text, calculated kW
and quality. **Download selected readings as CSV** exports those selected rows in the same
chronological order, preserving source text, original dates and missing values.

The source label 18:30 covers 18:00–18:30; `average_power_kw = energy_kwh / 0.5`.
Midnight END belongs to the previous consumption day. Missing values never become zero.

## Charts and day quality

- **Half-hour electricity demand**: actual date/time in GMT; measured energy converted to
  average kW. Scroll to zoom, drag to pan, double-click to reset, hover for original readings.
  Lines break at missing, invalid and unretained intervals.
- **Daily electricity consumption**: a total appears only with 48 valid unique half-hours.
  A separate coverage strip marks complete, incomplete and unretained days. Partial/missing
  daily energy is null, never a partial total or zero. Open Daily coverage details for counts.
- **Typical daily demand profile**: mean valid demand by half-hour of day in the selected
  household/date range, with an explicit 00:00–24:00 GMT axis. No value is invented at 24:00;
  the last actual interval starts at 23:30. Hover shows contributing valid observation count.

The five-house comparison uses the fixed January–March period, rather than the explorer's
individual date filter. Consistent ID colours link its profiles/bars to event replay; the
combined replay series is grey and dashed. Table columns can scroll horizontally on narrow
screens; native chart menus provide data inspection, image export and fullscreen controls.

## NESO replay

All five validated dates/windows and the same five household IDs are preserved, with
2/2/3/4/6 original half-hours (17 total). The NESO summary shows original event date,
GMT window, duration, national requirement in MW, Live status and interval count. The replay
shows the original mapped 2013 LCL date and both original interval start/end pairs, each
household's kW and combined kW. Chart hover includes the original LCL interval-END label.
An optional collapsed chart displays published national MW separately from household kW.

This is **synthetic historical replay using real household measurements**. Calendar mapping
v1 uses same month/exact weekday in 2013, nearest day number, earlier tie. Demand is joined
at mapped interval END, without interpolation or changing source timestamps. It does not
match weather, holidays or occupancy and does not imply simultaneous observations.
National MW is never a household target or portfolio commitment.

## Reliability and verification

Only the existing local prepared Parquet/CSV/audit artifacts are loaded. Hash validation and
cache invalidation by audit revision remain unchanged. Opening the lab or changing controls
never downloads or scans raw data. Missing preparation shows a restore message; corrupt
prepared files show an integrity error. There is no automatic fallback or acquisition control.

Final checks: 98 pytest tests passed, Ruff lint/format checks passed, ty passed. Tests cover
five/default and 100/candidate scopes, dependent household/date views, empty/corrupt states,
CSV content, interval-end/kWh-to-kW semantics, complete-day-only totals, missing-value and
line-gap handling, all five events/17 intervals/same IDs and distinct original date pairs.
All existing NESO tests continue to pass.

Real localhost agent API smoke checked all four sections, household/date changes, expanded
statistics/day diagnostics/provenance, all five replay tables and optional national chart.
Browser review confirmed five searchable recommended choices, no initial detailed view,
selected-household charts, comparison profiles/bars and replay rendering. Snapshots are
ignored outputs/task03b-*.jpg; temporary app stopped after verification. Browser Vega logs
briefly reported infinite extents while Arrow datasets hydrated during view changes; the
settled charts rendered correctly, with no browser errors or server warnings/tracebacks.

20 source/data files were hashed before and after: all raw/prepared artifacts, acquisition/
parsing/selection/replay modules, preparation script, NESO modules and frozen event manifest
are byte-for-byte unchanged. No re-acquisition, reprocessing, reselection or Task 04 work.

## Superseded public navigation — Task 03E

The guide above records the Task 03B research interface. Current public Data Explorer has
NESO Flexibility Events and Low Carbon London tabs, five recommended households, one dated
chart/readings table and a separate one-chart five-house comparison. The detailed Task 03B
components remain internally tested but are no longer routed publicly. Read UI_ARCHITECTURE.md
for the current three-page product. Source data, selection and replay remain unchanged.
