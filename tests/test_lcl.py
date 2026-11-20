"""Small synthetic parser fixtures, never presented as real household observations."""

import csv
import hashlib
import io
from datetime import UTC, date, timedelta
from zipfile import ZipFile

import pandas as pd
import pytest

from batteryflex.lcl import endpoint, energy, inspect_archive, parse_observations, sample_ids
from batteryflex.lcl_analysis import map_day, recommend, replay, statistics
from batteryflex.lcl_source import acquire


def observation(timestamp="2013-01-01 00:30:00.0000000", value="0.25", household="MAC000001"):
    return {"household_id": household, "source_timestamp": timestamp, "source_kwh": value}


def test_energy_conversion_original_text_and_midnight():
    frame = parse_observations([observation("2014-01-01 00:00:00.0000000", " 0.25 ")])
    row = frame.iloc[0]
    assert row.source_kwh == " 0.25 "
    assert row.energy_kwh == 0.25 and row.average_power_kw == 0.5
    assert row.interval_start_gmt.isoformat() == "2013-12-31T23:30:00+00:00"
    assert row.source_timestamp == "2014-01-01 00:00:00.0000000"


@pytest.mark.parametrize(
    "value,quality",
    [
        ("", "missing"),
        ("NaN", "missing"),
        ("Null", "missing"),
        ("-0.01", "invalid"),
        ("inf", "invalid"),
        ("bad", "invalid"),
        ("0", "valid"),
    ],
)
def test_missing_invalid_not_zero(value, quality):
    number, flag = energy(value)
    assert flag == quality
    assert (number == 0) if quality == "valid" else (number is None)


def test_duplicate_keys_all_quarantined():
    frame = parse_observations([observation(), observation(value="0.5")])
    assert frame.quality.tolist() == ["duplicate", "duplicate"]
    assert frame.average_power_kw.isna().all()


@pytest.mark.parametrize(
    "text",
    [
        "2013-01-01 00:15:00",
        "2013-01-01 00:30:01",
        "2013-01-01 00:30:00.0000001",
        "2013-01-01T00:30:00+01:00",
    ],
)
def test_reject_off_grid_or_ambiguous_timestamp(text):
    with pytest.raises(ValueError):
        endpoint(text)


def test_fixed_gmt_on_both_dst_transitions():
    for day in ("2013-03-31", "2013-10-27", "2013-07-01"):
        assert endpoint(f"{day} 01:30:00").utcoffset() == timedelta(0)
        assert endpoint(f"{day} 01:30:00").tzinfo == UTC


def test_streaming_archive_schema_missing_and_duplicates(tmp_path):
    path = tmp_path / "source.zip"
    stream = io.StringIO()
    csv.writer(stream).writerows(
        [
            ["DateTime", "MAC000001", "MAC000002"],
            ["2013-01-01 00:30:00", ".25", "NaN"],
            ["2013-01-01 01:00:00", "-.1", "0"],
            ["2013-01-01 01:00:00", ".2", "0"],
            ["2013-01-01 02:00:00", ".2", "0"],
        ]
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("source.csv", stream.getvalue())
    frame, audit = inspect_archive(path, {date(2013, 1, 1)}, count=2)
    assert audit["missing"] == 1 and audit["invalid"] == 1
    assert audit["missing_timestamp_rows"] == 1
    assert audit["duplicate_household_timestamp_keys"] == 2
    assert len(frame) == 8
    assert (frame.quality == "duplicate").sum() == 4


def test_sampling_order_independent_and_id_integrity():
    ids = [f"MAC{n:06d}" for n in range(100)]
    assert sample_ids(ids, 50) == sample_ids(ids[::-1], 50)
    assert len(set(sample_ids(ids, 50))) == 50
    for invalid in (["MAC000001", "MAC000001"], ["MAC1"]):
        with pytest.raises(ValueError):
            sample_ids(invalid)


@pytest.mark.parametrize(
    "event,mapped",
    [
        ("2025-03-18", "2013-03-19"),
        ("2025-11-06", "2013-11-07"),
        ("2023-12-01", "2013-12-06"),
        ("2026-01-11", "2013-01-13"),
        ("2025-02-02", "2013-02-03"),
    ],
)
def test_mapping_exact_weekday_and_month(event, mapped):
    day = date.fromisoformat(event)
    result = map_day(day)
    assert str(result) == mapped
    assert result.weekday() == day.weekday() and result.month == day.month


def test_replay_uses_endpoint_not_start_and_retains_all_17_intervals():
    frame = parse_observations(
        [
            observation("2013-03-19 18:00:00", "99"),
            observation("2013-03-19 18:30:00", ".25"),
            observation("2013-03-19 19:00:00", ".5"),
        ]
    )
    result = replay(frame, ["MAC000001"])
    assert len(result) == 17
    assert result.iloc[:2].MAC000001.tolist() == [0.5, 1.0]
    assert result.iloc[:2].combined_kw.tolist() == [0.5, 1.0]
    assert result.iloc[2:].combined_kw.isna().all()
    assert result.iloc[0].neso_date == "2025-03-18"
    assert result.iloc[0].household_date == "2013-03-19"


def test_statistics_complete_days_and_missing_slot():
    stamps = pd.date_range("2013-01-01 00:30", periods=96, freq="30min")
    rows = [observation(str(t), ".25" if i else "") for i, t in enumerate(stamps)]
    stats = statistics(parse_observations(rows)).iloc[0]
    assert stats.valid_winter_days == 1
    assert stats.average_daily_kwh == 12
    assert stats.completeness == 95 / (90 * 48)
    assert stats.mean_evening_kw == 0.5


def test_selection_reproducible_and_quality_gates():
    stats = pd.DataFrame(
        [
            dict(
                household_id=f"MAC{n:06d}",
                completeness=1,
                valid_winter_days=90,
                average_daily_kwh=n + 3,
                peak_kw=4,
                event_interval_completeness=1,
                event_min_kw=0.1,
                event_mean_kw=0.5,
            )
            for n in range(10)
        ]
    )
    chosen = recommend(stats)
    assert (
        chosen.household_id.tolist()
        == recommend(stats.sample(frac=1, random_state=4)).household_id.tolist()
    )
    stats.loc[:5, "event_min_kw"] = 0
    with pytest.raises(ValueError, match="Only 4"):
        recommend(stats)


def test_acquisition_rejects_existing_corruption_without_network(tmp_path, monkeypatch):
    (tmp_path / "README").write_text("corrupted")
    monkeypatch.setattr("batteryflex.lcl_source.urlopen", lambda *a, **k: pytest.fail("network"))
    with pytest.raises(ValueError, match="Existing source checksum"):
        acquire(tmp_path)


def test_acquisition_reuses_verified_local_files(tmp_path, monkeypatch):
    files = {}
    for name in ("README", "LCL_2013_kWh.csv.zip"):
        content = name.encode()
        (tmp_path / name).write_bytes(content)
        files[name] = ("fixture-file-id", hashlib.md5(content).hexdigest())
    monkeypatch.setattr("batteryflex.lcl_source.FILES", files)
    monkeypatch.setattr("batteryflex.lcl_source.urlopen", lambda *a, **k: pytest.fail("network"))
    assert acquire(tmp_path) == tmp_path / "LCL_2013_kWh.csv.zip"
    provenance = (tmp_path / "acquisition.json").read_bytes()
    acquire(tmp_path)
    assert (tmp_path / "acquisition.json").read_bytes() == provenance
