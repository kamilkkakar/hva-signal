"""Contract cluster 4: AnalysisMode and AnalysisRequest validation."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain import AnalysisMode, AnalysisRequest, DataMode


def _valid_request(**overrides) -> dict:
    payload = {
        "area_id": "phoenix-demo",
        "analysis_time": datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
        "analysis_mode": AnalysisMode.OPERATIONAL,
        "horizon_hours": 12,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": DataMode.AUTO,
        "scenario": None,
    }
    payload.update(overrides)
    return payload


def test_analysis_request_field_names() -> None:
    assert set(AnalysisRequest.model_fields) == {
        "area_id",
        "analysis_time",
        "analysis_mode",
        "horizon_hours",
        "lookback_hours",
        "granularity_m",
        "data_mode",
        "scenario",
    }


def test_analysis_request_defaults() -> None:
    request = AnalysisRequest(**_valid_request())
    assert request.lookback_hours == 0
    assert request.data_mode == DataMode.AUTO
    assert request.scenario is None
    assert request.analysis_mode == AnalysisMode.OPERATIONAL


def test_horizon_hours_bounds_0_to_12() -> None:
    AnalysisRequest(**_valid_request(horizon_hours=0))
    AnalysisRequest(**_valid_request(horizon_hours=12))
    with pytest.raises(ValidationError):
        AnalysisRequest(**_valid_request(horizon_hours=-1))
    with pytest.raises(ValidationError):
        AnalysisRequest(**_valid_request(horizon_hours=13))


def test_lookback_hours_bounds_0_to_24_times_31() -> None:
    AnalysisRequest(**_valid_request(lookback_hours=0))
    AnalysisRequest(**_valid_request(lookback_hours=24 * 31))
    with pytest.raises(ValidationError):
        AnalysisRequest(**_valid_request(lookback_hours=-1))
    with pytest.raises(ValidationError):
        AnalysisRequest(**_valid_request(lookback_hours=24 * 31 + 1))


def test_granularity_must_be_60_80_or_100() -> None:
    for granularity in (60, 80, 100):
        AnalysisRequest(**_valid_request(granularity_m=granularity))
    with pytest.raises(ValidationError):
        AnalysisRequest(**_valid_request(granularity_m=50))


def test_jobs_route_uses_domain_analysis_request() -> None:
    from app.api.routes import analysis_jobs
    from app.domain import AnalysisRequest as DomainAnalysisRequest

    assert analysis_jobs.AnalysisRequest is DomainAnalysisRequest
