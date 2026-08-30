# LIVE-H — Cache Recheck

Date: 2026-08-30  
Worktree: `f:\cursor\hackathon-live-h`  
Branch: `feat/live-h-cache-recheck`  
Contract: `hva-signal-live-h-cache-recheck-v1`

No FortyGuard calls. No real vendor. Hosted live default remains off
(`DemoAllowancePolicy.enabled=False`).

## Why this exists

Cache/dedupe before spend already exists in `demo_acquisition.resolve_hosted_demo_path`.
It is not enough:

- Recheck is not named as a mandatory gate immediately before reserve **and**
  immediately before submit.
- `recheck_demo_reservation_before_paid_submission` **consumes** the reservation
  on a miss. Consume must happen only after normalize → cache.
- There is no crash recovery for “result received but not cached” or
  “cached but not consumed”.
- Cache poisoning and unauthenticated cache-bust are not a first-class reject
  on this path.

LIVE-H hardens those points in isolated modules. It does not own Temporal
analytics, frontend, or the full worker state machine (LIVE-C).

## Recheck points

| Point | Function | Hit behavior | Miss behavior |
|---|---|---|---|
| **BEFORE_RESERVE** | `gate_reserve` → `recheck_cache` | `CACHE_HIT`. No ledger write. No submit. | `try_reserve` may proceed. |
| **BEFORE_SUBMIT** | `gate_submit` → `recheck_cache` | `CACHE_HIT`. Release reservation if still `RESERVED`. **Do not submit. Do not consume.** | Submit may proceed. Reservation stays `RESERVED`. |

A hit is either:

1. A fingerprint-bound record in `FingerprintResultCache` (identity:
   `request_fingerprint` + `geometry_sha256` + `area_id`, integrity SHA-256), or
2. A reusable `JobStore` job on the same dedupe key (`COMPLETE` / `PARTIAL`).
   `FAILED` is **not** a hit.

`CACHE_HIT` is a spend-side outcome. It is not a client flag and not a grant.

## After-result order

Mandatory, in this order, after a mock (or future vendor) result:

1. `RESULT_RECEIVED` — persist the raw result (secrets stripped).
2. `normalize_live_result` — bind identity; reject `reference_frame=relative`
   (no AOI min-max); strip secrets.
3. `FingerprintResultCache.put_from_worker` — worker writer only.
4. `consume_after_cache` — allowance consume. Idempotent if already `CONSUMED`.

Submit is **not** part of this sequence. Recovery never increments `submit_count`.

## Crash recovery

| Crash | Persisted phase | Recovery | Submit |
|---|---|---|---|
| After result, before cache | `RESULT_RECEIVED` (or `NORMALIZED`) | normalize if needed → cache → consume | no second submit |
| After cache, before consume | `CACHED` | consume only | no second submit |
| After submit, no result | `SUBMITTED` | `RECOVERY_REQUIRED` / unknown vendor state | **never** auto-resubmit |

`LiveCachePipeline.recover()` is the executable form. LIVE-D/E own vendor
activity-id reconciliation; LIVE-H only guarantees that a result already in
hand is cached and then consumed without another submit.

## Poison / cache-bust rejects

Rejected with no cache mutation and no spend:

- Client body/query/headers asking for a bypass (`cache_bust`, `no_cache`,
  `force_live`, `force_refresh`, `skip_cache`, `Cache-Control: no-cache`, …).
- Client-supplied cache records (`cache_record`, `ingest_client_record`).
- Operator token on a **client** payload.
- Operator bust with `source != "server"` or token mismatch.
- Integrity mismatch (tamper). Dropped, not served.
- Overwrite of an existing fingerprint with a **different** payload.
- Put bound to a different fingerprint / geometry / area.

Idempotent put of the **same** integrity is allowed (recovery-safe).

Server-side operator bust is the only authorized invalidation. It is not a
public route and is not wired to HTTP in this stream.

## Files

| Path | Role |
|---|---|
| `apps/api/app/domain/live_cache_recheck.py` | Codes, phases, records |
| `apps/api/app/services/live_cache_recheck.py` | Recheck gates, cache, pipeline |
| `apps/api/tests/unit/test_live_cache_recheck.py` | Guards, crash, poison |
| `docs/live-durability/LIVE_H_CACHE_RECHECK.md` | This note |

Does **not** edit `app/domain/__init__.py`, FortyGuard, frontend, or the
existing `demo_acquisition` consume-before-submit helper (see gaps).

## Gaps

1. **Not mounted on the HTTP worker.** `resolve_hosted_demo_path` still does
   first-line cache/join, then reserve. LIVE-C should call `gate_reserve` /
   `gate_submit` / `LiveCachePipeline` at the named points.
2. **Existing consume-before-submit.**
   `recheck_demo_reservation_before_paid_submission` still consumes on miss.
   That is the wrong order. Do not treat it as the LIVE-H gate. Prefer
   `gate_submit` (recheck, no consume) + `consume_after_cache`.
3. **Fingerprint cache is J0 process-local.** Restart loses in-memory records
   unless LIVE-B persists them. JobStore `COMPLETE` remains the durable reuse
   signal when SQLite is on.
4. **No claim of mathematical exactly-once.** At-most-one-submit is best-effort
   given vendor idempotency. LIVE-H only prevents a second submit after a
   result is already in hand.
5. **Sibling collision.** LIVE-G (dedupe) and LIVE-F (allowance durability)
   own neighboring surfaces. This stream adds new modules instead of rewriting
   theirs.
6. **Hosted live stays off** until an operator freezes a `DemoAllowancePolicy`.
   Cache recheck does not enable live.
