"""J3/J4 durable worker machine: apply events with illegal-transition guards.

Does not call vendors, FortyGuard, JobStore, or allowance ledgers.
Callers persist the record (LIVE-A/B) and perform side effects (LIVE-D/F/H).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.live_worker_state import (
    NEVER_RESUBMIT_FROM,
    RecoveryAction,
    RestartDisposition,
    SpendRisk,
    TransitionMode,
    WorkerEvent,
    WorkerState,
    IllegalWorkerTransition,
    LiveWorkerRecord,
    assert_legal_transition,
    assert_no_blind_paid_retry,
    classify_restart,
    is_terminal,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DurableWorkerMachine:
    """Explicit worker state machine for one live-acquisition attempt."""

    def __init__(self, record: LiveWorkerRecord) -> None:
        self.record = record

    @classmethod
    def create(cls, *, job_id: str, fingerprint: str) -> DurableWorkerMachine:
        return cls(LiveWorkerRecord(job_id=job_id, fingerprint=fingerprint))

    def snapshot(self) -> LiveWorkerRecord:
        return self.record.model_copy()

    def validate(self) -> LiveWorkerRecord:
        return self._move(WorkerState.VALIDATED, WorkerEvent.VALIDATE)

    def note_cache_hit(self) -> LiveWorkerRecord:
        self._require_not_joined_submit()
        if self.record.state not in {WorkerState.VALIDATED, WorkerState.ALLOWANCE_RESERVED}:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.CACHE_HIT,
                "cache hit is only legal after validation or a pre-submit recheck",
                event=WorkerEvent.CACHE_HIT,
            )
        if self.record.state == WorkerState.ALLOWANCE_RESERVED:
            return self._recheck_cache_hit()
        self.record.cache_checked = True
        return self._move(WorkerState.CACHE_HIT, WorkerEvent.CACHE_HIT)

    def join(self, leader_job_id: str) -> LiveWorkerRecord:
        if not leader_job_id:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.JOINED,
                "join requires a leader job_id",
                event=WorkerEvent.JOIN,
            )
        if leader_job_id == self.record.job_id:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.JOINED,
                "a job cannot join itself",
                event=WorkerEvent.JOIN,
            )
        self.record.cache_checked = True
        self.record.joined_job_id = leader_job_id
        return self._move(WorkerState.JOINED, WorkerEvent.JOIN)

    def note_cache_miss(self) -> LiveWorkerRecord:
        if self.record.state not in {WorkerState.VALIDATED, WorkerState.ALLOWANCE_RESERVED}:
            raise IllegalWorkerTransition(
                self.record.state,
                self.record.state,
                "cache miss may be noted only at VALIDATED or ALLOWANCE_RESERVED",
                event=WorkerEvent.RESERVE,
            )
        self.record.cache_checked = True
        if self.record.state == WorkerState.ALLOWANCE_RESERVED:
            self.record.cache_rechecked_before_submit = True
        self.record.updated_at = _now()
        return self.snapshot()

    def reserve(self, reservation_id: str) -> LiveWorkerRecord:
        if not reservation_id:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.ALLOWANCE_RESERVED,
                "reservation_id is required",
                event=WorkerEvent.RESERVE,
            )
        if not self.record.cache_checked:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.ALLOWANCE_RESERVED,
                "cache/dedupe must run before spend reservation",
                event=WorkerEvent.RESERVE,
            )
        if self.record.state == WorkerState.JOINED:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.ALLOWANCE_RESERVED,
                "joined jobs must not reserve",
                event=WorkerEvent.RESERVE,
            )
        if self.record.state == WorkerState.CACHE_HIT:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.ALLOWANCE_RESERVED,
                "CACHE_HIT must not reserve",
                event=WorkerEvent.RESERVE,
            )
        self.record.reservation_id = reservation_id
        return self._move(WorkerState.ALLOWANCE_RESERVED, WorkerEvent.RESERVE)

    def begin_submit(self) -> LiveWorkerRecord:
        if self.record.state != WorkerState.ALLOWANCE_RESERVED:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.SUBMITTING,
                "reserve before submit",
                event=WorkerEvent.BEGIN_SUBMIT,
            )
        if not self.record.reservation_id:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.SUBMITTING,
                "submit requires a reservation_id",
                event=WorkerEvent.BEGIN_SUBMIT,
            )
        if not self.record.cache_checked or not self.record.cache_rechecked_before_submit:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.SUBMITTING,
                "cache must be rechecked immediately before submit",
                event=WorkerEvent.BEGIN_SUBMIT,
            )
        if self.record.submit_attempted and not self.record.submit_never_left:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.SUBMITTING,
                "blind paid retry is forbidden",
                event=WorkerEvent.BEGIN_SUBMIT,
            )
        self._move(WorkerState.SUBMITTING, WorkerEvent.BEGIN_SUBMIT)
        self.record.submit_attempted = True
        self.record.submit_never_left = False
        self.record.updated_at = _now()
        return self.snapshot()

    def ack_submit(self, activity_id: str | None = None) -> LiveWorkerRecord:
        if self.record.state != WorkerState.SUBMITTING:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.SUBMITTED,
                "ACK_SUBMIT is only valid from SUBMITTING",
                event=WorkerEvent.ACK_SUBMIT,
            )
        self.record.submitted_to_vendor = True
        if activity_id:
            self.record.activity_id = activity_id
        self.record.activity_id_durable = False
        return self._move(WorkerState.SUBMITTED, WorkerEvent.ACK_SUBMIT)

    def persist_activity_id(self, activity_id: str) -> LiveWorkerRecord:
        if not activity_id:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.ACTIVITY_ID_PERSISTED,
                "activity_id is required before a submit is durable",
                event=WorkerEvent.PERSIST_ACTIVITY_ID,
            )
        if self.record.state != WorkerState.SUBMITTED:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.ACTIVITY_ID_PERSISTED,
                "persist activity_id only from SUBMITTED",
                event=WorkerEvent.PERSIST_ACTIVITY_ID,
            )
        self.record.activity_id = activity_id
        self.record.activity_id_durable = True
        self.record.submitted_to_vendor = True
        return self._move(
            WorkerState.ACTIVITY_ID_PERSISTED, WorkerEvent.PERSIST_ACTIVITY_ID
        )

    def begin_processing(self) -> LiveWorkerRecord:
        if not self.record.activity_id_durable or not self.record.activity_id:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.PROCESSING,
                "processing requires a durable activity_id",
                event=WorkerEvent.BEGIN_PROCESSING,
            )
        return self._move(WorkerState.PROCESSING, WorkerEvent.BEGIN_PROCESSING)

    def receive_result(self) -> LiveWorkerRecord:
        return self._move(WorkerState.RESULT_RECEIVED, WorkerEvent.RECEIVE_RESULT)

    def normalize(self) -> LiveWorkerRecord:
        return self._move(WorkerState.NORMALIZED, WorkerEvent.NORMALIZE)

    def cache_result(self) -> LiveWorkerRecord:
        self.record.result_cached = True
        self.record.consume_required = True
        return self._move(WorkerState.CACHED, WorkerEvent.CACHE)

    def consume(self) -> LiveWorkerRecord:
        if not self.record.result_cached:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.CONSUMED,
                "cache the result before consuming allowance",
                event=WorkerEvent.CONSUME,
            )
        self.record.consume_required = False
        return self._move(WorkerState.CONSUMED, WorkerEvent.CONSUME)

    def fail_pre_submit(self, reason: str, *, submit_never_left: bool = False) -> LiveWorkerRecord:
        if self.record.submitted_to_vendor or self.record.activity_id_durable:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.FAILED_PRE_SUBMIT,
                "vendor submit already happened; use FAILED_POST_SUBMIT",
                event=WorkerEvent.FAIL_PRE_SUBMIT,
            )
        if self.record.state == WorkerState.SUBMITTING and not submit_never_left:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.FAILED_PRE_SUBMIT,
                "SUBMITTING without proof the request never left must be UNKNOWN_VENDOR_STATE",
                event=WorkerEvent.FAIL_PRE_SUBMIT,
            )
        if self.record.submit_attempted and not submit_never_left:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.FAILED_PRE_SUBMIT,
                "a submit attempt without never-left proof is not pre-submit failure",
                event=WorkerEvent.FAIL_PRE_SUBMIT,
            )
        self.record.submit_never_left = submit_never_left or not self.record.submit_attempted
        self.record.error_class = "FAILED_PRE_SUBMIT"
        self.record.recovery_reason = reason
        if self.record.reservation_id:
            self.record.reservation_release_required = True
        return self._move(WorkerState.FAILED_PRE_SUBMIT, WorkerEvent.FAIL_PRE_SUBMIT)

    def fail_post_submit(self, reason: str) -> LiveWorkerRecord:
        if self.record.state in {
            WorkerState.REQUESTED,
            WorkerState.VALIDATED,
            WorkerState.CACHE_HIT,
            WorkerState.ALLOWANCE_RESERVED,
        }:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.FAILED_POST_SUBMIT,
                "post-submit failure requires a submit attempt",
                event=WorkerEvent.FAIL_POST_SUBMIT,
            )
        if (
            self.record.state == WorkerState.SUBMITTING
            and not self.record.submitted_to_vendor
        ):
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.FAILED_POST_SUBMIT,
                "SUBMITTING without vendor ack is UNKNOWN, not FAILED_POST_SUBMIT",
                event=WorkerEvent.FAIL_POST_SUBMIT,
            )
        self.record.error_class = "FAILED_POST_SUBMIT"
        self.record.recovery_reason = reason
        return self._move(WorkerState.FAILED_POST_SUBMIT, WorkerEvent.FAIL_POST_SUBMIT)

    def mark_unknown(self, reason: str) -> LiveWorkerRecord:
        if self.record.state not in {
            WorkerState.SUBMITTING,
            WorkerState.SUBMITTED,
            WorkerState.JOINED,
            WorkerState.RECOVERY_REQUIRED,
        }:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.UNKNOWN_VENDOR_STATE,
                "unknown vendor state is only for in-flight submit uncertainty",
                event=WorkerEvent.MARK_UNKNOWN,
            )
        self.record.error_class = "UNKNOWN_VENDOR_STATE"
        self.record.recovery_reason = reason
        return self._move(WorkerState.UNKNOWN_VENDOR_STATE, WorkerEvent.MARK_UNKNOWN)

    def require_recovery(self, reason: str) -> LiveWorkerRecord:
        self.record.recovery_reason = reason
        return self._move(WorkerState.RECOVERY_REQUIRED, WorkerEvent.REQUIRE_RECOVERY)

    def apply_restart(self) -> tuple[LiveWorkerRecord, RestartDisposition]:
        disposition = classify_restart(self.record)
        if disposition.may_resubmit:
            raise IllegalWorkerTransition(
                self.record.state,
                disposition.next_state,
                "restart classifier must never authorize resubmit",
                event=WorkerEvent.APPLY_RESTART,
            )
        if disposition.next_state != self.record.state:
            if (
                disposition.next_state in {WorkerState.SUBMITTING, WorkerState.SUBMITTED}
            ):
                raise IllegalWorkerTransition(
                    self.record.state,
                    disposition.next_state,
                    "restart must not enter a submit state automatically",
                    event=WorkerEvent.APPLY_RESTART,
                )
            self._move(
                disposition.next_state,
                WorkerEvent.APPLY_RESTART,
                mode=TransitionMode.AUTOMATIC,
            )
        else:
            self.record.updated_at = _now()
        return self.snapshot(), disposition

    def reconcile(self, to_state: WorkerState, *, reason: str, **facts: Any) -> LiveWorkerRecord:
        """Operator-safe reconcile. Never a paid retry or automatic resubmit."""
        if to_state in {WorkerState.SUBMITTING, WorkerState.SUBMITTED}:
            raise IllegalWorkerTransition(
                self.record.state,
                to_state,
                "reconcile must never resubmit",
                event=WorkerEvent.RECONCILE,
            )
        if self.record.state not in {
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.RECOVERY_REQUIRED,
        }:
            raise IllegalWorkerTransition(
                self.record.state,
                to_state,
                "reconcile is only legal from UNKNOWN_VENDOR_STATE or RECOVERY_REQUIRED",
                event=WorkerEvent.RECONCILE,
            )
        activity_id = facts.get("activity_id")
        if isinstance(activity_id, str) and activity_id:
            self.record.activity_id = activity_id
            self.record.activity_id_durable = True
            self.record.submitted_to_vendor = True
        if facts.get("result_cached") is True:
            self.record.result_cached = True
        if facts.get("proven_no_submit") is True:
            if to_state not in {
                WorkerState.FAILED_PRE_SUBMIT,
                WorkerState.CACHE_HIT,
            }:
                raise IllegalWorkerTransition(
                    self.record.state,
                    to_state,
                    "proven_no_submit may only resolve to FAILED_PRE_SUBMIT or CACHE_HIT",
                    event=WorkerEvent.RECONCILE,
                )
            self.record.submit_never_left = True
            self.record.submitted_to_vendor = False
            self.record.activity_id_durable = False
            if self.record.reservation_id:
                self.record.reservation_release_required = True
        elif to_state == WorkerState.FAILED_PRE_SUBMIT:
            raise IllegalWorkerTransition(
                self.record.state,
                to_state,
                "FAILED_PRE_SUBMIT from unknown/recovery requires proven_no_submit",
                event=WorkerEvent.RECONCILE,
            )
        if to_state == WorkerState.ALLOWANCE_RESERVED:
            if self.record.submit_attempted and not self.record.submit_never_left:
                raise IllegalWorkerTransition(
                    self.record.state,
                    to_state,
                    "cannot return to reserve after an uncertain submit",
                    event=WorkerEvent.RECONCILE,
                )
            if not self.record.reservation_id:
                raise IllegalWorkerTransition(
                    self.record.state,
                    to_state,
                    "cannot resume reserve without reservation_id",
                    event=WorkerEvent.RECONCILE,
                )
        self.record.error_class = None if to_state not in {
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.UNKNOWN_VENDOR_STATE,
        } else to_state.value
        self.record.recovery_reason = reason
        return self._move(
            to_state,
            WorkerEvent.RECONCILE,
            mode=TransitionMode.OPERATOR_RECONCILE,
        )

    def inherit_leader(self, leader: LiveWorkerRecord) -> LiveWorkerRecord:
        """Joiners copy a leader terminal/holding outcome. They never submit."""
        if self.record.state != WorkerState.JOINED:
            raise IllegalWorkerTransition(
                self.record.state,
                leader.state,
                "only JOINED records may inherit a leader",
                event=WorkerEvent.JOIN,
            )
        if leader.state in {WorkerState.SUBMITTING, WorkerState.SUBMITTED, WorkerState.ALLOWANCE_RESERVED}:
            self.record.recovery_reason = "leader still in flight"
            return self.snapshot()
        allowed = {
            WorkerState.CACHE_HIT,
            WorkerState.CONSUMED,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.RECOVERY_REQUIRED,
        }
        if leader.state not in allowed:
            raise IllegalWorkerTransition(
                self.record.state,
                leader.state,
                "joiner cannot inherit an in-progress leader state that implies local submit",
                event=WorkerEvent.JOIN,
            )
        if leader.state == WorkerState.CONSUMED:
            self.record.result_cached = True
        if leader.state == WorkerState.CACHE_HIT:
            self.record.cache_checked = True
        self.record.error_class = leader.error_class
        return self._move(leader.state, WorkerEvent.JOIN)

    def next_safe_action(self) -> RecoveryAction:
        return classify_restart(self.record).action

    def assert_cannot_resubmit(self) -> None:
        try:
            assert_no_blind_paid_retry(self.record, WorkerState.SUBMITTING)
        except IllegalWorkerTransition:
            return
        raise AssertionError("blind paid retry was not blocked")

    def _recheck_cache_hit(self) -> LiveWorkerRecord:
        self.record.cache_checked = True
        self.record.cache_rechecked_before_submit = True
        self.record.reservation_release_required = True
        return self._move(WorkerState.CACHE_HIT, WorkerEvent.RECHECK_CACHE_HIT)

    def _require_not_joined_submit(self) -> None:
        if self.record.state == WorkerState.JOINED:
            raise IllegalWorkerTransition(
                self.record.state,
                WorkerState.CACHE_HIT,
                "joined workers inherit; they do not drive cache/submit",
                event=WorkerEvent.CACHE_HIT,
            )

    def _move(
        self,
        to_state: WorkerState,
        event: WorkerEvent,
        *,
        mode: TransitionMode = TransitionMode.AUTOMATIC,
    ) -> LiveWorkerRecord:
        from_state = self.record.state
        if is_terminal(from_state):
            raise IllegalWorkerTransition(
                from_state,
                to_state,
                "terminal states are absorbing",
                event=event,
            )
        assert_no_blind_paid_retry(self.record, to_state)
        if from_state in NEVER_RESUBMIT_FROM and to_state in {
            WorkerState.SUBMITTING,
            WorkerState.SUBMITTED,
        }:
            raise IllegalWorkerTransition(
                from_state,
                to_state,
                "resubmit is forbidden",
                event=event,
            )
        if from_state == WorkerState.UNKNOWN_VENDOR_STATE and mode == TransitionMode.AUTOMATIC:
            if to_state != WorkerState.RECOVERY_REQUIRED:
                raise IllegalWorkerTransition(
                    from_state,
                    to_state,
                    "UNKNOWN_VENDOR_STATE may automatically move only to RECOVERY_REQUIRED",
                    event=event,
                )
        assert_legal_transition(from_state, to_state, mode=mode, event=event)
        self.record.state = to_state
        self.record.updated_at = _now()
        return self.snapshot()


def run_happy_path_cache_miss(
    *,
    job_id: str,
    fingerprint: str,
    reservation_id: str,
    activity_id: str,
) -> LiveWorkerRecord:
    """Pure in-process happy path. No vendor I/O."""
    machine = DurableWorkerMachine.create(job_id=job_id, fingerprint=fingerprint)
    machine.validate()
    machine.note_cache_miss()
    machine.reserve(reservation_id)
    machine.note_cache_miss()
    machine.begin_submit()
    machine.ack_submit(activity_id)
    machine.persist_activity_id(activity_id)
    machine.begin_processing()
    machine.receive_result()
    machine.normalize()
    machine.cache_result()
    machine.consume()
    return machine.snapshot()


def spend_risk_label(record: LiveWorkerRecord) -> SpendRisk:
    return record.spend_risk
