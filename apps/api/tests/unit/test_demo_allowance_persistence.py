"""Durable allowance store: restart, reserve≠consume, cache-before-consume."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Thread

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.domain.demo_allowance import (
    AllowanceDurability,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
    disabled_demo_policy,
)
from app.domain.requests import AnalysisRequest
from app.domain.signals import ThermalSignalKind
from app.schemas.two_signal_public import TwoSignalPublicationRequest
from app.services.allowance_client_denylist import client_set_forbidden_allowance_keys
from app.services.demo_allowance_ledger import DemoAllowanceError
from app.services.demo_allowance_recovery import (
    recover_after_cache_before_consume,
    recover_reservations_after_restart,
)
from app.services.demo_allowance_store import SqliteDemoAllowanceStore
from app.services.demo_policy_config import (
    demo_allowance_ledger_from_settings,
    demo_allowance_policy_from_settings,
)
from app.services.spend_threat_guards import client_flags_cannot_authorize

FP = "aa" * 32
GEO = "bb" * 32
CACHED_PAYLOAD = {"zones": [{"zone_id": "z1", "mean_temperature_c": 41.2}]}


def _identity(**overrides) -> DemoRequestIdentity:
    payload = {
        "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        "request_fingerprint": FP,
        "geometry_sha256": GEO,
        "area_id": "phoenix-demo",
    }
    payload.update(overrides)
    return DemoRequestIdentity.model_validate(payload)


def _policy(**overrides) -> DemoAllowancePolicy:
    payload = {
        "enabled": True,
        "max_total_acquisition_units": 4,
        "max_units_per_request": 1,
        "allowed_area_ids": frozenset({"phoenix-demo"}),
    }
    payload.update(overrides)
    return DemoAllowancePolicy.model_validate(payload)


def _store(path, policy=None, **kwargs) -> SqliteDemoAllowanceStore:
    return SqliteDemoAllowanceStore(path, policy or _policy(), **kwargs)


def test_hosted_live_and_durable_store_default_off() -> None:
    fields = Settings.model_fields
    assert fields["demo_allowance_enabled"].default is False
    assert fields["demo_allowance_store_path"].default == ""
    assert int(fields["demo_allowance_max_total_units"].default) == 0
    loaded = demo_allowance_policy_from_settings(
        Settings.model_construct(demo_allowance_enabled=False)
    )
    assert loaded.enabled is False
    assert disabled_demo_policy().enabled is False


def test_store_path_does_not_enable_hosted_live(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    settings = Settings.model_construct(
        demo_allowance_enabled=False,
        demo_allowance_store_path=str(path),
        demo_allowance_max_total_units=9,
    )
    ledger = demo_allowance_ledger_from_settings(settings)
    try:
        assert ledger.durability == AllowanceDurability.J3_LOCAL_SQLITE_DURABLE.value
        decision = ledger.try_reserve(_identity(), planned_units=1, now=datetime.now(timezone.utc))
        assert decision.code == DemoAllowanceDecisionCode.ALLOWANCE_DISABLED
        assert decision.spend_authorized is False
    finally:
        ledger.close()


def test_empty_store_path_stays_process_local() -> None:
    ledger = demo_allowance_ledger_from_settings(
        Settings.model_construct(demo_allowance_enabled=True, demo_allowance_store_path="")
    )
    assert ledger.durability == "J0_PROCESS_LOCAL_NOT_DURABLE"
    ledger.close()


def test_reserve_is_not_consume_and_survives_restart(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    first = _store(path, now=now)
    reserved = first.try_reserve(_identity(), planned_units=1, now=now)
    assert reserved.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert reserved.reservation is not None
    assert reserved.reservation.state == ReservationState.RESERVED
    assert first.snapshot().consumed_units == 0
    first.close()

    restarted = _store(path, now=now)
    try:
        snap = restarted.snapshot()
        assert snap.durability == AllowanceDurability.J3_LOCAL_SQLITE_DURABLE
        assert snap.restart_resets_remaining is False
        assert snap.reserved_units == 1
        assert snap.consumed_units == 0
        loaded = restarted.get(reserved.reservation.reservation_id)
        assert loaded is not None
        assert loaded.state == ReservationState.RESERVED
        report = recover_reservations_after_restart(restarted, now=now)
        assert report.auto_consumed is False
        assert report.auto_resumed_paid_work is False
        assert reserved.reservation.reservation_id in report.reserved_ids
    finally:
        restarted.close()


def test_consume_survives_restart(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    first = _store(path, now=now)
    reserved = first.try_reserve(_identity(), planned_units=1, now=now)
    assert reserved.reservation is not None
    first.consume(
        reserved.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        now=now,
    )
    first.close()

    restarted = _store(path, now=now)
    try:
        snap = restarted.snapshot()
        assert snap.consumed_units == 1
        assert snap.reserved_units == 0
        again = restarted.try_reserve(
            _identity(request_fingerprint="cc" * 32),
            planned_units=1,
            now=now,
        )
        assert again.code == DemoAllowanceDecisionCode.ELIGIBLE
        with pytest.raises(DemoAllowanceError, match="cannot consume CONSUMED"):
            restarted.consume(
                reserved.reservation.reservation_id,
                identity=_identity(),
                planned_units=1,
                now=now,
            )
    finally:
        restarted.close()


def test_crash_after_reserve_does_not_leak_unbounded_or_double_consume(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    policy = _policy(max_total_acquisition_units=50)
    crashed = _store(path, policy, reservation_ttl_seconds=30, max_open_reservations=2, now=now)
    first = crashed.try_reserve(_identity(), planned_units=1, now=now)
    second = crashed.try_reserve(
        _identity(request_fingerprint="cc" * 32),
        planned_units=1,
        now=now,
    )
    third = crashed.try_reserve(
        _identity(request_fingerprint="dd" * 32),
        planned_units=1,
        now=now,
    )
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert second.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert third.code == DemoAllowanceDecisionCode.RESERVATION_SLOT_EXHAUSTED
    assert crashed.snapshot().reserved_units == 2
    crashed.close()

    later = now + timedelta(seconds=31)
    recovered = _store(
        path, policy, reservation_ttl_seconds=30, max_open_reservations=2, now=later
    )
    try:
        report = recovered.last_restart_report
        assert len(report.expired_reservation_ids) == 2
        assert report.reserved_units == 0
        assert report.consumed_units == 0
        assert recover_reservations_after_restart(recovered, now=later).auto_consumed is False
        assert recovered.get(first.reservation.reservation_id).state == ReservationState.EXPIRED
        with pytest.raises(DemoAllowanceError, match="cannot consume EXPIRED"):
            recovered.consume(
                first.reservation.reservation_id,
                identity=_identity(),
                planned_units=1,
                now=later,
            )
        retry = recovered.try_reserve(_identity(), planned_units=1, now=later)
        assert retry.code == DemoAllowanceDecisionCode.ELIGIBLE
        assert retry.reservation.reservation_id != first.reservation.reservation_id
        assert recovered.snapshot().reserved_units == 1
        assert recovered.snapshot().consumed_units == 0
    finally:
        recovered.close()


def test_crash_after_cache_before_consume_recovers_without_double_spend(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    first = _store(path, now=now)
    reserved = first.try_reserve(_identity(), planned_units=1, now=now)
    assert reserved.reservation is not None
    cached = first.persist_cached_result(
        identity=_identity(),
        reservation_id=reserved.reservation.reservation_id,
        payload=CACHED_PAYLOAD,
        now=now,
    )
    assert first.get(reserved.reservation.reservation_id).state == ReservationState.RESERVED
    assert cached.payload == CACHED_PAYLOAD
    first.close()

    recovered = _store(path, now=now)
    try:
        still = recovered.get_cached_result(FP)
        assert still is not None
        assert still.payload == CACHED_PAYLOAD
        result = recover_after_cache_before_consume(
            recovered,
            reservation_id=reserved.reservation.reservation_id,
            identity=_identity(),
            planned_units=1,
            now=now,
        )
        assert result.already_consumed is False
        assert result.double_spend is False
        assert result.cache_lost is False
        assert result.reservation.state == ReservationState.CONSUMED
        assert result.cached.payload == CACHED_PAYLOAD
        assert recovered.snapshot().consumed_units == 1

        replay = recover_after_cache_before_consume(
            recovered,
            reservation_id=reserved.reservation.reservation_id,
            identity=_identity(),
            planned_units=1,
            now=now,
        )
        assert replay.already_consumed is True
        assert replay.double_spend is False
        assert replay.cached.payload == CACHED_PAYLOAD
        assert recovered.snapshot().consumed_units == 1
        assert recovered.get_cached_result(FP).payload == CACHED_PAYLOAD
    finally:
        recovered.close()


def test_cache_after_result_survives_even_if_reservation_ttl_lapses(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    first = _store(path, reservation_ttl_seconds=10, now=now)
    reserved = first.try_reserve(_identity(), planned_units=1, now=now)
    first.persist_cached_result(
        identity=_identity(),
        reservation_id=reserved.reservation.reservation_id,
        payload=CACHED_PAYLOAD,
        now=now,
    )
    first.close()

    later = now + timedelta(seconds=11)
    recovered = _store(path, reservation_ttl_seconds=10, now=later)
    try:
        assert recovered.get(reserved.reservation.reservation_id).state == ReservationState.EXPIRED
        assert recovered.get_cached_result(FP).payload == CACHED_PAYLOAD
        with pytest.raises(DemoAllowanceError, match="cannot consume EXPIRED"):
            recover_after_cache_before_consume(
                recovered,
                reservation_id=reserved.reservation.reservation_id,
                identity=_identity(),
                planned_units=1,
                now=later,
            )
        assert recovered.snapshot().consumed_units == 0
        assert recovered.get_cached_result(FP).payload == CACHED_PAYLOAD
    finally:
        recovered.close()


def test_identical_fingerprint_joins_across_restart(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    first = _store(path, now=now)
    reserved = first.try_reserve(_identity(), planned_units=1, now=now)
    first.close()
    restarted = _store(path, now=now)
    try:
        joined = restarted.try_reserve(_identity(), planned_units=1, now=now)
        assert joined.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION
        assert joined.reservation.reservation_id == reserved.reservation.reservation_id
        assert joined.spend_authorized is False
        assert restarted.snapshot().reserved_units == 1
    finally:
        restarted.close()


def test_concurrent_sqlite_reserves_do_not_double_spend(tmp_path) -> None:
    path = tmp_path / "allowance.sqlite"
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    store = _store(path, _policy(max_total_acquisition_units=1), now=now)
    codes: list[DemoAllowanceDecisionCode] = []

    def _attempt(fp: str) -> None:
        decision = store.try_reserve(
            _identity(request_fingerprint=fp),
            planned_units=1,
            now=now,
        )
        codes.append(decision.code)

    threads = [Thread(target=_attempt, args=("11" * 32,)), Thread(target=_attempt, args=("22" * 32,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    try:
        assert codes.count(DemoAllowanceDecisionCode.ELIGIBLE) == 1
        assert codes.count(DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED) == 1
        assert store.snapshot().reserved_units == 1
    finally:
        store.close()


def test_client_cannot_set_allowance_budget_key_force_live_approval_or_reservation() -> None:
    forbidden = {
        "allowance_cap": 99,
        "budget": 500,
        "key": "sk-client",
        "force_live": True,
        "operator_approval": True,
        "reservation_state": "CONSUMED",
    }
    assert set(client_set_forbidden_allowance_keys(forbidden)) == set(forbidden)
    nested = {"signals": {"selected_time": {"reservation_state": "RESERVED", "force_live": True}}}
    assert "reservation_state" in client_set_forbidden_allowance_keys(nested)
    assert "force_live" in client_flags_cannot_authorize(nested)

    base = {
        "contract_version": "hva-signal-two-signal-job-v1",
        "area_id": "phoenix-demo",
        "signals": {"selected_time": {"target_timestamp": "2024-07-15T15:00:00"}},
        "timezone": "America/Phoenix",
    }
    for key, value in forbidden.items():
        with pytest.raises(ValidationError):
            TwoSignalPublicationRequest.model_validate({**base, key: value})
        with pytest.raises(ValidationError):
            TwoSignalPublicationRequest.model_validate(
                {
                    **base,
                    "signals": {
                        "selected_time": {
                            "target_timestamp": "2024-07-15T15:00:00",
                            key: value,
                        }
                    },
                }
            )

    analysis = {
        "area_id": "phoenix-demo",
        "analysis_time": "2024-07-15T03:00:00",
        "analysis_mode": "operational",
        "horizon_hours": 0,
        "granularity_m": 100,
    }
    for key, value in forbidden.items():
        with pytest.raises(ValidationError):
            AnalysisRequest.model_validate({**analysis, key: value})


def test_client_cannot_force_reservation_state_on_store(tmp_path) -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    store = _store(tmp_path / "allowance.sqlite", now=now)
    try:
        reserved = store.try_reserve(_identity(), planned_units=1, now=now)
        assert reserved.reservation.state == ReservationState.RESERVED
        with pytest.raises(TypeError):
            store.try_reserve(  # type: ignore[misc]
                _identity(),
                planned_units=1,
                now=now,
                state=ReservationState.CONSUMED,
            )
    finally:
        store.close()
