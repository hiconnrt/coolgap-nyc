"""Experiment B: how good and how stable are the K-means groups?

Run from the coolgap folder:
    python -m experiments.exp_b_clusters

For k = 2 to 8 groups and 10 random seeds each, this measures:
  - silhouette score (-1 to 1, higher = groups are more separate)
  - agreement with the first seed (adjusted Rand index, 1 = identical grouping)
"""
from experiments import common
from src import clusters, config


def main() -> None:
    _, _, _, scores = common.load_inputs()

    runs = clusters.evaluate_k(scores)
    summary = clusters.summarize_k(runs)
    common.save_table(runs.round(4), "exp_b_all_runs.csv")
    common.save_table(summary.round(4), "exp_b_by_k.csv")

    _, groups = clusters.build_clusters(scores)
    common.save_table(groups.round(3), "exp_b_groups_at_chosen_k.csv")

    fig, ax = common.new_chart(8, 4.5)
    ax.fill_between(summary["k"], summary["silhouette_min"], summary["silhouette_max"],
                    color=common.BLUE, alpha=0.18, linewidth=0,
                    label="Lowest to highest across 10 seeds")
    ax.plot(summary["k"], summary["silhouette_mean"], color=common.BLUE, linewidth=2,
            marker="o", markersize=7, markeredgecolor="white", label="Average silhouette")
    for _, r in summary.iterrows():
        ax.annotate(f"{r['silhouette_mean']:.2f}", (r["k"], r["silhouette_mean"]),
                    xytext=(0, 9), textcoords="offset points", ha="center",
                    fontsize=8, color=common.INK)
    chosen = summary[summary["k"] == config.CLUSTER_K].iloc[0]
    ax.annotate(f"k = {config.CLUSTER_K} used in the app",
                (chosen["k"], chosen["silhouette_mean"]), xytext=(-30, -48),
                textcoords="offset points", fontsize=9, color=common.INK,
                arrowprops={"arrowstyle": "-", "color": common.MUTED})
    ax.set_xlabel("Number of groups (k)", color=common.INK)
    ax.set_ylabel("Silhouette score", color=common.INK)
    ax.set_ylim(0, 0.45)
    ax.set_title("Experiment B: clustering quality for each k",
                 fontsize=11, color=common.INK, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    common.save_chart(fig, "exp_b_silhouette.png")

    fig, ax = common.new_chart(8, 4)
    ax.bar(summary["k"], summary["agreement_mean"], color=common.BLUE, width=0.6)
    for _, r in summary.iterrows():
        ax.text(r["k"], r["agreement_mean"] + 0.02, f"{r['agreement_mean']:.2f}",
                ha="center", fontsize=8, color=common.INK)
    ax.set_xlabel("Number of groups (k)", color=common.INK)
    ax.set_ylabel("Agreement across seeds (1 = identical)", color=common.INK)
    ax.set_ylim(0, 1.12)
    ax.grid(axis="x", visible=False)
    ax.set_title("Experiment B: stability across 10 random seeds",
                 fontsize=11, color=common.INK, loc="left")
    common.save_chart(fig, "exp_b_stability.png")

    best = summary.loc[summary["silhouette_mean"].idxmax()]
    lines = [
        "EXPERIMENT B: clustering quality",
        f"Features: {', '.join(config.CLUSTER_FEATURES)} (standardized)",
        f"Neighborhoods: {len(scores)}. Seeds per k: {len(list(config.CLUSTER_SEEDS))}.",
    ] + [
        f"k={int(r['k'])}: silhouette {r['silhouette_mean']:.3f} "
        f"(range {r['silhouette_min']:.3f} to {r['silhouette_max']:.3f}), "
        f"agreement across seeds {r['agreement_mean']:.2f}, "
        f"smallest group {int(r['smallest_group'])}"
        for _, r in summary.iterrows()
    ] + [
        f"Highest average silhouette: k={int(best['k'])} ({best['silhouette_mean']:.3f})",
        f"k used in the app: {config.CLUSTER_K} "
        f"(silhouette {chosen['silhouette_mean']:.3f}, agreement {chosen['agreement_mean']:.2f})",
        "Groups at the chosen k:",
    ] + [
        f"  Group {int(g['cluster'])}: {g['cluster_name']} "
        f"({int(g['neighborhoods'])} neighborhoods, average CAGS {g['cags']:.1f})"
        for _, g in groups.iterrows()
    ]
    common.save_summary(lines, "exp_b_summary.txt")


if __name__ == "__main__":
    main()
