# ACTIVITY RECOVERY

HVA-SIGNAL / LIVE-D — activity_id reconciliation.

**Date:** 2026-08-30  
**Worktree:** `F:\cursor\hackathon-live-d-activity`  
**Branch:** `feat/live-d-activity-reconciliation`  
**Vendor:** interfaces and mock hooks only. No FortyGuard. No real vendor RPC.

## Claim (honest)

This control plane does **not** provide mathematical exactly-once delivery.

Best achievable: **at-most-one-submit** from this process, if and only if
`SUBMITTING` is durable **before** the vendor accepts the request.

Vendor idempotency is **not assumed**. If the vendor lacks an idempotency key,
a lost `activity_id` after a successful accept cannot be safely retried.

| Claim | Value |
|---|---|
| Mathematical exactly-once | **False** |
| Vendor idempotency assumed | **False** |
| Automatic resubmit | **False** |
| Blind paid retry | **False** |
| Resubmit without `activity_id` | **False** |
| Best achievable | `at_most_one_submit` |

## Algorithm

```
open_or_join(job, fingerprint, geometry)
    same fingerprint → JOIN existing binding (never a second submit path)

mark_submitting(record)          # durable intent BEFORE vendor RPC
    phase = SUBMITTING
    submit_attempted = true

vendor.submit(...)               # LIVE-C / LIVE-L. LIVE-D does not call this.

note_submitted_awaiting_persist  # crash window: SUBMITTED, activity_id missing

persist_activity_id(record, id)  # ONE critical section
    write activity_id
    write activity_id_persisted_at
    phase SUBMITTED → ACTIVITY_ID_PERSISTED
    index fingerprint ↔ activity_id  (bijection)
    optional snapshot sink commit-before-publish

restart / apply_restart
    if activity_id present:
        resume PROCESSING via poll_status / fetch_result
        NEVER submit
    if submit may have happened and activity_id missing
        (SUBMITTING | SUBMITTED | submit_attempted):
        diagnose UNKNOWN_VENDOR_STATE
        park RECOVERY_REQUIRED
        NEVER submit
    if clearly pre-submit (no submit_attempted):
        SUBMIT_ALLOWED (worker may submit once)
```

`persist_activity_id` is the atomic unit named in the program:
**SUBMITTED → ACTIVITY_ID_PERSISTED** together with the token. A snapshot
never contains `activity_id` on `SUBMITTING` or `SUBMITTED`.

## Fingerprint ↔ activity_id

- One fingerprint maps to at most one binding and at most one `activity_id`.
- One `activity_id` maps to at most one fingerprint.
- Duplicate requests join the existing binding (`JOINED` / reuse). They
  resume poll if the id is known; they never open a second submit.
- Conflicting maps raise. Forged or stolen `activity_id` values cannot be
  rebound onto another fingerprint.

Fingerprint identity itself is owned by existing
`job_identity` / `snapshot_request_fingerprint`. This ledger stores the
already-computed hex digest.

## Crash cases LIVE-D owns

| Crash | Durable leftover | Restart | Spend risk | Second submit |
|---|---|---|---|---|
| After submit, before `activity_id` save | `SUBMITTED`, id missing | `UNKNOWN_VENDOR_STATE` → `RECOVERY_REQUIRED` | `UNKNOWN_MAY_HAVE_SPENT` | **Forbidden** |
| After `activity_id` save | `ACTIVITY_ID_PERSISTED` + id | `RESUME_POLL` → `PROCESSING` | `SPENT_KNOWN_ACTIVITY` | **Forbidden** |
| During vendor processing | `PROCESSING` + id | `RESUME_POLL` / result fetch | `SPENT_KNOWN_ACTIVITY` | **Forbidden** |

Operator recovery for the first row is **not** a second paid submit. It is
out-of-band: vendor console, wait-and-see, or write-off. LIVE-I must not
turn this into an automatic retry.

## Resume surface (mockable)

`ActivityVendorHooks`:

- `poll_status(activity_id)`
- `fetch_result(activity_id)`

