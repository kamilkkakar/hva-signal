"""LIVE-E crash-matrix contract. Isolated from Agent A domain exports.

Executable specification for J3/J4 crash points. Fake vendor only.
UNKNOWN_VENDOR_STATE never becomes an automatic resubmit.
"""

from app.domain.live_crash_matrix.contract import (
    CRASH_MATRIX_ROWS,
    CrashMatrixRow,
    matrix_row,
)
from app.domain.live_crash_matrix.policy import (
    RecoveryDecision,
    decide_recovery,
)
from app.domain.live_crash_matrix.states import (
    CRASH_POINTS,
    DURABLE_WORKER_STATES,
    CrashPoint,
    DurableWorkerState,
    RecoveryAction,
    SpendRisk,
)

__all__ = [
    "CRASH_MATRIX_ROWS",
    "CRASH_POINTS",
    "DURABLE_WORKER_STATES",
    "CrashMatrixRow",
    "CrashPoint",
    "DurableWorkerState",
    "RecoveryAction",
    "RecoveryDecision",
    "SpendRisk",
    "decide_recovery",
    "matrix_row",
]
