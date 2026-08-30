"""LIVE-I retry / timeout policy for HVA-SIGNAL J3/J4 live acquisition.

Isolated contract. Does not call vendors. Does not import FortyGuard.

Hard rules:
- No blind paid retry.
- Pre-submit failures may retry only if no submit could have occurred.
- Post-submit / UNKNOWN_VENDOR_STATE: reconcile via activity_id only; never
  automatic resubmit.
- Timeouts distinguish submit-timeout (unknown) vs processing-timeout (poll)
  vs result-timeout.
- Retry budgets are operator / server-side only. Clients cannot set them.

Best achievable guarantee is at-most-one-submit, not mathematical exactly-once.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

RETRY_TIMEOUT_POLICY_VERSION = "hva-signal-retry-timeout-v1"

# Operator env keys. Anything else (including client-looking names) is ignored.
OPERATOR_ENV_MAX_PRE_SUBMIT_RETRIES = "HVA_LIVE_MAX_PRE_SUBMIT_RETRIES"
OPERATOR_ENV_MAX_STATUS_POLLS = "HVA_LIVE_MAX_STATUS_POLLS"
OPERATOR_ENV_MAX_RESULT_FETCHES = "HVA_LIVE_MAX_RESULT_FETCHES"
OPERATOR_ENV_SUBMIT_TIMEOUT_S = "HVA_LIVE_SUBMIT_TIMEOUT_S"
OPERATOR_ENV_PROCESSING_TIMEOUT_S = "HVA_LIVE_PROCESSING_TIMEOUT_S"
OPERATOR_ENV_RESULT_TIMEOUT_S = "HVA_LIVE_RESULT_TIMEOUT_S"

# Normalized (lower, hyphen/space → underscore). Nested keys included.
CLIENT_FORBIDDEN_RETRY_FIELDS = frozenset(
    {
        "retry_budget",
        "retry_policy",
        "timeout_policy",
        "timeout_budget",
        "max_retries",
        "max_pre_submit_retries",
        "retry_count",
        "automatic_retry",
        "automatic_paid_retry",
        "paid_retry",
        "force_retry",
        "force_resubmit",
        "resubmit",
        "resubmit_on_timeout",
        "resubmit_without_activity_id",
        "timeout_s",
        "submit_timeout",
        "submit_timeout_s",
        "processing_timeout",
        "processing_timeout_s",
        "poll_timeout",
        "poll_timeout_s",
        "result_timeout",
        "result_timeout_s",
        "max_status_polls",
        "max_result_fetches",
        "operator_retry_override",
        "retry_override",
        "x_retry_budget",
        "x_force_retry",
        "x_resubmit",
        "x_timeout_s",
    }
)


class WorkerPhase(str, Enum):
    """Durable worker phases owned by LIVE-C. Retry policy keys off these."""

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


class SubmitCertainty(str, Enum):
    """Whether a vendor submit could have occurred. Conservative: prefer POSSIBLE."""

    IMPOSSIBLE = "IMPOSSIBLE"
    POSSIBLE = "POSSIBLE"
    CONFIRMED = "CONFIRMED"


class TimeoutClass(str, Enum):
    """Three timeout classes. Do not collapse them into one 'vendor timeout'."""

    SUBMIT_TIMEOUT = "SUBMIT_TIMEOUT"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    RESULT_TIMEOUT = "RESULT_TIMEOUT"


class RetryAction(str, Enum):
    RETRY_PRE_SUBMIT = "RETRY_PRE_SUBMIT"
    PROCEED_FIRST_SUBMIT = "PROCEED_FIRST_SUBMIT"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"
    RECONCILE_VIA_ACTIVITY_ID = "RECONCILE_VIA_ACTIVITY_ID"
    CONTINUE_POLL = "CONTINUE_POLL"
    CONTINUE_RESULT_FETCH = "CONTINUE_RESULT_FETCH"
    FAIL_CLOSED_NO_RETRY = "FAIL_CLOSED_NO_RETRY"
    REJECT_CLIENT_CONTROL = "REJECT_CLIENT_CONTROL"
    NO_ACTION = "NO_ACTION"


class ReasonCode(str, Enum):
    CLIENT_RETRY_CONTROL_FORBIDDEN = "CLIENT_RETRY_CONTROL_FORBIDDEN"
    PRE_SUBMIT_RETRY_ALLOWED = "PRE_SUBMIT_RETRY_ALLOWED"
    PRE_SUBMIT_BUDGET_EXHAUSTED = "PRE_SUBMIT_BUDGET_EXHAUSTED"
    FIRST_SUBMIT_AUTHORIZED = "FIRST_SUBMIT_AUTHORIZED"
    SUBMIT_TIMEOUT_UNKNOWN_VENDOR = "SUBMIT_TIMEOUT_UNKNOWN_VENDOR"
    PROCESSING_TIMEOUT_CONTINUE_POLL = "PROCESSING_TIMEOUT_CONTINUE_POLL"
    PROCESSING_TIMEOUT_EXHAUSTED = "PROCESSING_TIMEOUT_EXHAUSTED"
    RESULT_TIMEOUT_CONTINUE_FETCH = "RESULT_TIMEOUT_CONTINUE_FETCH"
    RESULT_TIMEOUT_EXHAUSTED = "RESULT_TIMEOUT_EXHAUSTED"
    UNKNOWN_VENDOR_HOLD = "UNKNOWN_VENDOR_HOLD"
    UNKNOWN_VENDOR_RECONCILE = "UNKNOWN_VENDOR_RECONCILE"
    POST_SUBMIT_NO_RETRY = "POST_SUBMIT_NO_RETRY"
    ALREADY_CONSUMED_NO_RETRY = "ALREADY_CONSUMED_NO_RETRY"
    BLIND_PAID_RETRY_FORBIDDEN = "BLIND_PAID_RETRY_FORBIDDEN"
    RECOVERY_REQUIRED_NO_RESUBMIT = "RECOVERY_REQUIRED_NO_RESUBMIT"
    NO_RETRY_DECISION = "NO_RETRY_DECISION"
    SUBMIT_COULD_HAVE_OCCURRED = "SUBMIT_COULD_HAVE_OCCURRED"


class ClientRetryControlError(ValueError):
    """Client attempted to set a retry/timeout budget or force a resubmit."""

    def __init__(self, fields: frozenset[str]) -> None:
        self.fields = fields
        super().__init__(
            "client cannot set retry/timeout budgets or force resubmit: "
            + ", ".join(sorted(fields))
        )


_PRE_SUBMIT_STATES = frozenset(
    {
        WorkerPhase.REQUESTED,
        WorkerPhase.VALIDATED,
        WorkerPhase.CACHE_HIT,
        WorkerPhase.JOINED,
        WorkerPhase.ALLOWANCE_RESERVED,
        WorkerPhase.FAILED_PRE_SUBMIT,
    }
)
_SUBMIT_WINDOW_STATES = frozenset(
    {
        WorkerPhase.SUBMITTING,
        WorkerPhase.SUBMITTED,
    }
)
_PROCESSING_STATES = frozenset(
    {
        WorkerPhase.ACTIVITY_ID_PERSISTED,
        WorkerPhase.PROCESSING,
    }
)
_RESULT_STATES = frozenset(
    {
        WorkerPhase.RESULT_RECEIVED,
        WorkerPhase.NORMALIZED,
        WorkerPhase.CACHED,
    }
)
_TERMINAL_SUCCESS = frozenset(
    {
        WorkerPhase.CACHE_HIT,
        WorkerPhase.JOINED,
        WorkerPhase.CACHED,
        WorkerPhase.CONSUMED,
        WorkerPhase.NORMALIZED,
    }
)
# Durable states that mean a submit may already have left the process.
_SUBMIT_MAY_HAVE_OCCURRED_STATES = frozenset(
    {
        WorkerPhase.SUBMITTING,
        WorkerPhase.SUBMITTED,
        WorkerPhase.ACTIVITY_ID_PERSISTED,
        WorkerPhase.PROCESSING,
        WorkerPhase.RESULT_RECEIVED,
        WorkerPhase.NORMALIZED,
        WorkerPhase.CACHED,
        WorkerPhase.CONSUMED,
        WorkerPhase.FAILED_POST_SUBMIT,
        WorkerPhase.UNKNOWN_VENDOR_STATE,
        WorkerPhase.RECOVERY_REQUIRED,
    }
)


class RetryTimeoutBudget(BaseModel):
    """Operator/server-side budgets. Frozen anti-flags cannot be enabled."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["hva-signal-retry-timeout-v1"] = RETRY_TIMEOUT_POLICY_VERSION
    max_pre_submit_retries: int = Field(default=2, ge=0, le=8)
    max_status_polls: int = Field(default=8, ge=1, le=32)
    max_result_fetches: int = Field(default=3, ge=1, le=16)
    submit_timeout_s: float = Field(default=30.0, gt=0, le=120)
    processing_timeout_s: float = Field(default=120.0, gt=0, le=900)
    result_timeout_s: float = Field(default=30.0, gt=0, le=180)
    automatic_paid_retry: Literal[False] = False
    resubmit_without_activity_id: Literal[False] = False
    client_may_set_budget: Literal[False] = False
    source: Literal["operator_server"] = "operator_server"

    @model_validator(mode="after")
    def _anti_flags_frozen(self) -> RetryTimeoutBudget:
        if self.automatic_paid_retry or self.resubmit_without_activity_id:
            raise ValueError("paid automatic resubmit flags cannot be enabled")
        if self.client_may_set_budget:
            raise ValueError("clients cannot be granted retry-budget control")
        return self


