"""SQLite schema and migrations for local J3 persistence.

Not a hosted-live switch. Not multi-instance. Not production-durable on
an ephemeral filesystem.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

SCHEMA_VERSION = 2

SCHEMA_SQL = """
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
"""

INDEX_SQL = """
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
"""

RECOVERY_JOBS_SQL = """
SELECT
    job_id,
    worker_state,
    fingerprint,
    activity_id,
    reservation_id,
    error_class,
    recovery_required,
    public_status,
    payload
FROM analysis_jobs
WHERE worker_state IN (
    'SUBMITTING',
    'SUBMITTED',
    'UNKNOWN_VENDOR_STATE',
    'RECOVERY_REQUIRED'
)
   OR recovery_required = 1
"""

_JOB_V2_COLUMNS: tuple[tuple[str, str], ...] = (
    ("fingerprint", "TEXT"),
    ("activity_id", "TEXT"),
    ("reservation_id", "TEXT"),
    ("worker_state", "TEXT"),
    ("error_class", "TEXT"),
    ("recovery_required", "INTEGER NOT NULL DEFAULT 0"),
    ("public_status", "TEXT"),
    ("created_at", "TEXT"),
    ("updated_at", "TEXT"),
    ("revision", "INTEGER NOT NULL DEFAULT 0"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def current_schema_version(conn: sqlite3.Connection) -> int:
    tables = _table_names(conn)
    if "schema_migrations" not in tables:
        if "analysis_jobs" in tables:
            return 1
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def _stamp(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        """
        INSERT INTO schema_migrations (version, applied_at)
        VALUES (?, ?)
        ON CONFLICT(version) DO UPDATE SET applied_at = excluded.applied_at
        """,
        (version, _now()),
    )


def _add_missing_job_columns(conn: sqlite3.Connection) -> None:
    existing = _columns(conn, "analysis_jobs")
    for name, decl in _JOB_V2_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE analysis_jobs ADD COLUMN {name} {decl}")


def _backfill_fingerprints(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE analysis_jobs
        SET fingerprint = dedupe_key
        WHERE (fingerprint IS NULL OR fingerprint = '')
          AND dedupe_key IS NOT NULL
          AND dedupe_key != ''
        """
    )


def _exec_script(conn: sqlite3.Connection, script: str) -> None:
    """Run DDL statements without sqlite3.executescript (that auto-COMMITs)."""
    for raw in script.split(";"):
        statement = raw.strip()
        if statement:
            conn.execute(statement)


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply schema up to SCHEMA_VERSION. Safe to call on every open."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        version = current_schema_version(conn)
        _exec_script(conn, SCHEMA_SQL)
        if version <= 1 and "analysis_jobs" in _table_names(conn):
            _add_missing_job_columns(conn)
            _backfill_fingerprints(conn)
        _exec_script(conn, INDEX_SQL)
        if version < 1:
            _stamp(conn, 1)
        if version < 2:
            _stamp(conn, 2)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return SCHEMA_VERSION


def apply_durable_pragmas(conn: sqlite3.Connection) -> dict[str, str]:
    """WAL + FULL sync. Returns the applied pragma values."""
    journal = conn.execute("PRAGMA journal_mode=WAL").fetchone()
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA temp_store=MEMORY")
    sync = conn.execute("PRAGMA synchronous").fetchone()
    return {
        "journal_mode": str(journal[0] if journal else ""),
        "synchronous": str(sync[0] if sync else ""),
    }
