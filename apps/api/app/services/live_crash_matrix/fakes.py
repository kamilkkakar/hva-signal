"""In-process fake vendor for crash-matrix tests. No network. No FortyGuard."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.domain.live_crash_matrix.states import CrashPoint


class SimulatedCrash(RuntimeError):
    def __init__(self, point: CrashPoint) -> None:
        self.point = point
        super().__init__(f"simulated_crash:{point.value}")


class FakeLiveVendor:
    """Controllable mock. LIVE-L may replace this adapter; the crash points stay."""

    kind: str = "fake"

    def __init__(self, *, poll_ticks_until_ready: int = 1) -> None:
        self.poll_ticks_until_ready = poll_ticks_until_ready
        self.submit_count = 0
        self.poll_count = 0
        self.orphan_activity_ids: list[str] = []
        self._activities: dict[str, dict[str, Any]] = {}

    def begin_unacked_submit(self, fingerprint: str) -> None:
        """Submit left the process; caller crashed before the activity_id ack."""
        self.submit_count += 1
        activity_id = f"orphan_{uuid4().hex[:12]}"
        self._activities[activity_id] = {
            "status": "processing",
            "fingerprint": fingerprint,
            "orphaned": True,
            "ticks": 0,
            "result": None,
        }
        self.orphan_activity_ids.append(activity_id)

    def submit(self, fingerprint: str) -> str:
        self.submit_count += 1
        activity_id = f"fake_{uuid4().hex[:12]}"
        self._activities[activity_id] = {
            "status": "processing",
            "fingerprint": fingerprint,
            "orphaned": False,
            "ticks": 0,
            "result": None,
        }
        return activity_id

    def get_status(self, activity_id: str) -> dict[str, Any]:
        self.poll_count += 1
        state = self._activities.get(activity_id)
        if state is None:
            raise KeyError(f"unknown fake activity_id {activity_id}")
        state["ticks"] += 1
        if state["ticks"] >= self.poll_ticks_until_ready:
            state["status"] = "succeeded"
            state["result"] = {
                "ok": True,
                "activity_id": activity_id,
                "fingerprint": state["fingerprint"],
            }
        return {
            "status": state["status"],
            "activity_id": activity_id,
            "result": state["result"],
            "orphaned": state["orphaned"],
        }

    def fetch_result(self, activity_id: str) -> dict[str, Any]:
        status = self.get_status(activity_id)
        if status["status"] != "succeeded" or not isinstance(status["result"], dict):
            raise TimeoutError(f"fake activity {activity_id} not ready")
        return dict(status["result"])
