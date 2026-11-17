"""Cooling access: how close are people to cooling resources?

Run from the coolgap folder:
    python -m src.access

How it works, in plain words:
  1. Take the center of every census tract (a small area of a few blocks).
  2. Measure the straight-line distance from that center to every cooling
     resource, and note the nearest one and how many are within walking
     distance.
  3. Combine the tracts in each neighborhood, giving more weight to tracts
     where more people live. This is a population-weighted average.

Two versions are calculated:
  - "everyone": cooling centers open to all, plus libraries
  - "65+": the same, plus cooling centers marked OLDER ADULTS ONLY,
    weighted by where people aged 65 and over live

Distances are straight lines, not real walking routes. Real walks are longer.
"""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from src import config

WALK_FEET = config.WALK_DISTANCE_MILES * config.FEET_PER_MILE


def load_tracts() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "tracts.csv")


def load_resources() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "cooling_resources.csv")


def counted_resources(resources: pd.DataFrame, include_older_adult_sites: bool) -> pd.DataFrame:
    """Pick the resources that count toward access.

    Leaves out spray showers and leaves out libraries that are already in
    the cooling center list. Older-adult-only sites are left out unless asked for.
    """
    keep = (resources["resource_type"].isin(config.COUNTED_RESOURCE_TYPES)
            & ~resources["duplicate_of_cooling_center"])
    if not include_older_adult_sites:
        keep &= ~resources["older_adults_only"]
    return resources[keep]


def tract_access(tracts: pd.DataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    """For each tract: distance to the nearest resource and count within walking distance."""
    tree = cKDTree(resources[["x_feet", "y_feet"]].to_numpy())
    points = tracts[["x_feet", "y_feet"]].to_numpy()

    nearest_feet, _ = tree.query(points, k=1)
    nearby = tree.query_ball_point(points, r=WALK_FEET)

    return pd.DataFrame({
        "geoid": tracts["geoid"].to_numpy(),
        "nearest_miles": nearest_feet / config.FEET_PER_MILE,
        "resources_nearby": [len(found) for found in nearby],
    })


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    if weights.sum() == 0:
        return float("nan")
    return float(np.average(values, weights=weights))


def area_access(tracts: pd.DataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    """Access numbers for each neighborhood (NTA).

    `resources` is the full resource table. Passing it in (instead of always
    reading the file) lets the simulator add a pretend site and recalculate.
    """
    everyone = counted_resources(resources, include_older_adult_sites=False)
    seniors = counted_resources(resources, include_older_adult_sites=True)

    t = tracts.merge(tract_access(tracts, everyone), on="geoid")
    t = t.merge(tract_access(tracts, seniors), on="geoid", suffixes=("", "_65"))
    t["within_walk"] = t["resources_nearby"] > 0
    t["within_walk_65"] = t["resources_nearby_65"] > 0

    rows = []
    for nta, g in t.groupby("nta2020"):
        people, older = g["population"], g["pop_65_plus"]
        rows.append({
            "nta2020": nta,
            # Everyone
            "nearest_miles": weighted_average(g["nearest_miles"], people),
            "resources_nearby": weighted_average(g["resources_nearby"], people),
            "pct_pop_within_walk": 100 * people[g["within_walk"]].sum() / people.sum(),
            # People aged 65 and over
            "nearest_miles_65": weighted_average(g["nearest_miles_65"], older),
            "resources_nearby_65": weighted_average(g["resources_nearby_65"], older),
            "pct_65_within_walk": 100 * older[g["within_walk_65"]].sum() / older.sum(),
        })
    areas = pd.DataFrame(rows)

    # Resources located inside each neighborhood, per 10,000 residents.
    population = tracts.groupby("nta2020")[["population", "pop_65_plus"]].sum()
    inside = everyone.groupby("nta2020").size().rename("resources_inside")
    inside_65 = seniors.groupby("nta2020").size().rename("resources_inside_65")
    areas = (areas.merge(population, on="nta2020")
             .merge(inside, on="nta2020", how="left")
             .merge(inside_65, on="nta2020", how="left"))
    areas[["resources_inside", "resources_inside_65"]] = (
        areas[["resources_inside", "resources_inside_65"]].fillna(0).astype(int))
    areas["resources_per_10k"] = 10000 * areas["resources_inside"] / areas["population"]
    areas["resources_per_10k_65"] = 10000 * areas["resources_inside_65"] / areas["pop_65_plus"]
    return areas.drop(columns=["population", "pop_65_plus"])


def main() -> None:
    access = area_access(load_tracts(), load_resources())
    access.to_csv(config.PROCESSED_DIR / "access_by_nta.csv", index=False)
    print(f"Saved access numbers for {len(access)} neighborhoods")
    print(access.describe().round(2).T[["min", "mean", "max"]].to_string())


if __name__ == "__main__":
    main()
