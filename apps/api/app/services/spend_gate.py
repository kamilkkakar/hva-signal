"""Provider-neutral spend authorization. Valid request != spend permission.

No vendor imports. No public route. Approval is fingerprint-bound.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.job_lifecycle import CostAuthorization, CostAuthorizationState
from app.domain.signals import ThermalSignalKind

SPEND_GRANT_VERSION = "hva-signal-spend-grant-v1"

_ALLOWED: dict[CostAuthorizationState, frozenset[CostAuthorizationState]] = {
    CostAuthorizationState.NOT_REQUIRED: frozenset(
        {CostAuthorizationState.REQUIRED, CostAuthorizationState.NOT_REQUIRED}
    ),
    CostAuthorizationState.REQUIRED: frozenset(
        {CostAuthorizationState.WAITING_FOR_APPROVAL, CostAuthorizationState.DENIED}
    ),
    CostAuthorizationState.WAITING_FOR_APPROVAL: frozenset(
        {
            CostAuthorizationState.AUTHORIZED,
            CostAuthorizationState.DENIED,
            CostAuthorizationState.EXPIRED,
        }
    ),
    CostAuthorizationState.AUTHORIZED: frozenset(
        {
            CostAuthorizationState.CONSUMED,
            CostAuthorizationState.EXPIRED,
            CostAuthorizationState.INSUFFICIENT,
        }
    ),
    CostAuthorizationState.DENIED: frozenset(),
    CostAuthorizationState.EXPIRED: frozenset(),
    CostAuthorizationState.CONSUMED: frozenset(),
    CostAuthorizationState.INSUFFICIENT: frozenset(
        {CostAuthorizationState.WAITING_FOR_APPROVAL}
    ),
}


class SpendGateError(ValueError):
    """Illegal spend-authorization transition or bind mismatch."""


class SpendGrant(BaseModel):
    """Fingerprint-bound approval. Not reusable across hour/area/geometry."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["hva-signal-spend-grant-v1"] = SPEND_GRANT_VERSION
    state: CostAuthorizationState
    signal_kind: ThermalSignalKind
    request_fingerprint: str
    geometry_sha256: str
    authorized_max_units: int | None = Field(default=None, gt=0)
    requested_units: int = Field(ge=0)
    planned_acquisition_units: int = Field(ge=0)
    consumed_units: int = Field(default=0, ge=0)
    approved_at: datetime | None = None
    expires_at: datetime | None = None
    approval_ref: str | None = None
    reason: str | None = None


class ExecutionGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason: str


def _require_transition(current: CostAuthorizationState, nxt: CostAuthorizationState) -> None:
    if nxt not in _ALLOWED[current]:
        raise SpendGateError(f"illegal spend transition {current.value} -> {nxt.value}")


def waiting_grant(
    *,
    signal_kind: ThermalSignalKind,
    request_fingerprint: str,
    geometry_sha256: str,
    requested_units: int,
    planned_acquisition_units: int,
) -> SpendGrant:
    return SpendGrant(
        state=CostAuthorizationState.WAITING_FOR_APPROVAL,
        signal_kind=signal_kind,
        request_fingerprint=request_fingerprint,
        geometry_sha256=geometry_sha256,
        authorized_max_units=None,
        requested_units=requested_units,
        planned_acquisition_units=planned_acquisition_units,
        reason="Paid acquisition requires explicit approval.",
    )


