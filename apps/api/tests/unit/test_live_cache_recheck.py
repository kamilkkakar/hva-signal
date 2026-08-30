"""LIVE-H cache recheck. No FortyGuard. No real vendor."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.job_store import InMemoryJobStore
from app.domain.demo_allowance import (
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
)
from app.domain.enums import JobStatus
from app.domain.live_cache_recheck import (
    CacheRecheckCode,
    CacheRecheckError,
    CrashAfter,
    LiveCachePhase,
    RecheckPoint,
)
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.live_cache_recheck import (
    FingerprintResultCache,
    LiveCachePipeline,
    SimulatedCrash,
    client_cache_bust_keys,
    consume_after_cache,
    gate_reserve,
    gate_submit,
    normalize_live_result,
    recheck_cache,
    reject_unauthenticated_cache_control,
)

FP = "11" * 32
GEO = "22" * 32
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _identity(fp: str = FP, geo: str = GEO) -> DemoRequestIdentity:
    return DemoRequestIdentity(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint=fp,
        geometry_sha256=geo,
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


def _seed_cache(cache: FingerprintResultCache, identity: DemoRequestIdentity | None = None) -> None:
    ident = identity or _identity()
    normalized = normalize_live_result(ident, {"tcm_c": 41.2, "zones": 25})
    cache.put_from_worker(ident, normalized, now=NOW)


def test_recheck_before_reserve_hit_does_not_reserve() -> None:
    cache = FingerprintResultCache()
    ledger = _ledger()
    _seed_cache(cache)
    decision, reserved = gate_reserve(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        planned_units=1,
        now=NOW,
    )
    assert decision.code is CacheRecheckCode.CACHE_HIT
    assert decision.point is RecheckPoint.BEFORE_RESERVE
    assert decision.reserve_allowed is False
    assert reserved is None
    assert ledger.snapshot().reserved_units == 0
    assert ledger.snapshot().consumed_units == 0


def test_recheck_before_reserve_also_honors_job_store_complete() -> None:
    cache = FingerprintResultCache()
    ledger = _ledger()
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    store.set_result(job.job_id, {"ok": True}, JobStatus.COMPLETE)
    decision, reserved = gate_reserve(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        planned_units=1,
        now=NOW,
        store=store,
        dedupe_key="b-key",
    )
    assert decision.code is CacheRecheckCode.CACHE_HIT
    assert decision.joined_job_id == job.job_id
    assert reserved is None
    assert ledger.snapshot().reserved_units == 0


def test_failed_job_is_not_a_cache_hit() -> None:
    cache = FingerprintResultCache()
    store = InMemoryJobStore()
    job, _ = store.create_or_join({"area": "phoenix-demo"}, dedupe_key="b-key")
    store.update_status(job.job_id, JobStatus.FAILED, message="vendor")
    miss = recheck_cache(
        cache=cache,
        identity=_identity(),
        point=RecheckPoint.BEFORE_RESERVE,
        store=store,
        dedupe_key="b-key",
    )
    assert miss.code is CacheRecheckCode.CACHE_MISS
    assert miss.reserve_allowed is True


def test_cache_miss_may_reserve_then_submit() -> None:
    cache = FingerprintResultCache()
    ledger = _ledger()
    before_reserve, reserved = gate_reserve(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        planned_units=1,
        now=NOW,
    )
    assert before_reserve.code is CacheRecheckCode.CACHE_MISS
    assert reserved is not None
    assert reserved.code is DemoAllowanceDecisionCode.ELIGIBLE
    assert ledger.snapshot().reserved_units == 1
    before_submit = gate_submit(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        reservation_id=reserved.reservation.reservation_id,
    )
    assert before_submit.code is CacheRecheckCode.CACHE_MISS
    assert before_submit.submit_allowed is True
    assert ledger.snapshot().reserved_units == 1
    assert ledger.snapshot().consumed_units == 0


def test_recheck_before_submit_hit_releases_and_does_not_submit() -> None:
    cache = FingerprintResultCache()
    ledger = _ledger()
    _, reserved = gate_reserve(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        planned_units=1,
        now=NOW,
    )
    assert reserved is not None
    _seed_cache(cache)
    decision = gate_submit(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        reservation_id=reserved.reservation.reservation_id,
    )
    assert decision.code is CacheRecheckCode.CACHE_HIT
    assert decision.submit_allowed is False
    assert decision.released_reservation_id == reserved.reservation.reservation_id
    assert ledger.get(reserved.reservation.reservation_id).state is ReservationState.RELEASED
    assert ledger.snapshot().reserved_units == 0
    assert ledger.snapshot().consumed_units == 0


def test_pipeline_cache_hit_never_submits() -> None:
    cache = FingerprintResultCache()
    _seed_cache(cache)
    pipe = LiveCachePipeline(cache=cache, ledger=_ledger(), identity=_identity())
    pipe.reserve(now=NOW)
    assert pipe.job.phase is LiveCachePhase.CACHE_HIT
    decision = pipe.submit_if_allowed()
    assert decision.code is CacheRecheckCode.CACHE_HIT
    assert pipe.job.submit_count == 0


def test_normalize_cache_then_consume() -> None:
    ledger = _ledger()
    pipe = LiveCachePipeline(cache=FingerprintResultCache(), ledger=ledger, identity=_identity())
    pipe.reserve(now=NOW)
    assert pipe.submit_if_allowed().submit_allowed is True
    assert pipe.job.submit_count == 1
    job = pipe.accept_result({"tcm_c": 38.0, "api_key": "should-not-cache"})
    assert job.phase is LiveCachePhase.CONSUMED
    assert job.consumed is True
    assert job.normalized is not None
    assert "api_key" not in job.normalized.payload
    assert ledger.snapshot().consumed_units == 1
    assert ledger.snapshot().reserved_units == 0
    assert pipe.cache.get(_identity()) is not None


def test_crash_after_result_before_cache_recovers_without_resubmit() -> None:
    ledger = _ledger()
    pipe = LiveCachePipeline(cache=FingerprintResultCache(), ledger=ledger, identity=_identity())
    pipe.reserve(now=NOW)
    pipe.submit_if_allowed()
    with pytest.raises(SimulatedCrash) as crash:
        pipe.accept_result({"tcm_c": 40.1}, crash_after=CrashAfter.RESULT)
    assert crash.value.phase is LiveCachePhase.RESULT_RECEIVED
    assert pipe.job.phase is LiveCachePhase.RESULT_RECEIVED
    assert pipe.cache.get(_identity()) is None
    assert ledger.snapshot().consumed_units == 0
    recovered = pipe.recover(now=NOW)
    assert recovered.phase is LiveCachePhase.CONSUMED
    assert recovered.submit_count == 1
    assert pipe.cache.get(_identity()) is not None
    assert ledger.snapshot().consumed_units == 1


def test_crash_after_normalize_before_cache_recovers_without_resubmit() -> None:
    pipe = LiveCachePipeline(cache=FingerprintResultCache(), ledger=_ledger(), identity=_identity())
    pipe.reserve(now=NOW)
    pipe.submit_if_allowed()
    with pytest.raises(SimulatedCrash):
        pipe.accept_result({"tcm_c": 40.1}, crash_after=CrashAfter.NORMALIZE)
    assert pipe.job.phase is LiveCachePhase.NORMALIZED
    assert pipe.cache.get(_identity()) is None
    recovered = pipe.recover(now=NOW)
    assert recovered.phase is LiveCachePhase.CONSUMED
    assert recovered.submit_count == 1


def test_crash_after_cache_before_consume_consumes_on_recovery() -> None:
    ledger = _ledger()
    pipe = LiveCachePipeline(cache=FingerprintResultCache(), ledger=ledger, identity=_identity())
    pipe.reserve(now=NOW)
    pipe.submit_if_allowed()
    with pytest.raises(SimulatedCrash) as crash:
        pipe.accept_result({"tcm_c": 39.4}, crash_after=CrashAfter.CACHE)
    assert crash.value.phase is LiveCachePhase.CACHED
    assert pipe.job.phase is LiveCachePhase.CACHED
    assert pipe.cache.get(_identity()) is not None
    assert ledger.get(pipe.job.reservation_id).state is ReservationState.RESERVED
    recovered = pipe.recover(now=NOW)
    assert recovered.phase is LiveCachePhase.CONSUMED
    assert recovered.submit_count == 1
    assert ledger.snapshot().consumed_units == 1
    again = pipe.recover(now=NOW)
    assert again.phase is LiveCachePhase.CONSUMED
    assert again.submit_count == 1
    assert ledger.snapshot().consumed_units == 1


def test_submitted_without_result_does_not_resubmit_on_recovery() -> None:
    pipe = LiveCachePipeline(cache=FingerprintResultCache(), ledger=_ledger(), identity=_identity())
    pipe.reserve(now=NOW)
    pipe.submit_if_allowed()
    recovered = pipe.recover(now=NOW)
    assert recovered.phase is LiveCachePhase.RECOVERY_REQUIRED
    assert recovered.submit_count == 1
    assert recovered.last_error == "unknown_vendor_state_no_resubmit"


def test_client_cache_bust_is_rejected() -> None:
    keys = client_cache_bust_keys(
        {"force_live": True, "area_id": "phoenix-demo"},
        headers={"X-Cache-Bust": "1", "Cache-Control": "no-cache"},
        query={"skip_cache": "1"},
    )
    assert "force_live" in keys
    assert "cache_bust" in keys
    assert "no_cache" in keys
    assert "skip_cache" in keys
    with pytest.raises(CacheRecheckError) as exc:
        reject_unauthenticated_cache_control({"cache_bust": True})
    assert exc.value.code is CacheRecheckCode.REJECTED_CACHE_BUST


def test_client_cache_write_is_poison_and_rejected() -> None:
    cache = FingerprintResultCache()
    with pytest.raises(CacheRecheckError) as ingest:
        cache.ingest_client_record(_identity(), {"payload": {"tcm_c": 1}, "integrity_sha256": "00"})
    assert ingest.value.code is CacheRecheckCode.REJECTED_POISON
    with pytest.raises(CacheRecheckError) as body:
        reject_unauthenticated_cache_control({"cache_record": {"tcm_c": 99}})
    assert body.value.code is CacheRecheckCode.REJECTED_POISON
    assert cache.get(_identity()) is None


def test_operator_token_on_client_payload_is_rejected() -> None:
    with pytest.raises(CacheRecheckError) as exc:
        reject_unauthenticated_cache_control({"operator_token": "secret"})
    assert exc.value.code is CacheRecheckCode.REJECTED_UNAUTHENTICATED


def test_tampered_integrity_is_not_a_hit() -> None:
    cache = FingerprintResultCache()
    _seed_cache(cache)
    record = cache.get(_identity())
    assert record is not None
    cache._records[FP] = record.model_copy(update={"payload": {"tcm_c": 1.0}})
    assert cache.get(_identity()) is None


def test_overwrite_with_different_payload_is_poison() -> None:
    cache = FingerprintResultCache()
    identity = _identity()
    first = normalize_live_result(identity, {"tcm_c": 41.2})
    cache.put_from_worker(identity, first, now=NOW)
    second = normalize_live_result(identity, {"tcm_c": 12.0})
    with pytest.raises(CacheRecheckError) as exc:
        cache.put_from_worker(identity, second, now=NOW)
    assert exc.value.code is CacheRecheckCode.REJECTED_POISON
    assert cache.get(identity).payload["tcm_c"] == 41.2


def test_same_payload_put_is_idempotent() -> None:
    cache = FingerprintResultCache()
    identity = _identity()
    normalized = normalize_live_result(identity, {"tcm_c": 41.2})
    first = cache.put_from_worker(identity, normalized, now=NOW)
    second = cache.put_from_worker(identity, normalized, now=NOW)
    assert first.integrity_sha256 == second.integrity_sha256


def test_fingerprint_mismatch_cannot_be_cached() -> None:
    cache = FingerprintResultCache()
    normalized = normalize_live_result(_identity(), {"tcm_c": 30.0})
    with pytest.raises(CacheRecheckError) as exc:
        cache.put_from_worker(_identity(fp="33" * 32), normalized, now=NOW)
    assert exc.value.code is CacheRecheckCode.REJECTED_IDENTITY


def test_relative_reference_frame_cannot_be_normalized() -> None:
    with pytest.raises(CacheRecheckError) as exc:
        normalize_live_result(_identity(), {"tcm_c": 30.0, "reference_frame": "relative"})
    assert exc.value.code is CacheRecheckCode.REJECTED_POISON


def test_operator_bust_requires_server_source_and_token() -> None:
    cache = FingerprintResultCache()
    _seed_cache(cache)
    with pytest.raises(CacheRecheckError) as client:
        cache.operator_bust(
            request_fingerprint=FP,
            operator_token="tok",
            configured_token="tok",
            source="client",
        )
    assert client.value.code is CacheRecheckCode.REJECTED_UNAUTHENTICATED
    with pytest.raises(CacheRecheckError) as bad:
        cache.operator_bust(
            request_fingerprint=FP,
            operator_token="wrong",
            configured_token="tok",
            source="server",
        )
    assert bad.value.code is CacheRecheckCode.REJECTED_UNAUTHENTICATED
    assert cache.get(_identity()) is not None
    cache.operator_bust(
        request_fingerprint=FP,
        operator_token="tok",
        configured_token="tok",
        source="server",
    )
    assert cache.get(_identity()) is None


def test_consume_after_cache_is_idempotent() -> None:
    ledger = _ledger()
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=NOW)
    assert reserved.reservation is not None
    first = consume_after_cache(
        ledger=ledger,
        reservation_id=reserved.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        now=NOW,
    )
    second = consume_after_cache(
        ledger=ledger,
        reservation_id=reserved.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        now=NOW,
    )
    assert first is ReservationState.CONSUMED
    assert second is ReservationState.CONSUMED
    assert ledger.snapshot().consumed_units == 1


def test_submit_rejected_when_reservation_fingerprint_differs() -> None:
    cache = FingerprintResultCache()
    ledger = _ledger()
    _, reserved = gate_reserve(
        cache=cache,
        ledger=ledger,
        identity=_identity(),
        planned_units=1,
        now=NOW,
    )
    decision = gate_submit(
        cache=cache,
        ledger=ledger,
        identity=_identity(fp="44" * 32),
        reservation_id=reserved.reservation.reservation_id,
    )
    assert decision.code is CacheRecheckCode.REJECTED_IDENTITY
    assert decision.submit_allowed is False
    assert ledger.snapshot().reserved_units == 1
