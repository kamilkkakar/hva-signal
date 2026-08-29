"""Sanitized fixture loads, maps to tiles, and contains no api-key fields."""

from __future__ import annotations

import json
from typing import Any

from app.integrations.fortyguard.fingerprints import heatmap_fingerprint
from app.integrations.fortyguard.mapper import map_heatmap_result

from .helpers import HOURLY_TCM_FIXTURE, request_from_fixture

_SECRET_KEY_NAMES = {
    "api-key",
    "api_key",
    "authorization",
    "x-api-key",
    "fortyguard_api_key",
}


def _walk(obj: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.append(str(key))
            keys.extend(_walk(value))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_walk(item))
    return keys


def test_sanitized_fixture_file_exists() -> None:
    assert HOURLY_TCM_FIXTURE.is_file()


def test_fixture_has_no_api_key_fields(hourly_tcm_fixture: dict) -> None:
    keys = {k.lower() for k in _walk(hourly_tcm_fixture)}
    assert not (keys & _SECRET_KEY_NAMES)
    blob = json.dumps(hourly_tcm_fixture)
    for needle in ("api-key", "api_key", "Bearer ", "FORTYGUARD_API_KEY"):
        assert needle.lower() not in blob.lower()


def test_fixture_keeps_handful_of_tiles_and_stats(hourly_tcm_fixture: dict) -> None:
    features = hourly_tcm_fixture["result"]["map_data"]["features"]
    stats = hourly_tcm_fixture["result"]["stats_data"]
    assert 1 <= len(features) <= 8
    assert "temperature_stats" in stats
    assert "headers" not in hourly_tcm_fixture
    # Huge unused blobs stripped.
    assert "normal_temperature_distribution" not in stats
    assert "overall_temperature_distribution" not in stats


def test_sanitized_fixture_maps_to_tiles(hourly_tcm_fixture: dict) -> None:
    req = request_from_fixture(hourly_tcm_fixture)
    tiles = map_heatmap_result(
        hourly_tcm_fixture["result"],
        request=req,
        source="replay",
        partition_id="p0",
    )
    assert len(tiles) == len(hourly_tcm_fixture["result"]["map_data"]["features"])
    assert all(tile.geometry["type"] == "Polygon" for tile in tiles)


def test_fixture_fingerprint_matches_adapter_algorithm(hourly_tcm_fixture: dict) -> None:
    req = request_from_fixture(hourly_tcm_fixture)
    assert hourly_tcm_fixture["meta"]["fingerprint"] == heatmap_fingerprint(req)
