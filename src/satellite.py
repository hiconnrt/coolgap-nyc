"""Phase 4, step 1: get the satellite data and turn it into a grid.

Run from the coolgap folder:
    python -m src.satellite

What it does:
  1. Downloads one Landsat scene, but only the rectangle around the focus
     area (not the whole scene, which covers a big part of three states).
     Pixel values are saved unchanged in data/raw/landsat/.
  2. Lays a grid of 100 meter cells over the focus neighborhoods.
  3. For each cell, averages the 30 meter satellite pixels inside it to get:
       surface temperature (the thing the model will predict)
       NDVI   greenness. Plants reflect near-infrared light and absorb red.
       NDBI   built-up index. Buildings and pavement reflect more shortwave
              infrared than near-infrared. A stand-in for impervious surface.
       brightness  how much sunlight the surface reflects
       the average NDVI, NDBI, and brightness of the cells around it
       distance to the coast

Landsat Collection 2 Level-2 is published by the US Geological Survey (USGS).
It is read here through Microsoft Planetary Computer, which needs no account.
"""
import json
from datetime import date

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.windows import from_bounds
from shapely.geometry import box

from src import config

CELL = config.GRID_CELL_METERS

# Quality band bits (USGS). A pixel is skipped if any of these is set.
QA_FILL, QA_DILATED_CLOUD, QA_CIRRUS, QA_CLOUD, QA_SHADOW, QA_WATER = 0, 1, 2, 3, 4, 7
BAD_BITS = [QA_FILL, QA_DILATED_CLOUD, QA_CIRRUS, QA_CLOUD, QA_SHADOW, QA_WATER]


def focus_areas() -> gpd.GeoDataFrame:
    areas = gpd.read_file(config.PROCESSED_DIR / "nta_areas.geojson")
    return areas[areas["in_focus"]].to_crs(config.CRS_LANDSAT)


def download_scene(force: bool = False) -> None:
    """Save the focus-area window of each needed band as a small GeoTIFF."""
    config.LANDSAT_DIR.mkdir(parents=True, exist_ok=True)
    missing = [b for b in config.LANDSAT_BANDS
               if force or not (config.LANDSAT_DIR / f"{b}.tif").exists()]
    if not missing:
        print("  already have the Landsat bands, skipping")
        return

    base = config.PLANETARY_COMPUTER
    item_url = (f"{base}/stac/v1/collections/{config.LANDSAT_COLLECTION}"
                f"/items/{config.LANDSAT_ITEM}")
    item = requests.get(item_url, timeout=60)
    item.raise_for_status()
    item = item.json()
    # A short-lived read token. Anyone can request one, no account needed.
    token = requests.get(f"{base}/sas/v1/token/{config.LANDSAT_COLLECTION}", timeout=60)
    token.raise_for_status()
    token = token.json()["token"]

    west, south, east, north = focus_areas().total_bounds
    m = config.LANDSAT_MARGIN_METERS
    bounds = (west - m, south - m, east + m, north + m)

    log = {"item": config.LANDSAT_ITEM, "scene_date": item["properties"]["datetime"],
           "scene_cloud_cover_pct": item["properties"]["eo:cloud_cover"],
           "platform": item["properties"]["platform"],
           "source_page": item_url, "downloaded": date.today().isoformat(),
           "note": "Only the window around the focus area was saved. "
                   "Pixel values are unchanged.", "bands": {}}
    for band in missing:
        href = item["assets"][band]["href"]
        print(f"  downloading Landsat band {band} ...")
        with rasterio.open(f"{href}?{token}") as src:
            window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
            data = src.read(1, window=window)
            profile = src.profile.copy()
            profile.update(height=data.shape[0], width=data.shape[1],
                           transform=src.window_transform(window),
                           driver="GTiff", compress="deflate")
            profile.pop("blockxsize", None), profile.pop("blockysize", None)
            profile["tiled"] = False
        if data.max() == 0:
            raise RuntimeError(f"{band}: the window is empty. The scene may not cover this area.")
        with rasterio.open(config.LANDSAT_DIR / f"{band}.tif", "w", **profile) as dst:
            dst.write(data, 1)
        log["bands"][band] = {"file": f"landsat/{band}.tif", "url": href,
                              "rows": int(data.shape[0]), "cols": int(data.shape[1])}
    (config.LANDSAT_DIR / "download_log.json").write_text(json.dumps(log, indent=2))


def read_band(name: str):
    with rasterio.open(config.LANDSAT_DIR / f"{name}.tif") as src:
        return src.read(1), src.transform


