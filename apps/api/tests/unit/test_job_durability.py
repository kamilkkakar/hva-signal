"""J3 job durability: identity survives restart; never auto-resubmit."""

from __future__ import annotations

import pytest

from app.core.job_store import (
    InMemoryJobStore,
    JobStoreError,
    analysis_job_from_payload,
    analysis_job_to_payload,
)
from app.core.sqlite_job_store import SQLiteJobStore
from app.domain.enums import JobStatus
from app.domain.job_durability import (
    REQUIRED_DURABILITY_STATES,
    DurableJobContract,
    DurabilityState,
    JobErrorClass,
    RecoveryFlags,
    forbids_auto_resubmit,
    new_durability,
)
from app.domain.job_lifecycle import ExecutionState


REQUIRED = (
    "REQUESTED",
    "VALIDATED",
    "CACHE_HIT",
    "JOINED",
    "ALLOWANCE_RESERVED",
    "SUBMITTING",
    "SUBMITTED",
    "ACTIVITY_ID_PERSISTED",
    "PROCESSING",
    "RESULT_RECEIVED",
    "NORMALIZED",
    "CACHED",
    "CONSUMED",
    "FAILED_PRE_SUBMIT",
    "FAILED_POST_SUBMIT",
    "UNKNOWN_VENDOR_STATE",
    "RECOVERY_REQUIRED",
)


def test_required_durability_states_are_complete() -> None:
    assert tuple(state.value for state in REQUIRED_DURABILITY_STATES) == REQUIRED
    assert DurabilityState.UNKNOWN_VENDOR_STATE in REQUIRED_DURABILITY_STATES
    assert forbids_auto_resubmit(DurabilityState.UNKNOWN_VENDOR_STATE)


def test_create_seeds_identity_timestamps_and_requested() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "phoenix-demo"}, dedupe_key="fp-1")
    assert job.durability is not None
    assert job.durability.state == DurabilityState.REQUESTED
    assert job.durability.fingerprint == "fp-1"
    assert job.durability.activity_id is None
    assert job.durability.reservation_id is None
    assert job.durability.error_class == JobErrorClass.NONE
    assert job.durability.created_at is not None
    assert job.durability.updated_at is not None
    assert job.durability.recovery.auto_resubmit is False


def test_persist_fingerprint_activity_and_reservation() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "phoenix-demo"})
    store.persist_fingerprint(job.job_id, "fp-abc")
    store.persist_reservation_id(job.job_id, "res-1")
    store.replace_durability(
        job.job_id,
        DurableJobContract(
            fingerprint="fp-abc",
            state=DurabilityState.SUBMITTED,
            reservation_id="res-1",
            recovery=RecoveryFlags(submit_attempted=True, reservation_intact=True),
        ),
    )
    store.persist_activity_id(job.job_id, "act-9")
    loaded = store.get(job.job_id)
    assert loaded is not None and loaded.durability is not None
    assert loaded.durability.fingerprint == "fp-abc"
    assert loaded.durability.reservation_id == "res-1"
    assert loaded.durability.activity_id == "act-9"
    assert loaded.durability.activity_id_persisted_at is not None
    assert loaded.durability.reservation_persisted_at is not None
    assert loaded.durability.state == DurabilityState.ACTIVITY_ID_PERSISTED
    assert loaded.durability.recovery.activity_id_durable is True
    assert store.find_by_activity_id("act-9").job_id == job.job_id
    assert store.find_by_reservation_id("res-1").job_id == job.job_id
    assert store.find_by_fingerprint("fp-abc").job_id == job.job_id


def test_in_memory_export_import_recover_keeps_vendor_identity() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "phoenix-demo"}, dedupe_key="fp-x")
    store.update_status(job.job_id, JobStatus.FETCHING_THERMAL)
    store.persist_reservation_id(job.job_id, "res-keep")
    store.replace_durability(
        job.job_id,
        DurableJobContract(
            fingerprint="fp-x",
            state=DurabilityState.PROCESSING,
            activity_id="act-keep",
            reservation_id="res-keep",
            recovery=RecoveryFlags(
                activity_id_durable=True,
                reservation_intact=True,
                submit_attempted=True,
            ),
        ),
    )
    store.persist_activity_id(job.job_id, "act-keep")

    snapshot = store.export_jobs()
    store.reset()
    assert store.get(job.job_id) is None

    restarted = InMemoryJobStore()
    restarted.import_jobs(snapshot)
    restarted.recover_after_restart()
    recovered = restarted.get(job.job_id)
    assert recovered is not None and recovered.durability is not None
    assert recovered.durability.activity_id == "act-keep"
    assert recovered.durability.reservation_id == "res-keep"
    assert recovered.durability.fingerprint == "fp-x"
    assert recovered.durability.state == DurabilityState.RECOVERY_REQUIRED
    assert recovered.durability.recovery.auto_resubmit is False
    assert recovered.durability.recovery.requires_vendor_status_check is True
    assert recovered.durability.recovery.activity_id_durable is True
    assert recovered.durability.recovery.reservation_intact is True
    assert recovered.status == JobStatus.FETCHING_THERMAL
    assert recovered.execution_state == ExecutionState.INTERRUPTED


