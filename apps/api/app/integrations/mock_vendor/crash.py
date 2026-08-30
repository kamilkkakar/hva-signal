"""Controllable crash points for the hosted-live chaos / crash matrix.

LIVE-E and LIVE-M hook here. This module never talks to a vendor network.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from app.integrations.mock_vendor.types import LifecyclePhase

CrashHook = Callable[["CrashPoint", LifecyclePhase], None]


class CrashPoint(str, Enum):
    """The nine program crash sites plus NONE.

    Names are the hook contract. Do not rename without updating LIVE-E / LIVE-M.
    """

    NONE = "none"
    BEFORE_RESERVE = "before_reserve"
    AFTER_RESERVE = "after_reserve"
    BEFORE_VENDOR_SUBMIT = "before_vendor_submit"
    DURING_SUBMIT = "during_submit"
    AFTER_SUBMIT_BEFORE_ACTIVITY_ID = "after_submit_before_activity_id"
    AFTER_ACTIVITY_ID = "after_activity_id"
    DURING_VENDOR_PROCESSING = "during_vendor_processing"
    AFTER_RESULT_BEFORE_CACHE = "after_result_before_cache"
    AFTER_CACHE_BEFORE_CONSUME = "after_cache_before_consume"


CRASH_MATRIX_POINTS: tuple[CrashPoint, ...] = (
    CrashPoint.BEFORE_RESERVE,
    CrashPoint.AFTER_RESERVE,
    CrashPoint.BEFORE_VENDOR_SUBMIT,
    CrashPoint.DURING_SUBMIT,
    CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID,
    CrashPoint.AFTER_ACTIVITY_ID,
    CrashPoint.DURING_VENDOR_PROCESSING,
    CrashPoint.AFTER_RESULT_BEFORE_CACHE,
    CrashPoint.AFTER_CACHE_BEFORE_CONSUME,
)


class SimulatedCrash(RuntimeError):
    """Injected worker death. Not a vendor or network error."""

    def __init__(self, point: CrashPoint, phase: LifecyclePhase) -> None:
        self.point = point
        self.phase = phase
        super().__init__(f"simulated_crash:{point.value}")


class CrashController:
    """Arm one crash site and/or observe every site.

    Hook from LIVE-E / LIVE-M::

        crash = CrashController()
        crash.arm(CrashPoint.AFTER_ACTIVITY_ID)
        crash.on(CrashPoint.AFTER_ACTIVITY_ID, lambda p, phase: log(p, phase))
        crash.on_any(lambda p, phase: seen.append((p, phase)))

        run_mock_vendor_lifecycle(..., crash=crash)

    Or pass ``crash_at=CrashPoint.AFTER_RESERVE`` into the runner.
    """

    def __init__(self, crash_at: CrashPoint = CrashPoint.NONE) -> None:
        if crash_at not in CrashPoint:
            raise ValueError(f"unknown crash point: {crash_at}")
        self.crash_at = crash_at
        self._hooks: dict[CrashPoint, list[CrashHook]] = {}
        self._any: list[CrashHook] = []
        self.visited: list[tuple[CrashPoint, LifecyclePhase]] = []

    def arm(self, point: CrashPoint) -> CrashController:
        self.crash_at = point
        return self

    def disarm(self) -> CrashController:
        self.crash_at = CrashPoint.NONE
        return self

    def on(self, point: CrashPoint, hook: CrashHook) -> CrashController:
        self._hooks.setdefault(point, []).append(hook)
        return self

    def on_any(self, hook: CrashHook) -> CrashController:
        self._any.append(hook)
        return self

    def check(self, point: CrashPoint, *, phase: LifecyclePhase) -> None:
        if point is CrashPoint.NONE:
            return
        self.visited.append((point, phase))
        for hook in self._any:
            hook(point, phase)
        for hook in self._hooks.get(point, ()):
            hook(point, phase)
        if self.crash_at == point:
            raise SimulatedCrash(point, phase)
