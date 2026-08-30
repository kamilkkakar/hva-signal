"""Schema / WAL / unique-constraint tests for J3 local SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from app.core.durable_live import PersistenceError
from app.core.sqlite_job_store import SQLiteJobStore
from app.core.sqlite_schema import SCHEMA_VERSION, apply_migrations, current_schema_version
from app.domain.enums import JobStatus


def _legacy_payload(job_id: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return json.dumps(
        {
            "job_id": job_id,
            "status": JobStatus.QUEUED.value,
            "request": {"area_id": "phoenix-demo"},
            "created_at": now,
            "updated_at": now,
            "recoverable": False,
            "message": "Job queued.",
            "progress_notes": [],
            "result": None,
            "dedupe_key": "legacy-key",
            "execution_state": "NOT_STARTED",
            "revision": 0,
            "two_signal": None,
        }
    )


def test_fresh_database_applies_v2_and_wal(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    assert current_schema_version(store._conn) == SCHEMA_VERSION
    pragmas = store._pragmas
    assert pragmas["journal_mode"].lower() == "wal"
    assert str(pragmas["synchronous"]) in {"2", "FULL"}
    tables = {
        row[0]
        for row in store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert "analysis_jobs" in tables
    assert "demo_reservations" in tables
    assert "schema_migrations" in tables
    store.close()


def test_migrates_legacy_three_column_schema(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE analysis_jobs (
            job_id TEXT PRIMARY KEY,
            dedupe_key TEXT UNIQUE,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO analysis_jobs (job_id, dedupe_key, payload) VALUES (?, ?, ?)",
        ("job_legacy", "legacy-key", _legacy_payload("job_legacy")),
    )
    conn.commit()
    conn.close()

    store = SQLiteJobStore(path)
    assert current_schema_version(store._conn) == SCHEMA_VERSION
    durable = store.get_durable("job_legacy")
    assert durable is not None
    assert durable.fingerprint == "legacy-key"
    loaded = store.get("job_legacy")
    assert loaded is not None
    assert loaded.status == JobStatus.FAILED
    store.close()


def test_apply_migrations_is_idempotent(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    again = apply_migrations(store._conn)
    assert again == SCHEMA_VERSION
    assert current_schema_version(store._conn) == SCHEMA_VERSION
    store.close()


def test_unique_activity_id_and_fingerprint(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    first, _ = store.create_or_join({"area_id": "phoenix-demo"}, dedupe_key="fp-a")
    second = store.create({"area_id": "phoenix-demo"}, dedupe_key="fp-b")
    store.acknowledge_activity_id_persisted(
        first.job_id,
        activity_id="act-1",
        reservation_id="res-1",
        fingerprint="fp-a",
    )
    try:
        store.acknowledge_activity_id_persisted(
            second.job_id,
            activity_id="act-1",
            reservation_id="res-2",
            fingerprint="fp-b",
        )
        raise AssertionError("duplicate activity_id must fail")
    except PersistenceError as exc:
        assert "unique" in str(exc).lower()
    third = store.create({"area_id": "other"})
    try:
        store.commit_reservation_binding(
            third.job_id,
            reservation_id="res-3",
            fingerprint="fp-a",
        )
        raise AssertionError("duplicate fingerprint must fail")
    except PersistenceError as exc:
        assert "unique" in str(exc).lower()
    store.close()
