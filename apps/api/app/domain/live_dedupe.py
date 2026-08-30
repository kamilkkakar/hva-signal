"""LIVE-G join/dedupe contract for live Signal B submit.

This module does not own the full J3/J4 worker state machine. It owns
fingerprint-join outcomes and the honest at-most-one-submit claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


LIVE_JOIN_CONTRACT_VERSION = "hva-signal-live-join-v1"
# Vendor-submit join key is the existing Signal B snapshot identity — not a fork.
LIVE_SUBMIT_FINGERPRINT_VERSION = "hva-signal-b-snapshot-identity-v1"


class LiveJoinOutcome(str, Enum):
    """What this request did on the submit path."""

    CACHE_HIT = "CACHE_HIT"
    JOINED = "JOINED"
    LEADER = "LEADER"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class LiveJoinPhase(str, Enum):
    """Coordinator-local phases on the reserve+submit path."""

    OPEN = "OPEN"
    ALLOWANCE_RESERVED = "ALLOWANCE_RESERVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    ACTIVITY_ID_PERSISTED = "ACTIVITY_ID_PERSISTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED_PRE_SUBMIT = "FAILED_PRE_SUBMIT"
    FAILED_POST_SUBMIT = "FAILED_POST_SUBMIT"
    UNKNOWN_VENDOR_STATE = "UNKNOWN_VENDOR_STATE"


class LiveAcquireRequest(BaseModel):
    """Inputs that define a live B acquire. Client nonce is not a join field."""

    model_config = ConfigDict(extra="forbid")

    area_id: str
    geometry_sha256: str
    zone_geometry_version: str
    target_timestamp: datetime
    timezone: str
    analytic: str = "tcm"
    granularity_m: int = 100
    aggregation_spec_version: str
    temporal_mode: str = "single_hour"
    adapter_version: str | None = None
    planned_units: int = Field(default=1, gt=0)
    request_nonce: str | None = None


class LiveAcquireResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: LiveJoinOutcome
    fingerprint: str
    job_id: str
    phase: LiveJoinPhase
    shared_result: dict[str, Any] | None = None
    reservation_id: str | None = None
    activity_id: str | None = None
    error: str | None = None
    submitted: bool = False
    reserved: bool = False


@dataclass(frozen=True)
class AtMostOneSubmitContract:
    """Best achievable guarantee. Not mathematical exactly-once."""

    contract_version: Literal["hva-signal-live-join-v1"] = LIVE_JOIN_CONTRACT_VERSION
    scope: str = "single_process_join_lock"
    durability: str = "J0_PROCESS_LOCAL"
    at_most_one_submit_while_join_record_lives: bool = True
    at_most_one_reserve_while_join_record_lives: bool = True
    joiners_never_submit: bool = True
    joiners_never_reserve: bool = True
    cache_hit_never_spends: bool = True
    dedupe_before_allowance: bool = True
    submit_slot_taken_before_vendor_io: bool = True
    exactly_once_at_vendor: bool = False
    vendor_idempotency_required: bool = False
    vendor_idempotency_assumed: bool = False
    safe_automatic_resubmit_after_crash_during_submit: bool = False
    multi_process_without_shared_lock: bool = False
    failed_post_submit_may_resubmit: bool = False
    unknown_vendor_state_may_resubmit: bool = False


AT_MOST_ONE_SUBMIT = AtMostOneSubmitContract()

# Fields that MUST participate in the live submit fingerprint.
LIVE_SUBMIT_FINGERPRINT_FIELDS: tuple[str, ...] = (
    "identity_version",
    "area_id",
    "geometry_sha256",
    "zone_geometry_version",
    "target_local_timestamp",
    "timezone",
    "analytic",
    "granularity_m",
    "aggregation_spec_version",
    "temporal_mode",
    "adapter_version",
)

# Fields that MUST NOT participate. Changing them cannot split or join jobs.
LIVE_SUBMIT_FINGERPRINT_EXCLUDED: tuple[str, ...] = (
    "job_id",
    "request_id",
    "request_nonce",
    "client_session",
    "user_identity",
    "allowance_remaining",
    "reservation_id",
    "activity_id",
    "force_live",
    "acquisition_preference",
    "operator_approval",
    "approval_ref",
    "wall_clock",
    "reference_protocol_id",
    "reference_version",
    "vendor_api_key",
)
