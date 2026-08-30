# WORKER STATE MACHINE

**Program:** HVA-SIGNAL J3/J4 live execution & durability  
**Owner:** LIVE-C  
**Worktree:** `f:\cursor\hackathon-live-c-worker-sm` (`feat/live-c-worker-sm`)  
**Date:** 2026-08-30  
**Vendor I/O:** none (no FortyGuard, no real vendor)

Tracked copy of the LIVE-C worker contract. An identical research copy lives at
`workforce/live_durability/WORKER_STATE_MACHINE.md` (that tree is gitignored).

This document is the J3/J4 **durable worker acquisition** state machine.
It is not public `JobStatus`, not the two-signal section lifecycle, and not a
second JobStore. J0/J1/J2 already persist jobs; this SM owns **legal worker
transitions** only.

**Canonical 17-state type:** LIVE-D `DurableLivePhase`
(`app/domain/activity_reconciliation.py`). LIVE-C does **not** own a forked
enum. `WorkerState` is an alias/re-export of `DurableLivePhase`. Members and
values must stay identical. C owns the transition table, illegal-transition
guards, and `LiveWorkerMachine`.

Source of truth in code:

- `apps/api/app/domain/activity_reconciliation.py` — `DurableLivePhase` (LIVE-D)
- `apps/api/app/domain/live_worker_state.py` — transitions; `WorkerState = DurableLivePhase`
- `apps/api/app/services/live_worker_machine.py`

---

## Why J0/J1/J2 are not enough

| Level | What exists today | Worker gap |
|---|---|---|
| **J0** | `InMemoryJobStore`, process-local demo allowance | Lost on process death. No worker SM. |
| **J1** | Client reattach while the process lives | Reattach ≠ durable submit. |
| **J2** | Optional `SQLiteJobStore` (off by default) | File-backed jobs, **not worker-recoverable**. Comment in store: not production-durable. |
| **J3** | This SM + restart classification | Explicit states, illegal-transition guards, no blind paid retry. |
| **J4** | `WorkerHandoff` (payload concept only) | Handoff is not a queue. This SM is what a J4 worker must execute. |

`WorkerHandoff.must_recheck_authorization` is frozen `True`. The machine
enforces the same idea: **cache/dedupe before reserve, recheck before submit**.

---

## Required states

| State | Terminal? | Spend risk | Meaning |
|---|---|---|---|
| `REQUESTED` | no | `NONE` | Worker accepted a handoff. |
| `VALIDATED` | no | `NONE` | Request identity is structurally valid. |
| `CACHE_HIT` | success | `NONE` | Reuse path. **No reserve, no submit.** |
| `JOINED` | hold | `NONE` | Attached to an in-flight fingerprint owner. **No local spend.** |
| `ALLOWANCE_RESERVED` | no | `RESERVED` | Units reserved. Submit has not started. |
| `SUBMITTING` | no | `UNKNOWN` | Bytes may be in flight. Crash here is not pre-submit. |
| `SUBMITTED` | no | `POST_SUBMIT` | Vendor accepted in memory. **Not durable** until `activity_id` is persisted. |
| `ACTIVITY_ID_PERSISTED` | no | `POST_SUBMIT` | Submit is durable. Only now may the worker treat the attempt as real. |
| `PROCESSING` | no | `POST_SUBMIT` | Status poll / wait. Never a second submit. |
| `RESULT_RECEIVED` | no | `POST_SUBMIT` | Raw vendor payload in hand. |
| `NORMALIZED` | no | `POST_SUBMIT` | Domain-normalized result. |
| `CACHED` | no | `POST_SUBMIT` | Result written to cache. Consume still owed. |
| `CONSUMED` | success | `POST_SUBMIT` | Allowance consumed after cache. |
| `FAILED_PRE_SUBMIT` | failure | `NONE` | Failed with **no vendor submit**. Release reservation if any. |
| `FAILED_POST_SUBMIT` | failure | `POST_SUBMIT` | Failed after vendor accept. **Spend may have occurred.** |
| `UNKNOWN_VENDOR_STATE` | hold | `UNKNOWN` | Submit may have happened; `activity_id` missing or untrusted. |
| `RECOVERY_REQUIRED` | hold | varies | Operator-safe resume/reconcile. **Never auto-resubmit.** |

