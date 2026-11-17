# CoolGap: AI Mapping of Heat Risk and Cooling Access in Southern Brooklyn

**Proposal draft for the 2027 Presidential SI Challenge**

- Team leader: `[TEAM LEADER NAME]`
- School: `[SCHOOL NAME]`
- Grade: `[GRADE]`
- Teacher or mentor: `[MENTOR NAME, IF ANY]`
- App link: `[DEPLOYED APP LINK]`
- Video link: `[DEMO VIDEO LINK]`

> **How to use this draft.** This is an outline with real numbers already
> filled in where the experiments have been run. Every number below comes
> from a file in `experiments/results/` or `data/processed/`. Anything in
> `[BRACKETS]` is a placeholder that I still need to fill in myself. Parts
> marked "in my own words" should be rewritten so they sound like me.

---

## 1. The problem

*Goal of this section: say what the problem is and who it affects, in a few sentences.*

- Extreme heat is dangerous, especially for older adults and people without air conditioning at home.
  `[ADD ONE FACT ABOUT HEAT AND HEALTH IN NYC, WITH ITS SOURCE. Suggested place to look: the NYC Health Department's yearly heat-related mortality report.]`
- New York City measures heat risk with the Heat Vulnerability Index (HVI). It scores each neighborhood from 1 (lowest risk) to 5 (highest risk).
- The city also opens cooling centers during heat emergencies.
- These are usually looked at separately. A map of heat risk does not show if help is nearby. A list of cooling centers does not show who needs them most.
- **The gap:** a neighborhood can be very vulnerable to heat and also be far from a place to cool down. Looking at one dataset alone can hide that.

**Who it helps:** older adults and residents without air conditioning in southern Brooklyn (Coney Island, Brighton Beach, Gravesend, Bensonhurst, Bath Beach, Sheepshead Bay). Community organizations could use it to decide where to focus outreach.

**Why I care (in my own words):** `[WHY THIS PROBLEM MATTERS TO ME. For example, something I have seen in my own neighborhood during a heat wave.]`

**Research question:** Can an AI-assisted geospatial system find mismatches between heat vulnerability and cooling access better than looking at either dataset alone?

---

## 2. Research

*Goal: show what I learned before building, and where the data comes from.*

### What I found out about the data

- The city publishes the HVI by neighborhood (Neighborhood Tabulation Area). It is built from surface temperature, green space, home air conditioning, and income.
- The city does **not** publish a full open cooling center list on NYC Open Data. The best official source I found is a map layer from NYC Emergency Management with 476 sites citywide and 140 in Brooklyn.
- Of the 140 Brooklyn cooling centers, 94 are marked for older adults only. Another 40 are library branches.
- This means that for people under 65, the indoor cooling resources in the data are mostly libraries.

### Data sources (all real, all public)

| Data | Publisher |
|---|---|
| Heat Vulnerability Index by neighborhood | NYC Department of Health and Mental Hygiene |
| Cooling centers, summer 2026 | NYC Emergency Management |
| Neighborhood and census tract boundaries | NYC Department of City Planning |
| Population by age, 2020 to 2024 | US Census Bureau, American Community Survey |
| Public libraries | NYC Department of City Planning |
| Spray showers | NYC Parks |

Every link, download date, and column meaning is recorded in `data/SOURCES.md`.

### Other work on this topic

`[ADD 2 OR 3 SOURCES I READ, for example city reports on cooling center access. For each one: who wrote it, what they found, and how my project is different.]`

---

## 3. My solution

*Goal: explain what I built in plain words.*

CoolGap is a web app with five pages:

1. **Heat Gap Map.** Every Brooklyn neighborhood colored by its Cooling Access Gap Score. Click one to see why it scored that way.
2. **Neighborhood Explorer.** All the numbers for one neighborhood next to the Brooklyn middle value.
3. **Cooling Resource Finder.** The cooling resources in a neighborhood, with a warning that the data is historical.
4. **Simulator.** Click the map to add a hypothetical cooling center and see how access changes. Clearly labeled SIMULATION.
5. **Methods and Limitations.** The formula, the weights, the sources, and what the project cannot say.

### The Cooling Access Gap Score (CAGS)

This is my own score. It is not an official government or medical measure.

```
CAGS = 100 x ( 0.40 x HVI part + 0.25 x Distance part
             + 0.20 x Nearby part + 0.15 x Per person part )
```

- **HVI part:** the city's heat vulnerability score.
- **Distance part:** how far the average resident is from the nearest cooling resource open to everyone.
- **Nearby part:** how many resources are within half a mile.
- **Per person part:** resources per 10,000 residents.

Each part goes from 0 to 1, where 1 is worse. A higher score means higher vulnerability together with poorer access.

To measure distance fairly, I did not just use the middle of each neighborhood. I used the center of every census tract (a few blocks) and gave more weight to tracts where more people live.

---

## 4. The AI method

