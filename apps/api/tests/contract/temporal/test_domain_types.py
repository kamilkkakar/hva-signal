from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.domain.temporal import (
    TEMPORAL_DOMAIN_CONTRACT_VERSION,
    AnalysisGeography,
    Comparability,
    CoverageStatus,
    ObservationGeometry,
    ObservationKind,
    Quality,
    SamplingDesign,
    SpatialScope,
    TemperatureQuantity,
    TemporalCoverage,
    TemporalCoverageClass,
    TemporalProvenance,
    TemporalSourceFamily,
    TemporalSourceMode,
    ThermalStatistic,
    ZoneThermalObservation,
    local_to_utc,
)


def _geo() -> AnalysisGeography:
    return AnalysisGeography(
        area_id="phoenix-demo",
        zone_geometry_version="US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        expected_zone_count=25,
        zone_id_property="GEOID",
    )


def _coverage(*, present: bool = True) -> TemporalCoverage:
    return TemporalCoverage(
        area_id="phoenix-demo",
        zone_id="04013107401",
        spatial_scope=SpatialScope.ZONE,
        coverage_class=TemporalCoverageClass.FULL if present else TemporalCoverageClass.INSUFFICIENT,
        sampling_design=SamplingDesign.ANCHOR_0300,
        window_id="SLOT:2024-07-15T03:00:00",
        source_mode=TemporalSourceMode.REPLAY,
        temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
        n_present=1 if present else 0,
        n_expected=1,
        interpolated=False,
        silent_fill=False,
        geometry_version="US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        aggregation_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    )


def _prov() -> TemporalProvenance:
    return TemporalProvenance(
        source_mode=TemporalSourceMode.REPLAY,
        source_family=TemporalSourceFamily.FORTYGUARD,
        thermal_data_source="replay",
        data_status="replay",
        temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
        analytic="tcm",
        timezone="America/Phoenix",
        geometry_version="US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    )


def test_present_observation_round_trip() -> None:
    local = datetime(2024, 7, 15, 3, 0, 0)
    obs = ZoneThermalObservation(
        area_id="phoenix-demo",
        zone_id="04013107401",
        valid_time_local=local,
        valid_time_utc=local_to_utc(local, "America/Phoenix"),
        timezone="America/Phoenix",
        local_date=date(2024, 7, 15),
        local_hour=3,
        temperature_c=31.55,
        temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
        statistic=ThermalStatistic.MEAN,
        observation_kind=ObservationKind.INSTANT,
        source_mode=TemporalSourceMode.REPLAY,
        coverage_status=CoverageStatus.OK,
        coverage=_coverage(),
        analysis_geography=_geo(),
        observation_geometry=ObservationGeometry(provider="fortyguard", tile_count=128),
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        quality=Quality(),
        provenance=_prov(),
    )
    assert obs.contract_version == TEMPORAL_DOMAIN_CONTRACT_VERSION
    assert obs.valid_time_utc == datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc)
    assert obs.quality.interpolated is False


def test_missing_cannot_be_zero() -> None:
    local = datetime(2024, 7, 15, 3, 0, 0)
    with pytest.raises(ValueError):
        ZoneThermalObservation(
            area_id="phoenix-demo",
            zone_id="04013107401",
            valid_time_local=local,
            valid_time_utc=local_to_utc(local, "America/Phoenix"),
            timezone="America/Phoenix",
            local_date=date(2024, 7, 15),
            local_hour=3,
            temperature_c=None,
            temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
            statistic=ThermalStatistic.MEAN,
            observation_kind=ObservationKind.INSTANT,
            source_mode=TemporalSourceMode.REPLAY,
            coverage_status=CoverageStatus.OK,
            coverage=_coverage(present=False),
            analysis_geography=_geo(),
            observation_geometry=ObservationGeometry(provider="fortyguard", tile_count=0),
            aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
            quality=Quality(),
            provenance=_prov(),
        )


def test_incomparable_is_not_a_coverage_class() -> None:
    assert "INCOMPARABLE" not in {item.value for item in TemporalCoverageClass}
    assert Comparability.INCOMPARABLE.value == "INCOMPARABLE"
