"""Streamlit UI components for PowGenAUS."""
from __future__ import annotations

import base64
from typing import Any

import branca.colormap as cm
import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

import preprocess as pre


def _fmt_number(value: float, digits: int = 0) -> str:
    if pd.isna(value):
        value = 0
    return f"{value:,.{digits}f}"


def _csv_download_button(data: pd.DataFrame, filename: str, label: str) -> None:
    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def sidebar(data: pd.DataFrame, years: list[int]) -> dict[str, Any]:
    """Build the sidebar and return selected filters."""
    with st.sidebar:
        st.title("⚡ PowGenAUS")
        st.caption("Interactive dashboard for Australian power generation data")
        st.divider()

        selected_year = st.select_slider(
            "Generation year",
            options=years,
            value=st.session_state.get("select_year", max(years)),
            key="select_year",
        )

        all_fuels = sorted(data["primary_fuel"].dropna().unique().tolist())
        all_states = sorted(data["STATE_NAME"].dropna().unique().tolist())

        selected_fuels = st.multiselect(
            "Fuel type",
            options=all_fuels,
            default=all_fuels,
            help="Select one or more primary fuel types.",
        )
        selected_states = st.multiselect(
            "Australian state/territory",
            options=all_states,
            default=all_states,
            help="Select one or more states or territories.",
        )
        min_capacity = st.slider(
            "Minimum capacity (MW)",
            min_value=0,
            max_value=int(max(data["capacity_mw"].max(), 1)),
            value=0,
            step=25,
        )
        search_text = st.text_input(
            "Search station or owner",
            placeholder="Example: wind, Origin, Snowy...",
        )

        st.divider()
        st.caption(
            "Data source: Global Power Plant Database filtered to Australia, combined with Australian state boundaries."
        )

    return {
        "year": selected_year,
        "fuel_types": selected_fuels,
        "states": selected_states,
        "min_capacity": min_capacity,
        "search_text": search_text,
    }


