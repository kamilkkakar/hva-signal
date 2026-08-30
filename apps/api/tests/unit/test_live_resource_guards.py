"""LIVE-K: server-side rate / resource guards. No FortyGuard. No vendor I/O."""

from __future__ import annotations

import ast
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.core.job_store import InMemoryJobStore
from app.domain.demo_allowance import (
    AcquisitionPreference,
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
)
from app.domain.enums import DataMode
from app.domain.signals import ThermalSignalKind
from app.services.demo_acquisition import resolve_hosted_demo_path
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.live_resource_guards import (
    CEILING_MAX_CONCURRENT_SUBMITS,
    CEILING_MAX_IN_FLIGHT_JOBS,
    CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY,
    CEILING_MAX_RECOVERY_POLLS_PER_WINDOW,
    CEILING_MAX_RESERVATIONS,
    CEILING_QUEUE_DEPTH,
    CEILING_RESERVE_PER_WINDOW,
    CEILING_SUBMIT_PER_WINDOW,
    REASON_BACKPRESSURE,
    REASON_CLIENT_CAP_OVERRIDE,
    REASON_CLOSED,
    REASON_IN_FLIGHT_CAP,
    REASON_QUEUED,
    REASON_RATE_LIMITED,
    REASON_RECOVERY_POLL_CAP,
    REASON_SUBMIT_CAP,
    ACTION_SUBMIT,
    LiveResourceGuards,
    LiveResourceLimits,
    clamp_operator_limits,
    client_limit_override_keys,
    hosted_live_stays_off_here,
    limits_from_operator_env,
    limits_from_untrusted,
    refuse_client_limit_override,
    reset_live_resource_guards,
)

_OWNED = (
    Path("app/services/live_resource_guards.py"),
    Path("app/services/demo_acquisition.py"),
    Path("app/services/demo_allowance_ledger.py"),
)

FP = "11" * 32
GEO = "22" * 32


def _identity(fp: str = FP) -> DemoRequestIdentity:
    return DemoRequestIdentity(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint=fp,
        geometry_sha256=GEO,
        area_id="phoenix-demo",
    )


def _ledger() -> InMemoryDemoAllowanceLedger:
    return InMemoryDemoAllowanceLedger(
        DemoAllowancePolicy(
            enabled=True,
            max_total_acquisition_units=8,
            max_units_per_request=1,
            allowed_area_ids=frozenset({"phoenix-demo"}),
        )
    )


def _guards(**overrides: int) -> LiveResourceGuards:
    base = LiveResourceLimits().as_public_note()
    base.update(overrides)
    return LiveResourceGuards(LiveResourceLimits(**base))


def test_ceilings_are_demo_tight() -> None:
    assert CEILING_MAX_IN_FLIGHT_JOBS == 2
    assert CEILING_MAX_RESERVATIONS == 2
    assert CEILING_MAX_CONCURRENT_SUBMITS == 1
    assert CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY == 16
    assert CEILING_MAX_RECOVERY_POLLS_PER_WINDOW == 24
    assert CEILING_RESERVE_PER_WINDOW == 4
    assert CEILING_SUBMIT_PER_WINDOW == 2
    assert CEILING_QUEUE_DEPTH == 4


def test_operator_cannot_raise_above_ceiling() -> None:
    raised = clamp_operator_limits(
        {
            "max_in_flight_jobs": 99,
            "max_reservations": 99,
            "max_concurrent_submits": 16,
            "max_recovery_polls_per_activity": 999,
            "max_recovery_polls_per_window": 999,
            "reserve_per_window": 999,
            "submit_per_window": 999,
            "queue_depth": 64,
        }
    )
    assert raised.max_in_flight_jobs == CEILING_MAX_IN_FLIGHT_JOBS
    assert raised.max_reservations == CEILING_MAX_RESERVATIONS
    assert raised.max_concurrent_submits == CEILING_MAX_CONCURRENT_SUBMITS
    assert raised.max_recovery_polls_per_activity == CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY
    assert raised.max_recovery_polls_per_window == CEILING_MAX_RECOVERY_POLLS_PER_WINDOW
    assert raised.reserve_per_window == CEILING_RESERVE_PER_WINDOW
    assert raised.submit_per_window == CEILING_SUBMIT_PER_WINDOW
    assert raised.queue_depth == CEILING_QUEUE_DEPTH


