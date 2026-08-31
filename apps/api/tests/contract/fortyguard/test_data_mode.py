"""DataMode LIVE/REPLAY/AUTO labeling — replay is never labeled live."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.integrations.fortyguard.adapter import FortyGuardAdapter
from app.integrations.fortyguard.cache import FortyGuardCache
from app.integrations.fortyguard.exceptions import MissingApiKeyError
from app.integrations.fortyguard.transport_models import (
    DataMode,
    DataStatus,
    ThermalDataSource,
)

from .helpers import request_from_fixture


def test_replay_never_labeled_live(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    adapter = FortyGuardAdapter(
        api_key=None, fixture_dir=fixture_dir, cache_dir=tmp_path / "cache"
    )
    result = adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.REPLAY)
    )
    assert result.source == ThermalDataSource.REPLAY
    assert result.data_status == DataStatus.REPLAY
    assert result.source != ThermalDataSource.FORTYGUARD_LIVE
    assert result.data_status != DataStatus.LIVE
    assert result.data_mode_requested == DataMode.REPLAY


def test_auto_without_key_falls_back_to_replay_not_live(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    adapter = FortyGuardAdapter(
        api_key=None, fixture_dir=fixture_dir, cache_dir=tmp_path / "cache"
    )
    result = adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.AUTO)
    )
    assert result.source == ThermalDataSource.REPLAY
    assert result.data_status == DataStatus.REPLAY
    assert result.data_status != DataStatus.LIVE
    assert result.source != ThermalDataSource.FORTYGUARD_LIVE


def test_auto_cache_hit_labeled_cached_not_live(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    cache = FortyGuardCache(tmp_path / "fg-cache")
    adapter = FortyGuardAdapter(
        api_key=None,
        fixture_dir=fixture_dir,
        cache=cache,
    )
    req = request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.REPLAY)
    first = adapter.fetch_heatmap(req)
    cache.put(first.fingerprint, {"activity_id": "cached", "result": hourly_tcm_fixture["result"]})

    auto_adapter = FortyGuardAdapter(
        api_key=None,
        fixture_dir=fixture_dir,
        cache=cache,
    )
    cached = auto_adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.AUTO)
    )
    assert cached.source == ThermalDataSource.FORTYGUARD_CACHED
    assert cached.data_status == DataStatus.CACHED
    assert cached.data_status != DataStatus.LIVE
    assert cached.source != ThermalDataSource.FORTYGUARD_LIVE


def test_live_success_labeled_live(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/heatmap":
            return httpx.Response(200, json={"data": {"activity_id": "live-1"}})
        if request.url.path == "/v1/status/live-1":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "status": "succeeded",
                        "result": hourly_tcm_fixture["result"],
                    }
                },
            )
        return httpx.Response(500, text="unexpected")

    adapter = FortyGuardAdapter(
        api_key="test-key-not-real",
        fixture_dir=fixture_dir,
        cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        sleep=lambda _dt: None,
    )
    result = adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
    )
    assert result.source == ThermalDataSource.FORTYGUARD_LIVE
    assert result.data_status == DataStatus.LIVE


def test_auto_live_failure_falls_back_replay_not_live(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream down")

    adapter = FortyGuardAdapter(
        api_key="test-key-not-real",
        fixture_dir=fixture_dir,
        cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        sleep=lambda _dt: None,
    )
    result = adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.AUTO)
    )
    assert result.source == ThermalDataSource.REPLAY
    assert result.data_status == DataStatus.REPLAY
    assert result.data_status != DataStatus.LIVE


def test_live_mode_does_not_silently_use_replay(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    adapter = FortyGuardAdapter(
        api_key=None, fixture_dir=fixture_dir, cache_dir=tmp_path / "cache"
    )
    with pytest.raises(MissingApiKeyError):
        adapter.fetch_heatmap(
            request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
        )


def test_live_mode_cache_hit_zero_http_no_new_activity(
    hourly_tcm_fixture: dict, fixture_dir: Path, tmp_path: Path
) -> None:
    """Regression: DataMode.LIVE must be cache-first (duplicate-spend fix)."""
    calls = {"post": 0, "status": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/heatmap":
            calls["post"] += 1
            return httpx.Response(200, json={"data": {"activity_id": "live-seed-1"}})
        if request.url.path == "/v1/status/live-seed-1":
            calls["status"] += 1
            return httpx.Response(
                200,
                json={
                    "data": {
                        "status": "succeeded",
                        "result": hourly_tcm_fixture["result"],
                    }
                },
            )
        return httpx.Response(500, text="unexpected")

    cache = FortyGuardCache(tmp_path / "fg-cache")
    adapter = FortyGuardAdapter(
        api_key="test-key-not-real",
        fixture_dir=fixture_dir,
        cache=cache,
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        sleep=lambda _dt: None,
    )
    first = adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
    )
    assert first.source == ThermalDataSource.FORTYGUARD_LIVE
    assert calls["post"] == 1
    assert calls["status"] == 1

    # Identical LIVE request with seeded cache: zero new HTTP / no new activity.
    second = adapter.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
    )
    assert second.source == ThermalDataSource.FORTYGUARD_CACHED
    assert second.data_status == DataStatus.CACHED
    assert calls["post"] == 1
    assert calls["status"] == 1

    # Fresh adapter instance sharing the same cache still must not submit.
    other = FortyGuardAdapter(
        api_key="test-key-not-real",
        fixture_dir=fixture_dir,
        cache=cache,
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        sleep=lambda _dt: None,
    )
    third = other.fetch_heatmap(
        request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
    )
    assert third.source == ThermalDataSource.FORTYGUARD_CACHED
    assert calls["post"] == 1
    assert calls["status"] == 1
