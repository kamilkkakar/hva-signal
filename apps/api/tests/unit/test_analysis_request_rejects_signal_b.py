"""Current public analysis jobs must not accept unpublished Signal B fields."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.requests import AnalysisRequest
from app.main import app

client = TestClient(app)


def _valid() -> dict:
    return {
        "area_id": "phoenix-demo",
        "analysis_time": "2022-06-30T03:00:00",
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }


@pytest.mark.parametrize(
    "field",
    [
        "selected_time_snapshot",
        "selected_time",
        "signal_b",
        "snapshot",
        "prepare",
        "prepare_reference",
        "live_snapshot",
        "signals",
        "spend_authorization",
        "spend",
        "approval",
        "contract_version",
        "authorized_max_units",
    ],
)
def test_unpublished_signal_b_fields_are_rejected(field: str) -> None:
    payload = {**_valid(), field: True}
    with pytest.raises(ValidationError, match="unpublished two-signal"):
        AnalysisRequest.model_validate(payload)
    response = client.post("/api/v1/analysis/jobs", json=payload)
    assert response.status_code == 422


def test_current_replay_payload_still_validates() -> None:
    AnalysisRequest.model_validate(_valid())
