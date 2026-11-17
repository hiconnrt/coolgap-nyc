"""Map drawing, shared by the app and the experiments."""
import json

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go

from src import config

# HVI goes from 1 (lowest risk) to 5 (highest risk). One color family from
# light to dark, so darker always means more vulnerable.
HVI_COLORS = {1: "#fcd9c4", 2: "#f5a57c", 3: "#eb6834", 4: "#b8431a", 5: "#7a2a0e"}

# Marker colors were checked for colorblind safety.
RESOURCE_STYLE = {
    "cooling_center": {"label": "Cooling center (historical)", "color": "#2a78d6", "size": 11},
    "library": {"label": "Public library", "color": "#008300", "size": 9},
    "spray_shower": {"label": "Spray shower (outdoor)", "color": "#e87ba4", "size": 6},
}


# Gap Score colors: one color family, light (small gap) to dark (large gap).
CAGS_COLORSCALE = [[0.0, "#efeafc"], [0.25, "#c9bdf3"], [0.5, "#9085e9"],
                   [0.75, "#6250d6"], [1.0, "#2c1f7a"]]


def load_scores() -> gpd.GeoDataFrame:
    """Neighborhood shapes joined to access numbers, Gap Score, and cluster."""
    scores = pd.read_csv(config.PROCESSED_DIR / "cags_by_nta.csv")
    clusters = pd.read_csv(config.PROCESSED_DIR / "clusters_by_nta.csv")
    shapes = load_areas()[["nta2020", "geometry"]]
    return shapes.merge(scores, on="nta2020").merge(clusters, on="nta2020", how="left")


def zoom_layout(fig: go.Figure, areas: gpd.GeoDataFrame, focus_only_zoom: bool) -> None:
    view = areas[areas["in_focus"]] if focus_only_zoom else areas
    west, south, east, north = view.total_bounds
    fig.update_layout(
        map={"style": "carto-positron",
             "bounds": {"west": west - 0.15, "east": east + 0.15,
                        "south": south - 0.1, "north": north + 0.1},
             "center": {"lat": (south + north) / 2, "lon": (west + east) / 2},
             "zoom": 11.8 if focus_only_zoom else 10.6},
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=620, clickmode="event+select",
        legend={"groupclick": "toggleitem", "bgcolor": "rgba(255,255,255,0.9)",
                "x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top",
                "font": {"color": "#0b0b0b"},
                "grouptitlefont": {"color": "#0b0b0b"}},
    )


def cags_map(scores: gpd.GeoDataFrame, resources: pd.DataFrame,
             focus_only_zoom: bool = True) -> go.Figure:
    """Neighborhoods colored by Gap Score, with the counted resources on top."""
    geojson = json.loads(scores[["nta2020", "geometry"]].to_json())
    fig = go.Figure(go.Choroplethmap(
        geojson=geojson, locations=scores["nta2020"],
        featureidkey="properties.nta2020",
        z=scores["cags"], zmin=0, zmax=100, colorscale=CAGS_COLORSCALE,
        marker={"opacity": 0.8, "line": {"color": "#ffffff", "width": 1.5}},
        colorbar={"title": {"text": "Gap Score<br>(0 to 100)"}, "thickness": 14,
                  "len": 0.5, "x": 0.99, "xanchor": "right", "y": 0.5,
                  "bgcolor": "rgba(255,255,255,0.9)",
                  "tickfont": {"color": "#0b0b0b"},
                  "title_font": {"color": "#0b0b0b"}},
        name="Gap Score", showlegend=False,
        customdata=scores[["ntaname", "cags", "cags_rank", "hvi", "nearest_miles",
                           "resources_nearby", "resources_per_10k",
                           "pct_pop_within_walk"]],
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "Gap Score: %{customdata[1]:.1f} (rank %{customdata[2]})<br>"
                       "HVI: %{customdata[3]} of 5<br>"
                       "Nearest resource: %{customdata[4]:.2f} miles<br>"
                       "Resources within walking distance: %{customdata[5]:.1f}<br>"
                       "Resources per 10,000 residents: %{customdata[6]:.2f}<br>"
                       "Residents within walking distance: %{customdata[7]:.0f}%"
                       "<extra></extra>"),
    ))

    counted = resources[resources["resource_type"].isin(config.COUNTED_RESOURCE_TYPES)
                        & ~resources["duplicate_of_cooling_center"]]
    groups = [("Open to everyone (counted in score)", ~counted["older_adults_only"], "#008300", 10),
              ("Older adults only (65+ measure only)", counted["older_adults_only"], "#eb6834", 7)]
    for label, mask, color, size in reversed(groups):
        part = counted[mask]
        fig.add_trace(go.Scattermap(
            lat=part["lat"], lon=part["lon"], mode="markers",
            marker={"size": size, "color": color, "opacity": 0.95},
            name=label, legendgroup="resources",
            legendgrouptitle={"text": "Cooling resources (historical)"},
            customdata=list(zip(part["name"], part["address"].fillna(""))),
            hovertemplate=(f"<b>%{{customdata[0]}}</b><br>{label}<br>"
                           "%{customdata[1]}<extra></extra>"),
        ))
    zoom_layout(fig, scores, focus_only_zoom)
    return fig


