"""Public HVA-Signal remains accountless. Secrets stay off the wire."""

from app.core.config import Settings
from app.domain.public_contract import TwoSignalPublicJob, WorkerHandoff
from app.main import app
from app.services.secret_boundary import public_payload_leaks_secrets


def test_public_routes_have_no_auth_dependencies() -> None:
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        names = [str(dep.name or "") for dep in dependant.dependencies]
        assert not any("auth" in name.lower() for name in names)
        path = getattr(route, "path", "")
        assert "login" not in path
        assert "oauth" not in path
        assert "signup" not in path


def test_openapi_has_no_login_or_demo_budget() -> None:
    schema = app.openapi()
    blob = str(schema).lower()
    assert "login" not in blob
    assert "/oauth" not in blob
    assert "fortyguard_api_key" not in blob
    assert "demo_budget" not in blob
    assert "allowance_remaining" not in blob


def test_public_job_and_handoff_cannot_carry_key_fields() -> None:
    assert "fortyguard_api_key" not in TwoSignalPublicJob.model_fields
    assert "api_key" not in WorkerHandoff.model_fields
    assert "allowance_remaining" not in TwoSignalPublicJob.model_fields


def test_settings_key_is_not_a_public_ready_field() -> None:
    assert "fortyguard_api_key" in Settings.model_fields
    from fastapi.testclient import TestClient

    body = TestClient(app).get("/ready").json()
    assert public_payload_leaks_secrets(body) == []
    assert "fortyguard_api_key" not in body