There is no `submit` on the reconciler path. `ScriptedVendorHooks.submit`
raises if a caller tries.

Succeeded poll → fetch → `RESULT_RECEIVED`.  
Failed / not-found poll → `FAILED_POST_SUBMIT` (still no resubmit).

## Spend-risk analysis

| Phase / leftover | Risk | Why |
|---|---|---|
| `REQUESTED` / `VALIDATED` | `NONE` | Vendor RPC has not been permitted. |
| `ALLOWANCE_RESERVED` | `RESERVED_NOT_SUBMITTED` | Units reserved; not yet a vendor accept. LIVE-F owns leak/release. |
| `CACHE_HIT` / `JOINED` | `NONE` | No new vendor work. |
| `SUBMITTING` / `SUBMITTED` without id | `UNKNOWN_MAY_HAVE_SPENT` | Accept may have occurred. Second submit can double-charge. |
| `UNKNOWN_VENDOR_STATE` / `RECOVERY_REQUIRED` | `UNKNOWN_MAY_HAVE_SPENT` | Same. Parked. |
| `ACTIVITY_ID_PERSISTED` / `PROCESSING` | `SPENT_KNOWN_ACTIVITY` | Token exists; poll only. |
| `RESULT_RECEIVED` / `NORMALIZED` / `CACHED` | `SPENT_RESULT_IN_HAND` | Do not submit; LIVE-H caches then LIVE-F consumes. |
| `CONSUMED` | `CONSUMED` | Terminal spend. |
| `FAILED_PRE_SUBMIT` (no attempt) | `FAILED_PRE_SUBMIT` | No vendor accept. LIVE-I may allow a *new* attempt only if it can prove submit could not have occurred. LIVE-D does not auto-retry. |
| `FAILED_POST_SUBMIT` | `FAILED_POST_SUBMIT` | Spend may have occurred. No resubmit. |

**Highest residual spend risk:** crash *after* the vendor accepts and
*before* `SUBMITTING` is durable. Restart then looks pre-submit and a
naive worker would submit again. Mitigation is mandatory:
`persist_submitting_before_vendor_rpc = true`. If that write fails, do
not call the vendor.

## Ownership / integration

| Module | Owner |
|---|---|
| `app/domain/activity_reconciliation.py` | LIVE-D |
| `app/services/activity_reconciliation.py` | LIVE-D |
| `app/services/activity_vendor_hooks.py` | LIVE-D resume contract; LIVE-L may wrap |
| Job row / SQLite WAL | LIVE-A / LIVE-B (use `ActivitySnapshotSink`) |
| Worker transitions around reserve/cache | LIVE-C / LIVE-H |
| Retry budget | LIVE-I (must call `refuse_blind_resubmit`) |
| Full mock vendor | LIVE-L |

Do not import FortyGuard from these modules.

## Gaps

1. **Cross-process durability** — the ledger is process-local unless LIVE-B
   commits `ActivitySnapshotSink` (or an equivalent WAL) before ACK.
2. **No vendor-side idempotency key** — cannot convert UNKNOWN into a
   safe retry even with operator approval, unless a future vendor API
   can look up by fingerprint.
3. **J0 JobStore default** — a process kill still drops in-memory jobs
   unless SQLite / J3 is enabled. This module's `fork_after_restart`
   models the *reload* side only.
4. **LIVE-C wiring** — the durable worker does not yet call this ledger
   on this branch. Illegal transitions elsewhere can still skip
   `mark_submitting`.
5. **Operator runbook UI** — `RECOVERY_REQUIRED` is a parked state, not
   a console. LIVE-O owns deployment copy.
6. **Result cache / consume** — not performed here (LIVE-H / LIVE-F).
7. **Hosted live remains OFF** — this code does not enable a live path.

## Tests

`apps/api/tests/unit/test_activity_reconciliation.py`

Covers atomic persist, sink rollback, fingerprint bijection, honest
exactly-once construction, the three crash windows, poll-only resume,
and forbidden submit from UNKNOWN / RECOVERY_REQUIRED.
