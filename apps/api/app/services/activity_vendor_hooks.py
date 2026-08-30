"""Mockable vendor hooks for activity-id resume. Poll and fetch only.

LIVE-D never submits through this surface. LIVE-L may implement a richer
mock; this protocol is the resume contract. No FortyGuard. No network.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from app.domain.activity_reconciliation import VendorPollStatus


class VendorActivityStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    status: VendorPollStatus
    detail: str | None = None


class VendorActivityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    payload: dict[str, Any]


class ActivityVendorHooks(Protocol):
    """Resume surface. Implementations must not be invoked for submit."""

    def poll_status(self, activity_id: str) -> VendorActivityStatus: ...

    def fetch_result(self, activity_id: str) -> VendorActivityResult: ...


class ScriptedVendorHooks:
    """In-process test double. Submit is forbidden and counted if misused."""

    def __init__(
        self,
        *,
        statuses: list[VendorPollStatus] | None = None,
        result_payload: dict[str, Any] | None = None,
    ) -> None:
        self._statuses = list(statuses or [VendorPollStatus.PROCESSING])
        self._result_payload = result_payload or {"type": "FeatureCollection", "features": []}
        self.poll_calls: list[str] = []
        self.fetch_calls: list[str] = []
        self.submit_calls: list[str] = []

    def poll_status(self, activity_id: str) -> VendorActivityStatus:
        self.poll_calls.append(activity_id)
        if not activity_id or not activity_id.strip():
            return VendorActivityStatus(
                activity_id=activity_id,
                status=VendorPollStatus.NOT_FOUND,
                detail="empty_activity_id",
            )
        if not self._statuses:
            status = VendorPollStatus.PROCESSING
        else:
            status = self._statuses.pop(0)
            if not self._statuses:
                self._statuses.append(status)
        return VendorActivityStatus(activity_id=activity_id, status=status)

    def fetch_result(self, activity_id: str) -> VendorActivityResult:
        self.fetch_calls.append(activity_id)
        return VendorActivityResult(activity_id=activity_id, payload=dict(self._result_payload))

    def submit(self, *_args: object, **_kwargs: object) -> str:
        self.submit_calls.append("forbidden")
        raise RuntimeError("activity reconciler must never call vendor submit")
