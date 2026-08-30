"""Executable J3/J4 crash-matrix runner against fakes and existing ledgers.

Cache/dedupe before spend. Reserve before submit. Persist activity_id before
treating submit as durable. Consume only after cache. No FortyGuard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.job_store import InMemoryJobStore, JobStore
from app.domain.demo_allowance import (
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
)
from app.domain.enums import JobStatus
from app.domain.live_crash_matrix.policy import RecoveryDecision, decide_recovery
from app.domain.live_crash_matrix.states import (
    CrashPoint,
    DurableWorkerState,
    RecoveryAction,
)
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.live_crash_matrix.fakes import FakeLiveVendor, SimulatedCrash

GEO_SHA = "bb" * 32


class CrashMatrixRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    fingerprint: str
    state: DurableWorkerState
    reservation_id: str | None = None
    vendor_activity_id: str | None = None
    submit_attempted: bool = False
    result: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)


class CrashMatrixRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal[
        "ready",
        "crashed",
        "uncertain",
        "recovery_required",
        "reused",
        "denied",
        "no_resubmit",
        "joined",
    ]
    job_id: str | None = None
    state: str | None = None
    reservation_id: str | None = None
    reservation_state: str | None = None
    vendor_activity_id: str | None = None
    submit_count: int = 0
    recovery_action: str | None = None
    reason: str | None = None
    cache_hit: bool = False
    crash_point: str | None = None


class CrashMatrixRunner:
    """In-process durable harness. Surviving stores model a J3 worker restart."""

    def __init__(
        self,
        *,
        ledger: InMemoryDemoAllowanceLedger,
        vendor: FakeLiveVendor | None = None,
        store: JobStore | None = None,
        identity_area_id: str = "phoenix-demo",
    ) -> None:
        self.ledger = ledger
        self.vendor = vendor or FakeLiveVendor()
        self.store = store or InMemoryJobStore()
        self.identity_area_id = identity_area_id
        self.cache: dict[str, dict[str, Any]] = {}
        self._records: dict[str, CrashMatrixRecord] = {}
        self._by_fingerprint: dict[str, str] = {}
        self._lock = Lock()

    def identity(self, fingerprint: str) -> DemoRequestIdentity:
        return DemoRequestIdentity(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            request_fingerprint=fingerprint,
            geometry_sha256=GEO_SHA,
            area_id=self.identity_area_id,
        )

    def record(self, job_id: str) -> CrashMatrixRecord | None:
        return self._records.get(job_id)

    def acquire(
        self,
        fingerprint: str,
        *,
        crash_at: CrashPoint | None = None,
        force_resubmit: bool = False,
        automatic_paid_retry: bool = False,
        now: datetime | None = None,
    ) -> CrashMatrixRunResult:
        moment = now or datetime.now(timezone.utc)
        existing_id = self._by_fingerprint.get(fingerprint)
        if existing_id is not None:
            return self.recover(
                existing_id,
                crash_at=None,
                force_resubmit=force_resubmit,
                automatic_paid_retry=automatic_paid_retry,
                now=moment,
            )
        if fingerprint in self.cache:
            return CrashMatrixRunResult(
                outcome="reused",
                state=DurableWorkerState.CACHE_HIT.value,
                submit_count=self.vendor.submit_count,
                recovery_action=RecoveryAction.REUSE_CACHE.value,
                reason="cache_hit_before_job",
                cache_hit=True,
            )
        job, _joined = self.store.create_or_join(
            {"fingerprint": fingerprint},
            dedupe_key=fingerprint,
        )
        record = CrashMatrixRecord(
            job_id=job.job_id,
            fingerprint=fingerprint,
            state=DurableWorkerState.REQUESTED,
        )
        with self._lock:
            self._records[record.job_id] = record
            self._by_fingerprint[fingerprint] = record.job_id
        record.state = DurableWorkerState.VALIDATED
        try:
            return self._run_from_validated(record, crash_at=crash_at, now=moment)
        except SimulatedCrash as crash:
            return self._crashed(record, crash.point)

    def recover(
        self,
        job_id: str,
        *,
        crash_at: CrashPoint | None = None,
        force_resubmit: bool = False,
        automatic_paid_retry: bool = False,
        now: datetime | None = None,
    ) -> CrashMatrixRunResult:
        moment = now or datetime.now(timezone.utc)
        record = self._records.get(job_id)
        if record is None:
            return CrashMatrixRunResult(
                outcome="no_resubmit",
                submit_count=self.vendor.submit_count,
                recovery_action=RecoveryAction.NO_AUTOMATIC_RESUBMIT.value,
                reason="restart_state_lost",
            )
        reservation_state = self._reservation_state(record.reservation_id)
        decision = decide_recovery(
            record.state,
            vendor_activity_id=record.vendor_activity_id,
            submit_attempted=record.submit_attempted,
            cache_present=record.fingerprint in self.cache,
            reservation_state=reservation_state,
            force_resubmit=force_resubmit,
            automatic_paid_retry=automatic_paid_retry,
        )
        if not decision.allow_vendor_submit and decision.action in {
            RecoveryAction.NO_AUTOMATIC_RESUBMIT,
            RecoveryAction.OPERATOR_RECONCILE,
        }:
            record.state = decision.next_state
            record.notes.append(decision.reason)
            outcome: Literal["uncertain", "recovery_required", "no_resubmit"]
            if decision.action == RecoveryAction.OPERATOR_RECONCILE:
                outcome = "recovery_required"
            elif decision.next_state == DurableWorkerState.UNKNOWN_VENDOR_STATE:
                outcome = "uncertain"
            else:
                outcome = "no_resubmit"
            return self._result(
                record,
                outcome=outcome,
                decision=decision,
                reason=decision.reason,
            )
        try:
            result = self._apply_recovery(
                record, decision, crash_at=crash_at, now=moment
            )
            if result.recovery_action is None:
                return result.model_copy(
                    update={"recovery_action": decision.action.value}
                )
            return result
        except SimulatedCrash as crash:
            return self._crashed(record, crash.point)

    def simulate_process_death(self, *, keep_vendor: bool = True) -> None:
        """J0 wipe. Vendor object may survive as an external system."""
        self._records.clear()
        self._by_fingerprint.clear()
        self.cache.clear()
        self.store.reset()
        self.ledger = InMemoryDemoAllowanceLedger(self.ledger.policy)
        if not keep_vendor:
            self.vendor = FakeLiveVendor(
                poll_ticks_until_ready=self.vendor.poll_ticks_until_ready
            )

    def _apply_recovery(
        self,
        record: CrashMatrixRecord,
        decision: RecoveryDecision,
        *,
        crash_at: CrashPoint | None,
        now: datetime,
    ) -> CrashMatrixRunResult:
        if decision.action == RecoveryAction.REUSE_CACHE:
            record.state = DurableWorkerState.CACHE_HIT
            return self._result(
                record,
                outcome="reused",
                decision=decision,
                reason=decision.reason,
                cache_hit=True,
            )
        if decision.action == RecoveryAction.CONSUME_ONLY:
            self._consume(record, now=now)
            return self._result(
                record,
                outcome="ready",
                decision=decision,
                reason=decision.reason,
                cache_hit=True,
            )
        if decision.action == RecoveryAction.CACHE_THEN_CONSUME:
            self._write_cache(record)
            self._consume(record, now=now)
            return self._result(
                record,
                outcome="ready",
                decision=decision,
                reason=decision.reason,
                cache_hit=True,
            )
        if decision.action == RecoveryAction.RESUME_POLL:
            return self._poll_and_finish(record, crash_at=crash_at, now=now)
        if decision.action == RecoveryAction.CONTINUE_TO_SUBMIT:
            return self._submit_path(record, crash_at=crash_at, now=now)
        if decision.action == RecoveryAction.CONTINUE_FROM_CACHE_CHECK:
            return self._run_from_validated(record, crash_at=crash_at, now=now)
        if decision.action == RecoveryAction.RELEASE_AND_MAY_RETRY_PRE_SUBMIT:
            self._release_if_reserved(record)
            record.state = DurableWorkerState.VALIDATED
            return self._run_from_validated(record, crash_at=crash_at, now=now)
        if decision.action == RecoveryAction.JOIN_IN_FLIGHT:
            return self._result(
                record,
                outcome="joined",
                decision=decision,
                reason=decision.reason,
            )
        return self._result(
            record,
            outcome="no_resubmit",
            decision=decision,
            reason=decision.reason,
        )

    def _run_from_validated(
        self,
        record: CrashMatrixRecord,
        *,
        crash_at: CrashPoint | None,
        now: datetime,
    ) -> CrashMatrixRunResult:
        if record.fingerprint in self.cache:
            record.state = DurableWorkerState.CACHE_HIT
            return self._result(
                record,
                outcome="reused",
                reason="cache_hit_before_reserve",
                cache_hit=True,
            )
        self._maybe_crash(crash_at, CrashPoint.BEFORE_RESERVE)
        identity = self.identity(record.fingerprint)
        decision = self.ledger.try_reserve(identity, planned_units=1, now=now)
        if decision.reservation is None or not decision.spend_authorized:
            if (
                decision.reservation is not None
                and decision.code.value == "JOIN_EXISTING_RESERVATION"
            ):
                record.reservation_id = decision.reservation.reservation_id
                record.state = DurableWorkerState.ALLOWANCE_RESERVED
                return self._submit_path(record, crash_at=crash_at, now=now)
            record.state = DurableWorkerState.FAILED_PRE_SUBMIT
            record.notes.append(decision.code.value)
            return self._result(
                record,
                outcome="denied",
                reason=decision.code.value,
            )
        record.reservation_id = decision.reservation.reservation_id
        record.state = DurableWorkerState.ALLOWANCE_RESERVED
        self._maybe_crash(crash_at, CrashPoint.AFTER_RESERVE)
        return self._submit_path(record, crash_at=crash_at, now=now)

    def _submit_path(
        self,
        record: CrashMatrixRecord,
        *,
        crash_at: CrashPoint | None,
        now: datetime,
    ) -> CrashMatrixRunResult:
        if record.fingerprint in self.cache:
            self._release_if_reserved(record)
            record.state = DurableWorkerState.CACHE_HIT
            return self._result(
                record,
                outcome="reused",
                reason="cache_recheck_before_submit",
                cache_hit=True,
            )
        self._maybe_crash(crash_at, CrashPoint.BEFORE_VENDOR_SUBMIT)
        record.state = DurableWorkerState.SUBMITTING
        record.submit_attempted = True
        if crash_at == CrashPoint.DURING_SUBMIT:
            self.vendor.begin_unacked_submit(record.fingerprint)
            record.state = DurableWorkerState.UNKNOWN_VENDOR_STATE
            record.notes.append("crash_during_submit_no_activity_id")
            raise SimulatedCrash(CrashPoint.DURING_SUBMIT)
        activity_id = self.vendor.submit(record.fingerprint)
        record.state = DurableWorkerState.SUBMITTED
        if crash_at == CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID:
            record.state = DurableWorkerState.UNKNOWN_VENDOR_STATE
            record.notes.append("activity_id_not_persisted")
            raise SimulatedCrash(CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID)
        record.vendor_activity_id = activity_id
        record.state = DurableWorkerState.ACTIVITY_ID_PERSISTED
        self._maybe_crash(crash_at, CrashPoint.AFTER_ACTIVITY_ID_SAVE)
        return self._poll_and_finish(record, crash_at=crash_at, now=now)

    def _poll_and_finish(
        self,
        record: CrashMatrixRecord,
        *,
        crash_at: CrashPoint | None,
        now: datetime,
    ) -> CrashMatrixRunResult:
        if record.vendor_activity_id is None:
            record.state = DurableWorkerState.UNKNOWN_VENDOR_STATE
            return self._result(
                record,
                outcome="uncertain",
                reason="resume_poll_missing_activity_id",
            )
        record.state = DurableWorkerState.PROCESSING
        if crash_at == CrashPoint.DURING_VENDOR_PROCESSING:
            raise SimulatedCrash(CrashPoint.DURING_VENDOR_PROCESSING)
        result: dict[str, Any] | None = None
        for _ in range(8):
            status = self.vendor.get_status(record.vendor_activity_id)
            if status["status"] == "succeeded" and isinstance(status["result"], dict):
                result = dict(status["result"])
                break
        if result is None:
            record.state = DurableWorkerState.FAILED_POST_SUBMIT
            return self._result(record, outcome="denied", reason="poll_exhausted")
        record.result = result
        record.state = DurableWorkerState.RESULT_RECEIVED
        record.state = DurableWorkerState.NORMALIZED
        self._maybe_crash(crash_at, CrashPoint.AFTER_RESULT_BEFORE_CACHE)
        self._write_cache(record)
        self._maybe_crash(crash_at, CrashPoint.AFTER_CACHE_BEFORE_CONSUME)
        self._consume(record, now=now)
        return self._result(record, outcome="ready", reason="consumed")

    def _write_cache(self, record: CrashMatrixRecord) -> None:
        if record.result is None:
            raise RuntimeError("cannot cache without a result")
        self.cache[record.fingerprint] = dict(record.result)
        self.store.set_result(record.job_id, dict(record.result), JobStatus.COMPLETE)
        record.state = DurableWorkerState.CACHED

    def _consume(self, record: CrashMatrixRecord, *, now: datetime) -> None:
        if record.reservation_id is None:
            record.state = DurableWorkerState.CONSUMED
            return
        reservation = self.ledger.get(record.reservation_id)
        if reservation is None or reservation.state != ReservationState.RESERVED:
            record.state = DurableWorkerState.CONSUMED
            return
        self.ledger.consume(
            record.reservation_id,
            identity=self.identity(record.fingerprint),
            planned_units=reservation.planned_units,
            now=now,
        )
        record.state = DurableWorkerState.CONSUMED

    def _release_if_reserved(self, record: CrashMatrixRecord) -> None:
        if record.reservation_id is None:
            return
        reservation = self.ledger.get(record.reservation_id)
        if reservation is not None and reservation.state == ReservationState.RESERVED:
            self.ledger.release(record.reservation_id)

    def _reservation_state(self, reservation_id: str | None) -> str | None:
        if reservation_id is None:
            return None
        reservation = self.ledger.get(reservation_id)
        return reservation.state.value if reservation is not None else None

    def _maybe_crash(
        self, crash_at: CrashPoint | None, point: CrashPoint
    ) -> None:
        if crash_at == point:
            raise SimulatedCrash(point)

    def _crashed(
        self, record: CrashMatrixRecord, point: CrashPoint
    ) -> CrashMatrixRunResult:
        return CrashMatrixRunResult(
            outcome="crashed",
            job_id=record.job_id,
            state=record.state.value,
            reservation_id=record.reservation_id,
            reservation_state=self._reservation_state(record.reservation_id),
            vendor_activity_id=record.vendor_activity_id,
            submit_count=self.vendor.submit_count,
            reason=f"simulated_crash:{point.value}",
            crash_point=point.value,
            cache_hit=record.fingerprint in self.cache,
        )

    def _result(
        self,
        record: CrashMatrixRecord,
        *,
        outcome: Literal[
            "ready",
            "crashed",
            "uncertain",
            "recovery_required",
            "reused",
            "denied",
            "no_resubmit",
            "joined",
        ],
        reason: str | None,
        decision: RecoveryDecision | None = None,
        cache_hit: bool = False,
    ) -> CrashMatrixRunResult:
        return CrashMatrixRunResult(
            outcome=outcome,
            job_id=record.job_id,
            state=record.state.value,
            reservation_id=record.reservation_id,
            reservation_state=self._reservation_state(record.reservation_id),
            vendor_activity_id=record.vendor_activity_id,
            submit_count=self.vendor.submit_count,
            recovery_action=decision.action.value if decision else None,
            reason=reason,
            cache_hit=cache_hit,
        )


def default_enabled_policy(**overrides: object) -> DemoAllowancePolicy:
    payload: dict[str, object] = {
        "enabled": True,
        "max_total_acquisition_units": 4,
        "max_units_per_request": 1,
        "allowed_area_ids": frozenset({"phoenix-demo"}),
    }
    payload.update(overrides)
    return DemoAllowancePolicy.model_validate(payload)


def new_runner(**policy_overrides: object) -> CrashMatrixRunner:
    return CrashMatrixRunner(
        ledger=InMemoryDemoAllowanceLedger(default_enabled_policy(**policy_overrides)),
        vendor=FakeLiveVendor(poll_ticks_until_ready=1),
        store=InMemoryJobStore(),
    )
