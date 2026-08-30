"""Durable worker states, crash points, and recovery actions.

These states are the J3/J4 contract. Production ExecutionState is still
NOT_STARTED / RUNNING / FINISHED / INTERRUPTED — a documented gap.
"""

from __future__ import annotations

from enum import Enum


class DurableWorkerState(str, Enum):
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


DURABLE_WORKER_STATES: tuple[DurableWorkerState, ...] = tuple(DurableWorkerState)


class CrashPoint(str, Enum):
    """The nine LIVE-E crash points. Order is pipeline order."""

    BEFORE_RESERVE = "before_reserve"
    AFTER_RESERVE = "after_reserve"
    BEFORE_VENDOR_SUBMIT = "before_vendor_submit"
    DURING_SUBMIT = "during_submit"
    AFTER_SUBMIT_BEFORE_ACTIVITY_ID = "after_submit_before_activity_id"
    AFTER_ACTIVITY_ID_SAVE = "after_activity_id_save"
    DURING_VENDOR_PROCESSING = "during_vendor_processing"
    AFTER_RESULT_BEFORE_CACHE = "after_result_before_cache"
    AFTER_CACHE_BEFORE_CONSUME = "after_cache_before_allowance_consume"


CRASH_POINTS: tuple[CrashPoint, ...] = tuple(CrashPoint)


class RecoveryAction(str, Enum):
    CONTINUE_FROM_CACHE_CHECK = "continue_from_cache_check"
    CONTINUE_TO_SUBMIT = "continue_to_submit"
    RESUME_POLL = "resume_poll"
    CACHE_THEN_CONSUME = "cache_then_consume"
    CONSUME_ONLY = "consume_only"
    REUSE_CACHE = "reuse_cache"
    JOIN_IN_FLIGHT = "join_in_flight"
    RELEASE_AND_MAY_RETRY_PRE_SUBMIT = "release_and_may_retry_pre_submit"
    NO_AUTOMATIC_RESUBMIT = "no_automatic_resubmit"
    OPERATOR_RECONCILE = "operator_reconcile"


class SpendRisk(str, Enum):
    NONE = "none"
    RESERVATION_HELD = "reservation_held"
    UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED = "unknown_vendor_may_have_accepted"
    VENDOR_ACCEPTED_HANDLE_LOST = "vendor_accepted_handle_lost"
    VENDOR_IN_FLIGHT = "vendor_in_flight"
    RESULT_UNPROTECTED = "result_unprotected"
    CACHE_WITHOUT_CONSUME = "cache_without_consume"
    ALREADY_SPENT = "already_spent"
