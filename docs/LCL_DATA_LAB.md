# Task 03 — Low Carbon London exploration report

Reviewed 16 November 2026. Real measurements, synthetic historical replay; no battery assets,
commitments, dispatch, optimisation, MPC, Turso or changes to validated NESO inputs.

## Source and acquisition

Tindemans, Simon (2023), Low Carbon London smart meter data (refactored), version 1,
4TU.ResearchData. [Versioned DOI](https://doi.org/10.4121/fbbe775b-48d8-469f-a39b-b64488bfd6fd.v1).
[Dataset landing page](https://data.4tu.nl/datasets/fbbe775b-48d8-469f-a39b-b64488bfd6fd).
[Licence: CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Original data: UK Power Networks, Low Carbon London; retain attribution when reusing.
The separate survey-linked UK Data Service edition has a different licence and was not used.

The exact publisher README and landing HTML are saved unchanged under ignored `data/lcl/raw/`.
The browser research fetch returned 403, but direct authorised Python HTTPS succeeded.
Both publisher file MD5 checksums passed. Acquisition records UTC time, URLs, sizes and SHA-256.
Subsequent acquisition verifies and reuses existing files; it does not silently overwrite corruption.

| File | Direct URL | Bytes | Publisher MD5 |
| --- | --- | --- | --- |
| README | https://data.4tu.nl/file/fbbe775b-48d8-469f-a39b-b64488bfd6fd/b1787dea-0c7b-46b8-a99d-d8b17ceb6680 | 1,625 | 710093b41c0d3258b923a6495f8bdfa3 |
| LCL_2013_kWh.csv.zip | https://data.4tu.nl/file/fbbe775b-48d8-469f-a39b-b64488bfd6fd/c0471ebc-e008-4ec4-9cff-4f12c69bafe6 | 137,223,875 | 2a4bde340f2ee2a8aa9813debb9da363 |

ZIP member `LCL_2013.csv`: 587,690,273 uncompressed bytes (compressed payload 137,223,701).
Archive SHA-256: `bce91566326674d82ad3afd1b8cf73f5852f4fdbc0a1bbbfc5120b0ecf22b919`.
UTF-8 comma-delimited wide CSV: `DateTime` plus 4,443 unique `MAC` + six-digit IDs,
from MAC000002 to MAC005567 with gaps. IDs are opaque strings, not sequential row numbers.
The README's illustrative label length differs; the parser follows the actual header.
Standard tariff only; refactoring removes time-of-use households and original Null readings.

## Full-file audit and timestamp semantics

17,520 data rows, 4,444 columns, 77,841,360 household/time slots.
74,144,435 valid nonnegative finite readings; 3,696,925 missing (4.7493%), all blank cells.
The README describes NaN missingness; the actual wide file uses empty cells.
Zero negative/nonfinite/unparseable nonmissing readings; zero duplicate timestamps or
household/time keys; zero missing timestamps; zero off-grid timestamps; IDs unique and valid.
This detects format/value failures, not meter calibration, occupancy or behavioural anomalies.

First original label: `2013-01-01 00:30:00.0000000`.
Last original label: `2014-01-01 00:00:00.0000000`.
These describe all consumption intervals starting in calendar 2013.
Times are fixed GMT (UTC+00:00), never adjusted for BST. Labels mark interval END.
18:30 therefore covers [18:00,18:30); midnight belongs to the preceding consumption day.
Preserve source timestamp and kWh text, derive aware GMT end/start separately, and compute
`average_power_kw = energy_kwh / 0.5`. Do not localize source clocks as Europe/London.
Original files remain unchanged. Missing/invalid values are nullable, never zero-filled.
Every duplicate key is quarantined, even if repeated values agree. Invalid timestamps,
IDs and row widths fail preparation explicitly. Absent source timestamp rows are counted;
completeness retains the fixed 90 × 48 denominator, so gaps cannot inflate coverage.

## Prepared sample and selection

A single streaming pass audits every source cell and retains only 100 candidate columns
for 1 January–31 March 2013 (90 heating-season days), plus 7 November and 6 December for replay.
March is a heating-season shoulder month, not meteorological winter. The 90-day analysis
is not a continuous November-to-March winter across years; the source only covers 2013.
The parser never loads the full 588 MB CSV into memory or extracts it to disk.
Sort IDs by SHA-256 of `batteryflex-lcl-v1:ID`, retain the first 100, independent of column order.
No demand-based cherry-picking enters sampling. Prepared data: 441,600 rows, 436,634 valid,
4,966 missing, no duplicate/invalid retained readings. Parquet is about 2.16 MB.
Candidate/recommendation/replay CSVs and full audit JSON remain ignored local artifacts.

Metrics: completeness = valid unique Jan–Mar slots / 4,320; valid winter days = days with
48 valid intervals; daily energy mean uses those full days only; peak is maximum half-hour
average kW; evening = starts 16:00–19:30 (16:00–20:00); variability = sample standard deviation
(ddof=1) and coefficient of variation over valid half-hours. Event statistics cover the
17 original NESO half-hours, including the separately retained November/December dates.
Event means for incomplete candidates use available slots and are always accompanied by
completeness; recommendations require every slot. Combined demand propagates missing values.

100-candidate summary: mean coverage 98.99%, median 100%, range 63.29–100%; full days 55–90.
Daily kWh mean 11.2041, median 9.4061, range 0.2373–58.0717.
Peak kW range 0.606–9.646; evening kW mean 0.6594, median 0.5828, range 0.0081–2.5442.
92 candidates cover every replay interval. 71 pass all recommendation gates.

Gates: coverage ≥99%, ≥85 full days, mean complete-day energy 3–35 kWh, peak ≤15 kW,
all replay slots valid, every replay slot ≥0.05 kW and replay mean ≥0.3 kW.
These are transparent exploration thresholds, not population norms or battery constraints.
Sort passing households by mean daily energy then ID, select five evenly spaced ranks
(using numpy linspace + round). This provides low-to-high energy/pattern examples without
ranking on extreme peaks; it does not establish statistical representativeness or cluster diversity.
Household selection is event-conditioned and illustrative; no out-of-sample suitability is claimed.

## Five recommended actual households

| household_id | completeness | valid_winter_days | average_daily_kwh | peak_kw | mean_evening_kw | demand_std_kw | demand_cv | event_interval_completeness | event_mean_kw | event_min_kw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAC001391 | 1.0000 | 90 | 3.4949 | 1.4380 | 0.2634 | 0.1496 | 1.0272 | 1.0000 | 0.3139 | 0.1540 |
| MAC003288 | 1.0000 | 90 | 8.2387 | 3.0760 | 0.5388 | 0.2829 | 0.8242 | 1.0000 | 0.6669 | 0.2620 |
| MAC000143 | 1.0000 | 90 | 10.4509 | 3.2860 | 0.6276 | 0.3261 | 0.7490 | 1.0000 | 0.5819 | 0.1200 |
| MAC001534 | 0.9998 | 89 | 15.4507 | 3.8980 | 0.9280 | 0.4456 | 0.6930 | 1.0000 | 0.7706 | 0.4180 |
| MAC001395 | 0.9998 | 89 | 29.3130 | 6.3280 | 1.6557 | 0.8895 | 0.7276 | 1.0000 | 1.6402 | 0.4880 |

All five have every event interval. MAC001391, MAC003288 and MAC000143 have 90 complete
analysis days. MAC001534 and MAC001395 each lack one half-hour in Jan–Mar (89 complete days).
Their reasons are respectively lower-use, lower-middle, middle, upper-middle and higher-use
representatives among the passing sample, with measured evening and variability differences
shown above and in the app. These are actual household IDs, with no evidence of physical batteries.

## Historical replay mapping

Policy v1: for each NESO date, keep month and exact weekday in 2013; choose the nearest
day number, with earlier date breaking ties. This matches season/time-of-day/weekday without
optimising replay dates for demand. Holidays, weather and occupant behaviour are not matched.
All five dates are in GMT in both periods. No interpolation, resampling or overwriting of
source observations occurs. For a NESO interval [start,end), retrieve source reading at the
mapped END. Store both date/time pairs and unchanged internal scenario handle.

| neso_date | household_date | neso_start | neso_end | intervals | minimum_combined_kw | maximum_combined_kw |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-03-18 | 2013-03-19 | 2025-03-18T18:00:00+00:00 | 2025-03-18T19:00:00+00:00 | 2 | 4.7020 | 4.8420 |
| 2025-11-06 | 2013-11-07 | 2025-11-06T17:00:00+00:00 | 2025-11-06T18:00:00+00:00 | 2 | 2.3540 | 2.9100 |
| 2023-12-01 | 2013-12-06 | 2023-12-01T16:30:00+00:00 | 2023-12-01T18:00:00+00:00 | 3 | 4.0380 | 4.6800 |
| 2026-01-11 | 2013-01-13 | 2026-01-11T17:00:00+00:00 | 2026-01-11T19:00:00+00:00 | 4 | 3.9920 | 6.2400 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T16:00:00+00:00 | 2025-02-02T19:00:00+00:00 | 6 | 3.0620 | 4.1340 |

## All original half-hour demand comparisons

Each household column and combined demand below is kW. The mapped source END identifies
the original energy reading; each listed interval is exactly 30 minutes.

| neso_date | household_date | neso_start_gmt | neso_end_gmt | source_start_gmt | source_end_gmt | MAC001391 | MAC003288 | MAC000143 | MAC001534 | MAC001395 | combined_kw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-03-18 | 2013-03-19 | 2025-03-18T18:00:00+00:00 | 2025-03-18T18:30:00+00:00 | 2013-03-19T18:00:00+00:00 | 2013-03-19T18:30:00+00:00 | 0.1820 | 0.4280 | 0.7940 | 0.6680 | 2.6300 | 4.7020 |
| 2025-03-18 | 2013-03-19 | 2025-03-18T18:30:00+00:00 | 2025-03-18T19:00:00+00:00 | 2013-03-19T18:30:00+00:00 | 2013-03-19T19:00:00+00:00 | 0.2060 | 0.5340 | 0.9900 | 0.8940 | 2.2180 | 4.8420 |
| 2025-11-06 | 2013-11-07 | 2025-11-06T17:00:00+00:00 | 2025-11-06T17:30:00+00:00 | 2013-11-07T17:00:00+00:00 | 2013-11-07T17:30:00+00:00 | 0.2880 | 0.6320 | 0.4080 | 0.5380 | 0.4880 | 2.3540 |
| 2025-11-06 | 2013-11-07 | 2025-11-06T17:30:00+00:00 | 2025-11-06T18:00:00+00:00 | 2013-11-07T17:30:00+00:00 | 2013-11-07T18:00:00+00:00 | 0.2360 | 0.7860 | 0.5520 | 0.5620 | 0.7740 | 2.9100 |
| 2023-12-01 | 2013-12-06 | 2023-12-01T16:30:00+00:00 | 2023-12-01T17:00:00+00:00 | 2013-12-06T16:30:00+00:00 | 2013-12-06T17:00:00+00:00 | 0.5500 | 0.2620 | 0.6700 | 0.4180 | 2.7800 | 4.6800 |
| 2023-12-01 | 2013-12-06 | 2023-12-01T17:00:00+00:00 | 2023-12-01T17:30:00+00:00 | 2013-12-06T17:00:00+00:00 | 2013-12-06T17:30:00+00:00 | 0.4580 | 0.9900 | 0.6380 | 0.6600 | 1.2920 | 4.0380 |
| 2023-12-01 | 2013-12-06 | 2023-12-01T17:30:00+00:00 | 2023-12-01T18:00:00+00:00 | 2013-12-06T17:30:00+00:00 | 2013-12-06T18:00:00+00:00 | 0.5580 | 0.8720 | 0.6920 | 0.7000 | 1.2240 | 4.0460 |
| 2026-01-11 | 2013-01-13 | 2026-01-11T17:00:00+00:00 | 2026-01-11T17:30:00+00:00 | 2013-01-13T17:00:00+00:00 | 2013-01-13T17:30:00+00:00 | 0.4340 | 0.9680 | 0.6480 | 1.1380 | 1.7160 | 4.9040 |
| 2026-01-11 | 2013-01-13 | 2026-01-11T17:30:00+00:00 | 2026-01-11T18:00:00+00:00 | 2013-01-13T17:30:00+00:00 | 2013-01-13T18:00:00+00:00 | 0.4660 | 0.7140 | 0.8860 | 1.0320 | 1.4440 | 4.5420 |
| 2026-01-11 | 2013-01-13 | 2026-01-11T18:00:00+00:00 | 2026-01-11T18:30:00+00:00 | 2013-01-13T18:00:00+00:00 | 2013-01-13T18:30:00+00:00 | 0.2760 | 0.4020 | 0.7340 | 0.9440 | 1.6360 | 3.9920 |
| 2026-01-11 | 2013-01-13 | 2026-01-11T18:30:00+00:00 | 2026-01-11T19:00:00+00:00 | 2013-01-13T18:30:00+00:00 | 2013-01-13T19:00:00+00:00 | 0.2500 | 0.6920 | 1.0360 | 0.8080 | 3.4540 | 6.2400 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T16:00:00+00:00 | 2025-02-02T16:30:00+00:00 | 2013-02-03T16:00:00+00:00 | 2013-02-03T16:30:00+00:00 | 0.1540 | 0.5360 | 0.1240 | 0.6840 | 1.7640 | 3.2620 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T16:30:00+00:00 | 2025-02-02T17:00:00+00:00 | 2013-02-03T16:30:00+00:00 | 2013-02-03T17:00:00+00:00 | 0.2480 | 0.3760 | 0.1200 | 0.8940 | 1.4240 | 3.0620 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T17:00:00+00:00 | 2025-02-02T17:30:00+00:00 | 2013-02-03T17:00:00+00:00 | 2013-02-03T17:30:00+00:00 | 0.2940 | 0.8480 | 0.1860 | 0.7540 | 1.1780 | 3.2600 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T17:30:00+00:00 | 2025-02-02T18:00:00+00:00 | 2013-02-03T17:30:00+00:00 | 2013-02-03T18:00:00+00:00 | 0.2400 | 0.6880 | 0.5500 | 0.7200 | 1.0860 | 3.2840 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T18:00:00+00:00 | 2025-02-02T18:30:00+00:00 | 2013-02-03T18:00:00+00:00 | 2013-02-03T18:30:00+00:00 | 0.2320 | 0.3040 | 0.3780 | 0.9080 | 1.4760 | 3.2980 |
| 2025-02-02 | 2013-02-03 | 2025-02-02T18:30:00+00:00 | 2025-02-02T19:00:00+00:00 | 2013-02-03T18:30:00+00:00 | 2013-02-03T19:00:00+00:00 | 0.2640 | 1.3060 | 0.4860 | 0.7780 | 1.3000 | 4.1340 |

For example, NESO 18 March 2025 18:00–18:30 maps to source 19 March 2013 18:00–18:30.
MAC001391's original reading at 18:30 is 0.091 kWh, hence 0.182 kW; the five-house total
is 4.702 kW. The observation was not recorded on the NESO event date.

## Streamlit and reproduction

Data Explorer → enable **Low Carbon London Data Lab**. Provenance/quality panel, household
selector, inclusive date range, original kWh/end-label table, half-hour demand and complete-day
energy charts, 100-household comparison/scatter, five recommendations, mean daily/evening
profiles and event selector with per-house/combined half-hour kW. Both original date pairs
appear in the event table. National MW never becomes a household flexibility target.
The existing NESO selection and Advanced Historical Explorer remain available unchanged.

First acquisition (explicit command; package must be installed per README):

```powershell
.\.venv\Scripts\python.exe scripts/prepare_lcl.py --acquire
```

Local-only reprocessing:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_lcl.py
```

Raw archive publisher checksum is verified before processing. Saved artifact hashes, parser
version, source provenance, sample IDs, retained days and mapping version live in audit.json.
The UI reads only prepared data, verifies artifact hashes once per cached revision, and
invalidates on audit modification time. It neither acquires nor parses raw data on reruns.
A missing local preparation gives an explicit empty state; corrupt preparation gives an error.
Large/raw/prepared data and smoke-check snapshots are excluded by existing Git ignore rules.

## Scope and remaining feasibility inputs

Demand supports exploration of a future no-export discharge ceiling only. Battery capacity,
power, charge/discharge efficiency, initial/minimum SOC, charging opportunities and forecast
assumptions must be specified and checked later. A selected profile neither proves battery
installation nor sufficient energy/SOC to deliver an event. No 5 kW/10 kW commitment is assumed.
Single mapped days do not match weather, holidays, occupancy or changing electrification;
2013 standard-tariff London homes are not a representative modern VPP population. Very low or
high loads are screened heuristically; no appliance or demographic classifications are inferred.
The selection requires review before battery feasibility analysis. Task 03 stops here.

## Complete candidate statistics

| household_id | completeness | valid_winter_days | average_daily_kwh | peak_kw | mean_evening_kw | demand_std_kw | demand_cv | event_interval_completeness | event_mean_kw | event_min_kw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAC000026 | 0.9995 | 88 | 10.8814 | 4.7920 | 0.4757 | 0.3943 | 0.8643 | 1.0000 | 0.4611 | 0.2380 |
| MAC000127 | 1.0000 | 90 | 8.8795 | 2.9220 | 0.4787 | 0.2994 | 0.8092 | 1.0000 | 0.5728 | 0.1460 |
| MAC000143 | 1.0000 | 90 | 10.4509 | 3.2860 | 0.6276 | 0.3261 | 0.7490 | 1.0000 | 0.5819 | 0.1200 |
| MAC000151 | 0.9995 | 88 | 4.1521 | 1.7860 | 0.3024 | 0.1254 | 0.7251 | 1.0000 | 0.3452 | 0.2480 |
| MAC000227 | 0.9991 | 89 | 15.7873 | 5.1100 | 1.1267 | 0.6502 | 0.9873 | 1.0000 | 1.3216 | 0.4360 |
| MAC000296 | 0.9998 | 89 | 22.0010 | 6.0080 | 1.4727 | 1.0984 | 1.1950 | 1.0000 | 1.5089 | 0.4080 |
| MAC000331 | 1.0000 | 90 | 29.1240 | 7.3540 | 0.4178 | 2.0547 | 1.6932 | 1.0000 | 0.4600 | 0.1320 |
| MAC000353 | 0.9995 | 88 | 6.4391 | 2.1760 | 0.4298 | 0.2565 | 0.9532 | 1.0000 | 0.3822 | 0.1180 |
| MAC000359 | 1.0000 | 90 | 15.9438 | 5.9300 | 0.9480 | 0.6445 | 0.9702 | 1.0000 | 1.7687 | 0.3480 |
| MAC000412 | 0.9993 | 88 | 9.0556 | 3.6120 | 0.4893 | 0.1949 | 0.5161 | 1.0000 | 0.4769 | 0.1620 |
| MAC000424 | 1.0000 | 90 | 8.4737 | 2.6140 | 0.6647 | 0.3430 | 0.9715 | 1.0000 | 0.7671 | 0.2200 |
| MAC000604 | 1.0000 | 90 | 13.6206 | 3.8500 | 0.6834 | 0.3649 | 0.6429 | 1.0000 | 0.5580 | 0.1920 |
| MAC000615 | 1.0000 | 90 | 3.3619 | 1.0940 | 0.1224 | 0.1723 | 1.2299 | 1.0000 | 0.0578 | 0.0000 |
| MAC000630 | 1.0000 | 90 | 15.9108 | 5.8900 | 0.9552 | 0.7854 | 1.1847 | 1.0000 | 1.1986 | 0.3920 |
| MAC000636 | 0.9984 | 88 | 0.2373 | 0.6060 | 0.0081 | 0.0256 | 2.6001 | 0.7059 | 0.0000 | 0.0000 |
| MAC000676 | 1.0000 | 90 | 7.8952 | 1.6100 | 0.5137 | 0.2113 | 0.6422 | 1.0000 | 0.5158 | 0.1940 |
| MAC000693 | 1.0000 | 90 | 58.0717 | 7.2300 | 2.5442 | 0.9867 | 0.4078 | 1.0000 | 2.7213 | 1.0020 |
| MAC000699 | 0.9998 | 89 | 6.4579 | 3.1500 | 0.4354 | 0.2538 | 0.9407 | 1.0000 | 0.6086 | 0.2640 |
| MAC000776 | 1.0000 | 90 | 4.8644 | 1.3900 | 0.2647 | 0.1208 | 0.5960 | 1.0000 | 0.2042 | 0.1380 |
| MAC000825 | 1.0000 | 90 | 15.3823 | 5.6920 | 1.1558 | 0.6773 | 1.0568 | 1.0000 | 1.5295 | 0.1280 |
| MAC000891 | 1.0000 | 90 | 5.7231 | 5.2220 | 0.3728 | 0.3163 | 1.3265 | 1.0000 | 0.3622 | 0.0200 |
| MAC000905 | 1.0000 | 90 | 8.3519 | 3.4760 | 0.3469 | 0.2396 | 0.6886 | 1.0000 | 0.2921 | 0.2120 |
| MAC000941 | 1.0000 | 90 | 11.9903 | 4.4360 | 0.7034 | 0.4051 | 0.8109 | 1.0000 | 0.6978 | 0.2660 |
| MAC001126 | 0.9998 | 89 | 13.8856 | 2.6580 | 0.7061 | 0.4193 | 0.7228 | 1.0000 | 0.7142 | 0.2160 |
| MAC001217 | 1.0000 | 90 | 10.1493 | 4.2880 | 0.8765 | 0.5011 | 1.1850 | 1.0000 | 0.8518 | 0.1660 |
| MAC001291 | 1.0000 | 90 | 3.3060 | 2.3840 | 0.2326 | 0.1908 | 1.3853 | 1.0000 | 0.3116 | 0.0480 |
| MAC001361 | 1.0000 | 90 | 11.6590 | 3.1700 | 0.7769 | 0.3110 | 0.6402 | 1.0000 | 0.8822 | 0.5740 |
| MAC001387 | 0.9998 | 89 | 4.6253 | 2.3860 | 0.1827 | 0.2174 | 1.1227 | 1.0000 | 0.2485 | 0.0660 |
| MAC001391 | 1.0000 | 90 | 3.4949 | 1.4380 | 0.2634 | 0.1496 | 1.0272 | 1.0000 | 0.3139 | 0.1540 |
| MAC001395 | 0.9998 | 89 | 29.3130 | 6.3280 | 1.6557 | 0.8895 | 0.7276 | 1.0000 | 1.6402 | 0.4880 |
| MAC001483 | 1.0000 | 90 | 3.6352 | 1.9920 | 0.1436 | 0.1880 | 1.2411 | 1.0000 | 0.1481 | 0.0960 |
| MAC001534 | 0.9998 | 89 | 15.4507 | 3.8980 | 0.9280 | 0.4456 | 0.6930 | 1.0000 | 0.7706 | 0.4180 |
| MAC001625 | 1.0000 | 90 | 16.0363 | 5.6940 | 0.8522 | 0.6467 | 0.9679 | 1.0000 | 1.0894 | 0.3200 |
| MAC001746 | 1.0000 | 90 | 19.2961 | 9.6460 | 1.5122 | 0.9573 | 1.1906 | 1.0000 | 1.3931 | 0.2320 |
| MAC001748 | 0.6331 | 56 | 6.7844 | 2.8880 | 0.3374 | 0.2149 | 0.7542 | 0.5294 | 0.4109 | 0.3560 |
| MAC001762 | 1.0000 | 90 | 9.2166 | 4.4240 | 0.7453 | 0.4568 | 1.1895 | 0.8235 | 1.3359 | 0.1480 |
| MAC001774 | 0.7444 | 67 | 4.9749 | 3.6580 | 0.3275 | 0.2816 | 1.3586 | 0.8824 | 0.3840 | 0.0840 |
| MAC001779 | 1.0000 | 90 | 8.7259 | 2.8600 | 0.6146 | 0.2186 | 0.6012 | 1.0000 | 0.4667 | 0.2200 |
| MAC001839 | 0.9998 | 89 | 9.9509 | 2.6680 | 0.5360 | 0.2799 | 0.6748 | 1.0000 | 0.4131 | 0.2380 |
| MAC001874 | 1.0000 | 90 | 22.0062 | 3.1660 | 0.9763 | 0.2768 | 0.3018 | 1.0000 | 0.9582 | 0.7300 |
| MAC002031 | 0.9998 | 89 | 9.9205 | 4.0680 | 0.8198 | 0.3774 | 0.9129 | 0.7059 | 0.6533 | 0.4040 |
| MAC002037 | 1.0000 | 90 | 14.9523 | 5.5520 | 1.1663 | 0.6787 | 1.0895 | 1.0000 | 1.9886 | 0.8900 |
| MAC002296 | 1.0000 | 90 | 20.8055 | 4.0720 | 1.7254 | 0.9087 | 1.0482 | 1.0000 | 1.1466 | 0.2800 |
| MAC002302 | 1.0000 | 90 | 9.1327 | 4.6300 | 0.5891 | 0.4532 | 1.1909 | 1.0000 | 0.4685 | 0.2780 |
| MAC002313 | 0.6329 | 55 | 7.4811 | 2.4360 | 0.2810 | 0.3926 | 1.2534 | 0.5882 | 0.2706 | 0.1200 |
| MAC002340 | 1.0000 | 90 | 9.4159 | 5.1240 | 0.2380 | 0.6301 | 1.6059 | 1.0000 | 0.2621 | 0.1100 |
| MAC002381 | 0.9998 | 89 | 10.3692 | 4.1060 | 0.6030 | 0.3589 | 0.8306 | 1.0000 | 0.5889 | 0.2960 |
| MAC002393 | 1.0000 | 90 | 9.2062 | 2.2680 | 0.5344 | 0.2595 | 0.6766 | 1.0000 | 0.5231 | 0.3440 |
| MAC002397 | 0.9998 | 89 | 15.6339 | 3.5280 | 0.8814 | 0.4028 | 0.6153 | 1.0000 | 0.8732 | 0.1740 |
| MAC002478 | 1.0000 | 90 | 19.1332 | 5.8060 | 1.2438 | 0.7790 | 0.9772 | 1.0000 | 2.0778 | 0.1800 |
| MAC002616 | 1.0000 | 90 | 7.6439 | 3.7960 | 0.4112 | 0.3816 | 1.1980 | 1.0000 | 0.3544 | 0.0940 |
| MAC002674 | 1.0000 | 90 | 2.5697 | 1.6200 | 0.2381 | 0.1378 | 1.2873 | 1.0000 | 0.3198 | 0.0200 |
| MAC002685 | 1.0000 | 90 | 6.1111 | 3.9920 | 0.3811 | 0.2781 | 1.0921 | 1.0000 | 0.4011 | 0.1360 |
| MAC002706 | 0.9998 | 89 | 10.7020 | 5.1460 | 0.7474 | 0.4813 | 1.0797 | 1.0000 | 0.8705 | 0.4800 |
| MAC002721 | 0.9991 | 88 | 9.1783 | 2.2280 | 0.8051 | 0.4325 | 1.1340 | 1.0000 | 0.8373 | 0.0000 |
| MAC002731 | 0.9998 | 89 | 5.8200 | 3.1980 | 0.3746 | 0.3106 | 1.2831 | 1.0000 | 0.6366 | 0.1580 |
| MAC002746 | 1.0000 | 90 | 3.4921 | 1.6260 | 0.1410 | 0.1473 | 1.0125 | 1.0000 | 0.0747 | 0.0360 |
| MAC002782 | 1.0000 | 90 | 10.3606 | 4.0520 | 0.5779 | 0.3696 | 0.8562 | 1.0000 | 0.6580 | 0.3580 |
| MAC002793 | 0.9998 | 89 | 11.3671 | 3.3720 | 0.7555 | 0.3575 | 0.7558 | 1.0000 | 0.8664 | 0.3160 |
| MAC002835 | 1.0000 | 90 | 2.1329 | 1.2440 | 0.0922 | 0.0655 | 0.7365 | 0.7059 | 0.0930 | 0.0860 |
| MAC002900 | 1.0000 | 90 | 13.7688 | 4.8240 | 0.7412 | 0.4544 | 0.7921 | 1.0000 | 0.8346 | 0.3040 |
| MAC002913 | 1.0000 | 90 | 48.2440 | 4.9180 | 2.2515 | 0.6580 | 0.3273 | 1.0000 | 2.0991 | 1.3700 |
| MAC002939 | 0.9993 | 88 | 9.3963 | 3.8140 | 0.7151 | 0.4028 | 1.0249 | 1.0000 | 0.8633 | 0.3880 |
| MAC002941 | 0.9998 | 89 | 18.8656 | 4.6300 | 1.2485 | 0.6872 | 0.8779 | 1.0000 | 1.6992 | 0.1740 |
| MAC002961 | 1.0000 | 90 | 9.4248 | 2.2740 | 0.5890 | 0.1985 | 0.5054 | 1.0000 | 0.7431 | 0.5400 |
| MAC002974 | 1.0000 | 90 | 10.9308 | 3.2240 | 0.5270 | 0.4953 | 1.0875 | 1.0000 | 0.5862 | 0.0120 |
| MAC003021 | 1.0000 | 90 | 5.1068 | 1.7180 | 0.3289 | 0.1873 | 0.8800 | 1.0000 | 0.4995 | 0.0680 |
| MAC003273 | 1.0000 | 90 | 14.4407 | 6.2700 | 0.8553 | 0.7955 | 1.3221 | 1.0000 | 0.7240 | 0.0680 |
| MAC003288 | 1.0000 | 90 | 8.2387 | 3.0760 | 0.5388 | 0.2829 | 0.8242 | 1.0000 | 0.6669 | 0.2620 |
| MAC003309 | 1.0000 | 90 | 10.1351 | 2.6420 | 0.7418 | 0.3067 | 0.7263 | 1.0000 | 0.7994 | 0.2340 |
| MAC003448 | 0.9998 | 89 | 5.1109 | 1.7980 | 0.3051 | 0.1756 | 0.8252 | 1.0000 | 0.4228 | 0.1980 |
| MAC003469 | 1.0000 | 90 | 9.0626 | 4.1480 | 0.7697 | 0.5531 | 1.4647 | 1.0000 | 0.6009 | 0.1420 |
| MAC003563 | 1.0000 | 90 | 10.1035 | 3.7600 | 0.6565 | 0.3375 | 0.8018 | 1.0000 | 0.6979 | 0.2740 |
| MAC003601 | 1.0000 | 90 | 5.7953 | 2.2380 | 0.3826 | 0.2128 | 0.8811 | 1.0000 | 0.3505 | 0.1580 |
| MAC003662 | 0.9995 | 88 | 11.9719 | 3.9080 | 0.7884 | 0.3908 | 0.7854 | 0.8235 | 0.5834 | 0.4160 |
| MAC003694 | 1.0000 | 90 | 1.9868 | 1.5240 | 0.1442 | 0.1027 | 1.2411 | 1.0000 | 0.1641 | 0.0160 |
| MAC003696 | 1.0000 | 90 | 5.6613 | 1.6260 | 0.3790 | 0.2091 | 0.8866 | 1.0000 | 0.4019 | 0.0400 |
| MAC003742 | 1.0000 | 90 | 5.1317 | 4.3240 | 0.1670 | 0.3836 | 1.7940 | 1.0000 | 0.1845 | 0.0880 |
| MAC003750 | 1.0000 | 90 | 16.7755 | 4.6500 | 0.9584 | 0.5601 | 0.8014 | 1.0000 | 1.5039 | 0.2980 |
| MAC003763 | 1.0000 | 90 | 4.9893 | 3.1840 | 0.3456 | 0.3793 | 1.8245 | 1.0000 | 0.6604 | 0.0500 |
| MAC003900 | 1.0000 | 90 | 11.4334 | 3.9900 | 0.4810 | 0.4128 | 0.8666 | 1.0000 | 0.7202 | 0.2880 |
| MAC004038 | 1.0000 | 90 | 5.7765 | 3.4600 | 0.2978 | 0.2325 | 0.9659 | 1.0000 | 0.6671 | 0.0220 |
| MAC004128 | 0.9998 | 89 | 16.5640 | 4.5700 | 1.1956 | 0.5668 | 0.8222 | 1.0000 | 1.4004 | 0.8620 |
| MAC004136 | 0.9998 | 89 | 8.0399 | 1.7000 | 0.3607 | 0.1785 | 0.5308 | 1.0000 | 0.3075 | 0.0780 |
| MAC004343 | 0.9998 | 89 | 13.3347 | 5.4320 | 0.9444 | 0.5574 | 1.0075 | 1.0000 | 1.1586 | 0.1660 |
| MAC004345 | 0.9968 | 86 | 21.0447 | 5.6600 | 1.4056 | 0.7107 | 0.8070 | 1.0000 | 1.2980 | 0.2900 |
| MAC004372 | 1.0000 | 90 | 10.1714 | 3.5600 | 0.6765 | 0.5194 | 1.2256 | 1.0000 | 0.7944 | 0.1980 |
| MAC004387 | 0.9995 | 88 | 4.9454 | 2.8980 | 0.3495 | 0.1951 | 0.9398 | 1.0000 | 0.3346 | 0.0640 |
| MAC004477 | 1.0000 | 90 | 6.3804 | 3.2500 | 0.3459 | 0.2339 | 0.8798 | 1.0000 | 0.3484 | 0.0940 |
| MAC004628 | 1.0000 | 90 | 14.1973 | 3.5920 | 0.7844 | 0.6254 | 1.0572 | 1.0000 | 1.0404 | 0.2800 |
| MAC004820 | 0.9998 | 89 | 6.0382 | 1.9540 | 0.3150 | 0.1649 | 0.6541 | 1.0000 | 0.2998 | 0.2000 |
| MAC004938 | 1.0000 | 90 | 5.5194 | 2.4700 | 0.3491 | 0.2340 | 1.0177 | 1.0000 | 0.5380 | 0.2140 |
| MAC005052 | 1.0000 | 90 | 20.6604 | 4.1780 | 1.0939 | 0.6421 | 0.7459 | 1.0000 | 1.4518 | 0.4780 |
| MAC005109 | 1.0000 | 90 | 3.2287 | 2.7060 | 0.3257 | 0.2028 | 1.5072 | 1.0000 | 0.2878 | 0.0100 |
| MAC005237 | 0.9998 | 89 | 10.6015 | 3.6800 | 0.6470 | 0.3594 | 0.8137 | 1.0000 | 0.7296 | 0.3760 |
| MAC005297 | 1.0000 | 90 | 7.7730 | 2.7620 | 0.4890 | 0.2991 | 0.9236 | 1.0000 | 0.5814 | 0.1760 |
| MAC005315 | 1.0000 | 90 | 23.6400 | 4.9620 | 1.2816 | 0.6136 | 0.6230 | 1.0000 | 1.2432 | 0.1540 |
| MAC005357 | 1.0000 | 90 | 12.4981 | 2.3280 | 0.5877 | 0.1679 | 0.3224 | 1.0000 | 0.5847 | 0.1960 |
| MAC005438 | 0.9995 | 89 | 7.0715 | 1.8960 | 0.3704 | 0.1629 | 0.5536 | 1.0000 | 0.3721 | 0.2560 |
| MAC005540 | 1.0000 | 90 | 5.3614 | 3.4300 | 0.3950 | 0.3129 | 1.4005 | 1.0000 | 0.1665 | 0.0680 |

## Engineering verification and changed files

Final regression: 95 tests passed (66 existing, 29 new). Ruff lint and format checks passed;
ty check passed for src, the preparation script and app.py. Running localhost agent API
returned ready for local prepared data, all 2/2/3/4/6 event half-hour tables, household/date
filters and provenance. No new server warnings or tracebacks; temporary server stopped.
Browser rendering was not separately tested. Existing NESO logic/data remained unchanged.

New source modules: lcl_source.py, lcl.py, lcl_analysis.py and ui/lcl_lab.py; new preparation
script scripts/prepare_lcl.py; new tests test_lcl.py and test_lcl_ui.py. Updated Data Explorer,
explicit pandas/numpy/pyarrow dependencies in pyproject.toml, README and architecture,
contracts, plan, decisions and current handoff. See CURRENT_HANDOFF.md for the exact file list.
No staging/commits; existing parent Git changes preserved. Completed Task 03 only.

## Task 03B — presentation finalisation (17 November 2026)

The reviewed data, 100 candidates, five households, statistics and mappings in this report
remain unchanged. The finalised interface now provides a default unselected Household Explorer
with five recommended choices and a separate all-100 scope, household information/help,
original readings with CSV download, demand/daily/typical charts, a separate five-house
comparison and an unselected five-event replay. Advanced provenance is collapsed in its own
view. See [final UI guide](LCL_UI_GUIDE.md) for navigation, units/aggregation periods,
98-test verification and browser review. No Task 04 work was started.
