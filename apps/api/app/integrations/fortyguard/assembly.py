"""Assemble multi-partition heatmap fetches: dedupe tiles, flag PARTIAL."""

from __future__ import annotations

from typing import Any

from app.integrations.fortyguard.transport_models import (
    ADAPTER_VERSION,
    AssemblyResult,
    DataMode,
    DataStatus,
    PartitionFetch,
    ThermalDataSource,
)


def _as_data_mode(value: DataMode | str) -> DataMode:
    if isinstance(value, DataMode):
        return value
    return DataMode(value)


def _overall(
    sources: list[ThermalDataSource],
    missing: list[str],
) -> tuple[ThermalDataSource, DataStatus, str]:
    if not sources and missing:
        return ThermalDataSource.REPLAY, DataStatus.UNAVAILABLE, "partial"
    unique = set(sources)
    if missing:
        completeness = "partial"
        data_status = DataStatus.PARTIAL
        if unique == {ThermalDataSource.FORTYGUARD_LIVE}:
            return ThermalDataSource.FORTYGUARD_LIVE, data_status, completeness
        if ThermalDataSource.REPLAY in unique:
            return ThermalDataSource.REPLAY, data_status, completeness
        if ThermalDataSource.FORTYGUARD_CACHED in unique:
            return ThermalDataSource.FORTYGUARD_CACHED, data_status, completeness
        return next(iter(unique)), data_status, completeness
    if unique == {ThermalDataSource.FORTYGUARD_LIVE}:
        return ThermalDataSource.FORTYGUARD_LIVE, DataStatus.LIVE, "complete"
    if unique == {ThermalDataSource.FORTYGUARD_CACHED}:
        return ThermalDataSource.FORTYGUARD_CACHED, DataStatus.CACHED, "complete"
    if unique == {ThermalDataSource.REPLAY}:
        return ThermalDataSource.REPLAY, DataStatus.REPLAY, "complete"
    # Mixed sources are never labeled live.
    if ThermalDataSource.REPLAY in unique:
        source = ThermalDataSource.REPLAY
    elif ThermalDataSource.FORTYGUARD_CACHED in unique:
        source = ThermalDataSource.FORTYGUARD_CACHED
    else:
        source = next(iter(unique))
    return source, DataStatus.PARTIAL, "partial"


def assemble_partitions(
    fetches: list[PartitionFetch],
    *,
    expected_partition_ids: list[str],
    data_mode_requested: DataMode | str,
    upstream_payload: dict[str, Any],
    fingerprint: str,
    adapter_version: str = ADAPTER_VERSION,
) -> AssemblyResult:
    by_id = {item.partition_id: item for item in fetches}
    tiles_by_id: dict[str, Any] = {}
    sources: list[ThermalDataSource] = []
    missing: list[str] = []
    stats_data: dict[str, Any] | None = None
    quality_flags: list[str] = []

    for partition_id in expected_partition_ids:
        item = by_id.get(partition_id)
        if item is None:
            missing.append(partition_id)
            quality_flags.append(f"missing_partition:{partition_id}")
            continue
        sources.append(item.source)
        if stats_data is None and item.stats_data:
            stats_data = item.stats_data
        for tile in item.tiles:
            key = str(tile.tile_id)
            if key not in tiles_by_id:
                tiles_by_id[key] = tile

    source, data_status, completeness = _overall(sources, missing)
    return AssemblyResult(
        tiles=list(tiles_by_id.values()),
        completeness=completeness,  # type: ignore[arg-type]
        missing_partition_ids=missing,
        source=source,
        data_status=data_status,
        data_mode_requested=_as_data_mode(data_mode_requested),
        upstream_payload=upstream_payload,
        fingerprint=fingerprint,
        adapter_version=adapter_version,
        stats_data=stats_data,
        quality_flags=quality_flags,
    )
