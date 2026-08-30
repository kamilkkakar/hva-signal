"""Analysis job facade. Default store is process-local memory."""

from __future__ import annotations

from app.core.job_store import (
    AnalysisJob,
    DurableJobContract,
    DurabilityState,
    InMemoryJobStore,
    JobErrorClass,
    JobStore,
    JobStoreError,
)
from app.domain.enums import JobStatus

job_store = InMemoryJobStore()

__all__ = [
    "AnalysisJob",
    "DurableJobContract",
    "DurabilityState",
    "InMemoryJobStore",
    "JobErrorClass",
    "JobStatus",
    "JobStore",
    "JobStoreError",
    "job_store",
    "process_analysis_job",
]


def process_analysis_job(job_id: str) -> None:
    """Background runner for the replay orchestrator. Safe if the job was reset."""
    from app.services.orchestrator import execute_job

    execute_job(job_id)
