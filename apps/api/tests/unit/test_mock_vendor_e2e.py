"""LIVE-L mock vendor E2E. Zero FortyGuard I/O. Zero credentials. Zero sockets."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings
from app.core.job_store import InMemoryJobStore
from app.domain.aggregation import ThermalAggregationSpec
from app.domain.demo_allowance import (
    AcquisitionPreference,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
)
from app.domain.enums import (
    DataMode,
    JobStatus,
    TileAssignmentMethod,
    ZoneAggregationStatistic,
)
from app.domain.public_contract import TwoSignalPublicRequest
from app.domain.signals import SignalAvailability, ThermalSignalKind
from app.integrations.mock_vendor import (
    CRASH_MATRIX_POINTS,
    CrashController,
    CrashPoint,
    InMemoryMockActivityStore,
    InMemoryMockResultCache,
    LifecyclePhase,
    MockVendorAdapter,
    RestartAction,
    SimulatedCrash,
    resume_mock_vendor_lifecycle,
    run_mock_vendor_lifecycle,
    selected_time_fingerprint,
)
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.snapshot_processor import SnapshotGeography

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "zones"
SETTINGS = Settings.model_construct(demo_allowance_enabled=False)
TARGET = datetime(2024, 7, 15, 15, 0, 0)
MOCK_ROOT = Path(__file__).resolve().parents[2] / "app" / "integrations" / "mock_vendor"


def _zones() -> dict:
    return json.loads((FIXTURES / "synthetic_zones.geojson").read_text(encoding="utf-8"))


def _tiles() -> dict:
    tiles = json.loads((FIXTURES / "synthetic_tiles.geojson").read_text(encoding="utf-8"))
    for feature in tiles["features"]:
        feature.setdefault("properties", {})["valid_time"] = "2024-07-15T15:00:00"
    return tiles


def _geography() -> SnapshotGeography:
    zones = _zones()
    ids = tuple(str(f["properties"]["zone_id"]) for f in zones["features"])
    return SnapshotGeography(
        area_id="phoenix-demo",
        timezone="America/Phoenix",
        zone_geoids=ids,
        expected_zone_count=len(ids),
        aggregation_spec=ThermalAggregationSpec(
            version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
            assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
            statistic=ZoneAggregationStatistic.MEAN,
            minimum_coverage_ratio=None,
            zero_tile_behavior="insufficient_evidence",
            boundary_behavior="centroid_within_zone",
            notes=["LIVE-L mock vendor test geography"],
        ),
        area_selection_policy_version="TEST_POLICY_V1",
        zone_geometry_version="TEST_GEOM_V1",
        geometry_sha256="cc" * 32,
        zones_geojson=zones,
        zone_id_property="zone_id",
    )


def _request() -> TwoSignalPublicRequest:
    return TwoSignalPublicRequest.model_validate(
        {
            "area_id": "phoenix-demo",
            "signals": {
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "acquisition_preference": "allow_hosted_live_demo",
                }
            },
            "timezone": "America/Phoenix",
            "granularity_m": 100,
            "data_mode": "live",
        }
    )


def _test_policy(**overrides: object) -> DemoAllowancePolicy:
    payload: dict[str, object] = {
        "enabled": True,
        "max_total_acquisition_units": 2,
        "max_units_per_request": 1,
        "allowed_area_ids": frozenset({"phoenix-demo"}),
    }
    payload.update(overrides)
    return DemoAllowancePolicy.model_validate(payload)


def _identity(
    geography: SnapshotGeography, request: TwoSignalPublicRequest
) -> DemoRequestIdentity:
    return DemoRequestIdentity(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint=selected_time_fingerprint(request, geography),
        geometry_sha256=geography.geometry_sha256,
        area_id="phoenix-demo",
    )


def _ctx(
    *,
    policy: DemoAllowancePolicy | None = None,
    processing_delay_ticks: int = 1,
    unknown_after_submit: bool = False,
    fingerprint_mode: str = "new_activity",
    never_complete: bool = False,
):
    geography = _geography()
    request = _request()
    identity = _identity(geography, request)
    return {
        "store": InMemoryJobStore(),
        "ledger": InMemoryDemoAllowanceLedger(policy or _test_policy()),
        "activities": InMemoryMockActivityStore(),
        "cache": InMemoryMockResultCache(),
        "vendor": MockVendorAdapter(
            _tiles(),
            processing_delay_ticks=processing_delay_ticks,
            unknown_after_submit=unknown_after_submit,
            fingerprint_mode=fingerprint_mode,  # type: ignore[arg-type]
            never_complete=never_complete,
        ),
        "request": request,
        "identity": identity,
        "geography": geography,
        "now": datetime.now(timezone.utc),
    }


def test_mock_e2e_happy_path_request_to_consume() -> None:
    """request → cache miss → reserve → submit → activity_id → process →
    result → normalize → cache → consume."""
    ctx = _ctx()
    result = run_mock_vendor_lifecycle(**ctx)
    assert result.outcome == "ready"
    assert result.phase == LifecyclePhase.CONSUMED
    assert result.signal_availability == SignalAvailability.READY.value
    assert result.snapshot_valid_zone_count == 2
    assert result.reservation_state == ReservationState.CONSUMED.value
    assert result.vendor_submit_count == 1
    assert result.vendor_paid_submit_count == 1
    assert result.vendor_activity_id is not None
    assert result.vendor_activity_id.startswith("mock_")
    assert result.cache_hit is False
    job = ctx["store"].get(result.job_id)
    assert job is not None
    assert job.status == JobStatus.COMPLETE
    assert job.two_signal is not None
    assert job.two_signal.selected_time.progress.phase.value == "ready"
    assert ctx["cache"].contains(ctx["identity"].request_fingerprint)
    assert ctx["ledger"].snapshot().reserved_units == 0
    assert ctx["ledger"].snapshot().consumed_units == 1
    assert ctx["request"].signals.selected_time.acquisition_preference == (
        AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO
    )
    assert ctx["request"].data_mode == DataMode.LIVE
    assert SETTINGS.demo_allowance_enabled is False
    assert Settings.model_fields["demo_allowance_enabled"].default is False


def test_duplicate_fingerprint_does_not_resubmit() -> None:
    ctx = _ctx()
    first = run_mock_vendor_lifecycle(**ctx)
    second = run_mock_vendor_lifecycle(**ctx)
    assert first.outcome == "ready"
    assert second.outcome == "reused"
    assert second.phase == LifecyclePhase.CACHE_HIT
    assert second.cache_hit is True
    assert ctx["vendor"].submit_count == 1
    assert ctx["vendor"].paid_submit_count == 1
    assert ctx["ledger"].snapshot().consumed_units == 1


def test_vendor_fingerprint_reuse_returns_same_activity_id() -> None:
    ctx = _ctx(fingerprint_mode="reuse_activity")
    spec_fingerprint = ctx["identity"].request_fingerprint
    from app.integrations.mock_vendor import build_mock_vendor_request

    spec = build_mock_vendor_request(
        request=ctx["request"],
        identity=ctx["identity"],
        geography=ctx["geography"],
    )
    first = ctx["vendor"].submit(spec)
    second = ctx["vendor"].submit(spec)
    assert first == second
    assert ctx["vendor"].submit_count == 2
    assert ctx["vendor"].paid_submit_count == 1
    assert ctx["vendor"].vendor.activity_id_for_fingerprint(spec_fingerprint) == first


def test_unknown_after_submit_consumes_and_forbids_resubmit() -> None:
    ctx = _ctx(unknown_after_submit=True)
    result = run_mock_vendor_lifecycle(**ctx)
    assert result.outcome == "failed"
    assert result.phase == LifecyclePhase.FAILED_POST_SUBMIT
    assert result.reason == "unknown_after_submit"
    assert result.reservation_state == ReservationState.CONSUMED.value
    assert ctx["vendor"].paid_submit_count == 1
    retry = run_mock_vendor_lifecycle(**ctx)
    assert retry.outcome == "no_resubmit"
    assert retry.restart_action == RestartAction.NO_RESUBMIT_ALREADY_SPENT.value
    assert ctx["vendor"].paid_submit_count == 1


def test_processing_delay_requires_multiple_polls() -> None:
    ctx = _ctx(processing_delay_ticks=3)
    result = run_mock_vendor_lifecycle(**ctx)
    assert result.outcome == "ready"
    assert result.vendor_poll_count == 3
    assert ctx["vendor"].poll_count == 3


def test_crash_controller_visits_all_nine_matrix_points() -> None:
    seen: list[CrashPoint] = []
    crash = CrashController()
    crash.on_any(lambda point, _phase: seen.append(point))
    ctx = _ctx()
    result = run_mock_vendor_lifecycle(**ctx, crash=crash)
    assert result.outcome == "ready"
    assert tuple(seen) == CRASH_MATRIX_POINTS
    assert len(CRASH_MATRIX_POINTS) == 9


def test_each_crash_point_is_hookable() -> None:
    for point in CRASH_MATRIX_POINTS:
        ctx = _ctx()
        hooked: list[CrashPoint] = []
        crash = CrashController(point)
        crash.on(point, lambda p, _phase: hooked.append(p))
        result = run_mock_vendor_lifecycle(**ctx, crash=crash)
        assert result.outcome == "crashed"
        assert result.reason == f"simulated_crash:{point.value}"
        assert hooked == [point]
        if point in {
            CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID,
            CrashPoint.DURING_SUBMIT,
        }:
            record = ctx["activities"].find_by_fingerprint(
                ctx["identity"].request_fingerprint
            )
            assert record is not None
            assert record.phase == LifecyclePhase.UNKNOWN_VENDOR_STATE
            assert record.vendor_activity_id is None


def test_lost_activity_id_never_blind_resubmits() -> None:
    ctx = _ctx()
    crashed = run_mock_vendor_lifecycle(
        **ctx, crash_at=CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID
    )
    assert crashed.outcome == "crashed"
    assert crashed.vendor_activity_id is None
    resumed = resume_mock_vendor_lifecycle(
        store=ctx["store"],
        ledger=ctx["ledger"],
        vendor=ctx["vendor"],
        request=ctx["request"],
        identity=ctx["identity"],
        geography=ctx["geography"],
        activities=ctx["activities"],
        cache=ctx["cache"],
        job_id=crashed.job_id,
    )
    assert resumed.outcome == "uncertain"
    assert resumed.phase == LifecyclePhase.UNKNOWN_VENDOR_STATE
    assert resumed.restart_action == RestartAction.NO_RESUBMIT_UNCERTAIN.value
    assert ctx["vendor"].paid_submit_count == 1


def test_resume_after_activity_id_polls_only() -> None:
    ctx = _ctx(processing_delay_ticks=2)
    crashed = run_mock_vendor_lifecycle(
        **ctx, crash_at=CrashPoint.AFTER_ACTIVITY_ID
    )
    assert crashed.outcome == "crashed"
    assert crashed.vendor_activity_id is not None
    assert crashed.phase == LifecyclePhase.ACTIVITY_ID_PERSISTED
    resumed = resume_mock_vendor_lifecycle(
        store=ctx["store"],
        ledger=ctx["ledger"],
        vendor=ctx["vendor"],
        request=ctx["request"],
        identity=ctx["identity"],
        geography=ctx["geography"],
        activities=ctx["activities"],
        cache=ctx["cache"],
        job_id=crashed.job_id,
    )
    assert resumed.outcome == "ready"
    assert resumed.vendor_activity_id == crashed.vendor_activity_id
    assert ctx["vendor"].paid_submit_count == 1
    assert ctx["ledger"].snapshot().consumed_units == 1


def test_resume_after_cache_before_consume_reuses_and_releases() -> None:
    ctx = _ctx()
    crashed = run_mock_vendor_lifecycle(
        **ctx, crash_at=CrashPoint.AFTER_CACHE_BEFORE_CONSUME
    )
    assert crashed.outcome == "crashed"
    assert ctx["cache"].contains(ctx["identity"].request_fingerprint)
    assert crashed.reservation_state == ReservationState.RESERVED.value
    resumed = resume_mock_vendor_lifecycle(
        store=ctx["store"],
        ledger=ctx["ledger"],
        vendor=ctx["vendor"],
        request=ctx["request"],
        identity=ctx["identity"],
        geography=ctx["geography"],
        activities=ctx["activities"],
        cache=ctx["cache"],
        job_id=crashed.job_id,
    )
    assert resumed.outcome == "reused"
    assert resumed.restart_action == RestartAction.REUSE_CACHE.value
    assert ctx["ledger"].snapshot().consumed_units == 0
    assert ctx["ledger"].get(crashed.reservation_id).state == ReservationState.RELEASED
    assert ctx["vendor"].paid_submit_count == 1


def test_adapter_refuses_non_mock_kind() -> None:
    import pytest
    from pydantic import ValidationError

    from app.integrations.mock_vendor.types import MockVendorRequest

    ctx = _ctx()
    spec = MockVendorRequest(
        area_id="phoenix-demo",
        request_fingerprint=ctx["identity"].request_fingerprint,
        geometry_sha256=ctx["identity"].geometry_sha256,
        target_timestamp=TARGET,
        timezone="America/Phoenix",
    )
    assert spec.vendor_kind == "mock"
    with pytest.raises(ValidationError):
        MockVendorRequest.model_validate(
            {
                "vendor_kind": "fortyguard",
                "area_id": "phoenix-demo",
                "request_fingerprint": "aa" * 16,
                "geometry_sha256": "bb" * 16,
                "target_timestamp": "2024-07-15T15:00:00",
                "timezone": "America/Phoenix",
            }
        )
    activity_id = ctx["vendor"].submit(spec)
    assert activity_id.startswith("mock_")


def test_mock_package_never_imports_fortyguard_or_network() -> None:
    forbidden = {
        "app.integrations.fortyguard",
        "app.integrations.fortyguard.client",
        "app.integrations.fortyguard.adapter",
        "httpx",
        "requests",
        "urllib.request",
        "socket",
        "aiohttp",
    }
    paths = sorted(MOCK_ROOT.glob("*.py"))
    paths.append(
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "hosted_live_mock_vendor.py"
    )
    assert paths
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert imported.isdisjoint(forbidden), f"{path.name} imported {imported & forbidden}"
        source = path.read_text(encoding="utf-8")
        assert "FortyGuardHttpClient" not in source
        assert "fortyguard_api_key" not in source


def test_simulated_crash_is_not_a_network_error() -> None:
    crash = SimulatedCrash(CrashPoint.BEFORE_RESERVE, LifecyclePhase.VALIDATED)
    assert isinstance(crash, RuntimeError)
    assert "simulated_crash:before_reserve" in str(crash)
