"""Page 4: Simulator. Everything on this page is a SIMULATION."""
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src import access, config, maps, simulator
from views import common

WALK_METERS = config.WALK_DISTANCE_MILES * 1609.34

MAX_SITES = 3


@st.cache_data
def example_sites() -> dict:
    """Two saved locations from Experiment C, so the demo can be repeated exactly."""
    path = config.RESULTS_DIR / "exp_c_scenarios.csv"
    if not path.exists():
        return {}
    table = pd.read_csv(path)

    def first_site(row_number: int) -> tuple[float, float]:
        lat, lon = table.loc[row_number, "sites"].split(";")[0].split(",")
        return (round(float(lat), 5), round(float(lon), 5))

    return {
        "Example 1: center of the highest-gap neighborhood": first_site(1),
        "Example 2: best spot found by the search": first_site(2),
    }


def sim_map(scores, new_scores, resources, result, sites, whole) -> folium.Map:
    """Gap Score map with real resources, simulated sites, and newly reached tracts."""
    shown = scores[["nta2020", "geometry", "in_focus", "ntaname"]].merge(
        new_scores[["nta2020", "cags", "cags_rank"]], on="nta2020")
    fmap = common.score_map(shown, whole)

    real = access.counted_resources(resources, include_older_adult_sites=False)
    common.add_resource_dots(fmap, real[real["boroname"] == config.BOROUGH],
                             "#008300", "real, historical")

    for _, t in result["newly_reached_tracts"].iterrows():
        folium.CircleMarker([t["lat"], t["lon"]], radius=7, color="#ffffff", weight=1,
                            fill=True, fill_color="#eb6834", fill_opacity=0.9,
                            tooltip=f"SIMULATED: {int(t['population']):,} residents "
                                    "newly within walking distance").add_to(fmap)

    for i, (lat, lon) in enumerate(sites):
        folium.Circle([lat, lon], radius=WALK_METERS, color="#0b0b0b", weight=2,
                      fill=False, dash_array="6").add_to(fmap)
        folium.Marker([lat, lon], tooltip=f"SIMULATED site {i + 1} (not real)",
                      icon=folium.Icon(color="black", icon="star")).add_to(fmap)
    return fmap


