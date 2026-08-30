"""J3/J4 durable-live persistence types.

LIVE-C owns worker transitions. This module only names states the SQLite
store may persist and classify on restart. Enabling SQLite never enables
a live vendor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class PersistenceError(ValueError):
    """Illegal durable write or acknowledgement."""


class LiveWorkerState(str, Enum):
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


RECOVERY_QUERY_STATES = frozenset(
    {
        LiveWorkerState.SUBMITTING,
        LiveWorkerState.SUBMITTED,
        LiveWorkerState.UNKNOWN_VENDOR_STATE,
        LiveWorkerState.RECOVERY_REQUIRED,
    }
)

_ACTIVITY_BOUND_IN_FLIGHT = frozenset(
    {
        LiveWorkerState.SUBMITTED,
        LiveWorkerState.ACTIVITY_ID_PERSISTED,
        LiveWorkerState.PROCESSING,
        LiveWorkerState.RESULT_RECEIVED,
        LiveWorkerState.NORMALIZED,
        LiveWorkerState.CACHED,
    }
)

_KEEP_AS_IS = frozenset(
    {
        LiveWorkerState.CACHE_HIT,
        LiveWorkerState.JOINED,
        LiveWorkerState.CONSUMED,
        LiveWorkerState.FAILED_PRE_SUBMIT,
        LiveWorkerState.FAILED_POST_SUBMIT,
        LiveWorkerState.UNKNOWN_VENDOR_STATE,
        LiveWorkerState.RECOVERY_REQUIRED,
    }
)

_PRE_SUBMIT = frozenset(
    {
        LiveWorkerState.REQUESTED,
        LiveWorkerState.VALIDATED,
    }
)


class RestartAction(str, Enum):
    KEEP = "KEEP"
    INTERRUPT_LEGACY = "INTERRUPT_LEGACY"
    INTERRUPT_PRE_SUBMIT = "INTERRUPT_PRE_SUBMIT"
    MARK_UNKNOWN_VENDOR = "MARK_UNKNOWN_VENDOR"
    MARK_RECOVERY_REQUIRED = "MARK_RECOVERY_REQUIRED"


@dataclass(frozen=True)
class DurableJobRecord:
    job_id: str
    worker_state: LiveWorkerState | None
    fingerprint: str | None
    activity_id: str | None
    reservation_id: str | None
    error_class: str | None
    recovery_required: bool
    public_status: str | None
    auto_resubmit: Literal[False] = False


@dataclass(frozen=True)
class DurableAck:
    """Returned only after COMMIT. Callers must not ACK earlier."""

    job_id: str
    worker_state: LiveWorkerState
    activity_id: str | None
    reservation_id: str | None
    acknowledged_status: str
    committed: Literal[True] = True


def require_commit_before_ack(
    *,
    activity_id: str | None,
    reservation_id: str | None,
    acknowledged_status: str,
) -> None:
    """SUBMITTED / ACTIVITY_ID_PERSISTED require both ids in the same commit."""
    if acknowledged_status not in {"SUBMITTED", "ACTIVITY_ID_PERSISTED"}:
        raise PersistenceError(f"unsupported acknowledgement {acknowledged_status}")
    if not activity_id or not str(activity_id).strip():
        raise PersistenceError(
            f"cannot acknowledge {acknowledged_status} without committed activity_id"
        )
    if not reservation_id or not str(reservation_id).strip():
        raise PersistenceError(
            f"cannot acknowledge {acknowledged_status} without committed reservation_id"
        )


def classify_restart(record: DurableJobRecord) -> RestartAction:
    """Restart classification. Never returns an auto-resubmit action."""
    if record.worker_state is None:
        return RestartAction.INTERRUPT_LEGACY
    if record.worker_state in _KEEP_AS_IS:
        return RestartAction.KEEP
    if record.worker_state in _PRE_SUBMIT:
        return RestartAction.INTERRUPT_PRE_SUBMIT
    if record.worker_state == LiveWorkerState.ALLOWANCE_RESERVED:
        return RestartAction.MARK_RECOVERY_REQUIRED
    if record.worker_state == LiveWorkerState.SUBMITTING:
        if record.activity_id:
            return RestartAction.MARK_RECOVERY_REQUIRED
        return RestartAction.MARK_UNKNOWN_VENDOR
    if record.worker_state in _ACTIVITY_BOUND_IN_FLIGHT:
        if record.activity_id:
            return RestartAction.MARK_RECOVERY_REQUIRED
        return RestartAction.MARK_UNKNOWN_VENDOR
    return RestartAction.MARK_RECOVERY_REQUIRED


def resulting_worker_state(
    record: DurableJobRecord, action: RestartAction
) -> LiveWorkerState | None:
    if action == RestartAction.KEEP:
        return record.worker_state
    if action == RestartAction.INTERRUPT_LEGACY:
        return None
    if action == RestartAction.INTERRUPT_PRE_SUBMIT:
        return LiveWorkerState.FAILED_PRE_SUBMIT
    if action == RestartAction.MARK_UNKNOWN_VENDOR:
        return LiveWorkerState.UNKNOWN_VENDOR_STATE
    return LiveWorkerState.RECOVERY_REQUIRED
