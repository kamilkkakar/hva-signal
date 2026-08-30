"""Offline processor contract using the tracked hourly TCM fixture.

This is not a claim that the downtown fixture covers all 25 Phoenix zones.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.core.area_registry import resolve_area_geography
from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.phoenix_v1 import AREA_ID
from app.domain.signals import SignalAvailability
from app.integrations.fortyguard.mapper import map_heatmap_result
from app.services.evidence_builder import build_selected_time_snapshot_evidence_graph
from app.services.orchestrator import assembly_tiles_to_geojson
from app.services.snapshot_processor import (
    process_selected_time_snapshot,
    snapshot_geography_from_resolved,
)

from tests.contract.fortyguard.helpers import request_from_fixture

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "fortyguard"
    / "heatmap_tcm_hourly_1500.json"
)


def test_held_hourly_fixture_on_phoenix_geography_is_a_processor_contract() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    request = request_from_fixture(doc)
    tiles = map_heatmap_result(
        doc["result"],
        request=request,
        source="replay",
        partition_id="p0",
    )
    tiles_geojson = assembly_tiles_to_geojson(tiles)
    geography = snapshot_geography_from_resolved(resolve_area_geography(AREA_ID))
    snapshot = process_selected_time_snapshot(
        geography=geography,
        tiles_geojson=tiles_geojson,
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        source=ThermalDataSource.REPLAY,
        data_status=DataStatus.REPLAY,
        vendor_request_fingerprint="held-hourly-tcm",
    )
    assert snapshot.expected_zone_count == 25
    assert len(snapshot.zones) == 25
    assert snapshot.units == "celsius"
    assert snapshot.timezone == "America/Phoenix"
    assert snapshot.user_facing_tile_map is False
    dumped = snapshot.model_dump()
    assert "q_A" not in dumped
    assert snapshot.provenance.reference_version is None
    # Downtown fixture is smaller than the 25-zone AOI.
    assert snapshot.availability in {
        SignalAvailability.PARTIAL,
        SignalAvailability.UNAVAILABLE,
        SignalAvailability.READY,
    }
    if snapshot.availability != SignalAvailability.READY:
        assert snapshot.missing_zone_ids
        assert all(
            zone.mean_temperature_c is None
            for zone in snapshot.zones
            if zone.zone_id in snapshot.missing_zone_ids
        )
    graph = build_selected_time_snapshot_evidence_graph(
        area_id=snapshot.area_id,
        geometry_version=snapshot.provenance.geometry_version or "",
        timezone=snapshot.timezone,
        target_timestamp="2024-07-15T15:00:00",
        source_type="replay",
        aggregation_spec_version=snapshot.aggregation_spec_version,
        zone_ids=[zone.zone_id for zone in snapshot.zones],
    )
    types = {node.type for node in graph.nodes}
    assert "decision1b_reference" not in types
    assert "hazard_spread" not in types
    assert "selected_time_snapshot" in types
