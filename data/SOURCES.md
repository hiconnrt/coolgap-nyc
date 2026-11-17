# Data Sources

Every dataset in this project is listed here with its official link, the date it
was downloaded, and what each column means. Raw files are saved in `data/raw/`
and are never edited. The file `data/raw/download_log.json` is written by the
download script and records the exact link and date for each file.

All files below were downloaded on **2026-11-16**.

## Status summary

| # | Dataset | Status |
|---|---|---|
| 1 | Heat Vulnerability Index by neighborhood | Downloaded |
| 2 | Cooling centers | Downloaded (see caveats) |
| 3 | Neighborhood boundaries (2020 NTAs) | Downloaded |
| 3b | Census tract to NTA lookup | Downloaded |
| 3c | 2020 census tract boundaries | Downloaded |
| 4 | Population and age 65+ (ACS) | Downloaded (Brooklyn tract rows only, see notes) |
| 5 | Tree canopy | Using the green space column from dataset 1 (see note) |
| 6a | Public libraries | Downloaded |
| 6b | Spray showers | Downloaded |
| 7 | Landsat 9 satellite scene (Phase 4) | Downloaded 2026-11-17 (focus-area window only) |
| 8 | Daily high temperatures (used only to pick the satellite day) | Looked up 2026-11-17, not saved as a file |

---

## 1. Heat Vulnerability Index (HVI) by 2020 NTA

- **Publisher:** NYC Department of Health and Mental Hygiene, Environment and Health Data Portal
- **Page:** https://a816-dohbesp.nyc.gov/IndicatorPublic/data-features/hvi/
- **File link:** https://raw.githubusercontent.com/nychealth/EHDP-data/production/key-topics/heat-vulnerability-index/hvi-nta-2020.csv
- **Saved as:** `data/raw/hvi_nta_2020.csv`
- **Rows:** 198 (one per residential neighborhood in the city, with one duplicate, see notes)
- **What the publisher says went into it:** American Community Survey 2016 to 2020, 2017 LiDAR land cover, the 2020 Census, and satellite surface temperature.

| Column | Meaning |
|---|---|
| NTACode | 2020 Neighborhood Tabulation Area code, for example BK1302 |
| GEOCODE | Numeric version of the area code used by the data portal |
| GEONAME | Neighborhood name |
| CDTACode | Community District Tabulation Area the neighborhood belongs to |
| HVI_RANK | Heat Vulnerability Index score. 1 = lowest risk, 5 = highest risk |
| SURFACE_TEMP | Daytime summer surface temperature in degrees Fahrenheit |
| MEDIAN_INCOME | Median household income in dollars |
| GREENSPACE | Percent of the neighborhood covered by trees, grass, or shrubs |
| PCT_HOUSEHOLDS_AC | Percent of households with air conditioning |
| PCT_BLACK_POP | Percent of residents who are Black |
| SURFACE_TEMP_TERT, INCOME_TERT, GREENSPACE_TERT, AC_TERT | The same values sorted into thirds (1 to 3). Used by the city for map shading. Not used in this project. |

**Notes**
- Kingsbridge-Marble Hill (BX0802) appears twice with the same values. The cleaning step keeps one row. This does not affect Brooklyn.
- The air conditioning percent repeats across neighbors (for example three areas in BK13 all show 86.6). It looks like the city measured it for a larger area and copied it down. Treat it as a rough value.
- The HVI is the city's measure. It is not changed by this project.

## 2. Cooling centers (Indoor Cool Options)

- **Publisher:** NYC Emergency Management (ArcGIS account `NYCEM_ETL`)
- **Page:** https://www.arcgis.com/home/item.html?id=fb0cd480f900469e9f5ebeac3d6b06f0
- **File link:** https://services1.arcgis.com/8cuieNI8NbqQZQVJ/arcgis/rest/services/NYC_Open_Cooling_Centers_Site_Survey_view/FeatureServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=geojson
- **Saved as:** `data/raw/cooling_centers_nycem.geojson`
- **Rows:** 476 citywide (140 in Brooklyn)
- **Last edited by the publisher:** 2026-09-14

| Column | Meaning |
|---|---|
| OBJECTID | Row number from the map service |
| NYCEM_ID | NYC Emergency Management ID for the site, for example CC0001 |
| Facility_name | Site name. Sites for seniors only end with "OLDER ADULTS ONLY" |
| Address | Street address |
| Borough | Borough name |
| Finder_status | Status in the city's finder. Every row says OPEN |
| Operating_agency | Who runs the site. AGING = NYC Aging older adult centers, BPL / NYPL / QPL = the three library systems, Petco = pet friendly stores, plus a few cultural sites |
| geometry | Point location (longitude, latitude) |

