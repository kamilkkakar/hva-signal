# LIVE-K — Rate / Resource Guards

Date: 2026-08-30  
Worktree: `F:\cursor\hackathon-live-k`  
Branch: `feat/live-k-rate-guards`  
No FortyGuard. No real vendor. No push.

## What this is

Server-side admission for hosted-live **reserve**, **submit**, and **recovery polls**.

The HTTP anonymous limiter (`app/core/anonymous_guards.py`) still caps public POST volume. LIVE-K is the tighter layer so a demo stampede cannot reach the mock or a future vendor even if that HTTP cap is later raised.

This module does not authorize spend, enable hosted live, read credentials, or construct a vendor.

## Limits (hard ceilings)

Operator env may **lower** a value. It cannot raise above the ceiling. Client body / query / headers cannot set these at all.

| Cap | Ceiling / default | Env (lower only) |
|---|---|---|
| Max in-flight live jobs | **2** | `HVA_LIVE_MAX_IN_FLIGHT_JOBS` |
| Max active reservations | **2** | `HVA_LIVE_MAX_RESERVATIONS` |
| Max concurrent submits | **1** | `HVA_LIVE_MAX_CONCURRENT_SUBMITS` |
| Max recovery polls / activity | **16** | `HVA_LIVE_MAX_RECOVERY_POLLS_PER_ACTIVITY` |
| Max recovery polls / 60s window | **24** | `HVA_LIVE_MAX_RECOVERY_POLLS_PER_WINDOW` |
| New reserves / 60s window | **4** | `HVA_LIVE_RESERVE_PER_WINDOW` |
| Proceeding submits / 60s window | **2** | `HVA_LIVE_SUBMIT_PER_WINDOW` |
| Backpressure queue depth | **4** | `HVA_LIVE_QUEUE_DEPTH` |
| Window | 60s | not raisable |

Zero on a cap is fail-closed (refuse all of that action).

## Queue / backpressure

When a reservation or submit slot is full:

1. Enqueue up to `queue_depth` (reason `LIVE_QUEUED`). **Do not** reserve, submit, or poll.
2. Overflow is `LIVE_BACKPRESSURE`. **Do not** reserve, submit, or poll.
3. `promote()` admits the next queued item only after a slot is released. Promote never calls a vendor.

`Admission.proceed` is true only when the caller may touch the ledger / mock / future vendor. Queued is not proceed.

Join-existing reservations (`join_existing=True` or `ledger.has_active_reservation`) do not consume a reserve slot or a rate token.

## Client cannot raise caps

Rejected keys include `max_in_flight`, `max_reservations`, `max_recovery_polls`, `rate_limit`, `concurrency`, `queue_depth`, `submit_cap`, `reserve_cap`, `backpressure`, `poll_budget`, `retry_budget`, `bypass_limit`, `bypass_resource_guard`, and `x-max-*` / `x-rate*` / `x-concurrency*` / `x-queue*` headers.

`limits_from_untrusted(payload, headers)` always returns server/operator limits. Client numbers are ignored.

## Hook for other LIVE agents

```python
from app.services.live_resource_guards import LiveResourceGuards

guards = LiveResourceGuards()  # tests: pass an isolated instance
admission = guards.admit_reserve(join_existing=ledger.has_active_reservation(fp))
if not admission.proceed:
    # map to LIVE_ACQUISITION_UNAVAILABLE; do not try_reserve
    ...

submit = guards.admit_submit()
if not submit.proceed:
    # do not call mock / future vendor
    ...
guards.finish_submit_rpc(submit.token)   # after submit RPC returns
guards.complete_job(submit.token)        # when the job is terminal

poll = guards.admit_recovery_poll(activity_id)
if not poll.proceed:
    # stop recovery hammering
    ...
```

`resolve_hosted_demo_path(..., resource_guards=guards)` applies reserve admission. When `resource_guards` is omitted, the legacy path is unchanged so existing demo tests stay isolated. **J3/J4 workers must pass guards.** `call_if_admitted("submit", fn)` is the stampede-safe wrapper: `fn` runs only after proceed.

Process singleton: `get_live_resource_guards()` / `reset_live_resource_guards()`. Prefer a per-test instance.

## Reason codes

| Code | Meaning |
|---|---|
| `LIVE_RATE_LIMITED` | Window exhausted for proceeding reserve/submit |
| `LIVE_RESERVE_CAP` | Active reservation ceiling (promote path) |
| `LIVE_SUBMIT_CAP` | Concurrent submit ceiling (promote path) |
| `LIVE_IN_FLIGHT_CAP` | In-flight job ceiling (promote path) |
| `LIVE_RECOVERY_POLL_CAP` | Per-activity or process window poll ceiling |
| `LIVE_QUEUED` | Held in backpressure queue; no vendor I/O |
| `LIVE_BACKPRESSURE` | Queue full; refuse |
| `LIVE_CLIENT_CANNOT_RAISE_CAPS` | Client tried to set a cap |
| `LIVE_RESOURCE_CLOSED` | Operator set the action cap to 0 |

Demo-path mapping today: guard refusal → `DemoAllowanceDecisionCode.LIVE_ACQUISITION_UNAVAILABLE`.

## Files

- `apps/api/app/services/live_resource_guards.py` — guards
- `apps/api/app/services/demo_acquisition.py` — optional reserve hook
- `apps/api/app/services/demo_allowance_ledger.py` — `has_active_reservation` join peek
- `apps/api/tests/unit/test_live_resource_guards.py` — tests
- this note

## Gaps

- Guards are opt-in on `resolve_hosted_demo_path`. Until LIVE-C/L pass an instance, the legacy reserve path can still stampede the ledger (not a vendor; hosted live stays off).
- No ASGI middleware mount. HTTP 429 for these reasons is LIVE-O / route-owner work.
- Queue is process-local and not durable. Restart drops queued work (fail-closed; no auto-submit).
- Recovery-poll guard is not yet wired into a worker (LIVE-D owns reconcile). Call `admit_recovery_poll` before every mock/vendor status poll.
- Submit/in-flight counters are not bound to `JobStore` tokens. Worker must `complete_job` on terminal states or the slot leaks until process restart.
- Multi-process / multi-replica deploy needs a shared limiter (out of scope). InMemory / one demo process is the current model.
- Does not claim exactly-once. Caps are admission, not vendor idempotency.
- `retry_budget` rejection here is defense in depth; LIVE-I owns retry policy.
