"""Supported-area discovery. Metadata only; no geometry."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.core.phoenix_v1_area_config import load_frozen_phoenix_v1_area_config
from app.domain.phoenix_v1 import AREA_ID, ZONE_GEOMETRY_VERSION
from app.main import app

client = TestClient(app)


def test_list_areas_returns_only_supported_phoenix() -> None:
    response = client.get("/api/v1/areas")
    assert response.status_code == 200
    body = response.json()
    assert list(body.keys()) == ["areas"]
    assert len(body["areas"]) == 1
    area = body["areas"][0]
    assert area["area_id"] == AREA_ID
    assert area["supported"] is True
    assert area["expected_zone_count"] == 25
    config = load_frozen_phoenix_v1_area_config()
    assert area["area_config_version"] == config.version
    assert area["reference_version"] == config.historical_reference_window.version
    assert area["zone_geometry_version"] == config.zone_geometry_version
    assert area["zone_geometry_version"] == ZONE_GEOMETRY_VERSION
    blob = json.dumps(body)
    assert "workforce" not in blob
    assert "geometry_path" not in blob
    assert "geometry_sha256" not in blob
    assert "FeatureCollection" not in blob
    assert "coordinates" not in blob
    assert "data/demo" not in blob
    assert "data/phoenix" not in blob
    assert "data/areas" not in blob
    assert "/tmp" not in blob
    assert "api_key" not in blob.lower()
    assert "fortyguard" not in blob.lower()


def test_list_areas_is_driven_by_registry_enumeration() -> None:
    from app.core.area_registry import list_supported_area_ids

    response = client.get("/api/v1/areas")
    ids = [item["area_id"] for item in response.json()["areas"]]
    assert ids == list_supported_area_ids()


def test_unknown_area_analysis_job_fails_closed() -> None:
    from app.core.jobs import job_store

    job_store.reset()
    payload = {
        "area_id": "not-a-supported-area",
        "analysis_time": datetime(2022, 7, 1, 3, 0).isoformat(),
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }
    created = client.post("/api/v1/analysis/jobs", json=payload)
    assert created.status_code == 202
    body = client.get(f"/api/v1/analysis/jobs/{created.json()['job_id']}").json()
    assert body["status"] == "failed"
    assert body.get("result") in (None, {})
    assert "not-a-supported-area" in (body.get("message") or "")
    blob = json.dumps(body)
    assert "FULL_REFERENCE" not in blob
    assert "INSUFFICIENT" not in blob
    assert "SUFFICIENT" not in blob
    job_store.reset()
