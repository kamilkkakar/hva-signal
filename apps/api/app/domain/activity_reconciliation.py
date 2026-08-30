"""Canonical J3/J4 live-phase vocabulary.

LIVE-D owns this type. Copied into the LIVE-C worktree because worktrees
cannot import each other. Members and values MUST stay identical to
`hackathon-live-d-activity/apps/api/app/domain/activity_reconciliation.py`.

LIVE-C must not fork a second 17-state enum. On merge, LIVE-D's full
reconciliation module replaces this enum-only copy.

Not a public / OpenAPI type. No FortyGuard. No real vendor I/O.
"""

from __future__ import annotations

from enum import Enum


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
