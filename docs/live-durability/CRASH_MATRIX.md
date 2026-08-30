# CRASH MATRIX — HVA-SIGNAL live durability (LIVE-E)

**Worktree:** `F:\cursor\hackathon-live-e-crash-matrix`  
**Branch:** `feat/live-e-crash-matrix`  
**Date:** 2026-08-30  
**Vendor:** fake only. No FortyGuard. No real vendor. No push.

This document is the durable-worker crash contract. The same rows are executable as `CRASH_MATRIX_ROWS` in `app.domain.live_crash_matrix.contract`.

## Hard rules

1. **`UNKNOWN_VENDOR_STATE` never becomes an automatic resubmit.** Recovery may stay unknown or escalate to `RECOVERY_REQUIRED` / operator reconcile.
2. **No blind paid retry.** `force_resubmit` and `automatic_paid_retry` are rejected when submit may already have happened.
3. **Cache / dedupe before spend.** Reserve before submit. Persist `activity_id` before treating submit as durable. **Cache, then consume.**
4. Do not claim mathematical exactly-once. Best achievable is **at-most-one-submit** when `activity_id` is known, and **no second submit** when it is not.
5. Hosted live / demo allowance **default OFF** (`Settings.demo_allowance_enabled is False`).

## Worker states (LIVE-C contract)

`REQUESTED` → `VALIDATED` → (`CACHE_HIT` | `JOINED`) → `ALLOWANCE_RESERVED` → `SUBMITTING` → `SUBMITTED` → `ACTIVITY_ID_PERSISTED` → `PROCESSING` → `RESULT_RECEIVED` → `NORMALIZED` → `CACHED` → `CONSUMED`

Failure / uncertainty: `FAILED_PRE_SUBMIT`, `FAILED_POST_SUBMIT`, `UNKNOWN_VENDOR_STATE`, `RECOVERY_REQUIRED`.

## Full matrix

| # | Crash point | State at crash | Restart | Spend risk | Dedupe | Recovery | Production |
|---|---|---|---|---|---|---|---|
| 1 | **before reserve** | `VALIDATED` | Continue from cache check | **none** — no reservation, no vendor | Join in-flight job; at most one later reserve+submit | Recheck cache; reserve once; submit once | **not implemented** |
| 2 | **after reserve** | `ALLOWANCE_RESERVED` | Continue to submit after cache recheck | **reservation held**, vendor 0 | Join existing reservation; no second reserve | If cache appeared: release + reuse. Else submit once | **not implemented** |
| 3 | **before vendor submit** | `ALLOWANCE_RESERVED` | Same as #2 | **reservation held**, vendor 0 | Join reservation; one submit on recovery | Cache recheck, then one submit | **not implemented** |
| 4 | **during submit** | `UNKNOWN_VENDOR_STATE` | **No automatic resubmit** | **unknown** — vendor may have accepted; no `activity_id` | Join uncertain job; **must not** submit again | Stay unknown / `RECOVERY_REQUIRED`. `force_resubmit` rejected | **not implemented** |
| 5 | **after submit before activity_id save** | `UNKNOWN_VENDOR_STATE` | **No automatic resubmit** | **vendor accepted, handle lost** | Join uncertain job; submit count stays 1 | Operator reconcile only. Never invent a second submit | **not implemented** |
| 6 | **after activity_id save** | `ACTIVITY_ID_PERSISTED` | Resume poll / fetch | Vendor 1; reservation still held | Join in-flight; same `activity_id` | Poll → normalize → cache → consume | **not implemented** |
| 7 | **during vendor processing** | `PROCESSING` | Resume poll | Vendor in flight; extra submit would double-spend | Join processing job; poll same id | Poll until result, then cache and consume | **not implemented** |
| 8 | **after result before cache** | `NORMALIZED` | Cache then consume | Vendor already spent; result unprotected until cache | Finish cache+consume; no submit | Write cache, consume once. If result blob lost but id remains: resume fetch, never resubmit | **not implemented** |
| 9 | **after cache before allowance consume** | `CACHED` | Consume only | Cache present; **reservation leak** risk, not double vendor spend | Cache hit; no reserve, no submit | Consume if still `RESERVED`. Later callers reuse cache | **not implemented** |

