"""Tile→zone thermal aggregation (centroid-within assignment, mean statistic)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from shapely.geometry import shape

from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import (
    HeatmapTemporalMode,
    ThermalDataSource,
    ThermalStatistic,
    TileAssignmentMethod,
    UpstreamTimeSemantics,
    ZoneAggregationStatistic,
)
from app.domain.thermal import ThermalObservation, ZoneThermalSeries
from app.services.coverage import evaluate_coverage

__all__ = [
    "ThermalAggregationSpec",
    "ZoneAggregationOutcome",
    "aggregate_mean_temperature",
    "aggregate_tiles_to_zones",
    "assign_tiles_centroid_within",
]


@dataclass(frozen=True)
class ZoneAggregationOutcome:
    series: ZoneThermalSeries
    ranked: bool
    result_status: str


def aggregate_mean_temperature(values: list[float]) -> float | None:
    """Mean of assigned tile TCM values; no interpolation, no max/p90."""
    if not values:
        return None
    return sum(values) / len(values)


def _zone_id_from_feature(feature: dict[str, Any], zone_id_property: str) -> str:
    zone_id = feature.get("properties", {}).get(zone_id_property)
    if not zone_id:
        raise ValueError(f"Zone feature missing {zone_id_property!r}")
    return str(zone_id)


def assign_tiles_centroid_within(
    zones_geojson: dict[str, Any],
    tiles_geojson: dict[str, Any],
    *,
    zone_id_property: str = "zone_id",
    tile_id_property: str = "tile_id",
) -> dict[str, list[dict[str, Any]]]:
    """Assign tiles whose polygon centroid falls inside a zone polygon."""
    zone_polygons: list[tuple[str, Any]] = []
    for feature in zones_geojson.get("features", []):
        zone_id = _zone_id_from_feature(feature, zone_id_property)
        zone_polygons.append((zone_id, shape(feature["geometry"])))

    assignments: dict[str, list[dict[str, Any]]] = {
        zone_id: [] for zone_id, _ in zone_polygons
    }
    unassigned: list[dict[str, Any]] = []

    for tile in tiles_geojson.get("features", []):
        centroid = shape(tile["geometry"]).centroid
        matched_zone: str | None = None
        for zone_id, polygon in zone_polygons:
            if polygon.contains(centroid):
                matched_zone = zone_id
                break
        if matched_zone is None:
            unassigned.append(tile)
        else:
            assignments[matched_zone].append(tile)

    if unassigned:
        assignments["unassigned"] = unassigned
    return assignments


def _temperature_from_tile(
    tile: dict[str, Any],
    temperature_property: str,
) -> float | None:
    raw = tile.get("properties", {}).get(temperature_property)
    if raw is None:
        return None
    return float(raw)


def aggregate_tiles_to_zones(
    zones_geojson: dict[str, Any],
    tiles_geojson: dict[str, Any],
    *,
    spec: ThermalAggregationSpec,
    expected_tile_counts: dict[str, float],
    valid_time: datetime,
    source: ThermalDataSource = ThermalDataSource.REPLAY,
    temporal_mode: HeatmapTemporalMode = HeatmapTemporalMode.SINGLE_HOUR,
    upstream_time_semantics: UpstreamTimeSemantics = UpstreamTimeSemantics.AOI_LOCAL_TIME,
    resolution_m: Literal[60, 80, 100] | None = 100,
    zone_id_property: str = "zone_id",
    temperature_property: str = "average_temperature",
) -> list[ZoneAggregationOutcome]:
    """Aggregate tile TCM values to zones using centroid-within + mean."""
    if spec.assignment_method != TileAssignmentMethod.CENTROID_WITHIN:
        raise ValueError(f"Unsupported assignment method: {spec.assignment_method}")
    if spec.statistic != ZoneAggregationStatistic.MEAN:
        raise ValueError(f"Unsupported statistic: {spec.statistic}")

    assignments = assign_tiles_centroid_within(
        zones_geojson,
        tiles_geojson,
        zone_id_property=zone_id_property,
    )

    outcomes: list[ZoneAggregationOutcome] = []
    zone_ids = [
        _zone_id_from_feature(feature, zone_id_property)
        for feature in zones_geojson.get("features", [])
    ]

    for zone_id in zone_ids:
        assigned_tiles = assignments.get(zone_id, [])
        assigned_count = len(assigned_tiles)
        expected_count = expected_tile_counts.get(zone_id)
        coverage = evaluate_coverage(
            assigned_count,
            expected_count,
            spec.minimum_coverage_ratio,
            zero_tile_behavior=spec.zero_tile_behavior,
        )

        sampled_temps = [
            _temperature_from_tile(tile, temperature_property) for tile in assigned_tiles
        ]
        present_temps = [temp for temp in sampled_temps if temp is not None]
        missing_temp_count = len(sampled_temps) - len(present_temps)
        quality_flags = list(coverage.quality_flags)
        ranked = coverage.ranked
        result_status = coverage.result_status
        mean_value = aggregate_mean_temperature(present_temps)

        if assigned_count > 0 and not present_temps:
            mean_value = None
            ranked = False
            result_status = "insufficient_evidence"
            if "insufficient_evidence" not in quality_flags:
                quality_flags.append("insufficient_evidence")
        elif missing_temp_count:
            quality_flags.append("missing_tile_temperature")

        if result_status != "ok":
            mean_value = None

        observation = ThermalObservation(
            valid_time=valid_time,
            statistic=ThermalStatistic.MEAN,
            value=mean_value,
            quality_flags=list(quality_flags),
            evidence_refs=[
                str(tile.get("properties", {}).get("tile_id") or "")
                for tile in assigned_tiles
            ],
        )

        series = ZoneThermalSeries(
            zone_id=zone_id,
            source=source,
            temporal_mode=temporal_mode,
            upstream_time_semantics=upstream_time_semantics,
            resolution_m=resolution_m,
            aggregation_spec_version=spec.version,
            observations=[observation],
            tile_count=assigned_count,
            expected_tile_count=expected_count,
            tile_coverage_ratio=coverage.tile_coverage_ratio,
            evidence_refs=[],
            quality_flags=list(quality_flags),
        )
        outcomes.append(
            ZoneAggregationOutcome(
                series=series,
                ranked=ranked,
                result_status=result_status,
            )
        )

    return outcomes
