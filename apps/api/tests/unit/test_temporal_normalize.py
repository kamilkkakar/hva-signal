from __future__ import annotations

from datetime import datetime

from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.signals import (
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)
from app.domain.temporal import (
    TemperatureQuantity,
    TemporalSourceFamily,
    TemporalSourceMode,
    ZoneThermalObservation,
)
from app.services.temporal_normalize import normalize_snapshot
from app.services.temporal_source import stamp_public


def _snapshot(source: ThermalDataSource, status: DataStatus) -> SelectedTimeSnapshot:
    return SelectedTimeSnapshot(
        area_id="phoenix-demo",
        target_timestamp=datetime(2024, 7, 15, 3, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=SignalAvailability.READY,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id="phoenix-demo",
            target_timestamp=datetime(2024, 7, 15, 3, 0, 0),
            timezone="America/Phoenix",
            source=source,
            data_status=status,
            geometry_version="US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        ),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="04013107401",
                mean_temperature_c=33.5,
                tile_count=10,
                coverage_status="ok",
            )
        ],
        expected_zone_count=25,
        valid_zone_count=1,
        missing_zone_ids=[],
    )


def test_replay_cache_live_public_share_same_type() -> None:
    replay = normalize_snapshot(_snapshot(ThermalDataSource.REPLAY, DataStatus.REPLAY))
    cache = normalize_snapshot(
        _snapshot(ThermalDataSource.FORTYGUARD_CACHED, DataStatus.CACHED),
        source_mode=TemporalSourceMode.CACHE,
    )
    live = normalize_snapshot(
        _snapshot(ThermalDataSource.FORTYGUARD_LIVE, DataStatus.LIVE),
        source_mode=TemporalSourceMode.LIVE,
    )
    assert all(isinstance(row, ZoneThermalObservation) for row in replay + cache + live)
    assert replay[0].source_mode is TemporalSourceMode.REPLAY
    assert cache[0].source_mode is TemporalSourceMode.CACHE
    assert live[0].source_mode is TemporalSourceMode.LIVE
    public = stamp_public(acquire_mode="replay")
    assert public.temperature_quantity is TemperatureQuantity.PUBLIC_2M_AIR_ZONE_MEAN
    assert public.source_family is TemporalSourceFamily.PUBLIC
    assert replay[0].temperature_c == 33.5
    assert cache[0].quality.interpolated is False


def test_missing_stays_none() -> None:
    snap = _snapshot(ThermalDataSource.REPLAY, DataStatus.REPLAY)
    snap.zones[0].mean_temperature_c = None
    snap.zones[0].coverage_status = "insufficient_evidence"
    rows = normalize_snapshot(snap)
    assert rows[0].temperature_c is None
    assert rows[0].coverage_status.value != "ok"
