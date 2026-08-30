-- HVA-SIGNAL J3 local SQLite persistence.
-- Enabling this file/schema does not enable hosted live or a vendor.
-- Default product store remains InMemory.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    job_id TEXT PRIMARY KEY,
    dedupe_key TEXT,
    fingerprint TEXT,
    activity_id TEXT,
    reservation_id TEXT,
    worker_state TEXT,
    error_class TEXT,
    recovery_required INTEGER NOT NULL DEFAULT 0,
    public_status TEXT,
    payload TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    revision INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS demo_reservations (
    reservation_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    signal_kind TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    geometry_sha256 TEXT NOT NULL,
    area_id TEXT NOT NULL,
    planned_units INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    activity_id TEXT,
    job_id TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_dedupe_key
    ON analysis_jobs(dedupe_key)
    WHERE dedupe_key IS NOT NULL AND dedupe_key != '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_fingerprint
    ON analysis_jobs(fingerprint)
    WHERE fingerprint IS NOT NULL AND fingerprint != '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_activity_id
    ON analysis_jobs(activity_id)
    WHERE activity_id IS NOT NULL AND activity_id != '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_reservation_id
    ON analysis_jobs(reservation_id)
    WHERE reservation_id IS NOT NULL AND reservation_id != '';

CREATE INDEX IF NOT EXISTS ix_jobs_recovery_state
    ON analysis_jobs(worker_state);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_reservation_fingerprint
    ON demo_reservations(request_fingerprint)
    WHERE state = 'RESERVED';

CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_activity_id
    ON demo_reservations(activity_id)
    WHERE activity_id IS NOT NULL AND activity_id != '';
