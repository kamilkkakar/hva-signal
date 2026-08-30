"""Hosted live-demo resolution. Cache and join before any allowance reservation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.job_store import JobStore
from app.domain.demo_allowance import (
    AcquisitionPreference,
    DemoAllowanceDecision,
    DemoAllowanceDecisionCode,
    DemoRequestIdentity,
)
from app.domain.enums import DataMode, JobStatus
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import (
    InMemoryDemoAllowanceLedger,
    policy_blocks_spend,
)
from app.services.live_resource_guards import LiveResourceGuards
from app.services.spend_gate import ExecutionGateResult


_TERMINAL_OK = frozenset({JobStatus.COMPLETE, JobStatus.PARTIAL})
_TERMINAL_FAIL = frozenset({JobStatus.FAILED})


class HostedDemoResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: DemoAllowanceDecisionCode
    joined_job_id: str | None = None
    decision: DemoAllowanceDecision | None = None


def resolve_hosted_demo_path(
    *,
    store: JobStore,
    ledger: InMemoryDemoAllowanceLedger,
    dedupe_key: str,
    data_mode: DataMode,
    snapshot_capable: bool,
    preference: AcquisitionPreference,
    identity: DemoRequestIdentity,
    planned_units: int,
    now: datetime,
    resource_guards: LiveResourceGuards | None = None,
) -> HostedDemoResolution:
    """Replay/cache/join never touch the demo ledger."""
    if not snapshot_capable:
        return HostedDemoResolution(code=DemoAllowanceDecisionCode.NOT_SNAPSHOT_CAPABLE)
    if data_mode == DataMode.REPLAY:
        return HostedDemoResolution(code=DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE)

    existing = store.find_by_dedupe_key(dedupe_key)
    if existing is not None:
        if existing.status not in _TERMINAL_OK | _TERMINAL_FAIL:
            return HostedDemoResolution(
                code=DemoAllowanceDecisionCode.JOIN_IN_FLIGHT,
                joined_job_id=existing.job_id,
            )
        if existing.status in _TERMINAL_OK:
            return HostedDemoResolution(
                code=DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE,
                joined_job_id=existing.job_id,
            )

    if preference != AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO:
        return HostedDemoResolution(code=DemoAllowanceDecisionCode.LIVE_DEMO_NOT_REQUESTED)

    blocked = policy_blocks_spend(ledger.policy, now=now)
    if blocked is not None:
        return HostedDemoResolution(code=blocked)

    if resource_guards is not None:
        join_existing = ledger.has_active_reservation(identity.request_fingerprint)
        admission = resource_guards.admit_reserve(join_existing=join_existing)
        if not admission.proceed:
            return HostedDemoResolution(
                code=DemoAllowanceDecisionCode.LIVE_ACQUISITION_UNAVAILABLE
            )

    decision = ledger.try_reserve(identity, planned_units=planned_units, now=now)
    return HostedDemoResolution(code=decision.code, decision=decision)


def compatible_fallback_allowed(*, same_fingerprint: bool, same_geometry: bool) -> bool:
    """Unrelated Phoenix/time substitution is never a fallback."""
    return same_fingerprint and same_geometry


def historical_prep_not_triggered_by_demo() -> bool:
    return True


def recheck_demo_reservation_before_paid_submission(
    *,
    ledger: InMemoryDemoAllowanceLedger,
    reservation_id: str,
    identity: DemoRequestIdentity,
    planned_units: int,
    store: JobStore,
    dedupe_key: str,
    now: datetime,
) -> ExecutionGateResult:
    """Worker defense in depth. User confirmation is not a grant."""
    existing = store.find_by_dedupe_key(dedupe_key)
    if existing is not None and existing.status in _TERMINAL_OK:
        reservation = ledger.get(reservation_id)
        if reservation is not None and reservation.state.value == "RESERVED":
            ledger.release(reservation_id)
        return ExecutionGateResult(allowed=False, reason="compatible_result_appeared")
    try:
        ledger.consume(
            reservation_id,
            identity=identity,
            planned_units=planned_units,
            now=now,
        )
    except Exception as exc:
        return ExecutionGateResult(allowed=False, reason=str(exc))
    if identity.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        return ExecutionGateResult(allowed=False, reason="signal_kind_mismatch")
    return ExecutionGateResult(allowed=True, reason="reservation_consumed")