def render() -> None:
    scores, resources, tracts = common.load_all()
    st.session_state.setdefault("sim_sites", [])
    st.session_state.setdefault("sim_map_version", 0)
    sites = st.session_state["sim_sites"]

    st.title("Simulator")
    st.error(config.SIMULATION_WARNING)
    st.markdown(
        f"**Click anywhere on the map** to add a hypothetical cooling center "
        f"that is open to everyone (up to {MAX_SITES}). The app then recalculates "
        f"cooling access and the Gap Score, and counts how many residents are "
        f"newly within {config.WALK_DISTANCE_MILES} miles of a resource."
    )

    left, right = st.columns([3, 1])
    whole = left.toggle(f"Show all of {config.BOROUGH}", value=False)
    if right.button("Remove all simulated sites", disabled=not sites):
        st.session_state["sim_sites"] = []
        st.session_state["sim_map_version"] += 1   # forget the old click
        st.rerun()

    examples = example_sites()
    if examples:
        st.caption("Or load a saved location from Experiment C (still a SIMULATION):")
        for column, (label, site) in zip(st.columns(len(examples)), examples.items()):
            if column.button(label, use_container_width=True):
                st.session_state["sim_sites"] = [site]
                st.session_state["sim_map_version"] += 1
                st.rerun()

    areas = scores.drop(columns="geometry")
    baseline = areas.copy()
    plain_areas = areas[[c for c in areas.columns if c in
                         ("nta2020", "ntaname", "hvi", "population", "pop_65_plus",
                          "in_focus", "greenspace_pct")]]
    result = simulator.simulate(plain_areas, tracts, resources, sites, baseline)

    clicked = st_folium(
        sim_map(scores, result["new_scores"], resources, result, sites, whole),
        height=600, use_container_width=True, returned_objects=["last_clicked"],
        key=f"sim_map_{st.session_state['sim_map_version']}")
    st.markdown(common.score_legend(), unsafe_allow_html=True)
    st.caption(
        "Green dots: real resources open to everyone (historical). Black star "
        "and dashed circle: SIMULATED site and its "
        f"{config.WALK_DISTANCE_MILES} mile straight-line reach. Orange dots: "
        "census tracts newly within walking distance (SIMULATED). Darker purple "
        "means a higher Gap Score."
    )

    # A click anywhere on the map adds a simulated site there.
    click = (clicked or {}).get("last_clicked")
    if click:
        site = (round(click["lat"], 5), round(click["lng"], 5))
        if site != st.session_state.get("sim_last_click"):
            st.session_state["sim_last_click"] = site
            if len(sites) < MAX_SITES:
                st.session_state["sim_sites"] = sites + [site]
                st.rerun()
            else:
                st.warning(f"The limit is {MAX_SITES} simulated sites. Remove them to start over.")

    s = result["summary"]
    st.subheader("SIMULATION result" if sites else "Today's numbers (no simulated sites yet)")
    a, b, c = st.columns(3)
    a.metric("Simulated sites added", s["sites_added"])
    b.metric(f"Residents newly within {config.WALK_DISTANCE_MILES} miles",
             f"{s['people_newly_within_walk']:,}")
    c.metric(f"{config.BOROUGH} residents within {config.WALK_DISTANCE_MILES} miles",
             f"{s['pct_within_walk_after']:.1f}%",
             delta=f"{s['pct_within_walk_after'] - s['pct_within_walk_before']:.2f} points"
             if sites else None)
    focus_codes = set(scores[scores["in_focus"]]["nta2020"])
    reached = result["newly_reached_tracts"]
    focus_new = int(reached[reached["nta2020"].isin(focus_codes)]["population"].sum())
    if sites:
        st.markdown(f"Of the residents newly within walking distance, **{focus_new:,}** "
                    f"live in {config.FOCUS_NAME}.")
    st.caption(
        f"Before: {s['pct_within_walk_before']:.1f}% of {config.BOROUGH} residents "
        f"were within {config.WALK_DISTANCE_MILES} miles of a resource open to "
        f"everyone. For residents aged 65 and over (counting older adult sites): "
        f"{s['pct_65_within_walk_before']:.1f}% before, "
        f"{s['pct_65_within_walk_after']:.1f}% after, "
        f"{s['people_65_newly_within_walk']:,} newly within walking distance."
    )

    if sites:
        changed = result["changed_areas"]
        st.subheader(f"Neighborhoods whose Gap Score changed ({len(changed)})")
        st.dataframe(
            changed[["ntaname", "cags_before", "cags_after", "cags_change",
                     "cags_rank_before", "cags_rank_after",
                     "pct_pop_within_walk_before", "pct_pop_within_walk_after",
                     "nearest_miles_before", "nearest_miles_after"]]
            .rename(columns={
                "ntaname": "Neighborhood", "cags_before": "Gap Score before",
                "cags_after": "Gap Score after (SIMULATED)", "cags_change": "Change",
                "cags_rank_before": "Rank before", "cags_rank_after": "Rank after",
                "pct_pop_within_walk_before": "Within walking distance before (%)",
                "pct_pop_within_walk_after": "Within walking distance after (%)",
                "nearest_miles_before": "Nearest resource before (miles)",
                "nearest_miles_after": "Nearest resource after (miles)"})
            .round(2), hide_index=True, use_container_width=True)
        st.caption("Ranks can also shift by one or two places for neighborhoods "
                   "whose own score did not change.")

    st.markdown(
        "**What this simulation leaves out:** whether a building exists at that "
        "spot, cost, opening hours, how many people a site can hold, real walking "
        "routes, and whether people would actually go. It is a planning question "
        "starter, not an answer."
    )
