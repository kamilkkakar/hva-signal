"""Zero-vendor progressive delivery of independent signal sections."""

from datetime import datetime

from app.core.job_store import InMemoryJobStore
from app.domain.enums import DataStatus, JobStatus, ThermalDataSource
from app.domain.job_lifecycle import (
    ExecutionState,
    JobTerminality,
    SignalPhase,
    SignalProgress,
    SignalSection,
    SignalSectionError,
    TwoSignalJobState,
    derive_job_terminality,
    empty_section,
)
from app.domain.signals import (
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)


def _ready_snapshot() -> SelectedTimeSnapshot:
    return SelectedTimeSnapshot(
        area_id="test-area",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=SignalAvailability.READY,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id="test-area",
            source=ThermalDataSource.REPLAY,
            data_status=DataStatus.REPLAY,
            geometry_version="TEST_GEOM_V1",
            vendor_request_fingerprint="held-hourly-tcm",
        ),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="z1",
                mean_temperature_c=31.2,
                tile_count=2,
                coverage_status="ok",
            )
        ],
    )


def _state(
    store: InMemoryJobStore,
    job_id: str,
    *,
    a: SignalAvailability,
    b: SignalAvailability,
    b_error: SignalSectionError | None = None,
    snapshot: SelectedTimeSnapshot | None = None,
) -> TwoSignalJobState:
    historical = empty_section(
        ThermalSignalKind.HISTORICAL_NORMALIZED,
        requested=True,
        area_id="test-area",
    )
    selected = empty_section(
        ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        requested=True,
        area_id="test-area",
    )
    historical = historical.model_copy(
        update={
            "availability": a,
            "progress": SignalProgress(
                phase=SignalPhase.READY
                if a
                not in {SignalAvailability.PENDING, SignalAvailability.FETCHING}
                else SignalPhase.COMPUTING,
                message=a.value,
            ),
            "historical_result": {"thermal_differentiation_state": a.value}
            if a
            in {
                SignalAvailability.READY,
                SignalAvailability.D8_INSUFFICIENT,
                SignalAvailability.INSUFFICIENT_EVIDENCE,
            }
            else None,
            "provenance": SignalProvenance(
                signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                area_id="test-area",
                reference_version="PHX_ZTSI_REF_V1",
                source=ThermalDataSource.REPLAY,
                data_status=DataStatus.REPLAY,
            ),
        }
    )
    b_phase = SignalPhase.READY
    if b == SignalAvailability.PENDING:
        b_phase = SignalPhase.QUEUED
    elif b == SignalAvailability.FETCHING:
        b_phase = SignalPhase.VENDOR_PROCESSING
    elif b == SignalAvailability.FAILED:
        b_phase = SignalPhase.FAILED
    selected = selected.model_copy(
        update={
            "availability": b,
            "progress": SignalProgress(phase=b_phase, message=b.value),
            "selected_time_result": snapshot,
            "error": b_error,
            "provenance": SignalProvenance(
                signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
                area_id="test-area",
                source=ThermalDataSource.REPLAY,
                data_status=DataStatus.REPLAY,
            ),
        }
    )
    state = TwoSignalJobState(
        job_id=job_id,
        area_id="test-area",
        historical=historical,
        selected_time=selected,
        execution_state=ExecutionState.RUNNING,
    )
    store.replace_two_signal(job_id, state)
    return store.get(job_id).two_signal


def test_case_1_a_ready_then_b_pending_fetching_ready() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "test-area"})
    s1 = _state(store, job.job_id, a=SignalAvailability.READY, b=SignalAvailability.PENDING)
    assert derive_job_terminality(s1) == JobTerminality.IN_FLIGHT
    s2 = _state(store, job.job_id, a=SignalAvailability.READY, b=SignalAvailability.FETCHING)
    assert derive_job_terminality(s2) == JobTerminality.IN_FLIGHT
    s3 = _state(
        store,
        job.job_id,
        a=SignalAvailability.READY,
        b=SignalAvailability.READY,
        snapshot=_ready_snapshot(),
    )
    assert derive_job_terminality(s3) == JobTerminality.TERMINAL_SUCCESS
    assert s3.historical.provenance.reference_version == "PHX_ZTSI_REF_V1"
    assert s3.selected_time.provenance.reference_version is None
    assert s3.combined_score_authorized is False


def test_case_2_a_not_prepared_b_fetching_then_ready() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "test-area"})
    s1 = _state(
        store,
        job.job_id,
        a=SignalAvailability.NOT_PREPARED,
        b=SignalAvailability.FETCHING,
    )
    assert derive_job_terminality(s1) == JobTerminality.IN_FLIGHT
    s2 = _state(
        store,
        job.job_id,
        a=SignalAvailability.NOT_PREPARED,
        b=SignalAvailability.READY,
        snapshot=_ready_snapshot(),
    )
    assert derive_job_terminality(s2) == JobTerminality.TERMINAL_SUCCESS
    assert s2.historical.availability == SignalAvailability.NOT_PREPARED
    assert s2.selected_time.availability == SignalAvailability.READY


def test_case_3_a_ready_b_fails_independently() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "test-area"})
    _state(store, job.job_id, a=SignalAvailability.READY, b=SignalAvailability.FETCHING)
    s2 = _state(
        store,
        job.job_id,
        a=SignalAvailability.READY,
        b=SignalAvailability.FAILED,
        b_error=SignalSectionError(
            reason_code="VENDOR_TIMEOUT",
            user_message="Selected-time snapshot could not be retrieved.",
            log_ref="job-test-b",
        ),
    )
    assert derive_job_terminality(s2) == JobTerminality.TERMINAL_PARTIAL
    assert s2.historical.availability == SignalAvailability.READY
    assert s2.selected_time.error is not None
    assert "api-key" not in s2.selected_time.error.user_message.lower()
    assert s2.historical.error is None


def test_case_4_a_insufficient_b_ready() -> None:
    store = InMemoryJobStore()
    job = store.create({"area_id": "test-area"})
    s1 = _state(
        store,
        job.job_id,
        a=SignalAvailability.INSUFFICIENT_EVIDENCE,
        b=SignalAvailability.READY,
        snapshot=_ready_snapshot(),
    )
    assert derive_job_terminality(s1) == JobTerminality.TERMINAL_SUCCESS
    assert "q_A" not in s1.selected_time.selected_time_result.model_dump()
    store.set_result(job.job_id, {"legacy": True}, JobStatus.COMPLETE)
    public = store.get(job.job_id)
    assert public.result == {"legacy": True}
    assert public.two_signal is not None
    assert public.two_signal.selected_time.availability == SignalAvailability.READY
