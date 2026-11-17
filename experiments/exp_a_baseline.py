"""Experiment A: does the Gap Score find areas that single measures miss?

Run from the coolgap folder:
    python -m experiments.exp_a_baseline

Three ways to flag "high concern" neighborhoods are compared:
  1. HVI only     every neighborhood with the top HVI value of 5
  2. Access only  the same number of neighborhoods with the worst access
                  (the three access parts of the score, HVI left out)
  3. CAGS         the same number of neighborhoods with the highest Gap Score

The number flagged is set by how many neighborhoods have HVI 5, so all three
lists are the same length and the comparison is fair.
"""
import pandas as pd

from experiments import common
from src import config


def main() -> None:
    _, _, _, scores = common.load_inputs()
    w = config.CAGS_WEIGHTS
    access_weight = w["distance"] + w["nearby"] + w["per_capita"]

    t = scores.copy()
    # Access-only score: the three access parts, rescaled to 0 to 100.
    t["access_only"] = (t["points_distance"] + t["points_nearby"]
                        + t["points_per_capita"]) / access_weight

    hvi_flag = t["hvi"] == 5
    n = int(hvi_flag.sum())
    t["flag_hvi"] = hvi_flag
    t["flag_access"] = t["access_only"].rank(ascending=False, method="first") <= n
    t["flag_cags"] = t["cags"].rank(ascending=False, method="first") <= n

    t["rank_hvi"] = t["hvi"].rank(ascending=False, method="min").astype(int)
    t["rank_access"] = t["access_only"].rank(ascending=False, method="min").astype(int)

    cags_flagged = t[t["flag_cags"]]
    missed_by_hvi = cags_flagged[~cags_flagged["flag_hvi"]]
    missed_by_access = cags_flagged[~cags_flagged["flag_access"]]
    missed_by_both = cags_flagged[~cags_flagged["flag_hvi"] & ~cags_flagged["flag_access"]]
    hvi_not_cags = t[t["flag_hvi"] & ~t["flag_cags"]]
    access_not_cags = t[t["flag_access"] & ~t["flag_cags"]]

    corr = t[["hvi", "access_only", "cags"]].corr(method="spearman")

    table = t[["ntaname", "in_focus", "hvi", "access_only", "cags", "rank_hvi",
               "rank_access", "cags_rank", "flag_hvi", "flag_access", "flag_cags"]]
    common.save_table(table.round(2), "exp_a_rankings.csv")

    counts = pd.DataFrame([
        {"measure": "Neighborhoods flagged by each method", "count": n},
        {"measure": "Flagged by CAGS and by HVI only", "count": int((t["flag_cags"] & t["flag_hvi"]).sum())},
        {"measure": "Flagged by CAGS and by access only", "count": int((t["flag_cags"] & t["flag_access"]).sum())},
        {"measure": "Flagged by CAGS but missed by HVI only", "count": len(missed_by_hvi)},
        {"measure": "Flagged by CAGS but missed by access only", "count": len(missed_by_access)},
        {"measure": "Flagged by CAGS but missed by both", "count": len(missed_by_both)},
        {"measure": "Flagged by HVI only but not by CAGS", "count": len(hvi_not_cags)},
        {"measure": "Flagged by access only but not by CAGS", "count": len(access_not_cags)},
        {"measure": "Flagged by both HVI only and access only", "count": int((t["flag_hvi"] & t["flag_access"]).sum())},
    ])
    common.save_table(counts, "exp_a_counts.csv")

    # Chart: every neighborhood by access-only score (x) and HVI (y).
    fig, ax = common.new_chart(8.5, 5)
    rest = t[~t["flag_cags"]]
    ax.scatter(rest["access_only"], rest["hvi"], s=45, color=common.GRAY,
               edgecolor="white", linewidth=0.8, label="Not flagged by CAGS", zorder=2)
    ax.scatter(cags_flagged["access_only"], cags_flagged["hvi"], s=70, color=common.VIOLET,
               edgecolor="white", linewidth=0.8, label=f"Top {n} by CAGS", zorder=3)
    # Labels alternate above and below so neighbors do not overlap.
    for i, (_, r) in enumerate(missed_by_hvi.sort_values("access_only").iterrows()):
        above = i % 2 == 0
        ax.annotate(r["ntaname"], (r["access_only"], r["hvi"]),
                    xytext=(0, 9 if above else -15), textcoords="offset points",
                    ha="center", fontsize=8, color=common.INK)
    cutoff = t.loc[t["flag_access"], "access_only"].min()
    ax.axvline(cutoff, color=common.MUTED, linewidth=1, linestyle="--")
    ax.text(cutoff, 5.42, f"access-only top {n} starts here ",
            fontsize=8, color=common.MUTED, va="bottom", ha="right")
    ax.set_xlabel("Access-only score (0 = best access, 100 = worst)", color=common.INK)
    ax.set_ylabel("Heat Vulnerability Index (1 to 5)", color=common.INK)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylim(0.6, 5.7)
    ax.set_xlim(-4, 112)
    ax.set_title(f"Experiment A: which {config.BOROUGH} neighborhoods does each method flag?",
                 fontsize=11, color=common.INK, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    common.save_chart(fig, "exp_a_chart.png")

    lines = [
        "EXPERIMENT A: HVI only vs access only vs CAGS",
        f"Neighborhoods compared: {len(t)} ({config.BOROUGH}, residential)",
        f"Each method flags {n} neighborhoods (the number with HVI 5).",
        f"CAGS flagged but HVI-only missed: {len(missed_by_hvi)} "
        f"({', '.join(missed_by_hvi['ntaname']) or 'none'})",
        f"CAGS flagged but access-only missed: {len(missed_by_access)} "
        f"({', '.join(missed_by_access['ntaname']) or 'none'})",
        f"CAGS flagged but BOTH single measures missed: {len(missed_by_both)} "
        f"({', '.join(missed_by_both['ntaname']) or 'none'})",
        f"HVI-only flagged but CAGS did not: {len(hvi_not_cags)} "
        f"({', '.join(hvi_not_cags['ntaname']) or 'none'})",
        f"Access-only flagged but CAGS did not: {len(access_not_cags)} "
        f"({', '.join(access_not_cags['ntaname']) or 'none'})",
        f"Flagged by both HVI-only and access-only: "
        f"{int((t['flag_hvi'] & t['flag_access']).sum())}",
        f"Rank correlation (Spearman) HVI vs access-only: {corr.loc['hvi', 'access_only']:.2f}",
        f"Rank correlation (Spearman) CAGS vs HVI: {corr.loc['cags', 'hvi']:.2f}",
        f"Rank correlation (Spearman) CAGS vs access-only: {corr.loc['cags', 'access_only']:.2f}",
    ]
    common.save_summary(lines, "exp_a_summary.txt")


if __name__ == "__main__":
    main()
