"""Offline job-store microbench. No premature optimization."""

import time

from app.core.job_store import InMemoryJobStore
from app.core.sqlite_job_store import SQLiteJobStore
from app.domain.enums import JobStatus


def test_memory_store_1000_reads_and_progress_updates() -> None:
    store = InMemoryJobStore()
    job = store.create({"n": 1})
    started = time.perf_counter()
    for i in range(1000):
        store.update_status(job.job_id, JobStatus.COMPUTING, note=str(i))
        loaded = store.get(job.job_id)
        assert loaded is not None
    elapsed = time.perf_counter() - started
    assert elapsed < 2.0
    assert store.get(job.job_id).revision == 1000


def test_sqlite_store_basic_read_write(tmp_path) -> None:
    store = SQLiteJobStore(tmp_path / "jobs.sqlite")
    job = store.create({"n": 1})
    started = time.perf_counter()
    for i in range(200):
        store.update_status(job.job_id, JobStatus.COMPUTING, note=str(i))
        assert store.get(job.job_id) is not None
    elapsed = time.perf_counter() - started
    assert elapsed < 3.0
