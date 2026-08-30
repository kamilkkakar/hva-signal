"""Candidate public DTOs serialize without publishing a route."""

from datetime import datetime

from app.domain.job_lifecycle import (
    CostAuthorization,
    CostAuthorizationState,
    ExecutionState,
    SignalPhase,
    SignalProgress,
    SignalSection,
    SignalSectionError,
    TwoSignalJobState,
    empty_section,
)
from app.domain.public_contract import PublicJobStatus, PublicReasonCode
from app.domain.signals import (
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)
from app.services.orchestrator import run_replay_analysis
from app.services.public_contract_serialize import (
    historical_section_from_analysis_result,
    serialize_legacy_a_only_job,
    serialize_two_signal_job,
)
from app.domain.requests import AnalysisRequest


def _snapshot(*, availability=SignalAvailability.READY, missing=None) -> SelectedTimeSnapshot:
    return SelectedTimeSnapshot(
        area_id="phoenix-demo",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=availability,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id="phoenix-demo",
            geometry_version="GEO_V1",
        ),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="z1",
                mean_temperature_c=33.1 if availability != SignalAvailability.UNAVAILABLE else None,
                tile_count=2,
                coverage_status="ok" if availability == SignalAvailability.READY else "insufficient_evidence",
            )
        ],
        expected_zone_count=25,
        valid_zone_count=1 if availability == SignalAvailability.PARTIAL else (
            0 if availability == SignalAvailability.UNAVAILABLE else 1
        ),
        missing_zone_ids=missing or [],
    )


def _job(
    a: SignalAvailability,
    b: SignalAvailability,
    *,
    request_a=True,
    request_b=True,
    cost=None,
    snapshot=None,
    b_error=None,
) -> TwoSignalJobState:
    hist = (
        empty_section(ThermalSignalKind.HISTORICAL_NORMALIZED, requested=False, area_id="phoenix-demo")
        if not request_a
        else empty_section(ThermalSignalKind.HISTORICAL_NORMALIZED, requested=True, area_id="phoenix-demo")
    )
    sel = (
        empty_section(ThermalSignalKind.SELECTED_TIME_SNAPSHOT, requested=False, area_id="phoenix-demo")
        if not request_b
        else empty_section(ThermalSignalKind.SELECTED_TIME_SNAPSHOT, requested=True, area_id="phoenix-demo")
    )
    if request_a:
        hist = hist.model_copy(
            update={
                "availability": a,
                "progress": SignalProgress(phase=SignalPhase.READY, message=a.value),
                "historical_result": {"thermal_differentiation_state": a.value},
                "provenance": SignalProvenance(
                    signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                    area_id="phoenix-demo",
                    reference_version="PHX_ZTSI_REF_V1",
                ),
            }
        )
    if request_b:
        sel = sel.model_copy(
            update={
                "availability": b,
                "progress": SignalProgress(phase=SignalPhase.READY, message=b.value),
                "selected_time_result": snapshot,
                "error": b_error,
                "provenance": SignalProvenance(
                    signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
                    area_id="phoenix-demo",
                    geometry_version="GEO_V1",
                ),
            }
        )
    return TwoSignalJobState(
        job_id="job_pub",
        area_id="phoenix-demo",
        historical=hist,
        selected_time=sel,
        cost_authorization=cost or CostAuthorization(),
        execution_state=ExecutionState.RUNNING,
    )


def test_a_ready_b_fetching_is_running() -> None:
    dto = serialize_two_signal_job(_job(SignalAvailability.READY, SignalAvailability.FETCHING))
    assert dto.status == PublicJobStatus.RUNNING
    assert dto.historical.availability == SignalAvailability.READY
    assert dto.selected_time.availability == SignalAvailability.FETCHING
    assert dto.combined_score_authorized is False


def test_a_not_prepared_b_ready_is_complete() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.NOT_PREPARED,
            SignalAvailability.READY,
            snapshot=_snapshot(),
        )
    )
    assert dto.status == PublicJobStatus.COMPLETE
    assert dto.selected_time.selected_time_result is not None
    assert "q_A" not in dto.selected_time.selected_time_result.model_dump()
    assert dto.selected_time.provenance.reference_version is None


def test_a_ready_b_failed_is_partial() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.READY,
            SignalAvailability.FAILED,
            b_error=SignalSectionError(
                reason_code="VENDOR_FAILED",
                user_message="Selected-time snapshot could not be retrieved.",
            ),
        )
    )
    assert dto.status == PublicJobStatus.PARTIAL
    assert dto.selected_time.error.reason_code == PublicReasonCode.VENDOR_FAILED


def test_waiting_for_approval_is_awaiting_not_failed() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.NOT_PREPARED,
            SignalAvailability.WAITING_FOR_APPROVAL,
            cost=CostAuthorization(state=CostAuthorizationState.WAITING_FOR_APPROVAL),
        )
    )
    assert dto.status == PublicJobStatus.AWAITING_APPROVAL
    assert dto.spend is not None
    assert dto.spend.state == "WAITING_FOR_APPROVAL"


def test_denied_spend_is_not_complete() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.NOT_PREPARED,
            SignalAvailability.FAILED,
            cost=CostAuthorization(state=CostAuthorizationState.DENIED, reason="denied"),
            b_error=SignalSectionError(
                reason_code="SPEND_DENIED",
                user_message="Selected-time acquisition was not approved.",
            ),
        )
    )
    assert dto.status == PublicJobStatus.PARTIAL
    assert dto.spend.state == "DENIED"


