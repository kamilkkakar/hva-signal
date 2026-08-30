"""Local file-backed job store. J2 only. Not production-durable.

Render Free filesystems are ephemeral. Multi-instance deploy does not share
this file. A RUNNING row after process restart is INTERRUPTED and is never
auto-retried (no vendor resubmit).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.job_store import (
    AnalysisJob,
    JobStoreError,
    _assert_status_transition,
    _guard_section_progress,
    _TERMINAL,
)
from app.domain.enums import JobStatus
from app.domain.job_lifecycle import ExecutionState, TwoSignalJobState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_jobs (
    job_id TEXT PRIMARY KEY,
    dedupe_key TEXT UNIQUE,
    payload TEXT NOT NULL
);
"""

_INTERRUPT_MESSAGE = (
    "Job interrupted by process restart. Execution was not recovered "
    "and will not be retried automatically."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _job_to_payload(job: AnalysisJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "request": job.request,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "recoverable": job.recoverable,
        "message": job.message,
        "progress_notes": list(job.progress_notes),
        "result": job.result,
        "dedupe_key": job.dedupe_key,
        "execution_state": job.execution_state.value,
        "revision": job.revision,
        "two_signal": job.two_signal.model_dump(mode="json") if job.two_signal else None,
    }


def _job_from_payload(payload: dict[str, Any]) -> AnalysisJob:
    two = payload.get("two_signal")
    return AnalysisJob(
        job_id=payload["job_id"],
        status=JobStatus(payload["status"]),
        request=payload["request"],
        created_at=datetime.fromisoformat(payload["created_at"]),
        updated_at=(
            datetime.fromisoformat(payload["updated_at"])
            if payload.get("updated_at")
            else None
        ),
        recoverable=bool(payload.get("recoverable")),
        message=payload.get("message"),
        progress_notes=list(payload.get("progress_notes") or []),
        result=payload.get("result"),
        dedupe_key=payload.get("dedupe_key"),
        execution_state=ExecutionState(payload.get("execution_state") or "NOT_STARTED"),
        revision=int(payload.get("revision") or 0),
        two_signal=TwoSignalJobState.model_validate(two) if two else None,
    )


class SQLiteJobStore:
    """J2 local file-backed persistence. Off by default. Not production-durable."""

    durability_level = "J2"

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
        """STATE persisted != EXECUTION persisted. Never auto-retry vendor work."""
        rows = self._conn.execute("SELECT job_id, payload FROM analysis_jobs").fetchall()
        for job_id, raw in rows:
            payload = json.loads(raw)
            status = payload.get("status")
            if status in {item.value for item in _TERMINAL}:
                continue
            payload["status"] = JobStatus.FAILED.value
            payload["execution_state"] = ExecutionState.INTERRUPTED.value
            payload["recoverable"] = True
            payload["message"] = _INTERRUPT_MESSAGE
            payload["revision"] = int(payload.get("revision") or 0) + 1
            payload["updated_at"] = _now().isoformat()
            self._conn.execute(
                "UPDATE analysis_jobs SET payload = ? WHERE job_id = ?",
                (json.dumps(payload), job_id),
            )
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
        job = AnalysisJob(
            job_id=f"job_{uuid4().hex[:12]}",
            status=JobStatus.QUEUED,
            request=request,
            created_at=_now(),
            updated_at=_now(),
            message="Job queued.",
            result=None,
            dedupe_key=dedupe_key,
            execution_state=ExecutionState.NOT_STARTED,
        )
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
        jobs = [_job_from_payload(json.loads(row[0])) for row in rows]
        return [job for job in jobs if job.status not in _TERMINAL]

    def reset(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM analysis_jobs")
            self._conn.commit()
