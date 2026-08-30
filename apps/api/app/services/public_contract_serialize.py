"""Pure adapters: legacy AnalysisResult and TwoSignalJobState → candidate DTOs."""

from __future__ import annotations

from app.domain.job_lifecycle import (
    CostAuthorization,
    CostAuthorizationState,
    JobTerminality,
    SignalSection,
    TwoSignalJobState,
    effective_section_availability,
)
from app.domain.public_contract import (
    PublicError,
    PublicJobStatus,
    PublicProgress,
    PublicProvenance,
    PublicReasonCode,
    PublicSelectedTimeResult,
    PublicSignalSection,
    PublicSnapshotZone,
    PublicSpendView,
    TwoSignalPublicJob,
)
from app.domain.results import AnalysisResult
from app.domain.signals import (
    SelectedTimeSnapshot,
    SignalAvailability,
    ThermalSignalKind,
)


def public_job_status(state: TwoSignalJobState) -> PublicJobStatus:
    if state.terminality == JobTerminality.IN_FLIGHT:
        if (
            state.cost_authorization.state == CostAuthorizationState.WAITING_FOR_APPROVAL
            or state.selected_time.availability == SignalAvailability.WAITING_FOR_APPROVAL
        ):
            return PublicJobStatus.AWAITING_APPROVAL
        if state.historical.availability == SignalAvailability.PENDING and (
            not state.selected_time.requested
            or state.selected_time.availability == SignalAvailability.NOT_REQUESTED
        ):
            return PublicJobStatus.QUEUED
        return PublicJobStatus.RUNNING
    if state.terminality == JobTerminality.TERMINAL_PARTIAL:
        return PublicJobStatus.PARTIAL
    if state.terminality == JobTerminality.TERMINAL_FAILURE:
        return PublicJobStatus.FAILED
    return PublicJobStatus.COMPLETE


def _progress(section: SignalSection) -> PublicProgress:
    return PublicProgress(
        phase=section.progress.phase.value,
        message=section.progress.message,
        completed_units=section.progress.completed_units,
        required_units=section.progress.required_units,
        updated_at=section.updated_at,
    )


def _provenance(section: SignalSection) -> PublicProvenance | None:
    if section.provenance is None:
        return None
    return PublicProvenance(
        signal_kind=section.provenance.signal_kind,
        source=section.provenance.source.value if section.provenance.source else None,
        data_status=section.provenance.data_status.value
        if section.provenance.data_status
        else None,
        target_timestamp=section.provenance.target_timestamp,
        timezone=section.provenance.timezone,
        geometry_version=section.provenance.geometry_version,
        aggregation_spec_version=section.provenance.aggregation_spec_version,
        reference_version=section.provenance.reference_version,
        reference_source=section.provenance.reference_source,
        request_fingerprint=section.provenance.vendor_request_fingerprint,
    )


def _error(section: SignalSection) -> PublicError | None:
    if section.error is None:
        return None
    try:
        code = PublicReasonCode(section.error.reason_code)
    except ValueError:
        code = PublicReasonCode.VENDOR_FAILED
    return PublicError(reason_code=code, message=section.error.user_message)


def _snapshot_result(snapshot: SelectedTimeSnapshot) -> PublicSelectedTimeResult:
    temps = [
        zone.mean_temperature_c
        for zone in snapshot.zones
        if zone.mean_temperature_c is not None
    ]
    return PublicSelectedTimeResult(
        target_timestamp=snapshot.target_timestamp,
        timezone=snapshot.timezone,
        zones=[
            PublicSnapshotZone(
                zone_id=zone.zone_id,
                mean_temperature_c=zone.mean_temperature_c,
                tile_count=zone.tile_count,
                coverage_status=zone.coverage_status,
            )
            for zone in snapshot.zones
        ],
        expected_zone_count=snapshot.expected_zone_count,
        valid_zone_count=snapshot.valid_zone_count,
        missing_zone_ids=list(snapshot.missing_zone_ids),
        temperature_min_c=min(temps) if temps else None,
        temperature_max_c=max(temps) if temps else None,
    )


