# PERSISTENCE — LIVE-B (SQLite / local durability)

**Worktree:** `F:\cursor\hackathon-live-b-persistence`  
**Branch:** `feat/live-b-sqlite-persistence`  
**Date:** 2026-08-30  
**Scope:** J3 local file persistence for jobs, reservations, and `activity_id`.  
**Not owned:** Temporal analytics, frontend, FortyGuard, hosted-live vendor path.

## Default

The process default remains **InMemory (J0)**.

```
local_sqlite_persistence_enabled = False
local_sqlite_path = ""
demo_allowance_enabled = False
```

SQLite is used only when an operator sets **both** `local_sqlite_persistence_enabled=true` **and** a non-empty `local_sqlite_path`. That switch is local/demo durability. It does **not** enable hosted live, demo allowance, or a vendor adapter.

`app.core.jobs.job_store` stays `InMemoryJobStore()`. Composition for opt-in SQLite is `app.core.persistence_factory.build_job_store`.

## Schema (v2)

Canonical SQL: `apps/api/app/core/sql/j3_local_persistence.sql`  
Applied by: `app.core.sqlite_schema.apply_migrations` (idempotent).

| Table | Role |
|---|---|
| `schema_migrations` | Version stamp (current = 2) |
| `analysis_jobs` | Job payload + durable columns |
| `demo_reservations` | Allowance reserve / consume / release |

Durable columns on `analysis_jobs`: `fingerprint`, `activity_id`, `reservation_id`, `worker_state`, `error_class`, `recovery_required`.

Partial unique indexes:

- fingerprint (jobs)
- activity_id (jobs)
- reservation_id (jobs)
- active reservation fingerprint (`state = 'RESERVED'`)
- reservation activity_id

Legacy J2 databases (`job_id`, `dedupe_key`, `payload`) migrate in place. `dedupe_key` is backfilled into `fingerprint`.

## Crash-safe writes

On open:

- `PRAGMA journal_mode=WAL`
- `PRAGMA synchronous=FULL`
- `PRAGMA busy_timeout=5000`
- `PRAGMA foreign_keys=ON`

Writes that acknowledge spend-risk states use `BEGIN IMMEDIATE` … `COMMIT`.  
`DurableAck` is constructed **only after COMMIT**.

Rules:

- `SUBMITTING` may be committed without `activity_id` (pre-vendor window).
- `acknowledge_submitted` and `acknowledge_activity_id_persisted` **refuse** empty `activity_id` or `reservation_id`.
- Callers must not treat a submit as `SUBMITTED` / `ACTIVITY_ID_PERSISTED` until the ack returns.

Uncommitted `activity_id` writes roll back on process death. Recovery then classifies `SUBMITTING` without `activity_id` as `UNKNOWN_VENDOR_STATE`. **No automatic resubmit.**

## Recovery query

Jobs in `SUBMITTING`, `SUBMITTED`, `UNKNOWN_VENDOR_STATE`, `RECOVERY_REQUIRED` (or `recovery_required = 1`):

See `RECOVERY_JOBS_SQL` in `sqlite_schema.py` and `SQLiteJobStore.list_recovery_jobs()`.

Restart classification (`classify_restart`):

| Persisted state | activity_id | After reopen |
|---|---|---|
| (legacy, no worker_state, in-flight) | — | `FAILED` + `INTERRUPTED` (J2, no retry) |
| `REQUESTED` / `VALIDATED` | — | `FAILED_PRE_SUBMIT` |
| `ALLOWANCE_RESERVED` | — | `RECOVERY_REQUIRED` (keep reservation) |
| `SUBMITTING` / `SUBMITTED` | missing | `UNKNOWN_VENDOR_STATE` |
| `SUBMITTING` / `SUBMITTED` / `ACTIVITY_ID_PERSISTED` / `PROCESSING` / … | present | `RECOVERY_REQUIRED` (resume, no resubmit) |
| `UNKNOWN_VENDOR_STATE` / `RECOVERY_REQUIRED` | any | kept (never auto-resubmit) |

`activity_id` and `reservation_id` are never cleared on recovery.

## Allowance

`SQLiteDemoAllowanceLedger` persists `RESERVED` / `CONSUMED` / `RELEASED` / `EXPIRED`.  
Restart does **not** reset remaining units.  
A durable file plus a **disabled** policy still cannot reserve.  
SQLite ledger enablement does not imply hosted live.

## Durability guarantees (honest)

What this **does** guarantee on a local disk that survives the process:

- Committed `activity_id`, `reservation_id`, and fingerprint are still present after reopen.
- Uncommitted writes are not visible after reopen.
- Unique fingerprints / activity_ids cannot be inserted twice.
- Recovery rows are queryable; UNKNOWN never becomes an automatic second submit.

What this **does not** guarantee:

- Production durability on ephemeral host filesystems (Render Free, etc.).
- Multi-instance shared state.
- Mathematical exactly-once if the vendor lacks idempotency.
- Hosted live / vendor connectivity (explicitly out of scope; default OFF).
- Worker transition legality (LIVE-C) or activity poll/reconcile (LIVE-D).

## Gaps

- `jobs.py` is not auto-wired to the factory (avoids `.env` flipping the test singleton). Operators must compose `build_job_store`.
- InMemory still loses everything on process death (intentional J0).
- LIVE-C must call `mark_submitting` before the vendor call and only ACK after `acknowledge_*`.
- LIVE-F may extend consume/cache crash semantics on top of this ledger.
- No cross-process lock beyond SQLite; one writer process is assumed.
- WAL files (`-wal`, `-shm`) must stay beside the DB file.