`FAILED_PRE_SUBMIT` and `FAILED_POST_SUBMIT` are distinct **because spend risk
differs**. Do not collapse them.

---

## Rules (normative)

1. **Cache / dedupe before spend.** `reserve` is illegal until a cache check ran.
2. **Reserve before submit.** `VALIDATED → SUBMITTING` is illegal.
3. **Recheck cache immediately before submit.** `ALLOWANCE_RESERVED → CACHE_HIT` is legal (release reservation). Submit without recheck is illegal.
4. **Persist `activity_id` before treating submit as durable.** `SUBMITTED` is not durable. `PROCESSING` requires `activity_id_durable`.
5. **`FAILED_PRE_SUBMIT` vs `FAILED_POST_SUBMIT` stay distinct.**
6. **`UNKNOWN_VENDOR_STATE` never automatically resubmits.** The only automatic edge is `→ RECOVERY_REQUIRED`. Resume is operator-safe reconcile (found `activity_id`, proven no-submit, found cached result).
7. **No blind paid retry.** After `submit_attempted` without `submit_never_left` proof, `SUBMITTING` / `SUBMITTED` are forbidden.
8. **Joiners do not spend.** `JOINED` cannot reserve or submit; they inherit a leader outcome.
9. **Cache before consume.** Crash after cache / before consume recovers by consuming, not resubmitting.
10. **Hosted live default remains OFF** at the policy layer. This SM does not enable a vendor.

---

## Happy paths

```
REQUESTED → VALIDATED → CACHE_HIT
REQUESTED → VALIDATED → JOINED → (inherit CACHE_HIT | CONSUMED | failure/hold)
REQUESTED → VALIDATED → ALLOWANCE_RESERVED → SUBMITTING → SUBMITTED
        → ACTIVITY_ID_PERSISTED → PROCESSING → RESULT_RECEIVED
        → NORMALIZED → CACHED → CONSUMED
```

Pre-submit abort after reserve (cache recheck hit):

```
ALLOWANCE_RESERVED → CACHE_HIT   (reservation_release_required)
```

---

## Transition table

Modes:

- `AUTOMATIC` — worker / restart classifier
- `OPERATOR_RECONCILE` — extra edges from `UNKNOWN_VENDOR_STATE` / `RECOVERY_REQUIRED` only

`to` spend risk is the **destination state's** default risk.

### Automatic

