"""LIVE-N hosted-live adversarial guards. Mock/policy only. No vendor I/O.

Best-effort at-most-one-submit defense. Not mathematical exactly-once.
UNKNOWN_VENDOR_STATE never becomes an automatic resubmit.
"""

from __future__ import annotations

from enum import Enum
from threading import Lock
from typing import Any, Iterable, Mapping
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.domain.client_privilege import (
    CLIENT_CACHE_BUST_FIELDS,
    CLIENT_NEVER_SET_FIELDS,
    CLIENT_PRIVILEGE_HEADERS,
    HOSTED_LIVE_ENABLE_FIELDS,
)
from app.domain.demo_allowance import DemoRequestIdentity, ReservationState
from app.services.demo_allowance_ledger import (
    DemoAllowanceError,
    InMemoryDemoAllowanceLedger,
)
from app.services.spend_gate import ExecutionGateResult


class ClientPrivilegeError(ValueError):
    """Client attempted to set a server-only spend, live, or recovery field."""

    def __init__(self, hits: Iterable[str]) -> None:
        self.hits = tuple(sorted(set(hits)))
        super().__init__(
            "client cannot set server-only fields: " + ", ".join(self.hits)
        )


class ForgedActivityError(ValueError):
    """Client-minted or cross-job activity_id is not a vendor handle."""


class ReservationStealError(DemoAllowanceError):
    """Reservation id from a client surface cannot be consumed."""


class ForcedResubmitError(ValueError):
    """UNKNOWN_VENDOR_STATE / paid-retry cannot be forced into a second submit."""


class RecoveryAction(str, Enum):
    RECONCILE_ONLY = "RECONCILE_ONLY"
    RESUME_POLL = "RESUME_POLL"
    REFUSE_RESUBMIT = "REFUSE_RESUBMIT"
    PRE_SUBMIT_RETRY_OK = "PRE_SUBMIT_RETRY_OK"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class WorkerRecoveryState(str, Enum):
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    ACTIVITY_ID_PERSISTED = "ACTIVITY_ID_PERSISTED"
    PROCESSING = "PROCESSING"
    UNKNOWN_VENDOR_STATE = "UNKNOWN_VENDOR_STATE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    FAILED_PRE_SUBMIT = "FAILED_PRE_SUBMIT"
    FAILED_POST_SUBMIT = "FAILED_POST_SUBMIT"
    CONSUMED = "CONSUMED"


