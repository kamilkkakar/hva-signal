"""P2 publication-safe two-signal DTOs.

Not the unpublished candidate in ``app.domain.public_contract``.
No spend, allowance, approval, or acquisition preference.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.client_privilege import CLIENT_NEVER_SET_FIELDS
from app.services.snapshot_identity import (
    require_dst_safe_requested_hour,
    require_requested_hour,
)

PUBLIC_JOB_CONTRACT_VERSION = "hva-signal-two-signal-job-v1"
PUBLIC_PROVENANCE_CONTRACT_VERSION = "hva-signal-public-provenance-v1"
FROZEN_SIGNAL_A_HOUR = 3

_LEAK_REQUEST_FIELDS = frozenset(
    {
        "acquisition_preference",
        "approval",
        "approved",
        "approve",
        "authorize",
        "authorized",
        "authorized_max_units",
        "spend",
        "spend_authorization",
        "spend_authorized",
        "skip_approval",
        "allowance",
        "allowance_remaining",
        "demo_budget",
        "demo",
        "demo_test",
        "live_demo",
        "force_live",
        "bypass_limit",
        "operator",
        "operator_override",
        "operator_id",
        "authorization_source",
        "reservation_id",
        "approval_ref",
        "consumed_units",
        "planned_acquisition_units",
        "requested_units",
        "estimated_units",
        "max_total_acquisition_units",
        "max_units_per_request",
        "demo_allowance_enabled",
        "awaiting_approval",
        "now",
        "current_conditions",
        "internal_key",
        "secret",
        "api_key",
        "fortyguard_api_key",
    }
) | CLIENT_NEVER_SET_FIELDS


def _reject_leak_fields(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    hits = _LEAK_REQUEST_FIELDS.intersection(data)
    if hits:
        raise ValueError(
            "unpublished spend or operator fields are not accepted: "
            + ", ".join(sorted(hits))
        )
    return data


class PublicJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    UNKNOWN_JOB = "unknown_job"


class ThermalSignalKind(str, Enum):
    HISTORICAL_NORMALIZED = "historical_normalized"
    SELECTED_TIME_SNAPSHOT = "selected_time_snapshot"


class PublicSignalAvailability(str, Enum):
    READY = "READY"
    PENDING = "PENDING"
    FAILED = "FAILED"
    NOT_REQUESTED = "NOT_REQUESTED"
    NOT_PREPARED = "NOT_PREPARED"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    D8_INSUFFICIENT = "D8_INSUFFICIENT"
    FETCHING = "FETCHING"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class PublicReasonCode(str, Enum):
    REFERENCE_NOT_PREPARED = "REFERENCE_NOT_PREPARED"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"
    THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT = (
        "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
    )
    SNAPSHOT_PARTIAL = "SNAPSHOT_PARTIAL"
    SNAPSHOT_UNAVAILABLE = "SNAPSHOT_UNAVAILABLE"
    VENDOR_FAILED = "VENDOR_FAILED"
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    UNKNOWN_AREA = "UNKNOWN_AREA"
    EVIDENCE_REUSED = "EVIDENCE_REUSED"
    JOINED_IN_FLIGHT = "JOINED_IN_FLIGHT"
    EXECUTION_INTERRUPTED = "EXECUTION_INTERRUPTED"


class HistoricalSignalRequest(BaseModel):
    """Presence means Signal A is requested. Time stays frozen 03:00 AOI-local."""

    model_config = ConfigDict(extra="forbid")

    analysis_time: datetime

    @model_validator(mode="before")
    @classmethod
    def _no_leaks(cls, data: Any) -> Any:
        return _reject_leak_fields(data)

    @field_validator("analysis_time")
    @classmethod
    def _naive_frozen_hour(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("Signal A analysis_time must be AOI-local naive")
        if (
            value.hour != FROZEN_SIGNAL_A_HOUR
            or value.minute != 0
            or value.second != 0
            or value.microsecond != 0
        ):
            raise ValueError("Signal A time is frozen at 03:00; do not silently change it")
        return value


class SelectedTimeSignalRequest(BaseModel):
    """Presence means Signal B is requested. Hour precision only. Not NOW."""

    model_config = ConfigDict(extra="forbid")

    target_timestamp: datetime
    analytic: Literal["tcm"] = "tcm"

    @model_validator(mode="before")
    @classmethod
    def _no_leaks(cls, data: Any) -> Any:
        return _reject_leak_fields(data)

    @field_validator("target_timestamp")
    @classmethod
    def _requested_hour(cls, value: datetime) -> datetime:
        return require_requested_hour(value)


class SignalSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    historical: HistoricalSignalRequest | None = None
    selected_time: SelectedTimeSignalRequest | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_leaks(cls, data: Any) -> Any:
        return _reject_leak_fields(data)

    @model_validator(mode="after")
    def _at_least_one(self) -> SignalSelection:
        if self.historical is None and self.selected_time is None:
            raise ValueError("at least one signal must be requested")
        return self


class TwoSignalPublicationRequest(BaseModel):
    """P2 POST body. Server implies reuse_only. ``data_mode=live`` is 422."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-two-signal-job-v1"]
    area_id: str = Field(min_length=1)
    signals: SignalSelection
    timezone: str = Field(min_length=1)
    granularity_m: Literal[60, 80, 100] = 100
    data_mode: Literal["replay", "auto"] = "replay"

    @model_validator(mode="before")
    @classmethod
    def _no_leaks(cls, data: Any) -> Any:
        return _reject_leak_fields(data)

    @model_validator(mode="after")
    def _dst_safe_selected_time(self) -> TwoSignalPublicationRequest:
        selected = self.signals.selected_time
        if selected is not None:
            require_dst_safe_requested_hour(selected.target_timestamp, self.timezone)
        return self


class PublicProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str
    message: str | None = None
    completed_units: int | None = Field(default=None, ge=0)
    required_units: int | None = Field(default=None, gt=0)
    updated_at: datetime | None = None


class PublicError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: PublicReasonCode
    message: str


class PublicProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-provenance-v1"] = (
        PUBLIC_PROVENANCE_CONTRACT_VERSION
    )
    signal_kind: ThermalSignalKind
    source: Literal["replay", "fortyguard_cached", "fortyguard_live"] | None = None
    data_status: Literal["replay", "cached", "live", "partial", "unavailable"] | None = None
    target_timestamp: datetime | None = None
    timezone: str | None = None
    geometry_version: str | None = None
    geometry_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    aggregation_spec_version: str | None = None
    reference_version: str | None = None
    reference_source: str | None = None
    request_fingerprint: str | None = None

    @field_validator("reference_version", "reference_source")
    @classmethod
    def _b_has_no_reference(cls, value: str | None, info):
        kind = info.data.get("signal_kind")
        if kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT and value is not None:
            raise ValueError("Signal B provenance cannot carry a historical reference")
        return value

    @model_validator(mode="after")
    def _cached_never_live(self) -> PublicProvenance:
        if self.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            return self
        if self.source == "fortyguard_live":
            raise ValueError("P2 must not emit fortyguard_live")
        if self.source == "fortyguard_cached" and self.data_status == "live":
            raise ValueError("cached Signal B cannot be labeled live")
        if self.source == "fortyguard_cached" and self.data_status == "replay":
            raise ValueError("cached Signal B cannot be labeled replay")
        if self.source == "replay" and self.data_status in {"live", "cached"}:
            raise ValueError("replay Signal B cannot be labeled live or cached")
        return self


class PublicSnapshotZone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    mean_temperature_c: float | None
    tile_count: int
    coverage_status: str


class PublicSelectedTimeResult(BaseModel):
    """Public Signal B payload. Absolute °C. No q_A, D8, color, or rank."""

    model_config = ConfigDict(extra="forbid")

    units: Literal["celsius"] = "celsius"
    aggregation_method: Literal["centroid_within_mean"] = "centroid_within_mean"
    spatial_resolution: Literal["zone"] = "zone"
    user_facing_tile_map: Literal[False] = False
    target_timestamp: datetime
    timezone: str
    zones: list[PublicSnapshotZone] = Field(default_factory=list)
    expected_zone_count: int | None = None
    valid_zone_count: int | None = None
    missing_zone_ids: list[str] = Field(default_factory=list)
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None


class PublicSignalSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ThermalSignalKind
    requested: bool
    availability: PublicSignalAvailability
    progress: PublicProgress
    provenance: PublicProvenance | None = None
    error: PublicError | None = None
    historical_result: dict[str, Any] | None = None
    selected_time_result: PublicSelectedTimeResult | None = None

    @model_validator(mode="after")
    def _no_cross_signal_payload(self) -> PublicSignalSection:
        if self.kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            if self.historical_result is not None:
                raise ValueError("Signal B cannot carry a historical result")
        if self.kind == ThermalSignalKind.HISTORICAL_NORMALIZED:
            if self.selected_time_result is not None:
                raise ValueError("Signal A cannot carry a selected-time result")
        if not self.requested and self.availability != PublicSignalAvailability.NOT_REQUESTED:
            raise ValueError("unrequested sections must be NOT_REQUESTED")
        return self


class TwoSignalPublicJob(BaseModel):
    """P2 GET/202 body. No spend view."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-two-signal-job-v1"] = PUBLIC_JOB_CONTRACT_VERSION
    job_id: str
    area_id: str
    status: PublicJobStatus
    combined_score_authorized: Literal[False] = False
    historical: PublicSignalSection
    selected_time: PublicSignalSection
    legacy_thermal_source: str | None = None
    created_at: datetime | None = None
    recoverable: bool | None = None
    message: str | None = None


class TwoSignalUnknownJob(BaseModel):
    """Thin unknown envelope. Dummy sections would look like B was not requested."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-two-signal-job-v1"] = PUBLIC_JOB_CONTRACT_VERSION
    job_id: str
    status: Literal["unknown_job"] = "unknown_job"
    combined_score_authorized: Literal[False] = False
    recoverable: Literal[True] = True
    message: str = "The analysis job is no longer present on this runtime."
