"""Generate Track A pre-registered equal-area AOIs. No FortyGuard HTTP.

Areas are local equirectangular 1000 m × 1000 m axis-aligned rectangles.
This script must be run (and its output committed to workforce/) BEFORE any
Track A live heatmap request.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "workforce" / "gate0" / "track_a"
OUT_JSON = OUT_DIR / "aois_preregistered.json"
OUT_GEOJSON = OUT_DIR / "aois_preregistered.geojson"

# WGS84 meters-per-degree approximations (sufficient for 1 km² ±10% check).
M_PER_DEG_LAT = 111_320.0
TARGET_SIDE_M = 1000.0
TARGET_AREA_M2 = TARGET_SIDE_M * TARGET_SIDE_M
AREA_TOLERANCE = 0.10  # ±10%

# Selected BEFORE any Track A TCM results. Urban-form rationale is land-cover /
# urban morphology, not thermal observations.
AOI_CENTERS = [
    {
        "aoi_id": "phx_downtown_cbd",
        "label": "Downtown Phoenix CBD",
        "urban_form": "dense commercial core / high impervious fraction",
        "lat": 33.4484,
        "lon": -112.0740,
    },
    {
        "aoi_id": "phx_encanto_park",
        "label": "Encanto Park and historic neighborhoods",
        "urban_form": "municipal park plus adjacent historic residential",
        "lat": 33.4743,
        "lon": -112.0863,
    },
    {
        "aoi_id": "phx_sky_harbor_industrial",
        "label": "Sky Harbor industrial fringe",
        "urban_form": "airport-adjacent industrial / logistics",
        "lat": 33.4275,
        "lon": -112.0140,
    },
    {
        "aoi_id": "phx_south_mountain_residential",
        "label": "South Mountain residential fringe",
        "urban_form": "lower-canopy residential / desert-urban edge",
        "lat": 33.3920,
        "lon": -112.0730,
    },
    {
        "aoi_id": "phx_tempe_mixed",
        "label": "Tempe mixed university/commercial",
        "urban_form": "university campus plus commercial mixed-use",
        "lat": 33.4255,
        "lon": -111.9400,
    },
]


def m_per_deg_lon(lat: float) -> float:
    return M_PER_DEG_LAT * math.cos(math.radians(lat))


def square_ring(lon: float, lat: float, side_m: float = TARGET_SIDE_M) -> list[list[float]]:
    half = side_m / 2.0
    dlat = half / M_PER_DEG_LAT
    dlon = half / m_per_deg_lon(lat)
    sw = [lon - dlon, lat - dlat]
    se = [lon + dlon, lat - dlat]
    ne = [lon + dlon, lat + dlat]
    nw = [lon - dlon, lat + dlat]
    return [sw, se, ne, nw, sw]


def shoelace_m2(ring: list[list[float]], lat0: float) -> float:
    mx = m_per_deg_lon(lat0)
    my = M_PER_DEG_LAT
    xs = [(pt[0]) * mx for pt in ring[:-1]]
    ys = [(pt[1]) * my for pt in ring[:-1]]
    area = 0.0
    n = len(xs)
    for i in range(n):
        j = (i + 1) % n
        area += xs[i] * ys[j] - xs[j] * ys[i]
    return abs(area) / 2.0


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    features = []
    aois = []
    for spec in AOI_CENTERS:
        ring = square_ring(spec["lon"], spec["lat"])
        area_m2 = shoelace_m2(ring, spec["lat"])
        rel = abs(area_m2 - TARGET_AREA_M2) / TARGET_AREA_M2
        if rel > AREA_TOLERANCE:
            raise SystemExit(
                f"{spec['aoi_id']} area {area_m2:.1f} m² outside ±10% of {TARGET_AREA_M2}"
            )
        geometry = {"type": "Polygon", "coordinates": [ring]}
        aois.append(
            {
                **spec,
                "shape_class": "axis_aligned_rectangle",
                "target_side_m": TARGET_SIDE_M,
                "area_m2": area_m2,
                "area_km2": area_m2 / 1e6,
                "area_rel_error_vs_target": rel,
                "polygon_aoi": geometry,
            }
        )
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "aoi_id": spec["aoi_id"],
                    "label": spec["label"],
                    "urban_form": spec["urban_form"],
                    "area_km2": area_m2 / 1e6,
                },
                "geometry": geometry,
            }
        )

    areas = [a["area_km2"] for a in aois]
    span = max(areas) / min(areas) - 1.0
    payload = {
        "status": "PREREGISTERED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "live_http": False,
        "tcm_results_observed": False,
        "target_area_km2": 1.0,
        "area_tolerance": AREA_TOLERANCE,
        "max_area_ratio_minus_one": span,
        "aois": aois,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_GEOJSON}")
    print(f"n_aois={len(aois)} area_km2={[round(a, 4) for a in areas]} max_rel_span={span:.4f}")
    if span > AREA_TOLERANCE:
        raise SystemExit("AOI areas differ by more than ±10%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
