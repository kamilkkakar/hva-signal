"""Anonymous availability guards. Spend stays impossible. No vendor I/O."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.anonymous_guards import (
    DEFAULT_ROUTE_LIMITS,
    PUBLIC_SERIALIZER_DENYLIST,
    REASON_CACHE_BYTE_CAP,
    REASON_CACHE_ENTRY_CAP,
    REASON_CLIENT_CACHE_KEY,
    REASON_JOB_QUOTA_CLASS,
    REASON_JOB_QUOTA_IN_FLIGHT,
    REASON_JOB_QUOTA_STORED,
    REASON_PUBLIC_VENDOR_CACHE_WRITE,
    REASON_RATE_LIMITED,
    AnonymousGuards,
    CacheCapPolicy,
    InProcessJobQuota,
    InProcessRateLimiter,
    RateLimitSpec,
    classify_route,
    client_class_from_headers,
    public_path_may_write_vendor_cache,
    public_payload_hits_denylist,
    spend_defaults_remain_closed,
    strip_denied_public_fields,
)
from app.core.geoid_format import (
    REASON_GEOID_STATE_MISMATCH,
    REASON_INVALID_PLACE_GEOID,
    REASON_INVALID_TRACT_GEOID,
    GeoidFormatError,
    is_place_geoid,
    is_tract_geoid,
    require_place_geoid,
    require_tract_for_place,
    require_tract_geoid,
    tract_state_matches_place,
)
from app.core.guard_middleware import (
    AnonymousGuardMiddleware,
    anonymous_guard_middleware_enabled,
)
from app.domain.demo_allowance import DemoAllowancePolicy, disabled_demo_policy
from app.domain.public_contract import PublicSpendView, TwoSignalPublicJob, WorkerHandoff
from app.domain.requests import AnalysisRequest
from app.services.orchestrator import run_replay_analysis
from app.services.public_contract_serialize import serialize_legacy_a_only_job


_OWNED_MODULES = (
    Path("app/core/anonymous_guards.py"),
    Path("app/core/geoid_format.py"),
    Path("app/core/guard_middleware.py"),
    Path("app/services/crs_bounds.py"),
)


def _valid_replay() -> dict:
    return {
        "area_id": "phoenix-demo",
        "analysis_time": "2022-06-30T03:00:00",
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }


def test_spend_defaults_remain_closed() -> None:
    assert spend_defaults_remain_closed() is True
    policy = DemoAllowancePolicy()
    assert policy.enabled is False
    assert policy.max_total_acquisition_units == 0
    disabled = disabled_demo_policy()
    assert disabled.enabled is False
    assert disabled.max_total_acquisition_units == 0


def test_public_path_never_writes_vendor_cache() -> None:
    assert public_path_may_write_vendor_cache() is False
    policy = CacheCapPolicy(allow_public_vendor_writes=True)
    assert policy.allow_public_vendor_writes is False
    denied = policy.decide_put(
        path="public",
        vendor=True,
        entry_count=0,
        used_bytes=0,
        incoming_bytes=16,
    )
    assert denied.allowed is False
    assert denied.reason_code == REASON_PUBLIC_VENDOR_CACHE_WRITE


def test_cache_caps_count_and_bytes_and_client_key() -> None:
    policy = CacheCapPolicy(max_entries=2, max_bytes=100)
    ok = policy.decide_put(
        path="internal",
        vendor=True,
        entry_count=1,
        used_bytes=10,
        incoming_bytes=10,
    )
    assert ok.allowed is True
    full = policy.decide_put(
        path="internal",
        vendor=False,
        entry_count=2,
        used_bytes=0,
        incoming_bytes=1,
    )
    assert full.allowed is False
    assert full.reason_code == REASON_CACHE_ENTRY_CAP
    too_big = policy.decide_put(
        path="internal",
        vendor=False,
        entry_count=0,
        used_bytes=90,
        incoming_bytes=20,
    )
    assert too_big.allowed is False
    assert too_big.reason_code == REASON_CACHE_BYTE_CAP
    named = policy.decide_put(
        path="internal",
        vendor=False,
        entry_count=0,
        used_bytes=0,
        incoming_bytes=1,
        client_supplied_key="attacker-fingerprint",
    )
    assert named.allowed is False
    assert named.reason_code == REASON_CLIENT_CACHE_KEY


def test_rate_limiter_is_enforcing_not_noop() -> None:
    clock = {"t": 0.0}

    def now() -> float:
        return clock["t"]

    limiter = InProcessRateLimiter(
        {"analysis_jobs_post": RateLimitSpec(max_events=2, window_seconds=10)},
        now=now,
    )
    first = limiter.allow(route_class="analysis_jobs_post", client_class="10.0.0.1")
    second = limiter.allow(route_class="analysis_jobs_post", client_class="10.0.0.1")
    third = limiter.allow(route_class="analysis_jobs_post", client_class="10.0.0.1")
    other = limiter.allow(route_class="analysis_jobs_post", client_class="10.0.0.2")
    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.reason_code == REASON_RATE_LIMITED
    assert third.retry_after_seconds is not None and third.retry_after_seconds >= 1
    assert other.allowed is True
    clock["t"] = 11.0
    later = limiter.allow(route_class="analysis_jobs_post", client_class="10.0.0.1")
    assert later.allowed is True


def test_default_route_limits_are_finite() -> None:
    assert DEFAULT_ROUTE_LIMITS["analysis_jobs_post"].max_events == 10
    assert DEFAULT_ROUTE_LIMITS["place_search"].max_events == 5
    assert DEFAULT_ROUTE_LIMITS["geography_resolve"].max_events == 2
    for spec in DEFAULT_ROUTE_LIMITS.values():
        assert spec.max_events >= 1
        assert spec.window_seconds > 0


def test_job_quota_in_flight_class_and_stored() -> None:
    quota = InProcessJobQuota(max_in_flight=2, max_stored=3, max_in_flight_per_class=1)
    first = quota.try_create("a")
    assert first.allowed is True
    assert first.token is not None
    same_class = quota.try_create("a")
    assert same_class.allowed is False
    assert same_class.reason_code == REASON_JOB_QUOTA_CLASS
    second = quota.try_create("b")
    assert second.allowed is True
    third = quota.try_create("c")
    assert third.allowed is False
    assert third.reason_code == REASON_JOB_QUOTA_IN_FLIGHT
    quota.mark_terminal(first.token)
    after_terminal = quota.try_create("a")
    assert after_terminal.allowed is True
    quota.mark_terminal(second.token)
    quota.mark_terminal(after_terminal.token)
    stored_full = quota.try_create("d")
    assert stored_full.allowed is False
    assert stored_full.reason_code == REASON_JOB_QUOTA_STORED
    assert quota.evict_oldest_terminal_slot() is True
    after_evict = quota.try_create("d")
    assert after_evict.allowed is True


def test_classify_route_and_client_class() -> None:
    assert classify_route("POST", "/api/v1/analysis/jobs") == "analysis_jobs_post"
    assert classify_route("GET", "/api/v1/areas/phoenix-demo/geometry") == "geometry_get"
    assert classify_route("GET", "/api/v1/areas") == "areas_get"
    assert classify_route("GET", "/api/v1/places") == "place_search"
    assert classify_route("POST", "/api/v1/geographies") == "geography_resolve"
    assert classify_route("GET", "/health") == "read"
    assert client_class_from_headers({"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}) == "203.0.113.9"
    assert client_class_from_headers({}) == "unknown"


@pytest.mark.parametrize(
    "value",
    ["0455000", "1714000", "1236550"],
)
def test_place_geoid_seven_digits_accepted(value: str) -> None:
    assert is_place_geoid(value) is True
    assert require_place_geoid(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "chicago",
        "045500",
        "04550000",
        "0455000 ",
        " 0455000",
        "04-55000",
        "０４５５０００",
        "0455000\n",
        455000,
        None,
        "",
    ],
)
def test_place_geoid_rejects_malformed(value: object) -> None:
    assert is_place_geoid(value) is False
    with pytest.raises(GeoidFormatError) as exc:
        require_place_geoid(value)
    assert exc.value.reason_code == REASON_INVALID_PLACE_GEOID


@pytest.mark.parametrize(
    "value",
    ["04013980100", "17031320100"],
)
def test_tract_geoid_eleven_digits_accepted(value: str) -> None:
    assert is_tract_geoid(value) is True
    assert require_tract_geoid(value) == value


@pytest.mark.parametrize(
    "value",
    ["04013", "0401398010", "040139801001", "not-a-tract", "04013980100 "],
)
def test_tract_geoid_rejects_malformed(value: str) -> None:
    assert is_tract_geoid(value) is False
    with pytest.raises(GeoidFormatError) as exc:
        require_tract_geoid(value)
    assert exc.value.reason_code == REASON_INVALID_TRACT_GEOID


def test_tract_statefp_must_match_place() -> None:
    assert tract_state_matches_place("04013980100", "0455000") is True
    assert tract_state_matches_place("17031320100", "0455000") is False
    assert require_tract_for_place("04013980100", "0455000") == "04013980100"
    with pytest.raises(GeoidFormatError) as exc:
        require_tract_for_place("17031320100", "0455000")
    assert exc.value.reason_code == REASON_GEOID_STATE_MISMATCH


def test_denylist_includes_required_public_keys() -> None:
    for name in ("grant", "force_live", "key", "authorized_max_units"):
        assert name in PUBLIC_SERIALIZER_DENYLIST
    planted = {
        "job_id": "job_x",
        "grant": {"state": "AUTHORIZED"},
        "force_live": True,
        "nested": {"key": "secret", "authorized_max_units": 9},
    }
    assert public_payload_hits_denylist(planted) == [
        "authorized_max_units",
        "force_live",
        "grant",
        "key",
    ]
    stripped = strip_denied_public_fields(planted)
    assert public_payload_hits_denylist(stripped) == []
    assert stripped == {"job_id": "job_x", "nested": {}}


def test_unpublished_spend_view_authorized_max_units_is_denylisted() -> None:
    assert "authorized_max_units" in PublicSpendView.model_fields
    dumped = PublicSpendView(state="DENIED", authorized_max_units=1).model_dump()
    hits = public_payload_hits_denylist(dumped)
    assert "authorized_max_units" in hits
    assert "requested_units" in hits
    assert "planned_acquisition_units" in hits
    stripped = strip_denied_public_fields(dumped)
    assert "authorized_max_units" not in stripped
    assert "requested_units" not in stripped
    assert "planned_acquisition_units" not in stripped
    assert "authorized_max_units" in WorkerHandoff.model_fields
    assert "fortyguard_api_key" not in TwoSignalPublicJob.model_fields
    assert "force_live" not in TwoSignalPublicJob.model_fields
    assert "grant" not in TwoSignalPublicJob.model_fields


def test_analysis_request_and_openapi_omit_denylist() -> None:
    from app.main import app

    for name in PUBLIC_SERIALIZER_DENYLIST:
        assert name not in AnalysisRequest.model_fields
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**_valid_replay(), "force_live": True})
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**_valid_replay(), "authorized_max_units": 4})
    schema = app.openapi()
    hits = public_payload_hits_denylist(schema)
    assert hits == []
    schemas = (schema.get("components") or {}).get("schemas") or {}
    assert "SpendGrant" not in schemas
    assert "DemoAllowancePolicy" not in schemas
    assert "WorkerHandoff" not in schemas


def test_legacy_public_job_serializer_omits_denylist() -> None:
    result = run_replay_analysis(
        AnalysisRequest.model_validate(
            {
                "area_id": "phoenix-demo",
                "analysis_time": datetime(2022, 6, 30, 3, 0),
                "analysis_mode": "retrospective",
                "horizon_hours": 0,
                "lookback_hours": 0,
                "granularity_m": 100,
                "data_mode": "replay",
            }
        )
    )
    dto = serialize_legacy_a_only_job(
        job_id="job_legacy_guard",
        area_id="phoenix-demo",
        result=result,
    )
    dumped = dto.model_dump(mode="json")
    assert public_payload_hits_denylist(dumped) == []
    assert dumped.get("spend") is None


def test_guard_middleware_is_gated_off_by_default() -> None:
    assert anonymous_guard_middleware_enabled() is False
    from app.main import app

    names = [getattr(item, "cls", type(item)).__name__ for item in app.user_middleware]
    assert "AnonymousGuardMiddleware" not in names


def test_guard_middleware_enforces_when_explicitly_enabled() -> None:
    inner = FastAPI()

    @inner.post("/api/v1/analysis/jobs")
    def _create() -> dict[str, bool]:
        return {"ok": True}

    guards = AnonymousGuards(
        limiter=InProcessRateLimiter(
            {"analysis_jobs_post": RateLimitSpec(max_events=2, window_seconds=60)}
        ),
        quota=InProcessJobQuota(max_in_flight=8, max_stored=256, max_in_flight_per_class=8),
    )
    inner.add_middleware(AnonymousGuardMiddleware, enabled=True, guards=guards)
    client = TestClient(inner)
    assert client.post("/api/v1/analysis/jobs").status_code == 200
    assert client.post("/api/v1/analysis/jobs").status_code == 200
    blocked = client.post("/api/v1/analysis/jobs")
    assert blocked.status_code == 429
    assert blocked.json()["reason_code"] == REASON_RATE_LIMITED
    assert "Retry-After" in blocked.headers


def test_guard_middleware_disabled_is_passthrough() -> None:
    inner = FastAPI()

    @inner.post("/api/v1/analysis/jobs")
    def _create() -> dict[str, bool]:
        return {"ok": True}

    guards = AnonymousGuards(
        limiter=InProcessRateLimiter(
            {"analysis_jobs_post": RateLimitSpec(max_events=1, window_seconds=60)}
        )
    )
    inner.add_middleware(AnonymousGuardMiddleware, enabled=False, guards=guards)
    client = TestClient(inner)
    assert client.post("/api/v1/analysis/jobs").status_code == 200
    assert client.post("/api/v1/analysis/jobs").status_code == 200


def test_guard_middleware_rejects_oversized_body() -> None:
    inner = FastAPI()

    @inner.post("/api/v1/analysis/jobs")
    def _create() -> dict[str, bool]:
        return {"ok": True}

    inner.add_middleware(AnonymousGuardMiddleware, enabled=True, max_body_bytes=8)
    client = TestClient(inner)
    response = client.post("/api/v1/analysis/jobs", content=b"0123456789")
    assert response.status_code == 413
    assert response.json()["reason_code"] == "BODY_TOO_LARGE"


def test_owned_modules_do_not_import_vendor_or_enable_allowance() -> None:
    for rel in _OWNED_MODULES:
        source = (Path(__file__).resolve().parents[2] / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "fortyguard" not in alias.name.lower()
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "fortyguard" not in node.module.lower()
        assert "demo_allowance_enabled=True" not in source
