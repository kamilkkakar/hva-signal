"""Bounded selected-time live POST — cache-first, vendor refuse on miss."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.domain.multicity.type1_live import Type1LiveClientRequest, seed_type1_live_cache
from app.integrations.fortyguard.cache import FortyGuardCache
from app.main import app


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_bounded_live_disabled_by_default() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/live/selected-time",
        json={"city_id": "phoenix", "local_datetime": "2024-07-08T15:00:00"},
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "bounded_selected_time_live_disabled"
    assert "GENERAL" in detail["message"]


def test_bounded_live_rejects_server_owned_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.post(
        "/api/v1/live/selected-time",
        json={
            "city_id": "phoenix",
            "local_datetime": "2024-07-08T15:00:00",
            "polygon_aoi": {"type": "Polygon", "coordinates": []},
        },
    )
    assert response.status_code == 422


def test_bounded_live_cache_hit_zero_vendor(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "fg-cache"))
    get_settings.cache_clear()
    cache = FortyGuardCache(tmp_path / "fg-cache")
    request = Type1LiveClientRequest(
        city="Phoenix",
        target_local=datetime(2024, 7, 8, 15, 0, 0),
    )
    seed_type1_live_cache(
        request,
        payload={"summary": {"status": "cached_ok"}, "key": "should-not-leak"},
        cache=cache,
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/live/selected-time",
        json={"city_id": "phoenix", "local_datetime": "2024-07-08T15:00:00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cache_hit"
    assert body["provenance"]["vendor_attempted"] is False
    assert body["provenance"]["acquisition_language"] == "cache_hit"
    blob = response.text
    assert "should-not-leak" not in blob
    assert "FORTYGUARD_API_KEY" not in blob


def test_bounded_live_cache_miss_refuses_vendor(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "empty-cache"))
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.post(
        "/api/v1/live/selected-time",
        json={"city_id": "tucson", "local_datetime": "2024-07-08T15:00:00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "acquisition_unavailable"
    assert body["provenance"]["vendor_attempted"] is False
    assert "No FortyGuard Type-1 request was made" in body["message"]


def test_settings_defaults_keep_bounded_off() -> None:
    fields = Settings.model_fields
    assert fields["bounded_selected_time_live_enabled"].default is False
    assert int(fields["bounded_selected_time_daily_limit"].default) == 20
