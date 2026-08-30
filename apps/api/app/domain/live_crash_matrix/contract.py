"""Executable crash-matrix table. Tests and the CRASH MATRIX doc share this."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.live_crash_matrix.states import (
    CRASH_POINTS,
    CrashPoint,
    DurableWorkerState,
    RecoveryAction,
    SpendRisk,
)


class CrashMatrixRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int = Field(ge=1, le=9)
    point: CrashPoint
    crashed_state: DurableWorkerState
    restart_action: RecoveryAction
    recover_outcome: Literal["ready", "uncertain", "recovery_required"]
    spend_risk: SpendRisk
    submit_count_at_crash: int = Field(ge=0)
    reserved_at_crash: int = Field(ge=0)
    consumed_at_crash: int = Field(ge=0)
    activity_id_at_crash: bool
    cache_at_crash: bool
    result_at_crash: bool
    duplicate_outcome: Literal["ready", "uncertain", "reused"]
    production_transition: Literal["not_implemented", "partial", "implemented"]
    restart_behavior: str
    spend_risk_note: str
    dedupe_behavior: str
    recovery_behavior: str


def matrix_row(point: CrashPoint) -> CrashMatrixRow:
    for row in CRASH_MATRIX_ROWS:
        if row.point == point:
            return row
    raise KeyError(point)


CRASH_MATRIX_ROWS: tuple[CrashMatrixRow, ...] = (
    CrashMatrixRow(
        seq=1,
        point=CrashPoint.BEFORE_RESERVE,
        crashed_state=DurableWorkerState.VALIDATED,
        restart_action=RecoveryAction.CONTINUE_FROM_CACHE_CHECK,
        recover_outcome="ready",
        spend_risk=SpendRisk.NONE,
        submit_count_at_crash=0,
        reserved_at_crash=0,
        consumed_at_crash=0,
        activity_id_at_crash=False,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior=(
            "Worker restarts at VALIDATED, rechecks cache, then may reserve once."
        ),
        spend_risk_note="No reservation and no vendor contact. Spend risk is none.",
        dedupe_behavior=(
            "Duplicate joins the in-flight VALIDATED job. One reserve and one submit."
        ),
        recovery_behavior=(
            "Continue from cache check. Submit is allowed only after a new reserve."
        ),
    ),
    CrashMatrixRow(
        seq=2,
        point=CrashPoint.AFTER_RESERVE,
        crashed_state=DurableWorkerState.ALLOWANCE_RESERVED,
        restart_action=RecoveryAction.CONTINUE_TO_SUBMIT,
        recover_outcome="ready",
        spend_risk=SpendRisk.RESERVATION_HELD,
        submit_count_at_crash=0,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=False,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior=(
            "Reuse the existing reservation. Recheck cache immediately before submit."
        ),
        spend_risk_note=(
            "Units are reserved, not consumed. Vendor spend is still zero."
        ),
        dedupe_behavior=(
            "Duplicate joins the reservation / in-flight job. No second reserve."
        ),
        recovery_behavior=(
            "If a compatible cache appeared, release reservation and reuse. "
            "Otherwise submit once."
        ),
    ),
    CrashMatrixRow(
        seq=3,
        point=CrashPoint.BEFORE_VENDOR_SUBMIT,
        crashed_state=DurableWorkerState.ALLOWANCE_RESERVED,
        restart_action=RecoveryAction.CONTINUE_TO_SUBMIT,
        recover_outcome="ready",
        spend_risk=SpendRisk.RESERVATION_HELD,
        submit_count_at_crash=0,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=False,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior=(
            "Same as after-reserve: reservation held, submit not yet attempted."
        ),
        spend_risk_note="Reservation held. Vendor has not been contacted.",
        dedupe_behavior="Join reservation. At most one submit on the recovery path.",
        recovery_behavior="Cache recheck, then one submit. Not a paid retry.",
    ),
    CrashMatrixRow(
        seq=4,
        point=CrashPoint.DURING_SUBMIT,
        crashed_state=DurableWorkerState.UNKNOWN_VENDOR_STATE,
        restart_action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
        recover_outcome="uncertain",
        spend_risk=SpendRisk.UNKNOWN_VENDOR_MAY_HAVE_ACCEPTED,
        submit_count_at_crash=1,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=False,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="uncertain",
        production_transition="not_implemented",
        restart_behavior=(
            "Remain UNKNOWN_VENDOR_STATE. Never automatic resubmit. "
            "Escalate only to RECOVERY_REQUIRED / operator reconcile."
        ),
        spend_risk_note=(
            "Vendor may have accepted. activity_id is unknown. Blind retry "
            "could double-spend."
        ),
        dedupe_behavior=(
            "Duplicates join the uncertain job and must not open a second submit."
        ),
        recovery_behavior=(
            "Operator-safe reconcile only. force_resubmit is rejected."
        ),
    ),
    CrashMatrixRow(
        seq=5,
        point=CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID,
        crashed_state=DurableWorkerState.UNKNOWN_VENDOR_STATE,
        restart_action=RecoveryAction.NO_AUTOMATIC_RESUBMIT,
        recover_outcome="uncertain",
        spend_risk=SpendRisk.VENDOR_ACCEPTED_HANDLE_LOST,
        submit_count_at_crash=1,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=False,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="uncertain",
        production_transition="not_implemented",
        restart_behavior=(
            "Vendor accepted but activity_id was not persisted. Stay unknown. "
            "No automatic resubmit."
        ),
        spend_risk_note=(
            "Paid submit happened. Handle was lost. A second submit is a "
            "blind paid retry."
        ),
        dedupe_behavior="Join uncertain job. Submit count must stay at one.",
        recovery_behavior=(
            "RECOVERY_REQUIRED / operator reconcile. Never invent a second submit."
        ),
    ),
    CrashMatrixRow(
        seq=6,
        point=CrashPoint.AFTER_ACTIVITY_ID_SAVE,
        crashed_state=DurableWorkerState.ACTIVITY_ID_PERSISTED,
        restart_action=RecoveryAction.RESUME_POLL,
        recover_outcome="ready",
        spend_risk=SpendRisk.VENDOR_IN_FLIGHT,
        submit_count_at_crash=1,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=True,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior="Resume status poll / result fetch for the saved activity_id.",
        spend_risk_note="Vendor already accepted. Reservation still held until consume.",
        dedupe_behavior="Join in-flight job. Same activity_id. No second submit.",
        recovery_behavior="Poll → normalize → cache → consume. Never resubmit.",
    ),
    CrashMatrixRow(
        seq=7,
        point=CrashPoint.DURING_VENDOR_PROCESSING,
        crashed_state=DurableWorkerState.PROCESSING,
        restart_action=RecoveryAction.RESUME_POLL,
        recover_outcome="ready",
        spend_risk=SpendRisk.VENDOR_IN_FLIGHT,
        submit_count_at_crash=1,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=True,
        cache_at_crash=False,
        result_at_crash=False,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior="Resume poll on the persisted activity_id.",
        spend_risk_note="Vendor work is in flight. Additional submit would double-spend.",
        dedupe_behavior="Join processing job. Poll the same activity_id.",
        recovery_behavior="Poll until result, then cache and consume.",
    ),
    CrashMatrixRow(
        seq=8,
        point=CrashPoint.AFTER_RESULT_BEFORE_CACHE,
        crashed_state=DurableWorkerState.NORMALIZED,
        restart_action=RecoveryAction.CACHE_THEN_CONSUME,
        recover_outcome="ready",
        spend_risk=SpendRisk.RESULT_UNPROTECTED,
        submit_count_at_crash=1,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=True,
        cache_at_crash=False,
        result_at_crash=True,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior=(
            "Persist/reuse the received result. Write cache, then consume. "
            "If the result blob was lost but activity_id remains, resume fetch — "
            "never resubmit."
        ),
        spend_risk_note=(
            "Vendor spend already occurred. Losing the cache write wastes the "
            "result, not a reason to buy another."
        ),
        dedupe_behavior="Join and finish cache+consume. No vendor submit.",
        recovery_behavior="Cache then consume. Submit count stays at one.",
    ),
    CrashMatrixRow(
        seq=9,
        point=CrashPoint.AFTER_CACHE_BEFORE_CONSUME,
        crashed_state=DurableWorkerState.CACHED,
        restart_action=RecoveryAction.CONSUME_ONLY,
        recover_outcome="ready",
        spend_risk=SpendRisk.CACHE_WITHOUT_CONSUME,
        submit_count_at_crash=1,
        reserved_at_crash=1,
        consumed_at_crash=0,
        activity_id_at_crash=True,
        cache_at_crash=True,
        result_at_crash=True,
        duplicate_outcome="ready",
        production_transition="not_implemented",
        restart_behavior="Cache hit. Consume the reservation. Do not submit.",
        spend_risk_note=(
            "Result is cached. Reservation leak (never consumed) is the risk, "
            "not double vendor spend. Do not consume twice."
        ),
        dedupe_behavior="CACHE_HIT / reuse. Duplicates must not reserve or submit.",
        recovery_behavior="Consume once if still RESERVED. Later callers reuse cache.",
    ),
)


if len(CRASH_MATRIX_ROWS) != 9:
    raise RuntimeError("crash matrix must contain exactly nine points")
if tuple(row.point for row in CRASH_MATRIX_ROWS) != CRASH_POINTS:
    raise RuntimeError("crash matrix row order must match CrashPoint order")
