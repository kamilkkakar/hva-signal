"""In-process adapter. The only vendor this mock program may construct.

Refuses FortyGuard, HTTP clients, and any vendor_kind other than mock.
"""

from __future__ import annotations

from typing import Any, Literal

from app.integrations.mock_vendor.crash import CrashController
from app.integrations.mock_vendor.types import MOCK_VENDOR_KIND, MockVendorRequest, MockVendorStatus
from app.integrations.mock_vendor.vendor import InProcessMockVendor, MockVendorError


class MockVendorAdapter:
    """Thin in-process adapter. TEST / chaos only. No sockets."""

    kind: Literal["mock"] = MOCK_VENDOR_KIND

    def __init__(
        self,
        tiles_geojson: dict[str, Any] | None = None,
        *,
        vendor: InProcessMockVendor | None = None,
        processing_delay_ticks: int = 1,
        processing_delay_s: float = 0.0,
        never_complete: bool = False,
        fail_on_submit: bool = False,
        unknown_after_submit: bool = False,
        fingerprint_mode: Literal["new_activity", "reuse_activity"] = "new_activity",
        crash: CrashController | None = None,
    ) -> None:
        if vendor is not None:
            if vendor.kind != MOCK_VENDOR_KIND:
                raise MockVendorError("adapter refuses non-mock vendor")
            self._vendor = vendor
            if crash is not None:
                self._vendor.bind_crash(crash)
            return
        if tiles_geojson is None:
            raise MockVendorError("adapter requires tiles_geojson or a vendor")
        self._vendor = InProcessMockVendor(
            tiles_geojson,
            processing_delay_ticks=processing_delay_ticks,
            processing_delay_s=processing_delay_s,
            never_complete=never_complete,
            fail_on_submit=fail_on_submit,
            unknown_after_submit=unknown_after_submit,
            fingerprint_mode=fingerprint_mode,
            crash=crash,
        )

    @property
    def vendor(self) -> InProcessMockVendor:
        return self._vendor

    @property
    def submit_count(self) -> int:
        return self._vendor.submit_count

    @property
    def paid_submit_count(self) -> int:
        return self._vendor.paid_submit_count

    @property
    def poll_count(self) -> int:
        return self._vendor.poll_count

    def bind_crash(self, crash: CrashController | None) -> None:
        self._vendor.bind_crash(crash)

    def submit(self, spec: MockVendorRequest) -> str:
        if spec.vendor_kind != MOCK_VENDOR_KIND:
            raise MockVendorError("adapter refuses non-mock vendor_kind")
        return self._vendor.submit(spec)

    def get_status(self, activity_id: str) -> MockVendorStatus:
        return self._vendor.get_status(activity_id)

    def forget_activity(self, activity_id: str) -> None:
        self._vendor.forget_activity(activity_id)


def refuse_real_vendor(adapter: object) -> MockVendorAdapter:
    """Hard gate. LIVE-L never constructs or wraps a paid vendor."""
    if not isinstance(adapter, MockVendorAdapter):
        raise TypeError("hosted-live mock runner accepts MockVendorAdapter only")
    if adapter.kind != MOCK_VENDOR_KIND:
        raise TypeError("vendor_kind must remain mock")
    vendor = adapter.vendor
    if not isinstance(vendor, InProcessMockVendor) or vendor.kind != MOCK_VENDOR_KIND:
        raise TypeError("inner vendor must be InProcessMockVendor")
    return adapter
