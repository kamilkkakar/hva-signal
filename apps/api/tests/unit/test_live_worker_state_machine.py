"""J3/J4 durable worker state machine. No vendor I/O."""

from __future__ import annotations

import pytest

from app.domain.activity_reconciliation import DurableLivePhase
from app.domain.live_worker_state import (
    AUTOMATIC_TRANSITIONS,
    REQUIRED_STATES,
    RecoveryAction,
    SpendRisk,
    TransitionMode,
    WorkerState,
    IllegalWorkerTransition,
    classify_restart,
    is_legal_transition,
    spend_risk_for_state,
    transition_table_rows,
)
from app.services.live_worker_machine import (
    DurableWorkerMachine,
    run_happy_path_cache_miss,
)


REQUIRED_STATE_NAMES = (
    "REQUESTED",
    "VALIDATED",
    "CACHE_HIT",
    "JOINED",
    "ALLOWANCE_RESERVED",
    "SUBMITTING",
    "SUBMITTED",
    "ACTIVITY_ID_PERSISTED",
    "PROCESSING",
    "RESULT_RECEIVED",
    "NORMALIZED",
    "CACHED",
    "CONSUMED",
    "FAILED_PRE_SUBMIT",
    "FAILED_POST_SUBMIT",
    "UNKNOWN_VENDOR_STATE",
    "RECOVERY_REQUIRED",
)


def _machine() -> DurableWorkerMachine:
    return DurableWorkerMachine.create(job_id="job_live_c", fingerprint="fp-1")


def _reserved() -> DurableWorkerMachine:
    machine = _machine()
    machine.validate()
    machine.note_cache_miss()
    machine.reserve("res-1")
    return machine


def _ready_to_submit() -> DurableWorkerMachine:
    machine = _reserved()
    machine.note_cache_miss()
    return machine


def _durable_processing() -> DurableWorkerMachine:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit("act-1")
    machine.persist_activity_id("act-1")
    machine.begin_processing()
    return machine


def test_required_states_are_exact() -> None:
    assert tuple(state.value for state in REQUIRED_STATES) == REQUIRED_STATE_NAMES
    assert set(AUTOMATIC_TRANSITIONS) == set(WorkerState)
    assert set(WorkerState) == {WorkerState[name] for name in REQUIRED_STATE_NAMES}


def test_worker_state_is_durable_live_phase_alias() -> None:
    """LEAD-LIVE: no forked 17-state enum. WorkerState is DurableLivePhase."""
    assert WorkerState is DurableLivePhase
    assert [member.name for member in WorkerState] == list(REQUIRED_STATE_NAMES)
    assert [member.value for member in DurableLivePhase] == list(REQUIRED_STATE_NAMES)
    assert set(WorkerState) == set(DurableLivePhase)
    assert WorkerState.UNKNOWN_VENDOR_STATE is DurableLivePhase.UNKNOWN_VENDOR_STATE
    assert WorkerState.RECOVERY_REQUIRED is DurableLivePhase.RECOVERY_REQUIRED


def test_unknown_automatic_edge_is_only_recovery() -> None:
    targets = AUTOMATIC_TRANSITIONS[WorkerState.UNKNOWN_VENDOR_STATE]
    assert targets == frozenset({WorkerState.RECOVERY_REQUIRED})
    for dest in WorkerState:
        automatic = is_legal_transition(
            WorkerState.UNKNOWN_VENDOR_STATE, dest, mode=TransitionMode.AUTOMATIC
        )
        assert automatic is (dest == WorkerState.RECOVERY_REQUIRED)


def test_unknown_cannot_resubmit_in_table() -> None:
    for mode in TransitionMode:
        assert not is_legal_transition(
            WorkerState.UNKNOWN_VENDOR_STATE, WorkerState.SUBMITTING, mode=mode
        )
        assert not is_legal_transition(
            WorkerState.UNKNOWN_VENDOR_STATE, WorkerState.SUBMITTED, mode=mode
        )
        assert not is_legal_transition(
            WorkerState.FAILED_POST_SUBMIT, WorkerState.SUBMITTING, mode=mode
        )


def test_happy_path_cache_miss_reaches_consumed() -> None:
    record = run_happy_path_cache_miss(
        job_id="job_1",
        fingerprint="fp-happy",
        reservation_id="res-1",
        activity_id="act-1",
    )
    assert record.state is WorkerState.CONSUMED
    assert record.activity_id == "act-1"
    assert record.activity_id_durable is True
    assert record.result_cached is True
    assert record.spend_risk is SpendRisk.POST_SUBMIT
    assert record.paid_retry_blocked is True