*Goal: explain the AI honestly, including what is and is not AI.*

| Part | Method | Is it AI? |
|---|---|---|
| Grouping neighborhoods | K-means clustering (scikit-learn) | Yes. Unsupervised machine learning |
| Gap Score | A weighted formula I designed | No. It is a formula, and I say so |
| Explanations | Fill-in-the-blank templates using the calculated numbers | No. No language model writes them |
| Simulator | Recalculates the same access numbers with one more site | No. It is a what-if calculation |
| Block-level heat model | Random Forest (scikit-learn) trained on Landsat satellite data | Yes. Supervised machine learning |

### K-means clustering

- K-means sorts neighborhoods into groups that look alike. Nobody tells it the right answer.
- I gave it four numbers per neighborhood: HVI, distance to the nearest resource, resources per 10,000 residents, and green space.
- I standardized the numbers first so no single one counts more just because its values are bigger.
- I tested 2 to 8 groups, with 10 random starting points each.
- I named the groups **after** seeing the results, using a rule based on each group's averages.

### The Random Forest heat model

- City heat data stops at the neighborhood level. I wanted to see differences inside a neighborhood.
- I used one Landsat 9 satellite scene from July 20, 2022, a clear day with a recorded high of 95 F.
- I cut southern Brooklyn into 2,926 grid cells of 100 meters.
- For each cell the model gets seven features: greenness (NDVI), a built-up index (NDBI), brightness, the same three for the cells around it, and distance to the coast.
- The target is the surface temperature the satellite measured.
- **Fair testing:** cells next to each other are very similar, so a random split would let the model cheat. I split by 1 km blocks instead, so the model is always tested on blocks it never saw (spatial cross-validation).

### How I used AI tools to build it

`[IN MY OWN WORDS: explain how I used an AI coding assistant to help write the code, what I checked myself, and what I can explain. The challenge rules may require this, so check them: [CHECK CHALLENGE RULES ON AI TOOL DISCLOSURE].]`

---

## 5. Results

*Goal: report what actually happened, including results that were not what I hoped for.*

All numbers below come from running the code on the real data. The files are in `experiments/results/`.

### The scores

- 53 residential Brooklyn neighborhoods were scored. 9 are in southern Brooklyn.
- **Coney Island-Sea Gate ranks 2 of 53** with a Gap Score of 85.5. It has an HVI of 5 and one cooling resource open to everyone for 54,465 residents.
- The other southern Brooklyn neighborhoods rank from 16 (Bensonhurst) to 49 (Sheepshead Bay-Manhattan Beach-Gerritsen Beach).
- 76.2% of southern Brooklyn residents live within half a mile (straight line) of a cooling resource open to everyone.

### Experiment A: Gap Score compared with single measures

Each method flags 11 neighborhoods.

- The Gap Score flagged **3** neighborhoods that HVI alone missed (Sunset Park (East)-Borough Park (West), East New York-City Line, Cypress Hills).
- It flagged **5** that access alone missed.
- It flagged **0** that both single measures missed.
- HVI and access mostly disagree with each other: only 3 neighborhoods are on both lists (rank correlation 0.23).

**Conclusion:** CAGS does not find areas that both measures miss, but it combines two lists that mostly disagree (rank correlation 0.23) into one ranking.

### Experiment B: clustering quality

- The best silhouette score was 0.319, at 2 groups. That grouping was the same for all 10 random starts.
- I used 3 groups (silhouette 0.246, agreement across random starts 0.71). With 2 groups, one group is simply worse on everything and the other is better on everything, which cannot show a mismatch. 3 is the smallest number that separates out neighborhoods with lower heat vulnerability but the poorest access.
- All the silhouette scores are low. This means Brooklyn neighborhoods do not fall into clean groups. They are more of a spread.

### Experiment C: simulator scenarios (SIMULATION)

| Scenario | Southern Brooklyn residents within 0.5 miles | Newly reached |
|---|---|---|
| Existing resources | 76.2% | 0 |
| Add 1 site at the population center of Coney Island-Sea Gate | 76.2% | 0 |
| Add 1 site at the best spot from a search | 80.4% | 18,400 |
| Add 2 sites at the best spots from a search | 82.3% | 27,125 |
| Add 1 site at the population center of the lowest-gap neighborhood | 77.0% | 3,212 |

**What surprised me:** putting a site in the middle of the highest-scoring neighborhood reached nobody new, because that spot is already close to an existing library. The exact location matters more than which neighborhood has the highest score.

### Experiment D: do the weights matter?

- With equal weights, or with the HVI weight changed to 0.60 or 0.20, 8 or 9 of the top 10 stayed the same.
- Across 1,000 random weight sets, 7.0 of the top 10 stayed on average (lowest 3, highest 10).
- Coney Island-Sea Gate stayed in the top 10 in 96% of the random weight sets, so its high rank does not depend on my weight choice.

### Experiment E: block-level heat model accuracy

