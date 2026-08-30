"""Local file-backed job store. J2 adapter. LIVE-B owns schema evolution.

Render Free filesystems are ephemeral. Multi-instance deploy does not share
this file. Restart recovery uses LIVE-A hooks: vendor identity
(activity_id / reservation_id) is preserved; jobs without vendor identity
keep the J2 interrupt (FAILED, never auto-retried).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.job_store import (
    INTERRUPT_MESSAGE,
    AnalysisJob,
    _TERMINAL,
    _assert_status_transition,
    _guard_section_progress,
    _new_job,
    analysis_job_from_payload,
    analysis_job_to_payload,
    apply_persist_activity_id,
    apply_persist_fingerprint,
    apply_persist_reservation_id,
    apply_replace_durability,
    apply_restart_recovery,
)
from app.domain.enums import JobStatus
from app.domain.job_durability import DurableJobContract
from app.domain.job_lifecycle import ExecutionState, TwoSignalJobState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_jobs (
    job_id TEXT PRIMARY KEY,
    dedupe_key TEXT UNIQUE,
    payload TEXT NOT NULL
);
"""

# Existing tests import this name. Same text as INTERRUPT_MESSAGE.
_INTERRUPT_MESSAGE = INTERRUPT_MESSAGE


def _job_to_payload(job: AnalysisJob) -> dict[str, Any]:
    """LIVE-B hook: shared J3 document, including durability fields."""
    return analysis_job_to_payload(job)


def _job_from_payload(payload: dict[str, Any]) -> AnalysisJob:
    """LIVE-B hook: accepts pre-J3 rows (durability missing)."""
    return analysis_job_from_payload(payload)


class SQLiteJobStore:
    """J2 local file-backed persistence. Off by default. Not production-durable."""

    durability_level = "J2"
    implements_durability_contract = True

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA)
        self._conn.commit()
        self._interrupt_orphans()

    def _interrupt_orphans(self) -> None:
        """Restart hook. Preserve activity_id/reservation. Never auto-resubmit."""
        rows = self._conn.execute("SELECT job_id, payload FROM analysis_jobs").fetchall()
        for _job_id, raw in rows:
            job = _job_from_payload(json.loads(raw))
            if job.status in _TERMINAL:
                continue
            apply_restart_recovery(job)
            self._put(job)
        self._conn.commit()

    def _put(self, job: AnalysisJob) -> None:
        payload = json.dumps(_job_to_payload(job))
        self._conn.execute(
            """
            INSERT INTO analysis_jobs (job_id, dedupe_key, payload)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                dedupe_key = excluded.dedupe_key,
                payload = excluded.payload
            """,
            (job.job_id, job.dedupe_key, payload),
        )
        self._conn.commit()

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
        return _job_from_payload(json.loads(row[0]))

    def find_by_dedupe_key(self, dedupe_key: str) -> AnalysisJob | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM analysis_jobs WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()
        if row is None:
            return None
        return _job_from_payload(json.loads(row[0]))

    def find_by_fingerprint(self, fingerprint: str) -> AnalysisJob | None:
        by_key = self.find_by_dedupe_key(fingerprint)
        if by_key is not None:
            return by_key
        for job in self._iter_jobs():
            if job.durability and job.durability.fingerprint == fingerprint:
                return job
        return None

    def find_by_activity_id(self, activity_id: str) -> AnalysisJob | None:
        for job in self._iter_jobs():
            if job.durability and job.durability.activity_id == activity_id:
                return job
        return None

    def find_by_reservation_id(self, reservation_id: str) -> AnalysisJob | None:
        for job in self._iter_jobs():
            if job.durability and job.durability.reservation_id == reservation_id:
                return job
        return None

    def create_or_join(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str,
    ) -> tuple[AnalysisJob, bool]:
        existing = self.find_by_dedupe_key(dedupe_key)
        if existing is not None:
            return existing, True
        return self.create(request, dedupe_key=dedupe_key), False

    def _mutate(self, job_id: str, mutator) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM analysis_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                return
            job = _job_from_payload(json.loads(row[0]))
            mutator(job)
            self._put(job)

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
            job.updated_at = datetime.now(timezone.utc)
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
            job.updated_at = datetime.now(timezone.utc)
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
            job.updated_at = datetime.now(timezone.utc)
            job.revision += 1

        self._mutate(job_id, _apply)

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

    def mark_interrupted(self, job_id: str, *, message: str) -> None:
        def _apply(job: AnalysisJob) -> None:
            if job.status in _TERMINAL:
                return
            job.status = JobStatus.FAILED
            job.execution_state = ExecutionState.INTERRUPTED
            job.recoverable = True
            job.message = message
            job.updated_at = datetime.now(timezone.utc)
            job.revision += 1

        self._mutate(job_id, _apply)

    def recover_after_restart(self) -> list[AnalysisJob]:
        recovered: list[AnalysisJob] = []
        with self._lock:
            rows = self._conn.execute("SELECT payload FROM analysis_jobs").fetchall()
            for row in rows:
                job = _job_from_payload(json.loads(row[0]))
                apply_restart_recovery(job)
                self._put(job)
                recovered.append(job)
        return recovered

    def export_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT payload FROM analysis_jobs").fetchall()
        return [json.loads(row[0]) for row in rows]

    def import_jobs(self, records: list[dict[str, Any]]) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM analysis_jobs")
            for record in records:
                self._put(_job_from_payload(record))

    def list_in_flight(self) -> list[AnalysisJob]:
        return [job for job in self._iter_jobs() if job.status not in _TERMINAL]

    def reset(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM analysis_jobs")
            self._conn.commit()

    def _iter_jobs(self) -> list[AnalysisJob]:
        with self._lock:
            rows = self._conn.execute("SELECT payload FROM analysis_jobs").fetchall()
        return [_job_from_payload(json.loads(row[0])) for row in rows]