def approve_grant(
    grant: SpendGrant,
    *,
    authorized_max_units: int,
    approval_ref: str,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> SpendGrant:
    _require_transition(grant.state, CostAuthorizationState.AUTHORIZED)
    if authorized_max_units < grant.planned_acquisition_units:
        raise SpendGateError("authorized_max_units is below planned acquisition units")
    return grant.model_copy(
        update={
            "state": CostAuthorizationState.AUTHORIZED,
            "authorized_max_units": authorized_max_units,
            "approval_ref": approval_ref,
            "approved_at": now or datetime.now(timezone.utc),
            "expires_at": expires_at,
            "reason": None,
        }
    )


def deny_grant(grant: SpendGrant, *, reason: str) -> SpendGrant:
    _require_transition(grant.state, CostAuthorizationState.DENIED)
    return grant.model_copy(
        update={"state": CostAuthorizationState.DENIED, "reason": reason}
    )


def expire_grant(grant: SpendGrant) -> SpendGrant:
    _require_transition(grant.state, CostAuthorizationState.EXPIRED)
    return grant.model_copy(
        update={"state": CostAuthorizationState.EXPIRED, "reason": "Approval expired."}
    )


def mark_insufficient(grant: SpendGrant, *, planned_acquisition_units: int) -> SpendGrant:
    _require_transition(grant.state, CostAuthorizationState.INSUFFICIENT)
    return grant.model_copy(
        update={
            "state": CostAuthorizationState.INSUFFICIENT,
            "planned_acquisition_units": planned_acquisition_units,
            "reason": "Planned acquisition units exceed authorized_max_units.",
        }
    )


def consume_grant(grant: SpendGrant, *, units: int) -> SpendGrant:
    _require_transition(grant.state, CostAuthorizationState.CONSUMED)
    if grant.authorized_max_units is None:
        raise SpendGateError("consume requires authorized_max_units")
    consumed = grant.consumed_units + units
    if consumed > grant.authorized_max_units:
        raise SpendGateError("consume would exceed authorized_max_units")
    return grant.model_copy(
        update={"state": CostAuthorizationState.CONSUMED, "consumed_units": consumed}
    )


def can_execute_paid_acquisition(
    grant: SpendGrant,
    *,
    request_fingerprint: str,
    signal_kind: ThermalSignalKind,
    geometry_sha256: str,
    planned_units: int,
    now: datetime,
) -> ExecutionGateResult:
    """Controller and worker both call this before any payable submission."""
    if grant.state != CostAuthorizationState.AUTHORIZED:
        return ExecutionGateResult(allowed=False, reason=f"grant_state_{grant.state.value}")
    if grant.authorized_max_units is None:
        return ExecutionGateResult(allowed=False, reason="missing_authorized_max_units")
    if grant.request_fingerprint != request_fingerprint:
        return ExecutionGateResult(allowed=False, reason="fingerprint_mismatch")
    if grant.signal_kind != signal_kind:
        return ExecutionGateResult(allowed=False, reason="signal_kind_mismatch")
    if grant.geometry_sha256 != geometry_sha256:
        return ExecutionGateResult(allowed=False, reason="geometry_mismatch")
    if grant.expires_at is not None and now >= grant.expires_at:
        return ExecutionGateResult(allowed=False, reason="expired")
    if planned_units > grant.authorized_max_units:
        return ExecutionGateResult(allowed=False, reason="planned_units_exceed_cap")
    if grant.consumed_units + planned_units > grant.authorized_max_units:
        return ExecutionGateResult(allowed=False, reason="consumed_plus_planned_exceed_cap")
    return ExecutionGateResult(allowed=True, reason="authorized")


def compare_planned_units_to_cap(
    grant: SpendGrant, *, planned_units: int
) -> CostAuthorizationState:
    if grant.authorized_max_units is None or planned_units > grant.authorized_max_units:
        return CostAuthorizationState.INSUFFICIENT
    return grant.state


def cost_view_from_grant(grant: SpendGrant) -> CostAuthorization:
    return CostAuthorization(
        state=grant.state,
        signal_kind=grant.signal_kind,
        request_fingerprint=grant.request_fingerprint,
        geometry_sha256=grant.geometry_sha256,
        requested_units=grant.requested_units,
        planned_acquisition_units=grant.planned_acquisition_units,
        estimated_units=grant.planned_acquisition_units,
        authorized_max_units=grant.authorized_max_units,
        consumed_units=grant.consumed_units,
        approved_at=grant.approved_at,
        expires_at=grant.expires_at,
        approval_ref=grant.approval_ref,
        reason=grant.reason,
    )
