"""SQLite adapter is local file-backed persistence, not production durability."""

from app.core.sqlite_job_store import SQLiteJobStore, _INTERRUPT_MESSAGE
from app.domain.enums import JobStatus
from app.domain.job_lifecycle import ExecutionState


def test_sqlite_round_trip_and_dedupe(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    assert store.durability_level == "J2"
    job, joined = store.create_or_join({"area_id": "phoenix-demo"}, dedupe_key="k")
    assert joined is False
    again, joined = store.create_or_join({"area_id": "phoenix-demo"}, dedupe_key="k")
    assert joined is True
    assert again.job_id == job.job_id
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE, message="done")
    loaded = store.get(job.job_id)
    assert loaded is not None
    assert loaded.result == {"ok": True}
    assert loaded.status == JobStatus.COMPLETE


def test_reopen_marks_in_flight_interrupted_and_does_not_retry(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"})
    store.update_status(job.job_id, JobStatus.FETCHING_THERMAL, note="fetch")
    assert store.get(job.job_id).status == JobStatus.FETCHING_THERMAL
    store._conn.close()

    reopened = SQLiteJobStore(path)
    recovered = reopened.get(job.job_id)
    assert recovered is not None
    assert recovered.status == JobStatus.FAILED
    assert recovered.execution_state == ExecutionState.INTERRUPTED
    assert recovered.recoverable is True
    assert recovered.message == _INTERRUPT_MESSAGE
    assert reopened.list_in_flight() == []