def test_cache_hit_never_reserves_or_submits() -> None:
    machine = _machine()
    machine.validate()
    machine.note_cache_hit()
    assert machine.record.state is WorkerState.CACHE_HIT
    assert machine.record.spend_risk is SpendRisk.NONE
    with pytest.raises(IllegalWorkerTransition, match="CACHE_HIT must not reserve"):
        machine.reserve("res-1")
    with pytest.raises(IllegalWorkerTransition, match="reserve before submit"):
        machine.begin_submit()


def test_cache_and_dedupe_before_spend() -> None:
    machine = _machine()
    machine.validate()
    with pytest.raises(IllegalWorkerTransition, match="cache/dedupe must run before"):
        machine.reserve("res-1")
    machine.note_cache_miss()
    machine.reserve("res-1")
    assert machine.record.state is WorkerState.ALLOWANCE_RESERVED
    assert machine.record.spend_risk is SpendRisk.RESERVED


def test_join_skips_reserve_and_submit() -> None:
    machine = _machine()
    machine.validate()
    machine.join("job_leader")
    assert machine.record.state is WorkerState.JOINED
    assert machine.record.spend_risk is SpendRisk.NONE
    with pytest.raises(IllegalWorkerTransition, match="must not reserve"):
        machine.reserve("res-1")
    with pytest.raises(IllegalWorkerTransition, match="reserve before submit"):
        machine.begin_submit()


def test_joiner_inherits_leader_consumed_not_submit() -> None:
    leader = run_happy_path_cache_miss(
        job_id="job_leader",
        fingerprint="fp-shared",
        reservation_id="res-1",
        activity_id="act-1",
    )
    joiner = DurableWorkerMachine.create(job_id="job_join", fingerprint="fp-shared")
    joiner.validate()
    joiner.join("job_leader")
    joiner.inherit_leader(leader)
    assert joiner.record.state is WorkerState.CONSUMED
    assert joiner.record.submit_attempted is False


def test_reserve_before_submit_and_recheck() -> None:
    machine = _reserved()
    with pytest.raises(IllegalWorkerTransition, match="rechecked immediately before submit"):
        machine.begin_submit()
    machine.note_cache_miss()
    machine.begin_submit()
    assert machine.record.state is WorkerState.SUBMITTING
    assert machine.record.submit_attempted is True
    assert machine.record.spend_risk is SpendRisk.UNKNOWN


def test_recheck_cache_hit_releases_reservation_without_submit() -> None:
    machine = _reserved()
    machine.note_cache_hit()
    assert machine.record.state is WorkerState.CACHE_HIT
    assert machine.record.reservation_release_required is True
    assert machine.record.submit_attempted is False
    assert machine.record.spend_risk is SpendRisk.NONE


def test_submit_is_not_durable_until_activity_id_persisted() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit("act-mem")
    assert machine.record.state is WorkerState.SUBMITTED
    assert machine.record.activity_id == "act-mem"
    assert machine.record.activity_id_durable is False
    with pytest.raises(IllegalWorkerTransition, match="durable activity_id"):
        machine.begin_processing()
    machine.persist_activity_id("act-mem")
    assert machine.record.state is WorkerState.ACTIVITY_ID_PERSISTED
    assert machine.record.activity_id_durable is True
    machine.begin_processing()
    assert machine.record.state is WorkerState.PROCESSING


def test_persist_requires_activity_id() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit()
    with pytest.raises(IllegalWorkerTransition, match="activity_id is required"):
        machine.persist_activity_id("")


def test_consume_requires_cache() -> None:
    machine = _durable_processing()
    machine.receive_result()
    machine.normalize()
    with pytest.raises(IllegalWorkerTransition, match="cache the result before consuming"):
        machine.consume()
    machine.cache_result()
    machine.consume()
    assert machine.record.state is WorkerState.CONSUMED


def test_failed_pre_and_post_submit_are_distinct() -> None:
    pre = _reserved()
    pre.fail_pre_submit("allowance expired")
    assert pre.record.state is WorkerState.FAILED_PRE_SUBMIT
    assert pre.record.spend_risk is SpendRisk.NONE
    assert pre.record.reservation_release_required is True
    assert spend_risk_for_state(WorkerState.FAILED_PRE_SUBMIT) is SpendRisk.NONE

    post = _ready_to_submit()
    post.begin_submit()
    post.ack_submit("act-1")
    post.fail_post_submit("vendor rejected after accept")
    assert post.record.state is WorkerState.FAILED_POST_SUBMIT
    assert post.record.spend_risk is SpendRisk.POST_SUBMIT
    assert spend_risk_for_state(WorkerState.FAILED_POST_SUBMIT) is SpendRisk.POST_SUBMIT
    assert pre.record.error_class != post.record.error_class


