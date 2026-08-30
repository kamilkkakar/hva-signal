"""Cache and join precede demo allowance. Live preference is not a grant."""

from datetime import datetime, timezone

from app.core.job_store import InMemoryJobStore
from app.domain.demo_allowance import (
    AcquisitionPreference,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
)
from app.domain.enums import DataMode, JobStatus
from app.domain.signals import ThermalSignalKind
from app.services.demo_acquisition import (
    compatible_fallback_allowed,
    historical_prep_not_triggered_by_demo,
    recheck_demo_reservation_before_paid_submission,
    resolve_hosted_demo_path,
)
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger

FP = "11" * 32
GEO = "22" * 32


def _identity() -> DemoRequestIdentity:
    return DemoRequestIdentity(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint=FP,
        geometry_sha256=GEO,
        area_id="phoenix-demo",
    )


def _ledger() -> InMemoryDemoAllowanceLedger:
    return InMemoryDemoAllowanceLedger(
        DemoAllowancePolicy(
            enabled=True,
            max_total_acquisition_units=3,
            max_units_per_request=1,
            allowed_area_ids=frozenset({"phoenix-demo"}),
        )
    )


def _resolve(store, ledger, **overrides):
    payload = {
        "store": store,
        "ledger": ledger,
        "dedupe_key": "b-key",
        "data_mode": DataMode.LIVE,
        "snapshot_capable": True,
        "preference": AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO,
        "identity": _identity(),
        "planned_units": 1,
        "now": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return resolve_hosted_demo_path(**payload)


def test_replay_and_cache_do_not_reserve() -> None:
    ledger = _ledger()
    replay = _resolve(InMemoryJobStore(), ledger, data_mode=DataMode.REPLAY)
    assert replay.code == DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    cached = _resolve(store, ledger)
    assert cached.code == DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE
    assert ledger.snapshot().reserved_units == 0


def test_in_flight_join_does_not_reserve() -> None:
    ledger = _ledger()
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    decision = _resolve(store, ledger)
    assert decision.code == DemoAllowanceDecisionCode.JOIN_IN_FLIGHT
    assert decision.joined_job_id == job.job_id
    assert ledger.snapshot().reserved_units == 0


def test_reuse_only_never_spends() -> None:
    decision = _resolve(
        InMemoryJobStore(),
        _ledger(),
        preference=AcquisitionPreference.REUSE_ONLY,
    )
    assert decision.code == DemoAllowanceDecisionCode.LIVE_DEMO_NOT_REQUESTED


def test_allow_live_with_cache_still_reuses() -> None:
    ledger = _ledger()
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    decision = _resolve(store, ledger)
    assert decision.code == DemoAllowanceDecisionCode.NOT_REQUIRED_REUSE
    assert ledger.snapshot().reserved_units == 0


def test_incompatible_fallback_is_refused() -> None:
    assert compatible_fallback_allowed(same_fingerprint=False, same_geometry=True) is False
    assert compatible_fallback_allowed(same_fingerprint=True, same_geometry=False) is False


def test_worker_recheck_releases_if_cache_appears() -> None:
    ledger = _ledger()
    store = InMemoryJobStore()
    reserved = _resolve(store, ledger)
    assert reserved.code == DemoAllowanceDecisionCode.ELIGIBLE
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    gate = recheck_demo_reservation_before_paid_submission(
        ledger=ledger,
        reservation_id=reserved.decision.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        store=store,
        dedupe_key="b-key",
        now=datetime.now(timezone.utc),
    )
    assert gate.allowed is False
    assert gate.reason == "compatible_result_appeared"
    assert ledger.snapshot().reserved_units == 0


def test_historical_prep_stays_independent() -> None:
    assert historical_prep_not_triggered_by_demo() is True


def test_failed_terminal_is_not_reusable_cache() -> None:
    ledger = _ledger()
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    store.update_status(job.job_id, JobStatus.FAILED, message="vendor")
    decision = _resolve(store, ledger)
    assert decision.code == DemoAllowanceDecisionCode.ELIGIBLE
