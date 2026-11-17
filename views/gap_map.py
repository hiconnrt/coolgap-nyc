"""Page 1: Heat Gap Map."""
import streamlit as st
from streamlit_folium import st_folium

from src import config
from views import common


def render() -> None:
    scores, resources, _ = common.load_all()

    st.title("Heat Gap Map")
    st.markdown(
        "Each neighborhood is colored by its **Cooling Access Gap Score**. A "
        "darker color means higher heat vulnerability together with poorer "
        "access to cooling resources. **Click a neighborhood** to see its details."
    )
    st.info("The Gap Score is my own research score. It is not an official "
            "government or medical measure.")

    whole = st.toggle(f"Show all of {config.BOROUGH}", value=False)
    fmap = common.score_map(scores, whole)
    counted = resources[resources["resource_type"].isin(config.COUNTED_RESOURCE_TYPES)
                        & ~resources["duplicate_of_cooling_center"]
                        & (resources["boroname"] == config.BOROUGH)]
    common.add_resource_dots(fmap, counted[counted["older_adults_only"]],
                             "#eb6834", "older adults only, historical", radius=4)
    common.add_resource_dots(fmap, counted[~counted["older_adults_only"]],
                             "#008300", "open to everyone, historical")
    clicked = st_folium(fmap, height=600, use_container_width=True,
                        returned_objects=["last_active_drawing"], key="gap_map")
    st.markdown(common.score_legend(), unsafe_allow_html=True)
    st.caption("Green dots: cooling resources open to everyone (counted in the "
               "score). Orange dots: cooling centers for older adults only "
               "(counted only in the age 65+ numbers). All locations are historical.")

    # Which neighborhood was clicked? Remember it between reruns.
    drawing = (clicked or {}).get("last_active_drawing") or {}
    code = (drawing.get("properties") or {}).get("nta2020")
    if code and code != st.session_state.get("map_last_click"):
        st.session_state["map_last_click"] = code
        st.session_state["picked_nta"] = code

    names = common.area_names(scores)
    picked = st.session_state.get("picked_nta")
    start = (names.index(scores.set_index("nta2020").loc[picked, "ntaname"])
             if picked else 0)
    name = st.selectbox("Neighborhood (or pick from this list)", names, index=start)
    row = scores[scores["ntaname"] == name].iloc[0]
    st.session_state["picked_nta"] = row["nta2020"]
    common.area_details(row, len(scores))

    st.subheader(f"All {config.FOCUS_NAME} neighborhoods")
    focus = scores[scores["in_focus"]].sort_values("cags", ascending=False)
    st.dataframe(
        focus[["cags_rank", "ntaname", "cags", "hvi", "nearest_miles",
               "pct_pop_within_walk", "resources_inside", "population"]]
        .rename(columns={
            "cags_rank": f"Rank in {config.BOROUGH}", "ntaname": "Neighborhood",
            "cags": "Gap Score", "hvi": "HVI",
            "nearest_miles": "Nearest resource (miles)",
            "pct_pop_within_walk": "Residents within walking distance (%)",
            "resources_inside": "Resources inside area", "population": "Population"})
        .round(2), hide_index=True, use_container_width=True)
    st.caption("Resources are cooling centers open to everyone plus public "
               "libraries, each building counted once. Cooling center data is "
               "historical (summer 2026).")
