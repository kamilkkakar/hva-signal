"""Internal selected-time snapshot processor.

Reuses centroid-within mean. Does not call a vendor, load a historical
reference, compute q_A, or run Decision 8.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import (
    DataStatus,
    HeatmapTemporalMode,
    ThermalDataSource,
    TileAssignmentMethod,
    UpstreamTimeSemantics,
    ZoneAggregationStatistic,
)
from app.domain.signals import (
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)
from app.services.aoi_timezone import AoiLocalTimeError
from app.services.snapshot_identity import require_dst_safe_requested_hour
from app.services.zone_aggregator import aggregate_tiles_to_zones

CENTROID_WITHIN_MEAN = "centroid_within_mean"


class SnapshotProcessorError(ValueError):
    """Illegal snapshot input. Missing zones are not coerced to zero."""


@dataclass(frozen=True)
class SnapshotGeography:
    """Geography assets required to aggregate a selected-time snapshot."""

    area_id: str
    timezone: str
    zone_geoids: tuple[str, ...]
    expected_zone_count: int
    aggregation_spec: ThermalAggregationSpec
    area_selection_policy_version: str
    zone_geometry_version: str
    geometry_sha256: str
    zones_geojson: dict[str, Any]
    zone_id_property: str = "GEOID"


def _statistic_name(statistic: Any) -> str:
    return statistic.value if hasattr(statistic, "value") else str(statistic)


def _require_centroid_within_mean(spec: ThermalAggregationSpec) -> None:
    if spec.assignment_method != TileAssignmentMethod.CENTROID_WITHIN:
        raise SnapshotProcessorError("Signal B must reuse centroid-within assignment")
    if spec.statistic != ZoneAggregationStatistic.MEAN:
        raise SnapshotProcessorError("Signal B must reuse mean aggregation")


def _geometry_feature_ids(zones_geojson: dict[str, Any], zone_id_property: str) -> list[str]:
    features = zones_geojson.get("features")
    if not isinstance(features, list):
        raise SnapshotProcessorError("zones GeoJSON must be a FeatureCollection")
    ids: list[str] = []
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            raise SnapshotProcessorError("invalid zone feature")
        if zone_id_property not in feature["properties"]:
            raise SnapshotProcessorError(f"zone feature missing {zone_id_property}")
        ids.append(str(feature["properties"][zone_id_property]))
    if len(ids) != len(set(ids)):
        raise SnapshotProcessorError("duplicate zone identifiers")
    return ids


def _require_unique_tile_ids(tiles_geojson: dict[str, Any]) -> None:
    ids: list[str] = []
    for feature in tiles_geojson.get("features") or []:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        raw = props.get("tile_id")
        if raw is None or str(raw) == "":
            raise SnapshotProcessorError("tile observation is missing tile_id")
        ids.append(str(raw))
    if len(ids) != len(set(ids)):
        raise SnapshotProcessorError("duplicate tile observation")


def _validate_observation_times(
    tiles_geojson: dict[str, Any],
    target: datetime,
) -> None:
    seen: set[str] = set()
    for feature in tiles_geojson.get("features") or []:
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            continue
        raw = feature["properties"].get("valid_time")
        if raw is None:
            continue
        if isinstance(raw, datetime):
            value = raw
        else:
            text = str(raw).replace("Z", "")
            value = datetime.fromisoformat(text)
        if value.tzinfo is not None:
            raise SnapshotProcessorError("tile valid_time must be AOI-local naive")
        if value != target:
            raise SnapshotProcessorError("tile valid_time does not match requested hour")
        seen.add(value.isoformat())
    if len(seen) > 1:
        raise SnapshotProcessorError("observations mix multiple requested timestamps")


def process_selected_time_snapshot(
    *,
    geography: SnapshotGeography,
    tiles_geojson: dict[str, Any],
    target_timestamp: datetime,
    source: ThermalDataSource,
    data_status: DataStatus,
    vendor_request_fingerprint: str | None = None,
) -> SelectedTimeSnapshot:
    """Aggregate mapped TCM tiles to zone-mean °C. Missing zones stay unknown."""
    try:
        target = require_dst_safe_requested_hour(target_timestamp, geography.timezone)
    except AoiLocalTimeError as exc:
        raise SnapshotProcessorError(str(exc)) from exc
    _require_centroid_within_mean(geography.aggregation_spec)
    if geography.expected_zone_count != len(geography.zone_geoids):
        raise SnapshotProcessorError("geography zone count is inconsistent")
    feature_ids = _geometry_feature_ids(geography.zones_geojson, geography.zone_id_property)
    if set(feature_ids) != set(geography.zone_geoids):
        raise SnapshotProcessorError("geometry zone identifiers do not match geography identity")
    if len(feature_ids) != geography.expected_zone_count:
        raise SnapshotProcessorError("geometry feature count does not match geography identity")
    if not geography.geometry_sha256:
        raise SnapshotProcessorError("geometry SHA-256 is required")
    if tiles_geojson.get("type") != "FeatureCollection":
        raise SnapshotProcessorError("tiles GeoJSON must be a FeatureCollection")
    _require_unique_tile_ids(tiles_geojson)
    _validate_observation_times(tiles_geojson, target)

    outcomes = aggregate_tiles_to_zones(
        zones_geojson=geography.zones_geojson,
        tiles_geojson=tiles_geojson,
        spec=geography.aggregation_spec,
        expected_tile_counts={},
        valid_time=target,
        source=source,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        resolution_m=100,
        zone_id_property=geography.zone_id_property,
        temperature_property="average_temperature",
    )

    zones: list[SelectedTimeSnapshotZone] = []
    for outcome in outcomes:
        mean = outcome.series.observations[0].value if outcome.series.observations else None
        status = outcome.result_status
        zones.append(
            SelectedTimeSnapshotZone(
                zone_id=outcome.series.zone_id,
                mean_temperature_c=mean,
                tile_count=outcome.series.tile_count,
                coverage_status=status,
                quality_flags=list(outcome.series.quality_flags),
            )
        )
    zones.sort(key=lambda item: item.zone_id)

    valid_ids = [zone.zone_id for zone in zones if zone.mean_temperature_c is not None]
    missing_ids = [zone.zone_id for zone in zones if zone.mean_temperature_c is None]
    expected = geography.expected_zone_count
    valid_count = len(valid_ids)
    if valid_count == expected and expected > 0:
        availability = SignalAvailability.READY
    elif valid_count == 0:
        availability = SignalAvailability.UNAVAILABLE
    else:
        availability = SignalAvailability.PARTIAL

    flags: list[str] = []
    if missing_ids:
        flags.append("missing_zone_unknown")
    if any(
        zone.mean_temperature_c is not None
        and zone.coverage_status != "ok"
        for zone in zones
    ):
        raise SnapshotProcessorError("unknown zones must not carry a temperature")

    provenance = SignalProvenance(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        area_id=geography.area_id,
        target_timestamp=target,
        timezone=geography.timezone,
        source=source,
        data_status=data_status,
        geometry_version=geography.zone_geometry_version,
        aggregation_spec_version=geography.aggregation_spec.version,
        vendor_request_fingerprint=vendor_request_fingerprint,
        notes=[
            "absolute zone-mean TCM average_temperature in celsius",
            "missing zones are unknown, not safe",
        ],
    )
    return SelectedTimeSnapshot(
        area_id=geography.area_id,
        target_timestamp=target,
        timezone=geography.timezone,
        aggregation_spec_version=geography.aggregation_spec.version,
        availability=availability,
        provenance=provenance,
        zones=zones,
        expected_zone_count=expected,
        valid_zone_count=valid_count,
        missing_zone_ids=missing_ids,
        geometry_sha256=geography.geometry_sha256,
        quality_flags=flags,
    )


def geometry_sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def snapshot_geography_from_resolved(geography: Any) -> SnapshotGeography:
    """Adapt a ResolvedAreaGeography to the processor input."""
    import json

    return SnapshotGeography(
        area_id=geography.manifest.area_id,
        timezone=geography.timezone,
        zone_geoids=geography.zone_geoids,
        expected_zone_count=len(geography.zone_geoids),
        aggregation_spec=geography.config.thermal_aggregation,
        area_selection_policy_version=geography.area_selection_policy_version,
        zone_geometry_version=geography.config.zone_geometry_version,
        geometry_sha256=geography.manifest.geometry_sha256,
        zones_geojson=json.loads(geography.geometry_body.decode("utf-8")),
        zone_id_property=geography.zone_id_property,
    )
