"""SIMULATION: what if a cooling center were added at a chosen spot?

Everything in this file is a what-if calculation. The added site is not
real. The result is not a prediction that a center will open there or that
people would use it. It only shows how the access numbers would change.

How it works:
  1. Copy the real resource table and add one or more pretend sites.
  2. Run the same access calculation used for the real data.
  3. Recalculate the Gap Score. The 0 to 1 scaling uses today's real
     smallest and largest values, so only the affected areas change.
  4. Compare before and after.
"""
import geopandas as gpd
import pandas as pd

from src import access, config, gap_score


def add_sites(resources: pd.DataFrame, sites: list[tuple[float, float]]) -> pd.DataFrame:
    """Return a copy of the resource table with pretend sites added.

    `sites` is a list of (latitude, longitude) pairs.
    """
    if not sites:
        return resources
    points = gpd.GeoSeries(
        gpd.points_from_xy([lon for _, lon in sites], [lat for lat, _ in sites]),
        crs=config.CRS_LATLON)

    # Find which neighborhood each new site falls in.
    areas = gpd.read_file(config.PROCESSED_DIR / "nta_areas.geojson")[
        ["nta2020", "ntaname", "boroname", "geometry"]]
    located = gpd.sjoin(gpd.GeoDataFrame(geometry=points), areas,
                        how="left", predicate="within")
    feet = points.to_crs(config.CRS_FEET)

    new_rows = pd.DataFrame({
        "resource_type": "cooling_center",
        "name": [f"SIMULATED site {i + 1}" for i in range(len(sites))],
        "address": "SIMULATION, not a real site",
        "operator": "SIMULATION",
        "older_adults_only": False,
        "source_id": [f"SIM{i + 1}" for i in range(len(sites))],
        "nta2020": located["nta2020"].to_numpy(),
        "ntaname": located["ntaname"].to_numpy(),
        "boroname": located["boroname"].to_numpy(),
        "duplicate_of_cooling_center": False,
        "x_feet": feet.x.to_numpy(), "y_feet": feet.y.to_numpy(),
        "lat": [lat for lat, _ in sites], "lon": [lon for _, lon in sites],
    })
    return pd.concat([resources, new_rows], ignore_index=True)


def people_within_walk(tracts: pd.DataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    """For each tract, is it within walking distance of a counted resource?"""
    everyone = access.counted_resources(resources, include_older_adult_sites=False)
    seniors = access.counted_resources(resources, include_older_adult_sites=True)
    out = tracts[["geoid", "nta2020", "population", "pop_65_plus"]].copy()
    out["within_walk"] = access.tract_access(tracts, everyone)["resources_nearby"].to_numpy() > 0
    out["within_walk_65"] = access.tract_access(tracts, seniors)["resources_nearby"].to_numpy() > 0
    return out


def simulate(areas: pd.DataFrame, tracts: pd.DataFrame, resources: pd.DataFrame,
             sites: list[tuple[float, float]], baseline: pd.DataFrame) -> dict:
    """Compare today's numbers to the numbers with pretend sites added.

    `areas` is the neighborhood table without access columns.
    `baseline` is today's scored table (from gap_score.build_scores).
    """
    new_resources = add_sites(resources, sites)
    new_scores = gap_score.build_scores(
        areas, access.area_access(tracts, new_resources), reference=baseline)

    before = people_within_walk(tracts, resources)
    after = people_within_walk(tracts, new_resources)
    newly = after["within_walk"] & ~before["within_walk"]
    newly_65 = after["within_walk_65"] & ~before["within_walk_65"]

    total, total_65 = tracts["population"].sum(), tracts["pop_65_plus"].sum()
    summary = {
        "sites_added": len(sites),
        "people_newly_within_walk": int(tracts.loc[newly.to_numpy(), "population"].sum()),
        "people_65_newly_within_walk": int(tracts.loc[newly_65.to_numpy(), "pop_65_plus"].sum()),
        "pct_within_walk_before": 100 * before.loc[before["within_walk"], "population"].sum() / total,
        "pct_within_walk_after": 100 * after.loc[after["within_walk"], "population"].sum() / total,
        "pct_65_within_walk_before": 100 * before.loc[before["within_walk_65"], "pop_65_plus"].sum() / total_65,
        "pct_65_within_walk_after": 100 * after.loc[after["within_walk_65"], "pop_65_plus"].sum() / total_65,
    }

    keep = ["nta2020", "ntaname", "cags", "cags_rank", "nearest_miles",
            "resources_nearby", "pct_pop_within_walk", "resources_per_10k"]
    change = baseline[keep].merge(new_scores[keep], on=["nta2020", "ntaname"],
                                  suffixes=("_before", "_after"))
    change["cags_change"] = change["cags_after"] - change["cags_before"]
    changed = change[change["cags_change"].abs() > 1e-9].sort_values("cags_change")

    return {"summary": summary, "changed_areas": changed,
            "new_scores": new_scores, "new_resources": new_resources,
            "newly_reached_tracts": tracts.loc[newly.to_numpy(),
                                                ["lat", "lon", "population", "nta2020"]]}
