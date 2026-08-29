"""Plan AOI partitions under the FortyGuard ~130 km² ceiling.

Geometric stub: pass through small AOIs unchanged (preserving coordinates for
fingerprint stability) and split large bounding boxes on a lon/lat grid.
"""

from __future__ import annotations

import math
from typing import Any

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

from app.integrations.fortyguard.transport_models import PartitionPlan

AOI_AREA_CEILING_KM2 = 130.0


def as_polygon(aoi: dict[str, Any]) -> dict[str, Any]:
    kind = aoi.get("type")
    if kind == "Polygon":
        return aoi
    if kind == "Feature":
        return dict(aoi["geometry"])
    if kind == "FeatureCollection":
        return dict(aoi["features"][0]["geometry"])
    if "coordinates" in aoi:
        return {"type": "Polygon", "coordinates": aoi["coordinates"]}
    raise ValueError(f"Unsupported AOI geometry: {kind!r}")


def polygon_area_km2(polygon_aoi: dict[str, Any]) -> float:
    """Equirectangular approximation — enough to enforce the ~130 km² cap."""
    poly = as_polygon(polygon_aoi)
    ring = poly["coordinates"][0]
    lats = [p[1] for p in ring]
    lat0 = math.radians(sum(lats) / len(lats))
    pts = [(p[0] * 111.32 * math.cos(lat0), p[1] * 110.57) for p in ring]
    area = 0.0
    for i in range(len(pts) - 1):
        area += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return abs(area) / 2.0


def _geom_area_km2(geom: BaseGeometry) -> float:
    mapped = mapping(geom)
    if mapped["type"] == "Polygon":
        return polygon_area_km2(mapped)
    if mapped["type"] == "MultiPolygon":
        return sum(
            polygon_area_km2({"type": "Polygon", "coordinates": coords})
            for coords in mapped["coordinates"]
        )
    return 0.0


def _cell_polygons(geom: BaseGeometry, ceiling_km2: float) -> list[dict[str, Any]]:
    if geom.is_empty:
        return []
    geom_type = geom.geom_type
    if geom_type in {"GeometryCollection", "MultiPolygon"}:
        pieces: list[dict[str, Any]] = []
        for part in geom.geoms:
            pieces.extend(_cell_polygons(part, ceiling_km2))
        return pieces
    if geom_type != "Polygon":
        return []
    area = _geom_area_km2(geom)
    if area <= ceiling_km2 or area == 0.0:
        mapped = mapping(geom)
        if mapped["type"] == "Polygon":
            return [mapped]
        return []

    minx, miny, maxx, maxy = geom.bounds
    n = max(2, math.ceil(area / ceiling_km2))
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = max(1, math.ceil(n / cols))
    dx = (maxx - minx) / cols
    dy = (maxy - miny) / rows
    if dx == 0 or dy == 0:
        mapped = mapping(geom)
        return [mapped] if mapped.get("type") == "Polygon" else []

    from shapely.geometry import box

    pieces: list[dict[str, Any]] = []
    for row in range(rows):
        for col in range(cols):
            cell = box(
                minx + col * dx,
                miny + row * dy,
                minx + (col + 1) * dx,
                miny + (row + 1) * dy,
            )
            inter = geom.intersection(cell)
            if inter.is_empty:
                continue
            pieces.extend(_cell_polygons(inter, ceiling_km2))
    return pieces


def plan_partitions(
    aoi: dict[str, Any],
    *,
    ceiling_km2: float = AOI_AREA_CEILING_KM2,
) -> list[PartitionPlan]:
    poly = as_polygon(aoi)
    area = polygon_area_km2(poly)
    if area <= ceiling_km2:
        return [PartitionPlan(partition_id="p0", geometry=aoi, area_km2=area)]

    geom = shape(poly)
    polygons = _cell_polygons(geom, ceiling_km2)
    plans: list[PartitionPlan] = []
    for index, geometry in enumerate(polygons):
        cell_area = polygon_area_km2(geometry)
        if cell_area <= 0:
            continue
        plans.append(
            PartitionPlan(
                partition_id=f"p{index}",
                geometry=geometry,
                area_km2=cell_area,
            )
        )
    if not plans:
        return [PartitionPlan(partition_id="p0", geometry=aoi, area_km2=area)]
    return plans
