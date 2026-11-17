"""Things every page of the app shares: data loading and small helpers."""
import json

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import access, config, explain, gap_score, maps


@st.cache_data
def load_all():
    """Read the processed files once and reuse them on every page."""
    scores = maps.load_scores()          # shapes + HVI + access + score + cluster
    resources = maps.load_resources()
    tracts = access.load_tracts()
    return scores, resources, tracts


def score_color(score: float) -> str:
    """Pick the map color for a Gap Score, light (low) to dark (high)."""
    steps = maps.CAGS_COLORSCALE
    for cutoff, color in reversed(steps):
        if score / 100 >= cutoff:
            return color
    return steps[0][1]


def score_legend() -> str:
    """Small color key shown under the folium maps."""
    labels = ["0 to 24", "25 to 49", "50 to 74", "75 to 99", "100"]
    boxes = "".join(
        f'<span style="display:inline-block;width:14px;height:14px;background:{color};'
        f'border:1px solid #898781;margin:0 4px 0 12px;vertical-align:middle"></span>{label}'
        for (_, color), label in zip(maps.CAGS_COLORSCALE, labels))
    return f"<div>Gap Score: {boxes}</div>"


def score_map(shown, whole: bool) -> folium.Map:
    """Folium map of neighborhoods colored by Gap Score.

    `shown` needs the columns nta2020, ntaname, cags, cags_rank, in_focus and
    geometry. Folium is used because it reports clicks on the map.
    """
    view = shown if whole else shown[shown["in_focus"]]
    west, south, east, north = view.total_bounds
    fmap = folium.Map(tiles="OpenStreetMap", control_scale=True, scrollWheelZoom=False)
    fmap.fit_bounds([[south, west], [north, east]])

    shown = shown.assign(label=[f"{name}: Gap Score {score:.1f} (rank {rank})"
                                for name, score, rank in
                                zip(shown["ntaname"], shown["cags"], shown["cags_rank"])])
    folium.GeoJson(
        json.loads(shown[["nta2020", "label", "cags", "geometry"]].to_json()),
        style_function=lambda f: {"fillColor": score_color(f["properties"]["cags"]),
                                  "color": "#ffffff", "weight": 1.5, "fillOpacity": 0.8},
        highlight_function=lambda f: {"weight": 4, "color": "#0b0b0b"},
        tooltip=folium.GeoJsonTooltip(fields=["label"], labels=False),
    ).add_to(fmap)
    return fmap


def add_resource_dots(fmap: folium.Map, resources: pd.DataFrame,
                      color: str, note: str, radius: int = 5) -> None:
    for _, r in resources.iterrows():
        folium.CircleMarker([r["lat"], r["lon"]], radius=radius, color="#ffffff", weight=1,
                            fill=True, fill_color=color, fill_opacity=1,
                            tooltip=f"{r['name']} ({note})").add_to(fmap)


def area_names(scores: pd.DataFrame) -> list[str]:
    """Neighborhood names: focus area first, then the rest, both A to Z."""
    focus = sorted(scores[scores["in_focus"]]["ntaname"])
    rest = sorted(scores[~scores["in_focus"]]["ntaname"])
    return focus + rest


def points_chart(row: pd.Series) -> go.Figure:
    """Bar chart of the points each part adds to one area's Gap Score."""
    parts = gap_score.PARTS
    labels = [gap_score.PART_LABELS[p] for p in parts]
    points = [row[f"points_{p}"] for p in parts]
    most = [100 * config.CAGS_WEIGHTS[p] for p in parts]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=most, orientation="h", marker_color="#e1e0d9",
        name="Most points possible", hovertemplate="Most possible: %{x:.0f}<extra></extra>"))
    fig.add_trace(go.Bar(
        y=labels, x=points, orientation="h", marker_color="#6250d6",
        name="Points this area gets", text=[f"{v:.1f}" for v in points],
        textposition="outside", hovertemplate="%{y}: %{x:.1f} points<extra></extra>"))
    fig.update_layout(
        barmode="overlay", height=260, margin={"l": 0, "r": 30, "t": 10, "b": 0},
        xaxis={"title": "Points added to the Gap Score", "range": [0, 46]},
        yaxis={"autorange": "reversed"},
        legend={"orientation": "h", "y": -0.35})
    return fig


def area_details(row: pd.Series, total: int) -> None:
    """The detail block shown when an area is picked."""
    st.subheader(row["ntaname"])
    a, b, c, d = st.columns(4)
    a.metric("Gap Score (0 to 100)", f"{row['cags']:.1f}")
    b.metric(f"Rank in {config.BOROUGH}", f"{int(row['cags_rank'])} of {total}")
    c.metric("Heat Vulnerability Index", f"{int(row['hvi'])} of 5")
    d.metric("Population", f"{int(row['population']):,}")
    st.markdown(explain.explain_area(row, total))
    st.plotly_chart(points_chart(row), use_container_width=True)
    st.caption("Every sentence above is built from the numbers in the tables. "
               "The Gap Score is a research score, not an official measure.")
