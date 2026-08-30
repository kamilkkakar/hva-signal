"""Restart simulation: committed ids survive; uncommitted ids do not."""

from __future__ import annotations

import pytest

from app.core.durable_live import (
    LiveWorkerState,
    PersistenceError,
    RestartAction,
    classify_restart,
)
from app.core.durable_live import DurableJobRecord
from app.core.jobs import job_store
from app.core.job_store import InMemoryJobStore
from app.core.sqlite_job_store import SQLiteJobStore, _INTERRUPT_MESSAGE
from app.domain.enums import JobStatus
from app.domain.job_lifecycle import ExecutionState


def test_module_default_job_store_is_in_memory() -> None:
    assert isinstance(job_store, InMemoryJobStore)
    assert job_store.durability_level == "J0"


def test_legacy_in_flight_still_interrupts_without_retry(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"})
    store.update_status(job.job_id, JobStatus.FETCHING_THERMAL, note="fetch")
    store._conn.close()

    reopened = SQLiteJobStore(path)
    recovered = reopened.get(job.job_id)
    assert recovered is not None
    assert recovered.status == JobStatus.FAILED
    assert recovered.execution_state == ExecutionState.INTERRUPTED
    assert recovered.message == _INTERRUPT_MESSAGE
    assert reopened.list_in_flight() == []
    assert reopened.list_recovery_jobs() == []
    reopened.close()


def test_committed_activity_id_and_reservation_survive_restart(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"}, dedupe_key="fp-live")
    store.commit_reservation_binding(
        job.job_id, reservation_id="res_keep", fingerprint="fp-live"
    )
    ack = store.acknowledge_activity_id_persisted(
        job.job_id,
        activity_id="act_keep",
        reservation_id="res_keep",
        fingerprint="fp-live",
    )
    assert ack.committed is True
    assert ack.acknowledged_status == "ACTIVITY_ID_PERSISTED"
    store.close()

    reopened = SQLiteJobStore(path)
    durable = reopened.get_durable(job.job_id)
    assert durable is not None
    assert durable.activity_id == "act_keep"
    assert durable.reservation_id == "res_keep"
    assert durable.fingerprint == "fp-live"
    assert durable.worker_state == LiveWorkerState.RECOVERY_REQUIRED
    assert durable.recovery_required is True
    assert durable.auto_resubmit is False
    by_activity = reopened.find_by_activity_id("act_keep")
    assert by_activity is not None and by_activity.job_id == job.job_id
    recovery = reopened.list_recovery_jobs()
    assert [item.job_id for item in recovery] == [job.job_id]
    reopened.close()


def test_uncommitted_activity_id_rolls_back_to_unknown_vendor(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"})
    store.mark_submitting(job.job_id, reservation_id="res_maybe")
    submitting = [item.worker_state for item in store.list_recovery_jobs()]
    assert LiveWorkerState.SUBMITTING in submitting
    store.write_uncommitted_activity_id_for_tests(job.job_id, "act_lost")
    store.crash_close_for_tests()

    reopened = SQLiteJobStore(path)
    durable = reopened.get_durable(job.job_id)
    assert durable is not None
    assert durable.activity_id is None
    assert durable.worker_state == LiveWorkerState.UNKNOWN_VENDOR_STATE
    assert durable.recovery_required is True
    assert durable.auto_resubmit is False
    assert durable.reservation_id == "res_maybe"
    assert reopened.find_by_activity_id("act_lost") is None
    reopened.close()


def test_submitted_without_ids_is_rejected(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"})
    with pytest.raises(PersistenceError, match="activity_id"):
        store.acknowledge_submitted(job.job_id, activity_id="", reservation_id="res_1")
    with pytest.raises(PersistenceError, match="reservation"):
        store.acknowledge_submitted(job.job_id, activity_id="act_1", reservation_id="")
    with pytest.raises(PersistenceError, match="activity_id"):
        store.acknowledge_activity_id_persisted(
            job.job_id, activity_id="  ", reservation_id="res_1"
        )
    assert store.get_durable(job.job_id).activity_id is None
    store.close()


def test_recovery_query_includes_submitting_and_submitted(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    submitting = store.create({"n": 1})
    submitted = store.create({"n": 2})
    store.mark_submitting(submitting.job_id, reservation_id="res_s")
    store.acknowledge_submitted(
        submitted.job_id,
        activity_id="act_s",
        reservation_id="res_s2",
    )
    states = {item.worker_state for item in store.list_recovery_jobs()}
    assert LiveWorkerState.SUBMITTING in states
    assert LiveWorkerState.SUBMITTED in states
    store.close()


def test_submitting_crash_never_auto_resubmits(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"})
    store.mark_submitting(job.job_id, reservation_id="res_x")
    store.close()
    reopened = SQLiteJobStore(path)
    durable = reopened.get_durable(job.job_id)
    assert durable.worker_state == LiveWorkerState.UNKNOWN_VENDOR_STATE
    assert durable.auto_resubmit is False
    reopened.close()


def test_classify_restart_table() -> None:
    submitting = DurableJobRecord(
        job_id="j",
        worker_state=LiveWorkerState.SUBMITTING,
        fingerprint="f",
        activity_id=None,
        reservation_id="r",
        error_class=None,
        recovery_required=False,
        public_status="queued",
    )
    assert classify_restart(submitting) == RestartAction.MARK_UNKNOWN_VENDOR
    persisted = DurableJobRecord(
        job_id="j",
        worker_state=LiveWorkerState.ACTIVITY_ID_PERSISTED,
        fingerprint="f",
        activity_id="a",
        reservation_id="r",
        error_class=None,
        recovery_required=False,
        public_status="queued",
    )
    assert classify_restart(persisted) == RestartAction.MARK_RECOVERY_REQUIRED
    unknown = DurableJobRecord(
        job_id="j",
        worker_state=LiveWorkerState.UNKNOWN_VENDOR_STATE,
        fingerprint="f",
        activity_id=None,
        reservation_id="r",
        error_class="UNKNOWN_VENDOR_STATE",
        recovery_required=True,
        public_status="queued",
    )
    assert classify_restart(unknown) == RestartAction.KEEP
    legacy = DurableJobRecord(
        job_id="j",
        worker_state=None,
        fingerprint=None,
        activity_id=None,
        reservation_id=None,
        error_class=None,
        recovery_required=False,
        public_status="fetching_thermal",
    )
    assert classify_restart(legacy) == RestartAction.INTERRUPT_LEGACY
