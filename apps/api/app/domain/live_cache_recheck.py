"""LIVE-H cache-recheck contract. Provider-neutral. No vendor types.

CACHE_HIT is cheaper than a reservation. Consume happens only after a
normalized result is cached. Client cache-bust and client cache writes
are never authorization.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CACHE_RECHECK_CONTRACT_VERSION = "hva-signal-live-h-cache-recheck-v1"


class RecheckPoint(str, Enum):
    """Mandatory cache lookups immediately before spend-side actions."""

    BEFORE_RESERVE = "BEFORE_RESERVE"
    BEFORE_SUBMIT = "BEFORE_SUBMIT"


class CacheRecheckCode(str, Enum):
    CACHE_HIT = "CACHE_HIT"
    CACHE_MISS = "CACHE_MISS"
    REJECTED_POISON = "REJECTED_POISON"
    REJECTED_CACHE_BUST = "REJECTED_CACHE_BUST"
    REJECTED_UNAUTHENTICATED = "REJECTED_UNAUTHENTICATED"
    REJECTED_INTEGRITY = "REJECTED_INTEGRITY"
    REJECTED_IDENTITY = "REJECTED_IDENTITY"


class LiveCachePhase(str, Enum):
    """Phases LIVE-H owns on the post-result / pre-spend path.

    LIVE-C owns the full worker state machine. These values are the subset
    that cache recheck and crash recovery must distinguish.
    """

    VALIDATED = "VALIDATED"
    CACHE_HIT = "CACHE_HIT"
    ALLOWANCE_RESERVED = "ALLOWANCE_RESERVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    NORMALIZED = "NORMALIZED"
    CACHED = "CACHED"
    CONSUMED = "CONSUMED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    FAILED_PRE_SUBMIT = "FAILED_PRE_SUBMIT"


class CrashAfter(str, Enum):
    """Injectable crash points for recovery tests. Not a public API."""

    RESULT = "result"
    NORMALIZE = "normalize"
    CACHE = "cache"


class CacheRecheckError(ValueError):
    """Rejected cache write, bust, or identity bind."""

    def __init__(self, code: CacheRecheckCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class FingerprintCacheRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-live-h-cache-recheck-v1"] = (
        CACHE_RECHECK_CONTRACT_VERSION
    )
    request_fingerprint: str
    geometry_sha256: str
    area_id: str
    payload: dict[str, Any]
    integrity_sha256: str
    cached_at: datetime
    writer: Literal["worker"] = "worker"


class NormalizedLiveResult(BaseModel):
    """Identity-bound, secret-stripped result ready to cache."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-live-h-cache-recheck-v1"] = (
        CACHE_RECHECK_CONTRACT_VERSION
    )
    request_fingerprint: str
    geometry_sha256: str
    area_id: str
    payload: dict[str, Any]
    integrity_sha256: str


class CacheRecheckDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: CacheRecheckCode
    point: RecheckPoint
    record: FingerprintCacheRecord | None = None
    joined_job_id: str | None = None
    released_reservation_id: str | None = None
    submit_allowed: bool = False
    reserve_allowed: bool = False


class LiveCacheJob(BaseModel):
    """Process-local durable-enough job for LIVE-H recovery tests."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    phase: LiveCachePhase
    request_fingerprint: str
    geometry_sha256: str
    area_id: str
    reservation_id: str | None = None
    planned_units: int = Field(default=1, gt=0)
    submit_count: int = Field(default=0, ge=0)
    raw_result: dict[str, Any] | None = None
    normalized: NormalizedLiveResult | None = None
    cached_integrity: str | None = None
    consumed: bool = False
    recovery_required: bool = False
    last_error: str | None = None
