"""Vega-Lite presentation with GMT axes, hover/zoom and stable household colours."""

import pandas as pd
import streamlit as st

from batteryflex.ui.lcl_views import demand_segments

# Same ID domain and colours across comparison and replay, independent of series order.
HOUSEHOLDS = ["MAC001391", "MAC003288", "MAC000143", "MAC001534", "MAC001395"]
COLOURS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00"]


def household_colour(combined: bool = False) -> dict:
    return {
        "field": "household_id",
        "type": "nominal",
        "title": "Household",
        "scale": {
            "domain": HOUSEHOLDS + (["Combined"] if combined else []),
            "range": COLOURS + (["#666666"] if combined else []),
        },
    }


def demand_chart(rows: pd.DataFrame) -> None:
    st.vega_lite_chart(
        demand_segments(rows),
        {
            "height": 280,
            "params": [
                {
                    "name": "zoom",
                    "select": {"type": "interval", "encodings": ["x"]},
                    "bind": "scales",
                }
            ],
            "mark": {"type": "line", "point": {"size": 15}, "tooltip": True},
            "encoding": {
                "x": {
                    "field": "interval_start_gmt",
                    "type": "temporal",
                    "scale": {"type": "utc"},
                    "axis": {"title": "Interval start (GMT)"},
                },
                "y": {
                    "field": "average_power_kw",
                    "type": "quantitative",
                    "axis": {"title": "Average power (kW)"},
                    "scale": {"zero": True},
                },
                "detail": {"field": "segment", "type": "nominal"},
                "tooltip": [
                    {"field": "source_timestamp", "title": "Original interval END (GMT)"},
                    {"field": "source_kwh", "title": "Original energy (kWh)"},
                    {"field": "average_power_kw", "type": "quantitative", "title": "kW"},
                ],
            },
        },
        alt="Measured half-hour demand with gaps at missing or unretained intervals",
    )


def daily_chart(daily: pd.DataFrame) -> None:
    x = {
        "field": "day",
        "type": "temporal",
        "scale": {"type": "utc"},
        "axis": {
            "title": "Observation day (GMT)",
            "format": "%d %b",
            "tickCount": {"interval": "day", "step": max(1, (len(daily) + 9) // 10)},
        },
    }
    st.vega_lite_chart(
        daily,
        {
            "vconcat": [
                {
                    "height": 190,
                    "transform": [{"filter": "datum.status === 'Complete'"}],
                    "mark": {"type": "bar", "tooltip": True},
                    "encoding": {
                        "x": {**x, "axis": None},
                        "y": {
                            "field": "energy_kwh",
                            "type": "quantitative",
                            "axis": {"title": "Daily energy (kWh)"},
                        },
                        "tooltip": [
                            {"field": "day", "type": "temporal", "format": "%d %b %Y"},
                            {
                                "field": "energy_kwh",
                                "type": "quantitative",
                                "format": ".3f",
                                "title": "Complete-day kWh",
                            },
                        ],
                    },
                },
                {
                    "height": 30,
                    "mark": {"type": "tick", "thickness": 4, "size": 22},
                    "encoding": {
                        "x": x,
                        "color": {
                            "field": "status",
                            "type": "nominal",
                            "scale": {
                                "domain": ["Complete", "Incomplete", "Not retained"],
                                "range": ["#009E73", "#D55E00", "#888888"],
                            },
                            "legend": {"title": "Day coverage", "orient": "bottom"},
                        },
                        "tooltip": [
                            {"field": "day", "type": "temporal", "format": "%d %b %Y"},
                            {"field": "status"},
                            {"field": "valid_intervals"},
                        ],
                    },
                },
            ],
            "resolve": {"scale": {"x": "shared"}},
        },
        alt="Complete-day energy and coverage strip marking incomplete and unretained days",
    )


def profile_chart(profiles: pd.DataFrame, compare: bool = False) -> None:
    ids = profiles.household_id.unique().tolist()
    single_colour = (
        COLOURS[HOUSEHOLDS.index(ids[0])] if ids and ids[0] in HOUSEHOLDS else COLOURS[0]
    )
    st.vega_lite_chart(
        profiles,
        {
            "height": 250,
            "mark": {"type": "line", "tooltip": True},
            "encoding": {
                "x": {
                    "field": "hour_gmt",
                    "type": "quantitative",
                    "scale": {"domain": [0, 24]},
                    "axis": {
                        "title": "Time of day (GMT)",
                        "values": list(range(0, 25, 3)),
                        "labelExpr": "format(datum.value, '02d') + ':00'",
                    },
                },
                "y": {
                    "field": "average_power_kw",
                    "type": "quantitative",
                    "axis": {"title": "Mean half-hour demand (kW)"},
                },
                "color": household_colour() if compare else {"value": single_colour},
                "tooltip": [
                    {"field": "household_id", "title": "Household"},
                    {"field": "hour_gmt", "title": "Interval start hour (GMT)"},
                    {"field": "average_power_kw", "title": "Mean kW"},
                    {"field": "valid_readings", "title": "Valid observations"},
                ],
            },
        },
        alt="Typical daily load profiles from valid historical half-hour readings",
    )


def comparison_chart(stats: pd.DataFrame, field: str, label: str) -> None:
    st.vega_lite_chart(
        stats,
        {
            "height": 180,
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {
                    "field": "household_id",
                    "type": "nominal",
                    "sort": HOUSEHOLDS,
                    "axis": {"title": None, "labelAngle": -25},
                },
                "y": {"field": field, "type": "quantitative", "axis": {"title": label}},
                "color": {**household_colour(), "legend": None},
                "tooltip": [
                    {"field": "household_id", "title": "Household"},
                    {"field": field, "type": "quantitative", "title": label},
                ],
            },
        },
        alt=f"Five-household comparison of {label}",
    )


def replay_chart(rows: pd.DataFrame, ids: list[str]) -> None:
    long = rows.rename(columns={"combined_kw": "Combined"}).melt(
        id_vars=["neso_start_gmt", "neso_end_gmt", "source_end_gmt"],
        value_vars=[*ids, "Combined"],
        var_name="household_id",
        value_name="demand_kw",
    )
    st.vega_lite_chart(
        long,
        {
            "height": 280,
            "mark": {"type": "line", "point": True, "tooltip": True},
            "encoding": {
                "x": {
                    "field": "neso_start_gmt",
                    "type": "temporal",
                    "scale": {"type": "utc"},
                    "axis": {"title": "NESO interval start (GMT)", "format": "%H:%M"},
                },
                "y": {
                    "field": "demand_kw",
                    "type": "quantitative",
                    "axis": {"title": "Household demand (kW)"},
                    "scale": {"zero": True},
                },
                "color": household_colour(combined=True),
                "strokeDash": {
                    "condition": {"test": "datum.household_id === 'Combined'", "value": [6, 3]},
                    "value": [1, 0],
                },
                "tooltip": [
                    {"field": "household_id", "title": "Household"},
                    {"field": "neso_start_gmt", "title": "NESO interval start (GMT)"},
                    {"field": "neso_end_gmt", "title": "NESO interval end (GMT)"},
                    {"field": "source_end_gmt", "title": "Original LCL interval END (GMT)"},
                    {"field": "demand_kw", "title": "kW"},
                ],
            },
        },
        alt="Each recommended household and combined demand across original NESO half-hours",
    )
