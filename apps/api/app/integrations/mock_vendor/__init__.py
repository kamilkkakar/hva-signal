"""TEST-only in-process mock vendor for HVA-SIGNAL hosted-live.

No HTTP. No FortyGuard client. No credentials. Not a public route.

Hook crash points from LIVE-E / LIVE-M via CrashController or crash_at=.
"""

from app.integrations.mock_vendor.activity import (
    InMemoryMockActivityStore,
    MockActivityError,
)
from app.integrations.mock_vendor.adapter import MockVendorAdapter, refuse_real_vendor
from app.integrations.mock_vendor.cache import InMemoryMockResultCache
from app.integrations.mock_vendor.crash import (
    CRASH_MATRIX_POINTS,
    CrashController,
    CrashPoint,
    SimulatedCrash,
)
from app.integrations.mock_vendor.lifecycle import (
    build_mock_vendor_request,
    resume_mock_vendor_lifecycle,
    run_mock_vendor_lifecycle,
    selected_time_fingerprint,
)
from app.integrations.mock_vendor.types import (
    MOCK_VENDOR_KIND,
    LifecyclePhase,
    MockActivityRecord,
    MockLifecycleResult,
    MockVendorRequest,
    RestartAction,
)
from app.integrations.mock_vendor.vendor import (
    InProcessMockVendor,
    MockVendorError,
    MockVendorTimeout,
    MockVendorUnknownActivity,
)

__all__ = [
    "CRASH_MATRIX_POINTS",
    "CrashController",
    "CrashPoint",
    "InMemoryMockActivityStore",
    "InMemoryMockResultCache",
    "InProcessMockVendor",
    "LifecyclePhase",
    "MOCK_VENDOR_KIND",
    "MockActivityError",
    "MockActivityRecord",
    "MockLifecycleResult",
    "MockVendorAdapter",
    "MockVendorError",
    "MockVendorRequest",
    "MockVendorTimeout",
    "MockVendorUnknownActivity",
    "RestartAction",
    "SimulatedCrash",
    "build_mock_vendor_request",
    "refuse_real_vendor",
    "resume_mock_vendor_lifecycle",
    "run_mock_vendor_lifecycle",
    "selected_time_fingerprint",
]
