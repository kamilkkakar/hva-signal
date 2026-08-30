# LIVE-L mock vendor

In-process only. `vendor_kind="mock"`. No FortyGuard. No HTTP.

Full note: `workforce/live_execution/LIVE_L_MOCK_VENDOR.md` (gitignored workforce tree).

## Imports

```python
from app.integrations.mock_vendor import (
    CRASH_MATRIX_POINTS,
    CrashController,
    CrashPoint,
    InMemoryMockActivityStore,
    InMemoryMockResultCache,
    MockVendorAdapter,
    resume_mock_vendor_lifecycle,
    run_mock_vendor_lifecycle,
)
from app.services.hosted_live_mock_vendor import run_mock_vendor_lifecycle
```

## Crash hooks (LIVE-E / LIVE-M)

```python
run_mock_vendor_lifecycle(..., crash_at=CrashPoint.AFTER_ACTIVITY_ID)

crash = CrashController()
crash.arm(CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID)
crash.on_any(lambda point, phase: ...)
run_mock_vendor_lifecycle(..., crash=crash)
resume_mock_vendor_lifecycle(..., job_id=result.job_id)  # default crash_at=NONE
```

Nine sites: `before_reserve`, `after_reserve`, `before_vendor_submit`, `during_submit`, `after_submit_before_activity_id`, `after_activity_id`, `during_vendor_processing`, `after_result_before_cache`, `after_cache_before_consume`.

`UNKNOWN_VENDOR_STATE` never auto-resubmits. Share store/ledger/activities/cache/vendor across crash and resume.
