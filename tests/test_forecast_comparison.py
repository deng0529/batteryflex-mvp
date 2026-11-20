"""Full-partition chart values, fair winners and validation-only recommendations."""

import numpy as np
import pandas as pd
import pytest

from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.ui.forecast_comparison import (
    comparison_conclusion,
    lowest_rmse,
    rmse_rows,
    rmse_spec,
)

METHODS = ("Seasonal Naive", "LightGBM", "Ridge Regression")


@pytest.fixture
def scores():
    rows = []
    for partition in ("validation", "testing"):
        for i, household in enumerate((*HOUSEHOLDS, "Portfolio")):
            for j, method in enumerate(METHODS):
                # Test winners alternate; validation portfolio recommends the baseline.
                value = 0.1 if j == i % 3 else 0.5
                if partition == "validation" and household == "Portfolio":
                    value = 0.1 if j == 0 else 0.9
                rows.append(
                    dict(
                        partition=partition,
                        household=household,
                        method=method,
                        rmse_kw=value,
                        mae_kw=0.05,
                        observations=768,
                    )
                )
    return pd.DataFrame(rows)


def test_grouped_chart_uses_full_test_rmse_and_hover_units(scores):
    bars = rmse_rows(scores, METHODS)
    assert len(bars) == 15
    assert list(bars.columns) == ["household", "method", "rmse_kw"]
    assert set(bars.household) == set(HOUSEHOLDS)
    pd.testing.assert_frame_equal(
        bars,
        scores.loc[
            scores.partition.eq("testing") & scores.household.isin(HOUSEHOLDS),
            ["household", "method", "rmse_kw"],
        ],
    )
    spec = rmse_spec(METHODS)
    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["xOffset"]["field"] == "method"
    assert spec["encoding"]["y"]["title"] == "Test RMSE (kW)"
    assert spec["encoding"]["tooltip"][-1] == {
        "field": "rmse_kw",
        "type": "quantitative",
        "title": "RMSE (kW)",
        "format": ".4f",
    }
    assert [t["field"] for t in spec["encoding"]["tooltip"]] == ["household", "method", "rmse_kw"]
    assert set(rmse_rows(scores, METHODS[:2]).method) == set(METHODS[:2])
    scores.loc[scores.method.eq("LightGBM"), "rmse_kw"] = np.nan
    assert "LightGBM" not in set(rmse_rows(scores, METHODS).method)


def test_conclusion_counts_wins_and_uses_validation_for_save(scores):
    text = comparison_conclusion(scores, METHODS)
    assert f"Seasonal Naive: 2 wins ({HOUSEHOLDS[0]}, {HOUSEHOLDS[3]})" in text
    assert f"LightGBM: 2 wins ({HOUSEHOLDS[1]}, {HOUSEHOLDS[4]})" in text
    assert f"Ridge Regression: 1 wins ({HOUSEHOLDS[2]})" in text
    assert "Portfolio lowest RMSE: Ridge Regression." in text
    assert lowest_rmse(scores, "validation", "Portfolio", METHODS) == ("Seasonal Naive",)
    scores.loc[scores.partition.eq("testing"), "rmse_kw"] = 1000
    assert lowest_rmse(scores, "validation", "Portfolio", METHODS) == ("Seasonal Naive",)


def test_ties_missing_incomparable_and_zero_results(scores):
    mask = scores.household.eq(HOUSEHOLDS[0]) & scores.partition.eq("testing")
    scores.loc[mask, "rmse_kw"] = 0
    assert lowest_rmse(scores, "testing", HOUSEHOLDS[0], METHODS, require_all=True) == METHODS
    text = comparison_conclusion(scores, METHODS)
    assert f"Ties count for each tied algorithm: {HOUSEHOLDS[0]}" in text
    scores.loc[mask & scores.method.eq("LightGBM"), "observations"] = 48
    assert lowest_rmse(scores, "testing", HOUSEHOLDS[0], METHODS, require_all=True) == ()
    assert f"results unavailable for {HOUSEHOLDS[0]}" in comparison_conclusion(scores, METHODS)
    scores.loc[scores.household.eq("Portfolio"), "rmse_kw"] = np.nan
    assert "Portfolio comparison unavailable." in comparison_conclusion(scores, METHODS)
    assert lowest_rmse(scores, "validation", "Portfolio", METHODS) == ()


def test_validation_ties_use_stable_run_order(scores):
    scores.loc[scores.household.eq("Portfolio"), "rmse_kw"] = 0.2
    assert lowest_rmse(scores, "validation", "Portfolio", METHODS) == METHODS
