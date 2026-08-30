"""Zero-vendor hosted-demo flow matrix. No FortyGuard I/O."""

from datetime import datetime, timedelta, timezone

from app.core.job_store import InMemoryJobStore
from app.domain.demo_allowance import (
    AcquisitionPreference,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
)
from app.domain.enums import DataMode, JobStatus
from app.domain.public_contract import TwoSignalPublicRequest
from app.domain.signals import ThermalSignalKind
from app.services.demo_acquisition import resolve_hosted_demo_path
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from pydantic import ValidationError
import pytest


def _policy(**overrides) -> DemoAllowancePolicy:
    payload = {
        "enabled": True,
        "max_total_acquisition_units": 1,
        "max_units_per_request": 1,
        "allowed_area_ids": frozenset({"phoenix-demo"}),
    }
    payload.update(overrides)
    return DemoAllowancePolicy.model_validate(payload)


def _identity(fp: str = "aa" * 32) -> DemoRequestIdentity:
    return DemoRequestIdentity(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint=fp,
        geometry_sha256="bb" * 32,
        area_id="phoenix-demo",
    )


def _path(store, ledger, **overrides):
    payload = {
        "store": store,
        "ledger": ledger,
        "dedupe_key": "same-b",
        "data_mode": DataMode.LIVE,
        "snapshot_capable": True,
        "preference": AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO,
        "identity": _identity(),
        "planned_units": 1,
        "now": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return resolve_hosted_demo_path(**payload)


def test_case1_cache_wins_even_if_user_asks_live() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy())
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"k": 1}, dedupe_key="same-b")
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    decision = _path(store, ledger)
    assert decision.code == DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE
    assert ledger.snapshot().reserved_units == 0


def test_case2_reuse_only_does_not_reserve() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy())
    decision = _path(
        InMemoryJobStore(),
        ledger,
        preference=AcquisitionPreference.REUSE_ONLY,
    )
    assert decision.code == DemoAllowanceDecisionCode.LIVE_DEMO_NOT_REQUESTED
    assert ledger.snapshot().reserved_units == 0


def test_case3_live_preference_with_allowance_reserves_without_vendor() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy())
    decision = _path(InMemoryJobStore(), ledger)
    assert decision.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert decision.decision.reservation is not None
    assert ledger.snapshot().reserved_units == 1


def test_case4_one_hundred_identical_requests_one_reservation() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy(max_total_acquisition_units=5))
    store = InMemoryJobStore()
    first = _path(store, ledger)
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    store.create_or_join({"k": 1}, dedupe_key="same-b")
    codes = [_path(store, ledger).code for _ in range(99)]
    assert set(codes) == {DemoAllowanceDecisionCode.JOIN_IN_FLIGHT}
    assert ledger.snapshot().reserved_units == 1


def test_case5_exhausted_allowance_does_not_execute() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy())
    first = _path(InMemoryJobStore(), ledger)
    second = _path(
        InMemoryJobStore(),
        ledger,
        identity=_identity("cc" * 32),
        dedupe_key="other-b",
    )
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert second.code == DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED


def test_case6_partition_overrun_never_reserves() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy())
    decision = _path(InMemoryJobStore(), ledger, planned_units=2)
    assert decision.code == DemoAllowanceDecisionCode.REQUEST_UNIT_CAP_EXCEEDED
    assert ledger.snapshot().reserved_units == 0


def test_case7_expired_policy_blocks_worker_consume() -> None:
    now = datetime.now(timezone.utc)
    ledger = InMemoryDemoAllowanceLedger(
        _policy(valid_until=now + timedelta(minutes=5))
    )
    reserved = _path(InMemoryJobStore(), ledger, now=now)
    later = InMemoryDemoAllowanceLedger(
        _policy(valid_until=now - timedelta(seconds=1))
    )
    later._reservations = ledger._reservations
    later._active_by_fingerprint = ledger._active_by_fingerprint
    from app.services.demo_acquisition import recheck_demo_reservation_before_paid_submission

    gate = recheck_demo_reservation_before_paid_submission(
        ledger=later,
        reservation_id=reserved.decision.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        store=InMemoryJobStore(),
        dedupe_key="same-b",
        now=now,
    )
    assert gate.allowed is False


def test_case8_fingerprint_change_invalidates_reservation() -> None:
    ledger = InMemoryDemoAllowanceLedger(_policy())
    reserved = _path(InMemoryJobStore(), ledger)
    from app.services.demo_acquisition import recheck_demo_reservation_before_paid_submission

    gate = recheck_demo_reservation_before_paid_submission(
        ledger=ledger,
        reservation_id=reserved.decision.reservation.reservation_id,
        identity=_identity("ff" * 32),
        planned_units=1,
        store=InMemoryJobStore(),
        dedupe_key="same-b",
        now=datetime.now(timezone.utc),
    )
    assert gate.allowed is False


def test_case9_signal_a_not_prepared_does_not_block_b_eligibility() -> None:
    from app.services.acquisition_path import historical_does_not_start_preparation

    assert historical_does_not_start_preparation(reference_ready=False).value == (
        "REFERENCE_NOT_PREPARED"
    )
    ledger = InMemoryDemoAllowanceLedger(_policy())
    decision = _path(InMemoryJobStore(), ledger)
    assert decision.code == DemoAllowanceDecisionCode.ELIGIBLE


def test_case10_client_approved_flag_is_not_a_preference() -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicRequest.model_validate(
            {
                "area_id": "phoenix-demo",
                "signals": {
                    "selected_time": {
                        "target_timestamp": "2024-07-15T15:00:00",
                        "approved": True,
                    }
                },
                "timezone": "America/Phoenix",
            }
        )
    req = TwoSignalPublicRequest.model_validate(
        {
            "area_id": "phoenix-demo",
            "signals": {"selected_time": {"target_timestamp": "2024-07-15T15:00:00"}},
            "timezone": "America/Phoenix",
        }
    )
    assert req.signals.selected_time.acquisition_preference.value == "reuse_only"