def test_operator_env_can_only_lower() -> None:
    lowered = limits_from_operator_env(
        {
            "HVA_LIVE_MAX_IN_FLIGHT_JOBS": "1",
            "HVA_LIVE_MAX_RESERVATIONS": "1",
            "HVA_LIVE_MAX_CONCURRENT_SUBMITS": "0",
            "HVA_LIVE_QUEUE_DEPTH": "1",
        }
    )
    assert lowered.max_in_flight_jobs == 1
    assert lowered.max_reservations == 1
    assert lowered.max_concurrent_submits == 0
    assert lowered.queue_depth == 1
    assert lowered.max_recovery_polls_per_activity == CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY


def test_client_cannot_raise_caps_via_body_or_headers() -> None:
    payload = {
        "area_id": "phoenix-demo",
        "max_in_flight": 99,
        "max_reservations": 50,
        "queue_depth": 1000,
        "nested": {"rate_limit": 10_000, "bypass_resource_guard": True},
    }
    headers = {
        "X-Max-In-Flight": "99",
        "x-concurrency-cap": "16",
        "x-queue-depth": "64",
    }
    limits, hits = limits_from_untrusted(payload, headers)
    assert limits.max_in_flight_jobs == CEILING_MAX_IN_FLIGHT_JOBS
    assert "max_in_flight" in hits
    assert "max_reservations" in hits
    assert "rate_limit" in hits
    assert "bypass_resource_guard" in hits
    assert any(key.lower() == "x-max-in-flight" for key in hits)
    assert client_limit_override_keys(payload)
    refused = refuse_client_limit_override(payload, headers)
    assert refused == hits


def test_admit_rejects_client_cap_override_without_consuming_slot() -> None:
    guards = _guards()
    denied = guards.admit_reserve(payload={"max_reservations": 99})
    assert denied.proceed is False
    assert denied.reason_code == REASON_CLIENT_CAP_OVERRIDE
    assert guards.reservation_count == 0
    ok = guards.admit_reserve()
    assert ok.proceed is True


def test_join_existing_does_not_consume_reserve_slot() -> None:
    guards = _guards(max_reservations=1)
    first = guards.admit_reserve()
    assert first.proceed is True
    joined = guards.admit_reserve(join_existing=True)
    assert joined.proceed is True
    assert guards.reservation_count == 1
    extra = guards.admit_reserve()
    assert extra.proceed is False
    assert extra.queued is True
    assert extra.reason_code == REASON_QUEUED


def test_reserve_stampede_queues_then_backpressures() -> None:
    guards = _guards()
    outcomes = [guards.admit_reserve() for _ in range(10)]
    proceeded = [item for item in outcomes if item.proceed]
    queued = [item for item in outcomes if item.queued]
    rejected = [
        item for item in outcomes if not item.proceed and not item.queued
    ]
    assert len(proceeded) == CEILING_MAX_RESERVATIONS
    assert len(queued) == CEILING_QUEUE_DEPTH
    assert len(rejected) == 4
    assert {item.reason_code for item in rejected} == {REASON_BACKPRESSURE}
    assert guards.reservation_count == 2
    assert guards.queue_count == 4


