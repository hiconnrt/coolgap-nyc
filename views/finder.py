"""Page 3: Cooling Resource Finder."""
import json

import plotly.graph_objects as go
import streamlit as st

from src import config, maps
from views import common

TYPE_LABELS = {key: style["label"] for key, style in maps.RESOURCE_STYLE.items()}


def finder_map(area, found) -> go.Figure:
    """One neighborhood outline with its cooling resources."""
    geojson = json.loads(area[["nta2020", "geometry"]].to_json())
    fig = go.Figure(go.Choroplethmap(
        geojson=geojson, locations=area["nta2020"], featureidkey="properties.nta2020",
        z=[1] * len(area), colorscale=[[0, "#c9bdf3"], [1, "#c9bdf3"]], showscale=False,
        marker={"opacity": 0.35, "line": {"color": "#6250d6", "width": 2}},
        hoverinfo="skip", showlegend=False))
    for kind in ["spray_shower", "library", "cooling_center"]:
        style = maps.RESOURCE_STYLE[kind]
        part = found[found["resource_type"] == kind]
        if part.empty:
            continue
        note = part["older_adults_only"].map({True: "Older adults only", False: ""})
        fig.add_trace(go.Scattermap(
            lat=part["lat"], lon=part["lon"], mode="markers",
            marker={"size": style["size"] + 3, "color": style["color"]},
            name=style["label"],
            customdata=list(zip(part["name"], part["address"].fillna(""), note)),
            hovertemplate=(f"<b>%{{customdata[0]}}</b><br>{style['label']}<br>"
                           "%{customdata[1]}<br>%{customdata[2]}<extra></extra>")))
    west, south, east, north = area.total_bounds
    fig.update_layout(
        map={"style": "carto-positron", "zoom": 12.8,
             "center": {"lat": (south + north) / 2, "lon": (west + east) / 2}},
        margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=520,
        legend={"bgcolor": "rgba(255,255,255,0.9)", "x": 0.01, "y": 0.99,
                "font": {"color": "#0b0b0b"}})
    return fig


def render() -> None:
    scores, resources, _ = common.load_all()

    st.title("Cooling Resource Finder")
    st.error(config.COOLING_DATA_WARNING)
    st.markdown(
        "This page lists the cooling resources in the project's data for one "
        "neighborhood. It does not ask for your address or location."
    )

    names = common.area_names(scores)
    picked = st.session_state.get("picked_nta")
    start = (names.index(scores.set_index("nta2020").loc[picked, "ntaname"])
             if picked else 0)
    name = st.selectbox("Choose a neighborhood", names, index=start)
    area = scores[scores["ntaname"] == name]
    st.session_state["picked_nta"] = area.iloc[0]["nta2020"]

    kinds = st.multiselect("Show these kinds", list(TYPE_LABELS),
                           default=list(TYPE_LABELS), format_func=TYPE_LABELS.get)
    hide_older = st.checkbox("Hide sites that serve older adults only", value=False)

    found = resources[(resources["nta2020"] == area.iloc[0]["nta2020"])
                      & resources["resource_type"].isin(kinds)
                      & ~resources["duplicate_of_cooling_center"]]
    if hide_older:
        found = found[~found["older_adults_only"]]

    st.plotly_chart(finder_map(area, found), use_container_width=True, theme=None)

    st.subheader(f"{len(found)} resources listed in {name}")
    table = found.assign(
        Kind=found["resource_type"].map(TYPE_LABELS),
        Who=found["older_adults_only"].map({True: "Older adults only", False: "Everyone"}),
    ).sort_values(["resource_type", "name"])
    st.dataframe(
        table[["name", "Kind", "address", "Who"]]
        .rename(columns={"name": "Name", "address": "Address", "Who": "Who it serves"}),
        hide_index=True, use_container_width=True)
    st.caption(
        "Cooling centers: NYC Emergency Management, last edited 2026-09-14. "
        "Libraries: NYC Planning Facilities Database. Spray showers: NYC Parks "
        "(each row is one shower, outdoor, summer only). A library that is also "
        "a cooling center is listed once, as a cooling center. Hours are not in "
        "the data. Always check the official finder before going."
    )
