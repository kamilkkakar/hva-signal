"""Production J3/J4 gaps. Harness covers the matrix; production does not."""

from __future__ import annotations

from app.domain.live_crash_matrix.states import CRASH_POINTS, DurableWorkerState
from app.services.live_crash_matrix.production_gaps import inspect_production_gaps


def test_production_lacks_j3_j4_worker_and_activity_id() -> None:
    report = inspect_production_gaps()
    assert report.j3_j4_worker_implemented is False
    assert report.job_persists_activity_id is False
    assert report.harness_covers_all_nine_points is True
    assert DurableWorkerState.UNKNOWN_VENDOR_STATE.value in report.missing_durable_states
    assert DurableWorkerState.RECOVERY_REQUIRED.value in report.missing_durable_states
    assert set(report.missing_crash_points_in_production) == {
        point.value for point in CRASH_POINTS
    }


def test_production_recheck_consumes_before_submit_is_documented_gap() -> None:
    report = inspect_production_gaps()
    assert report.consume_happens_before_submit_in_recheck is True
    assert any("consume-before-submit" in note for note in report.notes)


def test_unimplemented_transitions_named_for_every_crash_point() -> None:
    report = inspect_production_gaps()
    crash_gaps = [
        item for item in report.unimplemented_transitions if item.startswith("crash:")
    ]
    assert [item.split(":", 1)[1] for item in crash_gaps] == [
        point.value for point in CRASH_POINTS
    ]
    assert "state:UNKNOWN_VENDOR_STATE" in report.unimplemented_transitions
    assert "state:ALLOWANCE_RESERVED" in report.unimplemented_transitions
    assert "state:ACTIVITY_ID_PERSISTED" in report.unimplemented_transitions