def test_submit_stampede_never_reaches_mock() -> None:
    guards = _guards()
    calls = {"n": 0}

    def _mock_vendor() -> str:
        calls["n"] += 1
        return "activity-fake"

    results = [
        guards.call_if_admitted(ACTION_SUBMIT, _mock_vendor) for _ in range(20)
    ]
    proceeded = [admission for admission, _ in results if admission.proceed]
    queued = [admission for admission, _ in results if admission.queued]
    blocked = [
        admission
        for admission, _ in results
        if not admission.proceed and not admission.queued
    ]
    # Sequential RPC completion frees the concurrent slot; in-flight still caps at 2.
    assert calls["n"] == CEILING_MAX_IN_FLIGHT_JOBS
    assert len(proceeded) == CEILING_MAX_IN_FLIGHT_JOBS
    assert len(queued) == CEILING_QUEUE_DEPTH
    assert len(blocked) == 14
    assert {item.reason_code for item in blocked} == {REASON_BACKPRESSURE}


def test_parallel_submit_stampede_one_vendor_call() -> None:
    guards = _guards()
    ready = threading.Barrier(16)
    calls = {"n": 0}
    admitted = {"n": 0}
    hold = threading.Event()
    tally = threading.Lock()

    def _worker() -> tuple[object, str | None]:
        ready.wait()
        admission = guards.admit_submit()
        with tally:
            admitted["n"] += 1
        if not admission.proceed:
            return admission, None
        calls["n"] += 1
        hold.wait(timeout=1.0)
        guards.finish_submit_rpc(admission.token or "")
        return admission, "activity-fake"

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(_worker) for _ in range(16)]
        deadline = time.monotonic() + 1.0
        while admitted["n"] < 16 and time.monotonic() < deadline:
            time.sleep(0.01)
        hold.set()
        results = [future.result() for future in futures]
    proceeded = [admission for admission, _ in results if admission.proceed]
    queued = [admission for admission, _ in results if admission.queued]
    blocked = [
        admission
        for admission, _ in results
        if not admission.proceed and not admission.queued
    ]
    assert calls["n"] == 1
    assert len(proceeded) == 1
    assert len(queued) == CEILING_QUEUE_DEPTH
    assert len(blocked) == 11


def test_submit_rate_limit_after_slots_free() -> None:
    clock = {"t": 0.0}

    def now() -> float:
        return clock["t"]

    guards = LiveResourceGuards(now=now)
    first = guards.admit_submit()
    assert first.proceed is True
    guards.complete_job(first.token or "")
    second = guards.admit_submit()
    assert second.proceed is True
    guards.complete_job(second.token or "")
    third = guards.admit_submit()
    assert third.proceed is False
    assert third.reason_code == REASON_RATE_LIMITED
    assert third.retry_after_seconds is not None
    clock["t"] = 61.0
    later = guards.admit_submit()
    assert later.proceed is True


def test_in_flight_cap_blocks_second_submit_until_complete() -> None:
    guards = _guards(max_in_flight_jobs=1, max_concurrent_submits=1, queue_depth=0)
    first = guards.admit_submit()
    assert first.proceed is True
    guards.finish_submit_rpc(first.token or "")
    second = guards.admit_submit()
    assert second.proceed is False
    assert second.reason_code == REASON_IN_FLIGHT_CAP
    guards.complete_job(first.token or "")
    third = guards.admit_submit()
    assert third.proceed is True


def test_concurrent_submit_cap_is_one() -> None:
    guards = _guards(queue_depth=0)
    first = guards.admit_submit()
    second = guards.admit_submit()
    assert first.proceed is True
    assert second.proceed is False
    assert second.reason_code == REASON_SUBMIT_CAP


def test_promote_after_release_does_not_call_vendor_itself() -> None:
    guards = _guards()
    held = [guards.admit_reserve() for _ in range(2)]
    overflow = [guards.admit_reserve() for _ in range(4)]
    assert all(item.proceed for item in held)
    assert all(item.queued for item in overflow)
    assert guards.promote() is None
    guards.release_reserve(held[0].token or "")
    promoted = guards.promote()
    assert promoted is not None
    assert promoted.proceed is True
    assert guards.reservation_count == 2


