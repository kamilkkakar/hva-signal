"""Async analysis jobs + UNKNOWN_JOB recovery."""

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _valid_payload() -> dict:
    return {
        "area_id": "phoenix-demo",
        "analysis_time": datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc).isoformat(),
        "analysis_mode": "operational",
        "horizon_hours": 12,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }


def test_create_job_returns_queued_job() -> None:
    response = client.post("/api/v1/analysis/jobs", json=_valid_payload())
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["job_id"]
    assert body["request"]["area_id"] == "phoenix-demo"
    assert body["request"]["horizon_hours"] == 12
    assert body["request"]["granularity_m"] == 100


def test_get_job_returns_same_job() -> None:
    created = client.post("/api/v1/analysis/jobs", json=_valid_payload()).json()
    response = client.get(f"/api/v1/analysis/jobs/{created['job_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == created["job_id"]
    assert body["status"] in {
        "queued",
        "loading_context",
        "fetching_thermal",
        "assembling_partitions",
        "aggregating_zones",
        "validating_hazard_spread",
        "normalizing",
        "computing",
        "complete",
        "partial",
        "failed",
    }


def test_unknown_job_is_recoverable() -> None:
    response = client.get("/api/v1/analysis/jobs/job_does_not_exist")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job_does_not_exist"
    assert body["status"] == "unknown_job"
    assert body["recoverable"] is True
    assert "no longer present" in body["message"].lower()


def test_job_unknown_after_runtime_restart() -> None:
    """Process restart clears the in-memory store; UI must resubmit.

    A fresh TestClient shares the same module-level job_store singleton, so
    restart is simulated by clearing the backing dict (equivalent to a new
    uvicorn worker with empty memory).
    """
    from app.core.jobs import job_store

    created = client.post("/api/v1/analysis/jobs", json=_valid_payload()).json()
    job_id = created["job_id"]

    job_store.reset()

    response = client.get(f"/api/v1/analysis/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "unknown_job"
    assert body["recoverable"] is True


def test_rejects_horizon_above_12h() -> None:
    payload = _valid_payload()
    payload["horizon_hours"] = 13
    response = client.post("/api/v1/analysis/jobs", json=payload)
    assert response.status_code == 422


def test_rejects_invalid_granularity() -> None:
    payload = _valid_payload()
    payload["granularity_m"] = 50
    response = client.post("/api/v1/analysis/jobs", json=payload)
    assert response.status_code == 422


def test_processed_replay_job_returns_terminal_status_with_null_probability() -> None:
    from app.core.jobs import job_store

    job_store.reset()
    created = client.post("/api/v1/analysis/jobs", json=_valid_payload())
    assert created.status_code == 202
    created_body = created.json()
    assert created_body["status"] == "queued"
    assert created_body.get("result") in (None, {})

    response = client.get(f"/api/v1/analysis/jobs/{created_body['job_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"complete", "partial"}
    assert body["status"] != "queued"
    result = body["result"]
    assert result is not None
    assert result["data_status"] == "replay"
    assert result["zones"]
    for zone in result["zones"]:
        assert zone["ranked"] is False
        assert zone["probability"]["value"] is None
        assert zone["probability"]["status"] == "insufficient_evidence"
        assert "EVENT_PROBABILITY_BLOCKED_PENDING_GATE0" in zone["probability"]["quality_flags"]
    blob = json.dumps(body)
    assert "72% probability" not in blob
    assert '"value": 0.72' not in blob
    job_store.reset()


def test_processed_historical_03_job_returns_phoenix_v1_decision8_state() -> None:
    from app.core.jobs import job_store

    job_store.reset()
    payload = {
        "area_id": "phoenix-demo",
        "analysis_time": datetime(2022, 6, 30, 3, 0).isoformat(),
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }
    created = client.post("/api/v1/analysis/jobs", json=payload)
    assert created.status_code == 202
    body = client.get(f"/api/v1/analysis/jobs/{created.json()['job_id']}").json()
    assert body["status"] == "complete"
    result = body["result"]
    assert result["versions"]["area_config_version"] == "PHX_AREA_CONFIG_V1"
    assert result["reference_quality"] == "FULL_REFERENCE"
    assert result["thermal_differentiation_state"] == "SUFFICIENT"
    assert result["hazard_spread"]["input_quantity"] == "q_A"
    assert result["area_config_sha256"] == (
        "df00333a4df900a9762b7be975ed0c36b6e1749c953e9fb4690d9f6e4e02a60a"
    )
    assert all(zone["ranked"] is True for zone in result["zones"])
    assert all(zone["probability"]["value"] is None for zone in result["zones"])
    job_store.reset()
