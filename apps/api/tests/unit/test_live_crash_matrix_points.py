"""Nine crash points: restart, spend, dedupe, recovery."""

from __future__ import annotations

import pytest

from app.domain.demo_allowance import ReservationState
from app.domain.live_crash_matrix.contract import CRASH_MATRIX_ROWS, CrashMatrixRow
from app.domain.live_crash_matrix.states import CrashPoint, RecoveryAction
from app.services.live_crash_matrix.runner import CrashMatrixRunner, new_runner

FP = "aa" * 32


def _snapshot(runner: CrashMatrixRunner) -> tuple[int, int]:
    snap = runner.ledger.snapshot()
    return snap.reserved_units, snap.consumed_units


def _assert_crash_snapshot(runner: CrashMatrixRunner, row: CrashMatrixRow, job_id: str) -> None:
    record = runner.record(job_id)
    assert record is not None
    reserved, consumed = _snapshot(runner)
    assert reserved == row.reserved_at_crash
    assert consumed == row.consumed_at_crash
    assert runner.vendor.submit_count == row.submit_count_at_crash
    assert (record.vendor_activity_id is not None) is row.activity_id_at_crash
    assert (record.fingerprint in runner.cache) is row.cache_at_crash
    assert (record.result is not None) is row.result_at_crash


@pytest.mark.parametrize("row", CRASH_MATRIX_ROWS, ids=lambda row: row.point.value)
def test_crash_point_restart_spend_dedupe_recovery(row: CrashMatrixRow) -> None:
    runner = new_runner()
    crashed = runner.acquire(FP, crash_at=row.point)
    assert crashed.outcome == "crashed"
    assert crashed.state == row.crashed_state.value
    assert crashed.crash_point == row.point.value
    assert crashed.job_id is not None
    _assert_crash_snapshot(runner, row, crashed.job_id)

    recovered = runner.recover(crashed.job_id)
    assert recovered.outcome == row.recover_outcome
    assert recovered.recovery_action == row.restart_action.value
    if row.recover_outcome == "ready":
        assert runner.vendor.submit_count == 1
        assert recovered.state == "CONSUMED"
        assert runner.ledger.snapshot().consumed_units == 1
        assert FP in runner.cache
    if row.recover_outcome == "uncertain":
        assert runner.vendor.submit_count == 1
        assert recovered.recovery_action == RecoveryAction.NO_AUTOMATIC_RESUBMIT.value
        assert recovered.state == "UNKNOWN_VENDOR_STATE"


@pytest.mark.parametrize("row", CRASH_MATRIX_ROWS, ids=lambda row: row.point.value)
def test_duplicate_after_crash_does_not_add_submit(row: CrashMatrixRow) -> None:
    runner = new_runner()
    crashed = runner.acquire(FP, crash_at=row.point)
    assert crashed.job_id is not None
    submits_after_crash = runner.vendor.submit_count
    duplicate = runner.acquire(FP)
    assert duplicate.outcome == row.duplicate_outcome
    if row.duplicate_outcome == "ready":
        assert runner.vendor.submit_count == 1
        assert duplicate.job_id == crashed.job_id
    if row.duplicate_outcome == "uncertain":
        assert runner.vendor.submit_count == submits_after_crash == 1
        assert duplicate.state == "UNKNOWN_VENDOR_STATE"


@pytest.mark.parametrize(
    "point",
    [
        CrashPoint.DURING_SUBMIT,
        CrashPoint.AFTER_SUBMIT_BEFORE_ACTIVITY_ID,
    ],
)
def test_unknown_rejects_forced_paid_retry(point: CrashPoint) -> None:
    runner = new_runner()
    crashed = runner.acquire(FP, crash_at=point)
    forced = runner.recover(
        crashed.job_id,  # type: ignore[arg-type]
        force_resubmit=True,
        automatic_paid_retry=True,
    )
    assert forced.outcome == "uncertain"
    assert forced.reason == "force_resubmit_rejected"
    assert runner.vendor.submit_count == 1
    assert runner.ledger.snapshot().consumed_units == 0


def test_cache_appearing_after_reserve_releases_and_skips_submit() -> None:
    runner = new_runner()
    crashed = runner.acquire(FP, crash_at=CrashPoint.AFTER_RESERVE)
    assert crashed.reservation_state == ReservationState.RESERVED.value
    runner.cache[FP] = {"ok": True, "planted": True}
    recovered = runner.recover(crashed.job_id)  # type: ignore[arg-type]
    assert recovered.outcome == "reused"
    assert runner.vendor.submit_count == 0
    assert runner.ledger.snapshot().reserved_units == 0
    reservation = runner.ledger.get(crashed.reservation_id)  # type: ignore[arg-type]
    assert reservation is not None
    assert reservation.state == ReservationState.RELEASED


def test_j0_process_death_does_not_auto_resubmit() -> None:
    runner = new_runner()
    crashed = runner.acquire(FP, crash_at=CrashPoint.AFTER_ACTIVITY_ID_SAVE)
    assert runner.vendor.submit_count == 1
    runner.simulate_process_death(keep_vendor=True)
    lost = runner.recover(crashed.job_id)  # type: ignore[arg-type]
    assert lost.outcome == "no_resubmit"
    assert lost.reason == "restart_state_lost"
    assert runner.vendor.submit_count == 1


def test_happy_path_cache_then_consume_then_reuse() -> None:
    runner = new_runner()
    first = runner.acquire(FP)
    assert first.outcome == "ready"
    assert first.state == "CONSUMED"
    assert runner.vendor.submit_count == 1
    assert runner.ledger.snapshot().consumed_units == 1
    second = runner.acquire(FP)
    assert second.outcome == "reused"
    assert runner.vendor.submit_count == 1
    assert runner.ledger.snapshot().consumed_units == 1


def test_after_cache_before_consume_then_second_caller_reuses() -> None:
    runner = new_runner()
    crashed = runner.acquire(FP, crash_at=CrashPoint.AFTER_CACHE_BEFORE_CONSUME)
    recovered = runner.recover(crashed.job_id)  # type: ignore[arg-type]
    assert recovered.outcome == "ready"
    third = runner.acquire(FP)
    assert third.outcome == "reused"
    assert runner.vendor.submit_count == 1
    assert runner.ledger.snapshot().consumed_units == 1
