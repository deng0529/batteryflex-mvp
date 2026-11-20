"""Hand-calculated peaks and reconstruction of pinned admitted training samples."""

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest
from test_forecast_training import frame as frame_fixture

from batteryflex.neso_manifest import load_selection
from batteryflex.peak_analysis import peak_diagnostics, training_context
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.ui.event_forecasts import full_day_spec


def sample():
    times = pd.date_range("2013-03-19", periods=48, freq="30min", tz="UTC")
    actual, predicted = np.ones(48), np.ones(48)
    actual[20], actual[21], predicted[21] = 10, 4, 8
    full = pd.DataFrame(
        dict(
            partition="full_day",
            household="Portfolio",
            method="LightGBM",
            interval_start=times,
            actual=actual,
            prediction=predicted,
        )
    )
    return pd.concat([full, full.iloc[20:22].assign(partition="event_window")], ignore_index=True)


def test_peak_bias_timing_high_demand_and_event_underforecast():
    result = peak_diagnostics(sample(), {"Portfolio": 2}).iloc[0]
    assert result.peak_magnitude_error_kw == -2
    assert result.peak_timing_error_minutes == 30
    assert result.high_demand_intervals == 2
    assert result.high_demand_mae_kw == 6.5
    assert result.event_underforecast_kwh == 4.5
    assert result.actual_peak_in_event


def test_peak_ties_use_earliest_and_no_high_intervals_is_undefined():
    data = sample()
    data.loc[data.partition.eq("full_day") & data.interval_start.dt.hour.eq(11), "prediction"] = 8
    result = peak_diagnostics(data, {"Portfolio": 10}).iloc[0]
    assert result.peak_timing_error_minutes == 30
    assert result.predicted_peak_time.endswith("10:30:00+00:00")
    assert result.high_demand_intervals == 0 and np.isnan(result.high_demand_mae_kw)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "nonfinite"])
def test_incomplete_daily_diagnostics_are_rejected(fault):
    data = sample()
    if fault == "missing":
        data = data.iloc[1:]
    elif fault == "duplicate":
        data = pd.concat([data, data.iloc[:1]])
    else:
        data.loc[0, "actual"] = np.nan
    with pytest.raises(ValueError, match="complete measured 48-step"):
        peak_diagnostics(data, {"Portfolio": 2})


def metadata():
    return dict(
        request=dict(
            households=list(HOUSEHOLDS),
            forecast_origin="2013-01-14T00:00:00+00:00",
            periods={
                "training": dict(start="2013-01-08", end="2013-01-09"),
                "validation": dict(start="2013-01-10", end="2013-01-11"),
                "holdout": dict(start="2013-01-12", end="2013-01-13"),
            },
        ),
        counts={h: dict(training=2, validation=2, holdout=2) for h in HOUSEHOLDS},
    )


def test_saved_ranges_thresholds_and_future_independence():
    frame = frame_fixture.__wrapped__()
    dates, detail, thresholds = training_context(frame, metadata())
    assert dates.iloc[0].to_dict() == {
        "Dataset": "Training",
        "Start Date": "2013-01-08",
        "End Date": "2013-01-09",
        "Usable Days": 2,
    }
    assert dates.iloc[-1]["Start Date"] == dates.iloc[-1]["End Date"] == "2013-01-14"
    assert detail.Samples.eq(96).all() and detail["Usable Days"].eq(2).all()
    training = frame[
        frame.interval_start_gmt.between(
            pd.Timestamp("2013-01-08", tz="UTC"),
            pd.Timestamp("2013-01-10", tz="UTC"),
            inclusive="left",
        )
    ]
    for h in HOUSEHOLDS:
        assert thresholds[h] == pytest.approx(
            training[training.household_id.eq(h)].average_power_kw.quantile(0.9)
        )
    summed = training.groupby("interval_start_gmt").average_power_kw.sum()
    assert thresholds["Portfolio"] == pytest.approx(summed.quantile(0.9))
    future = frame.copy()
    mask = future.interval_start_gmt >= pd.Timestamp("2013-01-14", tz="UTC")
    future.loc[mask, "energy_kwh"] = 5000
    future.loc[mask, "average_power_kw"] = 10000
    second = training_context(future, metadata())
    pd.testing.assert_frame_equal(dates, second[0])
    assert thresholds == second[2]


def test_unequal_admitted_dates_and_counts_checked_against_saved_model():
    frame = frame_fixture.__wrapped__().copy()
    # Remove the weekly lookback for the first training origin, for one home only.
    frame = frame[
        ~(
            frame.household_id.eq(HOUSEHOLDS[0])
            & frame.interval_start_gmt.dt.strftime("%Y-%m-%d").eq("2013-01-01")
        )
    ]
    artifact = metadata()
    with pytest.raises(ValueError, match="saved model"):
        training_context(frame, artifact)
    artifact["counts"][HOUSEHOLDS[0]]["training"] = 1
    dates, detail, _ = training_context(frame, artifact)
    first = detail[detail.Household.eq(HOUSEHOLDS[0]) & detail.Dataset.eq("Training")].iloc[0]
    assert first["First Usable Date"] == first["Last Usable Date"] == "2013-01-09"
    assert first.Samples == 48 and dates.iloc[0]["Usable Days"] == 1
    invalid = deepcopy(artifact)
    invalid["request"]["forecast_origin"] = "2013-01-13T00:00:00+00:00"
    with pytest.raises(ValueError, match="event-day"):
        training_context(frame, invalid)


def test_event_highlight_uses_unchanged_replay_window_and_legend_selection():
    events, _, _ = load_selection()
    event = events[2]
    spec = full_day_spec(event, pd.Timestamp("2013-12-06", tz="UTC"))
    window = spec["layer"][0]["data"]["values"][0]
    assert window == dict(start="2013-12-06T16:30:00+00:00", end="2013-12-06T18:00:00+00:00")
    assert spec["layer"][1]["params"][0]["bind"] == "legend"
    assert spec["layer"][1]["encoding"]["x"]["scale"]["type"] == "utc"
