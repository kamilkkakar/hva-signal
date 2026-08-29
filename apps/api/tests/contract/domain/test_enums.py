"""Contract cluster 1: architecture enumerations and status codes."""

from app.domain import (
    AnalysisMode,
    DataMode,
    DataStatus,
    HeatmapTemporalMode,
    JobStatus,
    ReferenceFrame,
    ResultStatus,
    SystemLimitationCode,
    ThermalDataSource,
    ThermalStatistic,
    TileAssignmentMethod,
    UpstreamTimeSemantics,
    ZoneAggregationStatistic,
)


def test_tile_assignment_method_names_and_values() -> None:
    assert TileAssignmentMethod.CENTROID_WITHIN == "centroid_within"
    assert TileAssignmentMethod.AREA_WEIGHTED == "area_weighted"
    assert {member.value for member in TileAssignmentMethod} == {
        "centroid_within",
        "area_weighted",
    }


def test_zone_aggregation_statistic_names_and_values() -> None:
    assert ZoneAggregationStatistic.MEAN == "mean"
    assert ZoneAggregationStatistic.P90 == "p90"
    assert ZoneAggregationStatistic.MAX == "max"
    assert {member.value for member in ZoneAggregationStatistic} == {"mean", "p90", "max"}


def test_thermal_statistic_names_and_values() -> None:
    assert ThermalStatistic.INSTANT == "instant"
    assert ThermalStatistic.MIN == "min"
    assert ThermalStatistic.MEAN == "mean"
    assert ThermalStatistic.MAX == "max"
    assert {member.value for member in ThermalStatistic} == {"instant", "min", "mean", "max"}


def test_upstream_time_semantics_is_aoi_local_time() -> None:
    assert UpstreamTimeSemantics.AOI_LOCAL_TIME == "aoi_local_time"
    assert {member.value for member in UpstreamTimeSemantics} == {"aoi_local_time"}


def test_heatmap_temporal_mode_names_and_values() -> None:
    assert HeatmapTemporalMode.SINGLE_HOUR == "single_hour"
    assert HeatmapTemporalMode.HOUR_RANGE == "hour_range"
    assert HeatmapTemporalMode.FULL_DAY == "full_day"
    assert HeatmapTemporalMode.DAY_RANGE == "day_range"
    assert HeatmapTemporalMode.MONTH == "month"
    assert {member.value for member in HeatmapTemporalMode} == {
        "single_hour",
        "hour_range",
        "full_day",
        "day_range",
        "month",
    }


def test_thermal_data_source_names_and_values() -> None:
    assert ThermalDataSource.FORTYGUARD_LIVE == "fortyguard_live"
    assert ThermalDataSource.FORTYGUARD_CACHED == "fortyguard_cached"
    assert ThermalDataSource.REPLAY == "replay"
    assert {member.value for member in ThermalDataSource} == {
        "fortyguard_live",
        "fortyguard_cached",
        "replay",
    }


def test_analysis_mode_names_and_values() -> None:
    assert AnalysisMode.OPERATIONAL == "operational"
    assert AnalysisMode.RETROSPECTIVE == "retrospective"
    assert {member.value for member in AnalysisMode} == {"operational", "retrospective"}


def test_data_mode_names_and_values() -> None:
    assert DataMode.LIVE == "live"
    assert DataMode.REPLAY == "replay"
    assert DataMode.AUTO == "auto"
    assert {member.value for member in DataMode} == {"live", "replay", "auto"}


def test_reference_frame_names_and_values() -> None:
    assert ReferenceFrame.ABSOLUTE == "absolute"
    assert ReferenceFrame.HISTORICAL == "historical"
    assert ReferenceFrame.RELATIVE == "relative"
    assert {member.value for member in ReferenceFrame} == {
        "absolute",
        "historical",
        "relative",
    }


def test_job_status_pipeline_lists_normalizing_before_hazard_spread() -> None:
    members = [status.value for status in JobStatus]
    assert members.index("normalizing") < members.index("validating_hazard_spread")


def test_job_status_includes_unknown_job() -> None:
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.LOADING_CONTEXT == "loading_context"
    assert JobStatus.FETCHING_THERMAL == "fetching_thermal"
    assert JobStatus.ASSEMBLING_PARTITIONS == "assembling_partitions"
    assert JobStatus.AGGREGATING_ZONES == "aggregating_zones"
    assert JobStatus.VALIDATING_HAZARD_SPREAD == "validating_hazard_spread"
    assert JobStatus.NORMALIZING == "normalizing"
    assert JobStatus.COMPUTING == "computing"
    assert JobStatus.COMPLETE == "complete"
    assert JobStatus.PARTIAL == "partial"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.UNKNOWN_JOB == "unknown_job"
    assert JobStatus.UNKNOWN_JOB.value == "unknown_job"
    assert {member.value for member in JobStatus} == {
        "queued",
        "loading_context",
        "fetching_thermal",
        "assembling_partitions",
        "aggregating_zones",
        "validating_hazard_spread",
        "normalizing",
        "computing",
        "complete",
        "partial",
        "failed",
        "unknown_job",
    }


def test_result_status_names_and_values() -> None:
    assert ResultStatus.OK == "ok"
    assert ResultStatus.INSUFFICIENT_EVIDENCE == "insufficient_evidence"
    assert ResultStatus.FAILED == "failed"
    assert ResultStatus.PARTIAL == "partial"
    assert {member.value for member in ResultStatus} == {
        "ok",
        "insufficient_evidence",
        "failed",
        "partial",
    }


def test_data_status_names_and_values() -> None:
    assert DataStatus.LIVE == "live"
    assert DataStatus.CACHED == "cached"
    assert DataStatus.REPLAY == "replay"
    assert DataStatus.PARTIAL == "partial"
    assert DataStatus.UNAVAILABLE == "unavailable"
    assert {member.value for member in DataStatus} == {
        "live",
        "cached",
        "replay",
        "partial",
        "unavailable",
    }


def test_system_limitation_includes_thermal_spatial_differentiation_insufficient() -> None:
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT
        == "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
    )
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        == "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
    )


def test_system_limitation_includes_insufficient_reference() -> None:
    assert SystemLimitationCode.INSUFFICIENT_REFERENCE == "INSUFFICIENT_REFERENCE"
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT
        != SystemLimitationCode.INSUFFICIENT_REFERENCE
    )
