"""Activity-id reconciliation for J3/J4 live acquisition.

Honest guarantee: at-most-one-submit from this control plane when
SUBMITTING is persisted before the vendor RPC. Not mathematical
exactly-once. Vendor idempotency is not assumed.

Not a public / OpenAPI type. No FortyGuard. No real vendor I/O.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ACTIVITY_RECONCILIATION_CONTRACT_VERSION = "hva-signal-activity-reconciliation-v1"
AT_MOST_ONE_SUBMIT_POLICY_VERSION = "hva-signal-at-most-one-submit-v1"


class DurableLivePhase(str, Enum):
    """J3/J4 worker vocabulary. LIVE-D owns activity_id transitions only."""

    REQUESTED = "REQUESTED"
    VALIDATED = "VALIDATED"
    CACHE_HIT = "CACHE_HIT"
    JOINED = "JOINED"
    ALLOWANCE_RESERVED = "ALLOWANCE_RESERVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    ACTIVITY_ID_PERSISTED = "ACTIVITY_ID_PERSISTED"
    PROCESSING = "PROCESSING"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    NORMALIZED = "NORMALIZED"
    CACHED = "CACHED"
    CONSUMED = "CONSUMED"
    FAILED_PRE_SUBMIT = "FAILED_PRE_SUBMIT"
    FAILED_POST_SUBMIT = "FAILED_POST_SUBMIT"
    UNKNOWN_VENDOR_STATE = "UNKNOWN_VENDOR_STATE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class RecoveryAction(str, Enum):
    NO_VENDOR_WORK = "NO_VENDOR_WORK"
    SUBMIT_ALLOWED = "SUBMIT_ALLOWED"
    RESUME_POLL = "RESUME_POLL"
    FETCH_RESULT = "FETCH_RESULT"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"
    REQUIRE_OPERATOR_RECOVERY = "REQUIRE_OPERATOR_RECOVERY"
    FAIL_CLOSED = "FAIL_CLOSED"


class SpendRisk(str, Enum):
    NONE = "NONE"
    RESERVED_NOT_SUBMITTED = "RESERVED_NOT_SUBMITTED"
    UNKNOWN_MAY_HAVE_SPENT = "UNKNOWN_MAY_HAVE_SPENT"
    SPENT_KNOWN_ACTIVITY = "SPENT_KNOWN_ACTIVITY"
    SPENT_RESULT_IN_HAND = "SPENT_RESULT_IN_HAND"
    CONSUMED = "CONSUMED"
    FAILED_PRE_SUBMIT = "FAILED_PRE_SUBMIT"
    FAILED_POST_SUBMIT = "FAILED_POST_SUBMIT"


class ActivityCrashPoint(str, Enum):
    AFTER_SUBMIT_BEFORE_ACTIVITY_ID_SAVE = "after_submit_before_activity_id_save"
    AFTER_ACTIVITY_ID_SAVE = "after_activity_id_save"
    DURING_VENDOR_PROCESSING = "during_vendor_processing"


class VendorPollStatus(str, Enum):
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"


_PRE_SUBMIT = frozenset(
    {
        DurableLivePhase.REQUESTED,
        DurableLivePhase.VALIDATED,
        DurableLivePhase.ALLOWANCE_RESERVED,
    }
)
_NO_VENDOR = frozenset(
    {
        DurableLivePhase.CACHE_HIT,
        DurableLivePhase.JOINED,
        DurableLivePhase.CONSUMED,
        DurableLivePhase.NORMALIZED,
        DurableLivePhase.CACHED,
    }
)
_SUBMIT_MAY_HAVE_HAPPENED = frozenset(
    {
        DurableLivePhase.SUBMITTING,
        DurableLivePhase.SUBMITTED,
    }
)
_UNKNOWN_PARKED = frozenset(
    {
        DurableLivePhase.UNKNOWN_VENDOR_STATE,
        DurableLivePhase.RECOVERY_REQUIRED,
    }
)
_POST_ID = frozenset(
    {
        DurableLivePhase.ACTIVITY_ID_PERSISTED,
        DurableLivePhase.PROCESSING,
        DurableLivePhase.RESULT_RECEIVED,
        DurableLivePhase.NORMALIZED,
        DurableLivePhase.CACHED,
        DurableLivePhase.CONSUMED,
        DurableLivePhase.FAILED_POST_SUBMIT,
    }
)


class AtMostOneSubmitPolicy(BaseModel):
    """Best achievable control-plane guarantee. Not mathematical exactly-once."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["hva-signal-at-most-one-submit-v1"] = (
        AT_MOST_ONE_SUBMIT_POLICY_VERSION
    )
    mathematical_exactly_once: Literal[False] = False
    vendor_idempotency_assumed: Literal[False] = False
    automatic_resubmit: Literal[False] = False
    blind_paid_retry: Literal[False] = False
    resubmit_without_activity_id: Literal[False] = False
    persist_submitting_before_vendor_rpc: Literal[True] = True
    atomic_activity_id_with_persisted_phase: Literal[True] = True
    best_achievable: Literal["at_most_one_submit"] = "at_most_one_submit"