def test_recovery_polls_capped_per_activity() -> None:
    guards = _guards()
    allowed = [guards.admit_recovery_poll("act-1") for _ in range(16)]
    assert all(item.proceed for item in allowed)
    denied = guards.admit_recovery_poll("act-1")
    assert denied.proceed is False
    assert denied.reason_code == REASON_RECOVERY_POLL_CAP
    other = guards.admit_recovery_poll("act-2")
    assert other.proceed is True


def test_recovery_polls_capped_per_window() -> None:
    guards = _guards()
    for index in range(24):
        admission = guards.admit_recovery_poll(f"act-{index}")
        assert admission.proceed is True
    extra = guards.admit_recovery_poll("act-fresh")
    assert extra.proceed is False
    assert extra.reason_code == REASON_RECOVERY_POLL_CAP


def test_zero_caps_fail_closed() -> None:
    guards = LiveResourceGuards(
        LiveResourceLimits(
            max_reservations=0,
            max_concurrent_submits=0,
            max_in_flight_jobs=0,
            max_recovery_polls_per_activity=0,
        )
    )
    assert guards.admit_reserve().reason_code == REASON_CLOSED
    assert guards.admit_submit().reason_code == REASON_CLOSED
    assert guards.admit_recovery_poll("act").reason_code == REASON_CLOSED


def test_resolve_uses_guards_and_skips_join() -> None:
    ledger = _ledger()
    store = InMemoryJobStore()
    guards = _guards(max_reservations=1, queue_depth=0)
    first = resolve_hosted_demo_path(
        store=store,
        ledger=ledger,
        dedupe_key="b-1",
        data_mode=DataMode.LIVE,
        snapshot_capable=True,
        preference=AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO,
        identity=_identity(),
        planned_units=1,
        now=datetime.now(timezone.utc),
        resource_guards=guards,
    )
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    joined = resolve_hosted_demo_path(
        store=InMemoryJobStore(),
        ledger=ledger,
        dedupe_key="b-1-dup",
        data_mode=DataMode.LIVE,
        snapshot_capable=True,
        preference=AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO,
        identity=_identity(),
        planned_units=1,
        now=datetime.now(timezone.utc),
        resource_guards=guards,
    )
    assert joined.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION
    distinct = resolve_hosted_demo_path(
        store=InMemoryJobStore(),
        ledger=ledger,
        dedupe_key="b-2",
        data_mode=DataMode.LIVE,
        snapshot_capable=True,
        preference=AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO,
        identity=_identity("33" * 32),
        planned_units=1,
        now=datetime.now(timezone.utc),
        resource_guards=guards,
    )
    assert distinct.code == DemoAllowanceDecisionCode.LIVE_ACQUISITION_UNAVAILABLE
    assert ledger.snapshot().reserved_units == 1


def test_resolve_without_guards_keeps_legacy_path() -> None:
    ledger = _ledger()
    decision = resolve_hosted_demo_path(
        store=InMemoryJobStore(),
        ledger=ledger,
        dedupe_key="legacy",
        data_mode=DataMode.LIVE,
        snapshot_capable=True,
        preference=AcquisitionPreference.ALLOW_HOSTED_LIVE_DEMO,
        identity=_identity(),
        planned_units=1,
        now=datetime.now(timezone.utc),
    )
    assert decision.code == DemoAllowanceDecisionCode.ELIGIBLE


def test_ledger_join_peek() -> None:
    ledger = _ledger()
    assert ledger.has_active_reservation(FP) is False
    ledger.try_reserve(_identity(), planned_units=1, now=datetime.now(timezone.utc))
    assert ledger.has_active_reservation(FP) is True


def test_hosted_live_stays_off_and_no_fortyguard_import() -> None:
    assert hosted_live_stays_off_here() is True
    reset_live_resource_guards()
    root = Path(__file__).resolve().parents[2]
    for rel in _OWNED:
        source = (root / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "fortyguard" not in alias.name.lower()
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "fortyguard" not in node.module.lower()
        assert "hosted_live_real_vendor_enabled=True" not in source