| From | To | Spend risk after | Notes |
|---|---|---|---|
| REQUESTED | VALIDATED | NONE | |
| REQUESTED | FAILED_PRE_SUBMIT | NONE | Validation / policy reject |
| VALIDATED | CACHE_HIT | NONE | No spend |
| VALIDATED | JOINED | NONE | Dedupe attach |
| VALIDATED | ALLOWANCE_RESERVED | RESERVED | After cache miss |
| VALIDATED | FAILED_PRE_SUBMIT | NONE | |
| ALLOWANCE_RESERVED | SUBMITTING | UNKNOWN | After cache recheck miss |
| ALLOWANCE_RESERVED | CACHE_HIT | NONE | Recheck hit; release reserve |
| ALLOWANCE_RESERVED | FAILED_PRE_SUBMIT | NONE | Release reserve |
| ALLOWANCE_RESERVED | RECOVERY_REQUIRED | POST_SUBMIT* | Holding; classifier may return to reserve if submit never started |
| SUBMITTING | SUBMITTED | POST_SUBMIT | In-memory ack only |
| SUBMITTING | FAILED_PRE_SUBMIT | NONE | Only with `submit_never_left` proof |
| SUBMITTING | UNKNOWN_VENDOR_STATE | UNKNOWN | Timeout / crash / no proof |
| SUBMITTING | RECOVERY_REQUIRED | POST_SUBMIT* | |
| SUBMITTED | ACTIVITY_ID_PERSISTED | POST_SUBMIT | Durable submit |
| SUBMITTED | UNKNOWN_VENDOR_STATE | UNKNOWN | Lost before persist |
| SUBMITTED | RECOVERY_REQUIRED | POST_SUBMIT | |
| SUBMITTED | FAILED_POST_SUBMIT | POST_SUBMIT | Vendor rejected after accept |
| ACTIVITY_ID_PERSISTED | PROCESSING | POST_SUBMIT | |
| ACTIVITY_ID_PERSISTED | FAILED_POST_SUBMIT | POST_SUBMIT | |
| ACTIVITY_ID_PERSISTED | RECOVERY_REQUIRED | POST_SUBMIT | Resume poll |
| PROCESSING | RESULT_RECEIVED | POST_SUBMIT | |
| PROCESSING | FAILED_POST_SUBMIT | POST_SUBMIT | |
| PROCESSING | RECOVERY_REQUIRED | POST_SUBMIT | |
| RESULT_RECEIVED | NORMALIZED | POST_SUBMIT | |
| RESULT_RECEIVED | FAILED_POST_SUBMIT | POST_SUBMIT | |
| RESULT_RECEIVED | RECOVERY_REQUIRED | POST_SUBMIT | Cache without resubmit |
| NORMALIZED | CACHED | POST_SUBMIT | |
| NORMALIZED | FAILED_POST_SUBMIT | POST_SUBMIT | |
| NORMALIZED | RECOVERY_REQUIRED | POST_SUBMIT | |
| CACHED | CONSUMED | POST_SUBMIT | |
| CACHED | RECOVERY_REQUIRED | POST_SUBMIT | Consume without resubmit |
| JOINED | CACHE_HIT | NONE | Inherit |
| JOINED | CONSUMED | NONE | Inherit (joiner did not spend) |
| JOINED | FAILED_PRE_SUBMIT | NONE | Inherit |
| JOINED | FAILED_POST_SUBMIT | POST_SUBMIT | Inherit leader class |
| JOINED | UNKNOWN_VENDOR_STATE | UNKNOWN | Inherit; still no local submit |
| JOINED | RECOVERY_REQUIRED | POST_SUBMIT* | Inherit |
| UNKNOWN_VENDOR_STATE | RECOVERY_REQUIRED | POST_SUBMIT* | **Only automatic edge** |
| RECOVERY_REQUIRED | UNKNOWN_VENDOR_STATE | UNKNOWN | Still unknown |
| RECOVERY_REQUIRED | ALLOWANCE_RESERVED | RESERVED | Submit never attempted |
| RECOVERY_REQUIRED | CACHE_HIT / CACHED / CONSUMED / ACTIVITY_ID_PERSISTED / PROCESSING / RESULT_RECEIVED / NORMALIZED / FAILED_PRE_SUBMIT / FAILED_POST_SUBMIT | (dest) | Safe resume; **not** submit |

\* Default `spend_risk_for_state(RECOVERY_REQUIRED)` is `POST_SUBMIT`. The
record's computed risk stays `RESERVED` / `UNKNOWN` when facts say no durable
submit.

### Operator reconcile (additional)

From `UNKNOWN_VENDOR_STATE` or `RECOVERY_REQUIRED` only:

| To | Required fact | Forbidden? |
|---|---|---|
| ACTIVITY_ID_PERSISTED / PROCESSING / RESULT_RECEIVED / NORMALIZED / CACHED / CONSUMED | recovered `activity_id` or cached result | no |
| FAILED_POST_SUBMIT | vendor confirmed failure after accept | no |
| FAILED_PRE_SUBMIT | `proven_no_submit=True` | without proof: **illegal** |
| CACHE_HIT | result already cached; no local submit | no |
| SUBMITTING / SUBMITTED | — | **always illegal** |

Terminal states (`CACHE_HIT`, `CONSUMED`, `FAILED_PRE_SUBMIT`,
`FAILED_POST_SUBMIT`) are absorbing.

---

## Illegal transitions (guards)

The machine raises `IllegalWorkerTransition` for:

| Attempt | Why |
|---|---|
| reserve before cache check | spend before reuse |
| submit before reserve | spend path without allowance |
| submit without cache recheck | TOCTOU spend |
| `CACHE_HIT` / `JOINED` reserve or submit | reuse/join must not spend |
| `PROCESSING` before durable `activity_id` | submit is not durable yet |
| consume before cache | lose result / double-spend window |
| `FAILED_PRE_SUBMIT` after vendor ack | would hide spend risk |
| `FAILED_PRE_SUBMIT` from `SUBMITTING` without `submit_never_left` | must be `UNKNOWN_VENDOR_STATE` |
| `FAILED_POST_SUBMIT` from pre-submit states | no submit occurred |
| any automatic move from `UNKNOWN_VENDOR_STATE` except `RECOVERY_REQUIRED` | no auto-resubmit |
| reconcile to `SUBMITTING` / `SUBMITTED` | no paid retry |
| restart classifier emitting submit states | restart must not submit |
| any event out of a terminal state | absorbing |

