"""Page 5: Methods and Limitations."""
import pandas as pd
import streamlit as st

from src import clusters, config
from views import common

SOURCES = [
    ("Heat Vulnerability Index by neighborhood", "NYC Department of Health and Mental Hygiene",
     "https://a816-dohbesp.nyc.gov/IndicatorPublic/data-features/hvi/"),
    ("Cooling centers (Indoor Cool Options), summer 2026", "NYC Emergency Management",
     "https://www.arcgis.com/home/item.html?id=fb0cd480f900469e9f5ebeac3d6b06f0"),
    ("2020 Neighborhood Tabulation Areas", "NYC Department of City Planning",
     "https://data.cityofnewyork.us/d/9nt8-h7nd"),
    ("2020 Census Tracts", "NYC Department of City Planning",
     "https://data.cityofnewyork.us/d/63ge-mke6"),
    ("Census tract to neighborhood lookup", "NYC Department of City Planning",
     "https://data.cityofnewyork.us/d/hm78-6dwm"),
    ("Population by age, ACS 5-year 2020 to 2024, table B01001", "US Census Bureau",
     "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/"),
    ("Public libraries (Facilities Database)", "NYC Department of City Planning",
     "https://data.cityofnewyork.us/d/ji82-xba5"),
    ("Spray showers", "NYC Parks", "https://data.cityofnewyork.us/d/ckaz-6gaa"),
    ("Landsat 9 surface temperature and reflectance, 2022-07-20",
     "US Geological Survey, read through Microsoft Planetary Computer",
     "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2"),
]


@st.cache_data
def k_test_table() -> pd.DataFrame:
    scores, _, _ = common.load_all()
    return clusters.summarize_k(clusters.evaluate_k(scores.drop(columns="geometry")))


