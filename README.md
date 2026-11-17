# CoolGap: AI Mapping of Heat Risk and Cooling Access in Southern Brooklyn

A student research project for the 2027 Presidential SI Challenge.

## What this project does

Some New York City neighborhoods are more vulnerable to extreme heat than
others. The city also has cooling resources, like cooling centers and
libraries. But the two do not always line up. A neighborhood can be very
vulnerable to heat and still be far from a place to cool down.

CoolGap puts the two kinds of data together. It:

1. Maps the city's Heat Vulnerability Index (HVI) for every Brooklyn neighborhood.
2. Measures how close residents are to cooling resources.
3. Combines both into one number, the **Cooling Access Gap Score (CAGS)**.
4. Uses K-means clustering (a machine learning method) to group similar neighborhoods.
5. Lets you add a hypothetical cooling center on a map and see what changes (a **simulation**).
6. Explains every score in plain sentences built from the numbers.
7. Trains a Random Forest model on satellite data to estimate surface heat block by block (a stretch goal).

The focus area is southern Brooklyn: Coney Island, Brighton Beach, Gravesend,
Bensonhurst, Bath Beach, Sheepshead Bay, and nearby.

**Research question:** Can an AI-assisted geospatial system find mismatches
between heat vulnerability and cooling access better than looking at either
dataset alone?

## Important warnings

- **This is a research project, not an official city tool.**
- **The Gap Score is my own score.** It is not an official government or medical measure.
- **Cooling center data is historical** (summer 2026). Cooling centers change every summer and only open during heat emergencies. For current locations use the official NYC finder at https://finder.nyc.gov/coolingcenters/ or call 311.
- **The app does not give emergency instructions. In an emergency, call 911.**
- **Simulations are not predictions** that a real center will open or be used.
- **No personal data is collected.**

## How to run it

You need Python 3.11 or newer.

```bash
cd coolgap
python -m venv .venv
.venv\Scripts\activate          # on Mac or Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The processed data files are already in `data/processed/`, so the app runs
right away. To rebuild everything from the original sources, run these in order:

```bash
python -m src.load_data     # download raw files (one file is about 200 MB to read through)
python -m src.clean         # clean and match everything to neighborhoods
python -m src.access        # distance and access numbers
python -m src.gap_score     # the Gap Score
python -m src.clusters      # K-means groups
python -m src.satellite     # download the Landsat window and build the 100 m grid
python -m experiments.exp_e_model   # train and test the heat model
```

To rerun the experiments:

```bash
python -m experiments.exp_a_baseline
python -m experiments.exp_b_clusters
python -m experiments.exp_c_simulator
python -m experiments.exp_d_weights
python -m experiments.exp_e_model
```

### Putting it on Streamlit Community Cloud

1. Put the `coolgap` folder in a public GitHub repository (include `data/processed/`).
2. On https://share.streamlit.io choose the repository.
3. Set the main file to `app.py` (or `coolgap/app.py` if the repository holds the whole parent folder).
4. Deploy. Streamlit installs everything in `requirements.txt`.

This has not been deployed yet: `[DEPLOYED APP LINK]`

## The app pages

| Page | What it shows |
|---|---|
| Heat Gap Map | Neighborhoods colored by Gap Score. Click one for details. |
| Neighborhood Explorer | All the numbers for one neighborhood, its K-means group, and a written explanation. |
| Cooling Resource Finder | Cooling centers, libraries, and spray showers in one neighborhood, with the historical data warning. |
| Simulator | Click the map to add a hypothetical cooling center. Labeled SIMULATION. |
| Block-Level Heat | Satellite surface temperature for 100 meter cells, the trained model's predictions, and its accuracy. |
| Methods and Limitations | Data sources, the formula, the weights, and what the project can and cannot say. |

## How the Gap Score works

```
CAGS = 100 x ( 0.40 x HVI part
             + 0.25 x Distance part
             + 0.20 x Nearby part
             + 0.15 x Per person part )
```

Each part is a number from 0 to 1, where 1 is the worse direction.

| Part | What it measures |
|---|---|
| HVI part | The city's Heat Vulnerability Index (1 to 5), turned into 0 to 1 |
| Distance part | Average straight-line distance from residents to the nearest cooling resource open to everyone |
| Nearby part | Average number of resources within 0.5 miles of residents (fewer is worse) |
| Per person part | Resources inside the neighborhood per 10,000 residents (fewer is worse) |

The weights are my own choice and are stored in `src/config.py`. Experiment D
tests what happens when they change.

## Data sources

All data is real public data, downloaded on 2026-11-16 and 2026-11-17. Full details, links,
and the meaning of every column are in [`data/SOURCES.md`](data/SOURCES.md).

| Data | Publisher |
|---|---|
| Heat Vulnerability Index by neighborhood | NYC Department of Health and Mental Hygiene |
| Cooling centers (summer 2026) | NYC Emergency Management |
| Neighborhood and census tract boundaries | NYC Department of City Planning |
| Population by age (ACS 2020 to 2024) | US Census Bureau |
| Public libraries | NYC Department of City Planning |
| Spray showers | NYC Parks |
| Landsat 9 satellite scene (2022-07-20) | US Geological Survey, read through Microsoft Planetary Computer |

## Folder guide

```
coolgap/
  app.py              the Streamlit app (just the menu)
  views/              one file per app page
  src/
    config.py         every setting in one place (area, weights, links)
    load_data.py      downloads raw data
    clean.py          cleans data and matches it to neighborhoods
    access.py         distance and access calculations
    gap_score.py      the Cooling Access Gap Score
    clusters.py       K-means clustering
    simulator.py      add a hypothetical cooling center
    explain.py        plain language explanations
    satellite.py      downloads the Landsat scene and builds the 100 m grid
    model.py          Random Forest model for surface temperature
    maps.py           map drawing helpers
  experiments/        experiment scripts, results, and the feedback form
  data/
    raw/              downloaded files, never edited
    processed/        cleaned and calculated files
    SOURCES.md        where every dataset came from
  sample_data/        for FAKE test data only (empty, none was needed)
```

To study a different borough, change `BOROUGH` and `FOCUS_CDTAS` in
`src/config.py` and rerun the steps above.

## What is real and what is simulated

| Part | Status |
|---|---|
| HVI, population, boundaries, resource locations | Real public data (historical) |
| Distances, access numbers, Gap Score, clusters | Calculated by this project from the real data |
| Sites added in the Simulator and in Experiment C | SIMULATION, not real |
| Block-Level Heat, measured | Real satellite data from one day in 2022 |
| Block-Level Heat, predicted | Output of a trained model (R squared 0.50 in spatial cross-validation) |

## Main limitations

- Distances are straight lines, not real walking routes.
- The data has no opening hours and no building capacity.
- Most cooling centers serve older adults only, so for the general public the counted resources are mostly libraries.
- The years do not match: HVI uses 2016 to 2020 data, population is 2020 to 2024, resources are 2026.
- Neighborhood averages hide differences between blocks.
- The K-means groups overlap a lot (low silhouette scores).
- The block-level layer is surface temperature on one day, not the air temperature people feel.

The full list is on the Methods and Limitations page of the app.

## Not built yet

- User testing has not been done. The form is in `experiments/user_feedback_form.md`.

## Author

`[TEAM LEADER NAME]`, `[SCHOOL NAME]`, Brooklyn, New York