class ActivityBinding(BaseModel):
    """Server-minted activity handle. Never accepted from a client payload."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str
    request_fingerprint: str
    reservation_id: str | None = None
    minted_by: str = Field(default="server_vendor_adapter")


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RecoveryAction
    may_submit: bool
    reason: str


def normalize_client_key(name: str) -> str:
    folded = str(name).strip().lower().replace("-", "_")
    if folded.startswith("x_"):
        return folded[2:]
    return folded


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, inner in value.items():
            found.add(str(key))
            found.update(_walk_keys(inner))
    elif isinstance(value, list):
        for item in value:
            found.update(_walk_keys(item))
    return found


def privilege_hits_in_mapping(payload: Mapping[str, Any] | None) -> list[str]:
    if not payload:
        return []
    hits: set[str] = set()
    for key in _walk_keys(payload):
        normalized = normalize_client_key(key)
        if normalized in CLIENT_NEVER_SET_FIELDS or key.lower() in CLIENT_NEVER_SET_FIELDS:
            hits.add(normalized)
    return sorted(hits)


def privilege_hits_in_headers(headers: Mapping[str, Any] | None) -> list[str]:
    if not headers:
        return []
    hits: set[str] = set()
    for raw_key in headers:
        folded = str(raw_key).strip().lower()
        if folded in CLIENT_PRIVILEGE_HEADERS:
            hits.add(normalize_client_key(folded))
            continue
        normalized = normalize_client_key(folded)
        if normalized in CLIENT_NEVER_SET_FIELDS:
            hits.add(normalized)
    return sorted(hits)


def scan_client_surfaces(
    *,
    body: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    headers: Mapping[str, Any] | None = None,
) -> list[str]:
    """Union of privilege hits on body, query, and headers."""
    hits = set(privilege_hits_in_mapping(body))
    hits.update(privilege_hits_in_mapping(query))
    hits.update(privilege_hits_in_headers(headers))
    return sorted(hits)


def reject_client_privilege_surfaces(
    *,
    body: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    headers: Mapping[str, Any] | None = None,
) -> None:
    hits = scan_client_surfaces(body=body, query=query, headers=headers)
    if hits:
        raise ClientPrivilegeError(hits)


def client_tried_to_enable_hosted_live(
    *,
    body: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    headers: Mapping[str, Any] | None = None,
) -> bool:
    hits = set(scan_client_surfaces(body=body, query=query, headers=headers))
    return bool(hits.intersection(HOSTED_LIVE_ENABLE_FIELDS))


def hosted_live_defaults_remain_off(settings: Settings | None = None) -> bool:
    """Field defaults — not a client header — keep hosted live closed."""
    if settings is None:
        fields = Settings.model_fields
        return (
            fields["demo_allowance_enabled"].default is False
            and int(fields["demo_allowance_max_total_units"].default) == 0
        )
    return (
        bool(settings.demo_allowance_enabled) is False
        and int(settings.demo_allowance_max_total_units) == 0
    )


def cache_bust_hits(payload: Mapping[str, Any] | None) -> list[str]:
    if not payload:
        return []
    hits = {
        normalize_client_key(key)
        for key in _walk_keys(payload)
        if normalize_client_key(key) in CLIENT_CACHE_BUST_FIELDS
    }
    return sorted(hits)


def reject_cache_bust(payload: Mapping[str, Any] | None) -> None:
    hits = cache_bust_hits(payload)
    if hits:
        raise ClientPrivilegeError(hits)


class ServerActivityRegistry:
    """In-process activity_id bindings. Client cannot mint or steal handles."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, ActivityBinding] = {}
        self._by_fingerprint: dict[str, str] = {}

    def mint(
        self,
        *,
        request_fingerprint: str,
        reservation_id: str | None = None,
    ) -> ActivityBinding:
        with self._lock:
            existing_id = self._by_fingerprint.get(request_fingerprint)
            if existing_id is not None:
                return self._by_id[existing_id]
            binding = ActivityBinding(
                activity_id=f"act_{uuid4().hex[:16]}",
                request_fingerprint=request_fingerprint,
                reservation_id=reservation_id,
            )
            self._by_id[binding.activity_id] = binding
            self._by_fingerprint[request_fingerprint] = binding.activity_id
            return binding

    def lookup(
        self,
        activity_id: str,
        *,
        request_fingerprint: str,
    ) -> ActivityBinding:
        with self._lock:
            binding = self._by_id.get(activity_id)
            if binding is None:
                raise ForgedActivityError("unknown_activity_id")
            if binding.request_fingerprint != request_fingerprint:
                raise ForgedActivityError("activity_fingerprint_mismatch")
            return binding

    def reject_client_claimed_id(
        self,
        claimed: str | None,
        *,
        request_fingerprint: str,
    ) -> None:
        if claimed is None:
            return
        with self._lock:
            binding = self._by_id.get(claimed)
            if binding is None:
                raise ForgedActivityError("client_forged_activity_id")
            if binding.request_fingerprint != request_fingerprint:
                raise ForgedActivityError("activity_steal_denied")


def consume_server_reservation(
    ledger: InMemoryDemoAllowanceLedger,
    *,
    reservation_id: str,
    identity: DemoRequestIdentity,
    planned_units: int,
    client_supplied_reservation_id: bool,
    now=None,
):
    """Worker consume. A client-echoed reservation_id is never authority."""
    if client_supplied_reservation_id:
        raise ReservationStealError("client_supplied_reservation_id")
    return ledger.consume(
        reservation_id,
        identity=identity,
        planned_units=planned_units,
        now=now,
    )


