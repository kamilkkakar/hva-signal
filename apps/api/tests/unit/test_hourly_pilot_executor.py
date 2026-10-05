"""Authenticated exact-manifest pilot control-plane guards."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import hourly_pilot_executor as route
from app.api.routes.hourly_pilot_executor import (
    HOURLY_PILOT_CONTRACT_ROUTE,
    HOURLY_PILOT_CREDENTIAL_HEADER,
    HOURLY_PILOT_EXECUTE_ROUTE,
)
from app.core.config import Settings, get_settings
from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    PHOENIX_HOURLY_PILOT_MANIFEST_SHA256,
)
from app.core.postgres_acquisition import (
    AcquisitionInProgress,
    AcquisitionNeedsRecovery,
    AcquisitionStorageUnavailable,
)
from app.integrations.fortyguard.exceptions import (
    AcquisitionAllowanceExceeded,
    TaskFailedError,
    TaskTimeoutError,
)
from app.main import app

URL = f"/internal/v1{HOURLY_PILOT_CONTRACT_ROUTE}"
EXECUTE_URL = f"/internal/v1{HOURLY_PILOT_EXECUTE_ROUTE}"
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


def test_audit_authenticates_before_connecting(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(route, "store_from_settings", factory)
    response = _client().get("/internal/v1/hourly-pilot/audit")
    assert response.status_code == 401
    factory.assert_not_called()


def test_audit_is_private_read_only_metadata(monkeypatch):
    store = Mock()
    store.audit.return_value = {"total": 53, "records": [], "database_bytes": 25141248}
    monkeypatch.setattr(route, "store_from_settings", lambda _: store)
    vendor = Mock()
    monkeypatch.setattr(route, "FortyGuardHttpClient", vendor)
    response = _client().get("/internal/v1/hourly-pilot/audit", headers=_headers())
    assert response.status_code == 200
    assert response.json()["total"] == 53
    assert len(response.json()["slots"]) == 72
    assert response.json()["vendor_submission_attempted"] is False
    store.audit.assert_called_once_with()
    store.run.assert_not_called()
    store.migrate.assert_not_called()
    vendor.assert_not_called()
    assert "/internal/v1/hourly-pilot/audit" not in app.openapi()["paths"]


def test_audit_storage_failure_is_sanitized(monkeypatch):
    store = Mock()
    store.audit.side_effect = RuntimeError("private database connection detail")
    monkeypatch.setattr(route, "store_from_settings", lambda _: store)
    response = _client().get("/internal/v1/hourly-pilot/audit", headers=_headers())
    assert response.status_code == 503
    assert "private database" not in response.text


def test_executor_defaults_closed_and_route_stays_out_of_public_openapi() -> None:
    fields = Settings.model_fields
    assert fields["hourly_pilot_executor_enabled"].default is False
    assert fields["hourly_pilot_executor_credential"].default == ""
    assert URL not in app.openapi()["paths"]
    assert EXECUTE_URL not in app.openapi()["paths"]


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


def test_disabled_execution_never_constructs_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOURLY_PILOT_EXECUTOR_ENABLED", "false")
    get_settings.cache_clear()
    dependencies = Mock()
    monkeypatch.setattr(route, "_execution_dependencies", dependencies)

    response = _client().post(EXECUTE_URL, json=BODY, headers=_headers())

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "hourly_pilot_executor_disabled"
    dependencies.assert_not_called()


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


@pytest.mark.parametrize("headers", [{}, _headers("wrong")])
def test_execution_rejects_missing_or_wrong_credential_before_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    dependencies = Mock()
    monkeypatch.setattr(route, "_execution_dependencies", dependencies)
    response = _client().post(EXECUTE_URL, json=BODY, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "hourly_pilot_authentication_failed"
    dependencies.assert_not_called()


def test_execution_rejects_client_owned_aoi_before_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies = Mock()
    monkeypatch.setattr(route, "_execution_dependencies", dependencies)
    response = _client().post(
        EXECUTE_URL,
        json={**BODY, "polygon_aoi": {"type": "Polygon", "coordinates": []}},
        headers=_headers(),
    )
    assert response.status_code == 422
    dependencies.assert_not_called()


def test_execution_requires_shared_storage_and_vendor_credential() -> None:
    response = _client().post(EXECUTE_URL, json=BODY, headers=_headers())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "hourly_pilot_execution_unavailable"
    assert CREDENTIAL not in response.text


def test_execution_returns_only_bounded_durable_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, client = Mock(), Mock()
    monkeypatch.setattr(route, "_execution_dependencies", lambda _: (store, client))
    execute = Mock(
        return_value=(
            {"activity_id": "pilot-activity", "result": {"secret-shape": "omitted"}},
            "durable_resume",
        )
    )
    monkeypatch.setattr(route, "execute_hourly_pilot_canary", execute)

    response = _client().post(EXECUTE_URL, json=BODY, headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "status": "canary_execution_completed",
        "manifest_sha256": PHOENIX_HOURLY_PILOT_MANIFEST_SHA256,
        "slot_id": CANARY_SLOT_ID,
        "request_fingerprint": response.json()["request_fingerprint"],
        "activity_id": "pilot-activity",
        "acquisition_source": "durable_resume",
        "vendor_submission_attempted": False,
        "durable_recovery": True,
        "durable_replay": False,
        "result_stored": True,
    }
    assert len(response.json()["request_fingerprint"]) == 64
    assert "secret-shape" not in response.text
    assert "aoi" not in response.text.lower()
    execute.assert_called_once()
    client.close.assert_called_once()


@pytest.mark.parametrize(
    "error, status_code, code",
    [
        (AcquisitionAllowanceExceeded(20, 20), 429, "hourly_pilot_daily_limit"),
        (AcquisitionInProgress("private"), 409, "hourly_pilot_in_progress"),
        (AcquisitionNeedsRecovery("private"), 409, "hourly_pilot_recovery_required"),
        (AcquisitionStorageUnavailable("private"), 503, "hourly_pilot_execution_unavailable"),
        (TaskTimeoutError("private"), 504, "hourly_pilot_poll_timeout"),
        (TaskFailedError("private"), 502, "hourly_pilot_vendor_failed"),
        (httpx.ReadTimeout("private"), 502, "hourly_pilot_vendor_communication_interrupted"),
    ],
)
def test_execution_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    client = Mock()
    monkeypatch.setattr(route, "_execution_dependencies", lambda _: (Mock(), client))
    monkeypatch.setattr(route, "execute_hourly_pilot_canary", Mock(side_effect=error))

    response = _client().post(EXECUTE_URL, json=BODY, headers=_headers())

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code
    assert "private" not in response.text
    client.close.assert_called_once()


def test_batch_disabled_before_dependencies(monkeypatch):
    dependencies = Mock()
    monkeypatch.setattr(route, '_execution_dependencies', dependencies)
    response = _client().post('/internal/v1/hourly-pilot/slot', json=BODY, headers=_headers())
    assert response.status_code == 503
    dependencies.assert_not_called()


def test_batch_executes_exact_slot(monkeypatch):
    monkeypatch.setenv('HOURLY_PILOT_BATCH_ENABLED', 'true')
    get_settings.cache_clear()
    client = Mock()
    monkeypatch.setattr(route, '_execution_dependencies', lambda settings: (Mock(), client))
    execute = Mock(return_value=({'activity_id': 'saved'}, 'durable_replay'))
    monkeypatch.setattr(route, 'execute_hourly_pilot_slot', execute)
    body = {**BODY, 'slot_id': '2024-07-15T04:00'}
    response = _client().post('/internal/v1/hourly-pilot/slot', json=body, headers=_headers())
    assert response.status_code == 200
    assert response.json()['durable_replay'] is True
    assert response.json()['vendor_submission_attempted'] is False
    assert execute.call_args.kwargs['slot_id'] == body['slot_id']
    client.close.assert_called_once()


@pytest.mark.parametrize('payload', [{**BODY, 'slot_id': '2025-07-15T04:00'}, {**BODY, 'polygon_aoi': []}, {**BODY, 'manifest_sha256': '0' * 64}])
def test_batch_rejects_modified_contract(monkeypatch, payload):
    monkeypatch.setenv('HOURLY_PILOT_BATCH_ENABLED', 'true')
    get_settings.cache_clear()
    dependencies = Mock()
    monkeypatch.setattr(route, '_execution_dependencies', dependencies)
    response = _client().post('/internal/v1/hourly-pilot/slot', json=payload, headers=_headers())
    assert response.status_code in (404, 409, 422)
    dependencies.assert_not_called()


def test_usage_auth_and_sanitized_balance(monkeypatch):
    client = Mock()
    client.remaining_credits.return_value = 1995780.0
    factory = Mock(return_value=client)
    monkeypatch.setattr(route, 'FortyGuardHttpClient', factory)
    assert _client().get('/internal/v1/hourly-pilot/usage').status_code == 401
    factory.assert_not_called()
    response = _client().get('/internal/v1/hourly-pilot/usage', headers=_headers())
    assert response.status_code == 200
    assert response.json()['remaining_credits'] == 1995780.0
    assert response.json()['vendor_submission_attempted'] is False
    assert '/internal/v1/hourly-pilot/usage' not in app.openapi()['paths']
    assert '/internal/v1/hourly-pilot/slot' not in app.openapi()['paths']
    client.close.assert_called_once()
