"""Contract cluster 3: ThermalObservation and ZoneThermalSeries."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain import (
    HeatmapTemporalMode,
    ThermalDataSource,
    ThermalObservation,
    ThermalStatistic,
    UpstreamTimeSemantics,
    ZoneThermalSeries,
)


def test_thermal_observation_field_names() -> None:
    assert set(ThermalObservation.model_fields) == {
        "valid_time",
        "statistic",
        "value",
        "quality_flags",
        "evidence_refs",
    }


def test_thermal_observation_allows_null_value() -> None:
    observation = ThermalObservation(
        valid_time=datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
        statistic=ThermalStatistic.MEAN,
        value=None,
    )
    assert observation.value is None
    assert observation.quality_flags == []
    assert observation.evidence_refs == []


def test_zone_thermal_series_field_names() -> None:
    assert set(ZoneThermalSeries.model_fields) == {
        "zone_id",
        "source",
        "temporal_mode",
        "upstream_time_semantics",
        "resolution_m",
        "aggregation_spec_version",
        "observations",
        "tile_count",
        "expected_tile_count",
        "tile_coverage_ratio",
        "evidence_refs",
        "quality_flags",
    }


def test_zone_thermal_series_stores_aoi_local_time() -> None:
    series = ZoneThermalSeries(
        zone_id="tract-001",
        source=ThermalDataSource.REPLAY,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        resolution_m=100,
        aggregation_spec_version="agg-v0",
        observations=[],
        tile_count=0,
        expected_tile_count=None,
        tile_coverage_ratio=None,
        evidence_refs=[],
        quality_flags=[],
    )
    assert series.upstream_time_semantics == UpstreamTimeSemantics.AOI_LOCAL_TIME
    assert series.upstream_time_semantics == "aoi_local_time"


def test_zone_thermal_series_resolution_must_be_60_80_100_or_none() -> None:
    kwargs = dict(
        zone_id="tract-001",
        source=ThermalDataSource.REPLAY,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        aggregation_spec_version="agg-v0",
        observations=[],
        tile_count=0,
        evidence_refs=[],
        quality_flags=[],
    )
    for resolution in (60, 80, 100, None):
        ZoneThermalSeries(resolution_m=resolution, **kwargs)

    with pytest.raises(ValidationError):
        ZoneThermalSeries(resolution_m=50, **kwargs)
