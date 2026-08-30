"""Rook adjacency: shared-boundary segment, not corner, not distance."""

from __future__ import annotations

import pytest
from shapely.geometry import MultiPolygon, Point, Polygon


def _box(lon0: float, lat0: float, lon1: float, lat1: float) -> Polygon:
    return Polygon(
        [
            (lon0, lat0),
            (lon1, lat0),
            (lon1, lat1),
            (lon0, lat1),
            (lon0, lat0),
        ]
    )


def test_shared_edge_is_rook() -> None:
    from app.services.rook_adjacency import are_rook_neighbors, shared_boundary_length_m

    left = _box(-112.10, 33.40, -112.09, 33.41)
    right = _box(-112.09, 33.40, -112.08, 33.41)
    assert are_rook_neighbors(left, right) is True
    assert shared_boundary_length_m(left, right) > 1.0


def test_corner_only_is_not_rook() -> None:
    from app.services.rook_adjacency import are_rook_neighbors, shared_boundary_length_m

    sw = _box(-112.10, 33.40, -112.09, 33.41)
    ne = _box(-112.09, 33.41, -112.08, 33.42)
    assert sw.touches(ne) is True
    assert sw.intersection(ne).geom_type in {"Point", "MultiPoint"}
    assert shared_boundary_length_m(sw, ne) == 0.0
    assert are_rook_neighbors(sw, ne) is False


def test_near_but_disjoint_is_not_rook() -> None:
    from app.services.rook_adjacency import are_rook_neighbors

    left = _box(-112.10, 33.40, -112.09, 33.41)
    near = _box(-112.089, 33.40, -112.079, 33.41)
    assert left.distance(near) > 0
    assert are_rook_neighbors(left, near) is False


def test_distance_adjacency_is_refused() -> None:
    from app.services.rook_adjacency import (
        DistanceAdjacencyFallbackError,
        build_buffered_adjacency,
        build_distance_adjacency,
    )

    geoms = {
        "A": _box(-112.10, 33.40, -112.09, 33.41),
        "B": _box(-112.07, 33.40, -112.06, 33.41),
    }
    with pytest.raises(DistanceAdjacencyFallbackError, match="distance"):
        build_distance_adjacency(geoms, max_distance_m=5000.0)
    with pytest.raises(DistanceAdjacencyFallbackError, match="buffer"):
        build_buffered_adjacency(geoms, buffer_m=10.0)


def test_multipolygon_shares_edge_on_one_part() -> None:
    from app.services.rook_adjacency import are_rook_neighbors

    mainland = _box(-112.10, 33.40, -112.09, 33.41)
    island = _box(-112.05, 33.40, -112.04, 33.41)
    multi = MultiPolygon([mainland, island])
    neighbor = _box(-112.09, 33.40, -112.08, 33.41)
    assert are_rook_neighbors(multi, neighbor) is True
    far = _box(-112.00, 33.40, -111.99, 33.41)
    assert are_rook_neighbors(multi, far) is False


def test_rook_graph_has_no_invented_edges() -> None:
    from app.services.rook_adjacency import rook_graph

    geoms = {
        "A": _box(-112.10, 33.40, -112.09, 33.41),
        "B": _box(-112.09, 33.40, -112.08, 33.41),
        "C": _box(-112.06, 33.40, -112.05, 33.41),
    }
    graph = rook_graph(geoms)
    assert graph["A"] == ["B"]
    assert graph["B"] == ["A"]
    assert graph["C"] == []
    assert set(graph) == {"A", "B", "C"}


def test_point_geometries_are_not_rook() -> None:
    from app.services.rook_adjacency import are_rook_neighbors

    poly = _box(-112.10, 33.40, -112.09, 33.41)
    assert are_rook_neighbors(poly, Point(-112.10, 33.40)) is False


def test_rook_floor_is_strictly_greater_than_one_millimetre() -> None:
    from app.services.rook_adjacency import (
        ROOK_MIN_SHARED_BOUNDARY_M,
        shared_boundary_length_projected,
    )

    assert ROOK_MIN_SHARED_BOUNDARY_M == 1e-3
    left = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0)])
    sub_mm = Polygon(
        [(100.0, 0.0), (200.0, 0.0), (200.0, 4e-4), (100.0, 4e-4), (100.0, 0.0)]
    )
    exact_mm = Polygon(
        [(100.0, 0.0), (200.0, 0.0), (200.0, 1e-3), (100.0, 1e-3), (100.0, 0.0)]
    )
    over_mm = Polygon(
        [(100.0, 0.0), (200.0, 0.0), (200.0, 2.0), (100.0, 2.0), (100.0, 0.0)]
    )
    assert shared_boundary_length_projected(left, sub_mm) < ROOK_MIN_SHARED_BOUNDARY_M
    assert shared_boundary_length_projected(left, exact_mm) == pytest.approx(1e-3)
    assert shared_boundary_length_projected(left, exact_mm) <= ROOK_MIN_SHARED_BOUNDARY_M
    assert shared_boundary_length_projected(left, over_mm) > ROOK_MIN_SHARED_BOUNDARY_M


def test_rook_graph_neighbors_are_geoid_sorted() -> None:
    from app.services.rook_adjacency import rook_graph

    geoms = {
        "04013107601": _box(-112.08, 33.40, -112.07, 33.41),
        "04013107401": _box(-112.10, 33.40, -112.09, 33.41),
        "04013107500": _box(-112.09, 33.40, -112.08, 33.41),
    }
    graph = rook_graph(geoms)
    assert graph["04013107500"] == ["04013107401", "04013107601"]
