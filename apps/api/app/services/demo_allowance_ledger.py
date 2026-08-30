"""Atomic in-memory demo-allowance ledger. J0 only. Restart resets remaining.

Not production-durable. Lost reservations must not auto-resume paid work.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.domain.demo_allowance import (
    AllowanceRestartReport,
    CachedDemoResult,
    ConsumeAfterCacheResult,
    DemoAllowanceDecision,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoAllowanceState,
    DemoRequestIdentity,
    DemoReservation,
    ReservationState,
)
from app.domain.signals import ThermalSignalKind


class DemoAllowanceError(ValueError):
    """Illegal reservation transition or identity mismatch."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def policy_blocks_spend(policy: DemoAllowancePolicy, *, now: datetime) -> DemoAllowanceDecisionCode | None:
    if not policy.is_structurally_valid():
        return DemoAllowanceDecisionCode.POLICY_INVALID
    if not policy.enabled:
        return DemoAllowanceDecisionCode.ALLOWANCE_DISABLED
    if policy.max_total_acquisition_units <= 0 or policy.max_units_per_request <= 0:
        return DemoAllowanceDecisionCode.ALLOWANCE_DISABLED
    if policy.valid_from is not None and now < policy.valid_from:
        return DemoAllowanceDecisionCode.ALLOWANCE_EXPIRED
    if policy.valid_until is not None and now >= policy.valid_until:
        return DemoAllowanceDecisionCode.ALLOWANCE_EXPIRED
    return None


def request_supported(policy: DemoAllowancePolicy, identity: DemoRequestIdentity) -> bool:
    if identity.signal_kind not in policy.allowed_signal_kinds:
        return False
    if identity.analytic not in policy.allowed_analytics:
        return False
    if identity.granularity_m not in policy.allowed_granularities_m:
        return False
    if identity.temporal_mode not in policy.allowed_temporal_modes:
        return False
    if identity.area_id not in policy.allowed_area_ids:
        return False
    return True