def test_submitting_without_activity_id_becomes_unknown_never_resubmits() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    store.update_status(job.job_id, JobStatus.FETCHING_THERMAL)
    store.replace_durability(
        job.job_id,
        DurableJobContract(
            state=DurabilityState.SUBMITTING,
            reservation_id="res-risk",
            recovery=RecoveryFlags(submit_attempted=True, reservation_intact=True),
        ),
    )
    snapshot = store.export_jobs()
    restarted = InMemoryJobStore()
    restarted.import_jobs(snapshot)
    restarted.recover_after_restart()
    recovered = restarted.get(job.job_id)
    assert recovered is not None and recovered.durability is not None
    assert recovered.durability.state == DurabilityState.UNKNOWN_VENDOR_STATE
    assert recovered.durability.reservation_id == "res-risk"
    assert recovered.durability.activity_id is None
    assert recovered.durability.recovery.auto_resubmit is False
    assert recovered.durability.recovery.operator_reconcile is True
    assert recovered.durability.error_class == JobErrorClass.VENDOR_UNKNOWN

    with pytest.raises(JobStoreError, match="never auto-resubmit"):
        restarted.replace_durability(
            job.job_id,
            DurableJobContract(
                state=DurabilityState.SUBMITTING,
                reservation_id="res-risk",
                recovery=RecoveryFlags(auto_resubmit=True, submit_attempted=True),
            ),
        )


def test_unknown_vendor_state_stays_unknown_on_second_restart() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    store.replace_durability(
        job.job_id,
        DurableJobContract(
            state=DurabilityState.UNKNOWN_VENDOR_STATE,
            reservation_id="res-u",
            error_class=JobErrorClass.VENDOR_UNKNOWN,
            recovery=RecoveryFlags(operator_reconcile=True, reservation_intact=True),
        ),
    )
    store.recover_after_restart()
    loaded = store.get(job.job_id)
    assert loaded is not None and loaded.durability is not None
    assert loaded.durability.state == DurabilityState.UNKNOWN_VENDOR_STATE
    assert loaded.durability.reservation_id == "res-u"
    assert loaded.durability.recovery.auto_resubmit is False


def test_joined_follower_does_not_resubmit() -> None:
    store = InMemoryJobStore()
    job = store.create({}, dedupe_key="shared")
    store.replace_durability(
        job.job_id,
        DurableJobContract(state=DurabilityState.JOINED, fingerprint="shared"),
    )
    store.recover_after_restart()
    loaded = store.get(job.job_id)
    assert loaded is not None and loaded.durability is not None
    assert loaded.durability.state == DurabilityState.JOINED
    assert loaded.durability.recovery.auto_resubmit is False


def test_payload_round_trip_preserves_durability() -> None:
    store = InMemoryJobStore()
    job = store.create({"n": 1}, dedupe_key="fp")
    store.persist_reservation_id(job.job_id, "res-p")
    store.persist_activity_id(job.job_id, "act-p")
    blob = analysis_job_to_payload(store.get(job.job_id))
    assert blob["durability"]["activity_id"] == "act-p"
    assert blob["durability"]["reservation_id"] == "res-p"
    restored = analysis_job_from_payload(blob)
    assert restored.durability is not None
    assert restored.durability.activity_id == "act-p"
    assert restored.durability.reservation_id == "res-p"
    assert restored.durability.state == DurabilityState.ACTIVITY_ID_PERSISTED


def test_j2_jobs_without_vendor_identity_still_interrupt(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"})
    store.update_status(job.job_id, JobStatus.FETCHING_THERMAL)
    store._conn.close()

    reopened = SQLiteJobStore(path)
    recovered = reopened.get(job.job_id)
    assert recovered is not None
    assert recovered.status == JobStatus.FAILED
    assert recovered.execution_state == ExecutionState.INTERRUPTED
    assert recovered.recoverable is True
    assert reopened.list_in_flight() == []
    assert recovered.durability is not None
    assert recovered.durability.recovery.auto_resubmit is False


def test_sqlite_reopen_keeps_activity_and_reservation(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    store = SQLiteJobStore(path)
    job = store.create({"area_id": "phoenix-demo"}, dedupe_key="fp-sql")
    store.update_status(job.job_id, JobStatus.FETCHING_THERMAL)
    store.persist_reservation_id(job.job_id, "res-sql")
    store.replace_durability(
        job.job_id,
        DurableJobContract(
            fingerprint="fp-sql",
            state=DurabilityState.PROCESSING,
            activity_id="act-sql",
            reservation_id="res-sql",
            recovery=RecoveryFlags(
                activity_id_durable=True,
                reservation_intact=True,
                submit_attempted=True,
            ),
        ),
    )
    store._conn.close()

    reopened = SQLiteJobStore(path)
    recovered = reopened.get(job.job_id)
    assert recovered is not None and recovered.durability is not None
    assert recovered.durability.activity_id == "act-sql"
    assert recovered.durability.reservation_id == "res-sql"
    assert recovered.durability.fingerprint == "fp-sql"
    assert recovered.durability.state == DurabilityState.RECOVERY_REQUIRED
    assert recovered.durability.recovery.auto_resubmit is False
    assert recovered.status == JobStatus.FETCHING_THERMAL
    assert reopened.find_by_activity_id("act-sql").job_id == job.job_id
    assert reopened.find_by_reservation_id("res-sql").job_id == job.job_id


def test_replace_durability_can_store_every_required_state() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    for state in REQUIRED_DURABILITY_STATES:
        store.replace_durability(job.job_id, new_durability())
        current = store.get(job.job_id)
        assert current is not None
        store.replace_durability(
            job.job_id,
            DurableJobContract(state=state, fingerprint=f"fp-{state.value}"),
        )
        loaded = store.get(job.job_id)
        assert loaded is not None and loaded.durability is not None
        assert loaded.durability.state == state
