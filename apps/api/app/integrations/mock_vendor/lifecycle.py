"""Mock hosted-live lifecycle. Fake vendor only. Never calls FortyGuard.

Order:
request → validate → cache miss → allowance reserve → submit → activity_id
→ processing → result → normalization → cache → consume.

Crash points are the nine-site matrix. UNKNOWN_VENDOR_STATE never auto-resubmits.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.job_store import InMemoryJobStore, JobStore
from app.domain.aggregation import ThermalAggregationSpec
from app.domain.demo_allowance import (
    AcquisitionPreference,
    DemoAllowanceDecisionCode,
    DemoRequestIdentity,
    ReservationState,
)
from app.domain.enums import DataMode, DataStatus, JobStatus, ThermalDataSource
from app.domain.job_lifecycle import (
    ExecutionState,
    SignalPhase,
    SignalProgress,
    TwoSignalJobState,
    empty_section,
)
from app.domain.public_contract import TwoSignalPublicRequest
from app.domain.signals import SignalAvailability, ThermalSignalKind
from app.integrations.mock_vendor.activity import InMemoryMockActivityStore
from app.integrations.mock_vendor.adapter import MockVendorAdapter, refuse_real_vendor
from app.integrations.mock_vendor.cache import InMemoryMockResultCache
from app.integrations.mock_vendor.crash import CrashController, CrashPoint, SimulatedCrash
from app.integrations.mock_vendor.types import (
    LifecyclePhase,
    MockLifecycleResult,
    MockVendorRequest,
    RestartAction,
)
from app.integrations.mock_vendor.vendor import MockVendorError, MockVendorUnknownActivity
from app.services.demo_allowance_ledger import (
    InMemoryDemoAllowanceLedger,
    policy_blocks_spend,
)
from app.services.snapshot_identity import snapshot_request_fingerprint
from app.services.snapshot_processor import SnapshotGeography, process_selected_time_snapshot


def selected_time_fingerprint(
    request: TwoSignalPublicRequest, geography: SnapshotGeography
) -> str:
    selected = request.signals.selected_time
    if selected is None:
        raise ValueError("Signal B request is required")
    return snapshot_request_fingerprint(
        area_id=request.area_id,
        geometry_sha256=geography.geometry_sha256,
        zone_geometry_version=geography.zone_geometry_version,
        target_timestamp=selected.target_timestamp,
        timezone=request.timezone,
        analytic=selected.analytic,
        granularity_m=request.granularity_m,
        aggregation_spec_version=geography.aggregation_spec.version,
        temporal_mode="single_hour",
    )


def build_mock_vendor_request(
    *,
    request: TwoSignalPublicRequest,
    identity: DemoRequestIdentity,
    geography: SnapshotGeography,
) -> MockVendorRequest:
    selected = request.signals.selected_time
    if selected is None:
        raise ValueError("Signal B request is required")
    return MockVendorRequest(
        area_id=identity.area_id,
        request_fingerprint=identity.request_fingerprint,
        geometry_sha256=identity.geometry_sha256,
        target_timestamp=selected.target_timestamp,
        timezone=request.timezone,
        analytic=selected.analytic,
        granularity_m=request.granularity_m,
        temporal_mode=identity.temporal_mode,
        planned_units=1,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reservation_state(
    ledger: InMemoryDemoAllowanceLedger, reservation_id: str | None
) -> str | None:
    if reservation_id is None:
        return None
    reservation = ledger.get(reservation_id)
    return None if reservation is None else reservation.state.value


def _result(
    *,
    outcome: str,
    phase: LifecyclePhase,
    vendor: MockVendorAdapter,
    crash: CrashController,
    job_id: str | None = None,
    reservation_id: str | None = None,
    reservation_state: str | None = None,
    activity_record_id: str | None = None,
    vendor_activity_id: str | None = None,
    restart_action: str | None = None,
    signal_availability: str | None = None,
    snapshot_valid_zone_count: int | None = None,
    reason: str | None = None,
    cache_hit: bool = False,
) -> MockLifecycleResult:
    return MockLifecycleResult(
        outcome=outcome,  # type: ignore[arg-type]
        phase=phase,
        job_id=job_id,
        reservation_id=reservation_id,
        reservation_state=reservation_state,
        activity_record_id=activity_record_id,
        vendor_activity_id=vendor_activity_id,
        restart_action=restart_action,
        signal_availability=signal_availability,
        vendor_submit_count=vendor.submit_count,
        vendor_paid_submit_count=vendor.paid_submit_count,
        vendor_poll_count=vendor.poll_count,
        snapshot_valid_zone_count=snapshot_valid_zone_count,
        visited_crash_points=[point.value for point, _ in crash.visited],
        reason=reason,
        cache_hit=cache_hit,
    )


def _stamp_b_phase(
    store: JobStore,
    job_id: str,
    *,
    area_id: str,
    phase: SignalPhase,
    availability: SignalAvailability,
    snapshot: Any = None,
    message: str | None = None,
) -> None:
    job = store.get(job_id)
    if job is None:
        return
    historical = (
        job.two_signal.historical
        if job.two_signal is not None
        else empty_section(
            ThermalSignalKind.HISTORICAL_NORMALIZED,
            requested=False,
            area_id=area_id,
        )
    )
    selected = (
        job.two_signal.selected_time
        if job.two_signal is not None
        else empty_section(
            ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            requested=True,
            area_id=area_id,
        )
    )
    selected = selected.model_copy(
        update={
            "availability": availability,
            "progress": SignalProgress(phase=phase, message=message or phase.value),
            "selected_time_result": snapshot
            if snapshot is not None
            else selected.selected_time_result,
        }
    )
    store.replace_two_signal(
        job_id,
        TwoSignalJobState(
            job_id=job_id,
            area_id=area_id,
            historical=historical,
            selected_time=selected,
            execution_state=ExecutionState.RUNNING
            if phase not in {SignalPhase.READY, SignalPhase.FAILED}
            else ExecutionState.FINISHED,
        ),
    )


def _consume_if_reserved(
    ledger: InMemoryDemoAllowanceLedger,
    reservation_id: str,
    identity: DemoRequestIdentity,
    now: datetime,
) -> None:
    reservation = ledger.get(reservation_id)
    if reservation is None or reservation.state != ReservationState.RESERVED:
        return
    ledger.consume(
        reservation_id,
        identity=identity,
        planned_units=reservation.planned_units,
        now=now,
    )


def _validate_request(
    request: TwoSignalPublicRequest, identity: DemoRequestIdentity
) -> str | None:
    selected = request.signals.selected_time
    if selected is None:
        return "signal_b_required"
    if selected.acquisition_preference != AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO:
        return DemoAllowanceDecisionCode.LIVE_DEMO_NOT_REQUESTED.value
    if request.granularity_m != 100 or selected.analytic != "tcm":
        return "unsupported_request"
    if request.data_mode == DataMode.REPLAY:
        return DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE.value
    if identity.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        return "unsupported_request"
    return None


def run_mock_vendor_lifecycle(
    *,
    store: JobStore,
    ledger: InMemoryDemoAllowanceLedger,
    vendor: MockVendorAdapter,
    request: TwoSignalPublicRequest,
    identity: DemoRequestIdentity,
    geography: SnapshotGeography,
    activities: InMemoryMockActivityStore | None = None,
    cache: InMemoryMockResultCache | None = None,
    now: datetime | None = None,
    crash_at: CrashPoint = CrashPoint.NONE,
    crash: CrashController | None = None,
    snapshot_capable: bool = True,
    max_status_polls: int = 8,
) -> MockLifecycleResult:
    """TEST-only mock E2E. Refuses any real vendor."""
    refuse_real_vendor(vendor)
    controller = crash or CrashController(crash_at)
    vendor.bind_crash(controller)
    activities = activities or InMemoryMockActivityStore()
    cache = cache or InMemoryMockResultCache()
    moment = now or _now()

    denied = _validate_request(request, identity)
    if denied is not None:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=controller,
            reason=denied,
        )
    if not snapshot_capable:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=controller,
            reason=DemoAllowanceDecisionCode.NOT_SNAPSHOT_CAPABLE.value,
        )

    spec = build_mock_vendor_request(
        request=request, identity=identity, geography=geography
    )
    if spec.request_fingerprint != identity.request_fingerprint:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=controller,
            reason="fingerprint_mismatch",
        )

    try:
        return _run_from_validated(
            store=store,
            ledger=ledger,
            vendor=vendor,
            request=request,
            identity=identity,
            geography=geography,
            spec=spec,
            activities=activities,
            cache=cache,
            moment=moment,
            crash=controller,
            max_status_polls=max_status_polls,
        )
    except SimulatedCrash as exc:
        record = activities.find_by_fingerprint(identity.request_fingerprint)
        reservation_id = record.reservation_id if record else None
        return _result(
            outcome="crashed",
            phase=record.phase if record else exc.phase,
            vendor=vendor,
            crash=controller,
            job_id=record.job_id if record else None,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record.record_id if record else None,
            vendor_activity_id=record.vendor_activity_id if record else None,
            reason=str(exc),
        )


def _run_from_validated(
    *,
    store: JobStore,
    ledger: InMemoryDemoAllowanceLedger,
    vendor: MockVendorAdapter,
    request: TwoSignalPublicRequest,
    identity: DemoRequestIdentity,
    geography: SnapshotGeography,
    spec: MockVendorRequest,
    activities: InMemoryMockActivityStore,
    cache: InMemoryMockResultCache,
    moment: datetime,
    crash: CrashController,
    max_status_polls: int,
) -> MockLifecycleResult:
    cached = cache.get(identity.request_fingerprint)
    existing = store.find_by_dedupe_key(identity.request_fingerprint)
    if cached is not None or (
        existing is not None and existing.status in {JobStatus.COMPLETE, JobStatus.PARTIAL}
    ):
        return _result(
            outcome="reused",
            phase=LifecyclePhase.CACHE_HIT,
            vendor=vendor,
            crash=crash,
            job_id=existing.job_id if existing else None,
            restart_action=RestartAction.REUSE_CACHE.value,
            reason="cache_hit",
            cache_hit=True,
            snapshot_valid_zone_count=cached.get("valid_zone_count")
            if cached
            else None,
        )

    prior = activities.find_by_fingerprint(identity.request_fingerprint)
    if prior is not None and prior.phase == LifecyclePhase.UNKNOWN_VENDOR_STATE:
        return _result(
            outcome="uncertain",
            phase=LifecyclePhase.UNKNOWN_VENDOR_STATE,
            vendor=vendor,
            crash=crash,
            job_id=prior.job_id,
            reservation_id=prior.reservation_id,
            reservation_state=_reservation_state(ledger, prior.reservation_id),
            activity_record_id=prior.record_id,
            restart_action=RestartAction.NO_RESUBMIT_UNCERTAIN.value,
            reason="no_automatic_paid_retry",
        )
    if prior is not None and prior.phase in {
        LifecyclePhase.FAILED_POST_SUBMIT,
        LifecyclePhase.CONSUMED,
    }:
        return _result(
            outcome="no_resubmit",
            phase=prior.phase,
            vendor=vendor,
            crash=crash,
            job_id=prior.job_id,
            reservation_id=prior.reservation_id,
            reservation_state=_reservation_state(ledger, prior.reservation_id),
            activity_record_id=prior.record_id,
            vendor_activity_id=prior.vendor_activity_id,
            restart_action=RestartAction.NO_RESUBMIT_ALREADY_SPENT.value,
            reason="no_automatic_paid_retry",
        )

    if (
        prior is not None
        and prior.phase == LifecyclePhase.ALLOWANCE_RESERVED
        and not prior.submit_attempted
    ):
        return _continue_after_reserve(
            store=store,
            ledger=ledger,
            vendor=vendor,
            request=request,
            identity=identity,
            geography=geography,
            spec=spec,
            activities=activities,
            cache=cache,
            moment=moment,
            crash=crash,
            job_id=prior.job_id,
            reservation_id=prior.reservation_id,
            record_id=prior.record_id,
            max_status_polls=max_status_polls,
        )

    if existing is not None and existing.status not in {
        JobStatus.COMPLETE,
        JobStatus.PARTIAL,
        JobStatus.FAILED,
    }:
        return _result(
            outcome="joined",
            phase=LifecyclePhase.JOINED,
            vendor=vendor,
            crash=crash,
            job_id=existing.job_id,
            reason=DemoAllowanceDecisionCode.JOIN_IN_FLIGHT.value,
        )

    selected = request.signals.selected_time
    assert selected is not None

    crash.check(CrashPoint.BEFORE_RESERVE, phase=LifecyclePhase.VALIDATED)

    blocked = policy_blocks_spend(ledger.policy, now=moment)
    if blocked is not None:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=crash,
            reason=blocked.value,
        )

    decision = ledger.try_reserve(identity, planned_units=1, now=moment)
    if decision.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION:
        reservation = decision.reservation
        assert reservation is not None
        job, _ = store.create_or_join(
            request.model_dump(mode="json"),
            dedupe_key=identity.request_fingerprint,
        )
        record = activities.create(
            job_id=job.job_id,
            request_fingerprint=identity.request_fingerprint,
            geometry_sha256=identity.geometry_sha256,
            reservation_id=reservation.reservation_id,
        )
        if record.vendor_activity_id or record.submit_attempted:
            return _result(
                outcome="joined",
                phase=LifecyclePhase.JOINED,
                vendor=vendor,
                crash=crash,
                job_id=job.job_id,
                reservation_id=reservation.reservation_id,
                reservation_state=reservation.state.value,
                activity_record_id=record.record_id,
                vendor_activity_id=record.vendor_activity_id,
                reason=decision.code.value,
            )
        return _continue_after_reserve(
            store=store,
            ledger=ledger,
            vendor=vendor,
            request=request,
            identity=identity,
            geography=geography,
            spec=spec,
            activities=activities,
            cache=cache,
            moment=moment,
            crash=crash,
            job_id=job.job_id,
            reservation_id=reservation.reservation_id,
            record_id=record.record_id,
            max_status_polls=max_status_polls,
        )
    if decision.code != DemoAllowanceDecisionCode.ELIGIBLE or decision.reservation is None:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=crash,
            reason=decision.code.value,
        )

    reservation = decision.reservation
    job, _ = store.create_or_join(
        request.model_dump(mode="json"),
        dedupe_key=identity.request_fingerprint,
    )
    record = activities.create(
        job_id=job.job_id,
        request_fingerprint=identity.request_fingerprint,
        geometry_sha256=identity.geometry_sha256,
        reservation_id=reservation.reservation_id,
        phase=LifecyclePhase.ALLOWANCE_RESERVED,
    )
    crash.check(CrashPoint.AFTER_RESERVE, phase=LifecyclePhase.ALLOWANCE_RESERVED)
    return _continue_after_reserve(
        store=store,
        ledger=ledger,
        vendor=vendor,
        request=request,
        identity=identity,
        geography=geography,
        spec=spec,
        activities=activities,
        cache=cache,
        moment=moment,
        crash=crash,
        job_id=job.job_id,
        reservation_id=reservation.reservation_id,
        record_id=record.record_id,
        max_status_polls=max_status_polls,
    )


def _continue_after_reserve(
    *,
    store: JobStore,
    ledger: InMemoryDemoAllowanceLedger,
    vendor: MockVendorAdapter,
    request: TwoSignalPublicRequest,
    identity: DemoRequestIdentity,
    geography: SnapshotGeography,
    spec: MockVendorRequest,
    activities: InMemoryMockActivityStore,
    cache: InMemoryMockResultCache,
    moment: datetime,
    crash: CrashController,
    job_id: str,
    reservation_id: str,
    record_id: str,
    max_status_polls: int,
) -> MockLifecycleResult:
    selected = request.signals.selected_time
    assert selected is not None

    recheck = cache.get(identity.request_fingerprint)
    existing = store.find_by_dedupe_key(identity.request_fingerprint)
    if recheck is not None or (
        existing is not None and existing.status in {JobStatus.COMPLETE, JobStatus.PARTIAL}
    ):
        reservation = ledger.get(reservation_id)
        if reservation is not None and reservation.state == ReservationState.RESERVED:
            ledger.release(reservation_id)
        return _result(
            outcome="reused",
            phase=LifecyclePhase.CACHE_HIT,
            vendor=vendor,
            crash=crash,
            job_id=job_id,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record_id,
            restart_action=RestartAction.RELEASE_AND_STOP.value,
            reason="compatible_result_appeared",
            cache_hit=True,
        )

    reservation = ledger.get(reservation_id)
    if reservation is None or reservation.state != ReservationState.RESERVED:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=crash,
            job_id=job_id,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record_id,
            reason="reservation_not_reserved",
        )
    if reservation.request_fingerprint != identity.request_fingerprint:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=crash,
            job_id=job_id,
            reservation_id=reservation_id,
            reason="fingerprint_mismatch",
        )
    blocked = policy_blocks_spend(ledger.policy, now=moment)
    if blocked is not None:
        return _result(
            outcome="denied",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=crash,
            job_id=job_id,
            reservation_id=reservation_id,
            reservation_state=reservation.state.value,
            activity_record_id=record_id,
            reason=blocked.value,
        )

    crash.check(CrashPoint.BEFORE_VENDOR_SUBMIT, phase=LifecyclePhase.ALLOWANCE_RESERVED)
    activities.set_phase(
        record_id,
        LifecyclePhase.SUBMITTING,
        note="submit_attempted",
        submit_attempted=True,
    )
    _stamp_b_phase(
        store,
        job_id,
        area_id=request.area_id,
        phase=SignalPhase.SUBMITTED,
        availability=SignalAvailability.FETCHING,
    )

    try:
        activity_id = vendor.submit(spec)
    except SimulatedCrash:
        activities.mark_unknown(record_id, note="crash_during_submit")
        raise
    except MockVendorError as exc:
        activities.set_phase(
            record_id, LifecyclePhase.FAILED_PRE_SUBMIT, note=str(exc)
        )
        return _result(
            outcome="failed",
            phase=LifecyclePhase.FAILED_PRE_SUBMIT,
            vendor=vendor,
            crash=crash,
            job_id=job_id,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record_id,
            reason=str(exc),
        )

    activities.set_phase(record_id, LifecyclePhase.SUBMITTED, note="submitted")
    try:
        crash.check(
            CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID,
            phase=LifecyclePhase.SUBMITTED,
        )
    except SimulatedCrash:
        activities.mark_unknown(record_id, note="lost_activity_id_after_submit")
        raise

    activities.persist_activity_id(record_id, activity_id)
    crash.check(
        CrashPoint.AFTER_ACTIVITY_ID, phase=LifecyclePhase.ACTIVITY_ID_PERSISTED
    )
    return _poll_normalize_cache_consume(
        store=store,
        ledger=ledger,
        vendor=vendor,
        request=request,
        identity=identity,
        geography=geography,
        activities=activities,
        cache=cache,
        moment=moment,
        crash=crash,
        job_id=job_id,
        reservation_id=reservation_id,
        record_id=record_id,
        activity_id=activity_id,
        max_status_polls=max_status_polls,
    )


def _poll_normalize_cache_consume(
    *,
    store: JobStore,
    ledger: InMemoryDemoAllowanceLedger,
    vendor: MockVendorAdapter,
    request: TwoSignalPublicRequest,
    identity: DemoRequestIdentity,
    geography: SnapshotGeography,
    activities: InMemoryMockActivityStore,
    cache: InMemoryMockResultCache,
    moment: datetime,
    crash: CrashController,
    job_id: str,
    reservation_id: str,
    record_id: str,
    activity_id: str,
    max_status_polls: int,
) -> MockLifecycleResult:
    selected = request.signals.selected_time
    assert selected is not None
    activities.set_phase(record_id, LifecyclePhase.PROCESSING)
    _stamp_b_phase(
        store,
        job_id,
        area_id=request.area_id,
        phase=SignalPhase.VENDOR_PROCESSING,
        availability=SignalAvailability.FETCHING,
    )

    tiles: dict[str, Any] | None = None
    for poll_index in range(max_status_polls):
        if poll_index == 0:
            crash.check(
                CrashPoint.DURING_VENDOR_PROCESSING,
                phase=LifecyclePhase.PROCESSING,
            )
        try:
            status = vendor.get_status(activity_id)
        except MockVendorUnknownActivity as exc:
            activities.set_phase(
                record_id,
                LifecyclePhase.FAILED_POST_SUBMIT,
                note=str(exc),
            )
            _consume_if_reserved(ledger, reservation_id, identity, moment)
            _stamp_b_phase(
                store,
                job_id,
                area_id=request.area_id,
                phase=SignalPhase.FAILED,
                availability=SignalAvailability.FAILED,
                message=str(exc),
            )
            store.update_status(job_id, JobStatus.FAILED, message=str(exc))
            return _result(
                outcome="failed",
                phase=LifecyclePhase.FAILED_POST_SUBMIT,
                vendor=vendor,
                crash=crash,
                job_id=job_id,
                reservation_id=reservation_id,
                reservation_state=_reservation_state(ledger, reservation_id),
                activity_record_id=record_id,
                vendor_activity_id=activity_id,
                restart_action=RestartAction.NO_RESUBMIT_ALREADY_SPENT.value,
                reason="unknown_after_submit",
            )
        except MockVendorError as exc:
            activities.set_phase(
                record_id, LifecyclePhase.FAILED_POST_SUBMIT, note=str(exc)
            )
            _consume_if_reserved(ledger, reservation_id, identity, moment)
            store.update_status(job_id, JobStatus.FAILED, message=str(exc))
            return _result(
                outcome="failed",
                phase=LifecyclePhase.FAILED_POST_SUBMIT,
                vendor=vendor,
                crash=crash,
                job_id=job_id,
                reservation_id=reservation_id,
                reservation_state=_reservation_state(ledger, reservation_id),
                activity_record_id=record_id,
                vendor_activity_id=activity_id,
                reason=str(exc),
            )
        if status.status == "succeeded":
            if not isinstance(status.result, dict):
                raise MockVendorError("mock result missing FeatureCollection")
            tiles = status.result
            break

    if tiles is None:
        activities.set_phase(
            record_id, LifecyclePhase.FAILED_POST_SUBMIT, note="poll_timeout"
        )
        _consume_if_reserved(ledger, reservation_id, identity, moment)
        store.update_status(job_id, JobStatus.FAILED, message="vendor_timeout")
        return _result(
            outcome="timed_out",
            phase=LifecyclePhase.FAILED_POST_SUBMIT,
            vendor=vendor,
            crash=crash,
            job_id=job_id,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record_id,
            vendor_activity_id=activity_id,
            restart_action=RestartAction.NO_RESUBMIT_ALREADY_SPENT.value,
            reason="poll_timeout",
        )

    activities.set_phase(record_id, LifecyclePhase.RESULT_RECEIVED)
    snapshot = process_selected_time_snapshot(
        geography=geography,
        tiles_geojson=tiles,
        target_timestamp=selected.target_timestamp,
        source=ThermalDataSource.REPLAY,
        data_status=DataStatus.REPLAY,
        vendor_request_fingerprint=identity.request_fingerprint,
    )
    activities.set_phase(record_id, LifecyclePhase.NORMALIZED)
    crash.check(
        CrashPoint.AFTER_RESULT_BEFORE_CACHE, phase=LifecyclePhase.NORMALIZED
    )

    cache.put(identity.request_fingerprint, snapshot.model_dump(mode="json"))
    activities.set_phase(record_id, LifecyclePhase.CACHED)
    crash.check(
        CrashPoint.AFTER_CACHE_BEFORE_CONSUME, phase=LifecyclePhase.CACHED
    )

    ledger.consume(
        reservation_id,
        identity=identity,
        planned_units=1,
        now=moment,
    )
    activities.set_phase(record_id, LifecyclePhase.CONSUMED)
    _stamp_b_phase(
        store,
        job_id,
        area_id=request.area_id,
        phase=SignalPhase.READY,
        availability=snapshot.availability,
        snapshot=snapshot,
    )
    terminal = (
        JobStatus.COMPLETE
        if snapshot.availability == SignalAvailability.READY
        else JobStatus.PARTIAL
    )
    store.set_result(job_id, snapshot.model_dump(mode="json"), terminal)
    return _result(
        outcome="ready" if terminal == JobStatus.COMPLETE else "failed",
        phase=LifecyclePhase.CONSUMED,
        vendor=vendor,
        crash=crash,
        job_id=job_id,
        reservation_id=reservation_id,
        reservation_state=ReservationState.CONSUMED.value,
        activity_record_id=record_id,
        vendor_activity_id=activity_id,
        signal_availability=snapshot.availability.value,
        snapshot_valid_zone_count=snapshot.valid_zone_count,
    )


def resume_mock_vendor_lifecycle(
    *,
    store: JobStore,
    ledger: InMemoryDemoAllowanceLedger,
    vendor: MockVendorAdapter,
    request: TwoSignalPublicRequest,
    identity: DemoRequestIdentity,
    geography: SnapshotGeography,
    activities: InMemoryMockActivityStore,
    cache: InMemoryMockResultCache,
    job_id: str | None = None,
    now: datetime | None = None,
    crash_at: CrashPoint = CrashPoint.NONE,
    crash: CrashController | None = None,
    max_status_polls: int = 8,
) -> MockLifecycleResult:
    """Resume after a simulated crash. Never blind-resubmits."""
    refuse_real_vendor(vendor)
    controller = crash or CrashController(crash_at)
    vendor.bind_crash(controller)
    moment = now or _now()

    record = None
    if job_id is not None:
        record = activities.find_by_job(job_id)
    if record is None:
        record = activities.find_by_fingerprint(identity.request_fingerprint)

    reservation_id = record.reservation_id if record else None
    reservation = ledger.get(reservation_id) if reservation_id else None
    cache_ok = cache.contains(identity.request_fingerprint)
    existing = store.find_by_dedupe_key(identity.request_fingerprint)
    job_ok = existing is not None and existing.status in {
        JobStatus.COMPLETE,
        JobStatus.PARTIAL,
    }
    action = activities.decide_restart(
        record,
        reservation_consumed=reservation is not None
        and reservation.state == ReservationState.CONSUMED,
        compatible_cache_present=cache_ok or job_ok,
    )

    if action == RestartAction.REUSE_CACHE:
        if reservation is not None and reservation.state == ReservationState.RESERVED:
            ledger.release(reservation.reservation_id)
        return _result(
            outcome="reused",
            phase=LifecyclePhase.CACHE_HIT,
            vendor=vendor,
            crash=controller,
            job_id=job_id or (existing.job_id if existing else None),
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record.record_id if record else None,
            restart_action=action.value,
            reason="resume_reuse_cache",
            cache_hit=True,
        )
    if action == RestartAction.NO_RESUBMIT_UNCERTAIN:
        if record is not None and record.phase != LifecyclePhase.UNKNOWN_VENDOR_STATE:
            activities.mark_unknown(record.record_id, note="resume_uncertain")
        return _result(
            outcome="uncertain",
            phase=LifecyclePhase.UNKNOWN_VENDOR_STATE,
            vendor=vendor,
            crash=controller,
            job_id=record.job_id if record else job_id,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record.record_id if record else None,
            restart_action=action.value,
            reason="no_automatic_paid_retry",
        )
    if action == RestartAction.NO_RESUBMIT_ALREADY_SPENT:
        return _result(
            outcome="no_resubmit",
            phase=record.phase if record else LifecyclePhase.RECOVERY_REQUIRED,
            vendor=vendor,
            crash=controller,
            job_id=record.job_id if record else job_id,
            reservation_id=reservation_id,
            reservation_state=_reservation_state(ledger, reservation_id),
            activity_record_id=record.record_id if record else None,
            vendor_activity_id=record.vendor_activity_id if record else None,
            restart_action=action.value,
            reason="no_automatic_paid_retry",
        )
    if action == RestartAction.RESUME_POLL:
        assert record is not None and record.vendor_activity_id is not None
        try:
            return _poll_normalize_cache_consume(
                store=store,
                ledger=ledger,
                vendor=vendor,
                request=request,
                identity=identity,
                geography=geography,
                activities=activities,
                cache=cache,
                moment=moment,
                crash=controller,
                job_id=record.job_id,
                reservation_id=record.reservation_id,
                record_id=record.record_id,
                activity_id=record.vendor_activity_id,
                max_status_polls=max_status_polls,
            )
        except SimulatedCrash as exc:
            current = activities.get(record.record_id)
            return _result(
                outcome="crashed",
                phase=current.phase if current else exc.phase,
                vendor=vendor,
                crash=controller,
                job_id=record.job_id,
                reservation_id=record.reservation_id,
                reservation_state=_reservation_state(ledger, record.reservation_id),
                activity_record_id=record.record_id,
                vendor_activity_id=record.vendor_activity_id,
                reason=str(exc),
            )

    return run_mock_vendor_lifecycle(
        store=store,
        ledger=ledger,
        vendor=vendor,
        request=request,
        identity=identity,
        geography=geography,
        activities=activities,
        cache=cache,
        now=moment,
        crash=controller,
        max_status_polls=max_status_polls,
    )


def new_in_memory_job_store() -> InMemoryJobStore:
    return InMemoryJobStore()


def aggregation_spec_for_tests() -> ThermalAggregationSpec:
    from app.domain.enums import TileAssignmentMethod, ZoneAggregationStatistic

    return ThermalAggregationSpec(
        version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
        statistic=ZoneAggregationStatistic.MEAN,
        minimum_coverage_ratio=None,
        zero_tile_behavior="insufficient_evidence",
        boundary_behavior="centroid_within_zone",
        notes=["LIVE-L mock-vendor test geography"],
    )
