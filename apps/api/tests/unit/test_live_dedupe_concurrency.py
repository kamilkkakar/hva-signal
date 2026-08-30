"""LIVE-G concurrency: 100 identical joins, distinct isolation, cache-miss race."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

from app.core.job_store import InMemoryJobStore
from app.domain.demo_allowance import (
    DemoAllowanceDecision,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    DemoReservation,
    ReservationState,
)
from app.domain.live_dedupe import LiveAcquireRequest, LiveJoinOutcome, LiveJoinPhase
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.live_dedupe import (
    CountingAllowance,
    CountingMockVendor,
    LiveDedupeCoordinator,
    live_submit_fingerprint,
)


def _req(**overrides: object) -> LiveAcquireRequest:
    payload = {
        "area_id": "phoenix-demo",
        "geometry_sha256": "aa" * 32,
        "zone_geometry_version": "GEO_V1",
        "target_timestamp": datetime(2024, 7, 15, 15, 0, 0),
        "timezone": "America/Phoenix",
        "aggregation_spec_version": "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    }
    payload.update(overrides)
    return LiveAcquireRequest(**payload)  # type: ignore[arg-type]


def _coordinator(
    *,
    max_units: int = 50,
    vendor: CountingMockVendor | None = None,
    fail_submit: bool = False,
) -> LiveDedupeCoordinator:
    ledger = InMemoryDemoAllowanceLedger(
        DemoAllowancePolicy(
            enabled=True,
            max_total_acquisition_units=max_units,
            max_units_per_request=1,
            allowed_area_ids=frozenset({"phoenix-demo", "other-area"}),
        )
    )
    return LiveDedupeCoordinator(
        store=InMemoryJobStore(),
        allowance=CountingAllowance(ledger),
        vendor=vendor or CountingMockVendor(fail_submit=fail_submit),
    )


def test_one_hundred_identical_requests_take_one_submit_path() -> None:
    coord = _coordinator()
    request = _req()
    start = Barrier(100)
    claimed = Barrier(100)

    def after_claim(_ticket) -> None:
        claimed.wait()

    def worker(_: int):
        start.wait()
        return coord.execute(request, on_after_claim=after_claim)

    with ThreadPoolExecutor(max_workers=100) as pool:
        results = list(pool.map(worker, range(100)))

    vendor = coord.vendor
    allowance = coord.allowance
    assert isinstance(vendor, CountingMockVendor)
    assert isinstance(allowance, CountingAllowance)
    assert vendor.submit_count == 1
    assert allowance.reserve_calls == 1
    assert allowance.consume_calls == 1
    leaders = [r for r in results if r.outcome == LiveJoinOutcome.LEADER]
    joiners = [r for r in results if r.outcome == LiveJoinOutcome.JOINED]
    assert len(leaders) == 1
    assert len(joiners) == 99
    job_ids = {r.job_id for r in results}
    assert len(job_ids) == 1
    fingerprints = {r.fingerprint for r in results}
    assert fingerprints == {live_submit_fingerprint(request)}
    shared = leaders[0].shared_result
    assert shared is not None
    for result in results:
        assert result.shared_result == shared
        assert result.activity_id == leaders[0].activity_id
    assert sum(1 for r in results if r.submitted) == 1
    assert sum(1 for r in results if r.reserved) == 1
    for joiner in joiners:
        assert joiner.submitted is False
        assert joiner.reserved is False
        assert joiner.outcome == LiveJoinOutcome.JOINED


def test_concurrent_distinct_requests_are_independent() -> None:
    coord = _coordinator()
    requests = [
        _req(target_timestamp=datetime(2024, 7, 15, hour, 0, 0))
        for hour in range(8, 20)
    ]
    start = Barrier(len(requests))

    def worker(request: LiveAcquireRequest):
        start.wait()
        return request, coord.execute(request)

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        pairs = list(pool.map(worker, requests))

    vendor = coord.vendor
    allowance = coord.allowance
    assert isinstance(vendor, CountingMockVendor)
    assert isinstance(allowance, CountingAllowance)
    assert vendor.submit_count == len(requests)
    assert allowance.reserve_calls == len(requests)
    results = [item[1] for item in pairs]
    assert all(r.outcome == LiveJoinOutcome.LEADER for r in results)
    assert len({r.job_id for r in results}) == len(requests)
    assert len({r.fingerprint for r in results}) == len(requests)
    assert len({r.activity_id for r in results}) == len(requests)
    by_fp = {r.fingerprint: r.shared_result for r in results}
    for request, result in pairs:
        expected = live_submit_fingerprint(request)
        assert result.fingerprint == expected
        assert result.shared_result is not None
        assert result.shared_result["fingerprint"] == expected
        assert result.shared_result["target_timestamp"] == request.target_timestamp.isoformat()
        for other_fp, other_result in by_fp.items():
            if other_fp == expected:
                continue
            assert other_result is not None
            assert other_result["fingerprint"] != result.shared_result["fingerprint"]


def test_cache_miss_race_only_one_reserve_and_submit() -> None:
    coord = _coordinator()
    request = _req()
    seen_misses: list[str] = []
    miss_barrier = Barrier(2)
    claim_barrier = Barrier(2)

    def on_miss(fingerprint: str) -> None:
        seen_misses.append(fingerprint)
        miss_barrier.wait()

    def after_claim(_ticket) -> None:
        claim_barrier.wait()

    def worker(_: int):
        return coord.execute(
            request, on_cache_miss=on_miss, on_after_claim=after_claim
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))

    vendor = coord.vendor
    allowance = coord.allowance
    assert isinstance(vendor, CountingMockVendor)
    assert isinstance(allowance, CountingAllowance)
    assert len(seen_misses) == 2
    assert vendor.submit_count == 1
    assert allowance.reserve_calls == 1
    outcomes = {r.outcome for r in results}
    assert outcomes == {LiveJoinOutcome.LEADER, LiveJoinOutcome.JOINED}


def test_dedupe_happens_before_allowance_on_cache_hit() -> None:
    coord = _coordinator()
    request = _req()
    first = coord.execute(request)
    assert first.outcome == LiveJoinOutcome.LEADER
    second = coord.execute(request)
    allowance = coord.allowance
    vendor = coord.vendor
    assert isinstance(allowance, CountingAllowance)
    assert isinstance(vendor, CountingMockVendor)
    assert second.outcome == LiveJoinOutcome.CACHE_HIT
    assert second.shared_result == first.shared_result
    assert allowance.reserve_calls == 1
    assert vendor.submit_count == 1
    assert second.reserved is False
    assert second.submitted is False


def test_unknown_vendor_state_does_not_resubmit() -> None:
    coord = _coordinator(fail_submit=True)
    request = _req()
    first = coord.execute(request)
    assert first.outcome == LiveJoinOutcome.RECOVERY_REQUIRED
    assert first.phase == LiveJoinPhase.UNKNOWN_VENDOR_STATE
    second = coord.execute(request)
    vendor = coord.vendor
    allowance = coord.allowance
    assert isinstance(vendor, CountingMockVendor)
    assert isinstance(allowance, CountingAllowance)
    assert vendor.submit_count == 1
    assert allowance.reserve_calls == 1
    assert second.outcome == LiveJoinOutcome.RECOVERY_REQUIRED
    assert second.submitted is False
    assert second.reserved is False


class _ScriptedAllowance:
    def __init__(self, codes: list[DemoAllowanceDecisionCode]) -> None:
        self._codes = list(codes)
        self.reserve_calls = 0
        self.consume_calls = 0
        self.release_calls = 0

    def try_reserve(
        self, identity: DemoRequestIdentity, *, planned_units: int
    ) -> DemoAllowanceDecision:
        self.reserve_calls += 1
        code = self._codes.pop(0)
        if code != DemoAllowanceDecisionCode.ELIGIBLE:
            return DemoAllowanceDecision(code=code, spend_authorized=False)
        reservation = DemoReservation(
            reservation_id=f"res_script_{self.reserve_calls}",
            state=ReservationState.RESERVED,
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            request_fingerprint=identity.request_fingerprint,
            geometry_sha256=identity.geometry_sha256,
            area_id=identity.area_id,
            planned_units=planned_units,
            created_at=datetime(2026, 8, 30, 12, 0, 0),
        )
        return DemoAllowanceDecision(
            code=code, reservation=reservation, spend_authorized=True
        )

    def consume(
        self,
        reservation_id: str,
        identity: DemoRequestIdentity,
        *,
        planned_units: int,
    ) -> None:
        self.consume_calls += 1

    def release(self, reservation_id: str) -> None:
        self.release_calls += 1


def test_failed_pre_submit_can_reopen_without_prior_submit() -> None:
    allowance = _ScriptedAllowance(
        [
            DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED,
            DemoAllowanceDecisionCode.ELIGIBLE,
        ]
    )
    vendor = CountingMockVendor()
    coord = LiveDedupeCoordinator(
        store=InMemoryJobStore(),
        allowance=allowance,
        vendor=vendor,
    )
    request = _req()
    first = coord.execute(request)
    assert first.phase == LiveJoinPhase.FAILED_PRE_SUBMIT
    assert vendor.submit_count == 0
    second = coord.execute(request, allow_reopen=True)
    assert second.outcome == LiveJoinOutcome.LEADER
    assert second.phase == LiveJoinPhase.SUCCEEDED
    assert vendor.submit_count == 1
    assert allowance.reserve_calls == 2
    assert allowance.consume_calls == 1


def test_joiners_share_pre_submit_failure_and_do_not_spend() -> None:
    ledger = InMemoryDemoAllowanceLedger(
        DemoAllowancePolicy(
            enabled=True,
            max_total_acquisition_units=0,
            max_units_per_request=1,
            allowed_area_ids=frozenset({"phoenix-demo"}),
        )
    )
    coord = LiveDedupeCoordinator(
        store=InMemoryJobStore(),
        allowance=CountingAllowance(ledger),
        vendor=CountingMockVendor(),
    )
    request = _req()
    start = Barrier(8)

    def worker(_: int):
        start.wait()
        return coord.execute(request)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(8)))

    vendor = coord.vendor
    allowance = coord.allowance
    assert isinstance(vendor, CountingMockVendor)
    assert isinstance(allowance, CountingAllowance)
    assert vendor.submit_count == 0
    assert allowance.reserve_calls == 1
    assert allowance.consume_calls == 0
    assert {r.job_id for r in results} == {results[0].job_id}
    leaders = [r for r in results if r.outcome == LiveJoinOutcome.LEADER]
    joiners = [r for r in results if r.outcome == LiveJoinOutcome.JOINED]
    assert len(leaders) == 1
    assert len(joiners) == 7
    assert all(r.phase == LiveJoinPhase.FAILED_PRE_SUBMIT for r in results)
    assert all(r.submitted is False and r.reserved is False for r in results)
