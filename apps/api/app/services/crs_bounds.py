"""Refuse metres-as-degrees without owning national_geometry.

Live ALG1 projection must not treat EPSG:5070 metres as lon/lat. This helper
is the fail-closed bounds check for that seam (R5 F1). Callers pass any object
with ``bounds`` / ``is_empty`` (Shapely geometries). No vendor I/O.
"""

from __future__ import annotations

from typing import Any, Protocol


class MetresAsDegreesError(ValueError):
    """Official rings are outside lon/lat; metres cannot be treated as degrees."""


class _HasBounds(Protocol):
    is_empty: bool
    bounds: tuple[float, float, float, float]


def lonlat_bounds_ok(minx: float, miny: float, maxx: float, maxy: float) -> bool:
    return (
        -180.0 <= minx <= 180.0
        and -180.0 <= maxx <= 180.0
        and -90.0 <= miny <= 90.0
        and -90.0 <= maxy <= 90.0
    )


def require_lonlat_bounds(geom: _HasBounds | Any) -> None:
    """Fail closed when rings cannot be official EPSG:4269 lon/lat."""
    if getattr(geom, "is_empty", False):
        return
    bounds = getattr(geom, "bounds", None)
    if bounds is None:
        raise MetresAsDegreesError(
            "official geometry must be EPSG:4269 lon/lat; "
            "analysis metres cannot be treated as degrees"
        )
    minx, miny, maxx, maxy = (float(part) for part in bounds)
    if not lonlat_bounds_ok(minx, miny, maxx, maxy):
        raise MetresAsDegreesError(
            "official geometry must be EPSG:4269 lon/lat; "
            "analysis metres cannot be treated as degrees"
        )


def refuse_metres_as_degrees(geom: _HasBounds | Any) -> None:
    """Alias used by projection entry points before Albers-projecting rings."""
    require_lonlat_bounds(geom)
