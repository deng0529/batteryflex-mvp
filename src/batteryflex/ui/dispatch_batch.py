"""Five-event summaries from individually persisted dispatch runs."""

from typing import cast

import altair as alt
import pandas as pd
import streamlit as st


def render_batch_summary(batch: pd.DataFrame, method: str) -> None:
    st.subheader("Five-Event Performance Summary")
    st.caption(
        f"{method} · Historical Replay · Each event keeps its own window and load profile. "
        "Objectives are scenario-specific."
    )
    execution = batch["Execution status"].value_counts()
    complete = len(batch) - int(execution.get("Failed", 0))
    a, b, c, d = st.columns(4)
    a.metric("Completed events", f"{complete}/{len(batch)}")
    b.metric("Newly calculated", int(execution.get("Newly calculated and saved", 0)))
    c.metric("Loaded from database", int(execution.get("Loaded from database", 0)))
    d.metric("Failed", int(execution.get("Failed", 0)))
    fields = [
        "NESO event date",
        "Hours",
        "Requested (kWh)",
        "Execution status",
        "Status",
        "Total objective (£)",
        "Issue",
    ]
    st.dataframe(
        batch.reindex(columns=fields).round(4),
        hide_index=True,
        alt="Five-event persistent execution status",
    )
    passed = batch[batch["Status"].isin(["MET", "NOT MET", "NOT ASSESSABLE"])]
    counts = batch["Status"].value_counts()
    a, b, c, d, e = st.columns(5)
    a.metric("Events MET", int(counts.get("MET", 0)))
    b.metric("Events NOT MET", int(counts.get("NOT MET", 0)))
    for column, name, field in (
        (c, "Total requested", "Requested (kWh)"),
        (d, "Total delivered", "Delivered (kWh)"),
        (e, "Total shortfall", "Shortfall (kWh)"),
    ):
        column.metric(
            name, f"{passed[field].sum():.2f} kWh" if field in passed and len(passed) else "—"
        )
    if len(passed) != len(batch):
        st.caption(
            f"Totals cover {len(passed)} completed events. Failed events are shown in the table."
        )
    if counts.get("NOT ASSESSABLE", 0):
        st.caption(f"{counts['NOT ASSESSABLE']} completed events had no positive target.")
    if len(passed):
        measures = ["Requested (kWh)", "Delivered (kWh)"]
        values = passed.melt(
            ["NESO event date", "Status"], value_vars=measures, var_name="Energy", value_name="kWh"
        )
        values["Bar"] = [
            "Requested" if kind == measures[0] else f"Delivered · {status}"
            for kind, status in zip(values["Energy"], values["Status"], strict=True)
        ]
        chart = cast(alt.Chart, alt.Chart(values).mark_bar()).encode(
            x=alt.X(
                "NESO event date:N",
                sort=passed["NESO event date"].tolist(),
                axis=alt.Axis(labelAngle=0),
            ),
            xOffset=alt.XOffset("Energy:N", sort=measures),
            y=alt.Y("kWh:Q", title="Event energy (kWh)"),
            color=alt.Color(
                "Bar:N",
                title=None,
                scale=alt.Scale(
                    domain=[
                        "Requested",
                        "Delivered · MET",
                        "Delivered · NOT MET",
                        "Delivered · NOT ASSESSABLE",
                    ],
                    range=["#7d8793", "#008174", "#b94b36", "#3167b8"],
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                "NESO event date:N",
                "Status:N",
                "Energy:N",
                alt.Tooltip("kWh:Q", format=".2f"),
            ],
        )
        st.altair_chart(
            chart.properties(height=205),
            width="stretch",
            alt="Requested and delivered energy across five NESO events",
        )
    st.dataframe(batch.round(2), hide_index=True, alt="Five-event dispatch batch results")
