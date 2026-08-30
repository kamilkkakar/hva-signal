from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.core.area_registry import resolve_area_geography
from app.domain.enums import ThermalDataSource
from app.domain.phoenix_v1 import AREA_ID, EXPECTED_ZONE_COUNT
from app.domain.temporal import TemporalCoverageClass
from app.integrations.fortyguard.mapper import map_heatmap_result
from app.services.orchestrator import assembly_tiles_to_geojson
from app.services.temporal_coverage import classify_spatial
from app.services.temporal_normalize import DOWNTOWN_FIXTURE_NOTE, join_tiles_to_observations
from tests.contract.fortyguard.helpers import request_from_fixture
from tests.contract.temporal.conftest import TEMPORAL, require_synthetic_banner

DOWNTOWN = (
    Path(__file__).resolve().parent.parent / "fixtures" / "fortyguard" / "heatmap_tcm_hourly_1500.json"
)


def test_synthetic_tiles_on_real_geometry_join_25_of_25() -> None:
    require_synthetic_banner(TEMPORAL / "zones_25")
    geometry = json.loads(resolve_area_geography(AREA_ID).geometry_body.decode("utf-8"))
    tiles = json.loads((TEMPORAL / "zones_25" / "tiles_full_25.geojson").read_text(encoding="utf-8"))
    rows = join_tiles_to_observations(
        zones_geojson=geometry,
        tiles_geojson=tiles,
        target_timestamp=datetime(2024, 7, 15, 3, 0, 0),
        source=ThermalDataSource.REPLAY,
    )
    valid = [row for row in rows if row.temperature_c is not None]
    assert len(rows) == EXPECTED_ZONE_COUNT
    assert len(valid) == 25
    assert classify_spatial(len(valid)) is TemporalCoverageClass.FULL
    assert all(row.observation_geometry.role == "thermal_observation_only" for row in rows)


def test_downtown_held_fixture_is_negative_25_zone_case() -> None:
    doc = json.loads(DOWNTOWN.read_text(encoding="utf-8"))
    request = request_from_fixture(doc)
    tiles = map_heatmap_result(doc["result"], request=request, source="replay", partition_id="p0")
    tiles_geojson = assembly_tiles_to_geojson(tiles)
    geometry = json.loads(resolve_area_geography(AREA_ID).geometry_body.decode("utf-8"))
    rows = join_tiles_to_observations(
        zones_geojson=geometry,
        tiles_geojson=tiles_geojson,
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        source=ThermalDataSource.REPLAY,
    )
    valid = [row for row in rows if row.temperature_c is not None]
    assert len(rows) == EXPECTED_ZONE_COUNT
    assert len(valid) == 0
    assert classify_spatial(0) is TemporalCoverageClass.INSUFFICIENT
    assert all(row.temperature_c is None for row in rows)
    assert DOWNTOWN_FIXTURE_NOTE in rows[0].coverage.quality_flags
    assert 0.0 not in [row.temperature_c for row in rows]


def test_zero_tiles_are_insufficient_not_empty_success() -> None:
    require_synthetic_banner(TEMPORAL / "zones_25")
    geometry = json.loads(resolve_area_geography(AREA_ID).geometry_body.decode("utf-8"))
    tiles = json.loads((TEMPORAL / "zones_25" / "tiles_zero.geojson").read_text(encoding="utf-8"))
    rows = join_tiles_to_observations(
        zones_geojson=geometry,
        tiles_geojson=tiles,
        target_timestamp=datetime(2024, 7, 15, 3, 0, 0),
    )
    assert classify_spatial(sum(1 for row in rows if row.temperature_c is not None)) is TemporalCoverageClass.INSUFFICIENT
    assert all(row.temperature_c is None for row in rows)