def hero(data: pd.DataFrame) -> None:
    year = st.session_state.select_year
    st.markdown(
        '<div class="main-title">PowGenAUS: Australian Power Generation Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="subtitle">Explore the location, fuel mix, capacity and reported generation of Australian power stations for <b>{year}</b>.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        This enhanced Streamlit application combines geospatial processing, interactive mapping and dashboard visualisation.
        Use the sidebar to filter by year, fuel type, state, station capacity and station/owner name.
        """
    )
    st.caption(f"Current selection: {len(data):,} power station records.")


def overview_metrics(data: pd.DataFrame, generation_var: str) -> None:
    """Display headline metrics."""
    total_capacity = data["capacity_mw"].sum()
    total_generation = data[generation_var].sum()
    avg_capacity = data["capacity_mw"].mean()
    fuel_count = data["primary_fuel"].nunique()
    state_count = data["STATE_NAME"].nunique()

    cols = st.columns(5)
    cols[0].metric("Power stations", f"{len(data):,}")
    cols[1].metric("Total capacity", f"{total_capacity:,.0f} MW")
    cols[2].metric("Generation", f"{total_generation:,.0f} GWh")
    cols[3].metric("Average capacity", f"{avg_capacity:,.0f} MW")
    cols[4].metric("Fuel / states", f"{fuel_count} / {state_count}")

    st.markdown(
        """
        The indicators above respond to the active filters. Capacity refers to installed power plant capacity in megawatts (MW), while generation refers to reported annual electricity generation in gigawatt-hours (GWh).
        """
    )


def top_lists(data: pd.DataFrame, generation_var: str) -> None:
    """Display top stations and a compact fuel table."""
    left, right = st.columns(2)

    with left:
        st.subheader("Top 10 power stations by capacity")
        top_capacity = (
            data[["name", "STATE_NAME", "primary_fuel", "capacity_mw", generation_var]]
            .sort_values("capacity_mw", ascending=False)
            .head(10)
            .rename(
                columns={
                    "name": "Power station",
                    "STATE_NAME": "State",
                    "primary_fuel": "Fuel",
                    "capacity_mw": "Capacity (MW)",
                    generation_var: "Generation (GWh)",
                }
            )
        )
        st.dataframe(top_capacity, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Fuel type summary")
        fuel_summary = pre.aggregate_by_fuel(data, generation_var).rename(
            columns={
                "primary_fuel": "Fuel",
                "power_station_count": "Stations",
                "total_capacity_mw": "Capacity (MW)",
                "total_generation_gwh": "Generation (GWh)",
            }
        )
        st.dataframe(
            fuel_summary[["Fuel", "Stations", "Capacity (MW)", "Generation (GWh)"]],
            use_container_width=True,
            hide_index=True,
        )


def power_map(
    data: pd.DataFrame,
    state_boundaries,
    state_summary,
    variable_choice: str,
    generation_var: str,
    show_markers: bool,
    marker_limit: int,
) -> None:
    """Create and render the Folium map."""
    if variable_choice == "Capacity":
        variable = "total_capacity_mw"
        legend_title = "Total capacity (MW)"
        popup_label = "Capacity"
        popup_unit = "MW"
    else:
        variable = "total_generation_gwh"
        legend_title = f"Reported generation ({st.session_state.select_year}, GWh)"
        popup_label = "Generation"
        popup_unit = "GWh"

    m = folium.Map(
        location=[-25.5, 134.0],
        zoom_start=4,
        tiles="CartoDB positron",
        scrollWheelZoom=False,
    )

    max_value = max(float(state_summary[variable].max()), 1.0)
    colormap = cm.linear.YlOrRd_09.scale(0, max_value)
    colormap.caption = legend_title

    def style_function(feature):
        value = feature["properties"].get(variable, 0) or 0
        return {
            "fillColor": colormap(value),
            "color": "#555555",
            "weight": 1,
            "fillOpacity": 0.72,
        }

    tooltip_fields = [
        "STATE_NAME",
        "power_station_count",
        "total_capacity_mw",
        "total_generation_gwh",
    ]
    tooltip_aliases = [
        "State:",
        "Power stations:",
        "Capacity (MW):",
        "Generation (GWh):",
    ]

    folium.GeoJson(
        state_summary,
        name="State summary",
        style_function=style_function,
        highlight_function=lambda feature: {
            "weight": 3,
            "color": "#000000",
            "fillOpacity": 0.82,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
            sticky=False,
        ),
    ).add_to(m)

    colormap.add_to(m)

    if show_markers:
        marker_data = data.sort_values("capacity_mw", ascending=False).head(marker_limit)
        cluster = MarkerCluster(name="Power stations").add_to(m)
        for _, row in marker_data.iterrows():
            popup_html = f"""
            <div style="font-size: 13px; line-height: 1.35; width: 260px;">
                <b>{row.get('name', 'Unknown station')}</b><br>
                <b>Owner:</b> {row.get('owner', 'Unknown Owner')}<br>
                <b>State:</b> {row.get('STATE_NAME', 'Unknown State')}<br>
                <b>Fuel:</b> {row.get('primary_fuel', 'Unknown Fuel')}<br>
                <b>Capacity:</b> {_fmt_number(row.get('capacity_mw', 0), 1)} MW<br>
                <b>Generation {st.session_state.select_year}:</b> {_fmt_number(row.get(generation_var, 0), 1)} GWh
            </div>
            """
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=5,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=str(row.get("name", "Power station")),
                fill=True,
                fill_opacity=0.85,
                weight=1,
            ).add_to(cluster)

    folium.LayerControl(position="bottomright").add_to(m)
    st_folium(m, width=None, height=560, returned_objects=[])


def chart_section(
    data: pd.DataFrame,
    state_summary: pd.DataFrame,
    fuel_summary: pd.DataFrame,
    generation_var: str,
) -> None:
    """Render chart tabs."""
    st.subheader("Interactive Charts")

    chart_tabs = st.tabs(
        [
            "Fuel mix",
            "State comparison",
            "Capacity vs generation",
            "Yearly trend",
        ]
    )

    with chart_tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(
                fuel_summary,
                values="total_capacity_mw",
                names="primary_fuel",
                title="Installed capacity by fuel type",
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(
                fuel_summary,
                values="total_generation_gwh",
                names="primary_fuel",
                title=f"Reported generation by fuel type ({st.session_state.select_year})",
            )
            st.plotly_chart(fig, use_container_width=True)

    with chart_tabs[1]:
        state_plot = state_summary.drop(columns="geometry", errors="ignore").sort_values(
            "total_capacity_mw", ascending=False
        )
        fig = px.bar(
            state_plot,
            x="STATE_NAME",
            y=["total_capacity_mw", "total_generation_gwh"],
            barmode="group",
            title="State-level capacity and generation comparison",
            labels={
                "STATE_NAME": "State/Territory",
                "value": "Value",
                "variable": "Metric",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_tabs[2]:
        fig = px.scatter(
            data,
            x="capacity_mw",
            y=generation_var,
            color="primary_fuel",
            size="capacity_mw",
            hover_name="name",
            hover_data=["STATE_NAME", "owner"],
            title="Relationship between installed capacity and reported generation",
            labels={
                "capacity_mw": "Capacity (MW)",
                generation_var: f"Generation {st.session_state.select_year} (GWh)",
                "primary_fuel": "Fuel type",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_tabs[3]:
        year_cols = [c for c in data.columns if c.startswith("generation_gwh_")]
        trend = []
        for col in year_cols:
            year = int(col.replace("generation_gwh_", ""))
            trend.append({"Year": year, "Generation (GWh)": data[col].sum()})
        trend_df = pd.DataFrame(trend).sort_values("Year")
        fig = px.line(
            trend_df,
            x="Year",
            y="Generation (GWh)",
            markers=True,
            title="Reported generation trend for the current filtered selection",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "The trend uses the same fuel, state, capacity and search filters currently selected in the sidebar."
        )


def data_section(
    filtered_data: pd.DataFrame,
    state_summary: pd.DataFrame,
    fuel_summary: pd.DataFrame,
    raw_power: pd.DataFrame,
) -> None:
    """Render data inspection and download section."""
    st.subheader("Inspect and Download Data")
    tabs = st.tabs(["Filtered stations", "State summary", "Fuel summary", "Raw source data"])

    with tabs[0]:
        df = pre.dataframe_for_download(filtered_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        _csv_download_button(df, "powgenaus_filtered_power_stations.csv", "Download filtered stations")

    with tabs[1]:
        df = pd.DataFrame(state_summary.drop(columns="geometry", errors="ignore"))
        st.dataframe(df, use_container_width=True, hide_index=True)
        _csv_download_button(df, "powgenaus_state_summary.csv", "Download state summary")

    with tabs[2]:
        st.dataframe(fuel_summary, use_container_width=True, hide_index=True)
        _csv_download_button(fuel_summary, "powgenaus_fuel_summary.csv", "Download fuel summary")

    with tabs[3]:
        au_raw = raw_power.loc[raw_power["country_long"].eq("Australia")].copy()
        st.dataframe(au_raw, use_container_width=True, hide_index=True)
        _csv_download_button(au_raw, "powgenaus_raw_australia_records.csv", "Download raw Australia records")


def about_section() -> None:
    """Project explanation for portfolio reviewers."""
    st.subheader("About this project")
    st.markdown(
        """
        **PowGenAUS** is a software development and geospatial dashboard project created for the MSc Applied Geoinformatics programme.
        It demonstrates how Python can be used to transform tabular energy infrastructure data into an interactive geospatial application.

        **Main techniques demonstrated:**
        - Python data cleaning with Pandas
        - Spatial data handling with GeoPandas and Shapely
        - Point-in-polygon spatial join between power stations and Australian states
        - Interactive dashboard design with Streamlit
        - Web map development with Folium and marker clustering
        - Interactive charts with Plotly
        - Filter-driven exploratory data analysis

        **Possible future improvements:**
        - Add newer Australian energy generation datasets
        - Deploy the dashboard publicly using Streamlit Community Cloud
        - Add time-series animation for the map
        - Add renewable vs non-renewable classification
        - Add carbon/emission indicators where suitable data is available
        """
    )
