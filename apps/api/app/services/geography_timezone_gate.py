"""Wire frozen-candidate AOI timezone policy into resolve / materialize.

Does not change HVA_AOI_TIMEZONE_POLICY_V1_CANDIDATE. Lookup stays injected.
No public route. No FortyGuard. No paid or online timezone vendor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.domain.national_geography_package import NationalGeographyError
from app.services.aoi_timezone import (
    EXPECTED_ZONE_COUNT,
    AoiTimezoneResolutionError,
    LonLat,
    TimezoneFailureCode,
    TimezoneLookup,
    TimezoneResolution,
    resolve_aoi_timezone,
    try_timezonefinder_lookup,
)


class GeographyTimezoneError(NationalGeographyError):
    """Timezone policy failed; geography must not become SNAPSHOT_CAPABLE."""

    def __init__(self, code: TimezoneFailureCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def require_injected_timezone_lookup(
    lookup: TimezoneLookup | None,
) -> TimezoneLookup:
    """Fail closed when no offline lookup is available. Does not add a pip package."""
    if lookup is not None:
        return lookup
    found = try_timezonefinder_lookup()
    if found is not None:
        return found
    raise AoiTimezoneResolutionError(
        TimezoneFailureCode.TIMEZONE_NOT_FOUND,
        "AOI timezone lookup is unavailable; fail closed",
        point_timezones=(),
        distinct=(),
    )


def representative_points_from_geometries(
    geoids: Sequence[str],
    geometries: Mapping[str, BaseGeometry],
) -> tuple[LonLat, ...]:
    """Shapely representative_point per selected official ring (policy production rule)."""
    points: list[LonLat] = []
    for geoid in geoids:
        geom = geometries[geoid]
        if geom.is_empty:
            raise AoiTimezoneResolutionError(
                TimezoneFailureCode.TIMEZONE_NOT_FOUND,
                f"selected tract {geoid} has empty geometry; timezone cannot be resolved",
                point_timezones=(),
                distinct=(),
            )
        point = geom.representative_point()
        points.append(LonLat(float(point.x), float(point.y)))
    return tuple(points)


def representative_points_from_geojson(
    geometry: Mapping[str, Any],
    *,
    zone_geoids: Sequence[str],
    zone_id_property: str = "GEOID",
) -> tuple[LonLat, ...]:
    """Representative points from packaged WGS84 FeatureCollection, GEOID order given."""
    if geometry.get("type") != "FeatureCollection":
        raise ValueError("geometry must be a GeoJSON FeatureCollection")
    features = geometry.get("features")
    if not isinstance(features, list):
        raise ValueError("geometry features are required")
    by_id: dict[str, Mapping[str, Any]] = {}
    for feature in features:
        if not isinstance(feature, Mapping):
            raise ValueError("invalid GeoJSON feature")
        props = feature.get("properties")
        if not isinstance(props, Mapping) or zone_id_property not in props:
            raise ValueError(f"feature missing {zone_id_property}")
        by_id[str(props[zone_id_property])] = feature
    points: list[LonLat] = []
    for geoid in zone_geoids:
        feature = by_id.get(geoid)
        if feature is None:
            raise ValueError(f"geometry missing feature {geoid}")
        geom = shape(feature.get("geometry"))
        if geom.is_empty:
            raise AoiTimezoneResolutionError(
                TimezoneFailureCode.TIMEZONE_NOT_FOUND,
                f"selected tract {geoid} has empty geometry; timezone cannot be resolved",
                point_timezones=(),
                distinct=(),
            )
        point = geom.representative_point()
        points.append(LonLat(float(point.x), float(point.y)))
    return tuple(points)


def resolve_selected_geography_timezone(
    representative_points: Sequence[LonLat],
    lookup: TimezoneLookup | None,
    *,
    zone_ids: Sequence[str] | None = None,
    expected_zone_count: int = EXPECTED_ZONE_COUNT,
) -> TimezoneResolution:
    """Apply the frozen-candidate unanimity rule. Does not invent a timezone."""
    resolved_lookup = require_injected_timezone_lookup(lookup)
    return resolve_aoi_timezone(
        representative_points,
        resolved_lookup,
        expected_zone_count=expected_zone_count,
        zone_ids=zone_ids,
    )
