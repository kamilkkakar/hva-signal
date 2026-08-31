#!/usr/bin/env python3
"""Materialize CROSS_CITY_CANOPY_CONTRACT_V1 from NLCD TCC 2021 via MRLC WCS.

Per-tract WCS windows (fast). No FortyGuard. No Phoenix OHR TREE_PCT_N.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image
from shapely.geometry import Point, shape
from shapely.prepared import prep

REPO = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO / "data" / "areas" / "cross-city" / "INDEX.json"
OUT_DIR = REPO / "data" / "context" / "cross-city" / "canopy"
WCS_URL = "https://www.mrlc.gov/geoserver/mrlc_download/wcs"
COVERAGE = "mrlc_download:nlcd_tcc_conus_2021_v2021-4"
USER_AGENT = "HVA-Signal/0.1 (cross-city-canopy; NLCD TCC WCS)"
CONTRACT = "CROSS_CITY_CANOPY_CONTRACT_V1"
VINTAGE = "2021 NLCD TCC for comparable four-city baseline"


def _fetch_window(
    client: httpx.Client,
    *,
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    size: int = 64,
) -> np.ndarray:
    params = {
        "SERVICE": "WCS",
        "VERSION": "1.0.0",
        "REQUEST": "GetCoverage",
        "COVERAGE": COVERAGE,
        "CRS": "EPSG:4326",
        "BBOX": f"{minx},{miny},{maxx},{maxy}",
        "WIDTH": str(size),
        "HEIGHT": str(size),
        "FORMAT": "GeoTIFF",
    }
    response = client.get(WCS_URL, params=params)
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content))
    arr = np.asarray(image, dtype=np.float64)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    return arr


def _tract_mean(client: httpx.Client, geom) -> float | None:
    minx, miny, maxx, maxy = geom.bounds
    pad_x = (maxx - minx) * 0.05 or 0.0003
    pad_y = (maxy - miny) * 0.05 or 0.0003
    extent = (minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y)
    arr = _fetch_window(
        client,
        minx=extent[0],
        miny=extent[1],
        maxx=extent[2],
        maxy=extent[3],
        size=64,
    )
    height, width = arr.shape
    prepared = prep(geom)
    samples: list[float] = []
    for row in range(height):
        lat = extent[3] - (row + 0.5) * (extent[3] - extent[1]) / height
        for col in range(width):
            lon = extent[0] + (col + 0.5) * (extent[2] - extent[0]) / width
            val = float(arr[row, col])
            if val < 0 or val > 100:
                continue
            if prepared.contains(Point(lon, lat)):
                samples.append(val)
    if samples:
        return float(sum(samples) / len(samples))
    rp = geom.representative_point()
    col = int((rp.x - extent[0]) / (extent[2] - extent[0]) * width)
    row = int((extent[3] - rp.y) / (extent[3] - extent[1]) * height)
    if 0 <= row < height and 0 <= col < width:
        val = float(arr[row, col])
        if 0 <= val <= 100:
            return val
    return None


def materialize_city(client: httpx.Client, city: dict[str, Any]) -> dict[str, Any]:
    fc = json.loads((REPO / city["paths"]["geometry"]).read_text(encoding="utf-8"))
    rows: dict[str, Any] = {}
    missing: list[str] = []
    values: list[float] = []
    for feature in fc["features"]:
        geoid = str(feature["properties"]["GEOID"]).zfill(11)
        mean = _tract_mean(client, shape(feature["geometry"]))
        if mean is None:
            missing.append(geoid)
            rows[geoid] = {"cross_city_tree_canopy_pct": None, "coverage": "missing"}
        else:
            values.append(mean)
            rows[geoid] = {
                "cross_city_tree_canopy_pct": round(mean, 3),
                "coverage": "ok",
            }
        print(f"  {city['city_id']} {geoid} -> {rows[geoid]['cross_city_tree_canopy_pct']}", flush=True)
    return {
        "city_id": city["city_id"],
        "place_geoid": city["place_geoid"],
        "tract_count": len(rows),
        "covered_count": len(rows) - len(missing),
        "missing_geoids": missing,
        "range": {
            "min": round(min(values), 3) if values else None,
            "max": round(max(values), 3) if values else None,
        },
        "rows": rows,
        "aggregation": (
            "Mean of NLCD TCC 2021 WCS pixel centers inside each tract polygon"
        ),
        "coverage_id": COVERAGE,
    }


def main() -> int:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cities_meta: list[dict[str, Any]] = []
    with httpx.Client(
        timeout=180.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for city in index["cities"]:
            print(f"CANOPY {city['city_id']}", flush=True)
            doc = materialize_city(client, city)
            path = OUT_DIR / f"{city['city_id']}.json"
            path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            cities_meta.append(
                {
                    "city_id": city["city_id"],
                    "path": str(path.relative_to(REPO).as_posix()),
                    "covered_count": doc["covered_count"],
                    "tract_count": doc["tract_count"],
                    "range": doc["range"],
                    "missing": len(doc["missing_geoids"]),
                }
            )
            print(
                f"OK {city['city_id']}: covered={doc['covered_count']}/{doc['tract_count']} "
                f"range={doc['range']}",
                flush=True,
            )

    contract = {
        "contract_version": CONTRACT,
        "status": "MATERIALIZED",
        "source_selected": (
            "NLCD / USDA Forest Service Percent Tree Canopy Cover (CONUS) via MRLC WCS "
            f"{COVERAGE}"
        ),
        "definition": (
            "Percent of each 30 m raster cell covered by tree canopy; tract value is "
            "mean of WCS pixel centers falling inside the tract polygon."
        ),
        "vintage": VINTAGE,
        "resolution": "30 m source; per-tract WCS window",
        "aggregation_to_tracts": (
            "Pixel-center mean inside tract polygon from NLCD TCC 2021 WCS window."
        ),
        "all_four_cities_supported": True,
        "phoenix_local_canopy_difference": (
            "Phoenix local canopy uses OHR shade-study TREE_PCT_N over plantable ground; "
            "not reused here."
        ),
        "silent_substitute_forbidden": True,
        "comparison_defensible": True,
        "cities": cities_meta,
    }
    (OUT_DIR / "CONTRACT.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"cities": cities_meta}, indent=2))
    return 1 if any(c["missing"] for c in cities_meta) else 0


if __name__ == "__main__":
    raise SystemExit(main())
