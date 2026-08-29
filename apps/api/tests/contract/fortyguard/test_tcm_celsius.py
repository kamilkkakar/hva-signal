"""tcm tile temperatures are treated as Celsius (official docstring °F is wrong)."""

from __future__ import annotations

from app.integrations.fortyguard.mapper import map_heatmap_result

from .helpers import request_from_fixture


def test_tcm_values_pass_through_as_celsius(hourly_tcm_fixture: dict) -> None:
    req = request_from_fixture(hourly_tcm_fixture)
    raw_features = hourly_tcm_fixture["result"]["map_data"]["features"]
    tiles = map_heatmap_result(
        hourly_tcm_fixture["result"],
        request=req,
        source="replay",
        partition_id="p0",
    )
    assert tiles
    assert all(tile.temperature_unit == "celsius" for tile in tiles)
    for tile, feature in zip(tiles, raw_features, strict=True):
        props = feature["properties"]
        by_stat = {
            (obs.statistic.value if hasattr(obs.statistic, "value") else obs.statistic): obs.value
            for obs in tile.observations
        }
        assert by_stat["mean"] == props["average_temperature"]
        assert by_stat["min"] == props["min_temperature"]
        assert by_stat["max"] == props["max_temperature"]
        assert "tcm_unit:celsius" in tile.observations[0].quality_flags
        # Phoenix 15:00 July snapshot is ~40 C. A mistaken F→C conversion of 40
        # would yield ~4.4 C; treating 40 C as F would be physically absurd.
        assert 30.0 < props["average_temperature"] < 50.0
        assert 30.0 < by_stat["mean"] < 50.0