class PolicyContext(BaseModel):
    """Facts the worker already persisted. Not a client request body."""

    model_config = ConfigDict(extra="forbid")

    worker_state: WorkerPhase
    activity_id: str | None = None
    submit_started: bool = False
    timeout_class: TimeoutClass | None = None
    pre_submit_attempts: int = Field(default=0, ge=0)
    poll_count: int = Field(default=0, ge=0)
    result_fetch_count: int = Field(default=0, ge=0)
    reservation_consumed: bool = False
    client_payload: dict[str, Any] | None = None


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RetryAction
    reason_code: ReasonCode
    submit_certainty: SubmitCertainty
    timeout_class: TimeoutClass | None = None
    next_worker_state: WorkerPhase | None = None
    automatic_resubmit: Literal[False] = False
    paid_retry_authorized: Literal[False] = False
    vendor_submit_authorized: bool = False
    reconcile_activity_id: str | None = None
    detail: str = ""


def default_retry_timeout_budget() -> RetryTimeoutBudget:
    return RetryTimeoutBudget()


def operator_budget_from_environ(
    environ: Mapping[str, str] | None = None,
) -> RetryTimeoutBudget:
    """Load budgets from operator env only. Client-looking keys are ignored."""
    src = os.environ if environ is None else environ
    payload: dict[str, Any] = {"source": "operator_server"}
    mapping = {
        OPERATOR_ENV_MAX_PRE_SUBMIT_RETRIES: ("max_pre_submit_retries", int),
        OPERATOR_ENV_MAX_STATUS_POLLS: ("max_status_polls", int),
        OPERATOR_ENV_MAX_RESULT_FETCHES: ("max_result_fetches", int),
        OPERATOR_ENV_SUBMIT_TIMEOUT_S: ("submit_timeout_s", float),
        OPERATOR_ENV_PROCESSING_TIMEOUT_S: ("processing_timeout_s", float),
        OPERATOR_ENV_RESULT_TIMEOUT_S: ("result_timeout_s", float),
    }
    for env_key, (field, caster) in mapping.items():
        raw = src.get(env_key)
        if raw is None or raw == "":
            continue
        payload[field] = caster(raw)
    return RetryTimeoutBudget.model_validate(payload)


