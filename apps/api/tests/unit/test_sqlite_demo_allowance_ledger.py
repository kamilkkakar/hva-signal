"""SQLite allowance ledger: reservations survive restart; policy still gates spend."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.durable_live import PersistenceError
from app.domain.demo_allowance import (
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
    disabled_demo_policy,
)
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import DemoAllowanceError
from app.services.sqlite_demo_allowance_ledger import SQLiteDemoAllowanceLedger

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


def test_sqlite_does_not_enable_spend_when_policy_disabled(tmp_path) -> None:
    ledger = SQLiteDemoAllowanceLedger(disabled_demo_policy(), tmp_path / "allow.sqlite")
    assert ledger.hosted_live_implied is False
    decision = ledger.try_reserve(_identity(), planned_units=1, now=datetime.now(timezone.utc))
    assert decision.code == DemoAllowanceDecisionCode.ALLOWANCE_DISABLED
    assert decision.spend_authorized is False
    ledger.close()


def test_reservation_survives_restart_and_does_not_double_consume(tmp_path) -> None:
    path = tmp_path / "allow.sqlite"
    now = datetime.now(timezone.utc)
    ledger = SQLiteDemoAllowanceLedger(_enabled_policy(), path)
    first = ledger.try_reserve(_identity(), planned_units=1, now=now)
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    reservation_id = first.reservation.reservation_id
    assert ledger.snapshot().restart_resets_remaining is False
    assert ledger.snapshot().durability == "J3_SQLITE_LOCAL_FILE_NOT_HOSTED_LIVE"
    assert ledger.snapshot().reserved_units == 1
    ledger.close()

    reopened = SQLiteDemoAllowanceLedger(_enabled_policy(), path)
    loaded = reopened.get(reservation_id)
    assert loaded is not None
    assert loaded.state == ReservationState.RESERVED
    assert reopened.snapshot().reserved_units == 1
    joined = reopened.try_reserve(_identity(), planned_units=1, now=now)
    assert joined.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION
    consumed = reopened.consume(
        reservation_id,
        identity=_identity(),
        planned_units=1,
        now=now,
    )
    assert consumed.state == ReservationState.CONSUMED
    with pytest.raises(DemoAllowanceError, match="consume"):
        reopened.consume(
            reservation_id,
            identity=_identity(),
            planned_units=1,
            now=now,
        )
    reopened.close()

    again = SQLiteDemoAllowanceLedger(_enabled_policy(), path)
    assert again.get(reservation_id).state == ReservationState.CONSUMED
    assert again.snapshot().consumed_units == 1
    assert again.snapshot().reserved_units == 0
    again.close()


def test_activity_id_unique_on_reservation(tmp_path) -> None:
    path = tmp_path / "allow.sqlite"
    now = datetime.now(timezone.utc)
    ledger = SQLiteDemoAllowanceLedger(
        _enabled_policy(max_total_acquisition_units=2), path
    )
    one = ledger.try_reserve(_identity(), planned_units=1, now=now)
    two = ledger.try_reserve(
        _identity(request_fingerprint="cc" * 32),
        planned_units=1,
        now=now,
    )
    ledger.bind_activity_id(one.reservation.reservation_id, "act-shared")
    with pytest.raises(PersistenceError, match="unique"):
        ledger.bind_activity_id(two.reservation.reservation_id, "act-shared")
    ledger.close()
