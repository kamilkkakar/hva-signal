"""J3 durable job contract. Persistence lives on JobStore (LIVE-A).

This is not public JobStatus, not two-signal section lifecycle, and not a
worker. LIVE-C owns automatic transitions. LIVE-B owns the SQLite file
adapter. This module owns identity, required states, error class, recovery
flags, and the restart classification that must never auto-resubmit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


DURABILITY_CONTRACT_VERSION = "hva-signal-job-durability-v1"


class DurabilityState(str, Enum):
    """Vendor-acquisition durability states. LIVE-C owns transition edges."""

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


REQUIRED_DURABILITY_STATES: tuple[DurabilityState, ...] = tuple(DurabilityState)


class JobErrorClass(str, Enum):
    NONE = "NONE"
    VALIDATION = "VALIDATION"
    CACHE = "CACHE"
    ALLOWANCE = "ALLOWANCE"
    PRE_SUBMIT = "PRE_SUBMIT"
    POST_SUBMIT = "POST_SUBMIT"
    VENDOR_UNKNOWN = "VENDOR_UNKNOWN"
    WORKER_CRASH = "WORKER_CRASH"
    INTERNAL = "INTERNAL"


# Automatic recovery must never move these back to SUBMITTING / SUBMITTED.
NEVER_AUTO_RESUBMIT_FROM = frozenset(
    {
        DurabilityState.UNKNOWN_VENDOR_STATE,
        DurabilityState.FAILED_POST_SUBMIT,
        DurabilityState.CONSUMED,
        DurabilityState.CACHE_HIT,
        DurabilityState.JOINED,
        DurabilityState.ACTIVITY_ID_PERSISTED,
        DurabilityState.PROCESSING,
        DurabilityState.RESULT_RECEIVED,
        DurabilityState.NORMALIZED,
        DurabilityState.CACHED,
        DurabilityState.SUBMITTED,
        DurabilityState.RECOVERY_REQUIRED,
    }
)

RESUBMIT_STATES = frozenset(
    {
        DurabilityState.SUBMITTING,
        DurabilityState.SUBMITTED,
    }
)

_TERMINAL_DURABILITY = frozenset(
    {
        DurabilityState.CACHE_HIT,
        DurabilityState.CONSUMED,
        DurabilityState.FAILED_PRE_SUBMIT,
        DurabilityState.FAILED_POST_SUBMIT,
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RecoveryFlags:
    """Recovery posture. auto_resubmit is never set true by restart recovery."""

    auto_resubmit: bool = False
    requires_vendor_status_check: bool = False
    operator_reconcile: bool = False
    reservation_intact: bool = False
    activity_id_durable: bool = False
    submit_attempted: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "auto_resubmit": self.auto_resubmit,
            "requires_vendor_status_check": self.requires_vendor_status_check,
            "operator_reconcile": self.operator_reconcile,
            "reservation_intact": self.reservation_intact,
            "activity_id_durable": self.activity_id_durable,
            "submit_attempted": self.submit_attempted,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> RecoveryFlags:
        if not payload:
            return cls()
        return cls(
            auto_resubmit=bool(payload.get("auto_resubmit")),
            requires_vendor_status_check=bool(
                payload.get("requires_vendor_status_check")
            ),
            operator_reconcile=bool(payload.get("operator_reconcile")),
            reservation_intact=bool(payload.get("reservation_intact")),
            activity_id_durable=bool(payload.get("activity_id_durable")),
            submit_attempted=bool(payload.get("submit_attempted")),
        )


@dataclass
class DurableJobContract:
    """Job identity + durability facts. Survives worker crash when persisted."""

    contract_version: str = DURABILITY_CONTRACT_VERSION
    fingerprint: str | None = None
    state: DurabilityState = DurabilityState.REQUESTED
    activity_id: str | None = None
    reservation_id: str | None = None
    error_class: JobErrorClass = JobErrorClass.NONE
    recovery: RecoveryFlags = field(default_factory=RecoveryFlags)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    activity_id_persisted_at: datetime | None = None
    reservation_persisted_at: datetime | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "fingerprint": self.fingerprint,
            "state": self.state.value,
            "activity_id": self.activity_id,
            "reservation_id": self.reservation_id,
            "error_class": self.error_class.value,
            "recovery": self.recovery.to_payload(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "activity_id_persisted_at": (
                self.activity_id_persisted_at.isoformat()
                if self.activity_id_persisted_at
                else None
            ),
            "reservation_persisted_at": (
                self.reservation_persisted_at.isoformat()
                if self.reservation_persisted_at
                else None
            ),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> DurableJobContract | None:
        if not payload:
            return None
        return cls(
            contract_version=str(
                payload.get("contract_version") or DURABILITY_CONTRACT_VERSION
            ),
            fingerprint=payload.get("fingerprint"),
            state=DurabilityState(payload.get("state") or DurabilityState.REQUESTED),
            activity_id=payload.get("activity_id"),
            reservation_id=payload.get("reservation_id"),
            error_class=JobErrorClass(payload.get("error_class") or JobErrorClass.NONE),
            recovery=RecoveryFlags.from_payload(payload.get("recovery")),
            created_at=_parse_dt(payload.get("created_at")) or _now(),
            updated_at=_parse_dt(payload.get("updated_at")) or _now(),
            activity_id_persisted_at=_parse_dt(payload.get("activity_id_persisted_at")),
            reservation_persisted_at=_parse_dt(payload.get("reservation_persisted_at")),
        )


def _parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def new_durability(*, fingerprint: str | None = None) -> DurableJobContract:
    stamp = _now()
    return DurableJobContract(
        fingerprint=fingerprint,
        state=DurabilityState.REQUESTED,
        created_at=stamp,
        updated_at=stamp,
    )


def forbids_auto_resubmit(state: DurabilityState) -> bool:
    return state in NEVER_AUTO_RESUBMIT_FROM or state == DurabilityState.UNKNOWN_VENDOR_STATE


def is_auto_resubmit_target(state: DurabilityState) -> bool:
    return state in RESUBMIT_STATES


@dataclass(frozen=True)
class CrashRecoveryPlan:
    """Restart disposition. may_resubmit is always False."""

    state: DurabilityState
    error_class: JobErrorClass
    requires_vendor_status_check: bool
    operator_reconcile: bool
    reservation_intact: bool
    activity_id_durable: bool
    interrupt_public_job: bool
    message: str
    may_resubmit: Literal[False] = False


def plan_crash_recovery(
    durability: DurableJobContract | None,
    *,
    public_terminal: bool,
) -> CrashRecoveryPlan:
    """Classify a persisted job after worker/process death.

    Never auto-resubmits. UNKNOWN_VENDOR_STATE stays there.
    activity_id and reservation_id are facts on the contract; this plan
    only chooses the next durability state and flags.
    """
    if public_terminal:
        state = durability.state if durability else DurabilityState.CONSUMED
        return CrashRecoveryPlan(
            state=state,
            error_class=durability.error_class if durability else JobErrorClass.NONE,
            requires_vendor_status_check=False,
            operator_reconcile=False,
            reservation_intact=bool(durability and durability.reservation_id),
            activity_id_durable=bool(durability and durability.activity_id),
            interrupt_public_job=False,
            message="terminal public job; durability unchanged",
        )

    if durability is None:
        return CrashRecoveryPlan(
            state=DurabilityState.RECOVERY_REQUIRED,
            error_class=JobErrorClass.WORKER_CRASH,
            requires_vendor_status_check=False,
            operator_reconcile=False,
            reservation_intact=False,
            activity_id_durable=False,
            interrupt_public_job=True,
            message=(
                "Job interrupted by process restart. Execution was not recovered "
                "and will not be retried automatically."
            ),
        )

    if durability.state == DurabilityState.UNKNOWN_VENDOR_STATE:
        return CrashRecoveryPlan(
            state=DurabilityState.UNKNOWN_VENDOR_STATE,
            error_class=JobErrorClass.VENDOR_UNKNOWN,
            requires_vendor_status_check=False,
            operator_reconcile=True,
            reservation_intact=durability.reservation_id is not None,
            activity_id_durable=durability.activity_id is not None,
            interrupt_public_job=False,
            message=(
                "UNKNOWN_VENDOR_STATE after restart. Operator reconcile only. "
                "Never auto-resubmit."
            ),
        )

    if durability.state == DurabilityState.JOINED:
        return CrashRecoveryPlan(
            state=DurabilityState.JOINED,
            error_class=JobErrorClass.NONE,
            requires_vendor_status_check=False,
            operator_reconcile=False,
            reservation_intact=durability.reservation_id is not None,
            activity_id_durable=durability.activity_id is not None,
            interrupt_public_job=False,
            message="Joined follower; inherit the leader. Do not submit.",
        )

    if durability.activity_id or durability.recovery.activity_id_durable:
        return CrashRecoveryPlan(
            state=DurabilityState.RECOVERY_REQUIRED,
            error_class=JobErrorClass.WORKER_CRASH,
            requires_vendor_status_check=True,
            operator_reconcile=False,
            reservation_intact=durability.reservation_id is not None,
            activity_id_durable=True,
            interrupt_public_job=False,
            message=(
                "Worker crashed with a persisted activity_id. Resume vendor "
                "status only. Never resubmit."
            ),
        )

    if (
        durability.state in {DurabilityState.SUBMITTING, DurabilityState.SUBMITTED}
        or durability.recovery.submit_attempted
    ):
        return CrashRecoveryPlan(
            state=DurabilityState.UNKNOWN_VENDOR_STATE,
            error_class=JobErrorClass.VENDOR_UNKNOWN,
            requires_vendor_status_check=False,
            operator_reconcile=True,
            reservation_intact=durability.reservation_id is not None,
            activity_id_durable=False,
            interrupt_public_job=False,
            message=(
                "Submit may have reached the vendor; activity_id is not durable. "
                "UNKNOWN_VENDOR_STATE. Never auto-resubmit."
            ),
        )

    if durability.reservation_id:
        return CrashRecoveryPlan(
            state=DurabilityState.RECOVERY_REQUIRED,
            error_class=JobErrorClass.WORKER_CRASH,
            requires_vendor_status_check=False,
            operator_reconcile=False,
            reservation_intact=True,
            activity_id_durable=False,
            interrupt_public_job=False,
            message=(
                "Worker crashed with a persisted reservation_id. Keep the "
                "reservation. Do not auto-resubmit."
            ),
        )

    if durability.state in _TERMINAL_DURABILITY:
        return CrashRecoveryPlan(
            state=durability.state,
            error_class=durability.error_class,
            requires_vendor_status_check=False,
            operator_reconcile=False,
            reservation_intact=False,
            activity_id_durable=False,
            interrupt_public_job=False,
            message="terminal durability state; unchanged",
        )

    return CrashRecoveryPlan(
        state=DurabilityState.RECOVERY_REQUIRED,
        error_class=JobErrorClass.WORKER_CRASH,
        requires_vendor_status_check=False,
        operator_reconcile=False,
        reservation_intact=False,
        activity_id_durable=False,
        interrupt_public_job=True,
        message=(
            "Job interrupted by process restart. Execution was not recovered "
            "and will not be retried automatically."
        ),
    )
