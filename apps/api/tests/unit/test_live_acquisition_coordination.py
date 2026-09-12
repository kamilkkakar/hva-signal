"""Concurrent HTTP requests must not duplicate or oversubscribe acquisitions."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import bounded_selected_time_live as route
from app.core.config import Settings
from app.domain.multicity.type1_live import run_type1_live
from app.integrations.fortyguard.cache import FortyGuardCache
from app.main import app


@pytest.fixture
def acquisition(monkeypatch, tmp_path):
    settings = Settings.model_construct(
        app_env="coordination-test",
        bounded_selected_time_live_enabled=True,
        bounded_selected_time_daily_limit=1,
        fortyguard_api_key="test-only-key",
        cache_dir=str(tmp_path / "cache"),
    )
    entered, release, joined = Event(), Event(), Event()
    release.set()
    calls = []
    failure = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            joined.set()
            return super().result(timeout=timeout)

    def transport(request):
        calls.append(request.method)
        if request.method == "POST":
            entered.set()
            assert release.wait(5), "Test did not release the vendor submission"
            if failure:
                raise httpx.ReadTimeout("response lost", request=request)
            return httpx.Response(200, json={"data": {"activity_id": "test-activity"}})
        return httpx.Response(200, json={"data": {
            "status": "succeeded",
            "result": {
                "map_data": {"type": "FeatureCollection", "features": []},
                "stats_data": {},
            },
        }})

    def run(*args, **kwargs):
        return run_type1_live(
            *args, **kwargs, vendor_transport=httpx.MockTransport(transport),
            poll_interval=0, poll_timeout=1,
        )

    monkeypatch.setattr(route, "get_settings", lambda: settings)
    monkeypatch.setattr(route, "run_type1_live", run)
    monkeypatch.setattr(route, "Future", ObservedFuture)
    monkeypatch.setattr(route, "_attach_zone_analysis", lambda public, **_: public)
    monkeypatch.setattr(route, "_daily_counts", {})
    monkeypatch.setattr(route, "_inflight", {})

    def post(hour=3):
        with TestClient(app) as client:
            return client.post("/api/v1/live/selected-time", json={
                "city_id": "phoenix",
                "local_datetime": f"2024-07-08T{hour:02d}:00:00",
            })

    yield settings, entered, release, joined, calls, failure, post
    release.set()


def test_distinct_requests_cannot_oversubscribe(acquisition):
    settings, entered, release, _, calls, _, post = acquisition
    release.clear()
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(post)
        try:
            assert entered.wait(5)
            second = pool.submit(post, 4).result(timeout=5)
            assert second.status_code == 429
            assert second.json()["detail"]["used"] == 1
            assert calls == ["POST"]
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
    assert route._daily_counts[route._day_key(settings)] == 1


def test_identical_requests_share_one_acquisition(acquisition):
    settings, entered, release, joined, calls, _, post = acquisition
    release.clear()
    with ThreadPoolExecutor(2) as pool:
        owner = pool.submit(post)
        try:
            assert entered.wait(5)
            follower = pool.submit(post)
            assert joined.wait(5)
        finally:
            release.set()
        first, second = owner.result(timeout=5), follower.result(timeout=5)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == ["POST", "GET"]
    assert route._daily_counts[route._day_key(settings)] == 1


def test_waiter_timeout_keeps_owner_and_never_resubmits(acquisition, monkeypatch):
    settings, entered, release, _, calls, _, post = acquisition
    monkeypatch.setattr(route, "_flight_wait_seconds", 0)
    release.clear()
    with ThreadPoolExecutor(1) as pool:
        owner = pool.submit(post)
        try:
            assert entered.wait(5)
            for _ in range(2):
                response = post()
                assert response.status_code == 504
                assert response.json()["detail"]["code"] == "bounded_selected_time_in_progress"
            assert calls == ["POST"]
        finally:
            release.set()
        assert owner.result(timeout=5).status_code == 200
    assert post().json()["status"] == "cache_hit"
    assert calls == ["POST", "GET"]
    assert route._daily_counts[route._day_key(settings)] == 1


@pytest.mark.parametrize("vendor_cache_only", [False, True])
def test_exhausted_allowance_preserves_both_cache_tiers(
    acquisition, monkeypatch, tmp_path, vendor_cache_only,
):
    settings, _, _, _, calls, _, post = acquisition
    assert post().json()["status"] == "live_acquired"
    if vendor_cache_only:
        monkeypatch.setattr(route, "FortyGuardCache", lambda _: FortyGuardCache(tmp_path / "empty-outer"))
    settings.bounded_selected_time_daily_limit = 0
    replay = post()
    assert replay.status_code == 200
    assert replay.json()["status"] == "cache_hit"
    assert replay.json()["provenance"]["vendor_attempted"] is False
    assert post(4).status_code == 429
    assert calls == ["POST", "GET"]


def test_zero_allowance_blocks_first_purchase(acquisition):
    settings, _, _, _, calls, _, post = acquisition
    settings.bounded_selected_time_daily_limit = 0
    response = post()
    assert response.status_code == 429
    assert response.json()["detail"]["used"] == 0
    assert not calls
    assert not route._daily_counts


def test_unknown_submission_outcome_keeps_reservation(acquisition):
    settings, _, _, _, calls, failure, post = acquisition
    failure.append(True)
    response = post()
    assert response.status_code == 200
    assert response.json()["status"] == "acquisition_unavailable"
    assert response.json()["provenance"]["vendor_attempted"] is True
    assert post(4).status_code == 429
    assert calls == ["POST"]
    assert route._daily_counts[route._day_key(settings)] == 1


def test_missing_credential_does_not_consume_allowance(acquisition):
    settings, _, _, _, calls, _, post = acquisition
    settings.fortyguard_api_key = ""
    assert post().json()["provenance"]["vendor_attempted"] is False
    assert not calls
    assert not route._daily_counts


def test_owner_exception_is_shared_without_rerun(monkeypatch):
    entered, release, joined = Event(), Event(), Event()
    calls = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            joined.set()
            return super().result(timeout=timeout)

    monkeypatch.setattr(route, "Future", ObservedFuture)

    def fail():
        calls.append(1)
        entered.set()
        assert release.wait(5)
        raise TimeoutError("owner failed")

    with ThreadPoolExecutor(2) as pool:
        owner = pool.submit(route._with_single_flight, ("error",), fail)
        try:
            assert entered.wait(5)
            follower = pool.submit(route._with_single_flight, ("error",), fail)
            assert joined.wait(5)
        finally:
            release.set()
        for future in (owner, follower):
            with pytest.raises(TimeoutError, match="owner failed"):
                future.result(timeout=5)
    assert calls == [1]
    assert ("error",) not in route._inflight