def steal_reservation_result(
    ledger: InMemoryDemoAllowanceLedger,
    *,
    victim_reservation_id: str,
    attacker_identity: DemoRequestIdentity,
    planned_units: int,
    now=None,
) -> ExecutionGateResult:
    """Attack helper: attacker presents victim reservation_id with own identity."""
    try:
        consume_server_reservation(
            ledger,
            reservation_id=victim_reservation_id,
            identity=attacker_identity,
            planned_units=planned_units,
            client_supplied_reservation_id=True,
            now=now,
        )
    except ReservationStealError as exc:
        return ExecutionGateResult(allowed=False, reason=str(exc))
    except DemoAllowanceError as exc:
        return ExecutionGateResult(allowed=False, reason=str(exc))
    return ExecutionGateResult(allowed=True, reason="unexpected_steal_success")


def decide_unknown_vendor_recovery(
    *,
    state: WorkerRecoveryState,
    activity_id: str | None,
    client_force_resubmit: bool,
    submit_could_have_occurred: bool,
) -> RecoveryDecision:
    """At-most-one-submit policy. Never claim vendor exactly-once."""
    if client_force_resubmit:
        return RecoveryDecision(
            action=RecoveryAction.REFUSE_RESUBMIT,
            may_submit=False,
            reason="client_cannot_force_resubmit",
        )
    if state == WorkerRecoveryState.UNKNOWN_VENDOR_STATE:
        return RecoveryDecision(
            action=RecoveryAction.RECONCILE_ONLY
            if activity_id
            else RecoveryAction.RECOVERY_REQUIRED,
            may_submit=False,
            reason="unknown_vendor_state_never_auto_resubmits",
        )
    if state == WorkerRecoveryState.RECOVERY_REQUIRED:
        return RecoveryDecision(
            action=RecoveryAction.RECOVERY_REQUIRED,
            may_submit=False,
            reason="operator_reconcile_only",
        )
    if state in {
        WorkerRecoveryState.SUBMITTED,
        WorkerRecoveryState.ACTIVITY_ID_PERSISTED,
        WorkerRecoveryState.PROCESSING,
        WorkerRecoveryState.FAILED_POST_SUBMIT,
        WorkerRecoveryState.CONSUMED,
    }:
        return RecoveryDecision(
            action=RecoveryAction.RESUME_POLL
            if activity_id
            else RecoveryAction.RECONCILE_ONLY,
            may_submit=False,
            reason="post_submit_reconcile_only",
        )
    if state == WorkerRecoveryState.FAILED_PRE_SUBMIT and not submit_could_have_occurred:
        return RecoveryDecision(
            action=RecoveryAction.PRE_SUBMIT_RETRY_OK,
            may_submit=True,
            reason="pre_submit_no_submit_could_have_occurred",
        )
    if state == WorkerRecoveryState.SUBMITTING and submit_could_have_occurred:
        return RecoveryDecision(
            action=RecoveryAction.RECONCILE_ONLY,
            may_submit=False,
            reason="submit_window_is_unknown_do_not_resubmit",
        )
    return RecoveryDecision(
        action=RecoveryAction.REFUSE_RESUBMIT,
        may_submit=False,
        reason="fail_closed",
    )


def paid_retry_allowed(
    *,
    state: WorkerRecoveryState,
    submit_could_have_occurred: bool,
    reservation_state: ReservationState | None,
    client_requested_retry: bool,
) -> bool:
    if client_requested_retry:
        return False
    if reservation_state == ReservationState.CONSUMED:
        return False
    if submit_could_have_occurred:
        return False
    if state in {
        WorkerRecoveryState.UNKNOWN_VENDOR_STATE,
        WorkerRecoveryState.RECOVERY_REQUIRED,
        WorkerRecoveryState.SUBMITTED,
        WorkerRecoveryState.ACTIVITY_ID_PERSISTED,
        WorkerRecoveryState.PROCESSING,
        WorkerRecoveryState.FAILED_POST_SUBMIT,
        WorkerRecoveryState.CONSUMED,
    }:
        return False
    return (
        state == WorkerRecoveryState.FAILED_PRE_SUBMIT and not submit_could_have_occurred
    )
