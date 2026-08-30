"""Provider-neutral analysis job store.

Durability language:
- InMemoryJobStore is J0 process-local / J1 client-reattachable while the
  process survives. It is not file-backed and not production-durable.
- SQLiteJobStore (optional, off by default) is J2 local file-backed
  persistence. It is not production-durable on an ephemeral filesystem
  and is not worker-recoverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from app.domain.enums import JobStatus
from app.domain.job_lifecycle import ExecutionState, TwoSignalJobState


_TERMINAL = frozenset({JobStatus.COMPLETE, JobStatus.PARTIAL, JobStatus.FAILED})


class JobStoreError(ValueError):
    """Illegal job-store transition."""


@dataclass
class AnalysisJob:
    job_id: str
    status: JobStatus
    request: dict[str, Any]
    created_at: datetime
    recoverable: bool = False
    message: str | None = None
    progress_notes: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    updated_at: datetime | None = None
    dedupe_key: str | None = None
    execution_state: ExecutionState = ExecutionState.NOT_STARTED
    revision: int = 0
    two_signal: TwoSignalJobState | None = None

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL


class JobStore(Protocol):
    """Provider-neutral job persistence. Implementations must document level."""

    durability_level: str

    def create(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str | None = None,
    ) -> AnalysisJob: ...

    def get(self, job_id: str) -> AnalysisJob | None: ...

    def find_by_dedupe_key(self, dedupe_key: str) -> AnalysisJob | None: ...

    def create_or_join(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str,
    ) -> tuple[AnalysisJob, bool]: ...

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        message: str | None = None,
        note: str | None = None,
        execution_state: ExecutionState | None = None,
    ) -> None: ...

    def set_result(
        self,
        job_id: str,
        result: dict[str, Any],
        status: JobStatus,
        *,
        message: str | None = None,
    ) -> None: ...

    def replace_two_signal(self, job_id: str, state: TwoSignalJobState) -> None: ...

    def mark_interrupted(
        self,
        job_id: str,
        *,
        message: str,
    ) -> None: ...

    def list_in_flight(self) -> list[AnalysisJob]: ...

    def reset(self) -> None: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_status_transition(current: JobStatus, nxt: JobStatus) -> None:
    if current in _TERMINAL and nxt not in _TERMINAL:
        raise JobStoreError("terminal job cannot return to in-flight")


class InMemoryJobStore:
    """J0 process-local memory. Client-reattachable (J1) until process death."""

    durability_level = "J0"

    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._by_key: dict[str, str] = {}
        self._lock = Lock()

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
            self._jobs[job.job_id] = job
            if dedupe_key:
                self._by_key[dedupe_key] = job.job_id
        return job

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def find_by_dedupe_key(self, dedupe_key: str) -> AnalysisJob | None:
        with self._lock:
            job_id = self._by_key.get(dedupe_key)
            if job_id is None:
                return None
            return self._jobs.get(job_id)

    def create_or_join(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str,
    ) -> tuple[AnalysisJob, bool]:
        with self._lock:
            existing_id = self._by_key.get(dedupe_key)
            if existing_id is not None:
                existing = self._jobs.get(existing_id)
                if existing is not None:
                    return existing, True
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
            self._jobs[job.job_id] = job
            self._by_key[dedupe_key] = job.job_id
            return job, False

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        message: str | None = None,
        note: str | None = None,
        execution_state: ExecutionState | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
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

    def set_result(
        self,
        job_id: str,
        result: dict[str, Any],
        status: JobStatus,
        *,
        message: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            _assert_status_transition(job.status, status)
            job.result = result
            job.status = status
            job.updated_at = _now()
            job.revision += 1
            job.execution_state = ExecutionState.FINISHED
            if message is not None:
                job.message = message
            job.progress_notes.append(status.value)

    def replace_two_signal(self, job_id: str, state: TwoSignalJobState) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.two_signal is not None:
                _guard_section_progress(job.two_signal, state)
            job.two_signal = state
            job.updated_at = _now()
            job.revision += 1

    def mark_interrupted(self, job_id: str, *, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status in _TERMINAL:
                return
            job.status = JobStatus.FAILED
            job.execution_state = ExecutionState.INTERRUPTED
            job.recoverable = True
            job.message = message
            job.updated_at = _now()
            job.revision += 1

    def list_in_flight(self) -> list[AnalysisJob]:
        with self._lock:
            return [job for job in self._jobs.values() if job.status not in _TERMINAL]

    def reset(self) -> None:
        """Drop in-memory jobs. Models a process restart."""
        with self._lock:
            self._jobs.clear()
            self._by_key.clear()


def _guard_section_progress(
    current: TwoSignalJobState, nxt: TwoSignalJobState
) -> None:
    from app.domain.job_lifecycle import apply_progress

    apply_progress(current.historical.progress, nxt.historical.progress)
    apply_progress(current.selected_time.progress, nxt.selected_time.progress)
