"""J3/J4 durable live-worker state machine.

This is the acquisition worker SM. It is not public JobStatus, not the
two-signal section lifecycle, and not a JobStore. J0/J1/J2 persist jobs;
this module owns legal worker transitions and spend-risk classification.

The public 17-state type is LIVE-D's DurableLivePhase. WorkerState is an
alias — LIVE-C does not own a forked enum. C owns transitions only.

No vendor I/O. No FortyGuard. Hosted live remains a caller policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.activity_reconciliation import DurableLivePhase

# Canonical phase vocabulary. Do not define a second 17-state enum.
WorkerState = DurableLivePhase


class WorkerEvent(str, Enum):
    VALIDATE = "VALIDATE"
    CACHE_HIT = "CACHE_HIT"
    JOIN = "JOIN"
    RESERVE = "RESERVE"
    RECHECK_CACHE_HIT = "RECHECK_CACHE_HIT"
    BEGIN_SUBMIT = "BEGIN_SUBMIT"
    ACK_SUBMIT = "ACK_SUBMIT"
    PERSIST_ACTIVITY_ID = "PERSIST_ACTIVITY_ID"
    BEGIN_PROCESSING = "BEGIN_PROCESSING"
    RECEIVE_RESULT = "RECEIVE_RESULT"
    NORMALIZE = "NORMALIZE"
    CACHE = "CACHE"
    CONSUME = "CONSUME"
    FAIL_PRE_SUBMIT = "FAIL_PRE_SUBMIT"
    FAIL_POST_SUBMIT = "FAIL_POST_SUBMIT"
    MARK_UNKNOWN = "MARK_UNKNOWN"
    REQUIRE_RECOVERY = "REQUIRE_RECOVERY"
    APPLY_RESTART = "APPLY_RESTART"
    RECONCILE = "RECONCILE"


class SpendRisk(str, Enum):
    """Vendor spend exposure. Distinct from reservation occupancy."""

    NONE = "NONE"
    RESERVED = "RESERVED"
    UNKNOWN = "UNKNOWN"
    POST_SUBMIT = "POST_SUBMIT"


class RecoveryAction(str, Enum):
    """Safe next step. RESUBMIT is intentionally absent."""

    NONE = "NONE"
    CONTINUE_PRE_SPEND = "CONTINUE_PRE_SPEND"
    RELEASE_RESERVATION = "RELEASE_RESERVATION"
    CACHE_RECHECK_THEN_FIRST_SUBMIT = "CACHE_RECHECK_THEN_FIRST_SUBMIT"
    WAIT_FOR_LEADER = "WAIT_FOR_LEADER"
    RESUME_VENDOR_POLL = "RESUME_VENDOR_POLL"
    CACHE_WITHOUT_RESUBMIT = "CACHE_WITHOUT_RESUBMIT"
    CONSUME_WITHOUT_RESUBMIT = "CONSUME_WITHOUT_RESUBMIT"
    OPERATOR_RECONCILE = "OPERATOR_RECONCILE"
    TERMINAL = "TERMINAL"


class TransitionMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    OPERATOR_RECONCILE = "OPERATOR_RECONCILE"


class IllegalWorkerTransition(ValueError):
    """Rejected worker transition. Never silently coerced."""

    def __init__(
        self,
        from_state: WorkerState,
        to_state: WorkerState,
        reason: str,
        *,
        event: WorkerEvent | None = None,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        self.event = event
        suffix = f" via {event.value}" if event is not None else ""
        super().__init__(
            f"illegal worker transition {from_state.value} -> {to_state.value}{suffix}: {reason}"
        )


REQUIRED_STATES: tuple[WorkerState, ...] = tuple(WorkerState)

TERMINAL_SUCCESS = frozenset({WorkerState.CACHE_HIT, WorkerState.CONSUMED})
TERMINAL_FAILURE = frozenset(
    {WorkerState.FAILED_PRE_SUBMIT, WorkerState.FAILED_POST_SUBMIT}
)
TERMINAL_STATES = TERMINAL_SUCCESS | TERMINAL_FAILURE

# Automatic worker edges. UNKNOWN_VENDOR_STATE may only advance to RECOVERY_REQUIRED.
AUTOMATIC_TRANSITIONS: dict[WorkerState, frozenset[WorkerState]] = {
    WorkerState.REQUESTED: frozenset(
        {WorkerState.VALIDATED, WorkerState.FAILED_PRE_SUBMIT}
    ),
    WorkerState.VALIDATED: frozenset(
        {
            WorkerState.CACHE_HIT,
            WorkerState.JOINED,
            WorkerState.ALLOWANCE_RESERVED,
            WorkerState.FAILED_PRE_SUBMIT,
        }
    ),
    WorkerState.CACHE_HIT: frozenset(),
    WorkerState.JOINED: frozenset(
        {
            WorkerState.CACHE_HIT,
            WorkerState.CONSUMED,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.ALLOWANCE_RESERVED: frozenset(
        {
            WorkerState.SUBMITTING,
            WorkerState.CACHE_HIT,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.SUBMITTING: frozenset(
        {
            WorkerState.SUBMITTED,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.SUBMITTED: frozenset(
        {
            WorkerState.ACTIVITY_ID_PERSISTED,
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.RECOVERY_REQUIRED,
            WorkerState.FAILED_POST_SUBMIT,
        }
    ),
    WorkerState.ACTIVITY_ID_PERSISTED: frozenset(
        {
            WorkerState.PROCESSING,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.PROCESSING: frozenset(
        {
            WorkerState.RESULT_RECEIVED,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.RESULT_RECEIVED: frozenset(
        {
            WorkerState.NORMALIZED,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.NORMALIZED: frozenset(
        {
            WorkerState.CACHED,
            WorkerState.FAILED_POST_SUBMIT,
            WorkerState.RECOVERY_REQUIRED,
        }
    ),
    WorkerState.CACHED: frozenset(
        {WorkerState.CONSUMED, WorkerState.RECOVERY_REQUIRED}
    ),
    WorkerState.CONSUMED: frozenset(),
    WorkerState.FAILED_PRE_SUBMIT: frozenset(),
    WorkerState.FAILED_POST_SUBMIT: frozenset(),
    WorkerState.UNKNOWN_VENDOR_STATE: frozenset({WorkerState.RECOVERY_REQUIRED}),
    WorkerState.RECOVERY_REQUIRED: frozenset(
        {
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.ALLOWANCE_RESERVED,
            WorkerState.CACHE_HIT,
            WorkerState.CACHED,
            WorkerState.CONSUMED,
            WorkerState.ACTIVITY_ID_PERSISTED,
            WorkerState.PROCESSING,
            WorkerState.RESULT_RECEIVED,
            WorkerState.NORMALIZED,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.FAILED_POST_SUBMIT,
        }
    ),
}

# Operator-safe reconcile may resolve UNKNOWN without resubmitting.
OPERATOR_RECONCILE_TRANSITIONS: dict[WorkerState, frozenset[WorkerState]] = {
    WorkerState.UNKNOWN_VENDOR_STATE: frozenset(
        {
            WorkerState.RECOVERY_REQUIRED,
            WorkerState.ACTIVITY_ID_PERSISTED,
            WorkerState.PROCESSING,
            WorkerState.RESULT_RECEIVED,
            WorkerState.NORMALIZED,
            WorkerState.CACHED,
            WorkerState.CONSUMED,
            WorkerState.CACHE_HIT,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.FAILED_POST_SUBMIT,
        }
    ),
    WorkerState.RECOVERY_REQUIRED: frozenset(
        {
            WorkerState.UNKNOWN_VENDOR_STATE,
            WorkerState.ALLOWANCE_RESERVED,
            WorkerState.ACTIVITY_ID_PERSISTED,
            WorkerState.PROCESSING,
            WorkerState.RESULT_RECEIVED,
            WorkerState.NORMALIZED,
            WorkerState.CACHED,
            WorkerState.CONSUMED,
            WorkerState.CACHE_HIT,
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.FAILED_POST_SUBMIT,
        }
    ),
}

RESUBMIT_STATES = frozenset(
    {
        WorkerState.SUBMITTING,
        WorkerState.SUBMITTED,
    }
)

NEVER_RESUBMIT_FROM = frozenset(
    {
        WorkerState.UNKNOWN_VENDOR_STATE,
        WorkerState.FAILED_POST_SUBMIT,
        WorkerState.CONSUMED,
        WorkerState.CACHE_HIT,
        WorkerState.JOINED,
        WorkerState.ACTIVITY_ID_PERSISTED,
        WorkerState.PROCESSING,
        WorkerState.RESULT_RECEIVED,
        WorkerState.NORMALIZED,
        WorkerState.CACHED,
        WorkerState.SUBMITTED,
    }
)


def is_terminal(state: WorkerState) -> bool:
    return state in TERMINAL_STATES


def spend_risk_for_state(state: WorkerState) -> SpendRisk:
    if state in {
        WorkerState.REQUESTED,
        WorkerState.VALIDATED,
        WorkerState.CACHE_HIT,
        WorkerState.JOINED,
        WorkerState.FAILED_PRE_SUBMIT,
    }:
        return SpendRisk.NONE
    if state == WorkerState.ALLOWANCE_RESERVED:
        return SpendRisk.RESERVED
    if state in {WorkerState.SUBMITTING, WorkerState.UNKNOWN_VENDOR_STATE}:
        return SpendRisk.UNKNOWN
    return SpendRisk.POST_SUBMIT


def legal_targets(
    from_state: WorkerState, *, mode: TransitionMode = TransitionMode.AUTOMATIC
) -> frozenset[WorkerState]:
    allowed = set(AUTOMATIC_TRANSITIONS[from_state])
    if mode == TransitionMode.OPERATOR_RECONCILE:
        allowed.update(OPERATOR_RECONCILE_TRANSITIONS.get(from_state, frozenset()))
    return frozenset(allowed)


def is_legal_transition(
    from_state: WorkerState,
    to_state: WorkerState,
    *,
    mode: TransitionMode = TransitionMode.AUTOMATIC,
) -> bool:
    if from_state == to_state:
        return False
    return to_state in legal_targets(from_state, mode=mode)


def assert_legal_transition(
    from_state: WorkerState,
    to_state: WorkerState,
    *,
    mode: TransitionMode = TransitionMode.AUTOMATIC,
    event: WorkerEvent | None = None,
    reason: str | None = None,
) -> None:
    if is_legal_transition(from_state, to_state, mode=mode):
        if from_state in NEVER_RESUBMIT_FROM and to_state in RESUBMIT_STATES:
            raise IllegalWorkerTransition(
                from_state,
                to_state,
                "resubmit is forbidden from this state",
                event=event,
            )
        return
    raise IllegalWorkerTransition(
        from_state,
        to_state,
        reason or "edge is not in the legal transition table",
        event=event,
    )


def transition_table_rows() -> list[tuple[str, str, str, str]]:
    """(from, to, mode, spend_risk_after) for documentation and tests."""
    rows: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for src, dests in AUTOMATIC_TRANSITIONS.items():
        for dest in sorted(dests, key=lambda s: s.value):
            key = (src.value, dest.value, TransitionMode.AUTOMATIC.value)
            seen.add(key)
            rows.append(
                (
                    src.value,
                    dest.value,
                    TransitionMode.AUTOMATIC.value,
                    spend_risk_for_state(dest).value,
                )
            )
    for src, dests in OPERATOR_RECONCILE_TRANSITIONS.items():
        for dest in sorted(dests, key=lambda s: s.value):
            key = (src.value, dest.value, TransitionMode.OPERATOR_RECONCILE.value)
            if (src.value, dest.value, TransitionMode.AUTOMATIC.value) in seen:
                continue
            rows.append(
                (
                    src.value,
                    dest.value,
                    TransitionMode.OPERATOR_RECONCILE.value,
                    spend_risk_for_state(dest).value,
                )
            )
    return rows


class LiveWorkerRecord(BaseModel):
    """Durable worker facts. JobStore identity stays in LIVE-A."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    fingerprint: str
    state: WorkerState = WorkerState.REQUESTED
    reservation_id: str | None = None
    activity_id: str | None = None
    activity_id_durable: bool = False
    cache_checked: bool = False
    cache_rechecked_before_submit: bool = False
    submit_attempted: bool = False
    submit_never_left: bool = False
    submitted_to_vendor: bool = False
    result_cached: bool = False
    joined_job_id: str | None = None
    error_class: str | None = None
    recovery_reason: str | None = None
    reservation_release_required: bool = False
    consume_required: bool = False
    paid_retry_blocked: Literal[True] = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def spend_risk(self) -> SpendRisk:
        if self.state in {
            WorkerState.FAILED_PRE_SUBMIT,
            WorkerState.CACHE_HIT,
            WorkerState.JOINED,
            WorkerState.REQUESTED,
            WorkerState.VALIDATED,
        }:
            return SpendRisk.NONE
        if self.submitted_to_vendor or self.activity_id_durable:
            return SpendRisk.POST_SUBMIT
        if self.submit_attempted and not self.submit_never_left:
            return SpendRisk.UNKNOWN
        if self.state == WorkerState.ALLOWANCE_RESERVED:
            return SpendRisk.RESERVED
        return spend_risk_for_state(self.state)


class RestartDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_state: WorkerState
    action: RecoveryAction
    reason: str
    may_first_submit: bool = False
    may_resubmit: Literal[False] = False


def classify_restart(record: LiveWorkerRecord) -> RestartDisposition:
    """Map a persisted record to a safe restart state. Never resubmits."""
    state = record.state
    if state in TERMINAL_STATES:
        return RestartDisposition(
            next_state=state,
            action=RecoveryAction.TERMINAL,
            reason="terminal state is absorbing",
        )
    if state == WorkerState.JOINED:
        return RestartDisposition(
            next_state=WorkerState.JOINED,
            action=RecoveryAction.WAIT_FOR_LEADER,
            reason="joiner must inherit the leader; it must not submit",
        )
    if record.activity_id_durable and record.activity_id:
        if state == WorkerState.CACHED or record.result_cached:
            return RestartDisposition(
                next_state=WorkerState.RECOVERY_REQUIRED,
                action=RecoveryAction.CONSUME_WITHOUT_RESUBMIT,
                reason="result is cached; consume allowance without a second submit",
            )
        if state in {
            WorkerState.RESULT_RECEIVED,
            WorkerState.NORMALIZED,
        }:
            return RestartDisposition(
                next_state=WorkerState.RECOVERY_REQUIRED,
                action=RecoveryAction.CACHE_WITHOUT_RESUBMIT,
                reason="vendor result exists; cache it without resubmit",
            )
        return RestartDisposition(
            next_state=WorkerState.RECOVERY_REQUIRED,
            action=RecoveryAction.RESUME_VENDOR_POLL,
            reason="activity_id is durable; resume status poll, never resubmit",
        )
    if record.submit_attempted and not record.submit_never_left:
        return RestartDisposition(
            next_state=WorkerState.UNKNOWN_VENDOR_STATE,
            action=RecoveryAction.OPERATOR_RECONCILE,
            reason="submit may have reached the vendor; activity_id is not durable",
        )
    if state == WorkerState.SUBMITTED and not record.activity_id_durable:
        return RestartDisposition(
            next_state=WorkerState.UNKNOWN_VENDOR_STATE,
            action=RecoveryAction.OPERATOR_RECONCILE,
            reason="SUBMITTED without durable activity_id is not a durable submit",
        )
    if state in {WorkerState.UNKNOWN_VENDOR_STATE, WorkerState.RECOVERY_REQUIRED}:
        if (
            state == WorkerState.RECOVERY_REQUIRED
            and record.reservation_id is not None
            and not record.submit_attempted
        ):
            return RestartDisposition(
                next_state=WorkerState.ALLOWANCE_RESERVED,
                action=RecoveryAction.CACHE_RECHECK_THEN_FIRST_SUBMIT,
                reason="recovery after reserve with no submit attempt; first submit is still allowed after cache recheck",
                may_first_submit=True,
            )
        action = (
            RecoveryAction.OPERATOR_RECONCILE
            if state == WorkerState.UNKNOWN_VENDOR_STATE
            else RecoveryAction.RESUME_VENDOR_POLL
            if record.activity_id_durable
            else RecoveryAction.OPERATOR_RECONCILE
        )
        return RestartDisposition(
            next_state=state,
            action=action,
            reason="holding state; operator-safe reconcile only; never resubmit",
        )
    if state == WorkerState.ALLOWANCE_RESERVED or (
        record.reservation_id is not None and not record.submit_attempted
    ):
        return RestartDisposition(
            next_state=WorkerState.ALLOWANCE_RESERVED,
            action=RecoveryAction.CACHE_RECHECK_THEN_FIRST_SUBMIT,
            reason="reservation exists and submit was not attempted; first submit is still allowed after cache recheck",
            may_first_submit=True,
        )
    if state in {WorkerState.REQUESTED, WorkerState.VALIDATED}:
        return RestartDisposition(
            next_state=state,
            action=RecoveryAction.CONTINUE_PRE_SPEND,
            reason="pre-spend; cache and dedupe before any reserve",
        )
    return RestartDisposition(
        next_state=WorkerState.RECOVERY_REQUIRED,
        action=RecoveryAction.OPERATOR_RECONCILE,
        reason="unclassified in-flight worker record; do not resubmit",
    )


def next_safe_action(record: LiveWorkerRecord) -> RecoveryAction:
    return classify_restart(record).action


def assert_no_blind_paid_retry(record: LiveWorkerRecord, to_state: WorkerState) -> None:
    """Block a new submit attempt. ACK of the in-flight submit is not a retry."""
    if to_state != WorkerState.SUBMITTING:
        return
    if record.state == WorkerState.UNKNOWN_VENDOR_STATE:
        raise IllegalWorkerTransition(
            record.state,
            to_state,
            "UNKNOWN_VENDOR_STATE must never resubmit",
        )
    if record.state in NEVER_RESUBMIT_FROM:
        raise IllegalWorkerTransition(
            record.state,
            to_state,
            "blind paid retry is forbidden from this state",
        )
    if record.submit_attempted and not record.submit_never_left:
        raise IllegalWorkerTransition(
            record.state,
            to_state,
            "blind paid retry is forbidden after a submit attempt",
        )
