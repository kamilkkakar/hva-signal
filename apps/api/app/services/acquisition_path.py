"""Cache / join / spend decision. Paid execution is last, never first."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.core.job_store import JobStore
from app.domain.enums import DataMode, JobStatus
from app.domain.job_lifecycle import CostAuthorizationState
from app.domain.signals import ThermalSignalKind
from app.services.spend_gate import SpendGrant, can_execute_paid_acquisition


class AcquisitionDisposition(str, Enum):
    REPLAY_FREE = "REPLAY_FREE"
    CACHED_REUSE = "CACHED_REUSE"
    JOIN_IN_FLIGHT = "JOIN_IN_FLIGHT"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    EXECUTION_ELIGIBLE = "EXECUTION_ELIGIBLE"
    SPEND_DENIED = "SPEND_DENIED"
    SPEND_EXPIRED = "SPEND_EXPIRED"
    REFERENCE_NOT_PREPARED = "REFERENCE_NOT_PREPARED"
    NOT_SNAPSHOT_CAPABLE = "NOT_SNAPSHOT_CAPABLE"
    AUTHORIZATION_INSUFFICIENT = "AUTHORIZATION_INSUFFICIENT"


class AcquisitionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: AcquisitionDisposition
    joined_job_id: str | None = None
    approval_required: bool
    spend_state: CostAuthorizationState


_TERMINAL_OK = frozenset({JobStatus.COMPLETE, JobStatus.PARTIAL})
_TERMINAL_FAIL = frozenset({JobStatus.FAILED})


def resolve_selected_time_path(
    *,
    store: JobStore,
    dedupe_key: str,
    data_mode: DataMode,
    snapshot_capable: bool,
    grant: SpendGrant | None,
    planned_units: int,
    request_fingerprint: str,
    geometry_sha256: str,
    now,
) -> AcquisitionDecision:
    """Replay/cached/in-flight reuse never requires paid authorization."""
    if not snapshot_capable:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.NOT_SNAPSHOT_CAPABLE,
            approval_required=False,
            spend_state=CostAuthorizationState.NOT_REQUIRED,
        )
    if data_mode == DataMode.REPLAY:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.REPLAY_FREE,
            approval_required=False,
            spend_state=CostAuthorizationState.NOT_REQUIRED,
        )

    existing = store.find_by_dedupe_key(dedupe_key)
    if existing is not None:
        if existing.status not in _TERMINAL_OK | _TERMINAL_FAIL:
            return AcquisitionDecision(
                disposition=AcquisitionDisposition.JOIN_IN_FLIGHT,
                joined_job_id=existing.job_id,
                approval_required=False,
                spend_state=CostAuthorizationState.NOT_REQUIRED,
            )
        if existing.status in _TERMINAL_OK:
            return AcquisitionDecision(
                disposition=AcquisitionDisposition.CACHED_REUSE,
                joined_job_id=existing.job_id,
                approval_required=False,
                spend_state=CostAuthorizationState.NOT_REQUIRED,
            )

    if grant is None or grant.state == CostAuthorizationState.WAITING_FOR_APPROVAL:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.WAITING_FOR_APPROVAL,
            approval_required=True,
            spend_state=CostAuthorizationState.WAITING_FOR_APPROVAL,
        )
    if grant.state == CostAuthorizationState.DENIED:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.SPEND_DENIED,
            approval_required=True,
            spend_state=CostAuthorizationState.DENIED,
        )
    if grant.state == CostAuthorizationState.EXPIRED:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.SPEND_EXPIRED,
            approval_required=True,
            spend_state=CostAuthorizationState.EXPIRED,
        )
    if grant.state == CostAuthorizationState.INSUFFICIENT:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.AUTHORIZATION_INSUFFICIENT,
            approval_required=True,
            spend_state=CostAuthorizationState.INSUFFICIENT,
        )
    gate = can_execute_paid_acquisition(
        grant,
        request_fingerprint=request_fingerprint,
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        geometry_sha256=geometry_sha256,
        planned_units=planned_units,
        now=now,
    )
    if gate.allowed:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.EXECUTION_ELIGIBLE,
            approval_required=False,
            spend_state=CostAuthorizationState.AUTHORIZED,
        )
    if gate.reason in {"planned_units_exceed_cap", "consumed_plus_planned_exceed_cap"}:
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.AUTHORIZATION_INSUFFICIENT,
            approval_required=True,
            spend_state=CostAuthorizationState.INSUFFICIENT,
        )
    if gate.reason == "expired":
        return AcquisitionDecision(
            disposition=AcquisitionDisposition.SPEND_EXPIRED,
            approval_required=True,
            spend_state=CostAuthorizationState.EXPIRED,
        )
    return AcquisitionDecision(
        disposition=AcquisitionDisposition.WAITING_FOR_APPROVAL,
        approval_required=True,
        spend_state=CostAuthorizationState.WAITING_FOR_APPROVAL,
    )


def historical_does_not_start_preparation(*, reference_ready: bool) -> AcquisitionDisposition:
    """Requesting Signal A never implicitly starts 93-call reference prep."""
    if reference_ready:
        return AcquisitionDisposition.REPLAY_FREE
    return AcquisitionDisposition.REFERENCE_NOT_PREPARED
