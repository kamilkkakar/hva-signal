from __future__ import annotations

from app.integrations.fortyguard.assembly import assemble_partitions
from app.integrations.fortyguard.mapper import map_heatmap_result
from app.integrations.fortyguard.transport_models import (
    DataStatus,
    PartitionFetch,
    ThermalDataSource,
)

from .helpers import request_from_fixture


def _tiles(hourly_tcm_fixture: dict, n: int = 2):
    req = request_from_fixture(hourly_tcm_fixture)
    slim = {
        "map_data": {
            "type": "FeatureCollection",
            "features": hourly_tcm_fixture["result"]["map_data"]["features"][:n],
        },
        "stats_data": hourly_tcm_fixture["result"]["stats_data"],
    }
    return map_heatmap_result(slim, request=req, source="replay", partition_id="p0")


def test_dedupes_overlapping_tile_ids(hourly_tcm_fixture: dict) -> None:
    tiles = _tiles(hourly_tcm_fixture, n=2)
    duplicate = tiles[0].model_copy(deep=True)
    mean = next(
        o
        for o in duplicate.observations
        if (o.statistic.value if hasattr(o.statistic, "value") else o.statistic) == "mean"
    )
    mean.value = 99.0
    assembled = assemble_partitions(
        [
            PartitionFetch(
                partition_id="p0",
                tiles=[tiles[0]],
                source=ThermalDataSource.REPLAY,
                stats_data={},
            ),
            PartitionFetch(
                partition_id="p1",
                tiles=[duplicate, tiles[1]],
                source=ThermalDataSource.REPLAY,
                stats_data={},
            ),
        ],
        expected_partition_ids=["p0", "p1"],
        data_mode_requested="replay",
        upstream_payload={},
        fingerprint="abc",
    )
    ids = [str(t.tile_id) for t in assembled.tiles]
    assert ids.count(str(tiles[0].tile_id)) == 1
    kept_mean = next(
        o.value
        for t in assembled.tiles
        if str(t.tile_id) == str(tiles[0].tile_id)
        for o in t.observations
        if (o.statistic.value if hasattr(o.statistic, "value") else o.statistic) == "mean"
    )
    assert kept_mean != 99.0


def test_missing_partition_is_partial(hourly_tcm_fixture: dict) -> None:
    tiles = _tiles(hourly_tcm_fixture, n=1)
    assembled = assemble_partitions(
        [
            PartitionFetch(
                partition_id="p0",
                tiles=tiles,
                source=ThermalDataSource.REPLAY,
                stats_data={},
            )
        ],
        expected_partition_ids=["p0", "p1"],
        data_mode_requested="replay",
        upstream_payload={},
        fingerprint="abc",
    )
    assert assembled.completeness == "partial"
    assert assembled.missing_partition_ids == ["p1"]
    assert assembled.data_status == DataStatus.PARTIAL
    assert assembled.source != ThermalDataSource.FORTYGUARD_LIVE
    assert any("missing_partition" in flag for flag in assembled.quality_flags)
