"""Suite-wide invariants: default-off hosted live, no FortyGuard, nine points."""

from __future__ import annotations

from app.core.config import Settings
from app.domain.demo_allowance import disabled_demo_policy
from app.domain.live_crash_matrix.contract import CRASH_MATRIX_ROWS
from app.domain.live_crash_matrix.states import CRASH_POINTS, DURABLE_WORKER_STATES
from app.services.live_crash_matrix.runner import new_runner


def test_hosted_live_and_demo_allowance_default_off() -> None:
    assert Settings.model_fields["demo_allowance_enabled"].default is False
    assert disabled_demo_policy().enabled is False


def test_matrix_has_exactly_the_nine_required_points() -> None:
    assert len(CRASH_MATRIX_ROWS) == 9
    assert tuple(row.point for row in CRASH_MATRIX_ROWS) == CRASH_POINTS
    assert [row.seq for row in CRASH_MATRIX_ROWS] == list(range(1, 10))


def test_all_seventeen_durable_states_are_named() -> None:
    assert len(DURABLE_WORKER_STATES) == 17
    assert "UNKNOWN_VENDOR_STATE" in {state.value for state in DURABLE_WORKER_STATES}
    assert "RECOVERY_REQUIRED" in {state.value for state in DURABLE_WORKER_STATES}


def test_distinct_fingerprints_do_not_share_submit() -> None:
    runner = new_runner()
    first = runner.acquire("aa" * 32)
    second = runner.acquire("cc" * 32)
    assert first.outcome == "ready"
    assert second.outcome == "ready"
    assert first.job_id != second.job_id
    assert runner.vendor.submit_count == 2
    assert runner.ledger.snapshot().consumed_units == 2


def test_unknown_row_production_flag_is_not_implemented() -> None:
    unknown_rows = [
        row
        for row in CRASH_MATRIX_ROWS
        if row.point.value
        in {"during_submit", "after_submit_before_activity_id"}
    ]
    assert unknown_rows
    for row in unknown_rows:
        assert row.production_transition == "not_implemented"
        assert row.restart_action.value == "no_automatic_resubmit"
