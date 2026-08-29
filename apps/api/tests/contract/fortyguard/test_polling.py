"""Status poll retries a brief 404, then succeeds."""

from __future__ import annotations

import httpx
import pytest

from app.integrations.fortyguard.client import FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import ActivityNotReadyError, TaskTimeoutError
from app.integrations.fortyguard.polling import wait_for


def test_wait_for_retries_404_then_succeeds() -> None:
    calls = {"n": 0}

    def get_status(_activity_id: str) -> dict:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ActivityNotReadyError("act-1")
        if calls["n"] == 2:
            return {"status": "running"}
        return {"status": "succeeded", "result": {"ok": True}}

    sleeps: list[float] = []
    result = wait_for(
        get_status,
        "act-1",
        poll_interval=0.01,
        timeout=5.0,
        sleep=sleeps.append,
    )
    assert result == {"ok": True}
    assert calls["n"] == 3
    assert sleeps


def test_client_get_status_404_is_not_ready() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/status/act-1":
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(404, json={"error": True, "message": "not found"})
            return httpx.Response(
                200,
                json={"data": {"status": "succeeded", "result": {"tiles": 1}}},
            )
        return httpx.Response(500, text="unexpected")

    client = FortyGuardHttpClient(
        api_key="test-key-not-real",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ActivityNotReadyError):
        client.get_status("act-1")
    body = client.get_status("act-1")
    assert body["status"] == "succeeded"


def test_submit_and_wait_retries_404_via_httpx() -> None:
    calls = {"status": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/heatmap":
            assert request.headers.get("api-key") == "test-key-not-real"
            assert request.headers.get("authorization") is None
            return httpx.Response(200, json={"data": {"activity_id": "act-1"}})
        if request.url.path == "/v1/status/act-1":
            calls["status"] += 1
            if calls["status"] == 1:
                return httpx.Response(404, text="not yet")
            return httpx.Response(
                200,
                json={
                    "data": {
                        "status": "completed",
                        "result": {"map_data": {"features": []}, "stats_data": {}},
                    }
                },
            )
        return httpx.Response(500, text="unexpected")

    client = FortyGuardHttpClient(
        api_key="test-key-not-real",
        transport=httpx.MockTransport(handler),
    )
    payload = client.submit_and_wait(
        "/v1/heatmap",
        {"polygon_aoi": {}, "date_time": {"start_date": "2024-07-15", "filter_type": 1}},
        poll_interval=0.0,
        timeout=5.0,
        sleep=lambda _dt: None,
    )
    assert payload["activity_id"] == "act-1"
    assert calls["status"] == 2


def test_wait_for_timeout_if_never_visible() -> None:
    clock = {"t": 0.0}

    def get_status(_activity_id: str) -> dict:
        raise ActivityNotReadyError("act-1")

    def sleep(dt: float) -> None:
        clock["t"] += dt

    with pytest.raises(TaskTimeoutError):
        wait_for(
            get_status,
            "act-1",
            poll_interval=1.0,
            timeout=2.5,
            sleep=sleep,
            monotonic=lambda: clock["t"],
        )
