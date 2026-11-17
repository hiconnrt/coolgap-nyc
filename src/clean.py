"""Step 2: clean the raw files and match everything to the same areas.

Run from the coolgap folder:
    python -m src.clean

What it makes (in data/processed/):
    nta_areas.geojson       one row per residential neighborhood (NTA) in the
                            borough, with its boundary, its HVI values, and
                            its population (total and age 65+)
    tracts.csv              one row per census tract in those neighborhoods,
                            with its center point and its population
    cooling_resources.csv   one row per cooling resource in the whole city,
                            with its type and the NTA it sits inside

The whole city is kept for cooling resources because a person near the
borough edge might walk to a site in the next borough.
"""
import geopandas as gpd
import pandas as pd

from src import config

RAW = config.RAW_DIR
OUT = config.PROCESSED_DIR


def load_nta_boundaries() -> gpd.GeoDataFrame:
    """All NTA shapes in the city, with clean column names."""
    nta = gpd.read_file(RAW / config.SOURCES["nta_boundaries"]["file"])
    nta = nta[["nta2020", "ntaname", "ntatype", "boroname", "cdta2020",
               "cdtaname", "geometry"]]
    return nta.to_crs(config.CRS_LATLON)


def load_hvi() -> pd.DataFrame:
    """Heat Vulnerability Index table, one row per NTA."""
    hvi = pd.read_csv(RAW / config.SOURCES["hvi"]["file"])

    # The source file lists one neighborhood twice (Kingsbridge-Marble Hill,
    # once under each borough code). The two rows have the same values, so
    # only the first is kept.
    hvi = hvi.drop_duplicates(subset="NTACode", keep="first")

    hvi = hvi.rename(columns={
        "NTACode": "nta2020",
        "HVI_RANK": "hvi",
        "SURFACE_TEMP": "surface_temp_f",
        "MEDIAN_INCOME": "median_income",
        "GREENSPACE": "greenspace_pct",
        "PCT_HOUSEHOLDS_AC": "pct_households_ac",
        "PCT_BLACK_POP": "pct_black_pop",
    })
    return hvi[["nta2020", "hvi", "surface_temp_f", "median_income",
                "greenspace_pct", "pct_households_ac", "pct_black_pop"]]


# In Census table B01001 (Sex by Age), these columns hold people aged 65 and
# over: columns 20 to 25 are men and 44 to 49 are women.
AGE_65_PLUS_COLUMNS = ([f"B01001_E{n:03d}" for n in range(20, 26)]
                       + [f"B01001_E{n:03d}" for n in range(44, 50)])


def load_tract_population() -> pd.DataFrame:
    """Total population and population 65+ for each census tract."""
    acs = pd.read_csv(RAW / config.SOURCES["acs_age"]["file"], sep="|")
    # GEO_ID looks like 1400000US36047000100. The last 11 digits are the tract.
    tracts = pd.DataFrame({
        "geoid": acs["GEO_ID"].str[-11:].astype("int64"),
        "population": acs["B01001_E001"],
        "pop_65_plus": acs[AGE_65_PLUS_COLUMNS].sum(axis=1),
    })

    lookup = pd.read_csv(RAW / config.SOURCES["tract_to_nta"]["file"])
    tracts = tracts.merge(
        lookup[["geoid", "ntacode"]], on="geoid", how="left")

    unmatched = tracts[tracts["ntacode"].isna()]
    if unmatched["population"].sum() > 0:
        raise RuntimeError(
            f"{len(unmatched)} tracts with people in them have no NTA match")
    return tracts.dropna(subset="ntacode").rename(columns={"ntacode": "nta2020"})


def load_population() -> pd.DataFrame:
    """Total population and population 65+, added up from tracts to NTAs."""
    tracts = load_tract_population().rename(columns={"nta2020": "ntacode"})
    by_nta = (tracts
              .groupby("ntacode")[["population", "pop_65_plus"]].sum()
              .reset_index().rename(columns={"ntacode": "nta2020"}))
    by_nta["pct_65_plus"] = (100 * by_nta["pop_65_plus"] / by_nta["population"]).round(1)
    return by_nta


def build_areas() -> gpd.GeoDataFrame:
    """Residential NTAs in the chosen borough, joined to their HVI values."""
    nta = load_nta_boundaries()
    areas = nta[(nta["boroname"] == config.BOROUGH)
                & (nta["ntatype"] == config.RESIDENTIAL_NTATYPE)].copy()

    areas = areas.merge(load_hvi(), on="nta2020", how="left")

    missing = areas[areas["hvi"].isna()]["ntaname"].tolist()
    if missing:
        raise RuntimeError(f"These areas have no HVI value: {missing}")

    areas = areas.merge(load_population(), on="nta2020", how="left")
    no_people = areas[areas["population"].isna()]["ntaname"].tolist()
    if no_people:
        raise RuntimeError(f"These areas have no population value: {no_people}")

    areas["in_focus"] = areas["cdta2020"].isin(config.FOCUS_CDTAS)
    return areas.sort_values("nta2020").reset_index(drop=True)


