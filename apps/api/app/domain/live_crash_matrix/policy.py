"""Crash recovery policy. Fail closed. No blind paid retry.

UNKNOWN_VENDOR_STATE and RECOVERY_REQUIRED never become a submit.
force_resubmit / automatic_paid_retry flags are rejected, not honored.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.live_crash_matrix.states import (
    DurableWorkerState,
    RecoveryAction,
    SpendRisk,
)

_UNKNOWN_LIKE = frozenset(
    {
        DurableWorkerState.UNKNOWN_VENDOR_STATE,
        DurableWorkerState.RECOVERY_REQUIRED,
    }
)

_POST_SUBMIT_NO_HANDLE = frozenset(
    {
        DurableWorkerState.SUBMITTING,
        DurableWorkerState.SUBMITTED,
    }
)

_RESUME_POLL_STATES = frozenset(
    {
        DurableWorkerState.ACTIVITY_ID_PERSISTED,
        DurableWorkerState.PROCESSING,
        DurableWorkerState.RESULT_RECEIVED,
    }
)


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RecoveryAction
    next_state: DurableWorkerState
    spend_risk: SpendRisk
    allow_vendor_submit: Literal[False] | bool
    reason: str


def decide_recovery(
    state: DurableWorkerState,
    *,
    vendor_activity_id: str | None,
    submit_attempted: bool,
    cache_present: bool,
    reservation_state: str | None,
    force_resubmit: bool = False,
    automatic_paid_retry: bool = False,
) -> RecoveryDecision:
    """What a restarted worker may do. Submit is allowed only pre-vendor."""

    if force_resubmit or automatic_paid_retry:
        if state in _UNKNOWN_LIKE or (
            submit_attempted and vendor_activity_id is None
        ):
            return RecoveryDecision(
                action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
                next_state=DurableWorkerState.UNKNOWN_VENDOR_STATE
                if state == DurableWorkerState.UNKNOWN_VENDOR_STATE
                else DurableWorkerState.RECOVERY_REQUIRED,
                spend_risk=SpendRisk.UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED
                if vendor_activity_id is None
                else SpendRisk.VENDOR_IN_FLIGHT,
                allow_vendor_submit=False,
                reason="force_resubmit_rejected",
            )

    if cache_present and state in {
        DurableWorkerState.CACHED,
        DurableWorkerState.CONSUMED,
        DurableWorkerState.CACHE_HIT,
    }:
        if (
            state == DurableWorkerState.CACHED
            and reservation_state == "RESERVED"
        ):
            return RecoveryDecision(
                action=RecoveryAction.CONSUME_ONLY,
                next_state=DurableWorkerState.CONSUMED,
                spend_risk=SpendRisk.CACHE_WITHOUT_CONSUME,
                allow_vendor_submit=False,
                reason="cache_present_consume_reservation",
            )
        return RecoveryDecision(
            action=RecoveryAction.REUSE_CACHE,
            next_state=DurableWorkerState.CACHE_HIT
            if state != DurableWorkerState.CONSUMED
            else DurableWorkerState.CONSUMED,
            spend_risk=SpendRisk.ALREADY_SPENT
            if reservation_state == "CONSUMED"
            else SpendRisk.NONE,
            allow_vendor_submit=False,
            reason="cache_hit_no_submit",
        )

    if state == DurableWorkerState.UNKNOWN_VENDOR_STATE:
        return RecoveryDecision(
            action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
            next_state=DurableWorkerState.UNKNOWN_VENDOR_STATE,
            spend_risk=SpendRisk.UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED
            if vendor_activity_id is None
            else SpendRisk.VENDOR_ACCEPTED_HANDLE_LOST,
            allow_vendor_submit=False,
            reason="unknown_vendor_state_never_auto_resubmit",
        )

    if state == DurableWorkerState.RECOVERY_REQUIRED:
        return RecoveryDecision(
            action=RecoveryAction.OPERATOR_RECONCILE,
            next_state=DurableWorkerState.RECOVERY_REQUIRED,
            spend_risk=SpendRisk.UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED,
            allow_vendor_submit=False,
            reason="operator_reconcile_only",
        )

    if state == DurableWorkerState.FAILED_POST_SUBMIT:
        return RecoveryDecision(
            action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
            next_state=DurableWorkerState.FAILED_POST_SUBMIT,
            spend_risk=SpendRisk.ALREADY_SPENT,
            allow_vendor_submit=False,
            reason="failed_post_submit_no_paid_retry",
        )

    if state == DurableWorkerState.FAILED_PRE_SUBMIT:
        return RecoveryDecision(
            action=RecoveryAction.RELEASE_AND_MAY_RETRY_PRE_SUBMIT,
            next_state=DurableWorkerState.VALIDATED,
            spend_risk=SpendRisk.NONE,
            allow_vendor_submit=False,
            reason="pre_submit_failure_no_vendor_contact",
        )

    if state in {DurableWorkerState.REQUESTED, DurableWorkerState.VALIDATED}:
        return RecoveryDecision(
            action=RecoveryAction.CONTINUE_FROM_CACHE_CHECK,
            next_state=DurableWorkerState.VALIDATED,
            spend_risk=SpendRisk.NONE,
            allow_vendor_submit=False,
            reason="pre_reserve_restart",
        )

    if state == DurableWorkerState.ALLOWANCE_RESERVED:
        return RecoveryDecision(
            action=RecoveryAction.CONTINUE_TO_SUBMIT,
            next_state=DurableWorkerState.ALLOWANCE_RESERVED,
            spend_risk=SpendRisk.RESERVATION_HELD,
            allow_vendor_submit=True,
            reason="reserved_no_vendor_contact_yet",
        )

    if state in _POST_SUBMIT_NO_HANDLE and vendor_activity_id is None:
        return RecoveryDecision(
            action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
            next_state=DurableWorkerState.UNKNOWN_VENDOR_STATE,
            spend_risk=SpendRisk.UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED
            if state == DurableWorkerState.SUBMITTING
            else SpendRisk.VENDOR_ACCEPTED_HANDLE_LOST,
            allow_vendor_submit=False,
            reason="submit_without_activity_id_is_unknown",
        )

    if vendor_activity_id and state in _RESUME_POLL_STATES | {
        DurableWorkerState.SUBMITTED,
    }:
        return RecoveryDecision(
            action=RecoveryAction.RESUME_POLL,
            next_state=DurableWorkerState.PROCESSING,
            spend_risk=SpendRisk.VENDOR_IN_FLIGHT,
            allow_vendor_submit=False,
            reason="activity_id_known_resume_poll_only",
        )

    if state == DurableWorkerState.NORMALIZED:
        return RecoveryDecision(
            action=RecoveryAction.CACHE_THEN_CONSUME,
            next_state=DurableWorkerState.CONSUMED,
            spend_risk=SpendRisk.RESULT_UNPROTECTED,
            allow_vendor_submit=False,
            reason="result_present_cache_then_consume",
        )

    if state == DurableWorkerState.CACHED:
        return RecoveryDecision(
            action=RecoveryAction.CONSUME_ONLY,
            next_state=DurableWorkerState.CONSUMED,
            spend_risk=SpendRisk.CACHE_WITHOUT_CONSUME,
            allow_vendor_submit=False,
            reason="cached_consume_reservation",
        )

    if state == DurableWorkerState.CONSUMED:
        return RecoveryDecision(
            action=RecoveryAction.REUSE_CACHE,
            next_state=DurableWorkerState.CONSUMED,
            spend_risk=SpendRisk.ALREADY_SPENT,
            allow_vendor_submit=False,
            reason="already_consumed",
        )

    if state == DurableWorkerState.JOINED:
        return RecoveryDecision(
            action=RecoveryAction.JOIN_IN_FLIGHT,
            next_state=DurableWorkerState.JOINED,
            spend_risk=SpendRisk.RESERVATION_HELD,
            allow_vendor_submit=False,
            reason="joined_existing_job",
        )

    if state == DurableWorkerState.CACHE_HIT:
        return RecoveryDecision(
            action=RecoveryAction.REUSE_CACHE,
            next_state=DurableWorkerState.CACHE_HIT,
            spend_risk=SpendRisk.NONE,
            allow_vendor_submit=False,
            reason="cache_hit",
        )

    return RecoveryDecision(
        action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
        next_state=DurableWorkerState.RECOVERY_REQUIRED,
        spend_risk=SpendRisk.UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED,
        allow_vendor_submit=False,
        reason="fail_closed_unrecognized_state",
    )
