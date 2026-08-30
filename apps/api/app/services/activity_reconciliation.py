"""Durable activity_id ledger and restart reconciler.

Atomic unit: activity_id + SUBMITTED → ACTIVITY_ID_PERSISTED + fingerprint map.
In-process atomicity is a lock + optional snapshot sink. Cross-process
durability is LIVE-B's store; this module exports a sink hook.

No FortyGuard. No real vendor submit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Protocol
from uuid import uuid4

from app.domain.activity_reconciliation import (
    ActivityBinding,
    ActivityCrashPoint,
    AtMostOneSubmitPolicy,
    DurableLivePhase,
    RecoveryAction,
    RecoveryDecision,
    VendorPollStatus,
    decide_recovery,
    default_at_most_one_submit_policy,
    exactly_once_claim,
    may_call_vendor_submit,
)
from app.services.activity_vendor_hooks import (
    ActivityVendorHooks,
    VendorActivityResult,
)


class ActivityReconciliationError(ValueError):
    """Illegal binding transition, mapping conflict, or forbidden submit."""


class ActivityCrash(RuntimeError):
    """Injected crash for recovery tests. Not a vendor error."""

    def __init__(self, point: ActivityCrashPoint) -> None:
        self.point = point
        super().__init__(point.value)


class ActivitySnapshotSink(Protocol):
    """LIVE-B hook. Called inside the mutation lock before memory publish."""

    def commit_binding(self, binding: ActivityBinding) -> None: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryActivityLedger:
    """J0 memory ledger with atomic publish. Snapshot-exportable for J3."""

    durability = "J0_PROCESS_LOCAL_SNAPSHOT_HOOK"

    def __init__(self, sink: ActivitySnapshotSink | None = None) -> None:
        self._lock = Lock()
        self._records: dict[str, ActivityBinding] = {}
        self._by_job: dict[str, str] = {}
        self._by_fingerprint: dict[str, str] = {}
        self._by_activity_id: dict[str, str] = {}
        self._sink = sink

    def open_or_join(
        self,
        *,
        job_id: str,
        request_fingerprint: str,
        geometry_sha256: str,
        reservation_id: str | None = None,
        phase: DurableLivePhase = DurableLivePhase.ALLOWANCE_RESERVED,
    ) -> tuple[ActivityBinding, bool]:
        with self._lock:
            existing_id = self._by_fingerprint.get(request_fingerprint) or self._by_job.get(
                job_id
            )
            if existing_id is not None:
                existing = self._records[existing_id]
                if existing.request_fingerprint != request_fingerprint:
                    raise ActivityReconciliationError(
                        "job_id already bound to a different fingerprint"
                    )
                if existing.geometry_sha256 != geometry_sha256:
                    raise ActivityReconciliationError(
                        "fingerprint already bound to a different geometry"
                    )
                return existing, True
            if phase not in {
                DurableLivePhase.REQUESTED,
                DurableLivePhase.VALIDATED,
                DurableLivePhase.ALLOWANCE_RESERVED,
            }:
                raise ActivityReconciliationError(
                    "new bindings must start before SUBMITTING"
                )
            record = ActivityBinding(
                record_id=f"act_{uuid4().hex[:12]}",
                job_id=job_id,
                request_fingerprint=request_fingerprint,
                geometry_sha256=geometry_sha256,
                reservation_id=reservation_id,
                phase=phase,
            )
            self._publish_locked(record)
            return record, False

    def get(self, record_id: str) -> ActivityBinding | None:
        with self._lock:
            return self._records.get(record_id)

    def find_by_job(self, job_id: str) -> ActivityBinding | None:
        with self._lock:
            record_id = self._by_job.get(job_id)
            return self._records.get(record_id) if record_id else None

    def find_by_fingerprint(self, request_fingerprint: str) -> ActivityBinding | None:
        with self._lock:
            record_id = self._by_fingerprint.get(request_fingerprint)
            return self._records.get(record_id) if record_id else None

    def find_by_activity_id(self, activity_id: str) -> ActivityBinding | None:
        with self._lock:
            record_id = self._by_activity_id.get(activity_id)
            return self._records.get(record_id) if record_id else None

    def list_all(self) -> list[ActivityBinding]:
        with self._lock:
            return list(self._records.values())

    def mark_submitting(
        self, record_id: str, *, now: datetime | None = None
    ) -> ActivityBinding:
        moment = now or _now()
        with self._lock:
            record = self._require_locked(record_id)
            if record.phase == DurableLivePhase.SUBMITTING and record.activity_id is None:
                return record
            if record.phase not in {
                DurableLivePhase.REQUESTED,
                DurableLivePhase.VALIDATED,
                DurableLivePhase.ALLOWANCE_RESERVED,
            }:
                raise ActivityReconciliationError(
                    f"cannot mark SUBMITTING from {record.phase.value}"
                )
            if record.activity_id is not None:
                raise ActivityReconciliationError("known activity_id cannot re-enter SUBMITTING")
            updated = record.model_copy(
                update={
                    "phase": DurableLivePhase.SUBMITTING,
                    "submit_attempted": True,
                    "submit_attempted_at": record.submit_attempted_at or moment,
                    "notes": [*record.notes, "submitting_persisted_before_vendor_rpc"],
                }
            )
            self._publish_locked(updated)
            return updated

    def note_submitted_awaiting_persist(self, record_id: str) -> ActivityBinding:
        """In-window SUBMITTED without activity_id. Crash here is UNKNOWN."""
        with self._lock:
            record = self._require_locked(record_id)
            if record.phase == DurableLivePhase.SUBMITTED and record.activity_id is None:
                return record
            if record.phase != DurableLivePhase.SUBMITTING or record.activity_id is not None:
                raise ActivityReconciliationError(
                    "SUBMITTED-without-id is only valid after SUBMITTING"
                )
            updated = record.model_copy(
                update={
                    "phase": DurableLivePhase.SUBMITTED,
                    "notes": [*record.notes, "vendor_returned_awaiting_activity_id_persist"],
                }
            )
            self._publish_locked(updated)
            return updated

    def persist_activity_id(
        self,
        record_id: str,
        activity_id: str,
        *,
        now: datetime | None = None,
    ) -> ActivityBinding:
        """Atomic: write activity_id, fingerprint map, ACTIVITY_ID_PERSISTED."""
        moment = now or _now()
        if not activity_id or not activity_id.strip():
            raise ActivityReconciliationError("activity_id is required")
        token = activity_id.strip()
        with self._lock:
            record = self._require_locked(record_id)
            if record.activity_id is not None:
                if record.activity_id != token:
                    raise ActivityReconciliationError(
                        "activity_id already persisted with a different value"
                    )
                return record
            if record.phase not in {
                DurableLivePhase.SUBMITTING,
                DurableLivePhase.SUBMITTED,
            }:
                raise ActivityReconciliationError(
                    f"cannot persist activity_id from {record.phase.value}"
                )
            owner = self._by_activity_id.get(token)
            if owner is not None and owner != record_id:
                raise ActivityReconciliationError(
                    "activity_id already mapped to a different fingerprint"
                )
            mapped = self._by_fingerprint.get(record.request_fingerprint)
            if mapped is not None and mapped != record_id:
                raise ActivityReconciliationError(
                    "fingerprint already mapped to a different record"
                )
            updated = record.model_copy(
                update={
                    "activity_id": token,
                    "phase": DurableLivePhase.ACTIVITY_ID_PERSISTED,
                    "activity_id_persisted_at": moment,
                    "submit_attempted": True,
                    "submit_attempted_at": record.submit_attempted_at or moment,
                    "notes": [*record.notes, "activity_id_persisted_atomically"],
                }
            )
            self._publish_locked(updated)
            return updated

    def mark_processing(self, record_id: str) -> ActivityBinding:
        with self._lock:
            record = self._require_locked(record_id)
            if record.activity_id is None:
                raise ActivityReconciliationError("PROCESSING requires activity_id")
            if record.phase not in {
                DurableLivePhase.ACTIVITY_ID_PERSISTED,
                DurableLivePhase.PROCESSING,
            }:
                raise ActivityReconciliationError(
                    f"cannot enter PROCESSING from {record.phase.value}"
                )
            updated = record.model_copy(
                update={
                    "phase": DurableLivePhase.PROCESSING,
                    "poll_count": record.poll_count + 1,
                }
            )
            self._publish_locked(updated)
            return updated

    def mark_result_received(self, record_id: str) -> ActivityBinding:
        with self._lock:
            record = self._require_locked(record_id)
            if record.activity_id is None:
                raise ActivityReconciliationError("RESULT_RECEIVED requires activity_id")
            if record.phase not in {
                DurableLivePhase.PROCESSING,
                DurableLivePhase.ACTIVITY_ID_PERSISTED,
                DurableLivePhase.RESULT_RECEIVED,
            }:
                raise ActivityReconciliationError(
                    f"cannot mark RESULT_RECEIVED from {record.phase.value}"
                )
            updated = record.model_copy(update={"phase": DurableLivePhase.RESULT_RECEIVED})
            self._publish_locked(updated)
            return updated

    def mark_failed_post_submit(self, record_id: str, *, note: str) -> ActivityBinding:
        with self._lock:
            record = self._require_locked(record_id)
            if record.activity_id is None and not record.submit_attempted:
                raise ActivityReconciliationError("post-submit failure requires submit attempt")
            updated = record.model_copy(
                update={
                    "phase": DurableLivePhase.FAILED_POST_SUBMIT,
                    "notes": [*record.notes, note],
                }
            )
            self._publish_locked(updated)
            return updated

    def park_unknown_for_recovery(
        self, record_id: str, *, reason: str
    ) -> ActivityBinding:
        """UNKNOWN_VENDOR_STATE then RECOVERY_REQUIRED. Never a submit permit."""
        with self._lock:
            record = self._require_locked(record_id)
            if record.activity_id is not None:
                raise ActivityReconciliationError(
                    "known activity_id is not UNKNOWN_VENDOR_STATE"
                )
            updated = record.model_copy(
                update={
                    "phase": DurableLivePhase.RECOVERY_REQUIRED,
                    "notes": [
                        *record.notes,
                        f"UNKNOWN_VENDOR_STATE:{reason}",
                        "parked_RECOVERY_REQUIRED_no_resubmit",
                    ],
                }
            )
            self._publish_locked(updated)
            return updated

    def export_snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return [row.model_dump(mode="json") for row in self._records.values()]

    def import_snapshot(self, rows: list[dict[str, object]]) -> None:
        with self._lock:
            self._records.clear()
            self._by_job.clear()
            self._by_fingerprint.clear()
            self._by_activity_id.clear()
            for raw in rows:
                record = ActivityBinding.model_validate(raw)
                self._index_locked(record)

    def fork_after_restart(self) -> InMemoryActivityLedger:
        """New ledger from snapshot. Models process death + durable reload."""
        clone = InMemoryActivityLedger(sink=self._sink)
        clone.import_snapshot(self.export_snapshot())
        return clone

    def _require_locked(self, record_id: str) -> ActivityBinding:
        record = self._records.get(record_id)
        if record is None:
            raise ActivityReconciliationError("unknown_activity_record")
        return record

    def _publish_locked(self, record: ActivityBinding) -> None:
        if self._sink is not None:
            self._sink.commit_binding(record)
        self._index_locked(record)

    def _index_locked(self, record: ActivityBinding) -> None:
        self._records[record.record_id] = record
        self._by_job[record.job_id] = record.record_id
        self._by_fingerprint[record.request_fingerprint] = record.record_id
        if record.activity_id:
            self._by_activity_id[record.activity_id] = record.record_id


class ActivityReconciler:
    """Restart + resume. Poll/fetch only when activity_id is known."""

    def __init__(
        self,
        ledger: InMemoryActivityLedger,
        *,
        policy: AtMostOneSubmitPolicy | None = None,
    ) -> None:
        self.ledger = ledger
        self.policy = policy or default_at_most_one_submit_policy()

    def inspect(self, record_id: str) -> RecoveryDecision:
        record = self.ledger.get(record_id)
        if record is None:
            raise ActivityReconciliationError("unknown_activity_record")
        return decide_recovery(record, policy=self.policy)

    def apply_restart(self, record_id: str) -> RecoveryDecision:
        record = self.ledger.get(record_id)
        if record is None:
            raise ActivityReconciliationError("unknown_activity_record")
        decision = decide_recovery(record, policy=self.policy)
        if decision.action in {
            RecoveryAction.HOLD_UNKNOWN,
            RecoveryAction.REQUIRE_OPERATOR_RECOVERY,
        }:
            parked = self.ledger.park_unknown_for_recovery(
                record_id, reason=decision.reason
            )
            return decide_recovery(parked, policy=self.policy)
        if decision.action == RecoveryAction.RESUME_POLL and record.activity_id:
            if record.phase in {
                DurableLivePhase.SUBMITTED,
                DurableLivePhase.ACTIVITY_ID_PERSISTED,
            }:
                self.ledger.mark_processing(record_id)
            return decide_recovery(self.ledger.get(record_id), policy=self.policy)
        return decision

    def apply_restart_all(self) -> list[RecoveryDecision]:
        return [self.apply_restart(row.record_id) for row in self.ledger.list_all()]

    def resume_processing(
        self,
        record_id: str,
        hooks: ActivityVendorHooks,
    ) -> tuple[ActivityBinding, VendorActivityResult | None]:
        """Status poll / result fetch. Never a second submit."""
        decision = self.inspect(record_id)
        if may_call_vendor_submit(decision):
            raise ActivityReconciliationError("resume_processing is not a submit path")
        if decision.action in {
            RecoveryAction.HOLD_UNKNOWN,
            RecoveryAction.REQUIRE_OPERATOR_RECOVERY,
        }:
            raise ActivityReconciliationError(
                "UNKNOWN_VENDOR_STATE cannot resume; operator recovery required"
            )
        if decision.action not in {
            RecoveryAction.RESUME_POLL,
            RecoveryAction.FETCH_RESULT,
        }:
            raise ActivityReconciliationError(
                f"cannot resume vendor I/O for action {decision.action.value}"
            )
        if not decision.activity_id:
            raise ActivityReconciliationError("resume requires activity_id")

        if decision.action == RecoveryAction.RESUME_POLL:
            current = self.ledger.get(record_id)
            assert current is not None
            if current.phase == DurableLivePhase.ACTIVITY_ID_PERSISTED:
                current = self.ledger.mark_processing(record_id)
            status = hooks.poll_status(decision.activity_id)
            if status.status == VendorPollStatus.PROCESSING:
                if current.phase != DurableLivePhase.PROCESSING:
                    current = self.ledger.mark_processing(record_id)
                return current, None
            if status.status == VendorPollStatus.SUCCEEDED:
                result = hooks.fetch_result(decision.activity_id)
                return self.ledger.mark_result_received(record_id), result
            if status.status in {VendorPollStatus.FAILED, VendorPollStatus.NOT_FOUND}:
                failed = self.ledger.mark_failed_post_submit(
                    record_id, note=f"vendor_{status.status.value.lower()}"
                )
                return failed, None
            raise ActivityReconciliationError(f"unhandled vendor status {status.status}")

        result = hooks.fetch_result(decision.activity_id)
        current = self.ledger.get(record_id)
        assert current is not None
        return current, result

    def refuse_blind_resubmit(self, record_id: str) -> None:
        decision = self.inspect(record_id)
        if may_call_vendor_submit(decision):
            return
        raise ActivityReconciliationError(
            f"blind resubmit refused: {decision.action.value} ({decision.reason})"
        )


def simulate_submit_then_crash(
    ledger: InMemoryActivityLedger,
    *,
    job_id: str,
    request_fingerprint: str,
    geometry_sha256: str,
    activity_id: str,
    crash_at: ActivityCrashPoint | None,
    submit_counter: list[str],
    reservation_id: str | None = None,
) -> ActivityBinding:
    """Controlled submit path for crash tests. Increments submit_counter once."""
    binding, _joined = ledger.open_or_join(
        job_id=job_id,
        request_fingerprint=request_fingerprint,
        geometry_sha256=geometry_sha256,
        reservation_id=reservation_id,
    )
    ledger.mark_submitting(binding.record_id)
    submit_counter.append(activity_id)
    ledger.note_submitted_awaiting_persist(binding.record_id)
    if crash_at == ActivityCrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID_SAVE:
        raise ActivityCrash(crash_at)
    persisted = ledger.persist_activity_id(binding.record_id, activity_id)
    if crash_at == ActivityCrashPoint.AFTER_ACTIVITY_ID_SAVE:
        raise ActivityCrash(crash_at)
    processing = ledger.mark_processing(persisted.record_id)
    if crash_at == ActivityCrashPoint.DURING_VENDOR_PROCESSING:
        raise ActivityCrash(crash_at)
    return processing


def honesty_record() -> dict[str, object]:
    claim = exactly_once_claim()
    policy = default_at_most_one_submit_policy()
    return {
        "claim": claim.model_dump(),
        "policy": policy.model_dump(),
        "mathematical_exactly_once": False,
    }