class InMemoryDemoAllowanceLedger:
    """Process-local check+reserve. Provider-neutral so a J3 store can replace it."""

    durability = "J0_PROCESS_LOCAL_NOT_DURABLE"

    def __init__(self, policy: DemoAllowancePolicy) -> None:
        self._policy = policy
        self._lock = Lock()
        self._reservations: dict[str, DemoReservation] = {}
        self._active_by_fingerprint: dict[str, str] = {}
        self._cached_results: dict[str, CachedDemoResult] = {}

    @property
    def policy(self) -> DemoAllowancePolicy:
        return self._policy

    def snapshot(self) -> DemoAllowanceState:
        with self._lock:
            return self._snapshot_unlocked()

    def try_reserve(
        self,
        identity: DemoRequestIdentity,
        *,
        planned_units: int,
        now: datetime | None = None,
    ) -> DemoAllowanceDecision:
        moment = now or _now()
        with self._lock:
            return self._try_reserve_unlocked(identity, planned_units=planned_units, now=moment)

    def release(self, reservation_id: str) -> DemoReservation:
        with self._lock:
            reservation = self._require(reservation_id)
            if reservation.state != ReservationState.RESERVED:
                raise DemoAllowanceError(f"cannot release {reservation.state.value}")
            updated = reservation.model_copy(update={"state": ReservationState.RELEASED})
            self._reservations[reservation_id] = updated
            self._forget_active(reservation)
            return updated

    def expire(self, reservation_id: str) -> DemoReservation:
        with self._lock:
            reservation = self._require(reservation_id)
            if reservation.state != ReservationState.RESERVED:
                raise DemoAllowanceError(f"cannot expire {reservation.state.value}")
            updated = reservation.model_copy(update={"state": ReservationState.EXPIRED})
            self._reservations[reservation_id] = updated
            self._forget_active(reservation)
            return updated

    def consume(
        self,
        reservation_id: str,
        *,
        identity: DemoRequestIdentity,
        planned_units: int,
        now: datetime | None = None,
    ) -> DemoReservation:
        moment = now or _now()
        with self._lock:
            reservation = self._require(reservation_id)
            if reservation.state != ReservationState.RESERVED:
                raise DemoAllowanceError(f"cannot consume {reservation.state.value}")
            blocked = policy_blocks_spend(self._policy, now=moment)
            if blocked is not None:
                raise DemoAllowanceError(blocked.value)
            if reservation.request_fingerprint != identity.request_fingerprint:
                raise DemoAllowanceError("fingerprint_mismatch")
            if reservation.geometry_sha256 != identity.geometry_sha256:
                raise DemoAllowanceError("geometry_mismatch")
            if reservation.signal_kind != identity.signal_kind:
                raise DemoAllowanceError("signal_kind_mismatch")
            if reservation.area_id != identity.area_id:
                raise DemoAllowanceError("area_mismatch")
            if reservation.planned_units != planned_units:
                raise DemoAllowanceError("planned_units_mismatch")
            if reservation.expires_at is not None and moment >= reservation.expires_at:
                raise DemoAllowanceError("reservation_expired")
            updated = reservation.model_copy(update={"state": ReservationState.CONSUMED})
            self._reservations[reservation_id] = updated
            self._forget_active(reservation)
            return updated

    def get(self, reservation_id: str) -> DemoReservation | None:
        with self._lock:
            return self._reservations.get(reservation_id)

    def has_active_reservation(self, request_fingerprint: str) -> bool:
        """Join peek. LIVE-K uses this so duplicate reserve does not consume a slot."""
        with self._lock:
            return request_fingerprint in self._active_by_fingerprint

    def expire_stale(self, *, now: datetime) -> list[DemoReservation]:
        with self._lock:
            return self._expire_stale_unlocked(now)

    def persist_cached_result(
        self,
        *,
        identity: DemoRequestIdentity,
        reservation_id: str,
        payload: dict,
        now: datetime | None = None,
    ) -> CachedDemoResult:
        moment = now or _now()
        with self._lock:
            reservation = self._require(reservation_id)
            if reservation.request_fingerprint != identity.request_fingerprint:
                raise DemoAllowanceError("fingerprint_mismatch")
            if reservation.geometry_sha256 != identity.geometry_sha256:
                raise DemoAllowanceError("geometry_mismatch")
            existing = self._cached_results.get(identity.request_fingerprint)
            if existing is not None:
                if existing.reservation_id != reservation_id:
                    raise DemoAllowanceError("cached_result_reservation_mismatch")
                return existing
            cached = CachedDemoResult(
                request_fingerprint=identity.request_fingerprint,
                geometry_sha256=identity.geometry_sha256,
                reservation_id=reservation_id,
                payload=dict(payload),
                cached_at=moment,
            )
            self._cached_results[identity.request_fingerprint] = cached
            return cached

    def get_cached_result(self, request_fingerprint: str) -> CachedDemoResult | None:
        with self._lock:
            return self._cached_results.get(request_fingerprint)

    def recover_after_restart(self, *, now: datetime) -> AllowanceRestartReport:
        with self._lock:
            expired = self._expire_stale_unlocked(now)
            reserved_ids = [
                item.reservation_id
                for item in self._reservations.values()
                if item.state == ReservationState.RESERVED
            ]
            consumed_ids = [
                item.reservation_id
                for item in self._reservations.values()
                if item.state == ReservationState.CONSUMED
            ]
            snap = self._snapshot_unlocked()
            return AllowanceRestartReport(
                expired_reservation_ids=[item.reservation_id for item in expired],
                reserved_ids=reserved_ids,
                consumed_ids=consumed_ids,
                reserved_units=snap.reserved_units,
                consumed_units=snap.consumed_units,
            )

    def consume_after_cached_result(
        self,
        reservation_id: str,
        *,
        identity: DemoRequestIdentity,
        planned_units: int,
        now: datetime | None = None,
    ) -> ConsumeAfterCacheResult:
        del now
        with self._lock:
            cached = self._cached_results.get(identity.request_fingerprint)
            if cached is None:
                raise DemoAllowanceError("cached_result_missing")
            if cached.reservation_id != reservation_id:
                raise DemoAllowanceError("cached_result_reservation_mismatch")
            reservation = self._require(reservation_id)
            if reservation.state == ReservationState.CONSUMED:
                return ConsumeAfterCacheResult(
                    reservation=reservation,
                    cached=cached,
                    already_consumed=True,
                )
            if reservation.state != ReservationState.RESERVED:
                raise DemoAllowanceError(f"cannot consume {reservation.state.value}")
            if reservation.request_fingerprint != identity.request_fingerprint:
                raise DemoAllowanceError("fingerprint_mismatch")
            if reservation.geometry_sha256 != identity.geometry_sha256:
                raise DemoAllowanceError("geometry_mismatch")
            if reservation.planned_units != planned_units:
                raise DemoAllowanceError("planned_units_mismatch")
            updated = reservation.model_copy(update={"state": ReservationState.CONSUMED})
            self._reservations[reservation_id] = updated
            self._forget_active(reservation)
            replay = self._cached_results.get(identity.request_fingerprint)
            if replay is None:
                raise DemoAllowanceError("cached_result_lost")
            return ConsumeAfterCacheResult(
                reservation=updated,
                cached=replay,
                already_consumed=False,
            )

    def close(self) -> None:
        return None

    def _expire_stale_unlocked(self, now: datetime) -> list[DemoReservation]:
        expired: list[DemoReservation] = []
        for reservation_id, reservation in list(self._reservations.items()):
            if (
                reservation.state == ReservationState.RESERVED
                and reservation.expires_at is not None
                and now >= reservation.expires_at
            ):
                updated = reservation.model_copy(update={"state": ReservationState.EXPIRED})
                self._reservations[reservation_id] = updated
                self._forget_active(reservation)
                expired.append(updated)
        return expired

    def _try_reserve_unlocked(
        self,
        identity: DemoRequestIdentity,
        *,
        planned_units: int,
        now: datetime,
    ) -> DemoAllowanceDecision:
        blocked = policy_blocks_spend(self._policy, now=now)
        if blocked is not None:
            return DemoAllowanceDecision(code=blocked, spend_authorized=False)
        if identity.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            return DemoAllowanceDecision(
                code=DemoAllowanceDecisionCode.UNSUPPORTED_REQUEST,
                spend_authorized=False,
            )
        if not request_supported(self._policy, identity):
            return DemoAllowanceDecision(
                code=DemoAllowanceDecisionCode.UNSUPPORTED_REQUEST,
                spend_authorized=False,
            )
        if planned_units <= 0:
            return DemoAllowanceDecision(
                code=DemoAllowanceDecisionCode.POLICY_INVALID,
                spend_authorized=False,
            )
        if planned_units > self._policy.max_units_per_request:
            return DemoAllowanceDecision(
                code=DemoAllowanceDecisionCode.REQUEST_UNIT_CAP_EXCEEDED,
                spend_authorized=False,
            )
        existing_id = self._active_by_fingerprint.get(identity.request_fingerprint)
        if existing_id is not None:
            existing = self._reservations[existing_id]
            if (
                existing.geometry_sha256 == identity.geometry_sha256
                and existing.area_id == identity.area_id
                and existing.planned_units == planned_units
            ):
                return DemoAllowanceDecision(
                    code=DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION,
                    reservation=existing,
                    spend_authorized=False,
                )
        remaining = self._snapshot_unlocked().remaining_units
        if planned_units > remaining:
            return DemoAllowanceDecision(
                code=DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED,
                spend_authorized=False,
            )
        reservation = DemoReservation(
            reservation_id=f"res_{uuid4().hex[:12]}",
            state=ReservationState.RESERVED,
            signal_kind=identity.signal_kind,
            request_fingerprint=identity.request_fingerprint,
            geometry_sha256=identity.geometry_sha256,
            area_id=identity.area_id,
            planned_units=planned_units,
            created_at=now,
            expires_at=self._policy.valid_until,
        )
        self._reservations[reservation.reservation_id] = reservation
        self._active_by_fingerprint[identity.request_fingerprint] = reservation.reservation_id
        return DemoAllowanceDecision(
            code=DemoAllowanceDecisionCode.ELIGIBLE,
            reservation=reservation,
            spend_authorized=True,
        )

    def _snapshot_unlocked(self) -> DemoAllowanceState:
        reserved = 0
        consumed = 0
        for reservation in self._reservations.values():
            if reservation.state == ReservationState.RESERVED:
                reserved += reservation.planned_units
            elif reservation.state == ReservationState.CONSUMED:
                consumed += reservation.planned_units
        authorized = self._policy.max_total_acquisition_units
        remaining = max(authorized - reserved - consumed, 0)
        return DemoAllowanceState(
            authorized_total_units=authorized,
            reserved_units=reserved,
            consumed_units=consumed,
            remaining_units=remaining,
        )

    def _require(self, reservation_id: str) -> DemoReservation:
        reservation = self._reservations.get(reservation_id)
        if reservation is None:
            raise DemoAllowanceError("unknown_reservation")
        return reservation

    def _forget_active(self, reservation: DemoReservation) -> None:
        current = self._active_by_fingerprint.get(reservation.request_fingerprint)
        if current == reservation.reservation_id:
            del self._active_by_fingerprint[reservation.request_fingerprint]
