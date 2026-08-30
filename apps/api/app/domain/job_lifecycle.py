"""Internal two-signal job lifecycle. Not a public AnalysisResult schema."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.signals import (
    SelectedTimeSnapshot,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)


class JobTerminality(str, Enum):
    IN_FLIGHT = "IN_FLIGHT"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_PARTIAL = "TERMINAL_PARTIAL"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


class ExecutionState(str, Enum):
    """Process execution, not analytical availability."""

    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    INTERRUPTED = "INTERRUPTED"


class CostAuthorizationState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"


class SignalPhase(str, Enum):
    QUEUED = "queued"
    SUBMITTED = "submitted"
    VENDOR_PROCESSING = "vendor_processing"
    RECEIVED = "received"
    AGGREGATING = "aggregating"
    LOADING_CONTEXT = "loading_context"
    COMPUTING = "computing"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"


class SignalSectionError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(min_length=1)
    user_message: str = Field(min_length=1)
    log_ref: str | None = None


class SignalProgress(BaseModel):
    """Numeric units only when the denominator is a real protocol count."""

    model_config = ConfigDict(extra="forbid")

    phase: SignalPhase
    message: str | None = None
    completed_units: int | None = Field(default=None, ge=0)
    required_units: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _units_together(self) -> SignalProgress:
        if (self.completed_units is None) != (self.required_units is None):
            raise ValueError("completed_units and required_units must be set together")
        if (
            self.completed_units is not None
            and self.required_units is not None
            and self.completed_units > self.required_units
        ):
            raise ValueError("completed_units cannot exceed required_units")
        return self


class CostAuthorization(BaseModel):
    """Spend approval. Not analytical availability."""

    model_config = ConfigDict(extra="forbid")

    state: CostAuthorizationState = CostAuthorizationState.NOT_REQUIRED
    estimated_units: int | None = Field(default=None, ge=0)
    authorized_max_units: int | None = Field(default=None, ge=0)
    request_fingerprint: str | None = None


class SignalSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ThermalSignalKind
    requested: bool
    availability: SignalAvailability
    progress: SignalProgress
    provenance: SignalProvenance | None = None
    error: SignalSectionError | None = None
    historical_result: dict[str, Any] | None = None
    selected_time_result: SelectedTimeSnapshot | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def _result_matches_kind(self) -> SignalSection:
        if self.kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            if self.historical_result is not None:
                raise ValueError("Signal B cannot carry a historical result")
            if self.selected_time_result is not None:
                dumped = self.selected_time_result.model_dump()
                if "q_A" in dumped or "thermal_ordering_permitted" in dumped:
                    raise ValueError("Signal B result cannot carry q_A")
        if self.kind == ThermalSignalKind.HISTORICAL_NORMALIZED:
            if self.selected_time_result is not None:
                raise ValueError("Signal A cannot carry a selected-time snapshot")
        if not self.requested and self.availability not in {
            SignalAvailability.NOT_REQUESTED,
        }:
            raise ValueError("unrequested sections must be NOT_REQUESTED")
        return self


class TwoSignalJobState(BaseModel):
    """Canonical internal job view. Not published on AnalysisResult."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    area_id: str
    historical: SignalSection
    selected_time: SignalSection
    cost_authorization: CostAuthorization = Field(default_factory=CostAuthorization)
    combined_score_authorized: Literal[False] = False
    execution_state: ExecutionState = ExecutionState.NOT_STARTED

    @model_validator(mode="after")
    def _kinds(self) -> TwoSignalJobState:
        if self.historical.kind != ThermalSignalKind.HISTORICAL_NORMALIZED:
            raise ValueError("historical section kind mismatch")
        if self.selected_time.kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            raise ValueError("selected-time section kind mismatch")
        return self

    @property
    def terminality(self) -> JobTerminality:
        return derive_job_terminality(self)


_IN_FLIGHT = frozenset(
    {SignalAvailability.PENDING, SignalAvailability.FETCHING}
)
_FAILED = frozenset({SignalAvailability.FAILED})
_USEFUL = frozenset(
    {
        SignalAvailability.READY,
        SignalAvailability.PARTIAL,
        SignalAvailability.UNAVAILABLE,
        SignalAvailability.NOT_PREPARED,
        SignalAvailability.INSUFFICIENT_REFERENCE,
        SignalAvailability.INSUFFICIENT_EVIDENCE,
        SignalAvailability.D8_INSUFFICIENT,
    }
)


def _requested(section: SignalSection) -> bool:
    return section.requested and section.availability != SignalAvailability.NOT_REQUESTED


def derive_job_terminality(state: TwoSignalJobState) -> JobTerminality:
    """Overall job terminality. Both signals need not be READY."""
    if state.cost_authorization.state == CostAuthorizationState.WAITING_FOR_APPROVAL:
        return JobTerminality.IN_FLIGHT
    if state.execution_state == ExecutionState.INTERRUPTED:
        return JobTerminality.TERMINAL_FAILURE

    classes: list[str] = []
    for section in (state.historical, state.selected_time):
        if not _requested(section):
            continue
        if section.availability in _IN_FLIGHT:
            classes.append("inflight")
        elif section.availability in _FAILED:
            classes.append("failed")
        elif section.availability in _USEFUL:
            classes.append("useful")
        else:
            classes.append("inflight")

    if not classes:
        return JobTerminality.TERMINAL_FAILURE
    if "inflight" in classes:
        return JobTerminality.IN_FLIGHT
    if "useful" in classes and "failed" in classes:
        return JobTerminality.TERMINAL_PARTIAL
    if "failed" in classes and "useful" not in classes:
        return JobTerminality.TERMINAL_FAILURE
    return JobTerminality.TERMINAL_SUCCESS


def empty_section(
    kind: ThermalSignalKind,
    *,
    requested: bool,
    area_id: str,
) -> SignalSection:
    availability = (
        SignalAvailability.PENDING if requested else SignalAvailability.NOT_REQUESTED
    )
    return SignalSection(
        kind=kind,
        requested=requested,
        availability=availability,
        progress=SignalProgress(
            phase=SignalPhase.QUEUED if requested else SignalPhase.READY,
            message="Not requested." if not requested else "Queued.",
        ),
        provenance=SignalProvenance(signal_kind=kind, area_id=area_id),
    )


def apply_progress(
    current: SignalProgress,
    next_progress: SignalProgress,
) -> SignalProgress:
    """Numeric progress is monotonic. Phase-only updates are allowed."""
    if (
        current.completed_units is not None
        and next_progress.completed_units is not None
        and next_progress.completed_units < current.completed_units
    ):
        raise ValueError("signal progress cannot regress")
    return next_progress