---

## Restart classification (crash matrix hook)

`classify_restart` / `apply_restart` **never** enter `SUBMITTING` or `SUBMITTED`.
`may_resubmit` is always `False`.

| Crash point | Persisted facts | Restart state | Safe action | Spend risk |
|---|---|---|---|---|
| before reserve | validated / requested | same | continue pre-spend | NONE |
| after reserve | reservation, `submit_attempted=false` | ALLOWANCE_RESERVED | cache recheck, then **first** submit or release | RESERVED |
| before vendor submit | reserved, recheck pending | ALLOWANCE_RESERVED | recheck then first submit | RESERVED |
| during submit | `submit_attempted`, no durable id | UNKNOWN_VENDOR_STATE | operator reconcile | UNKNOWN |
| after submit, before `activity_id` save | `SUBMITTED`, not durable | UNKNOWN_VENDOR_STATE | operator reconcile | UNKNOWN |
| after `activity_id` save | durable id | RECOVERY_REQUIRED | resume poll | POST_SUBMIT |
| during vendor processing | durable id | RECOVERY_REQUIRED | resume poll | POST_SUBMIT |
| after result, before cache | durable id + result | RECOVERY_REQUIRED | cache without resubmit | POST_SUBMIT |
| after cache, before consume | `result_cached` | RECOVERY_REQUIRED | consume without resubmit | POST_SUBMIT |

`SUBMITTING` without `submit_never_left` proof is **never** classified as
`FAILED_PRE_SUBMIT`.

---

## Exactly-once (honest)

This SM does **not** claim mathematical exactly-once delivery.

Best achievable here:

- **At most one submit attempt per worker record** unless `submit_never_left` is proven.
- **At most one durable `activity_id`** per record (`activity_id_durable`).
- Joiners share a leader; they do not open a second submit path.
- If the vendor lacks idempotency, a crash during `SUBMITTING` is
  `UNKNOWN_VENDOR_STATE`. Recovery is reconcile-by-`activity_id`, not resubmit.

LIVE-D owns vendor-side activity lookup. LIVE-G owns fingerprint join races.
LIVE-I owns retry budgets (must call this SM; they cannot add a paid retry edge).

---

## File ownership

| File | Role |
|---|---|
| `app/domain/activity_reconciliation.py` | `DurableLivePhase` (LIVE-D canonical; enum-only copy in this worktree) |
| `app/domain/live_worker_state.py` | Transition table, record, restart classifier; `WorkerState = DurableLivePhase` |
| `app/services/live_worker_machine.py` | Event API + guards |
| `tests/unit/test_live_worker_state_machine.py` | Unit tests |
| this document | Contract for sibling LIVE-* agents |

Not owned by LIVE-C (do not collide):

- JobStore / SQLite (LIVE-A / LIVE-B)
- Activity-id vendor reconcile I/O (LIVE-D)
- Allowance ledger persistence (LIVE-F)
- Fingerprint lock / 100-dupe runner (LIVE-G)
- Cache store (LIVE-H)
- Mock vendor (LIVE-L)
- Frontend / Temporal analytics / FortyGuard

---

## Gaps

1. **Not wired into `JobStore` / `AnalysisJob`.** LIVE-A must persist
   `LiveWorkerRecord` (or equivalent fields: state, `activity_id`,
   `reservation_id`, flags) across restart.
2. **No SQLite schema here.** LIVE-B should persist the record atomically with
   `activity_id` before acknowledging `ACTIVITY_ID_PERSISTED`.
3. **No vendor adapter.** `ack_submit` / `persist_activity_id` are facts the
   caller supplies. LIVE-L mock should drive this machine.
4. **`WorkerHandoff` is unchanged.** A future adapter can start a machine from
   a handoff; it must still begin at `REQUESTED` and recheck cache/auth.
5. **Allowance release/consume is signaled, not executed.**
   `reservation_release_required` / `consume_required` are flags for LIVE-F.
6. **Public API / OpenAPI unchanged.** Worker states are internal.
7. **Hosted live stays OFF** unless an operator policy (not this SM) enables it.
8. **No claim of vendor idempotency.** Unknown-after-submit remains a human/
   operator reconcile problem.
