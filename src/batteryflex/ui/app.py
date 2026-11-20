"""Application shell and product navigation."""

from importlib.resources import files

import streamlit as st

from batteryflex.defaults import (
    AppDefaults,
    ForecastingDefaults,
    load_defaults,
    portfolio_defaults,
)
from batteryflex.neso_intervals import event_intervals
from batteryflex.neso_manifest import load_selection
from batteryflex.storage.settings import Settings


def main() -> None:
    st.set_page_config(
        page_title="BatteryFlex", page_icon=":material/battery_charging_full:", layout="wide"
    )
    try:
        config = load_defaults("app.yaml", AppDefaults)
        portfolio = portfolio_defaults()
        events, sources, _ = load_selection()
        from batteryflex.dispatch_event import event_start_batteries, standard_scenario

        event_assets = event_start_batteries(portfolio.batteries)
        for event in events:
            steps = tuple(range(len(event_intervals(sources[event["resource_id"]], event))))
            standard_scenario(event_assets, steps)
        load_defaults("forecasting.yaml", ForecastingDefaults)
        storage = Settings.load()
        if storage.require_cloud_credentials or storage.url:
            storage.validate_cloud()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        st.error(str(exc), title="Application configuration is invalid")
        return

    from batteryflex.ui.explorer import render_data_explorer
    from batteryflex.ui.overview import render_overview
    from batteryflex.ui.planned import render_simulation
    from batteryflex.ui.portfolio import render_portfolio

    pages = [
        st.Page(
            render_data_explorer,
            title="Data Explorer",
            icon=":material/analytics:",
            url_path="data",
        ),
        st.Page(
            render_portfolio,
            title="Portfolio & Configuration",
            icon=":material/tune:",
            url_path="portfolio",
        ),
        st.Page(
            render_simulation,
            title="Simulation Lab",
            icon=":material/science:",
            url_path="simulation",
        ),
    ]

    def overview() -> None:
        diagram = (
            files("batteryflex")
            .joinpath("resources", "architecture.svg")
            .read_text(encoding="utf-8-sig")
        )
        render_overview(config, pages, diagram)

    st.sidebar.markdown(f"**{config.name}**")
    page = st.navigation(
        [st.Page(overview, title="Overview", icon=":material/home:", default=True), *pages]
    )
    st.sidebar.caption(f"Version {config.version}")
    page.run()