def render() -> None:
    scores, _, _ = common.load_all()
    w = config.CAGS_WEIGHTS

    st.title("Methods and Limitations")

    st.header("What this project is")
    st.markdown(
        "CoolGap is a student research project. It asks: can combining heat "
        "vulnerability data with cooling access data find gaps that looking at "
        "either one alone would miss? It covers the "
        f"{len(scores)} residential neighborhoods of {config.BOROUGH} and focuses "
        f"on {config.FOCUS_NAME}."
    )

    st.header("Data sources")
    st.dataframe(pd.DataFrame(SOURCES, columns=["Dataset", "Publisher", "Link"]),
                 hide_index=True, use_container_width=True,
                 column_config={"Link": st.column_config.LinkColumn()})
    st.markdown("Files were downloaded on 2026-11-16 (satellite data on 2026-11-17). Column meanings and "
                "notes for each file are in `data/SOURCES.md`.")

    st.header("The Cooling Access Gap Score (CAGS)")
    st.info("CAGS is my own research score. It is not an official government "
            "or medical measure.")
    st.markdown(
        f"**CAGS = 100 x ( {w['hvi']:.2f} x HVI part + {w['distance']:.2f} x "
        f"Distance part + {w['nearby']:.2f} x Nearby part + "
        f"{w['per_capita']:.2f} x Per person part )**"
    )
    st.dataframe(pd.DataFrame([
        {"Part": "HVI part", "Weight": w["hvi"],
         "What it measures": "NYC Heat Vulnerability Index, 1 to 5",
         "How it becomes 0 to 1": "(HVI - 1) / 4"},
        {"Part": "Distance part", "Weight": w["distance"],
         "What it measures": "Average straight-line miles from residents to the "
                             "nearest cooling resource open to everyone",
         "How it becomes 0 to 1": "Min-max scaling. Farthest = 1"},
        {"Part": "Nearby part", "Weight": w["nearby"],
         "What it measures": f"Average number of resources within "
                             f"{config.WALK_DISTANCE_MILES} miles of residents",
         "How it becomes 0 to 1": "1 minus min-max scaling. Fewest = 1"},
        {"Part": "Per person part", "Weight": w["per_capita"],
         "What it measures": "Resources inside the neighborhood per 10,000 residents",
         "How it becomes 0 to 1": "1 minus min-max scaling. Fewest = 1"},
    ]), hide_index=True, use_container_width=True)
    st.markdown(
        "- **Min-max scaling** means (value - smallest) / (largest - smallest), "
        f"using all {len(scores)} neighborhoods.\n"
        "- **Counted resources** are cooling centers open to everyone and public "
        "libraries. Each building is counted once. Spray showers are shown but "
        "not counted. Centers for older adults only are counted only in the "
        "separate age 65+ numbers.\n"
        "- **Distance** is measured from the center of each census tract, then "
        "averaged for the neighborhood with more weight where more people live.\n"
        "- **The weights are my own choice.** They are stored in `src/config.py`."
    )

    st.header("K-means clustering")
    st.markdown(
        "K-means sorts neighborhoods into groups using four standardized "
        "numbers: HVI, distance to the nearest resource, resources per 10,000 "
        "residents, and green space. I tested 2 to 8 groups with 10 random "
        "starting points each."
    )
    st.dataframe(
        k_test_table().rename(columns={
            "k": "Groups (k)", "silhouette_mean": "Silhouette (average)",
            "silhouette_min": "Silhouette (lowest)", "silhouette_max": "Silhouette (highest)",
            "agreement_mean": "Agreement across seeds (1 = identical)",
            "smallest_group": "Smallest group size"}).round(3),
        hide_index=True, use_container_width=True)
    st.markdown(
        f"**Why the app uses k = {config.CLUSTER_K}.** With 2 groups, K-means "
        "only splits neighborhoods into one group that is worse on everything "
        "(more vulnerable and farther from resources) and one that is better on "
        "everything. That cannot show a mismatch, which is what this project "
        f"looks for. {config.CLUSTER_K} is the smallest number of groups that "
        "separates out neighborhoods where the two do not line up: lower heat "
        "vulnerability but the poorest access to cooling resources."
    )
    st.markdown(
        "**The cost of that choice.** k = 2 has the highest silhouette score and "
        f"gives the same groups for every random start. k = {config.CLUSTER_K} "
        "scores lower and changes somewhat between random starts (see the table). "
        "All the scores are low, so the groups overlap and should be read as "
        "rough descriptions. Group names are written by a rule from each "
        "group's averages after the groups are made."
    )

    st.header("Block-level heat model (stretch goal)")
    st.markdown(
        f"A Random Forest model predicts land surface temperature for "
        f"{config.GRID_CELL_METERS} meter grid cells in {config.FOCUS_NAME}. The "
        f"data is one Landsat 9 satellite scene from {config.LANDSAT_DATE}, a day "
        "with a recorded high of 95 F. Features are greenness (NDVI), a built-up "
        "index (NDBI), surface brightness, the same three for surrounding cells, "
        "and distance to the coast. It is tested with spatial cross-validation, "
        "so it is always scored on 1 km blocks it did not train on. Results are "
        "on the Block-Level Heat page. This layer is not part of the Gap Score."
    )

    st.header("Explanations")
    st.markdown(
        "The text explanations are fill-in-the-blank templates. No AI language "
        "model writes them. Every sentence uses a number shown in the tables."
    )

    st.header("What is real and what is simulated")
    st.dataframe(pd.DataFrame([
        {"Part of the app": "HVI, population, boundaries, resource locations",
         "Status": "Real public data (historical)"},
        {"Part of the app": "Distances, access numbers, Gap Score, clusters",
         "Status": "Calculated by this project from the real data"},
        {"Part of the app": "Block-Level Heat: measured surface temperature",
         "Status": "Real satellite data (one day in 2022)"},
        {"Part of the app": "Block-Level Heat: predicted surface temperature",
         "Status": "Output of a trained model, with its error shown"},
        {"Part of the app": "Sites added on the Simulator page",
         "Status": "SIMULATION. Not real sites and not predictions"},
    ]), hide_index=True, use_container_width=True)

    st.header("Limitations")
    st.markdown(
        "- **Historical cooling center data.** The list is from summer 2026. "
        "Cooling centers change every year and only open during heat emergencies.\n"
        "- **The cooling center file has no stated license** and was made by the "
        "city for its own site survey. It is the best official source I found.\n"
        "- **Straight-line distance.** Real walking routes are longer, and "
        "half a mile is much harder for some people than others, especially in heat.\n"
        "- **No hours or capacity.** A site counts the same whether it is open "
        "two hours or twelve, and whether it holds 20 people or 200.\n"
        "- **Most cooling centers serve older adults only.** For the general "
        "public, the counted resources are mostly library branches.\n"
        "- **Neighborhood averages hide differences** between blocks inside a "
        "neighborhood.\n"
        "- **Surface temperature is not air temperature.** The Block-Level Heat "
        "page shows how hot roofs and ground were on one day in 2022. It is not "
        "what a person feels, and the model explains only about half of the "
        "differences between cells.\n"
        "- **Two score parts overlap.** Distance and the nearby count measure "
        "similar things, so distance is partly counted twice.\n"
        "- **Mismatched years.** The city built the HVI from 2016 to 2020 data. "
        "Population is from 2020 to 2024. Resources are from 2026.\n"
        "- **Population numbers are survey estimates** with margins of error.\n"
        "- **Green space** counts trees, grass, and shrubs together, and it is "
        "also one ingredient of the HVI.\n"
        "- **Home air conditioning is only inside the HVI.** The project does "
        "not know which homes have AC.\n"
        "- **The project cannot say** that any neighborhood is unsafe, that a "
        "person there is at risk, or that adding a site would save lives."
    )

    st.header("Safety and responsible use")
    st.markdown(
        "- **No personal data is collected.** The app does not ask for names, "
        "addresses, locations, or health information.\n"
        "- **Cooling center data is historical.** For current locations use the "
        "official NYC finder at https://finder.nyc.gov/coolingcenters/ or call 311.\n"
        "- **This app does not give emergency instructions. In an emergency, call 911.**\n"
        "- **The Gap Score is a research tool,** not an official measure.\n"
        "- **Simulations are not predictions** that a real center will open or be used."
    )