**Caveats (important)**
- This is **historical data** from the 2026 summer season. Cooling centers change every summer and only open during heat emergencies. For current locations use https://finder.nyc.gov/coolingcenters/ or call 311.
- The layer was made by the city for its own site visit survey. It has no description and no stated license. It is public, but it is not a formal open data release.
- 283 of the 476 sites (94 of 140 in Brooklyn) are for older adults only. They cannot be counted as cooling access for everyone.
- 40 Brooklyn sites are Brooklyn Public Library branches. These same buildings also appear in dataset 6a, so they must not be counted twice.

## 3. Neighborhood boundaries (2020 NTAs)

- **Publisher:** NYC Department of City Planning
- **Page:** https://data.cityofnewyork.us/d/9nt8-h7nd
- **File link:** https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?$limit=5000
- **Saved as:** `data/raw/nta_2020.geojson`
- **Rows:** 262 (197 residential, the rest are parks, cemeteries, airports and similar)

| Column | Meaning |
|---|---|
| nta2020 | Neighborhood code. Matches NTACode in dataset 1 |
| ntaname | Neighborhood name |
| ntaabbrev | Short name |
| ntatype | 0 = residential, 5 = Rikers Island, 6 = other special area, 7 = cemetery, 8 = airport, 9 = park |
| borocode, boroname, countyfips | Borough number, borough name, county code |
| cdta2020, cdtaname | Community District Tabulation Area code and name |
| shape_leng, shape_area | Boundary length (feet) and area (square feet) |
| geometry | The boundary shape |

## 3b. 2020 census tract to NTA lookup

- **Publisher:** NYC Department of City Planning
- **Page:** https://data.cityofnewyork.us/d/hm78-6dwm
- **File link:** https://data.cityofnewyork.us/resource/hm78-6dwm.csv?$limit=5000
- **Saved as:** `data/raw/tract_to_nta_2020.csv`
- **Rows:** 2,327 (one per census tract). Used to add tract population up to neighborhoods.

| Column | Meaning |
|---|---|
| geoid | Full 11 digit census tract code |
| countyfips, borocode, boroname | County code, borough number, borough name |
| boroct2020, ct2020, ctlabel | City and census versions of the tract number |
| ntacode, ntatype, ntaname, ntaabbrev | The NTA this tract belongs to |
| cdtacode, cdtatype, cdtaname | The Community District Tabulation Area this tract belongs to |

## 3c. 2020 census tract boundaries

- **Publisher:** NYC Department of City Planning
- **Page:** https://data.cityofnewyork.us/d/63ge-mke6
- **File link:** https://data.cityofnewyork.us/resource/63ge-mke6.geojson?boroname=Brooklyn&$limit=5000
- **Saved as:** `data/raw/tracts_2020_brooklyn.geojson`
- **Rows:** 804 Brooklyn tracts (clipped to the shoreline, so one water-only tract is left out). Dataset last updated 2026-11-02.
- **Used for:** finding the center of each tract, so distance can be measured from where people live.

| Column | Meaning |
|---|---|
| geoid | Full 11 digit census tract code. Matches dataset 3b and dataset 4 |
| ct2020, boroct2020, ctlabel | City versions of the tract number |
| borocode, boroname | Borough number and name |
| nta2020, ntaname | Neighborhood the tract belongs to |
| cdta2020, cdtaname | Community District Tabulation Area |
| cdeligibil | Whether the tract qualifies for federal community development funding. Not used |
| shape_leng, shape_area | Boundary length (feet) and area (square feet) |
| geometry | The boundary shape |

## 4. Population and age 65+ (American Community Survey)

- **Publisher:** US Census Bureau
- **Dataset:** American Community Survey 5-year estimates, 2020 to 2024, table B01001 (Sex by Age), table-based summary file
- **Folder page:** https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/
- **File link:** https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b01001.dat
- **Column names checked against:** https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/documentation/ACS20245YR_Table_Shells.txt
- **Saved as:** `data/raw/acs2024_b01001_tracts_047.dat`
- **Rows:** 805 (one per Brooklyn census tract)

