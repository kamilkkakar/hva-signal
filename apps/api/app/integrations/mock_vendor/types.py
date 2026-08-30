"""Provider-neutral mock vendor types. Not a public / OpenAPI contract.

Never an HTTP payload. Never a FortyGuard document.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.signals import ThermalSignalKind
from app.services.snapshot_identity import require_requested_hour

MOCK_VENDOR_KIND: Literal["mock"] = "mock"
MOCK_VENDOR_REQUEST_SPEC_VERSION = "hva-signal-mock-vendor-request-v1"
MOCK_ACTIVITY_CONTRACT_VERSION = "hva-signal-mock-vendor-activity-v1"


class LifecyclePhase(str, Enum):
    """Explicit hosted-live mock phases. UNKNOWN never auto-resubmits."""

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


class RestartAction(str, Enum):
    SUBMIT_ALLOWED = "submit_allowed"
    RESUME_POLL = "resume_poll"
    NO_RESUBMIT_UNCERTAIN = "no_resubmit_uncertain"
    NO_RESUBMIT_ALREADY_SPENT = "no_resubmit_already_spent"
    REUSE_CACHE = "reuse_cache"
    RELEASE_AND_STOP = "release_and_stop"


class MockVendorRequest(BaseModel):
    """Would-be vendor document. Mock only. Never sent on a wire."""

    model_config = ConfigDict(extra="forbid")

    spec_version: Literal["hva-signal-mock-vendor-request-v1"] = (
        MOCK_VENDOR_REQUEST_SPEC_VERSION
    )
    vendor_kind: Literal["mock"] = MOCK_VENDOR_KIND
    signal_kind: ThermalSignalKind = ThermalSignalKind.SELECTED_TIME_SNAPSHOT
    area_id: str = Field(min_length=1)
    request_fingerprint: str = Field(min_length=16)
    geometry_sha256: str = Field(min_length=16)
    target_timestamp: datetime
    timezone: str = Field(min_length=1)
    analytic: Literal["tcm"] = "tcm"
    granularity_m: Literal[100] = 100
    temporal_mode: Literal["single_hour"] = "single_hour"
    planned_units: int = Field(default=1, gt=0, le=1)

    @field_validator("target_timestamp")
    @classmethod
    def _requested_hour(cls, value: datetime) -> datetime:
        return require_requested_hour(value)

    @field_validator("signal_kind")
    @classmethod
    def _signal_b_only(cls, value: ThermalSignalKind) -> ThermalSignalKind:
        if value != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            raise ValueError("mock vendor spec is Signal B only")
        return value

    @field_validator("vendor_kind")
    @classmethod
    def _mock_only(cls, value: str) -> str:
        if value != MOCK_VENDOR_KIND:
            raise ValueError("mock vendor refuses non-mock vendor_kind")
        return value


class MockActivityRecord(BaseModel):
    """Crash-safe handle. activity_id is the only resume token after submit."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-mock-vendor-activity-v1"] = (
        MOCK_ACTIVITY_CONTRACT_VERSION
    )
    record_id: str
    job_id: str
    request_fingerprint: str
    geometry_sha256: str
    reservation_id: str
    vendor_kind: Literal["mock"] = MOCK_VENDOR_KIND
    vendor_activity_id: str | None = None
    phase: LifecyclePhase = LifecyclePhase.REQUESTED
    submit_attempted: bool = False
    notes: list[str] = Field(default_factory=list)
    durability: Literal["J0_PROCESS_LOCAL_NOT_DURABLE"] = "J0_PROCESS_LOCAL_NOT_DURABLE"


class MockLifecycleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal[
        "ready",
        "joined",
        "reused",
        "denied",
        "crashed",
        "uncertain",
        "timed_out",
        "failed",
        "no_resubmit",
    ]
    phase: LifecyclePhase
    job_id: str | None = None
    reservation_id: str | None = None
    reservation_state: str | None = None
    activity_record_id: str | None = None
    vendor_activity_id: str | None = None
    restart_action: str | None = None
    signal_availability: str | None = None
    vendor_submit_count: int = 0
    vendor_paid_submit_count: int = 0
    vendor_poll_count: int = 0
    snapshot_valid_zone_count: int | None = None
    visited_crash_points: list[str] = Field(default_factory=list)
    reason: str | None = None
    cache_hit: bool = False


class MockVendorStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["processing", "succeeded", "unknown"]
    activity_id: str
    result: dict[str, Any] | None = None
    fingerprint: str | None = None
