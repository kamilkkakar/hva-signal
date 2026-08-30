"""Process-local mock activity ledger. Not production-durable.

A missing activity_id after submit_attempted is UNKNOWN_VENDOR_STATE.
Never invent a second paid submit from that state.
"""

from __future__ import annotations

from threading import Lock
from uuid import uuid4

from app.integrations.mock_vendor.types import (
    LifecyclePhase,
    MockActivityRecord,
    RestartAction,
)


class MockActivityError(ValueError):
    """Illegal activity-record transition."""


_NO_RESUBMIT_PHASES = frozenset(
    {
        LifecyclePhase.UNKNOWN_VENDOR_STATE,
        LifecyclePhase.FAILED_POST_SUBMIT,
        LifecyclePhase.CONSUMED,
        LifecyclePhase.FAILED_PRE_SUBMIT,
    }
)


class InMemoryMockActivityStore:
    """J0 fingerprint + job activity handles."""

    durability = "J0_PROCESS_LOCAL_NOT_DURABLE"

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, MockActivityRecord] = {}
        self._by_job: dict[str, str] = {}
        self._by_fingerprint: dict[str, str] = {}

    def create(
        self,
        *,
        job_id: str,
        request_fingerprint: str,
        geometry_sha256: str,
        reservation_id: str,
        phase: LifecyclePhase = LifecyclePhase.ALLOWANCE_RESERVED,
    ) -> MockActivityRecord:
        with self._lock:
            existing_id = self._by_fingerprint.get(request_fingerprint)
            if existing_id is not None:
                return self._records[existing_id]
            record = MockActivityRecord(
                record_id=f"act_{uuid4().hex[:12]}",
                job_id=job_id,
                request_fingerprint=request_fingerprint,
                geometry_sha256=geometry_sha256,
                reservation_id=reservation_id,
                phase=phase,
            )
            self._records[record.record_id] = record
            self._by_job[job_id] = record.record_id
            self._by_fingerprint[request_fingerprint] = record.record_id
            return record

    def get(self, record_id: str) -> MockActivityRecord | None:
        with self._lock:
            return self._records.get(record_id)

    def find_by_job(self, job_id: str) -> MockActivityRecord | None:
        with self._lock:
            record_id = self._by_job.get(job_id)
            return self._records.get(record_id) if record_id else None

    def find_by_fingerprint(self, request_fingerprint: str) -> MockActivityRecord | None:
        with self._lock:
            record_id = self._by_fingerprint.get(request_fingerprint)
            return self._records.get(record_id) if record_id else None

    def set_phase(
        self,
        record_id: str,
        phase: LifecyclePhase,
        *,
        note: str | None = None,
        submit_attempted: bool | None = None,
    ) -> MockActivityRecord:
        with self._lock:
            record = self._require(record_id)
            updates: dict[str, object] = {"phase": phase}
            if note:
                updates["notes"] = [*record.notes, note]
            if submit_attempted is not None:
                updates["submit_attempted"] = submit_attempted
            updated = record.model_copy(update=updates)
            self._records[record_id] = updated
            return updated

    def persist_activity_id(self, record_id: str, vendor_activity_id: str) -> MockActivityRecord:
        if not vendor_activity_id or not vendor_activity_id.strip():
            raise MockActivityError("vendor_activity_id is required")
        with self._lock:
            record = self._require(record_id)
            if record.vendor_activity_id is not None:
                if record.vendor_activity_id != vendor_activity_id:
                    raise MockActivityError(
                        "activity_id already persisted with a different value"
                    )
                return record
            updated = record.model_copy(
                update={
                    "vendor_activity_id": vendor_activity_id,
                    "phase": LifecyclePhase.ACTIVITY_ID_PERSISTED,
                }
            )
            self._records[record_id] = updated
            return updated

    def mark_unknown(self, record_id: str, *, note: str) -> MockActivityRecord:
        with self._lock:
            record = self._require(record_id)
            if record.vendor_activity_id is not None:
                raise MockActivityError("known activity_id is not uncertain")
            updated = record.model_copy(
                update={
                    "phase": LifecyclePhase.UNKNOWN_VENDOR_STATE,
                    "notes": [*record.notes, note],
                }
            )
            self._records[record_id] = updated
            return updated

    def decide_restart(
        self,
        record: MockActivityRecord | None,
        *,
        reservation_consumed: bool,
        compatible_cache_present: bool,
    ) -> RestartAction:
        if compatible_cache_present:
            return RestartAction.REUSE_CACHE
        if reservation_consumed:
            return RestartAction.NO_RESUBMIT_ALREADY_SPENT
        if record is None:
            return RestartAction.SUBMIT_ALLOWED
        if record.phase == LifecyclePhase.CONSUMED:
            return RestartAction.NO_RESUBMIT_ALREADY_SPENT
        if record.phase == LifecyclePhase.UNKNOWN_VENDOR_STATE:
            return RestartAction.NO_RESUBMIT_UNCERTAIN
        if record.phase in _NO_RESUBMIT_PHASES:
            return RestartAction.NO_RESUBMIT_ALREADY_SPENT
        if record.vendor_activity_id:
            return RestartAction.RESUME_POLL
        if record.submit_attempted and record.vendor_activity_id is None:
            return RestartAction.NO_RESUBMIT_UNCERTAIN
        if record.phase in {
            LifecyclePhase.ALLOWANCE_RESERVED,
            LifecyclePhase.REQUESTED,
            LifecyclePhase.VALIDATED,
        }:
            return RestartAction.SUBMIT_ALLOWED
        return RestartAction.NO_RESUBMIT_UNCERTAIN

    def _require(self, record_id: str) -> MockActivityRecord:
        record = self._records.get(record_id)
        if record is None:
            raise MockActivityError("unknown_activity_record")
        return record
