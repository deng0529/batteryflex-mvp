# Task 05D — Phase A completed before model rebuilding

18 November 2026. The existing annual archive was audited first, with its original publisher MD5
and SHA-256 unchanged. It contains all 17,520 2013 half-hour labels for every reviewed home.
Original annual missing cells: MAC001391 2, MAC003288 1, MAC000143 1, MAC001534 3, MAC001395 2.
There are no duplicate/invalid retained 2013 cells or missing timestamp rows in that archive.

The same five original event/replay pairs are unchanged: 18 Mar 2025 -> 19 Mar 2013;
6 Nov 2025 -> 7 Nov 2013; 1 Dec 2023 -> 6 Dec 2013; 11 Jan 2026 -> 13 Jan 2013;
2 Feb 2025 -> 3 Feb 2013. The windows/durations remain 18:00–19:00 (60 minutes),
17:00–18:00 (60), 16:30–18:00 (90), 17:00–19:00 (120), 16:00–19:00 (180), respectively.
Internal BatteryFlex IDs are not official NESO event IDs; original raw source records identify them.

## Pre-2013 investigation and quality

The original UK Power Networks release, linked by the existing 4TU README and the official
[London Datastore](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d),
provides earlier history. The publisher's partitioned ZIP was acquired only after the local annual
audit demonstrated the January history limitation. Its acquisition metadata/SHA-256 are retained.
All 168 CSV members were scanned and ZIP CRC-checked. The same five IDs were retained, all Std tariff.
No household substitution, observations from mirrors, or synthetic consumption was used.

| Household | First original interval start GMT | Latest original interval end GMT |
| --- | --- | --- |
| MAC001391 | 2012-05-17 12:30:00+00:00 | 2014-02-28 00:00:00+00:00 |
| MAC003288 | 2012-09-21 11:00:00+00:00 | 2014-02-28 00:00:00+00:00 |
| MAC000143 | 2011-12-16 09:30:00+00:00 | 2014-02-28 00:00:00+00:00 |
| MAC001534 | 2012-05-22 10:30:00+00:00 | 2014-02-28 00:00:00+00:00 |
| MAC001395 | 2012-05-17 13:00:00+00:00 | 2014-02-28 00:00:00+00:00 |

All 87,531 valid overlapping original/refactored 2013 readings agree numerically. The original
release has five off-grid timestamp rows and 216 duplicate-key source rows across these homes;
they are quarantined with source values/locations preserved. Duplicate pairs become missing-quality
keys, never averages. For the expanded version, the existing validated refactored 2013 rows take
explicit priority and remain unchanged; only original observations before 1 January 2013 are added.
The resulting candidate dataset has 143,299 unique retained household/interval rows: 143,252 valid,
38 duplicate-quality nonnumeric placeholders and 9 explicit missing cells. Unretained calendar slots
remain absent/missing in aligned views; there is no interpolation or forward fill. Fixed GMT,
interval-END labels and kWh/0.5 = average kW semantics are preserved.

## Shared chronology and feature admission decision

Use the same predeclared rolling policy for all events: up to 90 calendar training days,
then 14 validation days, then 14 broader holdout days ending the day before the replay origin.
Require >=28 complete usable training origins and >=7 validation/holdout origins per home.
The event's midnight GMT origin predicts 48 half-hours. All fitting/scaling/selection precedes the
origin. The broader pre-origin holdout is distinct from the final event day/window.

The legacy feature schema requires every one of 336 intervening historical half-hours. It fails
at January/MAC001395 and November/MAC001391 because of measured gaps, despite complete actual
previous-day and previous-weekday profiles. Use an explicit new reduced schema for ALL events:
calendar/horizon features, direct previous-day/week profile lags, and mean/std of each of those
two complete 48-step profiles. Do not use the intervening-week rolling statistics. This changes
only the documented feature schema; it never fills missing observations. The decision is based
on coverage, before examining any event forecast errors. Original Task 05B/05C schemas/models stay intact.

All 25 household/event combinations have complete previous-day/week profiles, full-day actuals
and event-period actual load. All support Ridge and LightGBM under this shared reduced policy.
Usable counts (origins; multiply by 48 for target observations):

| Household | Replay date | Train | Validation | Broader holdout | Ridge / LightGBM feasible |
| --- | --- | ---: | ---: | ---: | --- |
| MAC001391 | 2013-03-19 | 86 | 14 | 14 | True |
| MAC003288 | 2013-03-19 | 86 | 14 | 14 | True |
| MAC000143 | 2013-03-19 | 86 | 14 | 14 | True |
| MAC001534 | 2013-03-19 | 86 | 14 | 11 | True |
| MAC001395 | 2013-03-19 | 83 | 14 | 14 | True |
| MAC001391 | 2013-11-07 | 90 | 14 | 12 | True |
| MAC003288 | 2013-11-07 | 87 | 14 | 14 | True |
| MAC000143 | 2013-11-07 | 90 | 14 | 14 | True |
| MAC001534 | 2013-11-07 | 87 | 14 | 14 | True |
| MAC001395 | 2013-11-07 | 90 | 14 | 14 | True |
| MAC001391 | 2013-12-06 | 88 | 13 | 14 | True |
| MAC003288 | 2013-12-06 | 90 | 14 | 14 | True |
| MAC000143 | 2013-12-06 | 90 | 13 | 12 | True |
| MAC001534 | 2013-12-06 | 87 | 14 | 14 | True |
| MAC001395 | 2013-12-06 | 90 | 14 | 14 | True |
| MAC001391 | 2013-01-13 | 79 | 11 | 14 | True |
| MAC003288 | 2013-01-13 | 72 | 11 | 14 | True |
| MAC000143 | 2013-01-13 | 79 | 11 | 14 | True |
| MAC001534 | 2013-01-13 | 77 | 11 | 14 | True |
| MAC001395 | 2013-01-13 | 79 | 11 | 12 | True |
| MAC001391 | 2013-02-03 | 79 | 14 | 14 | True |
| MAC003288 | 2013-02-03 | 81 | 14 | 14 | True |
| MAC000143 | 2013-02-03 | 81 | 14 | 14 | True |
| MAC001534 | 2013-02-03 | 78 | 14 | 14 | True |
| MAC001395 | 2013-02-03 | 79 | 11 | 14 | True |

The full 25-row coverage matrix records original event/window, replay origin, first/latest history,
missing history intervals, lag availability and actual-event availability in
`outputs/task05d/coverage-matrix.csv`. It will be persisted as a data-quality artifact with the new
immutable dataset. No model fitting was performed before completion of this Phase A decision.
