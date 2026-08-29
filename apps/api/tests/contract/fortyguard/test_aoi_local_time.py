"""AOI-local time: adapter does not convert request time to UTC."""

from __future__ import annotations

from app.integrations.fortyguard.adapter import FortyGuardAdapter
from app.integrations.fortyguard.mapper import requested_valid_time
from app.integrations.fortyguard.temporal_modes import build_heatmap_payload

from .helpers import hourly_tcm_request, request_from_fixture


def test_payload_preserves_requested_start_time_string() -> None:
    req = hourly_tcm_request(start_time="15:00")
    payload = build_heatmap_payload(req)
    assert payload["date_time"]["start_time"] == "15:00"
    assert payload["date_time"]["start_date"] == "2024-07-15"
    serialized = str(payload["date_time"])
    assert "Z" not in payload["date_time"]["start_time"]
    assert "utc" not in serialized.lower()
    # Phoenix MST (UTC-7): 15:00 local would become 22:00 if converted.
    assert payload["date_time"]["start_time"] != "22:00"


def test_payload_preserves_aoi_local_0300_without_utc_conversion() -> None:
    """Gate 0 overnight protocol: adapter must issue 03:00 AOI-local, not another hour."""
    req = hourly_tcm_request(start_time="03:00")
    payload = build_heatmap_payload(req)
    assert payload["date_time"]["start_time"] == "03:00"
    assert payload["date_time"]["start_time"] != "10:00"  # UTC+7 shift
    assert "Z" not in payload["date_time"]["start_time"]
    valid = requested_valid_time("2024-07-15", "03:00")
    assert valid.tzinfo is None
    assert valid.hour == 3


def test_valid_time_is_naive_aoi_local_not_utc() -> None:
    valid = requested_valid_time("2024-07-15", "15:00")
    assert valid.tzinfo is None
    assert valid.hour == 15
    assert valid.minute == 0
    assert valid.year == 2024
    assert valid.month == 7
    assert valid.day == 15


def test_replay_fetch_preserves_start_time_on_upstream_payload(
    hourly_tcm_fixture: dict, fixture_dir
) -> None:
    adapter = FortyGuardAdapter(api_key=None, fixture_dir=fixture_dir)
    req = request_from_fixture(hourly_tcm_fixture, start_time="15:00")
    result = adapter.fetch_heatmap(req)
    assert result.upstream_payload["date_time"]["start_time"] == "15:00"
    assert all(obs.valid_time.tzinfo is None for tile in result.tiles for obs in tile.observations)
    assert all(obs.valid_time.hour == 15 for tile in result.tiles for obs in tile.observations)
