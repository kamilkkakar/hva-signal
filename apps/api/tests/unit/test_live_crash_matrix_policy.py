"""Crash recovery policy: no unknown→resubmit, no blind paid retry."""

from __future__ import annotations

import pytest

from app.domain.live_crash_matrix.policy import decide_recovery
from app.domain.live_crash_matrix.states import (
    DurableWorkerState,
    RecoveryAction,
)


def test_unknown_vendor_state_never_allows_submit() -> None:
    decision = decide_recovery(
        DurableWorkerState.UNKNOWN_VENDOR_STATE,
        vendor_activity_id=None,
        submit_attempted=True,
        cache_present=False,
        reservation_state="RESERVED",
    )
    assert decision.allow_vendor_submit is False
    assert decision.action == RecoveryAction.NO_AUTOMATIC_RESUBMIT
    assert decision.next_state == DurableWorkerState.UNKNOWN_VENDOR_STATE


@pytest.mark.parametrize("flag_name", ["force_resubmit", "automatic_paid_retry"])
def test_force_flags_cannot_resubmit_unknown(flag_name: str) -> None:
    decision = decide_recovery(
        DurableWorkerState.UNKNOWN_VENDOR_STATE,
        vendor_activity_id=None,
        submit_attempted=True,
        cache_present=False,
        reservation_state="RESERVED",
        **{flag_name: True},
    )
    assert decision.allow_vendor_submit is False
    assert decision.reason == "force_resubmit_rejected"


def test_submitting_without_activity_id_is_unknown() -> None:
    decision = decide_recovery(
        DurableWorkerState.SUBMITTING,
        vendor_activity_id=None,
        submit_attempted=True,
        cache_present=False,
        reservation_state="RESERVED",
    )
    assert decision.action == RecoveryAction.NO_AUTOMATIC_RESUBMIT
    assert decision.next_state == DurableWorkerState.UNKNOWN_VENDOR_STATE
    assert decision.allow_vendor_submit is False


def test_activity_id_resumes_poll_only() -> None:
    decision = decide_recovery(
        DurableWorkerState.ACTIVITY_ID_PERSISTED,
        vendor_activity_id="fake_abc",
        submit_attempted=True,
        cache_present=False,
        reservation_state="RESERVED",
    )
    assert decision.action == RecoveryAction.RESUME_POLL
    assert decision.allow_vendor_submit is False


def test_cached_before_consume_does_not_submit() -> None:
    decision = decide_recovery(
        DurableWorkerState.CACHED,
        vendor_activity_id="fake_abc",
        submit_attempted=True,
        cache_present=True,
        reservation_state="RESERVED",
    )
    assert decision.action == RecoveryAction.CONSUME_ONLY
    assert decision.allow_vendor_submit is False


def test_pre_reserve_may_continue_but_decision_does_not_submit_yet() -> None:
    decision = decide_recovery(
        DurableWorkerState.VALIDATED,
        vendor_activity_id=None,
        submit_attempted=False,
        cache_present=False,
        reservation_state=None,
    )
    assert decision.action == RecoveryAction.CONTINUE_FROM_CACHE_CHECK
    assert decision.allow_vendor_submit is False


def test_reserved_may_submit_once() -> None:
    decision = decide_recovery(
        DurableWorkerState.ALLOWANCE_RESERVED,
        vendor_activity_id=None,
        submit_attempted=False,
        cache_present=False,
        reservation_state="RESERVED",
    )
    assert decision.action == RecoveryAction.CONTINUE_TO_SUBMIT
    assert decision.allow_vendor_submit is True


def test_failed_post_submit_is_not_a_paid_retry() -> None:
    decision = decide_recovery(
        DurableWorkerState.FAILED_POST_SUBMIT,
        vendor_activity_id="fake_abc",
        submit_attempted=True,
        cache_present=False,
        reservation_state="CONSUMED",
    )
    assert decision.allow_vendor_submit is False
    assert decision.action == RecoveryAction.NO_AUTOMATIC_RESUBMIT
