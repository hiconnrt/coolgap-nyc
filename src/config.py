"""All project settings live in this one file.

To study a different area, change BOROUGH and FOCUS_CDTAS below.
Nothing else in the code needs to change.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "experiments" / "results"

# ---------------------------------------------------------------------------
# Study area (the one setting to change for a different area)
# ---------------------------------------------------------------------------
BOROUGH = "Brooklyn"

# County FIPS codes the Census Bureau uses for each NYC borough.
BOROUGH_COUNTY_FIPS = {
    "Bronx": "005",
    "Brooklyn": "047",
    "Manhattan": "061",
    "Queens": "081",
    "Staten Island": "085",
}
STATE_FIPS = "36"  # New York State

# The focus area inside the borough. These are Community District
# Tabulation Area codes from NYC Planning.
#   BK11 = Bensonhurst, Bath Beach, Gravesend (West), Mapleton
#   BK13 = Coney Island, Brighton Beach, Sea Gate, Gravesend (South)
#   BK15 = Sheepshead Bay, Manhattan Beach, Gerritsen Beach, Homecrest
# Scores are calculated for the whole borough. The focus area is what the
# maps zoom to and what the tables highlight.
FOCUS_CDTAS = ["BK11", "BK13", "BK15"]
FOCUS_NAME = "Southern Brooklyn"

# Only areas where people live are scored. In the NYC Planning file,
# ntatype "0" means a residential neighborhood. Other codes are parks,
# cemeteries, airports and similar places.
RESIDENTIAL_NTATYPE = "0"

# ---------------------------------------------------------------------------
# Map projections
# ---------------------------------------------------------------------------
CRS_LATLON = "EPSG:4326"   # normal latitude and longitude, used for maps
CRS_FEET = "EPSG:2263"     # NY State Plane (feet), used to measure distance

# ---------------------------------------------------------------------------
# Data sources (official links, checked 2026-11-16)
# ---------------------------------------------------------------------------
ACS_YEAR = 2024  # ACS 5-year estimates covering 2020 to 2024

SOURCES = {
    "hvi": {
        "file": "hvi_nta_2020.csv",
        "url": "https://raw.githubusercontent.com/nychealth/EHDP-data/production/"
               "key-topics/heat-vulnerability-index/hvi-nta-2020.csv",
        "publisher": "NYC Department of Health and Mental Hygiene",
    },
    "cooling_centers": {
        "file": "cooling_centers_nycem.geojson",
        "url": "https://services1.arcgis.com/8cuieNI8NbqQZQVJ/arcgis/rest/services/"
               "NYC_Open_Cooling_Centers_Site_Survey_view/FeatureServer/1/query"
               "?where=1%3D1&outFields=*&outSR=4326&f=geojson",
        "publisher": "NYC Emergency Management",
    },
    "nta_boundaries": {
        "file": "nta_2020.geojson",
        "url": "https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?$limit=5000",
        "publisher": "NYC Department of City Planning",
    },
    "tract_to_nta": {
        "file": "tract_to_nta_2020.csv",
        "url": "https://data.cityofnewyork.us/resource/hm78-6dwm.csv?$limit=5000",
        "publisher": "NYC Department of City Planning",
    },
    "acs_age": {
        # The Census API needs a key, so this uses the Census Bureau's public
        # summary file instead. It is the same table (B01001, Sex by Age).
        # The file covers the whole country (about 200 MB), so the download
        # script keeps only the header and the census tract rows for the
        # chosen borough. The kept rows are not changed in any way.
        "file": f"acs{ACS_YEAR}_b01001_tracts_{BOROUGH_COUNTY_FIPS[BOROUGH]}.dat",
        "url": f"https://www2.census.gov/programs-surveys/acs/summary_file/{ACS_YEAR}/"
               f"table-based-SF/data/5YRData/acsdt5y{ACS_YEAR}-b01001.dat",
        "keep_rows_starting_with":
            f"1400000US{STATE_FIPS}{BOROUGH_COUNTY_FIPS[BOROUGH]}",
        "publisher": "US Census Bureau",
    },
    "tract_boundaries": {
        "file": f"tracts_2020_{BOROUGH.lower().replace(' ', '_')}.geojson",
        "url": "https://data.cityofnewyork.us/resource/63ge-mke6.geojson"
               f"?boroname={BOROUGH.replace(' ', '%20')}&$limit=5000",
        "publisher": "NYC Department of City Planning",
    },
    "libraries": {
        "file": "facdb_libraries.csv",
        "url": "https://data.cityofnewyork.us/resource/ji82-xba5.csv"
               "?$where=facsubgrp%3D%27PUBLIC%20LIBRARIES%27&$limit=5000",
        "publisher": "NYC Department of City Planning",
    },
    "spray_showers": {
        "file": "parks_spray_showers.geojson",
        "url": "https://data.cityofnewyork.us/resource/ckaz-6gaa.geojson?$limit=5000",
        "publisher": "NYC Parks",
    },
}

# ---------------------------------------------------------------------------
# Cooling access settings (Phase 2)
# ---------------------------------------------------------------------------
# How far counts as "walking distance". Measured in a straight line.
WALK_DISTANCE_MILES = 0.5
FEET_PER_MILE = 5280

# A library that sits within this many feet of a library-run cooling center
# is treated as the same building, so it is only counted once.
SAME_BUILDING_FEET = 400

# Which resource types count toward the access numbers and the score.
# Spray showers are shown on the map but not counted, because they are
# outdoors and only run in summer.
COUNTED_RESOURCE_TYPES = ["cooling_center", "library"]

# ---------------------------------------------------------------------------
# Cooling Access Gap Score (CAGS) weights
# ---------------------------------------------------------------------------
# This is the student's own research score. It is NOT an official government
# or medical measure. The weights are a judgment call and must add up to 1.
# Experiment D tests how much the results change when these change.
CAGS_WEIGHTS = {
    "hvi": 0.40,             # heat vulnerability (higher HVI = higher score)
    "distance": 0.25,        # distance to nearest resource (farther = higher)
    "nearby": 0.20,          # resources within walking distance (fewer = higher)
    "per_capita": 0.15,      # resources per 10,000 residents (fewer = higher)
}

# ---------------------------------------------------------------------------
# K-means clustering (Phase 3)
# ---------------------------------------------------------------------------
# The four numbers each neighborhood is grouped on.
CLUSTER_FEATURES = ["hvi", "nearest_miles", "resources_per_10k", "greenspace_pct"]
CLUSTER_K_RANGE = range(2, 9)   # the values of k that get tested (2 to 8)
CLUSTER_SEEDS = range(10)       # 10 random starting points, to test stability
# The number of groups used in the app. Chosen after looking at the test
# results. See the Methods page and src/clusters.py for the reasons.
CLUSTER_K = 3
CLUSTER_SEED = 0

# ---------------------------------------------------------------------------
# Block-level heat model (Phase 4)
# ---------------------------------------------------------------------------
# One Landsat 9 scene from a hot, clear summer day. The recorded high that
# day was 95 F at both JFK Airport and Central Park (NOAA daily summaries).
# Source: USGS Landsat Collection 2 Level-2, read through Microsoft
# Planetary Computer (no account needed).
LANDSAT_ITEM = "LC09_L2SP_014032_20220720_02_T1"
LANDSAT_DATE = "2022-07-20"
LANDSAT_COLLECTION = "landsat-c2-l2"
PLANETARY_COMPUTER = "https://planetarycomputer.microsoft.com/api"
# Bands saved: red and near-infrared (for NDVI), shortwave infrared (for the
# built-up index), surface temperature, and the quality band (clouds, water).
LANDSAT_BANDS = ["red", "nir08", "swir16", "lwir11", "qa_pixel"]
LANDSAT_DIR = RAW_DIR / "landsat"
LANDSAT_MARGIN_METERS = 1000      # extra space kept around the focus area
CRS_LANDSAT = "EPSG:32618"        # UTM zone 18N, in meters

GRID_CELL_METERS = 100            # size of each grid cell
GRID_MIN_PIXELS = 5               # a cell needs this many clear land pixels
MODEL_FEATURES = ["ndvi", "ndbi", "brightness", "ndvi_nearby", "ndbi_nearby",
                  "brightness_nearby", "coast_distance_m"]
MODEL_BLOCK_METERS = 1000         # size of the blocks used for the spatial split
MODEL_TEST_SHARE = 0.25
MODEL_CV_FOLDS = 5                # spatial cross-validation folds
MODEL_SEED = 0
MODEL_TREES = 300

SURFACE_TEMP_WARNING = (
    "This layer shows land surface temperature from a satellite on one day "
    "(July 20, 2022, about 11:40 am). It is how hot roofs, streets, and "
    "ground were, not the air temperature people feel. Shade, wind, and "
    "humidity are not included."
)

# ---------------------------------------------------------------------------
# Wording that must appear in the app
# ---------------------------------------------------------------------------
SIMULATION_WARNING = (
    "SIMULATION. The cooling center you add here is hypothetical. It is not a "
    "real site and not a prediction that a center will open or that people "
    "would use it. It only shows how the access numbers would change."
)

COOLING_DATA_WARNING = (
    "Cooling center locations shown here are historical data. Cooling centers "
    "change every summer and only open during heat emergencies. For current "
    "locations use the official NYC Cool Options finder at "
    "https://finder.nyc.gov/coolingcenters/ or call 311. "
    "In an emergency, call 911."
)
