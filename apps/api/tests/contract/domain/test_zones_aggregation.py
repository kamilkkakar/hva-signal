"""Contract cluster 2: AnalysisZone, ThermalAggregationSpec, UpstreamPartition."""

import pytest
from pydantic import ValidationError

from app.domain import (
    AnalysisZone,
    ThermalAggregationSpec,
    TileAssignmentMethod,
    UpstreamPartition,
    ZoneAggregationStatistic,
    default_thermal_aggregation_spec,
)

POINT = {"type": "Point", "coordinates": [-112.07, 33.45]}


def test_analysis_zone_field_names() -> None:
    assert set(AnalysisZone.model_fields) == {
        "zone_id",
        "area_id",
        "geometry",
        "geometry_version",
        "display_name",
        "source",
        "source_resolution",
        "area_km2",
    }


def test_analysis_zone_accepts_geojson_geometry_dict() -> None:
    zone = AnalysisZone(
        zone_id="tract-001",
        area_id="phoenix-demo",
        geometry=POINT,
        geometry_version="geom-v0",
        source="tiger/line",
        area_km2=2.5,
    )
    assert zone.zone_id == "tract-001"
    assert zone.geometry["type"] == "Point"
    assert zone.display_name is None
    assert zone.source_resolution is None


def test_upstream_partition_field_names() -> None:
    assert set(UpstreamPartition.model_fields) == {
        "partition_id",
        "geometry",
        "request_fingerprint",
        "expected_zone_ids",
    }


def test_upstream_partition_construction() -> None:
    partition = UpstreamPartition(
        partition_id="p1",
        geometry=POINT,
        request_fingerprint="fp-1",
        expected_zone_ids=["tract-001"],
    )
    assert partition.expected_zone_ids == ["tract-001"]


def test_thermal_aggregation_spec_field_names() -> None:
    assert set(ThermalAggregationSpec.model_fields) == {
        "version",
        "assignment_method",
        "statistic",
        "minimum_coverage_ratio",
        "zero_tile_behavior",
        "boundary_behavior",
        "notes",
    }


def test_default_thermal_aggregation_spec_bias() -> None:
    spec = default_thermal_aggregation_spec(
        version="agg-v0",
        minimum_coverage_ratio=0.5,
    )
    assert spec.assignment_method == TileAssignmentMethod.CENTROID_WITHIN
    assert spec.statistic == ZoneAggregationStatistic.MEAN
    assert spec.zero_tile_behavior == "insufficient_evidence"
    assert spec.notes == []


def test_thermal_aggregation_rejects_unknown_zero_tile_behavior() -> None:
    with pytest.raises(ValidationError):
        ThermalAggregationSpec(
            version="agg-v0",
            assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
            statistic=ZoneAggregationStatistic.MEAN,
            minimum_coverage_ratio=0.5,
            zero_tile_behavior="interpolate",
            boundary_behavior="strict",
            notes=[],
        )