def _normalize_field_name(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def collect_client_retry_controls(payload: Any) -> frozenset[str]:
    """Walk a client body / query / header map for forbidden retry controls."""
    hits: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if not isinstance(key, str):
                    walk(value)
                    continue
                normalized = _normalize_field_name(key)
                if normalized in CLIENT_FORBIDDEN_RETRY_FIELDS:
                    hits.add(normalized)
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(payload)
    return frozenset(hits)


def reject_client_retry_controls(payload: Any) -> None:
    hits = collect_client_retry_controls(payload)
    if hits:
        raise ClientRetryControlError(hits)


def resolve_submit_certainty(ctx: PolicyContext) -> SubmitCertainty:
    """Never trust a 'pre-submit' label once submit may have occurred."""
    if ctx.activity_id:
        return SubmitCertainty.CONFIRMED
    if ctx.submit_started:
        return SubmitCertainty.POSSIBLE
    if ctx.worker_state in _SUBMIT_MAY_HAVE_OCCURRED_STATES:
        return SubmitCertainty.POSSIBLE
    return SubmitCertainty.IMPOSSIBLE


def classify_timeout(
    *,
    worker_state: WorkerPhase,
    activity_id: str | None,
    submit_elapsed_s: float | None = None,
    processing_elapsed_s: float | None = None,
    result_elapsed_s: float | None = None,
    budget: RetryTimeoutBudget | None = None,
) -> TimeoutClass | None:
    """Pick at most one timeout class from the current durable phase.

    Submit-timeout applies only while activity_id is unknown.
    Processing-timeout is a poll deadline after activity_id is known.
    Result-timeout is a result-fetch deadline after the vendor reports a result.
    """
    budget = budget or default_retry_timeout_budget()
    if worker_state in _RESULT_STATES or worker_state == WorkerPhase.RESULT_RECEIVED:
        if result_elapsed_s is not None and result_elapsed_s > budget.result_timeout_s:
            return TimeoutClass.RESULT_TIMEOUT
        return None
    if worker_state in _PROCESSING_STATES or activity_id:
        if (
            processing_elapsed_s is not None
            and processing_elapsed_s > budget.processing_timeout_s
            and worker_state not in _PRE_SUBMIT_STATES
        ):
            return TimeoutClass.PROCESSING_TIMEOUT
        if worker_state in _PROCESSING_STATES:
            return None
    if worker_state in _SUBMIT_WINDOW_STATES and not activity_id:
        if submit_elapsed_s is not None and submit_elapsed_s > budget.submit_timeout_s:
            return TimeoutClass.SUBMIT_TIMEOUT
    return None


def next_state_for(decision: PolicyDecision, current: WorkerPhase) -> WorkerPhase:
    if decision.next_worker_state is not None:
        return decision.next_worker_state
    return current


def _decision(
    *,
    action: RetryAction,
    reason: ReasonCode,
    certainty: SubmitCertainty,
    timeout_class: TimeoutClass | None,
    next_state: WorkerPhase | None,
    activity_id: str | None,
    vendor_submit_authorized: bool,
    detail: str,
) -> PolicyDecision:
    if vendor_submit_authorized and action != RetryAction.PROCEED_FIRST_SUBMIT:
        raise RuntimeError("vendor submit is authorized only for the first submit")
    return PolicyDecision(
        action=action,
        reason_code=reason,
        submit_certainty=certainty,
        timeout_class=timeout_class,
        next_worker_state=next_state,
        automatic_resubmit=False,
        paid_retry_authorized=False,
        vendor_submit_authorized=vendor_submit_authorized,
        reconcile_activity_id=activity_id if action in {
            RetryAction.RECONCILE_VIA_ACTIVITY_ID,
            RetryAction.CONTINUE_POLL,
            RetryAction.CONTINUE_RESULT_FETCH,
        } else None,
        detail=detail,
    )


def decide_retry_timeout(
    ctx: PolicyContext,
    budget: RetryTimeoutBudget | None = None,
) -> PolicyDecision:
    """Decide retry / timeout behavior. Never authorizes a paid resubmit."""
    budget = budget or default_retry_timeout_budget()
    if budget.automatic_paid_retry or budget.resubmit_without_activity_id:
        raise RuntimeError("budget anti-flags must stay false")

    if ctx.client_payload is not None:
        hits = collect_client_retry_controls(ctx.client_payload)
        if hits:
            return _decision(
                action=RetryAction.REJECT_CLIENT_CONTROL,
                reason=ReasonCode.CLIENT_RETRY_CONTROL_FORBIDDEN,
                certainty=resolve_submit_certainty(ctx),
                timeout_class=ctx.timeout_class,
                next_state=None,
                activity_id=None,
                vendor_submit_authorized=False,
                detail="client retry/timeout controls are rejected; budgets are operator-only",
            )

    certainty = resolve_submit_certainty(ctx)
    timeout = ctx.timeout_class

    if ctx.worker_state == WorkerPhase.CONSUMED:
        return _decision(
            action=RetryAction.NO_ACTION,
            reason=ReasonCode.ALREADY_CONSUMED_NO_RETRY,
            certainty=certainty,
            timeout_class=timeout,
            next_state=WorkerPhase.CONSUMED,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="job already consumed",
        )

    if ctx.reservation_consumed and certainty != SubmitCertainty.IMPOSSIBLE:
        return _decision(
            action=RetryAction.FAIL_CLOSED_NO_RETRY,
            reason=ReasonCode.ALREADY_CONSUMED_NO_RETRY,
            certainty=certainty,
            timeout_class=timeout,
            next_state=WorkerPhase.FAILED_POST_SUBMIT,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="reservation already consumed; no automatic resubmit",
        )

    if timeout == TimeoutClass.SUBMIT_TIMEOUT:
        return _decision(
            action=RetryAction.HOLD_UNKNOWN,
            reason=ReasonCode.SUBMIT_TIMEOUT_UNKNOWN_VENDOR,
            certainty=SubmitCertainty.POSSIBLE if certainty == SubmitCertainty.IMPOSSIBLE else certainty,
            timeout_class=timeout,
            next_state=WorkerPhase.UNKNOWN_VENDOR_STATE,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="submit-timeout is unknown vendor state; reconcile later via activity_id only",
        )

    if timeout == TimeoutClass.PROCESSING_TIMEOUT:
        if not ctx.activity_id:
            return _decision(
                action=RetryAction.HOLD_UNKNOWN,
                reason=ReasonCode.UNKNOWN_VENDOR_HOLD,
                certainty=certainty,
                timeout_class=timeout,
                next_state=WorkerPhase.RECOVERY_REQUIRED,
                activity_id=None,
                vendor_submit_authorized=False,
                detail="processing-timeout without activity_id cannot resubmit",
            )
        if ctx.poll_count < budget.max_status_polls:
            return _decision(
                action=RetryAction.CONTINUE_POLL,
                reason=ReasonCode.PROCESSING_TIMEOUT_CONTINUE_POLL,
                certainty=SubmitCertainty.CONFIRMED,
                timeout_class=timeout,
                next_state=WorkerPhase.PROCESSING,
                activity_id=ctx.activity_id,
                vendor_submit_authorized=False,
                detail="processing-timeout: continue status poll; never resubmit",
            )
        return _decision(
            action=RetryAction.FAIL_CLOSED_NO_RETRY,
            reason=ReasonCode.PROCESSING_TIMEOUT_EXHAUSTED,
            certainty=SubmitCertainty.CONFIRMED,
            timeout_class=timeout,
            next_state=WorkerPhase.FAILED_POST_SUBMIT,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="processing-timeout poll budget exhausted; fail closed",
        )

    if timeout == TimeoutClass.RESULT_TIMEOUT:
        if ctx.activity_id and ctx.result_fetch_count < budget.max_result_fetches:
            return _decision(
                action=RetryAction.CONTINUE_RESULT_FETCH,
                reason=ReasonCode.RESULT_TIMEOUT_CONTINUE_FETCH,
                certainty=SubmitCertainty.CONFIRMED,
                timeout_class=timeout,
                next_state=WorkerPhase.RESULT_RECEIVED,
                activity_id=ctx.activity_id,
                vendor_submit_authorized=False,
                detail="result-timeout: retry result fetch only; never resubmit",
            )
        return _decision(
            action=RetryAction.FAIL_CLOSED_NO_RETRY,
            reason=ReasonCode.RESULT_TIMEOUT_EXHAUSTED,
            certainty=certainty if ctx.activity_id else SubmitCertainty.POSSIBLE,
            timeout_class=timeout,
            next_state=WorkerPhase.FAILED_POST_SUBMIT,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="result-timeout fetch budget exhausted; fail closed",
        )

    if ctx.worker_state == WorkerPhase.UNKNOWN_VENDOR_STATE:
        if ctx.activity_id:
            return _decision(
                action=RetryAction.RECONCILE_VIA_ACTIVITY_ID,
                reason=ReasonCode.UNKNOWN_VENDOR_RECONCILE,
                certainty=SubmitCertainty.CONFIRMED,
                timeout_class=timeout,
                next_state=WorkerPhase.PROCESSING,
                activity_id=ctx.activity_id,
                vendor_submit_authorized=False,
                detail="UNKNOWN_VENDOR_STATE with activity_id: poll/fetch only",
            )
        return _decision(
            action=RetryAction.HOLD_UNKNOWN,
            reason=ReasonCode.UNKNOWN_VENDOR_HOLD,
            certainty=SubmitCertainty.POSSIBLE,
            timeout_class=timeout,
            next_state=WorkerPhase.RECOVERY_REQUIRED,
            activity_id=None,
            vendor_submit_authorized=False,
            detail="UNKNOWN_VENDOR_STATE without activity_id: operator reconcile, never resubmit",
        )

    if ctx.worker_state == WorkerPhase.RECOVERY_REQUIRED:
        if ctx.activity_id:
            return _decision(
                action=RetryAction.RECONCILE_VIA_ACTIVITY_ID,
                reason=ReasonCode.UNKNOWN_VENDOR_RECONCILE,
                certainty=SubmitCertainty.CONFIRMED,
                timeout_class=timeout,
                next_state=WorkerPhase.PROCESSING,
                activity_id=ctx.activity_id,
                vendor_submit_authorized=False,
                detail="RECOVERY_REQUIRED with activity_id: reconcile only",
            )
        return _decision(
            action=RetryAction.HOLD_UNKNOWN,
            reason=ReasonCode.RECOVERY_REQUIRED_NO_RESUBMIT,
            certainty=SubmitCertainty.POSSIBLE,
            timeout_class=timeout,
            next_state=WorkerPhase.RECOVERY_REQUIRED,
            activity_id=None,
            vendor_submit_authorized=False,
            detail="RECOVERY_REQUIRED: no automatic resubmit",
        )

    if ctx.worker_state == WorkerPhase.FAILED_POST_SUBMIT:
        return _decision(
            action=RetryAction.FAIL_CLOSED_NO_RETRY,
            reason=ReasonCode.POST_SUBMIT_NO_RETRY,
            certainty=certainty,
            timeout_class=timeout,
            next_state=WorkerPhase.FAILED_POST_SUBMIT,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="FAILED_POST_SUBMIT is terminal for automatic retry",
        )

    if certainty != SubmitCertainty.IMPOSSIBLE and ctx.worker_state == WorkerPhase.FAILED_PRE_SUBMIT:
        return _decision(
            action=RetryAction.HOLD_UNKNOWN,
            reason=ReasonCode.SUBMIT_COULD_HAVE_OCCURRED,
            certainty=certainty,
            timeout_class=timeout,
            next_state=WorkerPhase.UNKNOWN_VENDOR_STATE,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="claimed FAILED_PRE_SUBMIT but submit could have occurred; hold, do not retry",
        )

    if ctx.worker_state == WorkerPhase.FAILED_PRE_SUBMIT:
        if ctx.pre_submit_attempts < budget.max_pre_submit_retries:
            return _decision(
                action=RetryAction.RETRY_PRE_SUBMIT,
                reason=ReasonCode.PRE_SUBMIT_RETRY_ALLOWED,
                certainty=SubmitCertainty.IMPOSSIBLE,
                timeout_class=timeout,
                next_state=WorkerPhase.REQUESTED,
                activity_id=None,
                vendor_submit_authorized=False,
                detail="pre-submit failure with no possible submit; re-enter before reserve/submit",
            )
        return _decision(
            action=RetryAction.FAIL_CLOSED_NO_RETRY,
            reason=ReasonCode.PRE_SUBMIT_BUDGET_EXHAUSTED,
            certainty=SubmitCertainty.IMPOSSIBLE,
            timeout_class=timeout,
            next_state=WorkerPhase.FAILED_PRE_SUBMIT,
            activity_id=None,
            vendor_submit_authorized=False,
            detail="pre-submit retry budget exhausted",
        )

    if ctx.worker_state in _SUBMIT_WINDOW_STATES and not ctx.activity_id:
        return _decision(
            action=RetryAction.HOLD_UNKNOWN,
            reason=ReasonCode.SUBMIT_COULD_HAVE_OCCURRED,
            certainty=SubmitCertainty.POSSIBLE,
            timeout_class=timeout,
            next_state=WorkerPhase.UNKNOWN_VENDOR_STATE,
            activity_id=None,
            vendor_submit_authorized=False,
            detail="submit window without activity_id is unknown; never automatic resubmit",
        )

    if ctx.activity_id and ctx.worker_state in {
        WorkerPhase.SUBMITTED,
        WorkerPhase.ACTIVITY_ID_PERSISTED,
        WorkerPhase.PROCESSING,
    }:
        return _decision(
            action=RetryAction.RECONCILE_VIA_ACTIVITY_ID,
            reason=ReasonCode.UNKNOWN_VENDOR_RECONCILE,
            certainty=SubmitCertainty.CONFIRMED,
            timeout_class=timeout,
            next_state=WorkerPhase.PROCESSING,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="known activity_id: resume poll/result; never a second submit",
        )

    if (
        ctx.worker_state == WorkerPhase.ALLOWANCE_RESERVED
        and certainty == SubmitCertainty.IMPOSSIBLE
    ):
        return _decision(
            action=RetryAction.PROCEED_FIRST_SUBMIT,
            reason=ReasonCode.FIRST_SUBMIT_AUTHORIZED,
            certainty=SubmitCertainty.IMPOSSIBLE,
            timeout_class=timeout,
            next_state=WorkerPhase.SUBMITTING,
            activity_id=None,
            vendor_submit_authorized=True,
            detail="first submit only; not a retry",
        )

    if ctx.worker_state in _TERMINAL_SUCCESS:
        return _decision(
            action=RetryAction.NO_ACTION,
            reason=ReasonCode.NO_RETRY_DECISION,
            certainty=certainty,
            timeout_class=timeout,
            next_state=ctx.worker_state,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="terminal or joined state; no retry",
        )

    if certainty != SubmitCertainty.IMPOSSIBLE:
        return _decision(
            action=RetryAction.HOLD_UNKNOWN,
            reason=ReasonCode.BLIND_PAID_RETRY_FORBIDDEN,
            certainty=certainty,
            timeout_class=timeout,
            next_state=WorkerPhase.UNKNOWN_VENDOR_STATE,
            activity_id=ctx.activity_id,
            vendor_submit_authorized=False,
            detail="blind paid retry forbidden",
        )

    return _decision(
        action=RetryAction.NO_ACTION,
        reason=ReasonCode.NO_RETRY_DECISION,
        certainty=certainty,
        timeout_class=timeout,
        next_state=ctx.worker_state,
        activity_id=None,
        vendor_submit_authorized=False,
        detail="no retry/timeout action; LIVE-C owns the happy path",
    )
