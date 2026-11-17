"""The Cooling Access Gap Score (CAGS).

Run from the coolgap folder:
    python -m src.gap_score

IMPORTANT: CAGS is this project's own research score. It is not an official
government or medical measure.

The idea: a neighborhood has a "cooling gap" when it is vulnerable to heat
AND it is hard to reach a cooling resource there.

Steps:
  1. Turn each of four numbers into a 0 to 1 "part", where 1 is always the
     worse direction:
       hvi         (HVI - 1) / 4, so HVI 1 becomes 0 and HVI 5 becomes 1
       distance    farther from the nearest resource = closer to 1
       nearby      fewer resources within walking distance = closer to 1
       per_capita  fewer resources per 10,000 residents = closer to 1
     The last three use min-max scaling across all neighborhoods in the
     borough: (value - smallest) / (largest - smallest).
  2. Multiply each part by its weight from config.CAGS_WEIGHTS and add up.
  3. Multiply by 100, so the score runs from 0 to 100.

Higher score = higher vulnerability and poorer access.
"""
import geopandas as gpd
import pandas as pd

from src import access, config

PARTS = ["hvi", "distance", "nearby", "per_capita"]

PART_LABELS = {
    "hvi": "Heat vulnerability (HVI)",
    "distance": "Distance to nearest resource",
    "nearby": "Few resources within walking distance",
    "per_capita": "Few resources per 10,000 residents",
}


def min_max(values: pd.Series, reference: pd.Series | None = None) -> pd.Series:
    """Rescale a column so the smallest value is 0 and the largest is 1.

    `reference` is the column that sets "smallest" and "largest". The
    simulator passes in today's real values, so that adding a pretend site
    does not quietly change the scale every other neighborhood is judged on.
    Results are kept between 0 and 1.
    """
    reference = values if reference is None else reference
    spread = reference.max() - reference.min()
    if spread == 0:
        return pd.Series(0.0, index=values.index)
    return ((values - reference.min()) / spread).clip(0, 1)


def add_parts(table: pd.DataFrame, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add the four 0 to 1 parts. For every part, 1 is the worse direction."""
    ref = table if reference is None else reference
    out = table.copy()
    out["part_hvi"] = (out["hvi"] - 1) / 4
    out["part_distance"] = min_max(out["nearest_miles"], ref["nearest_miles"])
    out["part_nearby"] = 1 - min_max(out["resources_nearby"], ref["resources_nearby"])
    out["part_per_capita"] = 1 - min_max(out["resources_per_10k"], ref["resources_per_10k"])
    return out


def add_score(table: pd.DataFrame, weights: dict | None = None,
              reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add the CAGS column (0 to 100) and the points each part contributes."""
    weights = weights or config.CAGS_WEIGHTS
    if abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("CAGS weights must add up to 1")

    out = add_parts(table, reference)
    out["cags"] = 0.0
    for part in PARTS:
        out[f"points_{part}"] = 100 * weights[part] * out[f"part_{part}"]
        out["cags"] += out[f"points_{part}"]
    out["cags_rank"] = out["cags"].rank(ascending=False, method="min").astype(int)
    return out


def build_scores(areas: pd.DataFrame, access_table: pd.DataFrame,
                 weights: dict | None = None,
                 reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join the neighborhood table to its access numbers and score it."""
    table = areas.merge(access_table, on="nta2020", how="left")
    return add_score(table, weights, reference).sort_values("cags", ascending=False)


def main() -> None:
    areas = gpd.read_file(config.PROCESSED_DIR / "nta_areas.geojson")
    access_table = access.area_access(access.load_tracts(), access.load_resources())
    scores = build_scores(areas.drop(columns="geometry"), access_table)
    scores.to_csv(config.PROCESSED_DIR / "cags_by_nta.csv", index=False)

    print(f"Saved scores for {len(scores)} neighborhoods. Top 10:")
    show = ["cags_rank", "ntaname", "cags", "hvi", "nearest_miles",
            "resources_nearby", "resources_per_10k", "in_focus"]
    print(scores[show].head(10).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
