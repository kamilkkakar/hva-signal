"""Provider-neutral analysis job store.

Durability language:
- InMemoryJobStore is J0 process-local / J1 client-reattachable while the
  process survives. It is not file-backed and not production-durable.
- SQLiteJobStore (optional, off by default) is J2 local file-backed
  persistence with J3 WAL / activity_id / reservation columns. LIVE-B
  owns the SQLite adapter; InMemory remains the process default unless
  an operator sets local_sqlite_* explicitly. Enabling it does not
  enable hosted live. This module owns the J3 durable contract:
  job identity, durability state, fingerprint, activity_id,
  reservation_id, error class, and recovery flags persist on the same
  AnalysisJob. A worker crash must not drop activity_id or reservation.
  J4 worker transitions are LIVE-C. This store persists those states;
  it does not drive the vendor worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from app.domain.enums import JobStatus
from app.domain.job_durability import (
    CrashRecoveryPlan,
    DurableJobContract,
    DurabilityState,
    JobErrorClass,
    forbids_auto_resubmit,
    is_auto_resubmit_target,
    new_durability,
    plan_crash_recovery,
)
from app.domain.job_lifecycle import ExecutionState, TwoSignalJobState


_TERMINAL = frozenset({JobStatus.COMPLETE, JobStatus.PARTIAL, JobStatus.FAILED})

INTERRUPT_MESSAGE = (
    "Job interrupted by process restart. Execution was not recovered "
    "and will not be retried automatically."
)


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
    durability: DurableJobContract | None = None

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

    def find_by_fingerprint(self, fingerprint: str) -> AnalysisJob | None: ...

    def find_by_activity_id(self, activity_id: str) -> AnalysisJob | None: ...

    def find_by_reservation_id(self, reservation_id: str) -> AnalysisJob | None: ...

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

    def replace_durability(self, job_id: str, durability: DurableJobContract) -> None: ...

    def persist_fingerprint(self, job_id: str, fingerprint: str) -> None: ...

    def persist_activity_id(self, job_id: str, activity_id: str) -> None: ...

    def persist_reservation_id(self, job_id: str, reservation_id: str) -> None: ...

    def mark_interrupted(
        self,
        job_id: str,
        *,
        message: str,
    ) -> None: ...

    def recover_after_restart(self) -> list[AnalysisJob]: ...

    def export_jobs(self) -> list[dict[str, Any]]: ...

    def import_jobs(self, records: list[dict[str, Any]]) -> None: ...

    def list_in_flight(self) -> list[AnalysisJob]: ...

    def reset(self) -> None: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_status_transition(current: JobStatus, nxt: JobStatus) -> None:
    if current in _TERMINAL and nxt not in _TERMINAL:
        raise JobStoreError("terminal job cannot return to in-flight")


def _assert_no_auto_resubmit(
    current: DurableJobContract | None, nxt: DurableJobContract
) -> None:
    if current is None:
        return
    if forbids_auto_resubmit(current.state) and is_auto_resubmit_target(nxt.state):
        raise JobStoreError(
            f"{current.state.value} must never auto-resubmit "
            f"(refused {nxt.state.value})"
        )
    if nxt.recovery.auto_resubmit and current.state == DurabilityState.UNKNOWN_VENDOR_STATE:
        raise JobStoreError("UNKNOWN_VENDOR_STATE must never auto-resubmit")


def _new_job(
    request: dict[str, Any],
    *,
    dedupe_key: str | None = None,
) -> AnalysisJob:
    stamp = _now()
    return AnalysisJob(
        job_id=f"job_{uuid4().hex[:12]}",
        status=JobStatus.QUEUED,
        request=request,
        created_at=stamp,
        updated_at=stamp,
        message="Job queued.",
        result=None,
        dedupe_key=dedupe_key,
        execution_state=ExecutionState.NOT_STARTED,
        durability=new_durability(fingerprint=dedupe_key),
    )


def analysis_job_to_payload(job: AnalysisJob) -> dict[str, Any]:
    """SQLite / restart hook. LIVE-B should persist this document."""
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
        "durability": job.durability.to_payload() if job.durability else None,
    }


def analysis_job_from_payload(payload: dict[str, Any]) -> AnalysisJob:
    """SQLite / restart hook. Missing durability is a pre-J3 row."""
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
        durability=DurableJobContract.from_payload(payload.get("durability")),
    )


def apply_restart_recovery(job: AnalysisJob) -> AnalysisJob:
    """Apply crash recovery in place. Never drops activity_id or reservation."""
    public_terminal = job.status in _TERMINAL
    plan = plan_crash_recovery(job.durability, public_terminal=public_terminal)
    if public_terminal:
        return job
    stamp = _now()
    job.updated_at = stamp
    job.revision += 1
    job.recoverable = True

    if job.durability is None:
        job.durability = new_durability(fingerprint=job.dedupe_key)
    preserved_activity = job.durability.activity_id
    preserved_reservation = job.durability.reservation_id
    preserved_fingerprint = job.durability.fingerprint or job.dedupe_key
    preserved_activity_at = job.durability.activity_id_persisted_at
    preserved_reservation_at = job.durability.reservation_persisted_at
    submit_attempted = job.durability.recovery.submit_attempted

    job.durability.state = plan.state
    job.durability.error_class = plan.error_class
    job.durability.updated_at = stamp
    job.durability.activity_id = preserved_activity
    job.durability.reservation_id = preserved_reservation
    job.durability.fingerprint = preserved_fingerprint
    job.durability.activity_id_persisted_at = preserved_activity_at
    job.durability.reservation_persisted_at = preserved_reservation_at
    job.durability.recovery.auto_resubmit = False
    job.durability.recovery.requires_vendor_status_check = (
        plan.requires_vendor_status_check
    )
    job.durability.recovery.operator_reconcile = plan.operator_reconcile
    job.durability.recovery.reservation_intact = plan.reservation_intact
    job.durability.recovery.activity_id_durable = plan.activity_id_durable
    job.durability.recovery.submit_attempted = submit_attempted

    if plan.interrupt_public_job and not public_terminal:
        job.status = JobStatus.FAILED
        job.execution_state = ExecutionState.INTERRUPTED
        job.message = plan.message or INTERRUPT_MESSAGE
    elif not public_terminal:
        job.execution_state = ExecutionState.INTERRUPTED
        job.message = plan.message
    return job


def _touch_durability(job: AnalysisJob) -> DurableJobContract:
    if job.durability is None:
        job.durability = new_durability(fingerprint=job.dedupe_key)
    job.durability.updated_at = _now()
    return job.durability


def apply_replace_durability(job: AnalysisJob, durability: DurableJobContract) -> None:
    _assert_no_auto_resubmit(job.durability, durability)
    nxt = replace(durability, updated_at=_now())
    if nxt.recovery.auto_resubmit and forbids_auto_resubmit(nxt.state):
        raise JobStoreError(f"{nxt.state.value} must never auto-resubmit")
    current = job.durability
    if current is not None:
        if (
            nxt.activity_id
            and nxt.activity_id == current.activity_id
            and nxt.activity_id_persisted_at is None
        ):
            nxt.activity_id_persisted_at = current.activity_id_persisted_at
        if (
            nxt.reservation_id
            and nxt.reservation_id == current.reservation_id
            and nxt.reservation_persisted_at is None
        ):
            nxt.reservation_persisted_at = current.reservation_persisted_at
    job.durability = nxt
    if nxt.fingerprint and job.dedupe_key is None:
        job.dedupe_key = nxt.fingerprint
    job.updated_at = nxt.updated_at
    job.revision += 1


def apply_persist_fingerprint(job: AnalysisJob, fingerprint: str) -> None:
    durability = _touch_durability(job)
    durability.fingerprint = fingerprint
    if job.dedupe_key is None:
        job.dedupe_key = fingerprint
    job.updated_at = durability.updated_at
    job.revision += 1


def apply_persist_activity_id(job: AnalysisJob, activity_id: str) -> None:
    durability = _touch_durability(job)
    if (
        durability.state == DurabilityState.UNKNOWN_VENDOR_STATE
        and durability.activity_id
        and durability.activity_id != activity_id
    ):
        raise JobStoreError(
            "UNKNOWN_VENDOR_STATE must not replace a different activity_id"
        )
    stamp = durability.updated_at
    durability.activity_id = activity_id
    durability.activity_id_persisted_at = stamp
    durability.recovery.activity_id_durable = True
    durability.recovery.auto_resubmit = False
    if durability.state in {
        DurabilityState.SUBMITTING,
        DurabilityState.SUBMITTED,
        DurabilityState.REQUESTED,
        DurabilityState.VALIDATED,
        DurabilityState.ALLOWANCE_RESERVED,
    }:
        durability.state = DurabilityState.ACTIVITY_ID_PERSISTED
    job.updated_at = stamp
    job.revision += 1


def apply_persist_reservation_id(job: AnalysisJob, reservation_id: str) -> None:
    durability = _touch_durability(job)
    stamp = durability.updated_at
    durability.reservation_id = reservation_id
    durability.reservation_persisted_at = stamp
    durability.recovery.reservation_intact = True
    if durability.state in {
        DurabilityState.REQUESTED,
        DurabilityState.VALIDATED,
    }:
        durability.state = DurabilityState.ALLOWANCE_RESERVED
    job.updated_at = stamp
    job.revision += 1


class InMemoryJobStore:
    """J0 process-local memory. Client-reattachable (J1) until process death.

    Implements the J3 durability contract in process. Restart survival
    requires export_jobs/import_jobs (tests) or a file adapter (LIVE-B).
    """

    durability_level = "J0"
    implements_durability_contract = True

    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._by_key: dict[str, str] = {}
        self._by_fingerprint: dict[str, str] = {}
        self._by_activity: dict[str, str] = {}
        self._by_reservation: dict[str, str] = {}
        self._lock = Lock()

    def create(
        self,
        request: dict[str, Any],
        *,
        dedupe_key: str | None = None,
    ) -> AnalysisJob:
        job = _new_job(request, dedupe_key=dedupe_key)
        with self._lock:
            self._put_locked(job)
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

    def find_by_fingerprint(self, fingerprint: str) -> AnalysisJob | None:
        with self._lock:
            job_id = self._by_fingerprint.get(fingerprint) or self._by_key.get(
                fingerprint
            )
            if job_id is None:
                return None
            return self._jobs.get(job_id)

    def find_by_activity_id(self, activity_id: str) -> AnalysisJob | None:
        with self._lock:
            job_id = self._by_activity.get(activity_id)
            if job_id is None:
                return None
            return self._jobs.get(job_id)

    def find_by_reservation_id(self, reservation_id: str) -> AnalysisJob | None:
        with self._lock:
            job_id = self._by_reservation.get(reservation_id)
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
            job = _new_job(request, dedupe_key=dedupe_key)
            self._put_locked(job)
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

    def replace_durability(self, job_id: str, durability: DurableJobContract) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            apply_replace_durability(job, durability)
            self._reindex_locked(job)

    def persist_fingerprint(self, job_id: str, fingerprint: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            apply_persist_fingerprint(job, fingerprint)
            self._reindex_locked(job)

    def persist_activity_id(self, job_id: str, activity_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            apply_persist_activity_id(job, activity_id)
            self._reindex_locked(job)

    def persist_reservation_id(self, job_id: str, reservation_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            apply_persist_reservation_id(job, reservation_id)
            self._reindex_locked(job)

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

    def recover_after_restart(self) -> list[AnalysisJob]:
        recovered: list[AnalysisJob] = []
        with self._lock:
            for job in self._jobs.values():
                apply_restart_recovery(job)
                self._reindex_locked(job)
                recovered.append(job)
        return recovered

    def export_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [analysis_job_to_payload(job) for job in self._jobs.values()]

    def import_jobs(self, records: list[dict[str, Any]]) -> None:
        with self._lock:
            self._jobs.clear()
            self._by_key.clear()
            self._by_fingerprint.clear()
            self._by_activity.clear()
            self._by_reservation.clear()
            for record in records:
                job = analysis_job_from_payload(record)
                self._put_locked(job)

    def list_in_flight(self) -> list[AnalysisJob]:
        with self._lock:
            return [job for job in self._jobs.values() if job.status not in _TERMINAL]

    def reset(self) -> None:
        """Drop in-memory jobs. Models a process restart without persistence."""
        with self._lock:
            self._jobs.clear()
            self._by_key.clear()
            self._by_fingerprint.clear()
            self._by_activity.clear()
            self._by_reservation.clear()

    def _put_locked(self, job: AnalysisJob) -> None:
        self._jobs[job.job_id] = job
        self._reindex_locked(job)

    def _reindex_locked(self, job: AnalysisJob) -> None:
        if job.dedupe_key:
            self._by_key[job.dedupe_key] = job.job_id
        fingerprint = (
            job.durability.fingerprint if job.durability is not None else None
        ) or job.dedupe_key
        if fingerprint:
            self._by_fingerprint[fingerprint] = job.job_id
        if job.durability and job.durability.activity_id:
            self._by_activity[job.durability.activity_id] = job.job_id
        if job.durability and job.durability.reservation_id:
            self._by_reservation[job.durability.reservation_id] = job.job_id


def _guard_section_progress(
    current: TwoSignalJobState, nxt: TwoSignalJobState
) -> None:
    from app.domain.job_lifecycle import apply_progress

    apply_progress(current.historical.progress, nxt.historical.progress)
    apply_progress(current.selected_time.progress, nxt.selected_time.progress)


# Re-export contract types so callers can stay on the JobStore module.
__all__ = [
    "AnalysisJob",
    "CrashRecoveryPlan",
    "DurableJobContract",
    "DurabilityState",
    "INTERRUPT_MESSAGE",
    "InMemoryJobStore",
    "JobErrorClass",
    "JobStore",
    "JobStoreError",
    "_TERMINAL",
    "_assert_status_transition",
    "_guard_section_progress",
    "analysis_job_from_payload",
    "analysis_job_to_payload",
    "apply_persist_activity_id",
    "apply_persist_fingerprint",
    "apply_persist_reservation_id",
    "apply_replace_durability",
    "apply_restart_recovery",
    "_new_job",
]
