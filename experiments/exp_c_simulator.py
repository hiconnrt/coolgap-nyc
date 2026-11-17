"""Experiment C: SIMULATION scenarios.

Run from the coolgap folder:
    python -m experiments.exp_c_simulator

Every scenario except the first is a SIMULATION. The added sites are not
real and are not predictions.

Scenarios (all sites are placed inside the focus area):
  0. Existing resources only
  1. Add 1 site at the population center of the focus neighborhood with the
     highest Gap Score
  2. Add 1 site at the best spot found by a search
  3. Add 2 sites, each at the best spot found by a search (one after another)
  4. Add 1 site at the population center of the focus neighborhood with the
     lowest Gap Score (a comparison: what if the site goes where the gap is
     smallest?)

"Best spot" search: every census tract center in the focus area is tried as
the location. The one that brings the most residents newly within walking
distance wins. Residents anywhere in the borough count, so a site near the
edge of the focus area can also reach people just outside it. This is a
simple greedy search, not a full optimization.
"""
import textwrap

import numpy as np
import pandas as pd

from experiments import common
from src import config, simulator


def population_center(tracts: pd.DataFrame, nta: str) -> tuple[float, float]:
    """Population-weighted average location of a neighborhood's tracts."""
    g = tracts[tracts["nta2020"] == nta]
    return (float(np.average(g["lat"], weights=g["population"])),
            float(np.average(g["lon"], weights=g["population"])))


def best_spot(areas, tracts, resources, scores, focus_tracts, already):
    """Try every focus tract center. Return the one reaching the most new residents."""
    best, best_people = None, -1
    for _, t in focus_tracts.iterrows():
        site = (float(t["lat"]), float(t["lon"]))
        people = simulator.simulate(areas, tracts, resources, already + [site],
                                    scores)["summary"]["people_newly_within_walk"]
        if people > best_people:
            best, best_people = site, people
    return best


def main() -> None:
    areas, tracts, resources, scores = common.load_inputs()
    focus_ntas = scores[scores["in_focus"]].sort_values("cags", ascending=False)
    focus_tracts = tracts[tracts["nta2020"].isin(focus_ntas["nta2020"])]
    focus_pop = focus_tracts["population"].sum()
    highest, lowest = focus_ntas.iloc[0], focus_ntas.iloc[-1]

    print("  searching for the best spots (this takes a minute) ...")
    spot_1 = best_spot(areas, tracts, resources, scores, focus_tracts, [])
    spot_2 = best_spot(areas, tracts, resources, scores, focus_tracts, [spot_1])

    scenarios = [
        ("0. Existing resources", []),
        (f"1. +1 site, center of {highest['ntaname']} (highest gap)",
         [population_center(tracts, highest["nta2020"])]),
        ("2. +1 site, best spot from search", [spot_1]),
        ("3. +2 sites, best spots from search", [spot_1, spot_2]),
        (f"4. +1 site, center of {lowest['ntaname']} (lowest gap)",
         [population_center(tracts, lowest["nta2020"])]),
    ]

    before = simulator.people_within_walk(tracts, resources)
    focus_before = before[before["nta2020"].isin(focus_ntas["nta2020"])]
    focus_reached_before = focus_before.loc[focus_before["within_walk"], "population"].sum()

    rows = []
    for name, sites in scenarios:
        result = simulator.simulate(areas, tracts, resources, sites, scores)
        s = result["summary"]
        new = result["new_scores"]
        after = simulator.people_within_walk(tracts, result["new_resources"])
        focus_after = after[after["nta2020"].isin(focus_ntas["nta2020"])]
        focus_scores = new[new["nta2020"].isin(focus_ntas["nta2020"])]
        rows.append({
            "scenario": name,
            "simulated": bool(sites),
            "sites": "; ".join(f"{lat:.5f}, {lon:.5f}" for lat, lon in sites),
            "sites_in": "; ".join(
                str(n) for n in result["new_resources"].tail(len(sites))["ntaname"]) if sites else "",
            "residents_newly_within_walk": s["people_newly_within_walk"],
            "focus_residents_newly_within_walk": int(
                focus_after.loc[focus_after["within_walk"], "population"].sum()
                - focus_reached_before),
            "residents_65_newly_within_walk": s["people_65_newly_within_walk"],
            "pct_focus_within_walk": 100 * focus_after.loc[
                focus_after["within_walk"], "population"].sum() / focus_pop,
            "pct_borough_within_walk": s["pct_within_walk_after"],
            "average_focus_cags": float(focus_scores["cags"].mean()),
            "highest_focus_cags": float(focus_scores["cags"].max()),
        })
    table = pd.DataFrame(rows)
    common.save_table(table.round(2), "exp_c_scenarios.csv")

    fig, ax = common.new_chart(9, 4.2)
    labels = [textwrap.fill(r["scenario"], 34) for r in rows][::-1]
    values = [r["pct_focus_within_walk"] for r in rows][::-1]
    colors = [common.ORANGE if r["simulated"] else common.GRAY for r in rows][::-1]
    ax.barh(labels, values, color=colors, height=0.6)
    for y, v in enumerate(values):
        ax.text(v + 0.6, y, f"{v:.1f}%", va="center", fontsize=9, color=common.INK)
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"{config.FOCUS_NAME} residents within {config.WALK_DISTANCE_MILES} "
                  "miles of a resource (%)", color=common.INK)
    fig.suptitle("Experiment C: SIMULATION scenarios (orange bars are simulated, not real)",
                 fontsize=11, color=common.INK, x=0.02, ha="left")
    ax.tick_params(axis="y", labelsize=8, colors=common.INK)
    common.save_chart(fig, "exp_c_chart.png")

    lines = ["EXPERIMENT C: SIMULATION scenarios",
             "Scenarios 1 to 4 are SIMULATIONS. The added sites are not real.",
             f"Focus area: {config.FOCUS_NAME}, {int(focus_pop):,} residents."]
    for r in rows:
        lines.append(
            f"{r['scenario']}: {r['pct_focus_within_walk']:.1f}% of focus residents within "
            f"{config.WALK_DISTANCE_MILES} miles, {r['residents_newly_within_walk']:,} "
            f"{config.BOROUGH} residents newly reached, of whom "
            f"{r['focus_residents_newly_within_walk']:,} live in the focus area "
            f"({r['residents_65_newly_within_walk']:,} aged 65+ newly reached when "
            f"older adult sites are counted), average focus CAGS {r['average_focus_cags']:.1f}"
            + (f", site in {r['sites_in']}" if r["sites_in"] else ""))
    common.save_summary(lines, "exp_c_summary.txt")


if __name__ == "__main__":
    main()
