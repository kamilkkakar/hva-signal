"""R5 F1: refuse metres-as-degrees without editing national_geometry."""

from __future__ import annotations

import pytest
from shapely.geometry import Point, Polygon

from app.services.crs_bounds import (
    MetresAsDegreesError,
    lonlat_bounds_ok,
    refuse_metres_as_degrees,
    require_lonlat_bounds,
)


def test_projected_metres_are_rejected_as_official_rings() -> None:
    metres = Polygon(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0), (0.0, 0.0)]
    )
    with pytest.raises(MetresAsDegreesError, match="4269"):
        require_lonlat_bounds(metres)
    with pytest.raises(MetresAsDegreesError, match="metres cannot be treated as degrees"):
        refuse_metres_as_degrees(metres)


def test_conus_lonlat_rings_are_accepted() -> None:
    phoenix = Polygon(
        [
            (-112.1, 33.4),
            (-112.0, 33.4),
            (-112.0, 33.5),
            (-112.1, 33.5),
            (-112.1, 33.4),
        ]
    )
    require_lonlat_bounds(phoenix)
    refuse_metres_as_degrees(phoenix)


def test_empty_geometry_is_not_metres() -> None:
    require_lonlat_bounds(Point())


def test_lonlat_box_helper() -> None:
    assert lonlat_bounds_ok(-112.0, 33.0, -111.0, 34.0) is True
    assert lonlat_bounds_ok(-200.0, 33.0, -111.0, 34.0) is False
    assert lonlat_bounds_ok(0.0, 0.0, 1000.0, 1000.0) is False