def test_cannot_label_pre_submit_after_vendor_ack() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit("act-1")
    with pytest.raises(IllegalWorkerTransition, match="FAILED_POST_SUBMIT"):
        machine.fail_pre_submit("too late")


def test_submitting_without_never_left_proof_is_unknown_not_pre_fail() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    with pytest.raises(IllegalWorkerTransition, match="UNKNOWN_VENDOR_STATE"):
        machine.fail_pre_submit("timeout")
    machine.mark_unknown("submit timeout")
    assert machine.record.state is WorkerState.UNKNOWN_VENDOR_STATE
    assert machine.record.spend_risk is SpendRisk.UNKNOWN


def test_submitting_never_left_may_fail_pre() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.fail_pre_submit("connection refused before bytes left", submit_never_left=True)
    assert machine.record.state is WorkerState.FAILED_PRE_SUBMIT
    assert machine.record.spend_risk is SpendRisk.NONE


def test_unknown_never_automatically_resubmits() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.mark_unknown("lost activity_id")
    with pytest.raises(IllegalWorkerTransition, match="never resubmit|forbidden|reserve before"):
        machine.begin_submit()
    with pytest.raises(IllegalWorkerTransition, match="never resubmit|reconcile"):
        machine.reconcile(WorkerState.SUBMITTING, reason="please retry")
    machine.require_recovery("operator queue")
    assert machine.record.state is WorkerState.RECOVERY_REQUIRED
    with pytest.raises(IllegalWorkerTransition, match="never resubmit"):
        machine.reconcile(WorkerState.SUBMITTED, reason="forge submit")


def test_operator_reconcile_can_resume_poll_when_activity_id_found() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit()
    machine.mark_unknown("crash before persist")
    machine.reconcile(
        WorkerState.ACTIVITY_ID_PERSISTED,
        reason="operator found activity on vendor",
        activity_id="act-recovered",
    )
    assert machine.record.state is WorkerState.ACTIVITY_ID_PERSISTED
    assert machine.record.activity_id == "act-recovered"
    assert machine.record.activity_id_durable is True
    machine.begin_processing()
    assert machine.record.submit_attempted is True
    assert machine.next_safe_action() is RecoveryAction.RESUME_VENDOR_POLL


def test_operator_failed_pre_requires_proven_no_submit() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.mark_unknown("uncertain")
    with pytest.raises(IllegalWorkerTransition, match="proven_no_submit"):
        machine.reconcile(WorkerState.FAILED_PRE_SUBMIT, reason="guess")
    machine.reconcile(
        WorkerState.FAILED_PRE_SUBMIT,
        reason="vendor has no activity",
        proven_no_submit=True,
    )
    assert machine.record.state is WorkerState.FAILED_PRE_SUBMIT
    assert machine.record.spend_risk is SpendRisk.NONE


def test_restart_during_submit_is_unknown_not_resubmit() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.UNKNOWN_VENDOR_STATE
    assert disposition.may_resubmit is False
    assert disposition.may_first_submit is False
    assert disposition.action is RecoveryAction.OPERATOR_RECONCILE
    assert disposition.next_state is WorkerState.UNKNOWN_VENDOR_STATE


def test_restart_after_submit_before_activity_id_save() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit("act-mem")
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.UNKNOWN_VENDOR_STATE
    assert record.activity_id_durable is False
    assert disposition.action is RecoveryAction.OPERATOR_RECONCILE
    assert disposition.may_resubmit is False


def test_restart_after_activity_id_save_resumes_poll() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit("act-1")
    machine.persist_activity_id("act-1")
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.RECOVERY_REQUIRED
    assert disposition.action is RecoveryAction.RESUME_VENDOR_POLL
    assert disposition.may_resubmit is False


def test_restart_after_cache_before_consume() -> None:
    machine = _durable_processing()
    machine.receive_result()
    machine.normalize()
    machine.cache_result()
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.RECOVERY_REQUIRED
    assert disposition.action is RecoveryAction.CONSUME_WITHOUT_RESUBMIT
    machine.reconcile(WorkerState.CACHED, reason="replay cache pointer", result_cached=True)
    machine.consume()
    assert machine.record.state is WorkerState.CONSUMED
    assert machine.record.submit_attempted is True


