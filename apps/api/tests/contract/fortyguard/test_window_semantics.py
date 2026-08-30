"""Window temporal modes must not masquerade as SINGLE_HOUR instants."""

from __future__ import annotations

from datetime import datetime

from app.integrations.fortyguard.mapper import (
    WINDOW_AGGREGATE_FLAG,
    is_window_temporal_mode,
    map_heatmap_result,
    observation_claims_instant,
)
from app.integrations.fortyguard.transport_models import HeatmapTemporalMode

from .helpers import hourly_tcm_request, request_from_fixture


def _stats(tile) -> set[str]:
    names: set[str] = set()
    for obs in tile.observations:
        statistic = obs.statistic
        names.add(statistic.value if hasattr(statistic, "value") else str(statistic))
    return names


def test_single_hour_still_emits_instant_without_window_flags(
    hourly_tcm_fixture: dict,
) -> None:
    req = request_from_fixture(hourly_tcm_fixture)
    assert req.temporal_mode == HeatmapTemporalMode.SINGLE_HOUR
    tiles = map_heatmap_result(
        hourly_tcm_fixture["result"],
        request=req,
        source="replay",
        partition_id="p0",
    )
    assert tiles
    for tile in tiles:
        names = _stats(tile)
        assert names == {"mean", "min", "max", "instant"}
        for obs in tile.observations:
            assert WINDOW_AGGREGATE_FLAG not in obs.quality_flags
            assert not any(flag.startswith("window_start=") for flag in obs.quality_flags)
            assert not any(flag.startswith("window_end=") for flag in obs.quality_flags)
            assert obs.valid_time == datetime(2024, 7, 15, 15, 0, 0)
        instant = next(
            obs
            for obs in tile.observations
            if (obs.statistic.value if hasattr(obs.statistic, "value") else obs.statistic)
            == "instant"
        )
        assert observation_claims_instant(instant) is True


def test_hour_range_cannot_masquerade_as_instant(hourly_tcm_fixture: dict) -> None:
    req = hourly_tcm_request(
        temporal_mode=HeatmapTemporalMode.HOUR_RANGE,
        start_time="02:00",
        end_time="04:00",
        start_date="2024-07-15",
    )
    assert is_window_temporal_mode(req.temporal_mode) is True
    tiles = map_heatmap_result(
        hourly_tcm_fixture["result"],
        request=req,
        source="replay",
        partition_id="p0",
    )
    assert tiles
    for tile in tiles:
        assert "instant" not in _stats(tile)
        assert _stats(tile) == {"mean", "min", "max"}
        for obs in tile.observations:
            assert WINDOW_AGGREGATE_FLAG in obs.quality_flags
            assert "window_start=2024-07-15T02:00:00" in obs.quality_flags
            assert "window_end=2024-07-15T04:00:00" in obs.quality_flags
            assert observation_claims_instant(obs) is False


def test_day_range_cannot_masquerade_as_instant(hourly_tcm_fixture: dict) -> None:
    req = hourly_tcm_request(
        temporal_mode=HeatmapTemporalMode.DAY_RANGE,
        start_date="2024-07-15",
        start_time="00:00",
        end_date="2024-07-17",
        end_time="00:00",
    )
    tiles = map_heatmap_result(
        hourly_tcm_fixture["result"],
        request=req,
        source="replay",
        partition_id="p0",
    )
    assert tiles
    for tile in tiles:
        assert "instant" not in _stats(tile)
        for obs in tile.observations:
            assert WINDOW_AGGREGATE_FLAG in obs.quality_flags
            assert "window_start=2024-07-15T00:00:00" in obs.quality_flags
            assert "window_end=2024-07-17T00:00:00" in obs.quality_flags
            assert observation_claims_instant(obs) is False


def test_hour_range_without_end_time_is_still_a_window(hourly_tcm_fixture: dict) -> None:
    req = hourly_tcm_request(
        temporal_mode=HeatmapTemporalMode.HOUR_RANGE,
        start_time="02:00",
        end_time=None,
    )
    tiles = map_heatmap_result(
        hourly_tcm_fixture["result"],
        request=req,
        source="replay",
        partition_id="p0",
    )
    for tile in tiles:
        assert "instant" not in _stats(tile)
        for obs in tile.observations:
            assert "window_end=unspecified" in obs.quality_flags
            assert observation_claims_instant(obs) is False
