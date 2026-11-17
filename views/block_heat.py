"""Extra page: block-level surface heat from the trained model (Phase 4)."""
import json

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src import config, model, satellite
from views import common

# Light to dark, one color family. Darker = hotter surface.
HEAT_COLORS = ["#fcd9c4", "#f5a57c", "#eb6834", "#b8431a", "#7a2a0e"]
ERROR_COLORS = ["#256abf", "#9ec5f4", "#f0efec", "#f5a57c", "#b8431a"]


@st.cache_data
def load_heat():
    grid = pd.read_csv(config.PROCESSED_DIR / "heat_grid_predictions.csv")
    metrics = pd.read_csv(config.RESULTS_DIR / "exp_e_metrics.csv")
    importance = pd.read_csv(config.RESULTS_DIR / "exp_e_feature_importance.csv")
    return grid, metrics, importance


def heat_map(grid: pd.DataFrame, column: str, cuts: list[float], colors: list[str],
             unit: str) -> folium.Map:
    squares = gpd.GeoDataFrame(
        grid[list(dict.fromkeys([column, "surface_temp_f", "predicted_temp_f",
                                 "ntaname"]))].round(1),
        geometry=[satellite.cell_square(x, y) for x, y in zip(grid["x"], grid["y"])],
        crs=config.CRS_LANDSAT).to_crs(config.CRS_LATLON)

    def color(value: float) -> str:
        for cut, shade in zip(cuts, colors):
            if value <= cut:
                return shade
        return colors[-1]

    west, south, east, north = squares.total_bounds
    fmap = folium.Map(tiles="OpenStreetMap", control_scale=True, scrollWheelZoom=False)
    fmap.fit_bounds([[south, west], [north, east]])
    folium.GeoJson(
        json.loads(squares.to_json()),
        style_function=lambda f: {"fillColor": color(f["properties"][column]),
                                  "color": color(f["properties"][column]),
                                  "weight": 0.3, "fillOpacity": 0.75},
        tooltip=folium.GeoJsonTooltip(
            fields=["ntaname", "surface_temp_f", "predicted_temp_f"],
            aliases=["Neighborhood", f"Measured surface temp ({unit})",
                     f"Model prediction ({unit})"]),
    ).add_to(fmap)
    return fmap


def legend(cuts: list[float], colors: list[str], label: str) -> str:
    edges = [f"up to {cuts[0]:g}"] + [f"{a:g} to {b:g}" for a, b in zip(cuts, cuts[1:])]
    edges.append(f"above {cuts[-1]:g}")
    boxes = "".join(
        f'<span style="display:inline-block;width:14px;height:14px;background:{c};'
        f'border:1px solid #898781;margin:0 4px 0 12px;vertical-align:middle"></span>{e}'
        for c, e in zip(colors, edges))
    return f"<div>{label}: {boxes}</div>"


def render() -> None:
    grid, metrics, importance = load_heat()
    cv = metrics.iloc[0]
    baseline = metrics.iloc[1]

    st.title("Block-Level Heat")
    st.warning(config.SURFACE_TEMP_WARNING)
    st.markdown(
        f"City heat data is only available by neighborhood. This page goes "
        f"smaller. {config.FOCUS_NAME} is cut into **{len(grid):,} grid cells of "
        f"{config.GRID_CELL_METERS} meters**, and each one has a surface "
        f"temperature measured by the Landsat 9 satellite. A Random Forest model "
        f"was trained to predict that temperature from what the land looks like."
    )

    choice = st.radio(
        "Show", ["Measured by satellite", "Predicted by the model", "Model error"],
        horizontal=True)
    if choice == "Model error":
        cuts, colors = [-4, -1.5, 1.5, 4], ERROR_COLORS
        fmap = heat_map(grid, "error_f", cuts, colors, "F")
        key = legend(cuts, colors, "Prediction minus measurement (F). Blue = model too cool, orange = too hot")
    else:
        column = "surface_temp_f" if choice == "Measured by satellite" else "predicted_temp_f"
        # The same cut points for both maps, so they can be compared.
        cuts = [round(float(grid["surface_temp_f"].quantile(q)), 1)
                for q in (0.2, 0.4, 0.6, 0.8)]
        fmap = heat_map(grid, column, cuts, HEAT_COLORS, "F")
        key = legend(cuts, HEAT_COLORS, "Surface temperature (F)")
    st_folium(fmap, height=600, use_container_width=True, returned_objects=[],
              key=f"heat_{choice}")
    st.markdown(key, unsafe_allow_html=True)
    st.caption(
        "Each prediction comes from a model that did not train on that cell's "
        "1 km block. Cells over water or under cloud are left out."
    )

    st.subheader("How accurate is the model?")
    a, b, c = st.columns(3)
    a.metric("R squared (0 to 1, higher is better)", f"{cv['r2']:.2f}")
    b.metric("Average error", f"{cv['mae_f']:.1f} F")
    c.metric("Average error if it just guessed the average", f"{baseline['mae_f']:.1f} F")
    st.markdown(
        f"These come from **spatial cross-validation**: the area is cut into "
        f"{config.MODEL_BLOCK_METERS // 1000} km blocks, and the model is always "
        f"tested on blocks it did not train on. An R squared of {cv['r2']:.2f} "
        f"means the model explains about {100 * cv['r2']:.0f}% of the differences "
        f"in surface temperature between cells. That is a moderate result. "
        f"Measured temperatures only range from {grid['surface_temp_f'].min():.0f} "
        f"to {grid['surface_temp_f'].max():.0f} F, so there is not a lot of "
        f"difference to explain."
    )
    st.dataframe(metrics.rename(columns={"test": "Test", "r2": "R squared",
                                         "mae_f": "Average error (F)"}).round(2),
                 hide_index=True, use_container_width=True)

    st.subheader("What the model relies on")
    st.dataframe(
        importance[["label", "mae_increase_f"]]
        .rename(columns={"label": "Feature",
                         "mae_increase_f": "Error growth when scrambled (F)"}).round(2),
        hide_index=True, use_container_width=True)
    st.caption(
        "Scrambling a feature means shuffling its values so it carries no "
        "information. The more the error grows, the more the model needed it."
    )

    st.subheader("Average by neighborhood")
    by_area = (grid.groupby("ntaname")
               .agg(Cells=("x", "size"), **{
                   "Measured surface temp (F)": ("surface_temp_f", "mean"),
                   "Hottest cell (F)": ("surface_temp_f", "max"),
                   "Coolest cell (F)": ("surface_temp_f", "min"),
                   "Average model error (F)": ("error_f", lambda e: e.abs().mean())})
               .reset_index().rename(columns={"ntaname": "Neighborhood"}))
    st.dataframe(by_area.round(1), hide_index=True, use_container_width=True)

    st.markdown(
        "**Limits of this page**\n"
        "- It is **surface** temperature, not air temperature. A person in the "
        "shade of a tree can feel much cooler than the roof next to them.\n"
        f"- It is **one moment on one day** ({config.LANDSAT_DATE}, late morning). "
        "Other days and times look different.\n"
        "- The built-up index is a satellite estimate, not a measured percent "
        "of pavement. Greenness cannot tell trees from grass.\n"
        "- The model learned from this same area, so it cannot be trusted in "
        "other places without new testing.\n"
        "- This layer is **not** part of the Gap Score."
    )
    st.caption(f"Source: USGS Landsat Collection 2 Level-2, scene "
               f"{config.LANDSAT_ITEM}, read through Microsoft Planetary Computer.")