def _section_to_public(
    section: SignalSection, *, availability: SignalAvailability | None = None
) -> PublicSignalSection:
    return PublicSignalSection(
        kind=section.kind,
        requested=section.requested,
        availability=availability if availability is not None else section.availability,
        progress=_progress(section),
        provenance=_provenance(section),
        error=_error(section),
        historical_result=section.historical_result
        if section.kind == ThermalSignalKind.HISTORICAL_NORMALIZED
        else None,
        selected_time_result=(
            _snapshot_result(section.selected_time_result)
            if section.selected_time_result is not None
            else None
        ),
    )


def _spend_view(auth: CostAuthorization) -> PublicSpendView | None:
    if auth.state == CostAuthorizationState.NOT_REQUIRED:
        return None
    public_state = "APPROVED" if auth.state == CostAuthorizationState.AUTHORIZED else auth.state.value
    return PublicSpendView(
        state=public_state,
        requested_units=auth.requested_units,
        planned_acquisition_units=auth.planned_acquisition_units,
        authorized_max_units=auth.authorized_max_units,
        reason=auth.reason,
    )


def _legacy_thermal_source(state: TwoSignalJobState) -> str | None:
    """A-only compatibility. Not authoritative when Signal B is requested."""
    if state.selected_time.requested:
        return None
    provenance = state.historical.provenance
    if provenance is not None and provenance.source is not None:
        return provenance.source.value
    if state.historical.historical_result:
        status = state.historical.historical_result.get("data_status")
        if status == "replay":
            return "replay"
    return None


def serialize_two_signal_job(state: TwoSignalJobState) -> TwoSignalPublicJob:
    return TwoSignalPublicJob(
        job_id=state.job_id,
        area_id=state.area_id,
        status=public_job_status(state),
        historical=_section_to_public(state.historical),
        selected_time=_section_to_public(
            state.selected_time,
            availability=effective_section_availability(state, state.selected_time),
        ),
        spend=_spend_view(state.cost_authorization),
        legacy_thermal_source=_legacy_thermal_source(state),
    )


def historical_availability_from_result(result: AnalysisResult) -> SignalAvailability:
    if result.reference_quality == "INSUFFICIENT_REFERENCE":
        return SignalAvailability.INSUFFICIENT_REFERENCE
    if result.thermal_differentiation_state == "INSUFFICIENT":
        return SignalAvailability.D8_INSUFFICIENT
    if result.thermal_differentiation_state == "SUFFICIENT":
        return SignalAvailability.READY
    return SignalAvailability.INSUFFICIENT_EVIDENCE


def historical_section_from_analysis_result(
    result: AnalysisResult,
    *,
    area_id: str,
) -> PublicSignalSection:
    """Legacy A-only adapter. Does not invent Signal B."""
    availability = historical_availability_from_result(result)
    reason = None
    if availability == SignalAvailability.D8_INSUFFICIENT:
        reason = PublicError(
            reason_code=PublicReasonCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
            message="Historical thermal differentiation is insufficient for ranking.",
        )
    elif availability == SignalAvailability.INSUFFICIENT_REFERENCE:
        reason = PublicError(
            reason_code=PublicReasonCode.INSUFFICIENT_REFERENCE,
            message="Historical reference is insufficient.",
        )
    dumped = result.model_dump(mode="json")
    return PublicSignalSection(
        kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
        requested=True,
        availability=availability,
        progress=PublicProgress(phase="ready", message=availability.value),
        provenance=PublicProvenance(
            signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
            data_status=result.data_status.value,
            geometry_version=result.versions.zone_geometry_version,
            reference_version=result.hazard_spread.reference_version
            if result.hazard_spread
            else None,
            source="replay" if result.data_status.value == "replay" else result.data_status.value,
        ),
        error=reason,
        historical_result=dumped,
    )


def serialize_legacy_a_only_job(
    *,
    job_id: str,
    area_id: str,
    result: AnalysisResult,
) -> TwoSignalPublicJob:
    """Prove current AnalysisResult maps to a Signal-A section. Invents no B."""
    historical = historical_section_from_analysis_result(result, area_id=area_id)
    return TwoSignalPublicJob(
        job_id=job_id,
        area_id=area_id,
        status=PublicJobStatus.COMPLETE,
        historical=historical,
        selected_time=PublicSignalSection(
            kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            requested=False,
            availability=SignalAvailability.NOT_REQUESTED,
            progress=PublicProgress(phase="ready", message="Not requested."),
        ),
        legacy_thermal_source=(
            historical.provenance.source if historical.provenance is not None else None
        ),
    )