**How this file was saved (read this)**
- The Census API returned a "Missing Key" page on 2026-11-16, so the public summary file is used instead. It is the same table.
- The full file covers every area in the country and is about 200 MB. The download script keeps only the header line and the rows whose ID starts with `1400000US36047` (census tracts in Kings County, which is Brooklyn). The kept rows are not changed.
- So this raw file is a **row-filtered copy** of the official file, not the whole file.

| Column | Meaning |
|---|---|
| GEO_ID | Area ID. The last 11 digits are the census tract code (state 36, county 047, then the tract) |
| B01001_E001 | Estimate of total population |
| B01001_E002 | Estimate of total males |
| B01001_E003 to E025 | Males by age group. E020 to E025 are ages 65 and 66, 67 to 69, 70 to 74, 75 to 79, 80 to 84, and 85 and over |
| B01001_E026 | Estimate of total females |
| B01001_E027 to E049 | Females by age group. E044 to E049 are the same six groups for age 65 and over |
| B01001_M001 to M049 | Margin of error for each estimate above. Not used yet |

**Notes**
- These are survey **estimates**, not exact counts. Each has a margin of error, which is bigger for small areas.
- Population 65+ = E020 to E025 plus E044 to E049.
- Tracts are added up to neighborhoods using dataset 3b. Brooklyn tracts total 2,631,580 people. The 53 residential neighborhoods hold 2,630,586 of them. The other 994 live in tracts inside park or special areas, which are not scored.
- The HVI (dataset 1) was built by the city from 2016 to 2020 data, so the population years and the HVI years do not match exactly.

## 5. Tree canopy / green space

- No separate file. The project uses the `GREENSPACE` column from dataset 1.
- It measures trees, grass, and shrubs together, not trees only.
- Green space is also one of the ingredients of the HVI, so the two are related.

## 6a. Public libraries

- **Publisher:** NYC Department of City Planning, Facilities Database
- **Page:** https://data.cityofnewyork.us/d/ji82-xba5
- **File link:** https://data.cityofnewyork.us/resource/ji82-xba5.csv?$where=facsubgrp%3D%27PUBLIC%20LIBRARIES%27&$limit=5000
- **Saved as:** `data/raw/facdb_libraries.csv`
- **Rows:** 227 citywide (68 in Brooklyn). Dataset last updated 2026-07-16.

| Column | Meaning |
|---|---|
| uid | ID for the facility |
| facname | Library name |
| address, addressnum, streetname, city, zipcode | Address parts |
| boro, borocode | Borough name and number |
| latitude, longitude | Location |
| xcoord, ycoord | Location in NY State Plane feet |
| nta2020, nta2010, ct2020, ct2010, cd, council, schooldist, policeprct | Districts the library sits in |
| facgroup, facsubgrp, factype, facdomain | Facility categories. All rows are PUBLIC LIBRARIES |
| opname, opabbrev, optype | Who operates it (Brooklyn, New York, or Queens Public Library) |
| overagency, overabbrev, overlevel | Overseeing agency |
| capacity, captype, servarea | Not filled in for libraries |
| bin, bbl | Building and tax lot numbers |
| datasource | Where City Planning got the record |
| geometry | Point location |

## 6b. Spray showers

- **Publisher:** NYC Parks
- **Page:** https://data.cityofnewyork.us/d/ckaz-6gaa
- **File link:** https://data.cityofnewyork.us/resource/ckaz-6gaa.geojson?$limit=5000
- **Saved as:** `data/raw/parks_spray_showers.geojson`
- **Rows:** 1,136 citywide (336 with borough code B)

| Column | Meaning |
|---|---|
| propname | Park name |
| sitename | Name of the playground or site inside the park |
| propid, propnum | NYC Parks property IDs |
| system | NYC Parks internal ID for the spray shower |
| boro | Borough letter. B = Brooklyn, M = Manhattan, Q = Queens, X = Bronx, R = Staten Island |
| district | Parks district |
| coundist | City Council district |
| geometry | Point location |

**Caveats**
- Each row is one spray shower, so a single park can have many rows (Coney Island-Sea Gate has 25).
- Spray showers are outdoors and only run in summer on hot days. They are not the same kind of help as an air conditioned room.

## 7. Landsat 9 satellite scene (Phase 4)

