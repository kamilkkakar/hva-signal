"""Rook adjacency for the national resolver.

Rook = shared boundary *segment* in EPSG:5070 whose linear length
exceeds 1 mm. Corner-only contact is not adjacency. Distance, buffer,
and nearest-neighbor fallbacks are refused.
"""

from __future__ import annotations

from collections.abc import Mapping

from shapely.geometry.base import BaseGeometry

from app.services.national_geometry import (
    NationalGeometryError,
    computation_geometry,
)

ROOK_MIN_SHARED_BOUNDARY_M = 1e-3
LINEAR_TYPES = frozenset({"LineString", "MultiLineString", "LinearRing"})
_POINT_TYPES = frozenset({"Point", "MultiPoint"})

__all__ = [
    "DistanceAdjacencyFallbackError",
    "ROOK_MIN_SHARED_BOUNDARY_M",
    "are_rook_neighbors",
    "build_buffered_adjacency",
    "build_distance_adjacency",
    "rook_graph",
    "shared_boundary_length_m",
    "shared_boundary_length_projected",
]


class DistanceAdjacencyFallbackError(NationalGeometryError):
    """Callers asked for nearest-distance or buffered adjacency. That is not rook."""


def _linear_length_m(geom: BaseGeometry) -> float:
    if geom.is_empty:
        return 0.0
    kind = geom.geom_type
    if kind in LINEAR_TYPES:
        return float(geom.length)
    if kind == "GeometryCollection":
        return sum(_linear_length_m(part) for part in geom.geoms)
    return 0.0


def _bounds_overlap(a: BaseGeometry, b: BaseGeometry) -> bool:
    if not a.bounds or not b.bounds:
        return False
    minx = max(a.bounds[0], b.bounds[0])
    miny = max(a.bounds[1], b.bounds[1])
    maxx = min(a.bounds[2], b.bounds[2])
    maxy = min(a.bounds[3], b.bounds[3])
    return minx <= maxx and miny <= maxy


def shared_boundary_length_projected(a_proj: BaseGeometry, b_proj: BaseGeometry) -> float:
    """Linear length of boundary∩boundary for already-projected EPSG:5070 copies."""
    if a_proj.is_empty or b_proj.is_empty:
        return 0.0
    if not _bounds_overlap(a_proj, b_proj):
        return 0.0
    inter = a_proj.boundary.intersection(b_proj.boundary)
    return _linear_length_m(inter)


def shared_boundary_length_m(a_lonlat: BaseGeometry, b_lonlat: BaseGeometry) -> float:
    if a_lonlat.is_empty or b_lonlat.is_empty:
        return 0.0
    if a_lonlat.geom_type in _POINT_TYPES or b_lonlat.geom_type in _POINT_TYPES:
        return 0.0
    return shared_boundary_length_projected(
        computation_geometry(a_lonlat),
        computation_geometry(b_lonlat),
    )


def are_rook_neighbors(a_lonlat: BaseGeometry, b_lonlat: BaseGeometry) -> bool:
    return shared_boundary_length_m(a_lonlat, b_lonlat) > ROOK_MIN_SHARED_BOUNDARY_M


def rook_graph(geoms: Mapping[str, BaseGeometry]) -> dict[str, list[str]]:
    ids = list(geoms)
    projected = {key: computation_geometry(geoms[key]) for key in ids}
    neighbors: dict[str, list[str]] = {key: [] for key in ids}
    for i, left_id in enumerate(ids):
        left = projected[left_id]
        for right_id in ids[i + 1 :]:
            length = shared_boundary_length_projected(left, projected[right_id])
            if length > ROOK_MIN_SHARED_BOUNDARY_M:
                neighbors[left_id].append(right_id)
                neighbors[right_id].append(left_id)
    for key in neighbors:
        neighbors[key].sort()
    return neighbors


def build_distance_adjacency(
    geoms: Mapping[str, BaseGeometry],
    *,
    max_distance_m: float,
) -> dict[str, list[str]]:
    raise DistanceAdjacencyFallbackError(
        "nearest-distance / max_distance_m adjacency is not rook and is not permitted "
        f"(max_distance_m={max_distance_m}, n={len(geoms)})."
    )


def build_buffered_adjacency(
    geoms: Mapping[str, BaseGeometry],
    *,
    buffer_m: float,
) -> dict[str, list[str]]:
    raise DistanceAdjacencyFallbackError(
        "buffered / buffer_m adjacency is not rook and is not permitted "
        f"(buffer_m={buffer_m}, n={len(geoms)})."
    )