### Restart / spend / dedupe / recovery (prose)

**1. before reserve**  
Restart at `VALIDATED`. Spend risk is none. A duplicate joins the same job. Recovery rechecks cache, then may reserve and submit once.

**2. after reserve**  
Restart with the same reservation. Units are reserved, not consumed. Duplicates join the reservation. Recovery rechecks cache (LIVE-H): a newly appeared compatible cache **releases** the reservation and must not submit.

**3. before vendor submit**  
Same spend and dedupe profile as #2. The process died after the last cache recheck and before `SUBMITTING`. Recovery may submit once. That is not a paid retry; no vendor contact has occurred.

**4. during submit**  
`submit_attempted=True`, no persisted `activity_id`. The fake vendor increments submit count (orphaned activity). Restart must **not** submit. Duplicates must **not** submit. This is `UNKNOWN_VENDOR_STATE`.

**5. after submit before activity_id save**  
The vendor returned an id that was not written. Spend already happened. Blind retry is a second paid call. Stay unknown. Dedupe shares that unknown job.

**6. after activity_id save**  
The only legal resume token exists. Restart polls. Duplicates join and poll the same id. Consume happens after cache.

**7. during vendor processing**  
Same as #6 with state `PROCESSING`.

**8. after result before cache**  
Result is on the job record. Restart writes cache then consumes. Do not buy the snapshot again.

**9. after cache before allowance consume**  
Result is reusable. Restart consumes the reservation once. A second caller is a cache hit.

## Honest exactly-once

The vendor (when one exists) is not assumed idempotent. This matrix therefore claims:

- **At most one submit** when recovery can prove submit has not started (`VALIDATED`, `ALLOWANCE_RESERVED`).
- **No second submit** when submit started or `activity_id` is missing (`UNKNOWN_VENDOR_STATE`).
- **Poll-only** when `activity_id` is persisted.
- Not mathematical exactly-once.

## Production gaps (this tree)

Inspected by `inspect_production_gaps()`:

| Gap | Evidence |
|---|---|
| No J3/J4 durable worker SM | `ExecutionState` is `NOT_STARTED` / `RUNNING` / `FINISHED` / `INTERRUPTED` |
| No `UNKNOWN_VENDOR_STATE` in production lifecycle | Missing from `job_lifecycle.py` |
| `AnalysisJob` has no `vendor_activity_id` | LIVE-A/D persistence gap |
| Consume-before-submit | `recheck_demo_reservation_before_paid_submission` calls `ledger.consume` before a vendor submit — inverts points 8–9 |
| J0 ledger / job store | Process death wipes reservations and jobs; J0 restart must **not** auto-resubmit |
| Nine crash points absent from production runner | No `CrashPoint` / hosted-live runner in this product tree |

The **harness** (`CrashMatrixRunner` + `FakeLiveVendor`) implements all nine transitions so LIVE-M chaos tests and LIVE-L mock hooks can attach to `CrashPoint`.

Sibling worktrees (`hackathon-hosted-live-prevendor`) implement a **subset** (`before_submit`, `after_submit_before_activity_id`, `after_activity_id`, `during_processing`) and are not merged here.

## How siblings should hook

```python
from app.domain.live_crash_matrix import CRASH_MATRIX_ROWS, CrashPoint, decide_recovery
from app.services.live_crash_matrix import CrashMatrixRunner, FakeLiveVendor
```

- **LIVE-C:** durable states live in `DurableWorkerState`.
- **LIVE-D:** unknown-without-`activity_id` and poll-if-known are encoded in `decide_recovery`.
- **LIVE-L:** replace `FakeLiveVendor` if needed; keep `begin_unacked_submit` / `submit` / `get_status`.
- **LIVE-M:** inject `crash_at=CrashPoint.*` on `CrashMatrixRunner.acquire`.
- **LIVE-H:** cache recheck is in `_submit_path` and the after-reserve recovery test.

## Tests

```text
pytest apps/api/tests/unit/test_live_crash_matrix_*.py
```

From `hackathon-live-e-crash-matrix/apps/api`.