- **Main result (spatial cross-validation): R squared 0.50, average error 1.9 F.**
- Just guessing the average temperature gives an average error of 2.7 F, so the model is better, but not by a huge amount.
- On training cells the model scores R squared 0.88. The big drop to 0.50 on unseen blocks shows it partly memorizes, which is why the spatial test matters.
- A random split (the unfair way) gives R squared 0.59. That is higher than the fair test, which shows the leak is real.
- One of the five test folds scored about zero (R squared -0.04), so the model does not work equally well everywhere.
- **Most important features:** distance to the coast, then brightness. Greenness mattered less than I expected.
- **Honest note:** my first version did not have the brightness features and scored R squared 0.34. I added brightness after seeing that weak result.
- **Limit:** this is surface temperature on one day, not the air temperature people feel.

### User testing

`[RESULT: number of testers]`, `[RESULT: average clarity rating]`, `[RESULT: how many understood the simulator is hypothetical]`, `[RESULT: most common comment]`. The form is in `experiments/user_feedback_form.md`. Fill these in only after real people try the app.

---

## 6. Safety, privacy, and responsible AI

- **No personal data.** The app does not ask for names, addresses, locations, or health information. The feedback form does not either.
- **Historical data warning.** Cooling center locations are from summer 2026. The app tells people to use the official NYC finder (https://finder.nyc.gov/coolingcenters/) or call 311.
- **Not for emergencies.** The app does not give emergency instructions. It says to call 911 in an emergency.
- **Not official.** The Gap Score is a research tool, not a government or medical measure.
- **Simulations are labeled.** Every simulated site says SIMULATION. It is not a prediction that a center will open or be used.
- **Explanations cannot make things up.** They are templates filled with calculated numbers, so every sentence traces back to a number on screen.
- **Fairness.** The city's HVI includes income and race data because heat risk is not spread equally. My project does not change the HVI. `[IN MY OWN WORDS: one or two sentences about why a score like this should help direct resources, not label neighborhoods.]`

### Limits I want judges to know

- Distances are straight lines. Real walks are longer.
- The data has no opening hours and no building sizes.
- The years do not match (HVI 2016 to 2020, population 2020 to 2024, resources 2026).
- The cooling center file has no stated license and was made for the city's own survey.
- Two parts of my score overlap, so distance is partly counted twice.
- The block-level layer is surface temperature, not air temperature, and the model explains only about half of the differences between cells.
- The project cannot say that any person is at risk or that adding a site would save lives.

---

## 7. What I learned

*In my own words. Some honest starting points from the project:*

- Real data is messy. `[EXAMPLE: the Census website asked for a key, one neighborhood was listed twice, and most cooling centers turned out to be for older adults only.]`
- A result I did not expect can be more interesting than the one I wanted. `[EXAMPLE: Experiment A and Experiment C.]`
- Being honest about limits makes a project stronger. `[MY THOUGHTS]`
- `[SOMETHING I LEARNED ABOUT CODING OR AI]`
- `[SOMETHING I WOULD DO DIFFERENTLY]`

---

## 8. Next steps

- **Improve the block-level heat model.** Add more hot days, real tree canopy data, and building heights, and compare with air temperature sensors.
- **Real walking routes** instead of straight lines.
- **Opening hours and capacity,** if the city shares them.
- **A score for older adults.** Right now the 65+ access numbers are shown but are not part of the score.
- **More boroughs.** The code can switch areas by changing one setting.
- **Talk to a community organization** in southern Brooklyn and ask if the map matches what they see. `[ORGANIZATION NAME, IF I CONTACT ONE]`
- **User testing** with classmates and adults.

---

## Sources

1. NYC Department of Health and Mental Hygiene. Heat Vulnerability Index. https://a816-dohbesp.nyc.gov/IndicatorPublic/data-features/hvi/
2. NYC Emergency Management. Indoor Cool Options map layer. https://www.arcgis.com/home/item.html?id=fb0cd480f900469e9f5ebeac3d6b06f0
3. NYC Department of City Planning. 2020 Neighborhood Tabulation Areas. https://data.cityofnewyork.us/d/9nt8-h7nd
4. NYC Department of City Planning. 2020 Census Tracts. https://data.cityofnewyork.us/d/63ge-mke6
5. US Census Bureau. American Community Survey 5-year estimates, 2020 to 2024, table B01001.
6. NYC Department of City Planning. Facilities Database. https://data.cityofnewyork.us/d/ji82-xba5
7. NYC Parks. Spray Showers. https://data.cityofnewyork.us/d/ckaz-6gaa
8. US Geological Survey. Landsat Collection 2 Level-2, scene LC09_L2SP_014032_20220720_02_T1, read through Microsoft Planetary Computer. https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2
9. NOAA National Centers for Environmental Information. Daily Summaries (JFK Airport and Central Park), used to choose the satellite day.
10. `[OTHER SOURCES I READ]`
