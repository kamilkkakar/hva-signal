# JOB DURABILITY (LIVE-A / J3)

HVA-Signal already has one job system (`JobStore` / `AnalysisJob`). This work hardens that store. It does not add a second job table, queue, or worker.

## What is durable

Each `AnalysisJob` now carries a `DurableJobContract`:

- identity: `job_id`, fingerprint, timestamps
- vendor facts: `activity_id`, `reservation_id` (never dropped on crash)
- `DurabilityState` (all J3/J4 states, including `UNKNOWN_VENDOR_STATE`)
- `JobErrorClass` and `RecoveryFlags` (`auto_resubmit` is always false after restart)

Public `JobStatus` (`queued`, `fetching_thermal`, `failed`, …) is unchanged. Durability state is the acquisition worker contract. LIVE-C owns transition edges.

## Restart recovery

1. Persist the job document (`export_jobs` / SQLite payload hook).
2. New process loads documents (`import_jobs` or SQLite open).
3. `recover_after_restart()` / SQLite `_interrupt_orphans` applies `plan_crash_recovery`.

Rules:

- `activity_id` present → `RECOVERY_REQUIRED`, resume vendor status, **never resubmit**.
- Submit attempted without a durable `activity_id` → `UNKNOWN_VENDOR_STATE`. **Never auto-resubmit.**
- `UNKNOWN_VENDOR_STATE` stays there. `replace_durability` refuses `SUBMITTING` / `SUBMITTED`.
- `reservation_id` present, no submit → `RECOVERY_REQUIRED`, reservation kept.
- No vendor identity (classic J0/J2 in-flight) → public `FAILED` + `INTERRUPTED`, no auto-retry.

InMemory is still J0 (dies with the process) but implements the full contract via export/import. File durability is LIVE-B (`SQLiteJobStore` uses the shared payload + recovery hooks).

## Not this program

- LIVE-B: SQLite schema, WAL placement, hosted volume.
- LIVE-C: worker transition table and events.
- LIVE-D: vendor activity reconciliation / polling.
- Temporal analytics and frontend.

## Remaining gaps

- No durable worker process (J4) and no Temporal queue.
- InMemory default still loses jobs if the API process dies without a file adapter.
- SQLite lookups for `activity_id` / `reservation_id` scan payload JSON (LIVE-B can add columns).
- Recovery does not poll a vendor or consume/release allowance; it only preserves facts and blocks resubmit.
