"""Candidate public two-signal contract. Not bound to FastAPI. Not in OpenAPI.

Version: hva-signal-two-signal-job-v1
Publication status: UNPUBLISHED.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.demo_allowance import AcquisitionPreference
from app.domain.enums import DataMode
from app.domain.signals import SignalAvailability, ThermalSignalKind
from app.services.snapshot_identity import (
    require_dst_safe_requested_hour,
    require_requested_hour,
)

PUBLIC_JOB_CONTRACT_VERSION = "hva-signal-two-signal-job-v1"
SPEND_AUTHORIZATION_CONTRACT_VERSION = "hva-signal-spend-authorization-v1"
PUBLIC_PROVENANCE_CONTRACT_VERSION = "hva-signal-public-provenance-v1"

FROZEN_SIGNAL_A_HOUR = 3


class PublicJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class PublicReasonCode(str, Enum):
    REFERENCE_NOT_PREPARED = "REFERENCE_NOT_PREPARED"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"
    THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT = (
        "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
    )
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    SPEND_DENIED = "SPEND_DENIED"
    SPEND_EXPIRED = "SPEND_EXPIRED"
    AUTHORIZATION_INSUFFICIENT = "AUTHORIZATION_INSUFFICIENT"
    SNAPSHOT_PARTIAL = "SNAPSHOT_PARTIAL"
    VENDOR_FAILED = "VENDOR_FAILED"
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    UNKNOWN_AREA = "UNKNOWN_AREA"
    EVIDENCE_REUSED = "EVIDENCE_REUSED"
    JOINED_IN_FLIGHT = "JOINED_IN_FLIGHT"
    EXECUTION_INTERRUPTED = "EXECUTION_INTERRUPTED"
    LIVE_DEMO_NOT_REQUESTED = "LIVE_DEMO_NOT_REQUESTED"
    DEMO_ALLOWANCE_DISABLED = "DEMO_ALLOWANCE_DISABLED"
    DEMO_ALLOWANCE_EXHAUSTED = "DEMO_ALLOWANCE_EXHAUSTED"
    DEMO_ALLOWANCE_EXPIRED = "DEMO_ALLOWANCE_EXPIRED"
    REQUEST_UNIT_CAP_EXCEEDED = "REQUEST_UNIT_CAP_EXCEEDED"
    LIVE_ACQUISITION_UNAVAILABLE = "LIVE_ACQUISITION_UNAVAILABLE"


class HistoricalSignalRequest(BaseModel):
    """Presence means Signal A is requested. Time stays frozen 03:00 AOI-local."""

    model_config = ConfigDict(extra="forbid")

    analysis_time: datetime

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
    acquisition_preference: AcquisitionPreference = AcquisitionPreference.REUSE_ONLY

    @field_validator("target_timestamp")
    @classmethod
    def _requested_hour(cls, value: datetime) -> datetime:
        return require_requested_hour(value)


class SignalSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    historical: HistoricalSignalRequest | None = None
    selected_time: SelectedTimeSignalRequest | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> SignalSelection:
        if self.historical is None and self.selected_time is None:
            raise ValueError("at least one signal must be requested")
        return self


class TwoSignalPublicRequest(BaseModel):
    """Candidate request. Must never be accepted by today's AnalysisRequest."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-two-signal-job-v1"] = PUBLIC_JOB_CONTRACT_VERSION
    area_id: str = Field(min_length=1)
    signals: SignalSelection
    timezone: str = Field(min_length=1)
    granularity_m: Literal[60, 80, 100] = 100
    data_mode: DataMode = DataMode.REPLAY

    @model_validator(mode="after")
    def _dst_safe_selected_time(self) -> TwoSignalPublicRequest:
        """Unpublished Signal B request guard. Not a public route or reason code."""
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

    @property
    def percent(self) -> float | None:
        if self.completed_units is None or self.required_units is None:
            return None
        return self.completed_units / float(self.required_units)


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
    source: str | None = None
    data_status: str | None = None
    target_timestamp: datetime | None = None
    timezone: str | None = None
    geometry_version: str | None = None
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


class PublicSpendView(BaseModel):
    """Client-visible spend state. No prices. Not an approval action."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-spend-authorization-v1"] = (
        SPEND_AUTHORIZATION_CONTRACT_VERSION
    )
    state: str
    requested_units: int | None = None
    planned_acquisition_units: int | None = None
    authorized_max_units: int | None = None
    reason: str | None = None


class PublicSignalSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ThermalSignalKind
    requested: bool
    availability: SignalAvailability
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
        return self


class TwoSignalPublicJob(BaseModel):
    """Candidate GET body. Not served by any route."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-two-signal-job-v1"] = PUBLIC_JOB_CONTRACT_VERSION
    job_id: str
    area_id: str
    status: PublicJobStatus
    combined_score_authorized: Literal[False] = False
    historical: PublicSignalSection
    selected_time: PublicSignalSection
    spend: PublicSpendView | None = None
    legacy_thermal_source: str | None = None


class WorkerHandoff(BaseModel):
    """J4 worker payload concept. Not a queue implementation."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    signal_kind: ThermalSignalKind
    request_fingerprint: str
    geometry_sha256: str | None = None
    target_timestamp: datetime | None = None
    authorized_max_units: int
    planned_acquisition_units: int
    reservation_id: str | None = None
    authorization_source: Literal["demo_allowance", "manual_operator_future"] = (
        "manual_operator_future"
    )
    vendor_activity_id: str | None = None
    must_recheck_authorization: Literal[True] = True