def load_areas() -> gpd.GeoDataFrame:
    return gpd.read_file(config.PROCESSED_DIR / "nta_areas.geojson")


def load_resources() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "cooling_resources.csv")


def hvi_map(areas: gpd.GeoDataFrame, resources: pd.DataFrame,
            focus_only_zoom: bool = True) -> go.Figure:
    """Neighborhoods colored by HVI, with cooling resources as dots on top."""
    geojson = json.loads(areas[["nta2020", "geometry"]].to_json())
    fig = go.Figure()

    # One layer per HVI level so the legend shows the five levels.
    for level, color in HVI_COLORS.items():
        part = areas[areas["hvi"] == level]
        if part.empty:
            continue
        fig.add_trace(go.Choroplethmap(
            geojson=geojson,
            locations=part["nta2020"],
            featureidkey="properties.nta2020",
            z=[level] * len(part),
            colorscale=[[0, color], [1, color]],
            showscale=False,
            marker={"opacity": 0.75, "line": {"color": "#ffffff", "width": 1.5}},
            name=f"HVI {level}" + (" (lowest risk)" if level == 1 else
                                   " (highest risk)" if level == 5 else ""),
            showlegend=True,
            legendgroup="hvi",
            legendgrouptitle={"text": "Heat Vulnerability Index"},
            customdata=part[["ntaname", "hvi", "surface_temp_f", "greenspace_pct",
                             "pct_households_ac", "median_income",
                             "population", "pct_65_plus"]],
            hovertemplate=("<b>%{customdata[0]}</b><br>"
                           "HVI: %{customdata[1]} of 5<br>"
                           "Surface temperature: %{customdata[2]:.1f} F<br>"
                           "Green space: %{customdata[3]:.0f}%<br>"
                           "Households with AC: %{customdata[4]:.0f}%<br>"
                           "Median income: $%{customdata[5]:,.0f}<br>"
                           "Population: %{customdata[6]:,.0f}<br>"
                           "Age 65 and over: %{customdata[7]:.1f}%<extra></extra>"),
        ))

    # Cooling resources. Drawn smallest first so cooling centers end up on top.
    for kind in ["spray_shower", "library", "cooling_center"]:
        style = RESOURCE_STYLE[kind]
        part = resources[resources["resource_type"] == kind]
        note = part["older_adults_only"].map({True: "Older adults only", False: ""})
        fig.add_trace(go.Scattermap(
            lat=part["lat"], lon=part["lon"], mode="markers",
            marker={"size": style["size"], "color": style["color"], "opacity": 0.95},
            name=style["label"],
            legendgroup="resources",
            legendgrouptitle={"text": "Cooling resources"},
            customdata=list(zip(part["name"], part["address"].fillna(""), note)),
            hovertemplate=(f"<b>%{{customdata[0]}}</b><br>{style['label']}<br>"
                           "%{customdata[1]}<br>%{customdata[2]}<extra></extra>"),
        ))

    zoom_layout(fig, areas, focus_only_zoom)
    return fig


def hvi_table(areas: gpd.GeoDataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    """Plain table of each area with its HVI values and resource counts."""
    counts = (resources.groupby(["nta2020", "resource_type"]).size()
              .unstack(fill_value=0)
              .reindex(columns=list(RESOURCE_STYLE), fill_value=0))
    table = areas.drop(columns="geometry").merge(counts, on="nta2020", how="left")
    table[list(RESOURCE_STYLE)] = table[list(RESOURCE_STYLE)].fillna(0).astype(int)
    table = table.rename(columns={
        "ntaname": "Neighborhood", "hvi": "HVI (1 to 5)",
        "surface_temp_f": "Surface temp (F)", "greenspace_pct": "Green space (%)",
        "pct_households_ac": "Households with AC (%)",
        "median_income": "Median income ($)",
        "population": "Population", "pop_65_plus": "Age 65+",
        "pct_65_plus": "Age 65+ (%)",
        "cooling_center": "Cooling centers", "library": "Libraries",
        "spray_shower": "Spray showers",
    })
    columns = ["Neighborhood", "HVI (1 to 5)", "Population", "Age 65+",
               "Age 65+ (%)", "Surface temp (F)", "Green space (%)",
               "Households with AC (%)", "Median income ($)", "Cooling centers",
               "Libraries", "Spray showers"]
    return (table[columns + ["in_focus"]]
            .sort_values(["HVI (1 to 5)", "Neighborhood"], ascending=[False, True])
            .round({"Surface temp (F)": 1, "Green space (%)": 1,
                    "Households with AC (%)": 1})
            .astype({"Median income ($)": int})
            .reset_index(drop=True))
