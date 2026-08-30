"""Local file-backed job store with J3 WAL / crash-safe durable columns.

Default product store remains InMemory (see persistence_factory). This
adapter is opt-in local/demo durability. Enabling it does not enable a
live vendor, demo allowance, or hosted live.

Render Free filesystems are ephemeral. Multi-instance deploy does not
share this file. Recovery never auto-resubmits vendor work.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.durable_live import (
    DurableAck,
    DurableJobRecord,
    LiveWorkerState,
    PersistenceError,
    RECOVERY_QUERY_STATES,
    RestartAction,
    classify_restart,
    require_commit_before_ack,
    resulting_worker_state,
)
from app.core.job_store import (
    AnalysisJob,
    JobStoreError,
    _assert_status_transition,
    _guard_section_progress,
    _new_job,
    _TERMINAL,
    analysis_job_from_payload,
    analysis_job_to_payload,
    apply_persist_activity_id,
    apply_persist_fingerprint,
    apply_persist_reservation_id,
    apply_replace_durability,
    apply_restart_recovery,
)
from app.domain.job_durability import DurableJobContract
from app.core.sqlite_schema import (
    RECOVERY_JOBS_SQL,
    apply_durable_pragmas,
    apply_migrations,
)
from app.domain.enums import JobStatus
from app.domain.job_lifecycle import ExecutionState, TwoSignalJobState

_INTERRUPT_MESSAGE = (
    "Job interrupted by process restart. Execution was not recovered "
    "and will not be retried automatically."
)
_UNKNOWN_VENDOR_MESSAGE = (
    "Submit may have reached the vendor but activity_id was not committed. "
    "State is UNKNOWN_VENDOR_STATE. Do not resubmit."
)
_RECOVERY_MESSAGE = (
    "Process restarted. Resume via persisted activity_id / reservation only. "
    "Do not resubmit."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _job_to_payload(job: AnalysisJob) -> dict[str, Any]:
    return analysis_job_to_payload(job)


def _job_from_payload(payload: dict[str, Any]) -> AnalysisJob:
    return analysis_job_from_payload(payload)


def _wal_from_job(job: AnalysisJob) -> tuple[str | None, str | None, str | None, str | None]:
    """Fingerprint / activity / reservation / worker_state for J3 columns."""
    durability = job.durability
    fingerprint = job.dedupe_key
    activity_id = None
    reservation_id = None
    worker_state = None
    if durability is not None:
        fingerprint = durability.fingerprint or fingerprint
        activity_id = durability.activity_id
        reservation_id = durability.reservation_id
        if durability.state is not None:
            worker_state = durability.state.value
    return fingerprint, activity_id, reservation_id, worker_state


def _parse_worker_state(value: Any) -> LiveWorkerState | None:
    if value is None or value == "":
        return None
    return LiveWorkerState(str(value))


class SQLiteJobStore:
    """J2 local file store with J3 crash-safe activity_id / reservation columns.

    durability_level stays J2 for the JobStore protocol (file-backed, not
    production). durable_live_level names the WAL recovery tier.
    """

    durability_level = "J2"
    durable_live_level = "J3_LOCAL_SQLITE_WAL"
    hosted_live_implied = False
    implements_durability_contract = True

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(
            self._path,
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._pragmas = apply_durable_pragmas(self._conn)
        apply_migrations(self._conn)
        self._interrupt_orphans()

    @property
    def path(self) -> Path:
        return self._path

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _interrupt_orphans(self) -> None:
        """Classify persisted rows. Never auto-retry vendor work."""
        rows = self._conn.execute(
            """
            SELECT job_id, payload, worker_state, fingerprint, activity_id,
                   reservation_id, error_class, recovery_required, public_status
            FROM analysis_jobs
            """
        ).fetchall()
        if not rows:
            return
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                self._apply_restart_row(row)
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def _apply_restart_row(self, row: sqlite3.Row) -> None:
        payload = json.loads(row["payload"])
        job = _job_from_payload(payload)
        original_durability = job.durability
        original_status = payload.get("status")
        if job.status not in _TERMINAL:
            apply_restart_recovery(job)
        payload = _job_to_payload(job)
        status = payload.get("status")
        worker_state = _parse_worker_state(row["worker_state"])
        activity_id = row["activity_id"]
        reservation_id = row["reservation_id"]
        if original_durability is not None:
            if worker_state is None and original_durability.state is not None:
                try:
                    worker_state = LiveWorkerState(original_durability.state.value)
                except ValueError:
                    worker_state = None
            activity_id = activity_id or original_durability.activity_id
            reservation_id = reservation_id or original_durability.reservation_id
        record = DurableJobRecord(
            job_id=str(row["job_id"]),
            worker_state=worker_state,
            fingerprint=row["fingerprint"],
            activity_id=activity_id,
            reservation_id=reservation_id,
            error_class=row["error_class"],
            recovery_required=bool(row["recovery_required"]),
            public_status=row["public_status"] or original_status,
        )
        if record.worker_state is None:
            if original_status in {item.value for item in _TERMINAL}:
                return
            payload["status"] = JobStatus.FAILED.value
            payload["execution_state"] = ExecutionState.INTERRUPTED.value
            payload["recoverable"] = True
            payload["message"] = _INTERRUPT_MESSAGE
            payload["revision"] = int(payload.get("revision") or 0) + 1
            payload["updated_at"] = _now().isoformat()
            self._conn.execute(
                """
                UPDATE analysis_jobs
                SET payload = ?, public_status = ?, updated_at = ?,
                    revision = revision + 1
                WHERE job_id = ?
                """,
                (
                    json.dumps(payload),
                    JobStatus.FAILED.value,
                    payload["updated_at"],
                    record.job_id,
                ),
            )
            return

        action = classify_restart(record)
        if action == RestartAction.KEEP:
            return
        nxt = resulting_worker_state(record, action)
        recovery = action in {
            RestartAction.MARK_UNKNOWN_VENDOR,
            RestartAction.MARK_RECOVERY_REQUIRED,
        }
        error_class = None
        if action == RestartAction.MARK_UNKNOWN_VENDOR:
            error_class = "UNKNOWN_VENDOR_STATE"
            payload["message"] = _UNKNOWN_VENDOR_MESSAGE
            payload["recoverable"] = True
        elif action == RestartAction.MARK_RECOVERY_REQUIRED:
            error_class = "RECOVERY_REQUIRED"
            payload["message"] = _RECOVERY_MESSAGE
            payload["recoverable"] = True
        elif action == RestartAction.INTERRUPT_PRE_SUBMIT:
            error_class = "FAILED_PRE_SUBMIT"
            payload["status"] = JobStatus.FAILED.value
            payload["execution_state"] = ExecutionState.INTERRUPTED.value
            payload["recoverable"] = True
            payload["message"] = _INTERRUPT_MESSAGE
        payload["worker_state"] = nxt.value if nxt else None
        payload["activity_id"] = record.activity_id
        payload["reservation_id"] = record.reservation_id
        payload["revision"] = int(payload.get("revision") or 0) + 1
        payload["updated_at"] = _now().isoformat()
        self._conn.execute(
            """
            UPDATE analysis_jobs
            SET payload = ?,
                worker_state = ?,
                recovery_required = ?,
                error_class = COALESCE(?, error_class),
                public_status = ?,
                updated_at = ?,
                revision = revision + 1
            WHERE job_id = ?
            """,
            (
                json.dumps(payload),
                nxt.value if nxt else None,
                1 if recovery else 0,
                error_class,
                payload.get("status"),
                payload["updated_at"],
                record.job_id,
            ),
        )

    def _insert_job_unlocked(self, job: AnalysisJob) -> None:
        payload = _job_to_payload(job)
        fingerprint, activity_id, reservation_id, worker_state = _wal_from_job(job)
        self._conn.execute(
            """
            INSERT INTO analysis_jobs (
                job_id, dedupe_key, fingerprint, activity_id, reservation_id,
                worker_state, payload, public_status, created_at, updated_at,
                revision
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.dedupe_key,
                fingerprint,
                activity_id,
                reservation_id,
                worker_state,
                json.dumps(payload),
                job.status.value,
                job.created_at.isoformat(),
                job.updated_at.isoformat() if job.updated_at else None,
                job.revision,
            ),
        )

    def _put(self, job: AnalysisJob) -> None:
        payload = _job_to_payload(job)
        fingerprint, activity_id, reservation_id, worker_state = _wal_from_job(job)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                """
                INSERT INTO analysis_jobs (
                    job_id, dedupe_key, fingerprint, activity_id, reservation_id,
                    worker_state, payload, public_status, created_at, updated_at,
                    revision
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    dedupe_key = excluded.dedupe_key,
                    fingerprint = COALESCE(excluded.fingerprint, analysis_jobs.fingerprint),
                    activity_id = COALESCE(excluded.activity_id, analysis_jobs.activity_id),
                    reservation_id = COALESCE(excluded.reservation_id, analysis_jobs.reservation_id),
                    worker_state = COALESCE(excluded.worker_state, analysis_jobs.worker_state),
                    payload = excluded.payload,
                    public_status = excluded.public_status,
                    updated_at = excluded.updated_at,
                    revision = excluded.revision
                """,
                (
                    job.job_id,
                    job.dedupe_key,
                    fingerprint,
                    activity_id,
                    reservation_id,
                    worker_state,
                    json.dumps(payload),
                    job.status.value,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat() if job.updated_at else None,
                    job.revision,
                ),
            )
            self._conn.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            self._conn.execute("ROLLBACK")
            raise PersistenceError(f"unique constraint: {exc}") from exc
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def create(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str | None = None,
    ) -> AnalysisJob:
        job = _new_job(request, dedupe_key=dedupe_key)
        with self._lock:
            self._put(job)
        return job

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM analysis_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return _job_from_payload(json.loads(row["payload"]))

    def find_by_dedupe_key(self, dedupe_key: str) -> AnalysisJob | None:
        with self._lock:
            return self._find_by_key_unlocked(dedupe_key)

    def _find_by_key_unlocked(self, dedupe_key: str) -> AnalysisJob | None:
        row = self._conn.execute(
            """
            SELECT payload FROM analysis_jobs
            WHERE dedupe_key = ? OR fingerprint = ?
            LIMIT 1
            """,
            (dedupe_key, dedupe_key),
        ).fetchone()
        if row is None:
            return None
        return _job_from_payload(json.loads(row["payload"]))

    def create_or_join(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str,
    ) -> tuple[AnalysisJob, bool]:
        job = _new_job(request, dedupe_key=dedupe_key)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                existing = self._find_by_key_unlocked(dedupe_key)
                if existing is not None:
                    self._conn.execute("COMMIT")
                    return existing, True
                self._insert_job_unlocked(job)
                self._conn.execute("COMMIT")
                return job, False
            except sqlite3.IntegrityError:
                self._conn.execute("ROLLBACK")
                joined = self._find_by_key_unlocked(dedupe_key)
                if joined is None:
                    raise PersistenceError("fingerprint unique conflict without row")
                return joined, True
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def _mutate(self, job_id: str, mutator) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM analysis_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                return
            job = _job_from_payload(json.loads(row["payload"]))
            mutator(job)
            self._put(job)

    def replace_durability(self, job_id: str, durability: DurableJobContract) -> None:
        self._mutate(job_id, lambda job: apply_replace_durability(job, durability))

    def persist_fingerprint(self, job_id: str, fingerprint: str) -> None:
        self._mutate(job_id, lambda job: apply_persist_fingerprint(job, fingerprint))

    def persist_activity_id(self, job_id: str, activity_id: str) -> None:
        self._mutate(job_id, lambda job: apply_persist_activity_id(job, activity_id))

    def persist_reservation_id(self, job_id: str, reservation_id: str) -> None:
        self._mutate(
            job_id, lambda job: apply_persist_reservation_id(job, reservation_id)
        )

    def recover_after_restart(self) -> list[AnalysisJob]:
        recovered: list[AnalysisJob] = []
        with self._lock:
            rows = self._conn.execute("SELECT payload FROM analysis_jobs").fetchall()
            for row in rows:
                job = _job_from_payload(json.loads(row["payload"]))
                apply_restart_recovery(job)
                self._put(job)
                recovered.append(job)
        return recovered

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        message: str | None = None,
        note: str | None = None,
        execution_state: ExecutionState | None = None,
    ) -> None:
        def _apply(job: AnalysisJob) -> None:
            _assert_status_transition(job.status, status)
            job.status = status
            job.updated_at = _now()
            job.revision += 1
            if message is not None:
                job.message = message
            if note:
                job.progress_notes.append(note)
            if execution_state is not None:
                job.execution_state = execution_state
            elif status in _TERMINAL:
                job.execution_state = ExecutionState.FINISHED
            elif job.execution_state == ExecutionState.NOT_STARTED:
                job.execution_state = ExecutionState.RUNNING

        self._mutate(job_id, _apply)

    def set_result(
        self,
        job_id: str,
        result: dict[str, Any],
        status: JobStatus,
        *,
        message: str | None = None,
    ) -> None:
        def _apply(job: AnalysisJob) -> None:
            _assert_status_transition(job.status, status)
            job.result = result
            job.status = status
            job.updated_at = _now()
            job.revision += 1
            job.execution_state = ExecutionState.FINISHED
            if message is not None:
                job.message = message
            job.progress_notes.append(status.value)

        self._mutate(job_id, _apply)

    def replace_two_signal(self, job_id: str, state: TwoSignalJobState) -> None:
        def _apply(job: AnalysisJob) -> None:
            if job.two_signal is not None:
                _guard_section_progress(job.two_signal, state)
            job.two_signal = state
            job.updated_at = _now()
            job.revision += 1

        self._mutate(job_id, _apply)

    def mark_interrupted(self, job_id: str, *, message: str) -> None:
        def _apply(job: AnalysisJob) -> None:
            if job.status in _TERMINAL:
                return
            job.status = JobStatus.FAILED
            job.execution_state = ExecutionState.INTERRUPTED
            job.recoverable = True
            job.message = message
            job.updated_at = _now()
            job.revision += 1

        self._mutate(job_id, _apply)

    def list_in_flight(self) -> list[AnalysisJob]:
        with self._lock:
            rows = self._conn.execute("SELECT payload FROM analysis_jobs").fetchall()
        jobs = [_job_from_payload(json.loads(row["payload"])) for row in rows]
        return [job for job in jobs if job.status not in _TERMINAL]

    def reset(self) -> None:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute("DELETE FROM analysis_jobs")
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def get_durable(self, job_id: str) -> DurableJobRecord | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id, worker_state, fingerprint, activity_id,
                       reservation_id, error_class, recovery_required, public_status
                FROM analysis_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def find_by_fingerprint(self, fingerprint: str) -> DurableJobRecord | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id, worker_state, fingerprint, activity_id,
                       reservation_id, error_class, recovery_required, public_status
                FROM analysis_jobs
                WHERE fingerprint = ?
                """,
                (fingerprint,),
            ).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def find_by_reservation_id(self, reservation_id: str) -> DurableJobRecord | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id, worker_state, fingerprint, activity_id,
                       reservation_id, error_class, recovery_required, public_status
                FROM analysis_jobs
                WHERE reservation_id = ?
                """,
                (reservation_id,),
            ).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def find_by_activity_id(self, activity_id: str) -> DurableJobRecord | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id, worker_state, fingerprint, activity_id,
                       reservation_id, error_class, recovery_required, public_status
                FROM analysis_jobs
                WHERE activity_id = ?
                """,
                (activity_id,),
            ).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def list_recovery_jobs(self) -> list[DurableJobRecord]:
        with self._lock:
            rows = self._conn.execute(RECOVERY_JOBS_SQL).fetchall()
        return [self._record_from_row(row) for row in rows]

    def mark_submitting(
        self,
        job_id: str,
        *,
        reservation_id: str | None = None,
        fingerprint: str | None = None,
    ) -> DurableAck:
        """Commit SUBMITTING before the vendor call. No activity_id yet."""
        return self._commit_worker_write(
            job_id,
            worker_state=LiveWorkerState.SUBMITTING,
            activity_id=None,
            reservation_id=reservation_id,
            fingerprint=fingerprint,
            acknowledged_status="SUBMITTING",
            require_ids=False,
        )

    def commit_reservation_binding(
        self,
        job_id: str,
        *,
        reservation_id: str,
        fingerprint: str,
        worker_state: LiveWorkerState = LiveWorkerState.ALLOWANCE_RESERVED,
    ) -> DurableAck:
        if not reservation_id.strip() or not fingerprint.strip():
            raise PersistenceError("reservation binding requires reservation_id and fingerprint")
        return self._commit_worker_write(
            job_id,
            worker_state=worker_state,
            activity_id=None,
            reservation_id=reservation_id,
            fingerprint=fingerprint,
            acknowledged_status=worker_state.value,
            require_ids=False,
        )

    def acknowledge_submitted(
        self,
        job_id: str,
        *,
        activity_id: str,
        reservation_id: str,
        fingerprint: str | None = None,
    ) -> DurableAck:
        require_commit_before_ack(
            activity_id=activity_id,
            reservation_id=reservation_id,
            acknowledged_status="SUBMITTED",
        )
        return self._commit_worker_write(
            job_id,
            worker_state=LiveWorkerState.SUBMITTED,
            activity_id=activity_id,
            reservation_id=reservation_id,
            fingerprint=fingerprint,
            acknowledged_status="SUBMITTED",
            require_ids=True,
        )

    def acknowledge_activity_id_persisted(
        self,
        job_id: str,
        *,
        activity_id: str,
        reservation_id: str,
        fingerprint: str | None = None,
    ) -> DurableAck:
        require_commit_before_ack(
            activity_id=activity_id,
            reservation_id=reservation_id,
            acknowledged_status="ACTIVITY_ID_PERSISTED",
        )
        return self._commit_worker_write(
            job_id,
            worker_state=LiveWorkerState.ACTIVITY_ID_PERSISTED,
            activity_id=activity_id,
            reservation_id=reservation_id,
            fingerprint=fingerprint,
            acknowledged_status="ACTIVITY_ID_PERSISTED",
            require_ids=True,
        )

    def write_uncommitted_activity_id_for_tests(
        self, job_id: str, activity_id: str
    ) -> None:
        """Test hook: write activity_id inside an open transaction, no COMMIT."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "UPDATE analysis_jobs SET activity_id = ? WHERE job_id = ?",
                (activity_id, job_id),
            )

    def crash_close_for_tests(self) -> None:
        """Test hook: drop the connection so an open transaction rolls back."""
        self._conn.close()

    def _commit_worker_write(
        self,
        job_id: str,
        *,
        worker_state: LiveWorkerState,
        activity_id: str | None,
        reservation_id: str | None,
        fingerprint: str | None,
        acknowledged_status: str,
        require_ids: bool,
    ) -> DurableAck:
        if require_ids:
            require_commit_before_ack(
                activity_id=activity_id,
                reservation_id=reservation_id,
                acknowledged_status=acknowledged_status,
            )
        if worker_state in {
            LiveWorkerState.SUBMITTED,
            LiveWorkerState.ACTIVITY_ID_PERSISTED,
        } and (not activity_id or not reservation_id):
            raise PersistenceError(
                f"cannot persist {worker_state.value} without activity_id and reservation"
            )
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM analysis_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise PersistenceError(f"unknown job {job_id}")
            payload = json.loads(row["payload"])
            payload["worker_state"] = worker_state.value
            if activity_id:
                payload["activity_id"] = activity_id
            if reservation_id:
                payload["reservation_id"] = reservation_id
            if fingerprint:
                payload["fingerprint"] = fingerprint
            payload["updated_at"] = _now().isoformat()
            payload["revision"] = int(payload.get("revision") or 0) + 1
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute(
                    """
                    UPDATE analysis_jobs
                    SET payload = ?,
                        worker_state = ?,
                        activity_id = COALESCE(?, activity_id),
                        reservation_id = COALESCE(?, reservation_id),
                        fingerprint = COALESCE(?, fingerprint),
                        recovery_required = 0,
                        error_class = NULL,
                        updated_at = ?,
                        revision = revision + 1
                    WHERE job_id = ?
                    """,
                    (
                        json.dumps(payload),
                        worker_state.value,
                        activity_id,
                        reservation_id,
                        fingerprint,
                        payload["updated_at"],
                        job_id,
                    ),
                )
                self._conn.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self._conn.execute("ROLLBACK")
                raise PersistenceError(f"unique constraint: {exc}") from exc
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return DurableAck(
            job_id=job_id,
            worker_state=worker_state,
            activity_id=activity_id,
            reservation_id=reservation_id,
            acknowledged_status=acknowledged_status,
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> DurableJobRecord:
        return DurableJobRecord(
            job_id=str(row["job_id"]),
            worker_state=_parse_worker_state(row["worker_state"]),
            fingerprint=row["fingerprint"],
            activity_id=row["activity_id"],
            reservation_id=row["reservation_id"],
            error_class=row["error_class"],
            recovery_required=bool(row["recovery_required"]),
            public_status=row["public_status"],
        )


# Re-export for existing tests that import the interrupt copy.
__all__ = [
    "SQLiteJobStore",
    "PersistenceError",
    "JobStoreError",
    "_INTERRUPT_MESSAGE",
    "RECOVERY_QUERY_STATES",
]
