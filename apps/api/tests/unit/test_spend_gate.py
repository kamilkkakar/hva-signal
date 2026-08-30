"""Valid request does not imply vendor spend."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.job_lifecycle import CostAuthorizationState
from app.domain.signals import ThermalSignalKind
from app.services.spend_gate import (
    SpendGateError,
    approve_grant,
    can_execute_paid_acquisition,
    compare_planned_units_to_cap,
    consume_grant,
    deny_grant,
    expire_grant,
    mark_insufficient,
    waiting_grant,
)

FP = "aa" * 32
GEO = "bb" * 32
KIND = ThermalSignalKind.SELECTED_TIME_SNAPSHOT


def _waiting() -> object:
    return waiting_grant(
        signal_kind=KIND,
        request_fingerprint=FP,
        geometry_sha256=GEO,
        requested_units=1,
        planned_acquisition_units=1,
    )


def test_waiting_grant_has_no_authorized_cap() -> None:
    grant = _waiting()
    assert grant.authorized_max_units is None
    assert grant.state == CostAuthorizationState.WAITING_FOR_APPROVAL


def test_unapproved_cannot_execute() -> None:
    grant = _waiting()
    result = can_execute_paid_acquisition(
        grant,
        request_fingerprint=FP,
        signal_kind=KIND,
        geometry_sha256=GEO,
        planned_units=1,
        now=datetime.now(timezone.utc),
    )
    assert result.allowed is False


def test_approved_is_eligible() -> None:
    grant = approve_grant(
        _waiting(),
        authorized_max_units=2,
        approval_ref="op-1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    result = can_execute_paid_acquisition(
        grant,
        request_fingerprint=FP,
        signal_kind=KIND,
        geometry_sha256=GEO,
        planned_units=1,
        now=datetime.now(timezone.utc),
    )
    assert result.allowed is True


def test_denied_cannot_become_running() -> None:
    denied = deny_grant(_waiting(), reason="operator denied")
    with pytest.raises(SpendGateError, match="illegal spend transition"):
        approve_grant(
            denied,
            authorized_max_units=1,
            approval_ref="op-1",
            expires_at=None,
        )


def test_expired_cannot_execute() -> None:
    grant = approve_grant(
        _waiting(),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    result = can_execute_paid_acquisition(
        grant,
        request_fingerprint=FP,
        signal_kind=KIND,
        geometry_sha256=GEO,
        planned_units=1,
        now=datetime.now(timezone.utc),
    )
    assert result.allowed is False
    assert result.reason == "expired"
    expired = expire_grant(
        approve_grant(
            waiting_grant(
                signal_kind=KIND,
                request_fingerprint=FP,
                geometry_sha256=GEO,
                requested_units=1,
                planned_acquisition_units=1,
            ),
            authorized_max_units=1,
            approval_ref="op-2",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    assert expired.state == CostAuthorizationState.EXPIRED


def test_fingerprint_and_geometry_must_match() -> None:
    grant = approve_grant(
        _waiting(),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=None,
    )
    assert (
        can_execute_paid_acquisition(
            grant,
            request_fingerprint="cc" * 32,
            signal_kind=KIND,
            geometry_sha256=GEO,
            planned_units=1,
            now=datetime.now(timezone.utc),
        ).allowed
        is False
    )
    assert (
        can_execute_paid_acquisition(
            grant,
            request_fingerprint=FP,
            signal_kind=KIND,
            geometry_sha256="dd" * 32,
            planned_units=1,
            now=datetime.now(timezone.utc),
        ).reason
        == "geometry_mismatch"
    )


def test_partition_overrun_stops_before_spend() -> None:
    grant = approve_grant(
        _waiting(),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=None,
    )
    result = can_execute_paid_acquisition(
        grant,
        request_fingerprint=FP,
        signal_kind=KIND,
        geometry_sha256=GEO,
        planned_units=3,
        now=datetime.now(timezone.utc),
    )
    assert result.allowed is False
    assert result.reason == "planned_units_exceed_cap"
    assert compare_planned_units_to_cap(grant, planned_units=3) == (
        CostAuthorizationState.INSUFFICIENT
    )
    insufficient = mark_insufficient(grant, planned_acquisition_units=3)
    assert insufficient.state == CostAuthorizationState.INSUFFICIENT


def test_consume_cannot_exceed_cap() -> None:
    grant = approve_grant(
        _waiting(),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=None,
    )
    consumed = consume_grant(grant, units=1)
    assert consumed.state == CostAuthorizationState.CONSUMED
    with pytest.raises(SpendGateError):
        consume_grant(grant, units=2)
