"""Cached phoenix-demo Signal B seed. 25/25 reuse. Downtown 0/25 stays negative."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.two_signal_jobs import router as two_signal_router
from app.core.jobs import job_store
from app.schemas.two_signal_public import TwoSignalPublicationRequest
from app.services.signal_b_cached_seed import (
    ADAPTER_L2_KEY,
    CACHED_ACTIVITY_ID,
    CACHED_SNAPSHOT_FINGERPRINT,
    load_phoenix_cached_snapshot,
)
from app.services.snapshot_identity import snapshot_request_fingerprint
from app.services.two_signal_jobs import (
    reset_two_signal_runtime,
    reuse_store,
    seed_cached_selected_time,
    two_signal_job_service,
)

DOWNTOWN_FIXTURE = (
    "apps/api/tests/fixtures/fortyguard/heatmap_tcm_hourly_1500.json"
)


@pytest.fixture(autouse=True)
def _isolate() -> None:
    job_store.reset()
    reset_two_signal_runtime()
    yield
    job_store.reset()
    reset_two_signal_runtime()


def _client() -> TestClient:
    application = FastAPI()
    application.include_router(two_signal_router, prefix="/api/v1")
    return TestClient(application)


def test_seed_fingerprint_is_identity_v1_not_adapter_l2() -> None:
    snapshot = load_phoenix_cached_snapshot()
    computed = snapshot_request_fingerprint(
        area_id=snapshot.area_id,
        geometry_sha256=snapshot.geometry_sha256 or "",
        zone_geometry_version=snapshot.provenance.geometry_version or "",
        target_timestamp=snapshot.target_timestamp,
        timezone=snapshot.timezone,
        analytic="tcm",
        granularity_m=100,
        aggregation_spec_version=snapshot.aggregation_spec_version,
    )
    assert computed == CACHED_SNAPSHOT_FINGERPRINT
    assert computed != ADAPTER_L2_KEY
    assert CACHED_ACTIVITY_ID in " ".join(snapshot.provenance.notes)


def test_seed_is_25_of_25_cached_selected_time_only() -> None:
    snapshot = load_phoenix_cached_snapshot()
    dumped = snapshot.model_dump()
    assert snapshot.valid_zone_count == 25
    assert snapshot.expected_zone_count == 25
    assert snapshot.missing_zone_ids == []
    assert len(snapshot.zones) == 25
    assert snapshot.provenance.source.value == "fortyguard_cached"
    assert snapshot.provenance.data_status.value == "cached"
    assert snapshot.provenance.reference_version is None
    assert snapshot.provenance.reference_source is None
    assert "q_A" not in dumped
    assert "ranked" not in dumped
    assert "priority" not in dumped
    temps = [zone.mean_temperature_c for zone in snapshot.zones]
    assert all(value is not None for value in temps)
    assert min(temps) == pytest.approx(33.469, abs=0.02)
    assert max(temps) == pytest.approx(33.724, abs=0.02)


def test_reuse_hit_serves_cached_b_without_vendor() -> None:
    seed_cached_selected_time()
    payload = TwoSignalPublicationRequest.model_validate(
        {
            "contract_version": "hva-signal-two-signal-job-v1",
            "area_id": "phoenix-demo",
            "signals": {
                "selected_time": {
                    "target_timestamp": "2025-07-15T03:00:00",
                    "analytic": "tcm",
                }
            },
            "timezone": "America/Phoenix",
            "granularity_m": 100,
            "data_mode": "auto",
        }
    )
    job = two_signal_job_service.create(payload)
    section = job.selected_time
    assert section.requested is True
    assert section.availability.value == "READY"
    assert section.selected_time_result is not None
    result = section.selected_time_result
    assert result.valid_zone_count == 25
    assert result.expected_zone_count == 25
    assert section.provenance.source == "fortyguard_cached"
    assert section.provenance.data_status == "cached"
    assert result.temperature_min_c is not None
    assert result.temperature_max_c is not None
    body = job.model_dump(mode="json")
    assert "q_A" not in str(body["selected_time"])
    assert reuse_store.get(CACHED_SNAPSHOT_FINGERPRINT) is not None


def test_unseeded_hour_stays_unavailable() -> None:
    client = _client()
    response = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json={
            "contract_version": "hva-signal-two-signal-job-v1",
            "area_id": "phoenix-demo",
            "signals": {
                "selected_time": {
                    "target_timestamp": "2025-07-15T03:00:00",
                    "analytic": "tcm",
                }
            },
            "timezone": "America/Phoenix",
            "data_mode": "replay",
        },
    )
    assert response.status_code == 202
    selected = response.json()["selected_time"]
    assert selected["availability"] == "UNAVAILABLE"


def test_data_mode_live_is_422() -> None:
    client = _client()
    response = client.post(
        "/api/v1/analysis/two-signal-jobs",
        json={
            "contract_version": "hva-signal-two-signal-job-v1",
            "area_id": "phoenix-demo",
            "signals": {
                "selected_time": {
                    "target_timestamp": "2025-07-15T03:00:00",
                    "analytic": "tcm",
                }
            },
            "timezone": "America/Phoenix",
            "data_mode": "live",
        },
    )
    assert response.status_code == 422


def test_downtown_negative_fixture_path_unchanged() -> None:
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "fortyguard" / "heatmap_tcm_hourly_1500.json"
    assert fixture.is_file()
    text = fixture.read_text(encoding="utf-8")
    assert "q_A" not in text