def test_restart_after_result_before_cache() -> None:
    machine = _durable_processing()
    machine.receive_result()
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.RECOVERY_REQUIRED
    assert disposition.action is RecoveryAction.CACHE_WITHOUT_RESUBMIT
    machine.reconcile(WorkerState.NORMALIZED, reason="replay normalize")
    machine.cache_result()
    assert machine.record.state is WorkerState.CACHED


def test_restart_after_reserve_allows_first_submit_only() -> None:
    machine = _reserved()
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.ALLOWANCE_RESERVED
    assert disposition.may_first_submit is True
    assert disposition.may_resubmit is False
    assert disposition.action is RecoveryAction.CACHE_RECHECK_THEN_FIRST_SUBMIT
    machine.note_cache_miss()
    machine.begin_submit()
    assert machine.record.state is WorkerState.SUBMITTING


def test_restart_before_reserve_stays_pre_spend() -> None:
    machine = _machine()
    machine.validate()
    record, disposition = machine.apply_restart()
    assert record.state is WorkerState.VALIDATED
    assert disposition.action is RecoveryAction.CONTINUE_PRE_SPEND
    assert record.spend_risk is SpendRisk.NONE


def test_no_paid_retry_from_failed_post_submit() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.ack_submit("act-1")
    machine.persist_activity_id("act-1")
    machine.fail_post_submit("vendor failed")
    with pytest.raises(IllegalWorkerTransition, match="terminal|forbidden|reserve"):
        machine.begin_submit()
    with pytest.raises(IllegalWorkerTransition, match="terminal"):
        machine.require_recovery("retry")


def test_terminal_states_are_absorbing() -> None:
    hit = _machine()
    hit.validate()
    hit.note_cache_hit()
    with pytest.raises(IllegalWorkerTransition, match="terminal"):
        hit.validate()
    consumed = run_happy_path_cache_miss(
        job_id="job_2", fingerprint="fp-2", reservation_id="r", activity_id="a"
    )
    machine = DurableWorkerMachine(consumed)
    with pytest.raises(IllegalWorkerTransition, match="terminal"):
        machine.require_recovery("no")


def test_cannot_skip_reserve_or_persist() -> None:
    machine = _machine()
    machine.validate()
    machine.note_cache_miss()
    with pytest.raises(IllegalWorkerTransition, match="reserve before submit"):
        machine.begin_submit()
    with pytest.raises(IllegalWorkerTransition):
        machine.persist_activity_id("act-1")


def test_cannot_self_join() -> None:
    machine = _machine()
    machine.validate()
    with pytest.raises(IllegalWorkerTransition, match="cannot join itself"):
        machine.join("job_live_c")


def test_transition_table_covers_required_happy_and_failure_edges() -> None:
    rows = {(src, dest, mode) for src, dest, mode, _risk in transition_table_rows()}
    assert ("VALIDATED", "CACHE_HIT", "AUTOMATIC") in rows
    assert ("VALIDATED", "JOINED", "AUTOMATIC") in rows
    assert ("VALIDATED", "ALLOWANCE_RESERVED", "AUTOMATIC") in rows
    assert ("ALLOWANCE_RESERVED", "SUBMITTING", "AUTOMATIC") in rows
    assert ("SUBMITTING", "SUBMITTED", "AUTOMATIC") in rows
    assert ("SUBMITTED", "ACTIVITY_ID_PERSISTED", "AUTOMATIC") in rows
    assert ("CACHED", "CONSUMED", "AUTOMATIC") in rows
    assert ("UNKNOWN_VENDOR_STATE", "RECOVERY_REQUIRED", "AUTOMATIC") in rows
    assert ("UNKNOWN_VENDOR_STATE", "SUBMITTING", "AUTOMATIC") not in rows
    assert ("UNKNOWN_VENDOR_STATE", "PROCESSING", "OPERATOR_RECONCILE") in rows
    assert ("FAILED_PRE_SUBMIT", "SUBMITTING", "AUTOMATIC") not in rows
    assert ("FAILED_POST_SUBMIT", "SUBMITTING", "AUTOMATIC") not in rows


def test_next_safe_action_never_resubmits_unknown() -> None:
    machine = _ready_to_submit()
    machine.begin_submit()
    machine.mark_unknown("ambiguous")
    assert machine.next_safe_action() is RecoveryAction.OPERATOR_RECONCILE
    machine.assert_cannot_resubmit()
    with pytest.raises(IllegalWorkerTransition):
        machine.begin_submit()
