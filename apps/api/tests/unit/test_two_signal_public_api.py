"""P2 sibling two-signal API. Default flag off. Zero FortyGuard. Zero spend."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.optional_two_signal_router import (
    include_optional_two_signal_routes,
    public_two_signal_enabled,
)
from app.api.routes.two_signal_jobs import router as two_signal_router
from app.core.area_registry import PHOENIX_DEMO_AREA_ID, resolve_area_geography
from app.core.config import Settings
from app.core.jobs import job_store
from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.signals import (
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)
from app.main import app as default_app
from app.schemas.two_signal_public import (
    PublicReasonCode,
    TwoSignalPublicationRequest,
    TwoSignalPublicJob,
)
from app.services.secret_boundary import public_payload_leaks_secrets
from app.services.snapshot_identity import snapshot_request_fingerprint
from app.services.two_signal_jobs import (
    ReuseHit,
    reset_two_signal_runtime,
    reuse_store,
    two_signal_job_service,
)

OWNED = (
    Path(__file__).resolve().parents[2]
    / "app"
)
LEAK_PROPERTY_NAMES = frozenset(
    {
        "approval",
        "approved",
        "approve",
        "authorize",
        "authorized",
        "authorized_max_units",
        "spend",
        "spend_authorization",
        "spend_authorized",
        "skip_approval",
        "allowance",
        "allowance_remaining",
        "demo_budget",
        "demo",
        "demo_test",
        "live_demo",
        "force_live",
        "bypass_limit",
        "acquisition_preference",
        "operator",
        "operator_override",
        "operator_id",
        "authorization_source",
        "reservation_id",
        "approval_ref",
        "consumed_units",
        "planned_acquisition_units",
        "requested_units",
        "estimated_units",
        "max_total_acquisition_units",
        "max_units_per_request",
        "demo_allowance_enabled",
        "awaiting_approval",
        "WAITING_FOR_APPROVAL",
        "SPEND_DENIED",
        "SPEND_EXPIRED",
        "AUTHORIZATION_INSUFFICIENT",
        "DEMO_ALLOWANCE_DISABLED",
        "DEMO_ALLOWANCE_EXHAUSTED",
        "DEMO_ALLOWANCE_EXPIRED",
        "REQUEST_UNIT_CAP_EXCEEDED",
        "LIVE_DEMO_NOT_REQUESTED",
        "fortyguard_api_key",
        "api_key",
        "apikey",
        "secret",
        "password",
        "internal_key",
        "access_token",
        "combined_score",
        "combined_score_value",
    }
)
P3_REASON_CODES = frozenset(
    {
        "WAITING_FOR_APPROVAL",
        "SPEND_DENIED",
        "SPEND_EXPIRED",
        "AUTHORIZATION_INSUFFICIENT",
        "LIVE_DEMO_NOT_REQUESTED",
        "DEMO_ALLOWANCE_DISABLED",
        "DEMO_ALLOWANCE_EXHAUSTED",
        "DEMO_ALLOWANCE_EXPIRED",
        "REQUEST_UNIT_CAP_EXCEEDED",
        "LIVE_ACQUISITION_UNAVAILABLE",
    }
)
B_PRODUCT_LEAKS = (
    "q_A",
    "ZTSI",
    "ztsi",
    "probability",
    "risk",
    "danger",
    "D8",
    "decision8",
    "thermal_ordering_permitted",
    "ranked",
    "hazard_spread",
    "reference_version",
    "intervention",
    "intervention_ids",
    "now",
    "current_conditions",
)


def _publication(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_version": "hva-signal-two-signal-job-v1",
        "area_id": "phoenix-demo",
        "signals": {
            "historical": {"analysis_time": "2022-06-30T03:00:00"},
            "selected_time": {
                "target_timestamp": "2024-07-15T15:00:00",
                "analytic": "tcm",
            },
        },
        "timezone": "America/Phoenix",
        "granularity_m": 100,
        "data_mode": "replay",
    }
    payload.update(overrides)
    return payload


def _reuse_snapshot(*, source: str = "replay") -> SelectedTimeSnapshot:
    geography = resolve_area_geography(PHOENIX_DEMO_AREA_ID)
    return SelectedTimeSnapshot(
        area_id="phoenix-demo",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=SignalAvailability.READY,
        geometry_sha256=geography.manifest.geometry_sha256,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id="phoenix-demo",
            source=ThermalDataSource.REPLAY
            if source == "replay"
            else ThermalDataSource.FORTYGUARD_CACHED,
            data_status=DataStatus.REPLAY if source == "replay" else DataStatus.CACHED,
            geometry_version=geography.config.zone_geometry_version,
            aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        ),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="04013109100",
                mean_temperature_c=34.2,
                tile_count=4,
                coverage_status="ok",
            )
        ],
        expected_zone_count=25,
        valid_zone_count=1,
        missing_zone_ids=[],
    )


def _seed_reuse(*, source: str = "replay", joined: bool = False) -> str:
    geography = resolve_area_geography(PHOENIX_DEMO_AREA_ID)
    fingerprint = snapshot_request_fingerprint(
        area_id="phoenix-demo",
        geometry_sha256=geography.manifest.geometry_sha256,
        zone_geometry_version=geography.config.zone_geometry_version,
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        analytic="tcm",
        granularity_m=100,
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    )
    reuse_store.put(
        fingerprint,
        ReuseHit(
            snapshot=_reuse_snapshot(source=source),
            source="replay" if source == "replay" else "fortyguard_cached",
            joined_in_flight=joined,
        ),
    )
    return fingerprint


def _flagged_client() -> TestClient:
    application = FastAPI()
    application.include_router(two_signal_router, prefix="/api/v1")
    return TestClient(application)


def _forbid_vendor(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("FortyGuard must not be called")

    monkeypatch.setattr(
        "app.integrations.fortyguard.adapter.FortyGuardAdapter.fetch_heatmap",
        boom,
    )


@pytest.fixture(autouse=True)
def _isolate_runtime() -> None:
    job_store.reset()
    reset_two_signal_runtime()
    yield
    job_store.reset()
    reset_two_signal_runtime()


def test_flag_defaults_off() -> None:
    assert Settings.model_fields["hva_public_two_signal"].default is False
    assert Settings.model_fields["demo_allowance_enabled"].default is False
    assert Settings.model_construct().hva_public_two_signal is False
    assert public_two_signal_enabled(Settings.model_construct()) is False


def test_default_app_openapi_excludes_two_signal_and_spend() -> None:
    schema = default_app.openapi()
    paths = schema.get("paths") or {}
    assert set(paths) == {
        "/health",
        "/ready",
        "/api/v1/areas",
        "/api/v1/areas/{area_id}/geometry",
        "/api/v1/analysis/jobs",
        "/api/v1/analysis/jobs/{job_id}",
        "/api/v1/areas/{area_id}/context",
    }
    assert "/api/v1/analysis/two-signal-jobs" not in paths
    schemas = schema.get("components", {}).get("schemas", {})
    for name in (
        "TwoSignalPublicJob",
        "TwoSignalPublicationRequest",
        "PublicSpendView",
        "DemoAllowancePolicy",
        "AcquisitionPreference",
        "WorkerHandoff",
        "SpendGrant",
        "CostAuthorization",
        "HostedDemoResolution",
        "DemoReservation",
    ):
        assert name not in schemas


def test_gated_include_off_adds_nothing() -> None:
    router = APIRouter()
    include_optional_two_signal_routes(router, enabled=False)
    assert [getattr(route, "path", "") for route in router.routes] == []


def test_gated_include_on_adds_sibling_paths() -> None:
    application = FastAPI()
    include_optional_two_signal_routes(application, enabled=True)
    paths = set(application.openapi().get("paths") or {})
    assert "/api/v1/analysis/two-signal-jobs" in paths
    assert "/api/v1/analysis/two-signal-jobs/{job_id}" in paths


def test_p1_jobs_route_unchanged() -> None:
    client = TestClient(default_app)
    payload = {
        "area_id": "phoenix-demo",
        "analysis_time": "2022-06-30T03:00:00",
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }
    created = client.post("/api/v1/analysis/jobs", json=payload)
    assert created.status_code == 202
    body = created.json()
    assert "two_signal" not in body
    assert "selected_time" not in body
    assert "signals" not in body
    assert "spend" not in body
    assert "contract_version" not in body
    rejected = client.post("/api/v1/analysis/jobs", json={**payload, "signals": True})
    assert rejected.status_code == 422


@pytest.mark.parametrize(
    "signals",
    [
        {"historical": {"analysis_time": "2022-06-30T03:00:00"}},
        {
            "selected_time": {
                "target_timestamp": "2024-07-15T15:00:00",
                "analytic": "tcm",
            }
        },
        {
            "historical": {"analysis_time": "2022-06-30T03:00:00"},
            "selected_time": {
                "target_timestamp": "2024-07-15T15:00:00",
                "analytic": "tcm",
            },
        },
    ],
)
def test_publication_request_parses_independent_timestamps(signals: dict) -> None:
    req = TwoSignalPublicationRequest.model_validate(_publication(signals=signals))
    if req.signals.historical is not None:
        assert req.signals.historical.analysis_time == datetime(2022, 6, 30, 3, 0, 0)
        assert req.signals.historical.analysis_time.tzinfo is None
    if req.signals.selected_time is not None:
        assert req.signals.selected_time.target_timestamp == datetime(2024, 7, 15, 15, 0, 0)
        assert req.signals.selected_time.target_timestamp.tzinfo is None
        assert not hasattr(req.signals.selected_time, "acquisition_preference")


@pytest.mark.parametrize(
    "payload",
    [
        _publication(signals={"historical": {"analysis_time": "2022-06-30T15:00:00"}}),
        _publication(
            signals={
                "selected_time": {"target_timestamp": "2024-07-15T15:10:00", "analytic": "tcm"}
            }
        ),
        _publication(
            signals={
                "selected_time": {
                    "target_timestamp": datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
                    "analytic": "tcm",
                }
            }
        ),
        _publication(data_mode="live"),
        _publication(
            signals={
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                    "acquisition_preference": "reuse_only",
                }
            }
        ),
        _publication(approval=True),
        _publication(authorized_max_units=4),
        _publication(demo_budget=1),
        _publication(allowance=True),
        _publication(allowance_remaining=3),
        _publication(internal_key="x"),
        _publication(operator_override=True),
        _publication(skip_approval=True),
        _publication(force_live=True),
        _publication(signals={"historical": {"analysis_time": "2022-06-30T03:00:00"}, "overnight": {}}),
        {
            "contract_version": "hva-signal-two-signal-job-v1",
            "area_id": "phoenix-demo",
            "signals": {
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                    "now": True,
                }
            },
            "timezone": "America/Phoenix",
        },
        _publication(signals={}),
    ],
)
def test_publication_request_rejects_leaks_and_clocks(payload: dict) -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicationRequest.model_validate(payload)


def test_unknown_area_parses() -> None:
    req = TwoSignalPublicationRequest.model_validate(
        _publication(area_id="us-place-1714000-2025-national-place-geography-v1")
    )
    assert req.area_id.startswith("us-place-")


def test_reuse_miss_is_snapshot_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    client = _flagged_client()
    response = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(
            signals={
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                }
            }
        ),
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "complete"
    assert body["combined_score_authorized"] is False
    assert "spend" not in body
    assert "combined_score" not in body
    section = body["selected_time"]
    assert section["requested"] is True
    assert section["availability"] == "UNAVAILABLE"
    assert section["error"]["reason_code"] == "SNAPSHOT_UNAVAILABLE"
    assert section["selected_time_result"] is None
    assert section["provenance"]["reference_version"] is None
    assert section["provenance"]["reference_source"] is None
    assert section["provenance"]["source"] != "fortyguard_live"
    assert body["legacy_thermal_source"] is None
    assert public_payload_leaks_secrets(body) == []


def test_replay_reuse_hit_is_ready_celsius(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    _seed_reuse(source="replay")
    client = _flagged_client()
    body = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(
            signals={
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                }
            }
        ),
    ).json()
    section = body["selected_time"]
    assert section["availability"] == "READY"
    assert section["provenance"]["source"] == "replay"
    assert section["provenance"]["data_status"] == "replay"
    assert section["provenance"]["reference_version"] is None
    result = section["selected_time_result"]
    assert result["units"] == "celsius"
    assert result["spatial_resolution"] == "zone"
    assert result["user_facing_tile_map"] is False
    assert result["zones"][0]["mean_temperature_c"] == 34.2
    for leak in B_PRODUCT_LEAKS:
        assert leak not in result
        assert leak not in result["zones"][0]


def test_cached_reuse_never_labeled_live(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    _seed_reuse(source="fortyguard_cached")
    client = _flagged_client()
    body = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(
            data_mode="auto",
            signals={
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                }
            },
        ),
    ).json()
    provenance = body["selected_time"]["provenance"]
    assert provenance["source"] == "fortyguard_cached"
    assert provenance["data_status"] == "cached"
    assert provenance["data_status"] != "live"
    assert body["selected_time"]["error"]["reason_code"] == "EVIDENCE_REUSED"


def test_joined_in_flight_has_no_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    _seed_reuse(source="replay", joined=True)
    client = _flagged_client()
    body = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(
            signals={
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                }
            }
        ),
    ).json()
    assert body["selected_time"]["error"]["reason_code"] == "JOINED_IN_FLIGHT"
    assert "spend" not in body
    assert body["status"] != "awaiting_approval"


def test_a_d8_insufficient_does_not_suppress_b(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    _seed_reuse(source="replay")
    client = _flagged_client()
    body = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(
            signals={
                "historical": {"analysis_time": "2022-07-01T03:00:00"},
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "analytic": "tcm",
                },
            }
        ),
    ).json()
    assert body["status"] == "complete"
    assert body["historical"]["availability"] == "D8_INSUFFICIENT"
    assert body["selected_time"]["availability"] == "READY"
    assert body["selected_time"]["selected_time_result"]["zones"][0]["mean_temperature_c"] == 34.2
    assert body["selected_time"]["provenance"]["reference_version"] is None
    a_zones = body["historical"]["historical_result"]["zones"]
    assert any("q_A" in zone for zone in a_zones)


def test_timezone_mismatch_is_422(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    client = _flagged_client()
    response = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(timezone="America/Chicago"),
    )
    assert response.status_code == 422


def test_national_area_is_unknown_not_areas_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_vendor(monkeypatch)
    client = _flagged_client()
    body = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(area_id="us-place-1714000-2025-national-place-geography-v1"),
    ).json()
    assert body["historical"]["error"]["reason_code"] == "UNKNOWN_AREA"
    assert body["selected_time"]["error"]["reason_code"] == "UNKNOWN_AREA"
    assert body["status"] == "failed"
    areas = TestClient(default_app).get("/api/v1/areas").json()
    assert all(item["area_id"] != body["area_id"] for item in areas["areas"])


def test_unknown_job_is_thin_and_recoverable() -> None:
    client = _flagged_client()
    body = client.get("/api/v1/analysis/two-signal-jobs/job_does_not_exist").json()
    assert body["status"] == "unknown_job"
    assert body["recoverable"] is True
    assert body["contract_version"] == "hva-signal-two-signal-job-v1"
    assert "historical" not in body
    assert "selected_time" not in body
    assert "spend" not in body
    assert "reservation_id" not in body


def test_crosswalk_p2_create_p1_get_strips_b(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    _seed_reuse(source="replay")
    flagged = _flagged_client()
    created = flagged.post(
        "/api/v1/analysis/two-signal-jobs",
        json=_publication(),
    ).json()
    p1 = TestClient(default_app).get(f"/api/v1/analysis/jobs/{created['job_id']}").json()
    assert "selected_time" not in p1
    assert "signals" not in p1
    assert "two_signal" not in p1
    assert "spend" not in p1
    assert "contract_version" not in p1
    assert p1["result"] is not None
    dumped = str(p1["result"])
    assert "mean_temperature_c" not in dumped or "q_A" in dumped
    request = p1["request"]
    assert "signals" not in request
    assert "selected_time" not in request


def test_crosswalk_p1_job_wraps_a_only_on_p2_get() -> None:
    p1 = TestClient(default_app)
    created = p1.post(
        "/api/v1/analysis/jobs",
        json={
            "area_id": "phoenix-demo",
            "analysis_time": "2022-06-30T03:00:00",
            "analysis_mode": "retrospective",
            "horizon_hours": 0,
            "lookback_hours": 0,
            "granularity_m": 100,
            "data_mode": "replay",
        },
    ).json()
    job = job_store.get(created["job_id"])
    assert job is not None
    wrapped = two_signal_job_service.get(created["job_id"])
    assert isinstance(wrapped, TwoSignalPublicJob)
    assert wrapped.selected_time.requested is False
    assert wrapped.selected_time.availability.value == "NOT_REQUESTED"
    assert wrapped.selected_time.selected_time_result is None


def test_ready_omits_settings_and_flag() -> None:
    body = TestClient(default_app).get("/ready").json()
    assert body == {"status": "ready", "data_mode": body["data_mode"]}
    assert "fortyguard_api_key" not in body
    assert "hva_public_two_signal" not in body
    assert "demo_allowance_enabled" not in body


def test_publication_schemas_have_no_spend_fields() -> None:
    assert "spend" not in TwoSignalPublicJob.model_fields
    assert "acquisition_preference" not in TwoSignalPublicationRequest.model_fields
    published = {item.value for item in PublicReasonCode}
    assert published.isdisjoint(P3_REASON_CODES)
    assert "SNAPSHOT_UNAVAILABLE" in published


def test_owned_modules_do_not_import_spend_or_vendor() -> None:
    forbidden_imports = (
        "demo_allowance",
        "AcquisitionPreference",
        "PublicSpendView",
        "WorkerHandoff",
        "fortyguard",
        "FortyGuardClient",
        "FortyGuardAdapter",
    )
    files = [
        OWNED / "schemas" / "two_signal_public.py",
        OWNED / "services" / "two_signal_jobs.py",
        OWNED / "api" / "routes" / "two_signal_jobs.py",
        OWNED / "api" / "optional_two_signal_router.py",
    ]
    for path in files:
        imports = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith(("import ", "from "))
        ]
        blob = "\n".join(imports)
        for token in forbidden_imports:
            assert token not in blob, f"{path.name} imported {token}"


def test_flagged_openapi_still_bans_spend_schemas() -> None:
    application = FastAPI()
    application.include_router(two_signal_router, prefix="/api/v1")
    schemas = application.openapi().get("components", {}).get("schemas", {})
    for name in (
        "DemoAllowancePolicy",
        "DemoAllowanceState",
        "DemoReservation",
        "AcquisitionPreference",
        "PublicSpendView",
        "SpendGrant",
        "CostAuthorization",
        "WorkerHandoff",
        "HostedDemoResolution",
    ):
        assert name not in schemas
    properties = _openapi_property_names(application.openapi())
    assert properties.isdisjoint(LEAK_PROPERTY_NAMES)


def test_public_payload_leak_checklist(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_vendor(monkeypatch)
    _seed_reuse(source="replay")
    client = _flagged_client()
    created = client.post("/api/v1/analysis/two-signal-jobs", json=_publication()).json()
    fetched = client.get(f"/api/v1/analysis/two-signal-jobs/{created['job_id']}").json()
    for body in (created, fetched):
        assert public_payload_leaks_secrets(body) == []
        keys = _walk_keys(body)
        assert keys.isdisjoint(LEAK_PROPERTY_NAMES)
        assert body["selected_time"]["provenance"]["reference_version"] is None
        assert body["legacy_thermal_source"] is None


def _walk_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            found.add(str(key))
            found.update(_walk_keys(inner))
    elif isinstance(value, list):
        for item in value:
            found.update(_walk_keys(item))
    return found


def _openapi_property_names(schema: dict) -> set[str]:
    found: set[str] = set()
    components = ((schema.get("components") or {}).get("schemas") or {})
    for model in components.values():
        if not isinstance(model, dict):
            continue
        props = model.get("properties") or {}
        found.update(str(key) for key in props)
        for item in model.get("enum") or []:
            found.add(str(item))
    return found