def build_tracts(areas: gpd.GeoDataFrame) -> pd.DataFrame:
    """One row per census tract: where its center is and who lives there.

    Tracts are much smaller than neighborhoods, so they show where people
    actually live inside a neighborhood. Only tracts inside the scored
    (residential) neighborhoods are kept.
    """
    shapes = gpd.read_file(RAW / config.SOURCES["tract_boundaries"]["file"])
    shapes["geoid"] = shapes["geoid"].astype("int64")

    # Measure in feet, find each tract's center, then turn it back into
    # latitude and longitude for mapping.
    feet = shapes.to_crs(config.CRS_FEET)
    centers = feet.geometry.representative_point()
    latlon = gpd.GeoSeries(centers, crs=config.CRS_FEET).to_crs(config.CRS_LATLON)

    tracts = pd.DataFrame({
        "geoid": shapes["geoid"],
        "x_feet": centers.x, "y_feet": centers.y,
        "lat": latlon.y, "lon": latlon.x,
    }).merge(load_tract_population(), on="geoid", how="inner")

    tracts = tracts[tracts["nta2020"].isin(areas["nta2020"])]
    return tracts.sort_values("geoid").reset_index(drop=True)


def flag_duplicate_libraries(resources: gpd.GeoDataFrame) -> pd.Series:
    """True for a library that is already in the cooling center list.

    Many cooling centers are library branches. The same building then shows
    up in both lists. A library within SAME_BUILDING_FEET of a library-run
    cooling center is marked as a duplicate so it is counted only once.
    """
    feet = resources.to_crs(config.CRS_FEET)
    libraries = feet[feet["resource_type"] == "library"]
    library_centers = feet[(feet["resource_type"] == "cooling_center")
                           & feet["operator"].isin(["BPL", "NYPL", "QPL"])]
    nearest = gpd.sjoin_nearest(libraries[["geometry"]], library_centers[["geometry"]],
                                distance_col="feet_apart", how="left")
    nearest = nearest[~nearest.index.duplicated()]  # one answer per library
    is_duplicate = pd.Series(False, index=resources.index)
    is_duplicate.loc[nearest.index] = nearest["feet_apart"] <= config.SAME_BUILDING_FEET
    return is_duplicate


def build_cooling_resources(nta: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Stack the three kinds of cooling resource into one table of points."""
    # 1. Cooling centers from NYC Emergency Management
    cc = gpd.read_file(RAW / config.SOURCES["cooling_centers"]["file"])
    name = cc["Facility_name"].str.strip()
    centers = gpd.GeoDataFrame({
        "resource_type": "cooling_center",
        "name": name,
        "address": cc["Address"].str.strip(),
        "operator": cc["Operating_agency"].str.strip().str.upper(),
        # Some sites only serve older adults. The source marks this in the name.
        "older_adults_only": name.str.upper().str.contains("OLDER ADULTS ONLY"),
        "source_id": cc["NYCEM_ID"],
    }, geometry=cc.geometry, crs=cc.crs)

    # 2. Public libraries from the NYC Planning Facilities Database
    lib = pd.read_csv(RAW / config.SOURCES["libraries"]["file"])
    libraries = gpd.GeoDataFrame({
        "resource_type": "library",
        "name": lib["facname"].str.strip(),
        "address": lib["address"].str.strip(),
        "operator": lib["opname"].str.strip(),
        "older_adults_only": False,
        "source_id": lib["uid"].astype(str),
    }, geometry=gpd.points_from_xy(lib["longitude"], lib["latitude"]),
        crs=config.CRS_LATLON)

    # 3. Spray showers from NYC Parks (outdoor, summer only)
    sp = gpd.read_file(RAW / config.SOURCES["spray_showers"]["file"])
    site = sp["sitename"].fillna(sp["propname"])
    sprays = gpd.GeoDataFrame({
        "resource_type": "spray_shower",
        "name": site.str.strip(),
        "address": pd.NA,
        "operator": "NYC Parks",
        "older_adults_only": False,
        "source_id": sp["propid"].astype(str),
    }, geometry=sp.geometry, crs=sp.crs)

    resources = pd.concat([centers, libraries.to_crs(centers.crs),
                           sprays.to_crs(centers.crs)], ignore_index=True)
    resources = gpd.GeoDataFrame(resources, geometry="geometry", crs=centers.crs)

    # Find which NTA each point sits inside.
    resources = gpd.sjoin(resources, nta[["nta2020", "ntaname", "boroname", "geometry"]],
                          how="left", predicate="within").drop(columns="index_right")
    resources["duplicate_of_cooling_center"] = flag_duplicate_libraries(resources)
    feet = resources.to_crs(config.CRS_FEET)
    resources["x_feet"] = feet.geometry.x
    resources["y_feet"] = feet.geometry.y
    resources["lat"] = resources.geometry.y
    resources["lon"] = resources.geometry.x
    return resources


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    areas = build_areas()
    areas.to_file(OUT / "nta_areas.geojson", driver="GeoJSON")
    print(f"Saved {len(areas)} {config.BOROUGH} neighborhoods "
          f"({int(areas['in_focus'].sum())} in {config.FOCUS_NAME})")

    tracts = build_tracts(areas)
    tracts.to_csv(OUT / "tracts.csv", index=False)
    print(f"Saved {len(tracts)} census tracts with "
          f"{int(tracts['population'].sum()):,} residents")

    resources = build_cooling_resources(load_nta_boundaries())
    resources.drop(columns="geometry").to_csv(OUT / "cooling_resources.csv", index=False)
    print(f"Saved {len(resources)} cooling resources citywide:")
    print(resources["resource_type"].value_counts().to_string())
    print("Libraries already listed as cooling centers:",
          int(resources["duplicate_of_cooling_center"].sum()))
    print("Points that fall outside every NTA:", int(resources["nta2020"].isna().sum()))


if __name__ == "__main__":
    main()
