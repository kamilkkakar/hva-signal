"""Cache and join happen before any spend approval."""

from datetime import datetime, timedelta, timezone

from app.core.job_store import InMemoryJobStore
from app.domain.enums import DataMode, JobStatus
from app.domain.signals import ThermalSignalKind
from app.services.acquisition_path import (
    AcquisitionDisposition,
    historical_does_not_start_preparation,
    resolve_selected_time_path,
)
from app.services.spend_gate import approve_grant, deny_grant, expire_grant, waiting_grant

FP = "11" * 32
GEO = "22" * 32


def _path(store, **overrides):
    payload = {
        "store": store,
        "dedupe_key": "b-key",
        "data_mode": DataMode.LIVE,
        "snapshot_capable": True,
        "grant": None,
        "planned_units": 1,
        "request_fingerprint": FP,
        "geometry_sha256": GEO,
        "now": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return resolve_selected_time_path(**payload)


def test_replay_never_requires_approval() -> None:
    decision = _path(InMemoryJobStore(), data_mode=DataMode.REPLAY)
    assert decision.disposition == AcquisitionDisposition.REPLAY_FREE
    assert decision.approval_required is False


def test_cached_terminal_reuses_without_approval() -> None:
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "x"}, dedupe_key="b-key")
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    decision = _path(store)
    assert decision.disposition == AcquisitionDisposition.CACHED_REUSE
    assert decision.joined_job_id == job.job_id
    assert decision.approval_required is False


def test_in_flight_joins_without_approval() -> None:
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "x"}, dedupe_key="b-key")
    decision = _path(store)
    assert decision.disposition == AcquisitionDisposition.JOIN_IN_FLIGHT
    assert decision.joined_job_id == job.job_id


def test_failed_terminal_does_not_reuse_as_cache() -> None:
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "x"}, dedupe_key="b-key")
    store.update_status(job.job_id, JobStatus.FAILED, message="vendor")
    decision = _path(store)
    assert decision.disposition == AcquisitionDisposition.WAITING_FOR_APPROVAL
    assert decision.approval_required is True


def test_live_cache_miss_waits_for_approval() -> None:
    decision = _path(InMemoryJobStore())
    assert decision.disposition == AcquisitionDisposition.WAITING_FOR_APPROVAL


def test_approved_live_is_execution_eligible() -> None:
    grant = approve_grant(
        waiting_grant(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            request_fingerprint=FP,
            geometry_sha256=GEO,
            requested_units=1,
            planned_acquisition_units=1,
        ),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=None,
    )
    decision = _path(InMemoryJobStore(), grant=grant)
    assert decision.disposition == AcquisitionDisposition.EXECUTION_ELIGIBLE


def test_denied_is_not_execution() -> None:
    grant = deny_grant(
        waiting_grant(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            request_fingerprint=FP,
            geometry_sha256=GEO,
            requested_units=1,
            planned_acquisition_units=1,
        ),
        reason="no",
    )
    decision = _path(InMemoryJobStore(), grant=grant)
    assert decision.disposition == AcquisitionDisposition.SPEND_DENIED


def test_incapable_geography_does_not_ask_for_spend() -> None:
    decision = _path(InMemoryJobStore(), snapshot_capable=False)
    assert decision.disposition == AcquisitionDisposition.NOT_SNAPSHOT_CAPABLE
    assert decision.approval_required is False


def test_unprepared_reference_does_not_start_prep() -> None:
    assert (
        historical_does_not_start_preparation(reference_ready=False)
        == AcquisitionDisposition.REFERENCE_NOT_PREPARED
    )


def test_expired_grant_is_not_execution() -> None:
    grant = expire_grant(
        approve_grant(
            waiting_grant(
                signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
                request_fingerprint=FP,
                geometry_sha256=GEO,
                requested_units=1,
                planned_acquisition_units=1,
            ),
            authorized_max_units=1,
            approval_ref="op-1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    decision = _path(InMemoryJobStore(), grant=grant)
    assert decision.disposition == AcquisitionDisposition.SPEND_EXPIRED


def test_partition_overrun_is_insufficient_not_partial_spend() -> None:
    grant = approve_grant(
        waiting_grant(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            request_fingerprint=FP,
            geometry_sha256=GEO,
            requested_units=1,
            planned_acquisition_units=1,
        ),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=None,
    )
    decision = _path(InMemoryJobStore(), grant=grant, planned_units=4)
    assert decision.disposition == AcquisitionDisposition.AUTHORIZATION_INSUFFICIENT


def test_different_fingerprint_cannot_reuse_approval() -> None:
    grant = approve_grant(
        waiting_grant(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            request_fingerprint=FP,
            geometry_sha256=GEO,
            requested_units=1,
            planned_acquisition_units=1,
        ),
        authorized_max_units=1,
        approval_ref="op-1",
        expires_at=None,
    )
    decision = _path(InMemoryJobStore(), grant=grant, request_fingerprint="33" * 32)
    assert decision.disposition == AcquisitionDisposition.WAITING_FOR_APPROVAL
    assert decision.spend_state.value == "WAITING_FOR_APPROVAL"
