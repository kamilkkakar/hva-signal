"""Server demo allowance is the spend control. User confirmation is not."""

from datetime import datetime, timedelta, timezone
from threading import Thread

import pytest

from app.domain.demo_allowance import (
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
    disabled_demo_policy,
)
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import (
    DemoAllowanceError,
    InMemoryDemoAllowanceLedger,
)
from app.services.demo_policy_config import demo_allowance_policy_from_settings
from app.services.spend_gate import can_execute_paid_acquisition, grant_from_demo_reservation

FP = "aa" * 32
GEO = "bb" * 32


def _identity(**overrides) -> DemoRequestIdentity:
    payload = {
        "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        "request_fingerprint": FP,
        "geometry_sha256": GEO,
        "area_id": "phoenix-demo",
    }
    payload.update(overrides)
    return DemoRequestIdentity.model_validate(payload)


def _enabled_policy(**overrides) -> DemoAllowancePolicy:
    payload = {
        "enabled": True,
        "max_total_acquisition_units": 2,
        "max_units_per_request": 1,
        "allowed_area_ids": frozenset({"phoenix-demo"}),
    }
    payload.update(overrides)
    return DemoAllowancePolicy.model_validate(payload)


def test_default_policy_is_disabled() -> None:
    policy = disabled_demo_policy()
    assert policy.enabled is False
    assert policy.max_total_acquisition_units == 0
    from app.core.config import Settings

    assert Settings.model_fields["demo_allowance_enabled"].default is False
    loaded = demo_allowance_policy_from_settings(
        Settings.model_construct(demo_allowance_enabled=False)
    )
    assert loaded.enabled is False


def test_disabled_policy_cannot_reserve() -> None:
    ledger = InMemoryDemoAllowanceLedger(disabled_demo_policy())
    decision = ledger.try_reserve(_identity(), planned_units=1, now=datetime.now(timezone.utc))
    assert decision.code == DemoAllowanceDecisionCode.ALLOWANCE_DISABLED
    assert decision.spend_authorized is False


def test_reserve_then_identical_fingerprint_joins() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy())
    now = datetime.now(timezone.utc)
    first = ledger.try_reserve(_identity(), planned_units=1, now=now)
    second = ledger.try_reserve(_identity(), planned_units=1, now=now)
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert second.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION
    assert first.reservation.reservation_id == second.reservation.reservation_id
    assert ledger.snapshot().reserved_units == 1


def test_exhausted_total_cap() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy(max_total_acquisition_units=1))
    now = datetime.now(timezone.utc)
    first = ledger.try_reserve(_identity(), planned_units=1, now=now)
    other = ledger.try_reserve(
        _identity(request_fingerprint="cc" * 32),
        planned_units=1,
        now=now,
    )
    assert first.spend_authorized is True
    assert other.code == DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED


def test_per_request_cap_blocks_before_reserve() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy(max_units_per_request=1))
    decision = ledger.try_reserve(_identity(), planned_units=2, now=datetime.now(timezone.utc))
    assert decision.code == DemoAllowanceDecisionCode.REQUEST_UNIT_CAP_EXCEEDED
    assert ledger.snapshot().reserved_units == 0


def test_unknown_area_is_unsupported() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy())
    decision = ledger.try_reserve(
        _identity(area_id="chicago-unresolved"),
        planned_units=1,
        now=datetime.now(timezone.utc),
    )
    assert decision.code == DemoAllowanceDecisionCode.UNSUPPORTED_REQUEST


def test_expired_window_fails_closed() -> None:
    now = datetime.now(timezone.utc)
    ledger = InMemoryDemoAllowanceLedger(
        _enabled_policy(valid_until=now - timedelta(minutes=1))
    )
    decision = ledger.try_reserve(_identity(), planned_units=1, now=now)
    assert decision.code == DemoAllowanceDecisionCode.ALLOWANCE_EXPIRED


def test_consume_requires_same_identity() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy())
    now = datetime.now(timezone.utc)
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=now)
    with pytest.raises(DemoAllowanceError, match="fingerprint"):
        ledger.consume(
            reserved.reservation.reservation_id,
            identity=_identity(request_fingerprint="dd" * 32),
            planned_units=1,
            now=now,
        )


def test_release_returns_capacity() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy(max_total_acquisition_units=1))
    now = datetime.now(timezone.utc)
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=now)
    ledger.release(reserved.reservation.reservation_id)
    again = ledger.try_reserve(
        _identity(request_fingerprint="ee" * 32),
        planned_units=1,
        now=now,
    )
    assert again.code == DemoAllowanceDecisionCode.ELIGIBLE


def test_concurrent_reserves_do_not_double_spend() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy(max_total_acquisition_units=1))
    now = datetime.now(timezone.utc)
    results: list[DemoAllowanceDecisionCode] = []

    def _attempt(fp: str) -> None:
        decision = ledger.try_reserve(
            _identity(request_fingerprint=fp),
            planned_units=1,
            now=now,
        )
        results.append(decision.code)

    threads = [
        Thread(target=_attempt, args=("11" * 32,)),
        Thread(target=_attempt, args=("22" * 32,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(DemoAllowanceDecisionCode.ELIGIBLE) == 1
    assert results.count(DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED) == 1
    assert ledger.snapshot().reserved_units == 1


def test_demo_reservation_becomes_fingerprint_bound_grant() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy())
    now = datetime.now(timezone.utc)
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=now)
    grant = grant_from_demo_reservation(reserved.reservation)
    gate = can_execute_paid_acquisition(
        grant,
        request_fingerprint=FP,
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        geometry_sha256=GEO,
        planned_units=1,
        now=now,
    )
    assert gate.allowed is True
    assert grant.authorization_source.value == "demo_allowance"


def test_consume_is_terminal_no_automatic_retry() -> None:
    ledger = InMemoryDemoAllowanceLedger(_enabled_policy())
    now = datetime.now(timezone.utc)
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=now)
    consumed = ledger.consume(
        reserved.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        now=now,
    )
    assert consumed.state == ReservationState.CONSUMED
    with pytest.raises(DemoAllowanceError):
        ledger.consume(
            reserved.reservation.reservation_id,
            identity=_identity(),
            planned_units=1,
            now=now,
        )
