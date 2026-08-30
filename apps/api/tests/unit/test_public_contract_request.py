"""Candidate public request validates independently of spend authorization."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.public_contract import (
    PublicSelectedTimeResult,
    TwoSignalPublicRequest,
    WorkerHandoff,
)
from app.domain.signals import ThermalSignalKind


def _base(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "area_id": "phoenix-demo",
        "signals": {
            "historical": {"analysis_time": "2022-06-30T03:00:00"},
            "selected_time": {"target_timestamp": "2024-07-15T15:00:00"},
        },
        "timezone": "America/Phoenix",
        "granularity_m": 100,
        "data_mode": "replay",
    }
    payload.update(overrides)
    return payload


def test_a_only_request() -> None:
    req = TwoSignalPublicRequest.model_validate(
        _base(signals={"historical": {"analysis_time": "2022-06-30T03:00:00"}})
    )
    assert req.signals.historical is not None
    assert req.signals.selected_time is None


def test_b_only_request() -> None:
    req = TwoSignalPublicRequest.model_validate(
        _base(signals={"selected_time": {"target_timestamp": "2024-07-15T15:00:00"}})
    )
    assert req.signals.historical is None
    assert req.signals.selected_time is not None
    assert req.signals.selected_time.acquisition_preference.value == "reuse_only"


def test_hosted_live_preference_is_intent_not_authorization() -> None:
    req = TwoSignalPublicRequest.model_validate(
        _base(
            signals={
                "selected_time": {
                    "target_timestamp": "2024-07-15T15:00:00",
                    "acquisition_preference": "allow_hosted_live_demo",
                }
            }
        )
    )
    assert req.signals.selected_time.acquisition_preference.value == (
        "allow_hosted_live_demo"
    )
    with pytest.raises(ValidationError):
        TwoSignalPublicRequest.model_validate(_base(authorized_max_units=99))


def test_a_plus_b_keeps_independent_timestamps() -> None:
    req = TwoSignalPublicRequest.model_validate(_base())
    assert req.signals.historical.analysis_time == datetime(2022, 6, 30, 3, 0, 0)
    assert req.signals.selected_time.target_timestamp == datetime(2024, 7, 15, 15, 0, 0)


def test_b_on_unnamed_geography_is_syntactically_valid() -> None:
    req = TwoSignalPublicRequest.model_validate(
        _base(
            area_id="unregistered-place",
            signals={"selected_time": {"target_timestamp": "2024-07-15T15:00:00"}},
        )
    )
    assert req.area_id == "unregistered-place"


def test_nonzero_minutes_are_rejected() -> None:
    with pytest.raises(ValidationError, match="minutes"):
        TwoSignalPublicRequest.model_validate(
            _base(
                signals={"selected_time": {"target_timestamp": "2024-07-15T15:10:00"}}
            )
        )


def test_signal_a_non_0300_is_rejected() -> None:
    with pytest.raises(ValidationError, match="03:00"):
        TwoSignalPublicRequest.model_validate(
            _base(signals={"historical": {"analysis_time": "2022-06-30T15:00:00"}})
        )


def test_unsupported_signal_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicRequest.model_validate(
            _base(
                signals={
                    "historical": {"analysis_time": "2022-06-30T03:00:00"},
                    "overnight": {"requested": True},
                }
            )
        )


def test_now_alias_is_not_a_field() -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicRequest.model_validate(
            _base(
                signals={
                    "selected_time": {
                        "target_timestamp": "2024-07-15T15:00:00",
                        "now": True,
                    }
                }
            )
        )


def test_approval_flag_is_not_a_request_field() -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicRequest.model_validate(_base(approval=True))


def test_signal_b_result_rejects_q_a_and_rank() -> None:
    with pytest.raises(ValidationError):
        PublicSelectedTimeResult.model_validate(
            {
                "target_timestamp": "2024-07-15T15:00:00",
                "timezone": "America/Phoenix",
                "q_A": 0.4,
            }
        )
    with pytest.raises(ValidationError):
        PublicSelectedTimeResult.model_validate(
            {
                "target_timestamp": "2024-07-15T15:00:00",
                "timezone": "America/Phoenix",
                "thermal_ordering_permitted": True,
            }
        )


def test_worker_handoff_must_recheck() -> None:
    handoff = WorkerHandoff(
        job_id="job_1",
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint="aa" * 32,
        authorized_max_units=1,
        planned_acquisition_units=1,
    )
    assert handoff.must_recheck_authorization is True
    with pytest.raises(ValidationError):
        WorkerHandoff.model_validate(
            {
                "job_id": "job_1",
                "signal_kind": "selected_time_snapshot",
                "request_fingerprint": "aa" * 32,
                "authorized_max_units": 1,
                "planned_acquisition_units": 1,
                "must_recheck_authorization": False,
            }
        )


def test_dst_gap_and_fold_are_rejected_without_new_public_code() -> None:
    with pytest.raises(ValidationError, match="does not exist"):
        TwoSignalPublicRequest.model_validate(
            _base(
                timezone="America/New_York",
                signals={"selected_time": {"target_timestamp": "2026-03-08T02:00:00"}},
            )
        )
    with pytest.raises(ValidationError, match="ambiguous"):
        TwoSignalPublicRequest.model_validate(
            _base(
                timezone="America/New_York",
                signals={"selected_time": {"target_timestamp": "2026-11-01T01:00:00"}},
            )
        )


def test_phoenix_transition_hours_remain_valid() -> None:
    spring = TwoSignalPublicRequest.model_validate(
        _base(
            signals={"selected_time": {"target_timestamp": "2026-03-08T02:00:00"}}
        )
    )
    fall = TwoSignalPublicRequest.model_validate(
        _base(
            signals={"selected_time": {"target_timestamp": "2026-11-01T01:00:00"}}
        )
    )
    assert spring.timezone == "America/Phoenix"
    assert fall.timezone == "America/Phoenix"


def test_aware_b_timestamp_rejected() -> None:
    with pytest.raises(ValidationError, match="naive"):
        TwoSignalPublicRequest.model_validate(
            _base(
                signals={
                    "selected_time": {
                        "target_timestamp": datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
                    }
                }
            )
        )
