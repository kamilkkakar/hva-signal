"""Signal B processor reuses centroid-within mean. Tests only; not product data."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import (
    DataStatus,
    ThermalDataSource,
    TileAssignmentMethod,
    ZoneAggregationStatistic,
)
from app.domain.signals import SignalAvailability
from app.services.snapshot_processor import (
    SnapshotGeography,
    SnapshotProcessorError,
    process_selected_time_snapshot,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "zones"


def _spec() -> ThermalAggregationSpec:
    return ThermalAggregationSpec(
        version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
        statistic=ZoneAggregationStatistic.MEAN,
        minimum_coverage_ratio=None,
        zero_tile_behavior="insufficient_evidence",
        boundary_behavior="centroid_within_zone",
        notes=[],
    )


def _geography(zones: dict, *, sha: str = "a" * 64) -> SnapshotGeography:
    ids = tuple(str(f["properties"]["zone_id"]) for f in zones["features"])
    return SnapshotGeography(
        area_id="test-area",
        timezone="America/Phoenix",
        zone_geoids=ids,
        expected_zone_count=len(ids),
        aggregation_spec=_spec(),
        area_selection_policy_version="TEST_POLICY_V1",
        zone_geometry_version="TEST_GEOM_V1",
        geometry_sha256=sha,
        zones_geojson=zones,
        zone_id_property="zone_id",
    )


def _process(zones: dict, tiles: dict, **overrides: object):
    kwargs = {
        "geography": _geography(zones),
        "tiles_geojson": tiles,
        "target_timestamp": datetime(2024, 7, 15, 15, 0, 0),
        "source": ThermalDataSource.REPLAY,
        "data_status": DataStatus.REPLAY,
    }
    kwargs.update(overrides)
    return process_selected_time_snapshot(**kwargs)


def test_two_zone_success_is_deterministic_and_not_ranked() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    first = _process(zones, tiles)
    second = _process(zones, tiles)
    assert first.availability == SignalAvailability.READY
    assert first.units == "celsius"
    assert first.aggregation_method == "centroid_within_mean"
    assert first.aggregation_spec_version == "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
    assert first.target_timestamp == datetime(2024, 7, 15, 15, 0, 0)
    assert first.valid_zone_count == 2
    assert first.missing_zone_ids == []
    by_id = {zone.zone_id: zone for zone in first.zones}
    assert by_id["zone_a"].mean_temperature_c == pytest.approx(32.0)
    assert by_id["zone_b"].mean_temperature_c == pytest.approx(40.0)
    assert [zone.zone_id for zone in first.zones] == ["zone_a", "zone_b"]
    assert first.model_dump() == second.model_dump()
    dumped = first.model_dump()
    assert "q_A" not in dumped
    assert "thermal_ordering_permitted" not in dumped
    assert first.user_facing_tile_map is False


def test_zero_tiles_is_unavailable_unknown_not_zero() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = {"type": "FeatureCollection", "features": []}
    snapshot = _process(zones, tiles)
    assert snapshot.availability == SignalAvailability.UNAVAILABLE
    assert snapshot.valid_zone_count == 0
    assert set(snapshot.missing_zone_ids) == {"zone_a", "zone_b"}
    assert all(zone.mean_temperature_c is None for zone in snapshot.zones)
    assert all(zone.mean_temperature_c != 0 for zone in snapshot.zones)
    assert "missing_zone_unknown" in snapshot.quality_flags


def test_partial_snapshot_keeps_missing_zones_unknown() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    tiles["features"] = [
        feature
        for feature in tiles["features"]
        if feature["properties"]["tile_id"] in {"tile_a1", "tile_a2"}
    ]
    snapshot = _process(zones, tiles)
    assert snapshot.availability == SignalAvailability.PARTIAL
    by_id = {zone.zone_id: zone for zone in snapshot.zones}
    assert by_id["zone_a"].mean_temperature_c == pytest.approx(32.0)
    assert by_id["zone_b"].mean_temperature_c is None
    assert "zone_b" in snapshot.missing_zone_ids


def test_aware_timestamp_and_nonzero_minutes_are_rejected() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="naive"):
        _process(
            zones,
            tiles,
            target_timestamp=datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
        )
    with pytest.raises(ValueError, match="minutes"):
        _process(zones, tiles, target_timestamp=datetime(2024, 7, 15, 15, 10, 0))


def test_tile_valid_time_mismatch_fails_closed() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    tiles["features"][0]["properties"]["valid_time"] = "2024-07-15T03:00:00"
    with pytest.raises(SnapshotProcessorError, match="valid_time"):
        _process(zones, tiles)


def test_duplicate_tile_id_fails_closed() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    tiles["features"][1]["properties"]["tile_id"] = tiles["features"][0]["properties"]["tile_id"]
    with pytest.raises(SnapshotProcessorError, match="duplicate"):
        _process(zones, tiles)


def test_geometry_identity_mismatch_fails_closed() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    geo = _geography(zones)
    geo = SnapshotGeography(
        **{
            **geo.__dict__,
            "zone_geoids": ("other_a", "other_b"),
        }
    )
    with pytest.raises(SnapshotProcessorError, match="zone identifiers"):
        process_selected_time_snapshot(
            geography=geo,
            tiles_geojson=tiles,
            target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
            source=ThermalDataSource.REPLAY,
            data_status=DataStatus.REPLAY,
        )


def test_dst_gap_and_fold_are_rejected() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = {"type": "FeatureCollection", "features": []}
    geo = SnapshotGeography(**{**_geography(zones).__dict__, "timezone": "America/New_York"})
    with pytest.raises(SnapshotProcessorError, match="does not exist"):
        process_selected_time_snapshot(
            geography=geo,
            tiles_geojson=tiles,
            target_timestamp=datetime(2026, 3, 8, 2, 0, 0),
            source=ThermalDataSource.REPLAY,
            data_status=DataStatus.REPLAY,
        )
    with pytest.raises(SnapshotProcessorError, match="ambiguous"):
        process_selected_time_snapshot(
            geography=geo,
            tiles_geojson=tiles,
            target_timestamp=datetime(2026, 11, 1, 1, 0, 0),
            source=ThermalDataSource.REPLAY,
            data_status=DataStatus.REPLAY,
        )


def test_phoenix_transition_hours_are_unique() -> None:
    zones = json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))
    tiles = {"type": "FeatureCollection", "features": []}
    snapshot = process_selected_time_snapshot(
        geography=_geography(zones),
        tiles_geojson=tiles,
        target_timestamp=datetime(2026, 3, 8, 2, 0, 0),
        source=ThermalDataSource.REPLAY,
        data_status=DataStatus.REPLAY,
    )
    assert snapshot.target_timestamp == datetime(2026, 3, 8, 2, 0, 0)


def test_snapshot_processor_has_no_historical_imports() -> None:
    source = Path(
        Path(__file__).resolve().parents[2] / "app" / "services" / "snapshot_processor.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "app.services.hazard_spread",
        "app.services.phoenix_v1_thermal",
        "app.services.normalization",
        "app.core.phoenix_v1_area_config",
        "app.integrations.fortyguard.client",
        "app.integrations.fortyguard.adapter",
    }
    assert imported.isdisjoint(forbidden)
    assert "app.services.hazard_spread" not in source
    assert "app.services.phoenix_v1_thermal" not in source
    assert "app.integrations.fortyguard.client" not in source


def test_processor_sha_helper_is_stable() -> None:
    from app.services.snapshot_processor import geometry_sha256_hex

    body = b'{"type":"FeatureCollection","features":[]}'
    assert geometry_sha256_hex(body) == hashlib.sha256(body).hexdigest()
