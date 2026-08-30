"""Normalize held/cached zone snapshots into T-B types.

source_mode=cache. No HTTP. No second FortyGuard call.
Downtown 0/25 is spatial INSUFFICIENT, not a day of zeros.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from app.domain.enums import HeatmapTemporalMode, ThermalDataSource
from app.domain.phoenix_v1 import (
    EXPECTED_ZONE_COUNT,
    THERMAL_AGGREGATION_VERSION,
    ZONE_GEOMETRY_VERSION,
)
from app.domain.signals import SelectedTimeSnapshot
from app.domain.temporal import (
    AnalysisGeography,
    Comparability,
    CoverageStatus,
    ObservationGeometry,
    ObservationKind,
    Quality,
    SamplingDesign,
    SpatialScope,
    TemperatureQuantity,
    ThermalStatistic,
    TemporalCoverage,
    TemporalCoverageClass,
    TemporalProvenance,
    TemporalSourceFamily,
    TemporalSourceMode,
    ZoneThermalObservation,
    local_to_utc,
)
from app.services.temporal_coverage import classify_spatial
from app.services.temporal_source import stamp_from_thermal_data_source
from app.services.zone_aggregator import aggregate_tiles_to_zones
from app.domain.aggregation import default_thermal_aggregation_spec

CACHED_ACTIVITY_ID = "e0244934-0840-4072-bcb6-96cca26a9a20"
CACHED_FINGERPRINT = "d83bde1d8e3e7807d67571a8a164c5767ac744c5b125fdfed8fbb1e890813c1d"
PHOENIX_GEOMETRY_SHA256 = "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"
DOWNTOWN_FIXTURE_NOTE = "downtown_0_25_not_a_day"


def _geography(
    area_id: str,
    zone_geometry_version: str,
    geometry_sha256: str | None,
) -> AnalysisGeography:
    return AnalysisGeography(
        area_id=area_id,
        zone_geometry_version=zone_geometry_version,
        geometry_sha256=geometry_sha256,
        expected_zone_count=25,
        zone_id_property="GEOID",
    )


def _slot_coverage(
    *,
    area_id: str,
    zone_id: str,
    present: bool,
    source_mode: TemporalSourceMode,
    geometry_version: str,
    aggregation_version: str,
    window_id: str,
    spatial_class: TemporalCoverageClass | None,
    missing_zone_ids: list[str],
    downtown: bool,
) -> TemporalCoverage:
    flags = [DOWNTOWN_FIXTURE_NOTE] if downtown else []
    return TemporalCoverage(
        area_id=area_id,
        zone_id=zone_id,
        spatial_scope=SpatialScope.ZONE,
        coverage_class=TemporalCoverageClass.FULL if present else TemporalCoverageClass.INSUFFICIENT,
        spatial_coverage_class=spatial_class,
        comparability=Comparability.NOT_APPLICABLE,
        sampling_design=SamplingDesign.ANCHOR_0300,
        window_id=window_id,
        source_mode=source_mode,
        temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
        n_present=1 if present else 0,
        n_expected=1,
        n_valid_zones=1 if present else 0,
        interpolated=False,
        silent_fill=False,
        geometry_version=geometry_version,
        aggregation_version=aggregation_version,
        missing_slot_ids=[] if present else [window_id],
        missing_zone_ids=list(missing_zone_ids),
        quality_flags=flags,
    )


def normalize_snapshot(
    snapshot: SelectedTimeSnapshot,
    *,
    source_mode: TemporalSourceMode | None = None,
    activity_id: str | None = None,
    request_fingerprint: str | None = None,
    sampling_design: SamplingDesign = SamplingDesign.ANCHOR_0300,
) -> list[ZoneThermalObservation]:
    """Map an already-joined snapshot. No vendor I/O."""
    thermal_source = snapshot.provenance.source
    if thermal_source is None:
        thermal_source = ThermalDataSource.REPLAY
    stamp = stamp_from_thermal_data_source(
        thermal_source.value if hasattr(thermal_source, "value") else str(thermal_source),
        data_status=snapshot.provenance.data_status.value
        if snapshot.provenance.data_status is not None
        else None,
    )
    mode = source_mode or stamp.source_mode
    if mode is TemporalSourceMode.CACHE:
        stamp = stamp_from_thermal_data_source("fortyguard_cached", data_status="cached")
    elif mode is TemporalSourceMode.LIVE:
        stamp = stamp_from_thermal_data_source("fortyguard_live", data_status="live")
    elif mode is TemporalSourceMode.REPLAY:
        stamp = stamp_from_thermal_data_source("replay", data_status="replay")
    local = snapshot.target_timestamp
    if local.tzinfo is not None:
        raise ValueError("snapshot target_timestamp must be AOI-local naive")
    utc = local_to_utc(local, snapshot.timezone)
    geometry_version = snapshot.provenance.geometry_version or ZONE_GEOMETRY_VERSION
    aggregation = snapshot.aggregation_spec_version
    geo = _geography(snapshot.area_id, geometry_version, snapshot.geometry_sha256)
    n_valid = snapshot.valid_zone_count if snapshot.valid_zone_count is not None else sum(
        1 for zone in snapshot.zones if zone.mean_temperature_c is not None
    )
    spatial = classify_spatial(n_valid, snapshot.expected_zone_count or EXPECTED_ZONE_COUNT)
    downtown = n_valid == 0 or DOWNTOWN_FIXTURE_NOTE in snapshot.quality_flags
    window_id = f"SLOT:{local.strftime('%Y-%m-%dT%H:%M:%S')}"
    rows: list[ZoneThermalObservation] = []
    for zone in snapshot.zones:
        present = zone.mean_temperature_c is not None
        status = CoverageStatus.OK if present else CoverageStatus.INSUFFICIENT_EVIDENCE
        provenance = TemporalProvenance(
            source_mode=mode,
            source_family=stamp.source_family,
            source_dataset="fortyguard_tcm",
            thermal_data_source=stamp.thermal_data_source,  # type: ignore[arg-type]
            data_status=stamp.data_status,  # type: ignore[arg-type]
            temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
            analytic="tcm",
            timezone=snapshot.timezone,
            geometry_version=geometry_version,
            geometry_sha256=snapshot.geometry_sha256,
            aggregation_spec_version=aggregation,
            request_fingerprint=request_fingerprint,
            vendor_request_fingerprint=snapshot.provenance.vendor_request_fingerprint,
            activity_id=activity_id,
            reference_version=None,
            notes=["normalized from SelectedTimeSnapshot; no HTTP"],
        )
        rows.append(
            ZoneThermalObservation(
                area_id=snapshot.area_id,
                zone_id=zone.zone_id,
                valid_time_local=local,
                valid_time_utc=utc,
                timezone=snapshot.timezone,
                local_date=local.date(),
                local_hour=local.hour,
                temperature_c=zone.mean_temperature_c,
                temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
                statistic=ThermalStatistic.MEAN,
                observation_kind=ObservationKind.INSTANT,
                temporal_mode="single_hour",
                sampling_design=sampling_design,
                source_mode=mode,
                coverage_status=status,
                coverage=_slot_coverage(
                    area_id=snapshot.area_id,
                    zone_id=zone.zone_id,
                    present=present,
                    source_mode=mode,
                    geometry_version=geometry_version,
                    aggregation_version=aggregation,
                    window_id=window_id,
                    spatial_class=spatial,
                    missing_zone_ids=snapshot.missing_zone_ids,
                    downtown=downtown,
                ),
                analysis_geography=geo,
                observation_geometry=ObservationGeometry(
                    role="thermal_observation_only",
                    provider="fortyguard",
                    tile_resolution_m=100,
                    tile_count=zone.tile_count,
                    notes=["tiles are observation geometry only"],
                ),
                aggregation_spec_version=aggregation,
                quality=Quality(interpolated=False, silent_fill=False, flags=list(zone.quality_flags)),
                provenance=provenance,
            )
        )
    return rows


def normalize_cached_25zone_snapshot(
    snapshot: SelectedTimeSnapshot,
    *,
    activity_id: str = CACHED_ACTIVITY_ID,
    request_fingerprint: str = CACHED_FINGERPRINT,
) -> list[ZoneThermalObservation]:
    """T-K cache reuse path. LIVE CALL remains 0."""
    return normalize_snapshot(
        snapshot,
        source_mode=TemporalSourceMode.CACHE,
        activity_id=activity_id,
        request_fingerprint=request_fingerprint,
    )


def join_tiles_to_observations(
    *,
    zones_geojson: dict[str, Any],
    tiles_geojson: dict[str, Any],
    target_timestamp: datetime,
    timezone_name: str = "America/Phoenix",
    area_id: str = "phoenix-demo",
    source: ThermalDataSource = ThermalDataSource.REPLAY,
    zone_id_property: str = "GEOID",
    temperature_property: str = "average_temperature",
    activity_id: str | None = None,
    source_mode: TemporalSourceMode | None = None,
) -> list[ZoneThermalObservation]:
    """Centroid-within join then T-B normalize. Missing ≠ 0."""
    spec = default_thermal_aggregation_spec(THERMAL_AGGREGATION_VERSION)
    outcomes = aggregate_tiles_to_zones(
        zones_geojson,
        tiles_geojson,
        spec=spec,
        expected_tile_counts={},
        valid_time=target_timestamp,
        source=source,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        zone_id_property=zone_id_property,
        temperature_property=temperature_property,
    )
    from app.domain.enums import DataStatus
    from app.domain.signals import (
        SelectedTimeSnapshotZone,
        SignalAvailability,
        SignalProvenance,
        ThermalSignalKind,
    )

    zones = []
    missing = []
    valid = 0
    for outcome in outcomes:
        value = outcome.series.observations[0].value if outcome.series.observations else None
        if value is None:
            missing.append(outcome.series.zone_id)
        else:
            valid += 1
        zones.append(
            SelectedTimeSnapshotZone(
                zone_id=outcome.series.zone_id,
                mean_temperature_c=value,
                tile_count=outcome.series.tile_count,
                coverage_status="ok" if value is not None else "insufficient_evidence",
            )
        )
    availability = (
        SignalAvailability.READY
        if valid == EXPECTED_ZONE_COUNT
        else SignalAvailability.UNAVAILABLE
        if valid == 0
        else SignalAvailability.PARTIAL
    )
    data_status = {
        ThermalDataSource.REPLAY: DataStatus.REPLAY,
        ThermalDataSource.FORTYGUARD_CACHED: DataStatus.CACHED,
        ThermalDataSource.FORTYGUARD_LIVE: DataStatus.LIVE,
    }[source]
    snapshot = SelectedTimeSnapshot(
        area_id=area_id,
        target_timestamp=target_timestamp,
        timezone=timezone_name,
        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        availability=availability,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id=area_id,
            target_timestamp=target_timestamp,
            timezone=timezone_name,
            source=source,
            data_status=data_status,
            geometry_version=ZONE_GEOMETRY_VERSION,
        ),
        zones=zones,
        expected_zone_count=EXPECTED_ZONE_COUNT,
        valid_zone_count=valid,
        missing_zone_ids=missing,
        geometry_sha256=PHOENIX_GEOMETRY_SHA256,
        quality_flags=[DOWNTOWN_FIXTURE_NOTE] if valid == 0 else [],
    )
    mode = source_mode or (
        TemporalSourceMode.CACHE
        if source is ThermalDataSource.FORTYGUARD_CACHED
        else TemporalSourceMode.REPLAY
        if source is ThermalDataSource.REPLAY
        else TemporalSourceMode.LIVE
    )
    return normalize_snapshot(snapshot, source_mode=mode, activity_id=activity_id)


def spatial_class_from_observations(rows: Iterable[ZoneThermalObservation]) -> TemporalCoverageClass:
    valid = sum(1 for row in rows if row.temperature_c is not None)
    return classify_spatial(valid)
