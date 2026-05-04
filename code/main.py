"""
PowGenAUS - Interactive Power Generation Dashboard for Australia

Run from the project root with:
    streamlit run code/main.py
"""
from __future__ import annotations

import streamlit as st

import dashboard
import preprocess as pre

st.set_page_config(
    page_title="PowGenAUS | Australian Power Generation Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Global style
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        .main-title {font-size: 2.6rem; font-weight: 800; margin-bottom: 0.1rem;}
        .subtitle {font-size: 1.05rem; color: #555; margin-bottom: 1.2rem;}
        .small-note {font-size: 0.88rem; color: #666;}
        div[data-testid="stMetricValue"] {font-size: 1.75rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Data loading and filtering
# -----------------------------------------------------------------------------
raw_power, state_boundaries = pre.load_project_data()
power_with_states = pre.prepare_power_station_data(raw_power, state_boundaries)

available_years = pre.available_generation_years(power_with_states)
if "select_year" not in st.session_state:
    st.session_state.select_year = max(available_years)

generation_var = pre.generation_column(st.session_state.select_year)
st.session_state.generation_var = generation_var

filters = dashboard.sidebar(power_with_states, available_years)
filtered_data = pre.apply_filters(
    power_with_states,
    fuel_types=filters["fuel_types"],
    states=filters["states"],
    min_capacity=filters["min_capacity"],
    search_text=filters["search_text"],
)
st.session_state.data_filtered = filtered_data

state_summary = pre.aggregate_by_state(filtered_data, generation_var, state_boundaries)
fuel_summary = pre.aggregate_by_fuel(filtered_data, generation_var)

# -----------------------------------------------------------------------------
# Main page
# -----------------------------------------------------------------------------
dashboard.hero(filtered_data)

if filtered_data.empty:
    st.warning(
        "No power stations match the current filters. Please adjust the sidebar selections."
    )
    st.stop()

metric_tab, map_tab, chart_tab, data_tab, about_tab = st.tabs(
    ["Overview", "Map Explorer", "Charts", "Data", "About"]
)

with metric_tab:
    dashboard.overview_metrics(filtered_data, generation_var)
    dashboard.top_lists(filtered_data, generation_var)

with map_tab:
    st.subheader("Interactive Map Explorer")
    st.caption(
        "Use the controls below to switch between state-level choropleth mapping and individual power station markers."
    )
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        map_variable = st.radio(
            "Map variable",
            options=["Capacity", "Generation"],
            horizontal=True,
            help="Capacity is measured in MW. Generation is measured in GWh for the selected year.",
        )
    with col2:
        show_markers = st.checkbox(
            "Show power station markers",
            value=False,
            help="Markers are clustered for readability and performance.",
        )
    with col3:
        marker_limit = st.slider(
            "Maximum markers",
            min_value=50,
            max_value=500,
            value=250,
            step=50,
            disabled=not show_markers,
        )

    dashboard.power_map(
        data=filtered_data,
        state_boundaries=state_boundaries,
        state_summary=state_summary,
        variable_choice=map_variable,
        generation_var=generation_var,
        show_markers=show_markers,
        marker_limit=marker_limit,
    )

    st.info(
        "Tip: enable markers to inspect individual power stations. The marker popup shows fuel type, owner, capacity, state, and generation for the selected year."
    )

with chart_tab:
    dashboard.chart_section(filtered_data, state_summary, fuel_summary, generation_var)

with data_tab:
    dashboard.data_section(filtered_data, state_summary, fuel_summary, raw_power)

with about_tab:
    dashboard.about_section()
