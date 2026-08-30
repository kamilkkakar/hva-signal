"""Activity-id reconciliation: atomic persist, restart, no blind resubmit."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.activity_reconciliation import (
    ActivityBinding,
    ActivityCrashPoint,
    AtMostOneSubmitPolicy,
    DurableLivePhase,
    ExactlyOnceClaim,
    RecoveryAction,
    SpendRisk,
    VendorPollStatus,
    decide_recovery,
    exactly_once_claim,
    may_call_vendor_submit,
    spend_risk_for,
)
from app.services.activity_reconciliation import (
    ActivityCrash,
    ActivityReconciliationError,
    ActivityReconciler,
    InMemoryActivityLedger,
    honesty_record,
    simulate_submit_then_crash,
)
from app.services.activity_vendor_hooks import ScriptedVendorHooks


FP = "aa" * 32
GEO = "bb" * 32
ACT = "mock_activity_01"


class _FailingSink:
    def __init__(self) -> None:
        self.commits = 0
        self.fail = False

    def commit_binding(self, binding: ActivityBinding) -> None:
        if self.fail:
            raise RuntimeError("sink_refused")
        self.commits += 1


class _RecordingSink:
    def __init__(self) -> None:
        self.rows: list[ActivityBinding] = []

    def commit_binding(self, binding: ActivityBinding) -> None:
        dumped = binding.model_dump()
        ActivityBinding.model_validate(dumped)
        if dumped.get("activity_id") is not None:
            assert dumped["phase"] == DurableLivePhase.ACTIVITY_ID_PERSISTED.value or dumped[
                "phase"
            ] in {
                DurableLivePhase.PROCESSING.value,
                DurableLivePhase.RESULT_RECEIVED.value,
                DurableLivePhase.FAILED_POST_SUBMIT.value,
            }
            assert dumped["phase"] not in {
                DurableLivePhase.SUBMITTING.value,
                DurableLivePhase.SUBMITTED.value,
            }
        self.rows.append(binding)


def _open(
    ledger: InMemoryActivityLedger | None = None,
    *,
    job_id: str = "job_1",
    fingerprint: str = FP,
) -> tuple[InMemoryActivityLedger, ActivityBinding]:
    store = ledger or InMemoryActivityLedger()
    binding, joined = store.open_or_join(
        job_id=job_id,
        request_fingerprint=fingerprint,
        geometry_sha256=GEO,
        reservation_id="res_1",
    )
    assert joined is False
    return store, binding


def test_atomic_persist_is_submitted_to_activity_id_persisted() -> None:
    sink = _RecordingSink()
    ledger, binding = _open(InMemoryActivityLedger(sink=sink))
    ledger.mark_submitting(binding.record_id)
    ledger.note_submitted_awaiting_persist(binding.record_id)
    awaiting = ledger.get(binding.record_id)
    assert awaiting is not None
    assert awaiting.phase == DurableLivePhase.SUBMITTED
    assert awaiting.activity_id is None
    persisted = ledger.persist_activity_id(binding.record_id, ACT)
    assert persisted.phase == DurableLivePhase.ACTIVITY_ID_PERSISTED
    assert persisted.activity_id == ACT
    assert persisted.activity_id_persisted_at is not None
    assert ledger.find_by_fingerprint(FP) == persisted
    assert ledger.find_by_activity_id(ACT) == persisted
    durable_with_id = [row for row in sink.rows if row.activity_id]
    assert durable_with_id
    assert all(
        row.phase != DurableLivePhase.SUBMITTED or row.activity_id is None
        for row in sink.rows
    )


def test_persist_is_idempotent_for_same_id_and_rejects_other() -> None:
    ledger, binding = _open()
    ledger.mark_submitting(binding.record_id)
    first = ledger.persist_activity_id(binding.record_id, ACT)
    second = ledger.persist_activity_id(binding.record_id, ACT)
    assert first.activity_id == second.activity_id == ACT
    with pytest.raises(ActivityReconciliationError, match="different value"):
        ledger.persist_activity_id(binding.record_id, "mock_other")
    with pytest.raises(ActivityReconciliationError, match="required"):
        ledger.persist_activity_id(binding.record_id, "   ")


def test_sink_failure_does_not_publish_activity_id() -> None:
    sink = _FailingSink()
    ledger, binding = _open(InMemoryActivityLedger(sink=sink))
    ledger.mark_submitting(binding.record_id)
    sink.fail = True
    with pytest.raises(RuntimeError, match="sink_refused"):
        ledger.persist_activity_id(binding.record_id, ACT)
    current = ledger.get(binding.record_id)
    assert current is not None
    assert current.activity_id is None
    assert current.phase == DurableLivePhase.SUBMITTING
    assert ledger.find_by_activity_id(ACT) is None


def test_fingerprint_activity_id_bijection() -> None:
    ledger, first = _open()
    ledger.mark_submitting(first.record_id)
    ledger.persist_activity_id(first.record_id, ACT)
    joined, was_join = ledger.open_or_join(
        job_id="job_2",
        request_fingerprint=FP,
        geometry_sha256=GEO,
    )
    assert was_join is True
    assert joined.record_id == first.record_id
    assert joined.activity_id == ACT
    other, _ = ledger.open_or_join(
        job_id="job_3",
        request_fingerprint="cc" * 32,
        geometry_sha256="dd" * 32,
    )
    ledger.mark_submitting(other.record_id)
    with pytest.raises(ActivityReconciliationError, match="different fingerprint"):
        ledger.persist_activity_id(other.record_id, ACT)


def test_exactly_once_is_at_most_one_submit_not_mathematical() -> None:
    claim = exactly_once_claim()
    assert claim.mathematical_exactly_once is False
    assert claim.best_achievable == "at_most_one_submit"
    assert claim.vendor_idempotency == "NOT_ASSUMED"
    policy = AtMostOneSubmitPolicy()
    assert policy.automatic_resubmit is False
    assert policy.resubmit_without_activity_id is False
    with pytest.raises(ValidationError):
        AtMostOneSubmitPolicy.model_validate({"mathematical_exactly_once": True})
    with pytest.raises(ValidationError):
        AtMostOneSubmitPolicy.model_validate({"automatic_resubmit": True})
    with pytest.raises(ValidationError):
        ExactlyOnceClaim.model_validate({"mathematical_exactly_once": True})
    record = honesty_record()
    assert record["mathematical_exactly_once"] is False


def test_crash_after_submit_before_activity_id_never_resubmits() -> None:
    ledger = InMemoryActivityLedger()
    submits: list[str] = []
    with pytest.raises(ActivityCrash) as crashed:
        simulate_submit_then_crash(
            ledger,
            job_id="job_1",
            request_fingerprint=FP,
            geometry_sha256=GEO,
            activity_id=ACT,
            crash_at=ActivityCrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID_SAVE,
            submit_counter=submits,
        )
    assert crashed.value.point == ActivityCrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID_SAVE
    assert submits == [ACT]
    binding = ledger.find_by_fingerprint(FP)
    assert binding is not None
    assert binding.activity_id is None
    assert binding.phase == DurableLivePhase.SUBMITTED
    assert spend_risk_for(binding) == SpendRisk.UNKNOWN_MAY_HAVE_SPENT

    restarted = ledger.fork_after_restart()
    reconciler = ActivityReconciler(restarted)
    decision = reconciler.apply_restart(binding.record_id)
    assert decision.action == RecoveryAction.REQUIRE_OPERATOR_RECOVERY
    assert decision.may_submit is False
    parked = restarted.get(binding.record_id)
    assert parked is not None
    assert parked.phase == DurableLivePhase.RECOVERY_REQUIRED
    assert any("UNKNOWN_VENDOR_STATE" in note for note in parked.notes)
    with pytest.raises(ActivityReconciliationError, match="blind resubmit"):
        reconciler.refuse_blind_resubmit(binding.record_id)
    hooks = ScriptedVendorHooks()
    with pytest.raises(ActivityReconciliationError, match="UNKNOWN_VENDOR_STATE"):
        reconciler.resume_processing(binding.record_id, hooks)
    assert hooks.submit_calls == []
    assert len(submits) == 1


def test_crash_after_activity_id_save_resumes_poll_only() -> None:
    ledger = InMemoryActivityLedger()
    submits: list[str] = []
    with pytest.raises(ActivityCrash):
        simulate_submit_then_crash(
            ledger,
            job_id="job_1",
            request_fingerprint=FP,
            geometry_sha256=GEO,
            activity_id=ACT,
            crash_at=ActivityCrashPoint.AFTER_ACTIVITY_ID_SAVE,
            submit_counter=submits,
        )
    binding = ledger.find_by_activity_id(ACT)
    assert binding is not None
    assert binding.phase == DurableLivePhase.ACTIVITY_ID_PERSISTED
    assert spend_risk_for(binding) == SpendRisk.SPENT_KNOWN_ACTIVITY

    restarted = ledger.fork_after_restart()
    reconciler = ActivityReconciler(restarted)
    decision = reconciler.apply_restart(binding.record_id)
    assert decision.action == RecoveryAction.RESUME_POLL
    assert decision.may_submit is False
    assert decision.activity_id == ACT
    current = restarted.get(binding.record_id)
    assert current is not None
    assert current.phase == DurableLivePhase.PROCESSING

    hooks = ScriptedVendorHooks(
        statuses=[VendorPollStatus.PROCESSING, VendorPollStatus.SUCCEEDED],
        result_payload={"ok": True},
    )
    still, payload = reconciler.resume_processing(binding.record_id, hooks)
    assert still.phase == DurableLivePhase.PROCESSING
    assert payload is None
    done, result = reconciler.resume_processing(binding.record_id, hooks)
    assert done.phase == DurableLivePhase.RESULT_RECEIVED
    assert result is not None
    assert result.payload["ok"] is True
    assert hooks.poll_calls == [ACT, ACT]
    assert hooks.fetch_calls == [ACT]
    assert hooks.submit_calls == []
    assert submits == [ACT]


def test_crash_during_vendor_processing_resumes_poll_never_second_submit() -> None:
    ledger = InMemoryActivityLedger()
    submits: list[str] = []
    with pytest.raises(ActivityCrash) as crashed:
        simulate_submit_then_crash(
            ledger,
            job_id="job_1",
            request_fingerprint=FP,
            geometry_sha256=GEO,
            activity_id=ACT,
            crash_at=ActivityCrashPoint.DURING_VENDOR_PROCESSING,
            submit_counter=submits,
        )
    assert crashed.value.point == ActivityCrashPoint.DURING_VENDOR_PROCESSING
    binding = ledger.find_by_activity_id(ACT)
    assert binding is not None
    assert binding.phase == DurableLivePhase.PROCESSING

    restarted = ledger.fork_after_restart()
    reconciler = ActivityReconciler(restarted)
    decision = reconciler.apply_restart(binding.record_id)
    assert decision.action == RecoveryAction.RESUME_POLL
    assert may_call_vendor_submit(decision) is False
    hooks = ScriptedVendorHooks(statuses=[VendorPollStatus.SUCCEEDED])
    done, result = reconciler.resume_processing(binding.record_id, hooks)
    assert done.phase == DurableLivePhase.RESULT_RECEIVED
    assert result is not None
    assert hooks.submit_calls == []
    assert submits == [ACT]


def test_pre_submit_may_submit_once_cache_hit_must_not() -> None:
    ledger, reserved = _open()
    allowed = decide_recovery(reserved)
    assert allowed.action == RecoveryAction.SUBMIT_ALLOWED
    assert may_call_vendor_submit(allowed) is True
    assert spend_risk_for(reserved) == SpendRisk.RESERVED_NOT_SUBMITTED

    reuse = reserved.model_copy(update={"phase": DurableLivePhase.CACHE_HIT})
    blocked = decide_recovery(reuse)
    assert blocked.action == RecoveryAction.NO_VENDOR_WORK
    assert blocked.may_submit is False


def test_unknown_and_recovery_required_never_become_submit() -> None:
    ledger, binding = _open()
    ledger.mark_submitting(binding.record_id)
    parked = ledger.park_unknown_for_recovery(binding.record_id, reason="lost_id")
    assert parked.phase == DurableLivePhase.RECOVERY_REQUIRED
    decision = decide_recovery(parked)
    assert decision.action == RecoveryAction.REQUIRE_OPERATOR_RECOVERY
    assert decision.may_submit is False
    assert not may_call_vendor_submit(decision)


def test_failed_post_submit_does_not_resubmit() -> None:
    ledger, binding = _open()
    ledger.mark_submitting(binding.record_id)
    ledger.persist_activity_id(binding.record_id, ACT)
    ledger.mark_processing(binding.record_id)
    failed = ledger.mark_failed_post_submit(binding.record_id, note="vendor_failed")
    decision = decide_recovery(failed)
    assert decision.action == RecoveryAction.FAIL_CLOSED
    assert decision.may_submit is False
    assert spend_risk_for(failed) == SpendRisk.FAILED_POST_SUBMIT


def test_scripted_hooks_submit_is_forbidden() -> None:
    hooks = ScriptedVendorHooks()
    with pytest.raises(RuntimeError, match="never call vendor submit"):
        hooks.submit({"fingerprint": FP})
    assert hooks.submit_calls == ["forbidden"]


def test_binding_rejects_activity_id_on_submitted_phase() -> None:
    with pytest.raises(ValidationError, match="ACTIVITY_ID_PERSISTED"):
        ActivityBinding(
            record_id="act_1",
            job_id="job_1",
            request_fingerprint=FP,
            geometry_sha256=GEO,
            activity_id=ACT,
            phase=DurableLivePhase.SUBMITTED,
            activity_id_persisted_at=datetime.now(timezone.utc),
        )


def test_apply_restart_all_parks_uncertain_and_resumes_known() -> None:
    ledger = InMemoryActivityLedger()
    lost, _ = ledger.open_or_join(
        job_id="job_lost",
        request_fingerprint="ee" * 32,
        geometry_sha256=GEO,
    )
    ledger.mark_submitting(lost.record_id)
    known, _ = ledger.open_or_join(
        job_id="job_known",
        request_fingerprint="ff" * 32,
        geometry_sha256=GEO,
    )
    ledger.mark_submitting(known.record_id)
    ledger.persist_activity_id(known.record_id, "mock_known")
    decisions = ActivityReconciler(ledger).apply_restart_all()
    actions = {item.action for item in decisions}
    assert RecoveryAction.REQUIRE_OPERATOR_RECOVERY in actions
    assert RecoveryAction.RESUME_POLL in actions
    assert ledger.find_by_job("job_lost").phase == DurableLivePhase.RECOVERY_REQUIRED
    assert ledger.find_by_job("job_known").phase == DurableLivePhase.PROCESSING
