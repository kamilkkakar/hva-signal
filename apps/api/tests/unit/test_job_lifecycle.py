"""Independent A/B job terminality. Internal only."""

from datetime import datetime

import pytest

from app.domain.job_lifecycle import (
    CostAuthorization,
    CostAuthorizationState,
    ExecutionState,
    JobTerminality,
    SignalPhase,
    SignalProgress,
    SignalSection,
    TwoSignalJobState,
    apply_progress,
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


def _snapshot() -> SelectedTimeSnapshot:
    return SelectedTimeSnapshot(
        area_id="phoenix-demo",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=SignalAvailability.READY,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id="phoenix-demo",
        ),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="z1",
                mean_temperature_c=33.0,
                tile_count=2,
                coverage_status="ok",
            )
        ],
    )


def _section(
    kind: ThermalSignalKind,
    availability: SignalAvailability,
    *,
    requested: bool = True,
    snapshot: SelectedTimeSnapshot | None = None,
) -> SignalSection:
    return SignalSection(
        kind=kind,
        requested=requested,
        availability=availability,
        progress=SignalProgress(phase=SignalPhase.READY, message=availability.value),
        provenance=SignalProvenance(signal_kind=kind, area_id="phoenix-demo"),
        selected_time_result=snapshot
        if kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT
        else None,
        historical_result={"reference_quality": "FULL_REFERENCE"}
        if kind == ThermalSignalKind.HISTORICAL_NORMALIZED
        and availability
        in {SignalAvailability.READY, SignalAvailability.D8_INSUFFICIENT}
        else None,
    )


def _job(
    historical: SignalAvailability,
    selected: SignalAvailability,
    *,
    request_a: bool = True,
    request_b: bool = True,
    cost: CostAuthorization | None = None,
    execution: ExecutionState = ExecutionState.RUNNING,
) -> TwoSignalJobState:
    hist = (
        empty_section(
            ThermalSignalKind.HISTORICAL_NORMALIZED,
            requested=False,
            area_id="phoenix-demo",
        )
        if not request_a
        else _section(ThermalSignalKind.HISTORICAL_NORMALIZED, historical)
    )
    snap = (
        empty_section(
            ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            requested=False,
            area_id="phoenix-demo",
        )
        if not request_b
        else _section(
            ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            selected,
            snapshot=_snapshot() if selected == SignalAvailability.READY else None,
        )
    )
    return TwoSignalJobState(
        job_id="job_test",
        area_id="phoenix-demo",
        historical=hist,
        selected_time=snap,
        cost_authorization=cost or CostAuthorization(),
        execution_state=execution,
    )


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (SignalAvailability.READY, SignalAvailability.FETCHING, JobTerminality.IN_FLIGHT),
        (SignalAvailability.READY, SignalAvailability.FAILED, JobTerminality.TERMINAL_PARTIAL),
        (SignalAvailability.NOT_PREPARED, SignalAvailability.READY, JobTerminality.TERMINAL_SUCCESS),
        (SignalAvailability.INSUFFICIENT_EVIDENCE, SignalAvailability.READY, JobTerminality.TERMINAL_SUCCESS),
        (SignalAvailability.D8_INSUFFICIENT, SignalAvailability.READY, JobTerminality.TERMINAL_SUCCESS),
        (SignalAvailability.FAILED, SignalAvailability.READY, JobTerminality.TERMINAL_PARTIAL),
        (SignalAvailability.READY, SignalAvailability.READY, JobTerminality.TERMINAL_SUCCESS),
        (SignalAvailability.FAILED, SignalAvailability.FAILED, JobTerminality.TERMINAL_FAILURE),
    ],
)
def test_terminality_matrix(a, b, expected) -> None:
    assert derive_job_terminality(_job(a, b)) == expected


def test_a_not_requested_b_ready_is_terminal() -> None:
    state = _job(
        SignalAvailability.NOT_REQUESTED,
        SignalAvailability.READY,
        request_a=False,
    )
    assert state.terminality == JobTerminality.TERMINAL_SUCCESS


def test_a_ready_b_not_requested_is_terminal() -> None:
    state = _job(
        SignalAvailability.READY,
        SignalAvailability.NOT_REQUESTED,
        request_b=False,
    )
    assert state.terminality == JobTerminality.TERMINAL_SUCCESS


def test_waiting_for_approval_is_in_flight_not_failed() -> None:
    state = _job(
        SignalAvailability.READY,
        SignalAvailability.PENDING,
        cost=CostAuthorization(state=CostAuthorizationState.WAITING_FOR_APPROVAL),
    )
    assert state.terminality == JobTerminality.IN_FLIGHT


def test_interrupted_execution_is_terminal_failure() -> None:
    state = _job(
        SignalAvailability.READY,
        SignalAvailability.FETCHING,
        execution=ExecutionState.INTERRUPTED,
    )
    assert state.terminality == JobTerminality.TERMINAL_FAILURE


def test_signal_b_section_rejects_historical_result() -> None:
    with pytest.raises(ValueError, match="historical result"):
        SignalSection(
            kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            requested=True,
            availability=SignalAvailability.READY,
            progress=SignalProgress(phase=SignalPhase.READY),
            historical_result={"q_A": 0.2},
        )


def test_progress_cannot_regress() -> None:
    current = SignalProgress(
        phase=SignalPhase.VENDOR_PROCESSING,
        completed_units=4,
        required_units=10,
    )
    nxt = SignalProgress(
        phase=SignalPhase.VENDOR_PROCESSING,
        completed_units=3,
        required_units=10,
    )
    with pytest.raises(ValueError, match="regress"):
        apply_progress(current, nxt)


def test_combined_score_remains_forbidden() -> None:
    assert _job(SignalAvailability.READY, SignalAvailability.READY).combined_score_authorized is False
