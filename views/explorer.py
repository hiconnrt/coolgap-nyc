"""Page 2: Neighborhood Explorer."""
import pandas as pd
import streamlit as st

from src import clusters, config
from views import common

# (column, label, number of decimals)
NUMBERS = [
    ("cags", "Gap Score (0 to 100)", 1),
    ("hvi", "Heat Vulnerability Index (1 to 5)", 0),
    ("population", "Population", 0),
    ("pct_65_plus", "Residents aged 65+ (%)", 1),
    ("nearest_miles", "Nearest resource open to everyone (miles)", 2),
    ("resources_nearby", f"Resources within {config.WALK_DISTANCE_MILES} miles (average)", 1),
    ("pct_pop_within_walk", "Residents within walking distance (%)", 0),
    ("resources_inside", "Resources inside the area", 0),
    ("resources_per_10k", "Resources per 10,000 residents", 2),
    ("pct_65_within_walk", "Age 65+ within walking distance, counting older adult sites (%)", 0),
    ("greenspace_pct", "Green space (%)", 1),
    ("surface_temp_f", "Summer surface temperature (F)", 1),
    ("pct_households_ac", "Households with air conditioning (%)", 1),
    ("median_income", "Median household income ($)", 0),
]


def render() -> None:
    scores, _, _ = common.load_all()

    st.title("Neighborhood Explorer")
    names = common.area_names(scores)
    picked = st.session_state.get("picked_nta")
    start = (names.index(scores.set_index("nta2020").loc[picked, "ntaname"])
             if picked else 0)
    name = st.selectbox("Choose a neighborhood", names, index=start)
    row = scores[scores["ntaname"] == name].iloc[0]
    st.session_state["picked_nta"] = row["nta2020"]

    common.area_details(row, len(scores))

    st.subheader("The numbers")
    table = pd.DataFrame([{
        "Measure": label,
        name: f"{row[col]:,.{dec}f}",
        f"{config.BOROUGH} middle value (median)": f"{scores[col].median():,.{dec}f}",
    } for col, label, dec in NUMBERS])
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.caption("Population is a Census survey estimate (2020 to 2024). HVI, "
               "temperature, green space, AC, and income come from the NYC "
               "Health Department. Access numbers are calculated by this project.")

    st.subheader("Its group (K-means clustering)")
    st.markdown(
        f"**Group {int(row['cluster'])} of {config.CLUSTER_K}: {row['cluster_name']}**"
    )
    st.markdown(
        "K-means is a machine learning method that sorts neighborhoods into "
        "groups that look alike on four numbers: HVI, distance to the nearest "
        "resource, resources per 10,000 residents, and green space. The group "
        "names are written by a rule from each group's averages, compared with "
        f"the {config.BOROUGH} average."
    )
    summary = (scores.groupby(["cluster", "cluster_name"])
               .agg(Neighborhoods=("nta2020", "size"),
                    **{clusters.FEATURE_LABELS[f]: (f, "mean") for f in clusters.FEATURES},
                    **{"Average Gap Score": ("cags", "mean")})
               .reset_index()
               .rename(columns={"cluster": "Group", "cluster_name": "Group name"}))
    st.dataframe(summary.round(2), hide_index=True, use_container_width=True)

    same = scores[scores["cluster"] == row["cluster"]].sort_values("cags", ascending=False)
    with st.expander(f"All {len(same)} neighborhoods in group {int(row['cluster'])}"):
        st.dataframe(same[["ntaname", "cags", "hvi", "nearest_miles",
                           "resources_per_10k", "greenspace_pct"]]
                     .rename(columns={"ntaname": "Neighborhood", "cags": "Gap Score",
                                      "hvi": "HVI", "nearest_miles": "Nearest resource (miles)",
                                      "resources_per_10k": "Resources per 10,000",
                                      "greenspace_pct": "Green space (%)"})
                     .round(2), hide_index=True, use_container_width=True)
    st.caption("The groups overlap a lot (see the Methods page), so treat a group "
               "as a rough description, not a hard category.")
