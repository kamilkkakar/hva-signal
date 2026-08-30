"""LIVE-I retry / timeout policy. No vendor. No FortyGuard."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.retry_timeout_policy import (
    CLIENT_FORBIDDEN_RETRY_FIELDS,
    ClientRetryControlError,
    PolicyContext,
    ReasonCode,
    RetryAction,
    RetryTimeoutBudget,
    SubmitCertainty,
    TimeoutClass,
    WorkerPhase,
    classify_timeout,
    collect_client_retry_controls,
    decide_retry_timeout,
    default_retry_timeout_budget,
    next_state_for,
    operator_budget_from_environ,
    reject_client_retry_controls,
    resolve_submit_certainty,
)
from app.services.retry_timeout import evaluate_retry_timeout, server_retry_timeout_budget


def _ctx(**overrides: object) -> PolicyContext:
    payload: dict[str, object] = {"worker_state": WorkerPhase.REQUESTED}
    payload.update(overrides)
    return PolicyContext.model_validate(payload)


def _assert_no_paid_resubmit(decision) -> None:
    assert decision.automatic_resubmit is False
    assert decision.paid_retry_authorized is False
    if decision.action != RetryAction.PROCEED_FIRST_SUBMIT:
        assert decision.vendor_submit_authorized is False


def test_default_budget_forbids_paid_retry_and_client_control() -> None:
    budget = default_retry_timeout_budget()
    assert budget.automatic_paid_retry is False
    assert budget.resubmit_without_activity_id is False
    assert budget.client_may_set_budget is False
    assert budget.source == "operator_server"
    with pytest.raises(ValidationError):
        RetryTimeoutBudget.model_validate({"automatic_paid_retry": True})
    with pytest.raises(ValidationError):
        RetryTimeoutBudget.model_validate({"resubmit_without_activity_id": True})
    with pytest.raises(ValidationError):
        RetryTimeoutBudget.model_validate({"client_may_set_budget": True})
    with pytest.raises(ValidationError):
        RetryTimeoutBudget.model_validate({"max_pre_submit_retries": 99})


def test_client_retry_fields_are_rejected_from_body_query_and_headers() -> None:
    body = {
        "area_id": "phoenix-demo",
        "retry_budget": {"max_retries": 9},
        "nested": [{"X-Force-Retry": "1"}],
    }
    hits = collect_client_retry_controls(body)
    assert "retry_budget" in hits
    assert "max_retries" in hits
    assert "x_force_retry" in hits
    with pytest.raises(ClientRetryControlError):
        reject_client_retry_controls({"poll_timeout_s": 1, "resubmit": True})

    decision = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.FAILED_PRE_SUBMIT,
            client_payload={"timeout_s": 5, "force_resubmit": True},
        )
    )
    assert decision.action == RetryAction.REJECT_CLIENT_CONTROL
    assert decision.reason_code == ReasonCode.CLIENT_RETRY_CONTROL_FORBIDDEN
    _assert_no_paid_resubmit(decision)


def test_operator_env_sets_budget_client_looking_env_ignored() -> None:
    budget = operator_budget_from_environ(
        {
            "HVA_LIVE_MAX_PRE_SUBMIT_RETRIES": "3",
            "HVA_LIVE_MAX_STATUS_POLLS": "10",
            "HVA_LIVE_MAX_RESULT_FETCHES": "4",
            "HVA_LIVE_SUBMIT_TIMEOUT_S": "15",
            "HVA_LIVE_PROCESSING_TIMEOUT_S": "90",
            "HVA_LIVE_RESULT_TIMEOUT_S": "20",
            "max_retries": "99",
            "RETRY_BUDGET": "unlimited",
            "force_retry": "true",
        }
    )
    assert budget.max_pre_submit_retries == 3
    assert budget.max_status_polls == 10
    assert budget.max_result_fetches == 4
    assert budget.submit_timeout_s == 15
    assert budget.processing_timeout_s == 90
    assert budget.result_timeout_s == 20
    assert budget.automatic_paid_retry is False


def test_pre_submit_failure_retries_only_when_submit_impossible() -> None:
    allowed = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.FAILED_PRE_SUBMIT, pre_submit_attempts=0)
    )
    assert allowed.action == RetryAction.RETRY_PRE_SUBMIT
    assert allowed.next_worker_state == WorkerPhase.REQUESTED
    assert allowed.submit_certainty == SubmitCertainty.IMPOSSIBLE
    assert allowed.vendor_submit_authorized is False
    _assert_no_paid_resubmit(allowed)

    exhausted = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.FAILED_PRE_SUBMIT, pre_submit_attempts=2)
    )
    assert exhausted.action == RetryAction.FAIL_CLOSED_NO_RETRY
    assert exhausted.reason_code == ReasonCode.PRE_SUBMIT_BUDGET_EXHAUSTED
    assert exhausted.next_worker_state == WorkerPhase.FAILED_PRE_SUBMIT
    _assert_no_paid_resubmit(exhausted)


def test_claimed_pre_submit_failure_after_submit_started_is_unknown() -> None:
    decision = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.FAILED_PRE_SUBMIT,
            submit_started=True,
        )
    )
    assert decision.action == RetryAction.HOLD_UNKNOWN
    assert decision.submit_certainty == SubmitCertainty.POSSIBLE
    assert decision.next_worker_state == WorkerPhase.UNKNOWN_VENDOR_STATE
    assert decision.vendor_submit_authorized is False
    _assert_no_paid_resubmit(decision)


def test_first_submit_from_reserved_is_not_a_retry() -> None:
    decision = decide_retry_timeout(_ctx(worker_state=WorkerPhase.ALLOWANCE_RESERVED))
    assert decision.action == RetryAction.PROCEED_FIRST_SUBMIT
    assert decision.vendor_submit_authorized is True
    assert decision.paid_retry_authorized is False
    assert decision.automatic_resubmit is False
    assert decision.next_worker_state == WorkerPhase.SUBMITTING


def test_submit_window_without_activity_id_never_resubmits() -> None:
    for state in (WorkerPhase.SUBMITTING, WorkerPhase.SUBMITTED):
        decision = decide_retry_timeout(_ctx(worker_state=state))
        assert decision.action == RetryAction.HOLD_UNKNOWN
        assert decision.next_worker_state == WorkerPhase.UNKNOWN_VENDOR_STATE
        assert decision.vendor_submit_authorized is False
        _assert_no_paid_resubmit(decision)


def test_submit_timeout_is_unknown_vendor_state() -> None:
    classified = classify_timeout(
        worker_state=WorkerPhase.SUBMITTING,
        activity_id=None,
        submit_elapsed_s=31.0,
    )
    assert classified == TimeoutClass.SUBMIT_TIMEOUT
    decision = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.SUBMITTING,
            timeout_class=TimeoutClass.SUBMIT_TIMEOUT,
        )
    )
    assert decision.action == RetryAction.HOLD_UNKNOWN
    assert decision.reason_code == ReasonCode.SUBMIT_TIMEOUT_UNKNOWN_VENDOR
    assert decision.next_worker_state == WorkerPhase.UNKNOWN_VENDOR_STATE
    assert decision.timeout_class == TimeoutClass.SUBMIT_TIMEOUT
    _assert_no_paid_resubmit(decision)


def test_processing_timeout_polls_then_fails_closed_never_resubmits() -> None:
    assert (
        classify_timeout(
            worker_state=WorkerPhase.PROCESSING,
            activity_id="act_1",
            processing_elapsed_s=121.0,
        )
        == TimeoutClass.PROCESSING_TIMEOUT
    )
    cont = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.PROCESSING,
            activity_id="act_1",
            timeout_class=TimeoutClass.PROCESSING_TIMEOUT,
            poll_count=3,
        )
    )
    assert cont.action == RetryAction.CONTINUE_POLL
    assert cont.reconcile_activity_id == "act_1"
    assert cont.next_worker_state == WorkerPhase.PROCESSING
    _assert_no_paid_resubmit(cont)

    done = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.PROCESSING,
            activity_id="act_1",
            timeout_class=TimeoutClass.PROCESSING_TIMEOUT,
            poll_count=8,
        )
    )
    assert done.action == RetryAction.FAIL_CLOSED_NO_RETRY
    assert done.reason_code == ReasonCode.PROCESSING_TIMEOUT_EXHAUSTED
    assert done.next_worker_state == WorkerPhase.FAILED_POST_SUBMIT
    _assert_no_paid_resubmit(done)


def test_result_timeout_retries_fetch_only() -> None:
    assert (
        classify_timeout(
            worker_state=WorkerPhase.RESULT_RECEIVED,
            activity_id="act_1",
            result_elapsed_s=31.0,
            processing_elapsed_s=999.0,
        )
        == TimeoutClass.RESULT_TIMEOUT
    )
    cont = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.RESULT_RECEIVED,
            activity_id="act_1",
            timeout_class=TimeoutClass.RESULT_TIMEOUT,
            result_fetch_count=1,
        )
    )
    assert cont.action == RetryAction.CONTINUE_RESULT_FETCH
    assert cont.next_worker_state == WorkerPhase.RESULT_RECEIVED
    _assert_no_paid_resubmit(cont)

    done = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.RESULT_RECEIVED,
            activity_id="act_1",
            timeout_class=TimeoutClass.RESULT_TIMEOUT,
            result_fetch_count=3,
        )
    )
    assert done.action == RetryAction.FAIL_CLOSED_NO_RETRY
    assert done.reason_code == ReasonCode.RESULT_TIMEOUT_EXHAUSTED
    assert done.next_worker_state == WorkerPhase.FAILED_POST_SUBMIT
    _assert_no_paid_resubmit(done)


def test_unknown_vendor_state_reconciles_via_activity_id_only() -> None:
    hold = decide_retry_timeout(_ctx(worker_state=WorkerPhase.UNKNOWN_VENDOR_STATE))
    assert hold.action == RetryAction.HOLD_UNKNOWN
    assert hold.next_worker_state == WorkerPhase.RECOVERY_REQUIRED
    _assert_no_paid_resubmit(hold)

    reconcile = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.UNKNOWN_VENDOR_STATE, activity_id="act_9")
    )
    assert reconcile.action == RetryAction.RECONCILE_VIA_ACTIVITY_ID
    assert reconcile.next_worker_state == WorkerPhase.PROCESSING
    assert reconcile.reconcile_activity_id == "act_9"
    _assert_no_paid_resubmit(reconcile)


def test_recovery_required_never_automatic_resubmit() -> None:
    decision = decide_retry_timeout(_ctx(worker_state=WorkerPhase.RECOVERY_REQUIRED))
    assert decision.action == RetryAction.HOLD_UNKNOWN
    assert decision.reason_code == ReasonCode.RECOVERY_REQUIRED_NO_RESUBMIT
    assert decision.next_worker_state == WorkerPhase.RECOVERY_REQUIRED
    _assert_no_paid_resubmit(decision)


def test_failed_post_submit_and_consumed_forbid_retry() -> None:
    post = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.FAILED_POST_SUBMIT, activity_id="act_1")
    )
    assert post.action == RetryAction.FAIL_CLOSED_NO_RETRY
    assert post.reason_code == ReasonCode.POST_SUBMIT_NO_RETRY
    _assert_no_paid_resubmit(post)

    consumed = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.CONSUMED, reservation_consumed=True, activity_id="act_1")
    )
    assert consumed.action == RetryAction.NO_ACTION
    _assert_no_paid_resubmit(consumed)

    spent = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.PROCESSING,
            activity_id="act_1",
            reservation_consumed=True,
        )
    )
    assert spent.action == RetryAction.FAIL_CLOSED_NO_RETRY
    assert spent.reason_code == ReasonCode.ALREADY_CONSUMED_NO_RETRY
    _assert_no_paid_resubmit(spent)


def test_known_activity_id_resumes_reconcile_not_submit() -> None:
    decision = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.ACTIVITY_ID_PERSISTED, activity_id="act_2")
    )
    assert decision.action == RetryAction.RECONCILE_VIA_ACTIVITY_ID
    assert decision.next_worker_state == WorkerPhase.PROCESSING
    assert decision.vendor_submit_authorized is False
    _assert_no_paid_resubmit(decision)


def test_submit_certainty_is_conservative() -> None:
    assert (
        resolve_submit_certainty(_ctx(worker_state=WorkerPhase.VALIDATED))
        == SubmitCertainty.IMPOSSIBLE
    )
    assert (
        resolve_submit_certainty(_ctx(worker_state=WorkerPhase.SUBMITTING))
        == SubmitCertainty.POSSIBLE
    )
    assert (
        resolve_submit_certainty(
            _ctx(worker_state=WorkerPhase.FAILED_PRE_SUBMIT, activity_id="act")
        )
        == SubmitCertainty.CONFIRMED
    )


def test_classify_timeout_does_not_collapse_classes() -> None:
    assert (
        classify_timeout(
            worker_state=WorkerPhase.SUBMITTING,
            activity_id=None,
            submit_elapsed_s=1.0,
        )
        is None
    )
    assert (
        classify_timeout(
            worker_state=WorkerPhase.PROCESSING,
            activity_id="act",
            submit_elapsed_s=999.0,
            processing_elapsed_s=1.0,
        )
        is None
    )
    assert (
        classify_timeout(
            worker_state=WorkerPhase.RESULT_RECEIVED,
            activity_id="act",
            submit_elapsed_s=999.0,
            processing_elapsed_s=999.0,
            result_elapsed_s=1.0,
        )
        is None
    )


def test_processing_timeout_without_activity_id_holds() -> None:
    decision = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.PROCESSING,
            timeout_class=TimeoutClass.PROCESSING_TIMEOUT,
        )
    )
    assert decision.action == RetryAction.HOLD_UNKNOWN
    assert decision.next_worker_state == WorkerPhase.RECOVERY_REQUIRED
    _assert_no_paid_resubmit(decision)


def test_happy_path_states_do_not_retry() -> None:
    for state in (
        WorkerPhase.REQUESTED,
        WorkerPhase.VALIDATED,
        WorkerPhase.CACHE_HIT,
        WorkerPhase.JOINED,
    ):
        decision = decide_retry_timeout(_ctx(worker_state=state))
        assert decision.action == RetryAction.NO_ACTION
        _assert_no_paid_resubmit(decision)


def test_next_state_helper_and_server_loader() -> None:
    decision = decide_retry_timeout(
        _ctx(worker_state=WorkerPhase.UNKNOWN_VENDOR_STATE, activity_id="act")
    )
    assert next_state_for(decision, WorkerPhase.UNKNOWN_VENDOR_STATE) == WorkerPhase.PROCESSING
    loaded = server_retry_timeout_budget()
    assert loaded.source == "operator_server"
    via_service = evaluate_retry_timeout(
        _ctx(worker_state=WorkerPhase.FAILED_PRE_SUBMIT),
        budget=RetryTimeoutBudget(),
    )
    assert via_service.action == RetryAction.RETRY_PRE_SUBMIT


def test_client_cannot_raise_caps_by_injecting_budget_model_fields() -> None:
    assert "max_status_polls" in CLIENT_FORBIDDEN_RETRY_FIELDS
    decision = decide_retry_timeout(
        _ctx(
            worker_state=WorkerPhase.PROCESSING,
            activity_id="act",
            timeout_class=TimeoutClass.PROCESSING_TIMEOUT,
            poll_count=8,
            client_payload={"max_status_polls": 32},
        )
    )
    assert decision.action == RetryAction.REJECT_CLIENT_CONTROL
    _assert_no_paid_resubmit(decision)


def test_policy_context_forbids_unknown_client_budget_fields() -> None:
    with pytest.raises(ValidationError):
        PolicyContext.model_validate(
            {"worker_state": "REQUESTED", "retry_budget": {"max_retries": 9}}
        )
