"""K-means clustering: group neighborhoods that look alike.

Run from the coolgap folder:
    python -m src.clusters

K-means is an unsupervised machine learning method. Nobody tells it the
right answer. It is given four numbers for each neighborhood and it sorts
the neighborhoods into k groups, so that members of a group are close to
each other on those four numbers.

Steps:
  1. Standardize the four numbers, so each has an average of 0 and a spread
     of 1. Without this, a number with a big range (like green space
     percent) would count more than a number with a small range (like miles).
  2. Try k = 2 to 8 groups. For each k, measure the silhouette score.
     It runs from -1 to 1. Higher means the groups are more separate.
  3. Repeat with 10 different random starting points to check the result
     is stable.
  4. Pick k (set in config.CLUSTER_K) using the silhouette score AND whether
     the groups make sense.
  5. Name each group from its actual averages. Names are made by a rule
     after the groups exist. They are not decided in advance.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from src import config

FEATURES = config.CLUSTER_FEATURES

FEATURE_LABELS = {
    "hvi": "Heat Vulnerability Index",
    "nearest_miles": "Distance to nearest resource (miles)",
    "resources_per_10k": "Resources per 10,000 residents",
    "greenspace_pct": "Green space (%)",
}

# Words used to build a group's name. (word if clearly above the borough
# average, word if clearly below). "Clearly" means more than half a standard
# deviation away. Features close to average are left out of the name.
NAME_WORDS = {
    "hvi": ("higher heat vulnerability", "lower heat vulnerability"),
    "nearest_miles": ("farther from cooling resources", "closer to cooling resources"),
    "resources_per_10k": ("more resources per person", "fewer resources per person"),
    "greenspace_pct": ("more green space", "less green space"),
}
CLEARLY = 0.5


def standardize(table: pd.DataFrame) -> np.ndarray:
    return StandardScaler().fit_transform(table[FEATURES])


def fit(table: pd.DataFrame, k: int, seed: int) -> np.ndarray:
    """Run K-means once and return the group number of each neighborhood."""
    model = KMeans(n_clusters=k, n_init=10, random_state=seed)
    return model.fit_predict(standardize(table))


def evaluate_k(table: pd.DataFrame) -> pd.DataFrame:
    """Silhouette score and stability for every k and every random seed."""
    x = standardize(table)
    rows = []
    for k in config.CLUSTER_K_RANGE:
        first = None
        for seed in config.CLUSTER_SEEDS:
            labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(x)
            first = labels if first is None else first
            rows.append({
                "k": k, "seed": seed,
                "silhouette": silhouette_score(x, labels),
                # 1.0 means exactly the same grouping as the first seed.
                "agreement_with_first_seed": adjusted_rand_score(first, labels),
                "smallest_group": int(np.bincount(labels).min()),
            })
    return pd.DataFrame(rows)


def summarize_k(runs: pd.DataFrame) -> pd.DataFrame:
    return (runs.groupby("k").agg(
        silhouette_mean=("silhouette", "mean"),
        silhouette_min=("silhouette", "min"),
        silhouette_max=("silhouette", "max"),
        agreement_mean=("agreement_with_first_seed", "mean"),
        smallest_group=("smallest_group", "min"),
    ).reset_index())


def name_groups(table: pd.DataFrame, labels: np.ndarray) -> dict:
    """Make a name for each group from how its averages compare to the borough."""
    z = pd.DataFrame(standardize(table), columns=FEATURES)
    z["group"] = labels
    names = {}
    for group, means in z.groupby("group")[FEATURES].mean().iterrows():
        words = []
        for feature in FEATURES:
            high_word, low_word = NAME_WORDS[feature]
            if means[feature] > CLEARLY:
                words.append(high_word)
            elif means[feature] < -CLEARLY:
                words.append(low_word)
        name = ", ".join(words) if words else "close to the borough average"
        names[group] = name[0].upper() + name[1:]
    return names


def build_clusters(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (group of each neighborhood, summary of each group)."""
    labels = fit(table, config.CLUSTER_K, config.CLUSTER_SEED)

    # Renumber the groups so group 1 has the highest average Gap Score.
    order = (table.assign(g=labels).groupby("g")["cags"].mean()
             .sort_values(ascending=False).index)
    renumber = {old: new for new, old in enumerate(order, start=1)}
    names = name_groups(table, labels)

    result = table[["nta2020"]].copy()
    result["cluster"] = [renumber[g] for g in labels]
    result["cluster_name"] = [names[g] for g in labels]

    joined = table.merge(result, on="nta2020")
    summary = (joined.groupby(["cluster", "cluster_name"])
               .agg(neighborhoods=("nta2020", "size"),
                    population=("population", "sum"),
                    **{f: (f, "mean") for f in FEATURES},
                    cags=("cags", "mean"))
               .reset_index())
    return result, summary


def main() -> None:
    table = pd.read_csv(config.PROCESSED_DIR / "cags_by_nta.csv")

    print("Silhouette score for each k (average over 10 random seeds):")
    print(summarize_k(evaluate_k(table)).round(3).to_string(index=False))

    result, summary = build_clusters(table)
    result.to_csv(config.PROCESSED_DIR / "clusters_by_nta.csv", index=False)
    summary.to_csv(config.PROCESSED_DIR / "cluster_summary.csv", index=False)
    print(f"\nUsing k = {config.CLUSTER_K}. Group summary:")
    print(summary.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