def pixel_table() -> pd.DataFrame:
    """One row per clear land pixel with its temperature and indexes."""
    red, transform = read_band("red")
    nir, _ = read_band("nir08")
    swir, _ = read_band("swir16")
    thermal, _ = read_band("lwir11")
    qa, _ = read_band("qa_pixel")

    bad = np.zeros(qa.shape, dtype=bool)
    for bit in BAD_BITS:
        bad |= (qa >> bit) & 1 == 1
    bad |= (thermal == 0) | (red == 0) | (nir == 0) | (swir == 0)

    # USGS scale factors turn stored numbers into real units.
    red_r = red * 0.0000275 - 0.2
    nir_r = nir * 0.0000275 - 0.2
    swir_r = swir * 0.0000275 - 0.2
    kelvin = thermal * 0.00341802 + 149.0

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir_r - red_r) / (nir_r + red_r)
        ndbi = (swir_r - nir_r) / (swir_r + nir_r)

    rows, cols = np.nonzero(~bad)
    x = transform.c + (cols + 0.5) * transform.a
    y = transform.f + (rows + 0.5) * transform.e
    table = pd.DataFrame({
        "x": x, "y": y,
        "surface_temp_f": (kelvin[rows, cols] - 273.15) * 9 / 5 + 32,
        "ndvi": ndvi[rows, cols], "ndbi": ndbi[rows, cols],
        # Brightness: how much sunlight the surface reflects (average of
        # three bands). Bright roofs and pavement soak up less heat.
        "brightness": ((red_r + nir_r + swir_r) / 3)[rows, cols],
    })
    return table.replace([np.inf, -np.inf], np.nan).dropna()


def build_grid() -> gpd.GeoDataFrame:
    """Average pixels into 100 m cells and add the other features."""
    pixels = pixel_table()
    pixels["cx"] = (pixels["x"] // CELL).astype(int)
    pixels["cy"] = (pixels["y"] // CELL).astype(int)
    cells = (pixels.groupby(["cx", "cy"])
             .agg(surface_temp_f=("surface_temp_f", "mean"), ndvi=("ndvi", "mean"),
                  ndbi=("ndbi", "mean"), brightness=("brightness", "mean"),
                  pixels=("ndvi", "size")).reset_index())
    cells = cells[cells["pixels"] >= config.GRID_MIN_PIXELS]

    # Average of the cell and its 8 neighbors (a 300 m by 300 m square).
    lookup = cells.set_index(["cx", "cy"])[["ndvi", "ndbi", "brightness"]]
    shifted = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            part = lookup.copy()
            part.index = pd.MultiIndex.from_arrays(
                [part.index.get_level_values(0) + dx, part.index.get_level_values(1) + dy],
                names=["cx", "cy"])
            shifted.append(part)
    nearby = pd.concat(shifted).groupby(level=["cx", "cy"]).mean()
    cells = cells.join(nearby.rename(columns={"ndvi": "ndvi_nearby", "ndbi": "ndbi_nearby",
                                             "brightness": "brightness_nearby"}),
                       on=["cx", "cy"])

    cells["x"] = (cells["cx"] + 0.5) * CELL
    cells["y"] = (cells["cy"] + 0.5) * CELL
    grid = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells["x"], cells["y"]),
                            crs=config.CRS_LANDSAT)

    # Keep cells whose center is inside a focus neighborhood.
    focus = focus_areas()[["nta2020", "ntaname", "geometry"]]
    grid = gpd.sjoin(grid, focus, predicate="within").drop(columns="index_right")

    # Distance to the coast: the edge of all city land, from the NTA file.
    land = gpd.read_file(config.RAW_DIR / config.SOURCES["nta_boundaries"]["file"])
    # Neighboring shapes can have hair-thin gaps between them. Growing the
    # land by 15 m and shrinking it back closes those gaps, so only real
    # water edges count as coast.
    merged = land.to_crs(config.CRS_LANDSAT).union_all().buffer(15).buffer(-15)
    coast = merged.boundary
    grid["coast_distance_m"] = grid.geometry.distance(coast)

    latlon = grid.geometry.to_crs(config.CRS_LATLON)
    grid["lat"], grid["lon"] = latlon.y, latlon.x
    return grid.reset_index(drop=True)


def cell_square(x: float, y: float):
    """The square outline of a cell, for drawing on a map."""
    half = CELL / 2
    return box(x - half, y - half, x + half, y + half)


def main() -> None:
    download_scene()
    grid = build_grid()
    out = config.PROCESSED_DIR / "heat_grid.csv"
    grid.drop(columns="geometry").to_csv(out, index=False)
    print(f"Saved {len(grid):,} grid cells to {out.name}")
    print(grid[["surface_temp_f", "ndvi", "ndbi", "coast_distance_m", "pixels"]]
          .describe().round(2).T[["min", "mean", "max"]].to_string())


if __name__ == "__main__":
    main()
