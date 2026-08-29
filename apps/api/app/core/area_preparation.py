"""Area-preparation job foundation.

NOT DURABLE YET. In-memory only. No vendor integration.
required_units are protocol-defined acquisition units, not a universal
timestamp count. reference_protocol_id is an opaque analytical identity
and may encode seasonal context without changing this state machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Protocol
from uuid import uuid4


class AreaPreparationStatus(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVING = "RESOLVING"
    PREPARING_REFERENCE = "PREPARING_REFERENCE"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"


_ALLOWED_TRANSITIONS: dict[AreaPreparationStatus, frozenset[AreaPreparationStatus]] = {
    AreaPreparationStatus.UNRESOLVED: frozenset(
        {AreaPreparationStatus.RESOLVING, AreaPreparationStatus.FAILED}
    ),
    AreaPreparationStatus.RESOLVING: frozenset(
        {AreaPreparationStatus.PREPARING_REFERENCE, AreaPreparationStatus.FAILED}
    ),
    AreaPreparationStatus.PREPARING_REFERENCE: frozenset(
        {AreaPreparationStatus.VALIDATING, AreaPreparationStatus.FAILED}
    ),
    AreaPreparationStatus.VALIDATING: frozenset(
        {AreaPreparationStatus.READY, AreaPreparationStatus.FAILED}
    ),
    AreaPreparationStatus.READY: frozenset(),
    AreaPreparationStatus.FAILED: frozenset(),
}


class AreaPreparationError(ValueError):
    """Illegal preparation-state transition or incomplete protocol units."""


@dataclass(frozen=True)
class PreparationIdentity:
    zone_set_id: str
    area_selection_policy_version: str
    reference_protocol_id: str
    geometry_sha256: str | None = None

    def key(self) -> str:
        geometry = self.geometry_sha256 or ""
        return "|".join(
            (
                self.zone_set_id,
                self.area_selection_policy_version,
                self.reference_protocol_id,
                geometry,
            )
        )


@dataclass
class AreaPreparationJob:
    job_id: str
    identity: PreparationIdentity
    status: AreaPreparationStatus
    required_units: int
    completed_units: int = 0
    checkpoint_unit_ids: list[str] = field(default_factory=list)
    package_id: str | None = None
    failure_reason: str | None = None
    joined_existing: bool = False
    durable: bool = False

    def progress_ratio(self) -> float:
        if self.required_units <= 0:
            return 0.0
        return self.completed_units / float(self.required_units)

    def resume_unit_ids(self) -> list[str]:
        return list(self.checkpoint_unit_ids)

    def missing_unit_count(self) -> int:
        return max(self.required_units - self.completed_units, 0)


class AreaPreparationStore(Protocol):
    durable: bool

    def get(self, job_id: str) -> AreaPreparationJob | None: ...

    def get_by_key(self, key: str) -> AreaPreparationJob | None: ...

    def put(self, job: AreaPreparationJob) -> AreaPreparationJob: ...


class InMemoryAreaPreparationStore:
    """Process-local store. NOT DURABLE YET."""

    durable = False

    def __init__(self) -> None:
        self._jobs: dict[str, AreaPreparationJob] = {}
        self._by_key: dict[str, str] = {}
        self._lock = Lock()

    def get(self, job_id: str) -> AreaPreparationJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_by_key(self, key: str) -> AreaPreparationJob | None:
        with self._lock:
            job_id = self._by_key.get(key)
            if job_id is None:
                return None
            return self._jobs.get(job_id)

    def put(self, job: AreaPreparationJob) -> AreaPreparationJob:
        with self._lock:
            self._jobs[job.job_id] = job
            self._by_key[job.identity.key()] = job.job_id
            return job


_store = InMemoryAreaPreparationStore()


def _require(job_id: str, store: AreaPreparationStore) -> AreaPreparationJob:
    job = store.get(job_id)
    if job is None:
        raise AreaPreparationError(f"unknown preparation job {job_id!r}")
    return job


def create_or_join_preparation(
    identity: PreparationIdentity,
    *,
    required_units: int,
    store: AreaPreparationStore | None = None,
) -> AreaPreparationJob:
    if required_units <= 0:
        raise AreaPreparationError("required_units must be a positive protocol-defined count")
    backend = store or _store
    existing = backend.get_by_key(identity.key())
    if existing is not None:
        existing.joined_existing = True
        return existing
    job = AreaPreparationJob(
        job_id=f"prep_{uuid4().hex[:12]}",
        identity=identity,
        status=AreaPreparationStatus.UNRESOLVED,
        required_units=required_units,
        durable=backend.durable,
    )
    return backend.put(job)


def transition(
    job_id: str,
    next_status: AreaPreparationStatus,
    *,
    store: AreaPreparationStore | None = None,
) -> AreaPreparationJob:
    backend = store or _store
    job = _require(job_id, backend)
    if job.status in {AreaPreparationStatus.READY, AreaPreparationStatus.FAILED}:
        raise AreaPreparationError(f"terminal status {job.status.value}")
    allowed = _ALLOWED_TRANSITIONS[job.status]
    if next_status not in allowed:
        raise AreaPreparationError(
            f"invalid transition {job.status.value} -> {next_status.value}"
        )
    if next_status == AreaPreparationStatus.VALIDATING:
        if job.completed_units < job.required_units:
            raise AreaPreparationError("incomplete protocol-defined acquisition units")
    job.status = next_status
    return backend.put(job)


def record_unit_checkpoint(
    job_id: str,
    *,
    unit_id: str,
    store: AreaPreparationStore | None = None,
) -> AreaPreparationJob:
    backend = store or _store
    job = _require(job_id, backend)
    if job.status != AreaPreparationStatus.PREPARING_REFERENCE:
        raise AreaPreparationError("checkpoints are only recorded while PREPARING_REFERENCE")
    if unit_id not in job.checkpoint_unit_ids:
        job.checkpoint_unit_ids.append(unit_id)
        job.completed_units = len(job.checkpoint_unit_ids)
    return backend.put(job)


def mark_ready(
    job_id: str,
    *,
    package_id: str,
    store: AreaPreparationStore | None = None,
) -> AreaPreparationJob:
    backend = store or _store
    job = transition(job_id, AreaPreparationStatus.READY, store=backend)
    job.package_id = package_id
    return backend.put(job)


def fail_preparation(
    job_id: str,
    *,
    reason: str,
    store: AreaPreparationStore | None = None,
) -> AreaPreparationJob:
    backend = store or _store
    job = _require(job_id, backend)
    if job.status == AreaPreparationStatus.READY:
        raise AreaPreparationError("READY jobs cannot fail")
    job.status = AreaPreparationStatus.FAILED
    job.failure_reason = reason
    return backend.put(job)
