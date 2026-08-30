"""SQLite-backed demo allowance ledger. Local file durability only.

Restart preserves RESERVED / CONSUMED rows. Enabling this ledger does
not enable hosted live or a vendor adapter. Policy remains the spend
gate; a durable file with a disabled policy still cannot reserve.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.core.durable_live import PersistenceError
from app.core.sqlite_schema import apply_durable_pragmas, apply_migrations
from app.domain.demo_allowance import (
    DemoAllowanceDecision,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoAllowanceState,
    DemoRequestIdentity,
    DemoReservation,
    ReservationState,
)
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import (
    DemoAllowanceError,
    policy_blocks_spend,
    request_supported,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_reservation(row: sqlite3.Row) -> DemoReservation:
    expires = row["expires_at"]
    return DemoReservation(
        reservation_id=row["reservation_id"],
        state=ReservationState(row["state"]),
        signal_kind=ThermalSignalKind(row["signal_kind"]),
        request_fingerprint=row["request_fingerprint"],
        geometry_sha256=row["geometry_sha256"],
        area_id=row["area_id"],
        planned_units=int(row["planned_units"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        expires_at=datetime.fromisoformat(expires) if expires else None,
    )


class SQLiteDemoAllowanceLedger:
    """J3 local reservation/consume persistence. Not hosted-live."""

    durability = "J3_SQLITE_LOCAL_FILE_NOT_HOSTED_LIVE"
    hosted_live_implied = False

    def __init__(
        self,
        policy: DemoAllowancePolicy,
        path: str | Path,
        *,
        connection: sqlite3.Connection | None = None,
        lock: Lock | None = None,
    ) -> None:
        self._policy = policy
        self._path = Path(path)
        self._owns_conn = connection is None
        if connection is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                self._path,
                check_same_thread=False,
                isolation_level=None,
            )
            self._conn.row_factory = sqlite3.Row
            apply_durable_pragmas(self._conn)
            apply_migrations(self._conn)
        else:
            self._conn = connection
        self._lock = lock or Lock()

    @property
    def policy(self) -> DemoAllowancePolicy:
        return self._policy

    def close(self) -> None:
        if self._owns_conn:
            with self._lock:
                self._conn.close()

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
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                decision = self._try_reserve_unlocked(
                    identity, planned_units=planned_units, now=moment
                )
                self._conn.execute("COMMIT")
                return decision
            except sqlite3.IntegrityError:
                self._conn.execute("ROLLBACK")
                existing = self._active_by_fingerprint(identity.request_fingerprint)
                if existing is not None:
                    return DemoAllowanceDecision(
                        code=DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION,
                        reservation=existing,
                        spend_authorized=False,
                    )
                raise PersistenceError("reservation unique constraint")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def release(self, reservation_id: str) -> DemoReservation:
        return self._transition(reservation_id, ReservationState.RELEASED)

    def expire(self, reservation_id: str) -> DemoReservation:
        return self._transition(reservation_id, ReservationState.EXPIRED)

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
            self._conn.execute("BEGIN IMMEDIATE")
            try:
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
                self._write_reservation(updated)
                self._conn.execute("COMMIT")
                return updated
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def get(self, reservation_id: str) -> DemoReservation | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM demo_reservations WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_reservation(row)

    def bind_activity_id(self, reservation_id: str, activity_id: str) -> DemoReservation:
        if not activity_id.strip():
            raise PersistenceError("activity_id is required")
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                reservation = self._require(reservation_id)
                self._conn.execute(
                    """
                    UPDATE demo_reservations
                    SET activity_id = ?
                    WHERE reservation_id = ?
                    """,
                    (activity_id, reservation_id),
                )
                self._conn.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self._conn.execute("ROLLBACK")
                raise PersistenceError(f"unique constraint: {exc}") from exc
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        bound = self.get(reservation_id)
        if bound is None:
            raise DemoAllowanceError("unknown_reservation")
        return bound

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
        existing = self._active_by_fingerprint(identity.request_fingerprint)
        if existing is not None:
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
        self._write_reservation(reservation)
        return DemoAllowanceDecision(
            code=DemoAllowanceDecisionCode.ELIGIBLE,
            reservation=reservation,
            spend_authorized=True,
        )

    def _snapshot_unlocked(self) -> DemoAllowanceState:
        reserved = 0
        consumed = 0
        for row in self._conn.execute("SELECT state, planned_units FROM demo_reservations"):
            if row["state"] == ReservationState.RESERVED.value:
                reserved += int(row["planned_units"])
            elif row["state"] == ReservationState.CONSUMED.value:
                consumed += int(row["planned_units"])
        authorized = self._policy.max_total_acquisition_units
        remaining = max(authorized - reserved - consumed, 0)
        return DemoAllowanceState(
            authorized_total_units=authorized,
            reserved_units=reserved,
            consumed_units=consumed,
            remaining_units=remaining,
            restart_resets_remaining=False,
            durability="J3_SQLITE_LOCAL_FILE_NOT_HOSTED_LIVE",
        )

    def _transition(
        self, reservation_id: str, nxt: ReservationState
    ) -> DemoReservation:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                reservation = self._require(reservation_id)
                if reservation.state != ReservationState.RESERVED:
                    raise DemoAllowanceError(f"cannot {nxt.value.lower()} {reservation.state.value}")
                updated = reservation.model_copy(update={"state": nxt})
                self._write_reservation(updated)
                self._conn.execute("COMMIT")
                return updated
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def _active_by_fingerprint(self, fingerprint: str) -> DemoReservation | None:
        row = self._conn.execute(
            """
            SELECT * FROM demo_reservations
            WHERE request_fingerprint = ? AND state = ?
            """,
            (fingerprint, ReservationState.RESERVED.value),
        ).fetchone()
        if row is None:
            return None
        return _row_to_reservation(row)

    def _require(self, reservation_id: str) -> DemoReservation:
        row = self._conn.execute(
            "SELECT * FROM demo_reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        if row is None:
            raise DemoAllowanceError("unknown_reservation")
        return _row_to_reservation(row)

    def _write_reservation(self, reservation: DemoReservation) -> None:
        self._conn.execute(
            """
            INSERT INTO demo_reservations (
                reservation_id, state, signal_kind, request_fingerprint,
                geometry_sha256, area_id, planned_units, created_at, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(reservation_id) DO UPDATE SET
                state = excluded.state,
                signal_kind = excluded.signal_kind,
                request_fingerprint = excluded.request_fingerprint,
                geometry_sha256 = excluded.geometry_sha256,
                area_id = excluded.area_id,
                planned_units = excluded.planned_units,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (
                reservation.reservation_id,
                reservation.state.value,
                reservation.signal_kind.value,
                reservation.request_fingerprint,
                reservation.geometry_sha256,
                reservation.area_id,
                reservation.planned_units,
                reservation.created_at.isoformat(),
                reservation.expires_at.isoformat() if reservation.expires_at else None,
            ),
        )
