"""Authenticated exact-manifest pilot control-plane guards."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes.hourly_pilot_executor import (
    HOURLY_PILOT_CONTRACT_ROUTE,
    HOURLY_PILOT_CREDENTIAL_HEADER,
)
from app.core.config import Settings, get_settings
from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    PHOENIX_HOURLY_PILOT_MANIFEST_SHA256,
)
from app.main import app

URL = f"/internal/v1{HOURLY_PILOT_CONTRACT_ROUTE}"
CREDENTIAL = "test-only-hourly-pilot-credential"
BODY = {
    "manifest_sha256": PHOENIX_HOURLY_PILOT_MANIFEST_SHA256,
    "slot_id": CANARY_SLOT_ID,
}


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOURLY_PILOT_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("HOURLY_PILOT_EXECUTOR_CREDENTIAL", CREDENTIAL)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client() -> TestClient:
    return TestClient(app)


def _headers(value: str = CREDENTIAL) -> dict[str, str]:
    return {HOURLY_PILOT_CREDENTIAL_HEADER: value}


def test_executor_defaults_closed_and_route_stays_out_of_public_openapi() -> None:
    fields = Settings.model_fields
    assert fields["hourly_pilot_executor_enabled"].default is False
    assert fields["hourly_pilot_executor_credential"].default == ""
    assert URL not in app.openapi()["paths"]


@pytest.mark.parametrize("headers", [{}, _headers("wrong")])
def test_missing_or_wrong_credential_is_rejected(headers: dict[str, str]) -> None:
    response = _client().post(URL, json=BODY, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "hourly_pilot_authentication_failed"
    assert CREDENTIAL not in response.text


def test_disabled_executor_fails_before_contract_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOURLY_PILOT_EXECUTOR_ENABLED", "false")
    get_settings.cache_clear()
    response = _client().post(URL, json=BODY, headers=_headers())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "hourly_pilot_executor_disabled"


def test_exact_canary_contract_comes_from_server_manifest() -> None:
    response = _client().post(URL, json=BODY, headers=_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "slot_contract_verified"
    assert body["manifest_sha256"] == PHOENIX_HOURLY_PILOT_MANIFEST_SHA256
    assert body["slot_id"] == CANARY_SLOT_ID
    assert body["phase"] == "canary"
    assert body["request_fingerprint"]
    assert body["vendor_attempted"] is False
    assert body["reservation_created"] is False
    assert "aoi" not in response.text.lower()


@pytest.mark.parametrize(
    "extra",
    [
        {"aoi": {"type": "Polygon", "coordinates": []}},
        {"manifest": {"slots": []}},
        {"polygon_aoi": {"type": "Polygon", "coordinates": []}},
    ],
)
def test_caller_cannot_replace_server_owned_manifest_or_aoi(extra: dict) -> None:
    response = _client().post(URL, json={**BODY, **extra}, headers=_headers())
    assert response.status_code == 422
    assert CREDENTIAL not in response.text


def test_altered_manifest_hash_is_rejected() -> None:
    response = _client().post(
        URL,
        json={**BODY, "manifest_sha256": "0" * 64},
        headers=_headers(),
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "hourly_pilot_manifest_mismatch"
    assert detail["expected_manifest_sha256"] == PHOENIX_HOURLY_PILOT_MANIFEST_SHA256


def test_unknown_slot_is_rejected() -> None:
    response = _client().post(
        URL,
        json={**BODY, "slot_id": "2024-07-15T03:30"},
        headers=_headers(),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "hourly_pilot_slot_not_found"


def test_batch_slot_is_blocked_until_canary_completion() -> None:
    response = _client().post(
        URL,
        json={**BODY, "slot_id": "2024-07-15T04:00"},
        headers=_headers(),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "hourly_pilot_canary_required"
