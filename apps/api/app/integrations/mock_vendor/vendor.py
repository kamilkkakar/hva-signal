"""In-process mock vendor. Zero sockets. Zero FortyGuard. Zero credentials.

Supports:
- processing delay (poll ticks; optional zero-default wall sleep)
- duplicate fingerprints (reuse same activity_id or mint a new one)
- unknown-after-submit (return an id, then forget it)
- DURING_SUBMIT crash injection via CrashController
"""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from time import sleep
from typing import Any, Literal
from uuid import uuid4

from app.integrations.mock_vendor.crash import CrashController, CrashPoint
from app.integrations.mock_vendor.types import (
    MOCK_VENDOR_KIND,
    LifecyclePhase,
    MockVendorRequest,
    MockVendorStatus,
)


class MockVendorError(RuntimeError):
    """Mock vendor refused or failed. Never a network error."""


class MockVendorUnknownActivity(MockVendorError):
    """activity_id is not known to the mock. Used for unknown-after-submit."""


class MockVendorTimeout(MockVendorError):
    """Configured never-complete poll."""


class InProcessMockVendor:
    """Scriptable submit/poll store. TEST / chaos only."""

    kind: Literal["mock"] = MOCK_VENDOR_KIND

    def __init__(
        self,
        tiles_geojson: dict[str, Any],
        *,
        processing_delay_ticks: int = 1,
        processing_delay_s: float = 0.0,
        never_complete: bool = False,
        fail_on_submit: bool = False,
        unknown_after_submit: bool = False,
        fingerprint_mode: Literal["new_activity", "reuse_activity"] = "new_activity",
        crash: CrashController | None = None,
    ) -> None:
        if tiles_geojson.get("type") != "FeatureCollection":
            raise MockVendorError("mock vendor requires a FeatureCollection")
        if processing_delay_ticks < 1:
            raise MockVendorError("processing_delay_ticks must be >= 1")
        if processing_delay_s < 0:
            raise MockVendorError("processing_delay_s must be >= 0")
        if fingerprint_mode not in {"new_activity", "reuse_activity"}:
            raise MockVendorError("fingerprint_mode must be new_activity or reuse_activity")
        self._tiles = deepcopy(tiles_geojson)
        self.processing_delay_ticks = processing_delay_ticks
        self.processing_delay_s = processing_delay_s
        self.never_complete = never_complete
        self.fail_on_submit = fail_on_submit
        self.unknown_after_submit = unknown_after_submit
        self.fingerprint_mode = fingerprint_mode
        self.crash = crash
        self._lock = Lock()
        self._activities: dict[str, dict[str, Any]] = {}
        self._by_fingerprint: dict[str, str] = {}
        self._forgotten: set[str] = set()
        self.submit_count = 0
        self.paid_submit_count = 0
        self.poll_count = 0

    def bind_crash(self, crash: CrashController | None) -> None:
        self.crash = crash

    def submit(self, spec: MockVendorRequest) -> str:
        if spec.vendor_kind != MOCK_VENDOR_KIND:
            raise MockVendorError("mock vendor refuses non-mock vendor_kind")
        with self._lock:
            self.submit_count += 1
            if self.fail_on_submit:
                raise MockVendorError("mock_submit_failed")
            if (
                self.fingerprint_mode == "reuse_activity"
                and spec.request_fingerprint in self._by_fingerprint
            ):
                return self._by_fingerprint[spec.request_fingerprint]
        if self.crash is not None:
            self.crash.check(CrashPoint.DURING_SUBMIT, phase=LifecyclePhase.SUBMITTING)
        with self._lock:
            activity_id = f"mock_{uuid4().hex[:12]}"
            self._activities[activity_id] = {
                "status": "processing",
                "ticks": 0,
                "fingerprint": spec.request_fingerprint,
            }
            self._by_fingerprint[spec.request_fingerprint] = activity_id
            self.paid_submit_count += 1
            if self.unknown_after_submit:
                self._forget_unlocked(activity_id)
            return activity_id

    def get_status(self, activity_id: str) -> MockVendorStatus:
        if self.processing_delay_s > 0:
            sleep(self.processing_delay_s)
        with self._lock:
            self.poll_count += 1
            if activity_id in self._forgotten or activity_id not in self._activities:
                raise MockVendorUnknownActivity(
                    f"unknown mock activity_id {activity_id}"
                )
            state = self._activities[activity_id]
            state["ticks"] += 1
            if self.never_complete or state["ticks"] < self.processing_delay_ticks:
                return MockVendorStatus(
                    status="processing",
                    activity_id=activity_id,
                    fingerprint=state["fingerprint"],
                )
            tiles = deepcopy(self._tiles)
            state["status"] = "succeeded"
            return MockVendorStatus(
                status="succeeded",
                activity_id=activity_id,
                result=tiles,
                fingerprint=state["fingerprint"],
            )

    def forget_activity(self, activity_id: str) -> None:
        """Chaos hook: lose the vendor handle after a successful submit."""
        with self._lock:
            self._forget_unlocked(activity_id)

    def known_activity_ids(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._activities.keys())

    def forgotten_activity_ids(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._forgotten)

    def activity_id_for_fingerprint(self, request_fingerprint: str) -> str | None:
        with self._lock:
            return self._by_fingerprint.get(request_fingerprint)

    def _forget_unlocked(self, activity_id: str) -> None:
        self._forgotten.add(activity_id)
        self._activities.pop(activity_id, None)
