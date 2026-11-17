# CoolGap Demo Video Script (under 4 minutes)

**Timing:** the spoken words below are about 520 words. At a normal pace
(about 140 words a minute) that is roughly 3 minutes 45 seconds, which
leaves a little room for clicks and page loads. Time yourself once before
recording and trim if you run over.

**Before recording**

- Open the app and click through every page once so the maps load fast.
- On the Simulator page, click "Remove all simulated sites" so it starts clean.
- Use a large browser zoom so the numbers are readable.
- The two simulator buttons load saved locations from Experiment C, so the
  numbers on screen should match this script (0 and 18,400). If they do not,
  the data or settings changed: rerun `python -m experiments.exp_c_simulator`
  and update the script. Always say the number that is on the screen.
- Check the challenge rules for video length and format: `[CHECK CHALLENGE VIDEO RULES]`

---

## 0:00 to 0:25 | The problem

**On screen:** Me on camera, or a title slide.

**Say:**
"Hi, I'm `[TEAM LEADER NAME]`, a student at `[SCHOOL NAME]` in Brooklyn. `[ONE SENTENCE ABOUT WHY I CARE, IN MY OWN WORDS.]` New York City measures which neighborhoods are most vulnerable to heat, and it also opens cooling centers. But those are usually looked at separately. My question: can combining them show gaps that one alone would miss?"

---

## 0:25 to 0:45 | The data

**On screen:** Methods and Limitations page, the Data sources table.

**Say:**
"I used only real public data: the city's Heat Vulnerability Index, cooling centers, libraries, and Census population. One early finding: 94 of Brooklyn's 140 cooling centers are for older adults only. For everyone else, the indoor options are mostly libraries."

---

## 0:45 to 1:15 | The map and the score

**On screen:** Heat Gap Map. Click Coney Island-Sea Gate. Scroll to the explanation and bar chart.

**Say:**
"This is CoolGap. Each neighborhood is colored by a score I designed, the Cooling Access Gap Score. It combines heat vulnerability with how far residents are from a cooling resource. It is my own research score, not an official measure.

Coney Island-Sea Gate ranks 2 out of 53. The explanation is built only from numbers on the screen, so it cannot make things up. I also used K-means clustering, a machine learning method, to group similar neighborhoods."

---

## 1:15 to 2:35 | The simulator (the main part)

**On screen:** Simulator page. Keep the red SIMULATION box visible.

**Say:**
"This is the simulator, and it is the heart of the project. Everything here is hypothetical. It is not a prediction that a center will open.

Here is the obvious idea. Coney Island-Sea Gate has the highest gap in southern Brooklyn, so let's put a new cooling center right in the middle of it."

**Do:** Click **"Example 1: center of the highest-gap neighborhood"**. Point at the black star, then at "Residents newly within 0.5 miles".

**Say:**
"Zero. Not one new resident is within walking distance. Why? Look at the green dot next to it. That is the library. This spot was already covered."

**Do:** Click **"Example 2: best spot found by the search"**. Point at the orange dots, then at the numbers.

*On screen the big number says 20,668. That counts all of Brooklyn. The sentence under it says 18,400 live in Southern Brooklyn. Point at that sentence.*

**Say:**
"Now a different spot. My code tried the center of every census tract in southern Brooklyn and kept the one that reached the most new people. It is not in Coney Island at all. It is here, in Gravesend. The orange dots are blocks that are newly within half a mile. That is 18,400 more residents of southern Brooklyn, with one site.

Zero compared to 18,400. The neighborhood with the worst score is not always the best place to build. You have to look at where people actually live and what is already nearby."

---

## 2:35 to 2:55 | Block-level heat (20 seconds)

**On screen:** Block-Level Heat page, "Measured by satellite", then switch to "Predicted by the model".

**Say:**
"City heat data stops at the neighborhood level, so I went smaller. Using a satellite image from a 95 degree day, I trained a Random Forest model to predict surface temperature for 100 meter blocks. Tested on areas it had never seen, it was off by about 2 degrees on average. This is surface heat, not what people feel."

---

## 2:55 to 3:25 | Results

**On screen:** Experiment A chart (`exp_a_chart.png`), then Experiment C chart (`exp_c_chart.png`).

**Say:**
"I ran five experiments. The honest result of the first one: my score does not find areas that both measures miss. But heat vulnerability and access mostly disagree with each other, and the score combines them into one ranking. It flagged 3 neighborhoods that heat vulnerability alone missed.

I also changed the weights a thousand times. Coney Island-Sea Gate stayed in the top ten 96 percent of the time."

---

## 3:25 to 3:55 | Limits and close

**On screen:** Methods and Limitations page, Safety section. End on the Heat Gap Map.

**Say:**
"CoolGap has limits. Distances are straight lines, the cooling center data is from last summer, and it has no opening hours. The app collects no personal data, points people to the official NYC finder, and says to call 911 in an emergency.

A tool like this could help a community group decide where to focus before a heat wave. Next, I want to `[MY NEXT STEP]`. Thank you."

---

## Shot checklist

- [ ] Title or intro
- [ ] Data sources table
- [ ] Heat Gap Map with Coney Island-Sea Gate clicked
- [ ] Written explanation and bar chart
- [ ] Simulator with the red SIMULATION warning visible
- [ ] Example 1 button: 0 residents newly within walking distance
- [ ] Example 2 button: orange dots and 18,400 southern Brooklyn residents
- [ ] Block-Level Heat: measured, then predicted
- [ ] Experiment A chart
- [ ] Experiment C chart
- [ ] Safety section

## Numbers used in this script and where they come from

| Number | Source file |
|---|---|
| 94 of 140 cooling centers for older adults only | `data/processed/cooling_resources.csv` |
| Rank 2 of 53 | `data/processed/cags_by_nta.csv` |
| 0 and 18,400 residents | `experiments/results/exp_c_scenarios.csv` |
| 95 degree day, about 2 degrees average error | `data/SOURCES.md`, `experiments/results/exp_e_metrics.csv` |
| 3 neighborhoods, rank correlation 0.23 | `experiments/results/exp_a_summary.txt` |
| 96 percent | `experiments/results/exp_d_summary.txt` |
