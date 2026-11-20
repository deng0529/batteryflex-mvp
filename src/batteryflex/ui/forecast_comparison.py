"""Presentation helpers for full-partition RMSE comparisons; no model fitting."""

from math import isclose

import numpy as np
import pandas as pd

from batteryflex.portfolio import HOUSEHOLDS


def rmse_rows(metrics: pd.DataFrame, methods: tuple[str, ...]) -> pd.DataFrame:
    rows = metrics[
        metrics.partition.eq("testing")
        & metrics.household.isin(HOUSEHOLDS)
        & metrics.method.isin(methods)
    ]
    return rows.loc[
        np.isfinite(rows.rmse_kw) & rows.rmse_kw.ge(0), ["household", "method", "rmse_kw"]
    ].copy()


def rmse_spec(methods: tuple[str, ...]) -> dict:
    return {
        "height": 320,
        "mark": {"type": "bar"},
        "encoding": {
            "x": {
                "field": "household",
                "type": "nominal",
                "sort": list(HOUSEHOLDS),
                "title": "Household",
                "axis": {"labelAngle": 0},
            },
            "xOffset": {"field": "method", "sort": list(methods)},
            "y": {
                "field": "rmse_kw",
                "type": "quantitative",
                "title": "Test RMSE (kW)",
                "scale": {"zero": True},
            },
            "color": {
                "field": "method",
                "type": "nominal",
                "title": "Algorithm",
                "scale": {"domain": list(methods)},
            },
            "tooltip": [
                {"field": "household", "type": "nominal", "title": "Household"},
                {"field": "method", "type": "nominal", "title": "Algorithm"},
                {"field": "rmse_kw", "type": "quantitative", "title": "RMSE (kW)", "format": ".4f"},
            ],
        },
    }


def lowest_rmse(
    metrics: pd.DataFrame,
    partition: str,
    household: str,
    methods: tuple[str, ...],
    *,
    require_all: bool = False,
) -> tuple[str, ...]:
    rows = metrics[
        metrics.partition.eq(partition)
        & metrics.household.eq(household)
        & metrics.method.isin(methods)
    ]
    rows = rows[np.isfinite(rows.rmse_kw) & rows.rmse_kw.ge(0) & rows.observations.gt(0)]
    if rows.empty or rows.method.duplicated().any():
        return ()
    if require_all and (set(rows.method) != set(methods) or rows.observations.nunique() != 1):
        return ()
    minimum = float(rows.rmse_kw.min())
    return tuple(
        m
        for m in methods
        if any(
            isclose(float(r), minimum, rel_tol=1e-9, abs_tol=1e-12)
            for r in rows.loc[rows.method.eq(m), "rmse_kw"]
        )
    )


def comparison_conclusion(metrics: pd.DataFrame, methods: tuple[str, ...]) -> str:
    wins: dict[str, list[str]] = {m: [] for m in methods}
    ties, unavailable = [], []
    for household in HOUSEHOLDS:
        best = lowest_rmse(metrics, "testing", household, methods, require_all=True)
        if not best:
            unavailable.append(household)
        if len(best) > 1:
            ties.append(household)
        for method in best:
            wins[method].append(household)
    groups = [
        f"{m}: {len(homes)} wins" + (f" ({', '.join(homes)})" if homes else "")
        for m, homes in wins.items()
    ]
    text = "Lowest test RMSE — " + "; ".join(groups) + "."
    if ties:
        text += f" Ties count for each tied algorithm: {', '.join(ties)}."
    if unavailable:
        text += f" Complete comparable results unavailable for {', '.join(unavailable)}."
    portfolio = lowest_rmse(metrics, "testing", "Portfolio", methods, require_all=True)
    text += (
        (
            " Portfolio lowest RMSE: "
            + " and ".join(portfolio)
            + (" (tie)." if len(portfolio) > 1 else ".")
        )
        if portfolio
        else (" Portfolio comparison unavailable.")
    )
    return text + " These comparisons apply to the evaluated periods."
