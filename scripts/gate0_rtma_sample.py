"""Sample NWS RTMA 2.5 km 2 m temperature for the frozen Gate 0 AOIs.

Valid time: 2024-07-15 03:00 Phoenix local = 2024-07-15 10:00 UTC (MST, no DST).
No FortyGuard calls. Does not change the frozen 03:00 TCM classification.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, box, mapping, shape
from shapely.ops import transform as shp_transform

ROOT = Path(__file__).resolve().parents[1]
GATE0 = ROOT / "workforce" / "gate0"
GRIB = GATE0 / "rtma" / "rtma2p5.t10z.2dvaranl_ndfd.grb2_wexp"
AOI_PATH = GATE0 / "track_a" / "aois_preregistered.json"
NIGHT = GATE0 / "nighttime" / "RESULTS.json"
OUT = GATE0 / "rtma"

# Phoenix local 03:00 year-round UTC-7 (Arizona does not observe DST).
PHOENIX_LOCAL = "2024-07-15T03:00:00"
UTC_EQUIVALENT = "2024-07-15T10:00:00Z"
CELL_M = 2500.0  # documented RTMA CONUS native spacing

LOCAL_CRS = CRS.from_proj4(
    "+proj=aeqd +lat_0=33.45 +lon_0=-112.05 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
)
TO_LOCAL = Transformer.from_crs("EPSG:4326", LOCAL_CRS, always_xy=True)
FROM_LOCAL = Transformer.from_crs(LOCAL_CRS, "EPSG:4326", always_xy=True)


def to_local_geom(geom: Polygon) -> Polygon:
    return shp_transform(lambda x, y, z=None: TO_LOCAL.transform(x, y), geom)


def lon180(lon: np.ndarray) -> np.ndarray:
    return ((lon + 180.0) % 360.0) - 180.0


def aoi_polygon(spec: dict) -> Polygon:
    return shape(spec["polygon_aoi"])


def main() -> int:
    aois = json.loads(AOI_PATH.read_text(encoding="utf-8"))["aois"]
    fg = {
        r["aoi_id"]: r["aoi_mean_c"]
        for r in json.loads(NIGHT.read_text(encoding="utf-8"))["fixed_03h"]["aois"]
    }

    ds = xr.open_dataset(
        GRIB,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                "typeOfLevel": "heightAboveGround",
                "level": 2,
                "shortName": "2t",
            }
        },
    )
    t2m = ds["t2m"]
    lat = t2m.latitude.values
    lon = lon180(t2m.longitude.values)
    kelvin = t2m.values
    valid = np.datetime_as_string(t2m.valid_time.values, unit="s")

    mask = (lat >= 33.30) & (lat <= 33.55) & (lon >= -112.20) & (lon <= -111.80)
    ys, xs = np.where(mask)
    points = []
    for y, x in zip(ys, xs, strict=True):
        t_c = float(kelvin[y, x] - 273.15)
        if not math.isfinite(t_c):
            continue
        gx, gy = TO_LOCAL.transform(float(lon[y, x]), float(lat[y, x]))
        cell = box(gx - CELL_M / 2, gy - CELL_M / 2, gx + CELL_M / 2, gy + CELL_M / 2)
        points.append(
            {
                "y": int(y),
                "x": int(x),
                "lat": float(lat[y, x]),
                "lon": float(lon[y, x]),
                "t_c": t_c,
                "cell": cell,
            }
        )

    rows = []
    for spec in aois:
        poly = aoi_polygon(spec)
        local = to_local_geom(poly)
        clon, clat = spec["lon"], spec["lat"]
        cx, cy = TO_LOCAL.transform(clon, clat)

        nearest = min(points, key=lambda p: (p["cell"].centroid.x - cx) ** 2 + (p["cell"].centroid.y - cy) ** 2)
        dist_m = math.hypot(nearest["cell"].centroid.x - cx, nearest["cell"].centroid.y - cy)

        intersecting = []
        weighted = 0.0
        area_sum = 0.0
        for p in points:
            inter = local.intersection(p["cell"])
            a = inter.area
            if a <= 0:
                continue
            intersecting.append({**{k: p[k] for k in ("y", "x", "lat", "lon", "t_c")}, "intersection_m2": a})
            weighted += p["t_c"] * a
            area_sum += a

        intersecting.sort(key=lambda r: -r["intersection_m2"])
        wholly = len(intersecting) == 1 and abs(area_sum - local.area) / local.area < 0.02
        rows.append(
            {
                "aoi_id": spec["aoi_id"],
                "label": spec["label"],
                "centroid_lon": clon,
                "centroid_lat": clat,
                "fortyguard_03h_mean_tcm_c": fg[spec["aoi_id"]],
                "rtma_centroid_t_c": nearest["t_c"],
                "rtma_centroid_cell": {
                    "y": nearest["y"],
                    "x": nearest["x"],
                    "lat": nearest["lat"],
                    "lon": nearest["lon"],
                    "distance_m": dist_m,
                },
                "rtma_aoi_representative_t_c": (weighted / area_sum) if area_sum else None,
                "rtma_intersecting_cell_count": len(intersecting),
                "rtma_intersecting_cells": intersecting,
                "wholly_within_one_rtma_cell": wholly,
                "aoi_area_m2": local.area,
                "intersected_area_m2": area_sum,
            }
        )

    nearest_ids = [(r["rtma_centroid_cell"]["y"], r["rtma_centroid_cell"]["x"]) for r in rows]
    unique_nearest = sorted(set(nearest_ids))
    all_inter = []
    for r in rows:
        all_inter.extend((c["y"], c["x"]) for c in r["rtma_intersecting_cells"])
    unique_inter = sorted(set(all_inter))

    shared = []
    for i, a in enumerate(rows):
        sa = {(c["y"], c["x"]) for c in a["rtma_intersecting_cells"]}
        na = (a["rtma_centroid_cell"]["y"], a["rtma_centroid_cell"]["x"])
        for b in rows[i + 1 :]:
            sb = {(c["y"], c["x"]) for c in b["rtma_intersecting_cells"]}
            nb = (b["rtma_centroid_cell"]["y"], b["rtma_centroid_cell"]["x"])
            if na == nb:
                shared.append(
                    {
                        "aoi_a": a["aoi_id"],
                        "aoi_b": b["aoi_id"],
                        "relationship": "SAME_NEAREST_CELL",
                        "cell": {"y": na[0], "x": na[1]},
                    }
                )
            if sa and sa == sb:
                shared.append(
                    {
                        "aoi_a": a["aoi_id"],
                        "aoi_b": b["aoi_id"],
                        "relationship": "IDENTICAL_INTERSECTING_SUPPORT",
                    }
                )
            overlap = sa & sb
            if overlap and sa != sb:
                shared.append(
                    {
                        "aoi_a": a["aoi_id"],
                        "aoi_b": b["aoi_id"],
                        "relationship": "PARTIAL_SUPPORT_OVERLAP",
                        "shared_cells": [{"y": y, "x": x} for y, x in sorted(overlap)],
                    }
                )

    cvals = [r["rtma_centroid_t_c"] for r in rows]
    avals = [r["rtma_aoi_representative_t_c"] for r in rows]
    payload = {
        "label": "RTMA_VS_FORTYGUARD_03H",
        "gate0_closed": False,
        "does_not_change_frozen_night_classification": True,
        "time_conversion": {
            "phoenix_local": PHOENIX_LOCAL,
            "offset": "UTC-7 year-round; Arizona does not observe DST",
            "utc": UTC_EQUIVALENT,
            "not_converted_as_mdt": True,
            "grib_valid_time": valid,
        },
        "source": {
            "authoritative": "NCEP RTMA CONUS 2.5 km (NDFD western-expansion grid), AWS NODD noaa-rtma-pds",
            "url": "https://noaa-rtma-pds.s3.amazonaws.com/rtma2p5.20240715/rtma2p5.t10z.2dvaranl_ndfd.grb2_wexp",
            "product": "rtma2p5.t10z.2dvaranl_ndfd.grb2_wexp",
            "variable": "t2m / TMP 2 m above ground",
            "units_native": "K",
            "units_reported": "degC (K-273.15)",
            "spatial_resolution": "2.5 km CONUS NDFD Lambert (western expansion, 2345 x 1597)",
            "valid_timestamp_utc": valid,
            "retrieval": "HTTP GET from AWS Open Data (no-sign-request equivalent)",
            "decoder": "cfgrib + xarray; filter_by_keys heightAboveGround level 2 shortName 2t",
            "sampling": {
                "centroid": "nearest RTMA grid point to AOI centroid in azimuthal-equidistant metres",
                "aoi_representative": "area-weighted mean of intersecting 2.5 km squares (aeqd, 2500 m boxes centered on grid points). Approximation of Lambert cell polygons, not exact GRIB cell vertices.",
            },
            "missing": "non-finite Kelvin samples dropped",
        },
        "distinct_rtma_nearest_cells": len(unique_nearest),
        "distinct_rtma_intersecting_cells": len(unique_inter),
        "nearest_cell_ids": [{"aoi_id": r["aoi_id"], "y": r["rtma_centroid_cell"]["y"], "x": r["rtma_centroid_cell"]["x"]} for r in rows],
        "shared_support": shared,
        "centroid_spread_c": max(cvals) - min(cvals),
        "aoi_representative_spread_c": max(avals) - min(avals),
        "centroid_order_warmest_to_coolest": [r["aoi_id"] for r in sorted(rows, key=lambda z: -z["rtma_centroid_t_c"])],
        "aoi_representative_order_warmest_to_coolest": [r["aoi_id"] for r in sorted(rows, key=lambda z: -z["rtma_aoi_representative_t_c"])],
        "fortyguard_03h_spread_frozen_c": 2.9969193181818206,
        "fortyguard_03h_order_frozen": [
            "phx_tempe_mixed",
            "phx_sky_harbor_industrial",
            "phx_downtown_cbd",
            "phx_encanto_park",
            "phx_south_mountain_residential",
        ],
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RTMA_COMPARISON.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print("valid", valid)
    print("nearest unique", len(unique_nearest), unique_nearest)
    print("intersect unique", len(unique_inter))
    print("centroid spread", payload["centroid_spread_c"], payload["centroid_order_warmest_to_coolest"])
    print("area spread", payload["aoi_representative_spread_c"], payload["aoi_representative_order_warmest_to_coolest"])
    print("shared", json.dumps(shared, indent=2))
    for r in rows:
        print(
            r["aoi_id"],
            "FG",
            round(r["fortyguard_03h_mean_tcm_c"], 3),
            "cent",
            round(r["rtma_centroid_t_c"], 3),
            "area",
            round(r["rtma_aoi_representative_t_c"], 3),
            "ncell",
            r["rtma_intersecting_cell_count"],
            "wholly",
            r["wholly_within_one_rtma_cell"],
            "cell",
            r["rtma_centroid_cell"]["y"],
            r["rtma_centroid_cell"]["x"],
            round(r["rtma_centroid_cell"]["lat"], 4),
            round(r["rtma_centroid_cell"]["lon"], 4),
            "dist_m",
            round(r["rtma_centroid_cell"]["distance_m"], 1),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
