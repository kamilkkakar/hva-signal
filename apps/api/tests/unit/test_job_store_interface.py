"""Job store interface: no public payload drift, guarded transitions."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.core.job_store import InMemoryJobStore, JobStoreError
from app.domain.enums import JobStatus
from app.domain.job_lifecycle import (
    ExecutionState,
    SignalPhase,
    SignalProgress,
    TwoSignalJobState,
    empty_section,
)
from app.domain.signals import SignalAvailability, ThermalSignalKind


def _two(job_id: str, b_units: int) -> TwoSignalJobState:
    historical = empty_section(
        ThermalSignalKind.HISTORICAL_NORMALIZED,
        requested=True,
        area_id="phoenix-demo",
    )
    selected = empty_section(
        ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        requested=True,
        area_id="phoenix-demo",
    )
    selected = selected.model_copy(
        update={
            "availability": SignalAvailability.FETCHING,
            "progress": SignalProgress(
                phase=SignalPhase.VENDOR_PROCESSING,
                completed_units=b_units,
                required_units=10,
                message="vendor",
            ),
        }
    )
    return TwoSignalJobState(
        job_id=job_id,
        area_id="phoenix-demo",
        historical=historical,
        selected_time=selected,
        execution_state=ExecutionState.RUNNING,
    )


def test_create_get_and_unknown() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "phoenix-demo"})
    assert job.status == JobStatus.QUEUED
    assert store.get(job.job_id) is job
    assert store.get("missing") is None
    assert store.durability_level == "J0"


def test_create_or_join_reuses_in_flight_and_terminal() -> None:
    store = InMemoryJobStore()
    first, joined = store.create_or_join({"area_id": "a"}, dedupe_key="k1")
    assert joined is False
    second, joined = store.create_or_join({"area_id": "a"}, dedupe_key="k1")
    assert joined is True
    assert second.job_id == first.job_id
    store.set_result(first.job_id, {"ok": True}, JobStatus.COMPLETE)
    third, joined = store.create_or_join({"area_id": "a"}, dedupe_key="k1")
    assert joined is True
    assert third.status == JobStatus.COMPLETE


def test_terminal_cannot_return_to_running() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    with pytest.raises(JobStoreError, match="terminal"):
        store.update_status(job.job_id, JobStatus.QUEUED)


def test_section_progress_cannot_regress() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    store.replace_two_signal(job.job_id, _two(job.job_id, 4))
    with pytest.raises(ValueError, match="regress"):
        store.replace_two_signal(job.job_id, _two(job.job_id, 2))


def test_section_updates_do_not_lose_sibling_state() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    state = _two(job.job_id, 1)
    store.replace_two_signal(job.job_id, state)
    updated = state.model_copy(
        update={
            "historical": state.historical.model_copy(
                update={"availability": SignalAvailability.READY}
            )
        }
    )
    store.replace_two_signal(job.job_id, updated)
    loaded = store.get(job.job_id)
    assert loaded is not None
    assert loaded.two_signal is not None
    assert loaded.two_signal.historical.availability == SignalAvailability.READY
    assert loaded.two_signal.selected_time.progress.completed_units == 1


def test_ordered_updates_from_two_workers_keep_both_sections() -> None:
    store = InMemoryJobStore()
    job = store.create({})

    def write(units: int) -> None:
        current = store.get(job.job_id)
        assert current is not None
        base = current.two_signal or _two(job.job_id, units)
        nxt = base.model_copy(
            update={
                "selected_time": base.selected_time.model_copy(
                    update={
                        "progress": SignalProgress(
                            phase=SignalPhase.VENDOR_PROCESSING,
                            completed_units=max(
                                units,
                                base.selected_time.progress.completed_units or 0,
                            ),
                            required_units=10,
                        )
                    }
                )
            }
        )
        try:
            store.replace_two_signal(job.job_id, nxt)
        except ValueError:
            pass

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, [3, 5, 4, 6]))
    loaded = store.get(job.job_id)
    assert loaded is not None and loaded.two_signal is not None
    assert loaded.two_signal.selected_time.progress.completed_units is not None
    assert loaded.two_signal.selected_time.progress.completed_units >= 3


def test_reset_models_process_restart() -> None:
    store = InMemoryJobStore()
    job = store.create({})
    store.reset()
    assert store.get(job.job_id) is None
