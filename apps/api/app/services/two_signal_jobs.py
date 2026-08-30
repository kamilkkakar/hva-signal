"""P2 two-signal job service. Reuse-only Signal B. Zero vendor calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Literal, Protocol

from app.core.area_registry import (
    PHOENIX_AOI_TIMEZONE,
    PHOENIX_DEMO_AREA_ID,
    resolve_area_geography,
)
from app.core.job_store import AnalysisJob, JobStore
from app.core.jobs import job_store
from app.domain.enums import AnalysisMode, DataMode, DataStatus, JobStatus, ThermalDataSource
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
from app.domain.phoenix_v1 import REFERENCE_VERSION, THERMAL_AGGREGATION_VERSION
from app.domain.requests import AnalysisRequest
from app.domain.results import AnalysisResult
from app.domain.signals import (
    SelectedTimeSnapshot,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)
from app.schemas.two_signal_public import (
    PUBLIC_JOB_CONTRACT_VERSION,
    PublicError,
    PublicJobStatus,
    PublicProgress,
    PublicProvenance,
    PublicReasonCode,
    PublicSelectedTimeResult,
    PublicSignalAvailability,
    PublicSignalSection,
    PublicSnapshotZone,
    ThermalSignalKind as PublicSignalKind,
    TwoSignalPublicationRequest,
    TwoSignalPublicJob,
    TwoSignalUnknownJob,
)
from app.services.job_identity import historical_request_fingerprint
from app.services.snapshot_identity import snapshot_request_fingerprint

UNKNOWN_JOB_MESSAGE = "The analysis job is no longer present on this runtime."
SNAPSHOT_UNAVAILABLE_MESSAGE = (
    "No reusable selected-time snapshot is available for this hour."
)
UNKNOWN_AREA_MESSAGE = "This area_id is not a published two-signal analysis window."
TIMEZONE_MISMATCH_MESSAGE = (
    "timezone must match the published geography IANA identifier."
)

_USEFUL = frozenset(
    {
        PublicSignalAvailability.READY,
        PublicSignalAvailability.PARTIAL,
        PublicSignalAvailability.UNAVAILABLE,
        PublicSignalAvailability.NOT_PREPARED,
        PublicSignalAvailability.INSUFFICIENT_REFERENCE,
        PublicSignalAvailability.INSUFFICIENT_EVIDENCE,
        PublicSignalAvailability.D8_INSUFFICIENT,
    }
)
_FAILED = frozenset({PublicSignalAvailability.FAILED})
_IN_FLIGHT = frozenset(
    {
        PublicSignalAvailability.PENDING,
        PublicSignalAvailability.FETCHING,
    }
)
_P3_AVAILABILITY = frozenset(
    {
        SignalAvailability.WAITING_FOR_APPROVAL,
        SignalAvailability.AUTHORIZATION_INSUFFICIENT,
    }
)


class TwoSignalRequestError(ValueError):
    """Create-time 422. Not a job document."""


@dataclass(frozen=True)
class ReuseHit:
    snapshot: SelectedTimeSnapshot
    source: Literal["replay", "fortyguard_cached"]
    joined_in_flight: bool = False


class SelectedTimeReusePort(Protocol):
    """Previously stored B evidence. Never a live vendor client."""

    def get(self, fingerprint: str) -> ReuseHit | None: ...

    def put(self, fingerprint: str, hit: ReuseHit) -> None: ...

    def clear(self) -> None: ...


class InMemorySelectedTimeReuse:
    """Process-local reuse table. Empty by default. No FortyGuard I/O."""

    def __init__(self) -> None:
        self._hits: dict[str, ReuseHit] = {}
        self._lock = Lock()

    def get(self, fingerprint: str) -> ReuseHit | None:
        with self._lock:
            return self._hits.get(fingerprint)

    def put(self, fingerprint: str, hit: ReuseHit) -> None:
        with self._lock:
            self._hits[fingerprint] = hit

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


HistoricalRunner = Callable[[AnalysisRequest], AnalysisResult]


def _default_run_historical(request: AnalysisRequest) -> AnalysisResult:
    """Phoenix 03:00 replay only. Lazy import keeps vendor modules off this path."""
    from app.services.orchestrator import run_replay_analysis

    return run_replay_analysis(request)


class TwoSignalJobService:
    def __init__(
        self,
        *,
        store: JobStore | None = None,
        reuse: SelectedTimeReusePort | None = None,
        run_historical: HistoricalRunner | None = None,
    ) -> None:
        self._store = store or job_store
        self._reuse = reuse if reuse is not None else reuse_store
        self._run_historical = run_historical or _default_run_historical

    def create(self, payload: TwoSignalPublicationRequest) -> TwoSignalPublicJob:
        if payload.area_id == PHOENIX_DEMO_AREA_ID:
            if payload.timezone != PHOENIX_AOI_TIMEZONE:
                raise TwoSignalRequestError(TIMEZONE_MISMATCH_MESSAGE)
        job = self._store.create(_p1_safe_request(payload))
        state = self._build_state(job.job_id, payload)
        self._store.replace_two_signal(job.job_id, state)
        self._sync_p1_projection(job.job_id, state)
        return self._project(self._store.get(job.job_id) or job, state)

    def get(
        self, job_id: str
    ) -> TwoSignalPublicJob | TwoSignalUnknownJob:
        job = self._store.get(job_id)
        if job is None:
            return TwoSignalUnknownJob(job_id=job_id, message=UNKNOWN_JOB_MESSAGE)
        if job.two_signal is not None:
            return self._project(job, job.two_signal)
        return self._project_legacy(job)

    def _build_state(
        self, job_id: str, payload: TwoSignalPublicationRequest
    ) -> TwoSignalJobState:
        request_a = payload.signals.historical is not None
        request_b = payload.signals.selected_time is not None
        historical = empty_section(
            ThermalSignalKind.HISTORICAL_NORMALIZED,
            requested=request_a,
            area_id=payload.area_id,
        )
        selected = empty_section(
            ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            requested=request_b,
            area_id=payload.area_id,
        )
        if request_a:
            historical = self._run_signal_a(historical, payload)
        if request_b:
            selected = self._run_signal_b(selected, payload)
        return TwoSignalJobState(
            job_id=job_id,
            area_id=payload.area_id,
            historical=historical,
            selected_time=selected,
            cost_authorization=CostAuthorization(
                state=CostAuthorizationState.NOT_REQUIRED
            ),
            execution_state=ExecutionState.FINISHED,
        )

    def _run_signal_a(
        self, section: SignalSection, payload: TwoSignalPublicationRequest
    ) -> SignalSection:
        historical_req = payload.signals.historical
        assert historical_req is not None
        if payload.area_id != PHOENIX_DEMO_AREA_ID:
            return _failed_section(
                section,
                reason=PublicReasonCode.UNKNOWN_AREA.value,
                message=UNKNOWN_AREA_MESSAGE,
                target=historical_req.analysis_time,
                timezone=payload.timezone,
            )
        geography = _phoenix_geography()
        fingerprint = historical_request_fingerprint(
            area_id=payload.area_id,
            analysis_time=historical_req.analysis_time,
            timezone=payload.timezone,
            analysis_mode=AnalysisMode.RETROSPECTIVE.value,
            granularity_m=payload.granularity_m,
            data_mode=payload.data_mode,
            geometry_sha256=geography.manifest.geometry_sha256,
            zone_geometry_version=geography.config.zone_geometry_version,
            reference_protocol_id=REFERENCE_VERSION,
            area_config_version=geography.config.version,
        )
        request = AnalysisRequest(
            area_id=payload.area_id,
            analysis_time=historical_req.analysis_time,
            analysis_mode=AnalysisMode.RETROSPECTIVE,
            horizon_hours=0,
            lookback_hours=0,
            granularity_m=payload.granularity_m,
            data_mode=DataMode.REPLAY,
        )
        result = self._run_historical(request)
        availability = _historical_availability(result)
        dumped = result.model_dump(mode="json")
        error = _historical_error(availability)
        return section.model_copy(
            update={
                "availability": availability,
                "progress": SignalProgress(
                    phase=SignalPhase.READY, message=availability.value
                ),
                "historical_result": dumped,
                "error": error,
                "provenance": SignalProvenance(
                    signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                    area_id=payload.area_id,
                    target_timestamp=historical_req.analysis_time,
                    timezone=payload.timezone,
                    source=ThermalDataSource.REPLAY,
                    data_status=DataStatus.REPLAY,
                    geometry_version=result.versions.zone_geometry_version,
                    aggregation_spec_version=result.versions.thermal_aggregation_version,
                    reference_version=(
                        result.hazard_spread.reference_version
                        if result.hazard_spread
                        else REFERENCE_VERSION
                    ),
                    reference_source="cached_reference",
                    vendor_request_fingerprint=fingerprint,
                ),
            }
        )

    def _run_signal_b(
        self, section: SignalSection, payload: TwoSignalPublicationRequest
    ) -> SignalSection:
        selected_req = payload.signals.selected_time
        assert selected_req is not None
        if payload.area_id != PHOENIX_DEMO_AREA_ID:
            return _failed_section(
                section,
                reason=PublicReasonCode.UNKNOWN_AREA.value,
                message=UNKNOWN_AREA_MESSAGE,
                target=selected_req.target_timestamp,
                timezone=payload.timezone,
                snapshot_kind=True,
            )
        geography = _phoenix_geography()
        fingerprint = snapshot_request_fingerprint(
            area_id=payload.area_id,
            geometry_sha256=geography.manifest.geometry_sha256,
            zone_geometry_version=geography.config.zone_geometry_version,
            target_timestamp=selected_req.target_timestamp,
            timezone=payload.timezone,
            analytic=selected_req.analytic,
            granularity_m=payload.granularity_m,
            aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        )
        provenance = SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id=payload.area_id,
            target_timestamp=selected_req.target_timestamp,
            timezone=payload.timezone,
            geometry_version=geography.config.zone_geometry_version,
            aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
            vendor_request_fingerprint=fingerprint,
        )
        hit = self._reuse.get(fingerprint)
        if hit is None:
            return section.model_copy(
                update={
                    "availability": SignalAvailability.UNAVAILABLE,
                    "progress": SignalProgress(
                        phase=SignalPhase.READY, message="Reuse miss."
                    ),
                    "error": SignalSectionError(
                        reason_code=PublicReasonCode.SNAPSHOT_UNAVAILABLE.value,
                        user_message=SNAPSHOT_UNAVAILABLE_MESSAGE,
                    ),
                    "provenance": provenance.model_copy(
                        update={"data_status": DataStatus.UNAVAILABLE}
                    ),
                }
            )
        source = (
            ThermalDataSource.REPLAY
            if hit.source == "replay"
            else ThermalDataSource.FORTYGUARD_CACHED
        )
        data_status = (
            DataStatus.REPLAY if hit.source == "replay" else DataStatus.CACHED
        )
        reason = None
        if hit.joined_in_flight:
            reason = SignalSectionError(
                reason_code=PublicReasonCode.JOINED_IN_FLIGHT.value,
                user_message="Joined an in-flight selected-time snapshot.",
            )
        elif hit.source == "fortyguard_cached":
            reason = SignalSectionError(
                reason_code=PublicReasonCode.EVIDENCE_REUSED.value,
                user_message="Reused a previously stored selected-time snapshot.",
            )
        snapshot = hit.snapshot.model_copy(
            update={
                "availability": SignalAvailability.READY,
                "geometry_sha256": (
                    hit.snapshot.geometry_sha256 or geography.manifest.geometry_sha256
                ),
                "provenance": provenance.model_copy(
                    update={
                        "source": source,
                        "data_status": data_status,
                        "reference_version": None,
                        "reference_source": None,
                    }
                ),
            }
        )
        return section.model_copy(
            update={
                "availability": SignalAvailability.READY,
                "progress": SignalProgress(
                    phase=SignalPhase.READY, message="Ready."
                ),
                "selected_time_result": snapshot,
                "error": reason,
                "provenance": snapshot.provenance,
            }
        )

    def _project(self, job: AnalysisJob, state: TwoSignalJobState) -> TwoSignalPublicJob:
        historical = _public_section(state.historical)
        selected = _public_section(state.selected_time)
        return TwoSignalPublicJob(
            contract_version=PUBLIC_JOB_CONTRACT_VERSION,
            job_id=job.job_id,
            area_id=state.area_id,
            status=_public_status(historical, selected),
            combined_score_authorized=False,
            historical=historical,
            selected_time=selected,
            legacy_thermal_source=_legacy_thermal_source(state),
            created_at=job.created_at,
            recoverable=None,
            message=job.message,
        )

    def _project_legacy(self, job: AnalysisJob) -> TwoSignalPublicJob:
        area_id = str((job.request or {}).get("area_id") or "")
        selected = _not_requested_b()
        if job.result is None:
            historical = PublicSignalSection(
                kind=PublicSignalKind.HISTORICAL_NORMALIZED,
                requested=True,
                availability=(
                    PublicSignalAvailability.PENDING
                    if not job.is_terminal()
                    else PublicSignalAvailability.FAILED
                ),
                progress=PublicProgress(
                    phase="queued" if not job.is_terminal() else "failed",
                    message=job.message,
                ),
            )
            status = (
                PublicJobStatus.QUEUED
                if job.status == JobStatus.QUEUED
                else PublicJobStatus.RUNNING
                if not job.is_terminal()
                else PublicJobStatus.FAILED
            )
            return TwoSignalPublicJob(
                job_id=job.job_id,
                area_id=area_id,
                status=status,
                historical=historical,
                selected_time=selected,
                created_at=job.created_at,
                message=job.message,
            )
        result = AnalysisResult.model_validate(job.result)
        historical = _public_section_from_analysis_result(result, area_id=area_id)
        return TwoSignalPublicJob(
            job_id=job.job_id,
            area_id=area_id,
            status=PublicJobStatus.COMPLETE,
            historical=historical,
            selected_time=selected,
            legacy_thermal_source=(
                historical.provenance.source if historical.provenance is not None else None
            ),
            created_at=job.created_at,
            message=job.message,
        )

    def _sync_p1_projection(self, job_id: str, state: TwoSignalJobState) -> None:
        historical = _public_section(state.historical)
        selected = _public_section(state.selected_time)
        status = _public_status(historical, selected)
        mapped = {
            PublicJobStatus.COMPLETE: JobStatus.COMPLETE,
            PublicJobStatus.PARTIAL: JobStatus.PARTIAL,
            PublicJobStatus.FAILED: JobStatus.FAILED,
            PublicJobStatus.QUEUED: JobStatus.QUEUED,
            PublicJobStatus.RUNNING: JobStatus.COMPUTING,
        }[status]
        result = state.historical.historical_result
        if result is not None and mapped in {
            JobStatus.COMPLETE,
            JobStatus.PARTIAL,
            JobStatus.FAILED,
        }:
            self._store.set_result(job_id, result, mapped, message=status.value)
            return
        self._store.update_status(
            job_id,
            mapped,
            message=status.value,
            execution_state=ExecutionState.FINISHED
            if mapped
            in {JobStatus.COMPLETE, JobStatus.PARTIAL, JobStatus.FAILED}
            else ExecutionState.RUNNING,
        )


def _phoenix_geography():
    return resolve_area_geography(PHOENIX_DEMO_AREA_ID)


def _p1_safe_request(payload: TwoSignalPublicationRequest) -> dict[str, Any]:
    """P1 GET must not grow B temperatures or unpublished keys."""
    safe: dict[str, Any] = {
        "area_id": payload.area_id,
        "granularity_m": payload.granularity_m,
        "data_mode": payload.data_mode,
    }
    if payload.signals.historical is not None:
        safe["analysis_time"] = payload.signals.historical.analysis_time.isoformat()
        safe["analysis_mode"] = AnalysisMode.RETROSPECTIVE.value
        safe["horizon_hours"] = 0
        safe["lookback_hours"] = 0
    return safe


def _failed_section(
    section: SignalSection,
    *,
    reason: str,
    message: str,
    target: datetime,
    timezone: str,
    snapshot_kind: bool = False,
) -> SignalSection:
    kind = (
        ThermalSignalKind.SELECTED_TIME_SNAPSHOT
        if snapshot_kind
        else ThermalSignalKind.HISTORICAL_NORMALIZED
    )
    return section.model_copy(
        update={
            "availability": SignalAvailability.FAILED,
            "progress": SignalProgress(phase=SignalPhase.FAILED, message=message),
            "error": SignalSectionError(reason_code=reason, user_message=message),
            "provenance": SignalProvenance(
                signal_kind=kind,
                area_id=section.provenance.area_id if section.provenance else "",
                target_timestamp=target,
                timezone=timezone,
            ),
        }
    )


def _historical_availability(result: AnalysisResult) -> SignalAvailability:
    if result.reference_quality == "INSUFFICIENT_REFERENCE":
        return SignalAvailability.INSUFFICIENT_REFERENCE
    if result.thermal_differentiation_state == "INSUFFICIENT":
        return SignalAvailability.D8_INSUFFICIENT
    if result.thermal_differentiation_state == "SUFFICIENT":
        return SignalAvailability.READY
    return SignalAvailability.INSUFFICIENT_EVIDENCE


def _historical_error(availability: SignalAvailability) -> SignalSectionError | None:
    if availability == SignalAvailability.D8_INSUFFICIENT:
        return SignalSectionError(
            reason_code=PublicReasonCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value,
            user_message="Historical thermal differentiation is insufficient for ranking.",
        )
    if availability == SignalAvailability.INSUFFICIENT_REFERENCE:
        return SignalSectionError(
            reason_code=PublicReasonCode.INSUFFICIENT_REFERENCE.value,
            user_message="Historical reference is insufficient.",
        )
    return None


def _map_availability(value: SignalAvailability) -> PublicSignalAvailability:
    if value in _P3_AVAILABILITY:
        return PublicSignalAvailability.FAILED
    return PublicSignalAvailability(value.value)


def _public_section(section: SignalSection) -> PublicSignalSection:
    availability = _map_availability(section.availability)
    error = None
    if section.error is not None:
        try:
            code = PublicReasonCode(section.error.reason_code)
        except ValueError:
            code = PublicReasonCode.VENDOR_FAILED
        error = PublicError(reason_code=code, message=section.error.user_message)
    return PublicSignalSection(
        kind=PublicSignalKind(section.kind.value),
        requested=section.requested,
        availability=availability,
        progress=PublicProgress(
            phase=section.progress.phase.value,
            message=section.progress.message,
            completed_units=section.progress.completed_units,
            required_units=section.progress.required_units,
            updated_at=section.updated_at,
        ),
        provenance=_public_provenance(section),
        error=error,
        historical_result=(
            section.historical_result
            if section.kind == ThermalSignalKind.HISTORICAL_NORMALIZED
            else None
        ),
        selected_time_result=_public_snapshot(section.selected_time_result),
    )


def _public_provenance(section: SignalSection) -> PublicProvenance | None:
    if section.provenance is None:
        return None
    source = section.provenance.source.value if section.provenance.source else None
    if (
        section.kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT
        and source == ThermalDataSource.FORTYGUARD_LIVE.value
    ):
        source = None
    geometry_sha256 = None
    if (
        section.kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT
        and section.selected_time_result is not None
        and section.selected_time_result.geometry_sha256
    ):
        geometry_sha256 = section.selected_time_result.geometry_sha256
    return PublicProvenance(
        signal_kind=PublicSignalKind(section.provenance.signal_kind.value),
        source=source,  # type: ignore[arg-type]
        data_status=(
            section.provenance.data_status.value
            if section.provenance.data_status
            else None
        ),
        target_timestamp=section.provenance.target_timestamp,
        timezone=section.provenance.timezone,
        geometry_version=section.provenance.geometry_version,
        geometry_sha256=geometry_sha256,
        aggregation_spec_version=section.provenance.aggregation_spec_version,
        reference_version=(
            section.provenance.reference_version
            if section.kind == ThermalSignalKind.HISTORICAL_NORMALIZED
            else None
        ),
        reference_source=(
            section.provenance.reference_source
            if section.kind == ThermalSignalKind.HISTORICAL_NORMALIZED
            else None
        ),
        request_fingerprint=section.provenance.vendor_request_fingerprint,
    )


def _public_snapshot(
    snapshot: SelectedTimeSnapshot | None,
) -> PublicSelectedTimeResult | None:
    if snapshot is None:
        return None
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


def _public_section_from_analysis_result(
    result: AnalysisResult, *, area_id: str
) -> PublicSignalSection:
    availability = _map_availability(_historical_availability(result))
    error = None
    domain_error = _historical_error(_historical_availability(result))
    if domain_error is not None:
        error = PublicError(
            reason_code=PublicReasonCode(domain_error.reason_code),
            message=domain_error.user_message,
        )
    return PublicSignalSection(
        kind=PublicSignalKind.HISTORICAL_NORMALIZED,
        requested=True,
        availability=availability,
        progress=PublicProgress(phase="ready", message=availability.value),
        provenance=PublicProvenance(
            signal_kind=PublicSignalKind.HISTORICAL_NORMALIZED,
            source="replay",
            data_status="replay",
            geometry_version=result.versions.zone_geometry_version,
            reference_version=(
                result.hazard_spread.reference_version if result.hazard_spread else None
            ),
            reference_source="cached_reference" if result.hazard_spread else None,
        ),
        error=error,
        historical_result=result.model_dump(mode="json"),
    )


def _not_requested_b() -> PublicSignalSection:
    return PublicSignalSection(
        kind=PublicSignalKind.SELECTED_TIME_SNAPSHOT,
        requested=False,
        availability=PublicSignalAvailability.NOT_REQUESTED,
        progress=PublicProgress(phase="ready", message="Not requested."),
    )


def _public_status(
    historical: PublicSignalSection, selected: PublicSignalSection
) -> PublicJobStatus:
    classes: list[str] = []
    pending_only_a = (
        historical.requested
        and historical.availability == PublicSignalAvailability.PENDING
        and not selected.requested
    )
    for section in (historical, selected):
        if not section.requested:
            continue
        if section.availability in _IN_FLIGHT:
            classes.append("inflight")
        elif section.availability in _FAILED:
            classes.append("failed")
        elif section.availability in _USEFUL:
            classes.append("useful")
        else:
            classes.append("inflight")
    if not classes:
        return PublicJobStatus.FAILED
    if "inflight" in classes:
        return PublicJobStatus.QUEUED if pending_only_a else PublicJobStatus.RUNNING
    if "useful" in classes and "failed" in classes:
        return PublicJobStatus.PARTIAL
    if "failed" in classes:
        return PublicJobStatus.FAILED
    return PublicJobStatus.COMPLETE


def _legacy_thermal_source(state: TwoSignalJobState) -> str | None:
    if state.selected_time.requested:
        return None
    provenance = state.historical.provenance
    if provenance is not None and provenance.source is not None:
        return provenance.source.value
    return None


reuse_store = InMemorySelectedTimeReuse()
two_signal_job_service = TwoSignalJobService(reuse=reuse_store)


def reset_two_signal_runtime() -> None:
    reuse_store.clear()
