"""J3 local SQLite demo-allowance store. Reservations and consumes survive restart.

Reserve is not consume. Opening the file never auto-resumes paid work.
A store path does not enable hosted live — DemoAllowancePolicy.enabled does.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.domain.demo_allowance import (
    AllowanceDurability,
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
from app.services.demo_allowance_ledger import DemoAllowanceError, policy_blocks_spend, request_supported

SCHEMA_VERSION = "hva-signal-allowance-store-v1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS allowance_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    signal_kind TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    geometry_sha256 TEXT NOT NULL,
    area_id TEXT NOT NULL,
    planned_units INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    consumed_at TEXT,
    released_at TEXT,
    expired_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reservations_active_fingerprint
    ON reservations(request_fingerprint) WHERE state = 'RESERVED';

CREATE TABLE IF NOT EXISTS cached_results (
    request_fingerprint TEXT PRIMARY KEY,
    geometry_sha256 TEXT NOT NULL,
    reservation_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    cached_at TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class SqliteDemoAllowanceStore:
    """Crash-safe local ledger. Not multi-instance. Not a vendor client."""

    durability = AllowanceDurability.J3_LOCAL_SQLITE_DURABLE.value

    def __init__(
        self,
        path: str | Path,
        policy: DemoAllowancePolicy,
        *,
        reservation_ttl_seconds: int = 900,
        max_open_reservations: int = 8,
        now: datetime | None = None,
    ) -> None:
        if reservation_ttl_seconds < 1:
            raise DemoAllowanceError("reservation_ttl_seconds_invalid")
        if max_open_reservations < 1:
            raise DemoAllowanceError("max_open_reservations_invalid")
        self._policy = policy
        self._reservation_ttl_seconds = reservation_ttl_seconds
        self._max_open_reservations = max_open_reservations
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.execute(
            "INSERT OR IGNORE INTO allowance_meta(key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        self.last_restart_report = self.recover_after_restart(now=now or _now())

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
            return self._transition(
                reservation,
                ReservationState.RELEASED,
                released_at=_now(),
            )

    def expire(self, reservation_id: str) -> DemoReservation:
        with self._lock:
            reservation = self._require(reservation_id)
            if reservation.state != ReservationState.RESERVED:
                raise DemoAllowanceError(f"cannot expire {reservation.state.value}")
            return self._transition(
                reservation,
                ReservationState.EXPIRED,
                expired_at=_now(),
            )

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
            return self._consume_unlocked(
                reservation_id,
                identity=identity,
                planned_units=planned_units,
                now=moment,
                ignore_expiry=False,
            )

    def get(self, reservation_id: str) -> DemoReservation | None:
        with self._lock:
            return self._get_unlocked(reservation_id)

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
        """Commit cache without consuming. Crash after this must not lose the payload."""
        moment = now or _now()
        with self._lock:
            reservation = self._require(reservation_id)
            if reservation.request_fingerprint != identity.request_fingerprint:
                raise DemoAllowanceError("fingerprint_mismatch")
            if reservation.geometry_sha256 != identity.geometry_sha256:
                raise DemoAllowanceError("geometry_mismatch")
            if reservation.state not in {ReservationState.RESERVED, ReservationState.CONSUMED}:
                raise DemoAllowanceError(f"cannot cache against {reservation.state.value}")
            existing = self._cached_unlocked(identity.request_fingerprint)
            if existing is not None:
                if existing.reservation_id != reservation_id:
                    raise DemoAllowanceError("cached_result_reservation_mismatch")
                if existing.geometry_sha256 != identity.geometry_sha256:
                    raise DemoAllowanceError("geometry_mismatch")
                return existing
            cached = CachedDemoResult(
                request_fingerprint=identity.request_fingerprint,
                geometry_sha256=identity.geometry_sha256,
                reservation_id=reservation_id,
                payload=dict(payload),
                cached_at=moment,
            )
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute(
                    """
                    INSERT INTO cached_results(
                        request_fingerprint, geometry_sha256, reservation_id,
                        payload_json, cached_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        cached.request_fingerprint,
                        cached.geometry_sha256,
                        cached.reservation_id,
                        json.dumps(cached.payload),
                        _iso(cached.cached_at),
                    ),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()
                existing = self._cached_unlocked(identity.request_fingerprint)
                if existing is None:
                    raise
                return existing
            still = self._get_unlocked(reservation_id)
            if still is None or still.state != reservation.state:
                raise DemoAllowanceError("cache_mutated_reservation")
            return cached

    def get_cached_result(self, request_fingerprint: str) -> CachedDemoResult | None:
        with self._lock:
            return self._cached_unlocked(request_fingerprint)

    def recover_after_restart(self, *, now: datetime) -> AllowanceRestartReport:
        """Expire leaked reservations. Never consume. Never resume paid work."""
        with self._lock:
            expired = self._expire_stale_unlocked(now)
            snap = self._snapshot_unlocked()
            reserved_ids: list[str] = []
            consumed_ids: list[str] = []
            for row in self._conn.execute("SELECT reservation_id, state FROM reservations"):
                if row["state"] == ReservationState.RESERVED.value:
                    reserved_ids.append(row["reservation_id"])
                elif row["state"] == ReservationState.CONSUMED.value:
                    consumed_ids.append(row["reservation_id"])
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
        """Idempotent consume after a durable cache hit. No second spend."""
        moment = now or _now()
        with self._lock:
            cached = self._cached_unlocked(identity.request_fingerprint)
            if cached is None:
                raise DemoAllowanceError("cached_result_missing")
            if cached.reservation_id != reservation_id:
                raise DemoAllowanceError("cached_result_reservation_mismatch")
            if cached.geometry_sha256 != identity.geometry_sha256:
                raise DemoAllowanceError("geometry_mismatch")
            reservation = self._require(reservation_id)
            self._assert_identity(reservation, identity, planned_units)
            if reservation.state == ReservationState.CONSUMED:
                return ConsumeAfterCacheResult(
                    reservation=reservation,
                    cached=cached,
                    already_consumed=True,
                )
            if reservation.state != ReservationState.RESERVED:
                raise DemoAllowanceError(f"cannot consume {reservation.state.value}")
            consumed = self._consume_unlocked(
                reservation_id,
                identity=identity,
                planned_units=planned_units,
                now=moment,
                ignore_expiry=True,
            )
            replay = self._cached_unlocked(identity.request_fingerprint)
            if replay is None:
                raise DemoAllowanceError("cached_result_lost")
            return ConsumeAfterCacheResult(
                reservation=consumed,
                cached=replay,
                already_consumed=False,
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _try_reserve_unlocked(
        self,
        identity: DemoRequestIdentity,
        *,
        planned_units: int,
        now: datetime,
    ) -> DemoAllowanceDecision:
        self._expire_stale_unlocked(now)
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
        open_count = self._count_state(ReservationState.RESERVED)
        if open_count >= self._max_open_reservations:
            return DemoAllowanceDecision(
                code=DemoAllowanceDecisionCode.RESERVATION_SLOT_EXHAUSTED,
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
            expires_at=self._expires_at(now),
        )
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._insert_reservation(reservation)
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            joined = self._active_by_fingerprint(identity.request_fingerprint)
            if joined is not None:
                return DemoAllowanceDecision(
                    code=DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION,
                    reservation=joined,
                    spend_authorized=False,
                )
            raise DemoAllowanceError("reservation_conflict") from exc
        return DemoAllowanceDecision(
            code=DemoAllowanceDecisionCode.ELIGIBLE,
            reservation=reservation,
            spend_authorized=True,
        )

    def _consume_unlocked(
        self,
        reservation_id: str,
        *,
        identity: DemoRequestIdentity,
        planned_units: int,
        now: datetime,
        ignore_expiry: bool,
    ) -> DemoReservation:
        reservation = self._require(reservation_id)
        if reservation.state != ReservationState.RESERVED:
            raise DemoAllowanceError(f"cannot consume {reservation.state.value}")
        if not ignore_expiry:
            blocked = policy_blocks_spend(self._policy, now=now)
            if blocked is not None:
                raise DemoAllowanceError(blocked.value)
        self._assert_identity(reservation, identity, planned_units)
        if (
            not ignore_expiry
            and reservation.expires_at is not None
            and now >= reservation.expires_at
        ):
            raise DemoAllowanceError("reservation_expired")
        return self._transition(
            reservation,
            ReservationState.CONSUMED,
            consumed_at=now,
        )

    def _expire_stale_unlocked(self, now: datetime) -> list[DemoReservation]:
        rows = self._conn.execute(
            """
            SELECT * FROM reservations
            WHERE state = ? AND expires_at IS NOT NULL AND expires_at <= ?
            """,
            (ReservationState.RESERVED.value, _iso(now)),
        ).fetchall()
        expired: list[DemoReservation] = []
        for row in rows:
            reservation = self._reservation_from_row(row)
            expired.append(
                self._transition(reservation, ReservationState.EXPIRED, expired_at=now)
            )
        return expired

    def _transition(
        self,
        reservation: DemoReservation,
        state: ReservationState,
        *,
        consumed_at: datetime | None = None,
        released_at: datetime | None = None,
        expired_at: datetime | None = None,
    ) -> DemoReservation:
        updated = reservation.model_copy(update={"state": state})
        self._conn.execute("BEGIN IMMEDIATE")
        cursor = self._conn.execute(
            """
            UPDATE reservations
            SET state = ?, consumed_at = COALESCE(?, consumed_at),
                released_at = COALESCE(?, released_at),
                expired_at = COALESCE(?, expired_at)
            WHERE reservation_id = ? AND state = ?
            """,
            (
                state.value,
                _iso(consumed_at),
                _iso(released_at),
                _iso(expired_at),
                reservation.reservation_id,
                reservation.state.value,
            ),
        )
        if cursor.rowcount != 1:
            self._conn.rollback()
            raise DemoAllowanceError("reservation_state_conflict")
        self._conn.commit()
        return updated

    def _insert_reservation(self, reservation: DemoReservation) -> None:
        self._conn.execute(
            """
            INSERT INTO reservations(
                reservation_id, state, signal_kind, request_fingerprint, geometry_sha256,
                area_id, planned_units, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reservation.reservation_id,
                reservation.state.value,
                reservation.signal_kind.value,
                reservation.request_fingerprint,
                reservation.geometry_sha256,
                reservation.area_id,
                reservation.planned_units,
                _iso(reservation.created_at),
                _iso(reservation.expires_at),
            ),
        )

    def _snapshot_unlocked(self) -> DemoAllowanceState:
        reserved = 0
        consumed = 0
        for row in self._conn.execute("SELECT state, planned_units FROM reservations"):
            if row["state"] == ReservationState.RESERVED.value:
                reserved += int(row["planned_units"])
            elif row["state"] == ReservationState.CONSUMED.value:
                consumed += int(row["planned_units"])
        authorized = self._policy.max_total_acquisition_units
        return DemoAllowanceState(
            authorized_total_units=authorized,
            reserved_units=reserved,
            consumed_units=consumed,
            remaining_units=max(authorized - reserved - consumed, 0),
            restart_resets_remaining=False,
            durability=AllowanceDurability.J3_LOCAL_SQLITE_DURABLE,
        )

    def _require(self, reservation_id: str) -> DemoReservation:
        reservation = self._get_unlocked(reservation_id)
        if reservation is None:
            raise DemoAllowanceError("unknown_reservation")
        return reservation

    def _get_unlocked(self, reservation_id: str) -> DemoReservation | None:
        row = self._conn.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        if row is None:
            return None
        return self._reservation_from_row(row)

    def _active_by_fingerprint(self, fingerprint: str) -> DemoReservation | None:
        row = self._conn.execute(
            "SELECT * FROM reservations WHERE request_fingerprint = ? AND state = ?",
            (fingerprint, ReservationState.RESERVED.value),
        ).fetchone()
        if row is None:
            return None
        return self._reservation_from_row(row)

    def _count_state(self, state: ReservationState) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM reservations WHERE state = ?",
            (state.value,),
        ).fetchone()
        return int(row["n"])

    def _cached_unlocked(self, fingerprint: str) -> CachedDemoResult | None:
        row = self._conn.execute(
            "SELECT * FROM cached_results WHERE request_fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if row is None:
            return None
        return CachedDemoResult(
            request_fingerprint=row["request_fingerprint"],
            geometry_sha256=row["geometry_sha256"],
            reservation_id=row["reservation_id"],
            payload=json.loads(row["payload_json"]),
            cached_at=datetime.fromisoformat(row["cached_at"]),
        )

    def _expires_at(self, now: datetime) -> datetime:
        ttl_end = now + timedelta(seconds=self._reservation_ttl_seconds)
        until = self._policy.valid_until
        if until is None:
            return ttl_end
        return min(until, ttl_end)

    @staticmethod
    def _assert_identity(
        reservation: DemoReservation,
        identity: DemoRequestIdentity,
        planned_units: int,
    ) -> None:
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

    @staticmethod
    def _reservation_from_row(row: sqlite3.Row) -> DemoReservation:
        return DemoReservation(
            reservation_id=row["reservation_id"],
            state=ReservationState(row["state"]),
            signal_kind=ThermalSignalKind(row["signal_kind"]),
            request_fingerprint=row["request_fingerprint"],
            geometry_sha256=row["geometry_sha256"],
            area_id=row["area_id"],
            planned_units=int(row["planned_units"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=(
                datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            ),
        )
