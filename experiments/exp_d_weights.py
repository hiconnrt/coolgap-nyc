"""Experiment D: how much does the top 10 depend on the weights?

Run from the coolgap folder:
    python -m experiments.exp_d_weights

The CAGS weights are a judgment call. This experiment changes them and
checks how many of the top 10 neighborhoods stay in the top 10.

Two tests:
  1. Named weight sets (equal weights, more HVI, less HVI, drop one part).
  2. 1,000 random weight sets, to see the full range of what could happen.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments import common
from src import config, gap_score

TOP_N = 10
RANDOM_SETS = 1000
RANDOM_SEED = 0


def rescale(weights: dict) -> dict:
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def named_weight_sets() -> dict:
    base = config.CAGS_WEIGHTS
    sets = {
        "Baseline (used in the app)": base,
        "Equal weights": {p: 0.25 for p in gap_score.PARTS},
        "More HVI (0.60)": rescale({**{p: base[p] * 0.4 / 0.6 for p in gap_score.PARTS}, "hvi": 0.60}),
        "Less HVI (0.20)": rescale({**{p: base[p] * 0.8 / 0.6 for p in gap_score.PARTS}, "hvi": 0.20}),
    }
    for part in gap_score.PARTS:
        sets[f"Drop {gap_score.PART_LABELS[part].lower()}"] = rescale(
            {p: (0 if p == part else base[p]) for p in gap_score.PARTS})
    return sets


def main() -> None:
    _, _, _, scores = common.load_inputs()
    base_top = set(scores.nlargest(TOP_N, "cags")["nta2020"])
    base_scores = scores.set_index("nta2020")["cags"]

    def compare(weights: dict) -> tuple[int, float, set]:
        new = gap_score.add_score(scores, weights)
        top = set(new.nlargest(TOP_N, "cags")["nta2020"])
        rho = spearmanr(base_scores, new.set_index("nta2020")["cags"].loc[base_scores.index])[0]
        return len(top & base_top), float(rho), top

    rows = []
    for name, weights in named_weight_sets().items():
        overlap, rho, _ = compare(weights)
        rows.append({"weight_set": name, **{f"w_{p}": round(weights[p], 3) for p in gap_score.PARTS},
                     "top10_same_as_baseline": overlap, "rank_correlation": round(rho, 3)})
    named = pd.DataFrame(rows)
    common.save_table(named, "exp_d_named_weights.csv")

    rng = np.random.default_rng(RANDOM_SEED)
    draws = rng.dirichlet(np.ones(len(gap_score.PARTS)), size=RANDOM_SETS)
    overlaps, appearances = [], pd.Series(0, index=scores["nta2020"])
    for draw in draws:
        overlap, _, top = compare(dict(zip(gap_score.PARTS, draw)))
        overlaps.append(overlap)
        appearances.loc[list(top)] += 1
    overlaps = np.array(overlaps)

    freq = (scores[["nta2020", "ntaname", "in_focus", "cags_rank", "hvi"]]
            .assign(pct_of_random_sets_in_top10=lambda d:
                    100 * d["nta2020"].map(appearances) / RANDOM_SETS)
            .sort_values("pct_of_random_sets_in_top10", ascending=False))
    common.save_table(freq.round(1), "exp_d_top10_frequency.csv")
    dist = (pd.Series(overlaps).value_counts().sort_index()
            .rename_axis("top10_same_as_baseline").reset_index(name="random_weight_sets"))
    common.save_table(dist, "exp_d_random_overlap.csv")

    fig, ax = common.new_chart(9, 4.4)
    shown = named.iloc[::-1]
    ax.barh(shown["weight_set"], shown["top10_same_as_baseline"], color=common.BLUE, height=0.6)
    for y, v in enumerate(shown["top10_same_as_baseline"]):
        ax.text(v + 0.12, y, f"{v} of {TOP_N}", va="center", fontsize=9, color=common.INK)
    ax.set_xlim(0, TOP_N + 1.2)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8, colors=common.INK)
    ax.set_xlabel(f"Neighborhoods still in the top {TOP_N}", color=common.INK)
    ax.set_title("Experiment D: top 10 under different weights",
                 fontsize=11, color=common.INK, loc="left")
    common.save_chart(fig, "exp_d_named_chart.png")

    fig, ax = common.new_chart(9, 5.5)
    head = freq.head(18).iloc[::-1]
    colors = [common.VIOLET if rank <= TOP_N else common.GRAY for rank in head["cags_rank"]]
    ax.barh(head["ntaname"], head["pct_of_random_sets_in_top10"], color=colors, height=0.65)
    for y, v in enumerate(head["pct_of_random_sets_in_top10"]):
        ax.text(v + 1, y, f"{v:.0f}%", va="center", fontsize=8, color=common.INK)
    ax.set_xlim(0, 110)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8, colors=common.INK)
    ax.set_xlabel(f"Share of {RANDOM_SETS:,} random weight sets where it is in the top {TOP_N} (%)",
                  color=common.INK)
    ax.set_title("Experiment D: purple = in the baseline top 10, gray = not",
                 fontsize=11, color=common.INK, loc="left")
    common.save_chart(fig, "exp_d_frequency_chart.png")

    always = freq[freq["pct_of_random_sets_in_top10"] >= 90]["ntaname"].tolist()
    lines = ["EXPERIMENT D: weight sensitivity",
             f"Baseline weights: {config.CAGS_WEIGHTS}"]
    lines += [f"{r['weight_set']}: {r['top10_same_as_baseline']} of {TOP_N} stay in the top "
              f"{TOP_N}, rank correlation with baseline {r['rank_correlation']:.2f}"
              for _, r in named.iterrows()]
    lines += [
        f"Random weights ({RANDOM_SETS} sets, seed {RANDOM_SEED}): on average "
        f"{overlaps.mean():.1f} of {TOP_N} stay in the top {TOP_N} "
        f"(lowest {overlaps.min()}, highest {overlaps.max()}).",
        f"In the top {TOP_N} for at least 90% of random weight sets: "
        f"{', '.join(always) or 'none'}",
    ]
    for _, r in freq[freq["in_focus"]].iterrows():
        lines.append(f"Focus area {r['ntaname']} (baseline rank {int(r['cags_rank'])}): in the "
                     f"top {TOP_N} for {r['pct_of_random_sets_in_top10']:.0f}% of random weight sets")
    common.save_summary(lines, "exp_d_summary.txt")


if __name__ == "__main__":
    main()