- **Publisher:** US Geological Survey (USGS), Landsat Collection 2 Level-2
- **Read through:** Microsoft Planetary Computer (no account needed)
- **Scene:** `LC09_L2SP_014032_20220720_02_T1`, taken 2022-07-20 at about 11:40 am local time
- **Scene page:** https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC09_L2SP_014032_20220720_02_T1
- **Saved as:** `data/raw/landsat/red.tif`, `nir08.tif`, `swir16.tif`, `lwir11.tif`, `qa_pixel.tif`
- **Downloaded:** 2026-11-17. The exact file links are in `data/raw/landsat/download_log.json`.
- **Why this day:** it was hot and clear. The recorded high was 95 F at both JFK Airport and Central Park (see dataset 8). Cloud cover was 3.67% over the whole scene and about 0.1% over the focus area.

**How these files were saved (read this)**
- A full Landsat scene covers a very large area. Only the rectangle around the focus area (plus a 1 km margin) was saved. Pixel values are unchanged.
- Pixels are 30 meters wide.

| File | Meaning | How stored numbers become real units |
|---|---|---|
| red.tif | Red light reflected by the surface | value x 0.0000275 - 0.2 = reflectance |
| nir08.tif | Near-infrared light reflected. Plants reflect a lot of it | same as red |
| swir16.tif | Shortwave infrared light reflected. Buildings and pavement reflect a lot of it | same as red |
| lwir11.tif | Land surface temperature | value x 0.00341802 + 149.0 = kelvin |
| qa_pixel.tif | Quality flags. Bits used: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow, 7 water | pixels with any of these flags are skipped |

**Notes**
- This is **surface** temperature (roofs, streets, ground), not the air temperature people feel.
- It is one moment on one day.
- The scene is from 2022. The cooling resources are from 2026.

## 8. Daily high temperatures (used only to choose the satellite day)

- **Publisher:** NOAA National Centers for Environmental Information, Daily Summaries
- **Link pattern:** https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094789&dataTypes=TMAX&units=standard&format=json (plus start and end dates)
- **Stations:** USW00094789 (JFK Airport) and USW00094728 (Central Park)
- **Looked up:** 2026-11-17. Not saved as a file, because it is not used in any calculation.
- **Column used:** TMAX, the highest temperature of the day in degrees Fahrenheit.
- Of 23 clear summer scenes checked, the hot ones were 2022-07-20 (95 F at both stations), 2025-07-28 (93 and 94 F), and 2025-07-29 (96 and 97 F).

---

## Processed files (made by `python -m src.clean`)

| File | What it is |
|---|---|
| `data/processed/nta_areas.geojson` | 53 residential Brooklyn neighborhoods with boundaries, HVI values, total population, population 65+, and percent 65+. `in_focus` is true for the 9 southern Brooklyn neighborhoods. |
| `data/processed/tracts.csv` | 787 census tracts inside the 53 scored neighborhoods, with the center point, total population, and population 65+ of each. |
| `data/processed/cooling_resources.csv` | 1,839 cooling resources citywide (476 cooling centers, 227 libraries, 1,136 spray showers) with type, name, location, and the neighborhood each one sits in. `duplicate_of_cooling_center` is true for 177 library rows that are the same building as a library-run cooling center (within 400 feet). |

## Calculated files (made by `python -m src.access` and `python -m src.gap_score`)

These are not downloaded data. They are numbers this project calculates.

| File | What it is |
|---|---|
| `data/processed/access_by_nta.csv` | Cooling access numbers for each neighborhood: distance to nearest resource, resources within walking distance, percent of residents within walking distance, resources per 10,000 residents. Columns ending in `_65` are the versions for people aged 65 and over, which also count older-adult-only centers. |
| `data/processed/cags_by_nta.csv` | Everything above plus the Cooling Access Gap Score. `part_` columns are the 0 to 1 parts, `points_` columns are the points each part adds, `cags` is the score, `cags_rank` is the rank in the borough. **CAGS is this project's own research score, not an official measure.** |
| `data/processed/clusters_by_nta.csv` | The K-means group of each neighborhood (made by `python -m src.clusters`). Group names are written by a rule from each group's averages. |
| `data/processed/cluster_summary.csv` | Averages for each K-means group. |
| `data/processed/heat_grid.csv` | 2,926 grid cells of 100 m in the focus area (made by `python -m src.satellite`). Columns: measured surface temperature, NDVI (greenness), NDBI (built-up index), brightness, the same three averaged over the surrounding cells, distance to coast in meters, and how many satellite pixels were averaged. |
| `data/processed/heat_grid_predictions.csv` | The same cells plus the Random Forest prediction and its error (made by `python -m experiments.exp_e_model`). Each prediction comes from a model that did not train on that cell's 1 km block. |
