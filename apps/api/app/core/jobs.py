from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.domain.enums import JobStatus


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


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = Lock()

    def create(self, request: dict[str, Any]) -> AnalysisJob:
        job = AnalysisJob(
            job_id=f"job_{uuid4().hex[:12]}",
            status=JobStatus.QUEUED,
            request=request,
            created_at=datetime.now(timezone.utc),
            message="Job queued.",
            result=None,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        message: str | None = None,
        note: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            if message is not None:
                job.message = message
            if note:
                job.progress_notes.append(note)

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
            job.result = result
            job.status = status
            if message is not None:
                job.message = message
            job.progress_notes.append(status.value)

    def reset(self) -> None:
        """Drop in-memory jobs. Models a process restart."""
        with self._lock:
            self._jobs.clear()


job_store = InMemoryJobStore()


def process_analysis_job(job_id: str) -> None:
    """Background runner for the replay orchestrator. Safe if the job was reset."""
    from app.services.orchestrator import execute_job

    execute_job(job_id)
