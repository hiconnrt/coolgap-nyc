"""Helpers shared by the experiment scripts.

Every number in experiments/results/ comes from running these scripts on the
real data files. Run each one from the coolgap folder, for example:
    python -m experiments.exp_a_baseline
"""
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")  # draw charts to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

from src import access, config, gap_score

RESULTS = config.RESULTS_DIR
RESULTS.mkdir(parents=True, exist_ok=True)

INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
VIOLET = "#6250d6"
GRAY = "#c3c2b7"


def load_inputs():
    """Return (areas without access columns, tracts, resources, scored table)."""
    areas = gpd.read_file(config.PROCESSED_DIR / "nta_areas.geojson").drop(columns="geometry")
    tracts = access.load_tracts()
    resources = access.load_resources()
    scores = gap_score.build_scores(areas, access.area_access(tracts, resources))
    return areas, tracts, resources, scores


def new_chart(width: float = 8, height: float = 4.5):
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(GRAY)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="both", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    return fig, ax


def save_chart(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(RESULTS / name, facecolor="white")
    plt.close(fig)
    print(f"  saved {name}")


def save_table(table: pd.DataFrame, name: str) -> None:
    table.to_csv(RESULTS / name, index=False)
    print(f"  saved {name}")


def save_summary(lines: list[str], name: str) -> None:
    (RESULTS / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  saved {name}")
    print("\n".join(lines))