class ActivityBinding(BaseModel):
    """Fingerprint ↔ activity_id binding. activity_id is the only resume token."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-activity-reconciliation-v1"] = (
        ACTIVITY_RECONCILIATION_CONTRACT_VERSION
    )
    record_id: str
    job_id: str
    request_fingerprint: str = Field(min_length=16)
    geometry_sha256: str = Field(min_length=16)
    reservation_id: str | None = None
    activity_id: str | None = None
    phase: DurableLivePhase = DurableLivePhase.ALLOWANCE_RESERVED
    submit_attempted: bool = False
    submit_attempted_at: datetime | None = None
    activity_id_persisted_at: datetime | None = None
    poll_count: int = Field(default=0, ge=0)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _id_and_phase_agree(self) -> ActivityBinding:
        if self.activity_id is not None and self.phase in _SUBMIT_MAY_HAVE_HAPPENED:
            raise ValueError(
                "activity_id cannot coexist with SUBMITTING/SUBMITTED; "
                "persist atomically to ACTIVITY_ID_PERSISTED"
            )
        if (
            self.activity_id is not None
            and self.phase in _PRE_SUBMIT | {DurableLivePhase.FAILED_PRE_SUBMIT}
        ):
            raise ValueError("pre-submit phases cannot carry an activity_id")
        if self.activity_id is None and self.phase in _POST_ID - {
            DurableLivePhase.FAILED_POST_SUBMIT
        }:
            raise ValueError(f"{self.phase.value} requires a persisted activity_id")
        if self.activity_id is not None and self.activity_id_persisted_at is None:
            raise ValueError("activity_id requires activity_id_persisted_at")
        return self


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RecoveryAction
    from_phase: DurableLivePhase
    to_phase: DurableLivePhase | None = None
    park_phase: DurableLivePhase | None = None
    activity_id: str | None = None
    request_fingerprint: str
    spend_risk: SpendRisk
    may_submit: Literal[False] | bool = False
    reason: str

    @model_validator(mode="after")
    def _never_submit_from_unknown(self) -> RecoveryDecision:
        if self.action in {
            RecoveryAction.HOLD_UNKNOWN,
            RecoveryAction.REQUIRE_OPERATOR_RECOVERY,
            RecoveryAction.RESUME_POLL,
            RecoveryAction.FETCH_RESULT,
            RecoveryAction.FAIL_CLOSED,
            RecoveryAction.NO_VENDOR_WORK,
        }:
            object.__setattr__(self, "may_submit", False)
        if self.from_phase in _UNKNOWN_PARKED and self.may_submit:
            raise ValueError("UNKNOWN_VENDOR_STATE/RECOVERY_REQUIRED must never submit")
        if self.activity_id and self.may_submit:
            raise ValueError("known activity_id must never submit again")
        return self


class ExactlyOnceClaim(BaseModel):
    """Public honesty record. mathematical_exactly_once is always false."""

    model_config = ConfigDict(extra="forbid")

    mathematical_exactly_once: Literal[False] = False
    vendor_idempotency: Literal["NOT_ASSUMED"] = "NOT_ASSUMED"
    best_achievable: Literal["at_most_one_submit"] = "at_most_one_submit"
    residual_double_submit_if: str = (
        "SUBMITTING was not durable before the vendor accepted the request, "
        "then the process died, then restart treated the job as pre-submit."
    )


def default_at_most_one_submit_policy() -> AtMostOneSubmitPolicy:
    return AtMostOneSubmitPolicy()


def exactly_once_claim() -> ExactlyOnceClaim:
    return ExactlyOnceClaim()


def spend_risk_for(binding: ActivityBinding) -> SpendRisk:
    if binding.phase == DurableLivePhase.CONSUMED:
        return SpendRisk.CONSUMED
    if binding.phase == DurableLivePhase.FAILED_PRE_SUBMIT and not binding.submit_attempted:
        return SpendRisk.FAILED_PRE_SUBMIT
    if binding.phase == DurableLivePhase.FAILED_POST_SUBMIT:
        return SpendRisk.FAILED_POST_SUBMIT
    if binding.activity_id is not None:
        if binding.phase in {
            DurableLivePhase.RESULT_RECEIVED,
            DurableLivePhase.NORMALIZED,
            DurableLivePhase.CACHED,
        }:
            return SpendRisk.SPENT_RESULT_IN_HAND
        return SpendRisk.SPENT_KNOWN_ACTIVITY
    if binding.phase in _UNKNOWN_PARKED:
        return SpendRisk.UNKNOWN_MAY_HAVE_SPENT
    if binding.submit_attempted or binding.phase in _SUBMIT_MAY_HAVE_HAPPENED:
        return SpendRisk.UNKNOWN_MAY_HAVE_SPENT
    if binding.phase == DurableLivePhase.ALLOWANCE_RESERVED:
        return SpendRisk.RESERVED_NOT_SUBMITTED
    if binding.phase == DurableLivePhase.FAILED_PRE_SUBMIT:
        return SpendRisk.FAILED_PRE_SUBMIT
    return SpendRisk.NONE


def decide_recovery(
    binding: ActivityBinding,
    *,
    policy: AtMostOneSubmitPolicy | None = None,
) -> RecoveryDecision:
    """Restart / resume decision. Never invents a second vendor submit."""

    policy = policy or default_at_most_one_submit_policy()
    risk = spend_risk_for(binding)
    fp = binding.request_fingerprint

    if policy.automatic_resubmit or policy.resubmit_without_activity_id:
        return RecoveryDecision(
            action=RecoveryAction.FAIL_CLOSED,
            from_phase=binding.phase,
            activity_id=binding.activity_id,
            request_fingerprint=fp,
            spend_risk=risk,
            may_submit=False,
            reason="illegal_policy_would_allow_resubmit",
        )

    if binding.phase in _NO_VENDOR:
        return RecoveryDecision(
            action=RecoveryAction.NO_VENDOR_WORK,
            from_phase=binding.phase,
            activity_id=binding.activity_id,
            request_fingerprint=fp,
            spend_risk=risk,
            may_submit=False,
            reason="reuse_or_terminal_no_vendor",
        )

    if binding.phase in _UNKNOWN_PARKED:
        return RecoveryDecision(
            action=RecoveryAction.REQUIRE_OPERATOR_RECOVERY,
            from_phase=binding.phase,
            to_phase=DurableLivePhase.RECOVERY_REQUIRED,
            park_phase=DurableLivePhase.RECOVERY_REQUIRED,
            activity_id=binding.activity_id,
            request_fingerprint=fp,
            spend_risk=SpendRisk.UNKNOWN_MAY_HAVE_SPENT,
            may_submit=False,
            reason="unknown_vendor_state_never_resubmit",
        )

    if binding.activity_id:
        if binding.phase == DurableLivePhase.FAILED_POST_SUBMIT:
            return RecoveryDecision(
                action=RecoveryAction.FAIL_CLOSED,
                from_phase=binding.phase,
                activity_id=binding.activity_id,
                request_fingerprint=fp,
                spend_risk=risk,
                may_submit=False,
                reason="post_submit_failure_no_resubmit",
            )
        if binding.phase == DurableLivePhase.RESULT_RECEIVED:
            return RecoveryDecision(
                action=RecoveryAction.FETCH_RESULT,
                from_phase=binding.phase,
                activity_id=binding.activity_id,
                request_fingerprint=fp,
                spend_risk=risk,
                may_submit=False,
                reason="result_fetch_only",
            )
        return RecoveryDecision(
            action=RecoveryAction.RESUME_POLL,
            from_phase=binding.phase,
            to_phase=DurableLivePhase.PROCESSING,
            activity_id=binding.activity_id,
            request_fingerprint=fp,
            spend_risk=risk,
            may_submit=False,
            reason="resume_processing_via_poll",
        )

    if (
        binding.submit_attempted
        or binding.phase in _SUBMIT_MAY_HAVE_HAPPENED
        or binding.phase == DurableLivePhase.FAILED_POST_SUBMIT
    ):
        return RecoveryDecision(
            action=RecoveryAction.HOLD_UNKNOWN,
            from_phase=binding.phase,
            to_phase=DurableLivePhase.UNKNOWN_VENDOR_STATE,
            park_phase=DurableLivePhase.RECOVERY_REQUIRED,
            activity_id=None,
            request_fingerprint=fp,
            spend_risk=SpendRisk.UNKNOWN_MAY_HAVE_SPENT,
            may_submit=False,
            reason="submit_may_have_happened_activity_id_missing",
        )

    if binding.phase == DurableLivePhase.FAILED_PRE_SUBMIT:
        return RecoveryDecision(
            action=RecoveryAction.FAIL_CLOSED,
            from_phase=binding.phase,
            activity_id=None,
            request_fingerprint=fp,
            spend_risk=risk,
            may_submit=False,
            reason="failed_pre_submit_no_automatic_retry",
        )

    if binding.phase in _PRE_SUBMIT:
        return RecoveryDecision(
            action=RecoveryAction.SUBMIT_ALLOWED,
            from_phase=binding.phase,
            to_phase=DurableLivePhase.SUBMITTING,
            activity_id=None,
            request_fingerprint=fp,
            spend_risk=risk,
            may_submit=True,
            reason="submit_could_not_have_occurred",
        )

    return RecoveryDecision(
        action=RecoveryAction.FAIL_CLOSED,
        from_phase=binding.phase,
        activity_id=binding.activity_id,
        request_fingerprint=fp,
        spend_risk=risk,
        may_submit=False,
        reason="unclassified_fail_closed",
    )


def may_call_vendor_submit(decision: RecoveryDecision) -> bool:
    return decision.action == RecoveryAction.SUBMIT_ALLOWED and decision.may_submit is True