def test_partial_b_exposes_missing_unknown() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.READY,
            SignalAvailability.PARTIAL,
            snapshot=_snapshot(availability=SignalAvailability.PARTIAL, missing=["z2"]),
        )
    )
    result = dto.selected_time.selected_time_result
    assert result.missing_zone_ids == ["z2"]
    assert result.expected_zone_count == 25
    assert result.temperature_min_c is not None
    dumped = result.model_dump()
    assert "low_contrast" not in dumped
    assert "color" not in dumped


def test_legacy_sufficient_and_insufficient_map_to_a_section() -> None:
    sufficient = run_replay_analysis(
        AnalysisRequest.model_validate(
            {
                "area_id": "phoenix-demo",
                "analysis_time": datetime(2022, 6, 30, 3, 0),
                "analysis_mode": "retrospective",
                "horizon_hours": 0,
                "lookback_hours": 0,
                "granularity_m": 100,
                "data_mode": "replay",
            }
        )
    )
    section = historical_section_from_analysis_result(sufficient, area_id="phoenix-demo")
    assert section.availability.value == "READY"
    assert section.historical_result["thermal_differentiation_state"] == "SUFFICIENT"
    assert abs(section.historical_result["hazard_spread"]["observed_spread"] - 0.13548387096774192) <= 1e-12
    assert section.selected_time_result is None

    insufficient = run_replay_analysis(
        AnalysisRequest.model_validate(
            {
                "area_id": "phoenix-demo",
                "analysis_time": datetime(2022, 7, 1, 3, 0),
                "analysis_mode": "retrospective",
                "horizon_hours": 0,
                "lookback_hours": 0,
                "granularity_m": 100,
                "data_mode": "replay",
            }
        )
    )
    section_i = historical_section_from_analysis_result(insufficient, area_id="phoenix-demo")
    assert section_i.availability.value == "D8_INSUFFICIENT"
    assert section_i.error.reason_code == PublicReasonCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT
    assert abs(section_i.historical_result["hazard_spread"]["observed_spread"] - 0.0439665471923536) <= 1e-12

    legacy = serialize_legacy_a_only_job(
        job_id="job_legacy",
        area_id="phoenix-demo",
        result=sufficient,
    )
    assert legacy.status == PublicJobStatus.COMPLETE
    assert legacy.selected_time.requested is False
    assert legacy.selected_time.selected_time_result is None
    assert legacy.legacy_thermal_source == sufficient.data_status.value
    assert any(
        "q_A" in zone for zone in (legacy.historical.historical_result or {}).get("zones", [])
    )


def test_a_d8_insufficient_b_ready_is_complete() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.D8_INSUFFICIENT,
            SignalAvailability.READY,
            snapshot=_snapshot(),
        )
    )
    assert dto.status == PublicJobStatus.COMPLETE
    assert dto.historical.availability == SignalAvailability.D8_INSUFFICIENT
    assert dto.selected_time.selected_time_result is not None


def test_both_failed_is_failed() -> None:
    dto = serialize_two_signal_job(
        _job(SignalAvailability.FAILED, SignalAvailability.FAILED)
    )
    assert dto.status == PublicJobStatus.FAILED


def test_interrupted_execution_is_failed() -> None:
    state = _job(SignalAvailability.READY, SignalAvailability.FETCHING)
    state = state.model_copy(update={"execution_state": ExecutionState.INTERRUPTED})
    dto = serialize_two_signal_job(state)
    assert dto.status == PublicJobStatus.FAILED


def test_denied_waiting_section_serializes_as_failed_b() -> None:
    dto = serialize_two_signal_job(
        _job(
            SignalAvailability.READY,
            SignalAvailability.WAITING_FOR_APPROVAL,
            cost=CostAuthorization(state=CostAuthorizationState.DENIED, reason="denied"),
        )
    )
    assert dto.status == PublicJobStatus.PARTIAL
    assert dto.selected_time.availability == SignalAvailability.FAILED


def test_unknown_area_failed_job() -> None:
    hist = empty_section(
        ThermalSignalKind.HISTORICAL_NORMALIZED,
        requested=True,
        area_id="no-such-area",
    ).model_copy(
        update={
            "availability": SignalAvailability.FAILED,
            "progress": SignalProgress(phase=SignalPhase.FAILED, message="unknown"),
            "error": SignalSectionError(
                reason_code="UNKNOWN_AREA",
                user_message="Area is not registered.",
            ),
        }
    )
    sel = empty_section(
        ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        requested=True,
        area_id="no-such-area",
    ).model_copy(
        update={
            "availability": SignalAvailability.FAILED,
            "progress": SignalProgress(phase=SignalPhase.FAILED, message="unknown"),
            "error": SignalSectionError(
                reason_code="UNKNOWN_AREA",
                user_message="Area is not registered.",
            ),
        }
    )
    dto = serialize_two_signal_job(
        TwoSignalJobState(
            job_id="job_unknown",
            area_id="no-such-area",
            historical=hist,
            selected_time=sel,
            execution_state=ExecutionState.FINISHED,
        )
    )
    assert dto.status == PublicJobStatus.FAILED
    assert dto.historical.error.reason_code == PublicReasonCode.UNKNOWN_AREA


def test_a_only_omits_b_result_and_may_expose_legacy_source() -> None:
    dto = serialize_two_signal_job(
        _job(SignalAvailability.READY, SignalAvailability.NOT_REQUESTED, request_b=False)
    )
    assert dto.status == PublicJobStatus.COMPLETE
    assert dto.selected_time.requested is False
    assert dto.selected_time.selected_time_result is None
