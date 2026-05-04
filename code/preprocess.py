"""Data loading, cleaning and aggregation helpers for PowGenAUS."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
POWER_FILE = DATA_DIR / "global_power_plant_database.csv"
STATE_FILE = DATA_DIR / "AustralianStates.geojson"


def generation_column(year: int | str) -> str:
    return f"generation_gwh_{int(year)}"


@st.cache_data(show_spinner="Loading power generation and state boundary data...")
def load_project_data() -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    """Load the CSV and GeoJSON source files."""
    power = pd.read_csv(POWER_FILE, low_memory=False)
    states = gpd.read_file(STATE_FILE).to_crs(epsg=4326)
    return power, states


def available_generation_years(data: pd.DataFrame) -> list[int]:
    """Return all years that have reported generation columns."""
    years: list[int] = []
    for col in data.columns:
        if col.startswith("generation_gwh_"):
            try:
                years.append(int(col.replace("generation_gwh_", "")))
            except ValueError:
                continue
    return sorted(years)


@st.cache_data(show_spinner="Preparing Australian power station records...")
def prepare_power_station_data(
    power: pd.DataFrame, _states: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Filter to Australia, clean important fields and assign each station to a state."""
    df = power.loc[power["country_long"].eq("Australia")].copy()

    # Keep only records with valid coordinates.
    df = df.dropna(subset=["latitude", "longitude"])

    # Create point geometry.
    geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Spatial join. Newer GeoPandas uses predicate; older versions used op.
    try:
        joined = gpd.sjoin(
            gdf,
            _states[["STATE_NAME", "geometry"]],
            how="left",
            predicate="intersects",
        )
    except TypeError:
        joined = gpd.sjoin(
            gdf,
            _states[["STATE_NAME", "geometry"]],
            how="left",
            op="intersects",
        )

    joined["STATE_NAME"] = joined["STATE_NAME"].fillna("Unknown State")
    joined["owner"] = joined["owner"].fillna("Unknown Owner")
    joined["primary_fuel"] = joined["primary_fuel"].fillna("Unknown Fuel")
    joined["capacity_mw"] = pd.to_numeric(joined["capacity_mw"], errors="coerce").fillna(0)

    for col in [c for c in joined.columns if c.startswith("generation_gwh_")]:
        joined[col] = pd.to_numeric(joined[col], errors="coerce").fillna(0)

    # Drop columns that are not useful for the dashboard display but keep source and ID fields.
    drop_cols = [
        "other_fuel1",
        "other_fuel2",
        "other_fuel3",
        "generation_data_source",
        "geolocation_source",
        "url",
        "country",
        "country_long",
        "index_right",
    ]
    note_cols = [c for c in joined.columns if "note" in c.lower()]
    joined = joined.drop(columns=[c for c in drop_cols + note_cols if c in joined.columns])

    return joined


def _safe_list(values: Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    return [v for v in values if v is not None]


def apply_filters(
    data: gpd.GeoDataFrame,
    fuel_types: Iterable[str] | None,
    states: Iterable[str] | None,
    min_capacity: float = 0,
    search_text: str = "",
) -> gpd.GeoDataFrame:
    """Apply sidebar filters to the prepared power station dataset."""
    filtered = data.copy()
    selected_fuels = _safe_list(fuel_types)
    selected_states = _safe_list(states)

    if selected_fuels:
        filtered = filtered.loc[filtered["primary_fuel"].isin(selected_fuels)]
    if selected_states:
        filtered = filtered.loc[filtered["STATE_NAME"].isin(selected_states)]
    if min_capacity:
        filtered = filtered.loc[filtered["capacity_mw"] >= min_capacity]
    if search_text.strip():
        text = search_text.strip().lower()
        search_area = (
            filtered["name"].fillna("").str.lower()
            + " "
            + filtered["owner"].fillna("").str.lower()
        )
        filtered = filtered.loc[search_area.str.contains(text, regex=False)]

    return filtered


def aggregate_by_state(
    data: gpd.GeoDataFrame, generation_var: str, states: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Summarise capacity and generation by Australian state."""
    grouped = (
        data.groupby("STATE_NAME", dropna=False)
        .agg(
            power_station_count=("gppd_idnr", "count"),
            total_capacity_mw=("capacity_mw", "sum"),
            average_capacity_mw=("capacity_mw", "mean"),
            total_generation_gwh=(generation_var, "sum"),
            average_generation_gwh=(generation_var, "mean"),
        )
        .reset_index()
    )
    merged = states.merge(grouped, on="STATE_NAME", how="left")
    fill_cols = [
        "power_station_count",
        "total_capacity_mw",
        "average_capacity_mw",
        "total_generation_gwh",
        "average_generation_gwh",
    ]
    merged[fill_cols] = merged[fill_cols].fillna(0)
    return merged


def aggregate_by_fuel(data: gpd.GeoDataFrame, generation_var: str) -> pd.DataFrame:
    """Summarise capacity and generation by primary fuel type."""
    return (
        data.groupby("primary_fuel", dropna=False)
        .agg(
            power_station_count=("gppd_idnr", "count"),
            total_capacity_mw=("capacity_mw", "sum"),
            average_capacity_mw=("capacity_mw", "mean"),
            total_generation_gwh=(generation_var, "sum"),
            average_generation_gwh=(generation_var, "mean"),
        )
        .reset_index()
        .sort_values("total_capacity_mw", ascending=False)
    )


def dataframe_for_download(data: pd.DataFrame) -> pd.DataFrame:
    """Convert GeoDataFrame to a normal DataFrame suitable for CSV download."""
    df = pd.DataFrame(data.drop(columns="geometry", errors="ignore"))
    return df
