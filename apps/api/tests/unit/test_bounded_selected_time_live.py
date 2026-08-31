"""Bounded selected-time live — GENERAL refuse vs narrow construction path."""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.hosted_live_policy import (
    HostedLiveDisabledError,
    may_construct_real_vendor,
    refuse_real_vendor,
)
from app.domain.multicity.type1_live import (
    Type1LiveClientRequest,
    construct_bounded_selected_time_http_client,
    construct_vendor_stage,
    run_type1_live,
    seed_type1_live_cache,
)
from app.integrations.fortyguard.cache import FortyGuardCache
from app.integrations.fortyguard.client import FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import MissingApiKeyError
from app.main import app

SECRET_VALUE = "unit-test-fortyguard-secret-never-leak"


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


def test_bounded_live_rejects_arbitrary_provider_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    get_settings.cache_clear()
    client = TestClient(app)
    for field, value in (
        ("fortyguard_api_key", SECRET_VALUE),
        ("api_key", SECRET_VALUE),
        ("provider_url", "https://evil.example"),
        ("base_url", "https://evil.example"),
        ("key_alias", "PRIMARY"),
        ("data_mode", "LIVE"),
    ):
        response = client.post(
            "/api/v1/live/selected-time",
            json={
                "city_id": "tucson",
                "local_datetime": "2024-07-08T03:00:00",
                field: value,
            },
        )
        assert response.status_code == 422, field
        assert SECRET_VALUE not in response.text


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


def test_bounded_live_cache_miss_missing_secret_safe_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "empty-cache"))
    monkeypatch.setenv("FORTYGUARD_API_KEY", "")
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
    assert SECRET_VALUE not in response.text


def test_settings_defaults_keep_bounded_off() -> None:
    fields = Settings.model_fields
    assert fields["bounded_selected_time_live_enabled"].default is False
    assert int(fields["bounded_selected_time_daily_limit"].default) == 20


def test_general_vendor_always_refused_even_with_flags() -> None:
    assert may_construct_real_vendor() is False
    opened = Settings.model_construct(
        hosted_live_enabled=True,
        hosted_live_real_vendor_enabled=True,
        bounded_selected_time_live_enabled=True,
        fortyguard_api_key=SECRET_VALUE,
    )
    assert may_construct_real_vendor(opened) is False
    with pytest.raises(HostedLiveDisabledError):
        refuse_real_vendor(opened)
    with pytest.raises(HostedLiveDisabledError):
        construct_vendor_stage(settings=opened)


def test_bounded_constructs_only_when_gate_true() -> None:
    closed = Settings.model_construct(
        bounded_selected_time_live_enabled=False,
        fortyguard_api_key=SECRET_VALUE,
    )
    with pytest.raises(HostedLiveDisabledError):
        construct_bounded_selected_time_http_client(settings=closed)

    opened = Settings.model_construct(
        bounded_selected_time_live_enabled=True,
        fortyguard_api_key=SECRET_VALUE,
        fortyguard_base_url="https://api.fortyguard.com",
    )
    client = construct_bounded_selected_time_http_client(settings=opened)
    assert isinstance(client, FortyGuardHttpClient)
    client.close()
    # Construction object must not expose the secret via repr/str of Settings dumps.
    dumped = opened.model_dump()
    # Settings may include the key in model_dump — public responses must not.
    assert dumped.get("fortyguard_api_key") == SECRET_VALUE


def test_bounded_construct_missing_secret_raises() -> None:
    settings = Settings.model_construct(
        bounded_selected_time_live_enabled=True,
        fortyguard_api_key="",
    )
    with pytest.raises(MissingApiKeyError):
        construct_bounded_selected_time_http_client(settings=settings)


def test_run_type1_live_without_bounded_auth_refuses_despite_gate(
    tmp_path,
) -> None:
    settings = Settings.model_construct(
        bounded_selected_time_live_enabled=True,
        fortyguard_api_key=SECRET_VALUE,
        cache_dir=str(tmp_path / "cache"),
    )
    cache = FortyGuardCache(tmp_path / "cache")
    with pytest.raises(HostedLiveDisabledError):
        run_type1_live(
            Type1LiveClientRequest(
                city="Las Vegas",
                target_local=datetime(2024, 7, 9, 3, 0, 0),
            ),
            cache=cache,
            settings=settings,
            bounded_selected_time_authorized=False,
        )


def test_run_type1_live_bounded_auth_acquires_with_mock_transport(
    tmp_path,
) -> None:
    calls = {"post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/heatmap":
            calls["post"] += 1
            assert request.headers.get("api-key") == SECRET_VALUE
            assert SECRET_VALUE not in request.url.path
            return httpx.Response(200, json={"data": {"activity_id": "act-bounded-1"}})
        if request.url.path == "/v1/status/act-bounded-1":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "status": "succeeded",
                        "result": {
                            "map_data": {"type": "FeatureCollection", "features": []},
                            "stats_data": {},
                        },
                    }
                },
            )
        return httpx.Response(500, text="unexpected")

    settings = Settings.model_construct(
        bounded_selected_time_live_enabled=True,
        fortyguard_api_key=SECRET_VALUE,
        fortyguard_base_url="https://api.fortyguard.com",
        cache_dir=str(tmp_path / "cache"),
    )
    cache = FortyGuardCache(tmp_path / "cache")
    result = run_type1_live(
        Type1LiveClientRequest(
            city="Las Vegas",
            target_local=datetime(2024, 7, 8, 3, 0, 0),
        ),
        cache=cache,
        settings=settings,
        bounded_selected_time_authorized=True,
        vendor_transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        poll_timeout=5.0,
    )
    assert result["status"] == "live_acquired"
    assert result["vendor_attempted"] is True
    assert calls["post"] == 1
    blob = str(result)
    assert SECRET_VALUE not in blob
    assert "fortyguard_api_key" not in blob.lower() or SECRET_VALUE not in blob

    # Identical request → cache hit, zero new vendor posts.
    second = run_type1_live(
        Type1LiveClientRequest(
            city="Las Vegas",
            target_local=datetime(2024, 7, 8, 3, 0, 0),
        ),
        cache=cache,
        settings=settings,
        bounded_selected_time_authorized=True,
        vendor_transport=httpx.MockTransport(handler),
        poll_interval=0.0,
    )
    assert second["status"] == "cache_hit"
    assert second["vendor_attempted"] is False
    assert calls["post"] == 1


def test_secret_never_serialized_on_live_route(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "seeded"))
    monkeypatch.setenv("FORTYGUARD_API_KEY", SECRET_VALUE)
    get_settings.cache_clear()
    cache = FortyGuardCache(tmp_path / "seeded")
    seed_type1_live_cache(
        Type1LiveClientRequest(
            city="Tucson",
            target_local=datetime(2024, 7, 8, 21, 0, 0),
        ),
        payload={"summary": {"ok": True}, "fortyguard_api_key": SECRET_VALUE},
        cache=cache,
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/live/selected-time",
        json={"city_id": "tucson", "local_datetime": "2024-07-08T21:00:00"},
    )
    assert response.status_code == 200
    assert SECRET_VALUE not in response.text
    assert "fortyguard_api_key" not in response.text.lower()
