"""Plain language explanations built only from the calculated numbers.

No AI model writes these. Each sentence is a fill-in-the-blank template, and
every blank is a number that is also shown in the app tables. That way every
sentence can be traced back to a number on screen.
"""
import pandas as pd

from src import config, gap_score


def score_sentence(row: pd.Series, total_areas: int) -> str:
    return (f"{row['ntaname']} has a Gap Score of {row['cags']:.1f} out of 100, "
            f"rank {int(row['cags_rank'])} of {total_areas} neighborhoods in "
            f"{config.BOROUGH}.")


def part_sentences(row: pd.Series) -> dict:
    """One sentence for each of the four parts of the score."""
    walk = config.WALK_DISTANCE_MILES
    return {
        "hvi": (f"Its Heat Vulnerability Index is {int(row['hvi'])} of 5, which "
                f"adds {row['points_hvi']:.1f} points."),
        "distance": (f"The average resident is {row['nearest_miles']:.2f} miles in "
                     f"a straight line from the nearest cooling resource open to "
                     f"everyone, which adds {row['points_distance']:.1f} points."),
        "nearby": (f"The average resident has {row['resources_nearby']:.1f} such "
                   f"resources within {walk} miles, and "
                   f"{row['pct_pop_within_walk']:.0f}% of residents have at least "
                   f"one, which adds {row['points_nearby']:.1f} points."),
        "per_capita": (f"It has {int(row['resources_inside'])} such "
                       f"{'resource' if int(row['resources_inside']) == 1 else 'resources'} inside "
                       f"its boundary for {int(row['population']):,} residents "
                       f"({row['resources_per_10k']:.2f} per 10,000), which adds "
                       f"{row['points_per_capita']:.1f} points."),
    }


def cluster_sentence(row: pd.Series) -> str:
    """Which K-means group the area is in. Empty if clusters are not loaded."""
    if "cluster_name" not in row or pd.isna(row["cluster_name"]):
        return ""
    return (f"K-means clustering put it in group {int(row['cluster'])}: "
            f"{row['cluster_name'].lower()} (compared with the "
            f"{config.BOROUGH} average).")


def explain_area(row: pd.Series, total_areas: int) -> str:
    """Short explanation: the score, then its parts from biggest to smallest."""
    sentences = part_sentences(row)
    order = sorted(gap_score.PARTS, key=lambda part: row[f"points_{part}"], reverse=True)
    older = (f"For residents aged 65 and over, counting sites for older adults, "
             f"{row['pct_65_within_walk']:.0f}% have a cooling resource within "
             f"{config.WALK_DISTANCE_MILES} miles.")
    parts = ([score_sentence(row, total_areas)]
             + [sentences[part] for part in order] + [older, cluster_sentence(row)])
    return " ".join(part for part in parts if part)
