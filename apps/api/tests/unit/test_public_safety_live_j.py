"""LIVE-J public-safety guards. No FortyGuard. No real vendor."""

from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.hosted_live_policy import (
    HostedLiveDisabledError,
    acquisition_preference_cannot_enable_live,
    client_cannot_enable_hosted_live,
    hosted_live_defaults_are_off,
    may_construct_real_vendor,
    refuse_real_vendor,
    resolve_hosted_live,
)
from app.core.operator_approval import (
    client_approval_is_ignored,
    resolve_operator_approval,
)
from app.core.public_safety import (
    REASON_CLIENT_FORBIDDEN_FIELD,
    rejection_payload,
    scan_client_request,
)
from app.core.public_safety_middleware import (
    PublicSafetyMiddleware,
    public_safety_middleware_enabled,
)
from app.domain.public_safety_fields import (
    CATEGORY_ALLOWANCE_CAP,
    CATEGORY_BUDGET,
    CATEGORY_FORCE_LIVE,
    CATEGORY_KEY,
    CATEGORY_OPERATOR_APPROVAL,
    CATEGORY_RESERVATION_STATE,
    REQUIRED_CLIENT_NEVER_SET_CATEGORIES,
    classify_client_control_field,
)
from app.domain.requests import AnalysisRequest
from app.schemas.two_signal_public import TwoSignalPublicationRequest
from app.services.secret_boundary import public_payload_leaks_secrets
from app.services.secret_redaction import (
    REDACTED,
    SecretLogFilter,
    public_payload_leaks_secret_names,
    redact_for_log,
    redact_known_values,
    strip_secrets_from_public,
)
from app.services.spend_threat_guards import client_flags_cannot_authorize

_OWNED = (
    "app/core/public_safety.py",
    "app/core/public_safety_middleware.py",
    "app/core/hosted_live_policy.py",
    "app/core/operator_approval.py",
    "app/domain/public_safety_fields.py",
    "app/services/secret_redaction.py",
)

_VALID_ANALYSIS = {
    "area_id": "phoenix-demo",
    "analysis_time": "2022-06-30T03:00:00",
    "analysis_mode": "retrospective",
    "horizon_hours": 0,
    "lookback_hours": 0,
    "granularity_m": 100,
    "data_mode": "replay",
}

# One representative client name per required category.
_CATEGORY_SAMPLES = {
    CATEGORY_ALLOWANCE_CAP: (
        "allowance_cap",
        "authorized_max_units",
        "demo_allowance_max_total_units",
        "max_units_per_request",
    ),
    CATEGORY_BUDGET: ("budget", "demo_budget", "allowance_remaining"),
    CATEGORY_KEY: ("key", "api_key", "fortyguard_api_key", "internal_key"),
    CATEGORY_FORCE_LIVE: (
        "force_live",
        "hosted_live_enabled",
        "allow_hosted_live_demo",
        "demo_allowance_enabled",
    ),
    CATEGORY_OPERATOR_APPROVAL: (
        "operator_approval",
        "approved",
        "skip_approval",
        "spend_authorized",
    ),
    CATEGORY_RESERVATION_STATE: (
        "reservation_state",
        "reservation_id",
        "reserved",
        "consumed_units",
    ),
}


def test_required_categories_are_complete() -> None:
    assert REQUIRED_CLIENT_NEVER_SET_CATEGORIES == frozenset(_CATEGORY_SAMPLES)


@pytest.mark.parametrize(
    "raw,category",
    [
        (name, category)
        for category, names in _CATEGORY_SAMPLES.items()
        for name in names
    ],
)
def test_canonical_names_classify(raw: str, category: str) -> None:
    classified = classify_client_control_field(raw)
    assert classified is not None
    assert classified[1] == category


@pytest.mark.parametrize(
    "raw,category",
    [
        ("X-Force-Live", CATEGORY_FORCE_LIVE),
        ("forceLive", CATEGORY_FORCE_LIVE),
        ("x-api-key", CATEGORY_KEY),
        ("allowanceCap", CATEGORY_ALLOWANCE_CAP),
        ("demoBudget", CATEGORY_BUDGET),
        ("operatorApproval", CATEGORY_OPERATOR_APPROVAL),
        ("reservation-id", CATEGORY_RESERVATION_STATE),
        ("Authorization", CATEGORY_KEY),
    ],
)
def test_aliases_and_headers_classify(raw: str, category: str) -> None:
    classified = classify_client_control_field(raw)
    assert classified is not None
    assert classified[1] == category


def test_legitimate_request_keys_are_not_forbidden() -> None:
    for name in (
        "area_id",
        "analysis_time",
        "analysis_mode",
        "horizon_hours",
        "lookback_hours",
        "granularity_m",
        "data_mode",
        "timezone",
        "contract_version",
        "job_id",
        "status",
    ):
        assert classify_client_control_field(name) is None


@pytest.mark.parametrize("field", ["allowance_cap", "budget", "key", "force_live", "operator_approval", "reservation_state"])
def test_analysis_request_rejects_required_client_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**_VALID_ANALYSIS, field: True})


def test_nested_body_hits_are_detected() -> None:
    hits = scan_client_request(
        body={"area_id": "phoenix-demo", "nested": {"force_live": True, "key": "secret"}}
    )
    categories = {hit.category for hit in hits}
    assert CATEGORY_FORCE_LIVE in categories
    assert CATEGORY_KEY in categories
    payload = rejection_payload(hits)
    assert payload["reason_code"] == REASON_CLIENT_FORBIDDEN_FIELD
    assert "sk-secret" not in str(payload)
    assert "secret" not in payload.get("values", [])


def test_query_and_header_surfaces() -> None:
    hits = scan_client_request(
        headers={"X-Force-Live": "1", "X-Api-Key": "do-not-echo"},
        query="budget=999&reservation_id=res_1",
        body=None,
    )
    surfaces = {hit.surface for hit in hits}
    assert surfaces == {"header", "query"}
    blob = str(rejection_payload(hits))
    assert "do-not-echo" not in blob
    assert "999" not in blob


def test_hosted_live_defaults_off_and_client_cannot_enable() -> None:
    assert hosted_live_defaults_are_off() is True
    assert Settings.model_fields["hosted_live_enabled"].default is False
    assert Settings.model_fields["hosted_live_real_vendor_enabled"].default is False
    assert Settings.model_fields["operator_approval_enabled"].default is False
    closed = Settings.model_construct()
    assert resolve_hosted_live(settings=closed) is False
    assert client_cannot_enable_hosted_live(closed) is True
    assert may_construct_real_vendor(closed) is False
    assert acquisition_preference_cannot_enable_live("allow_hosted_live_demo") is True
    with pytest.raises(HostedLiveDisabledError):
        refuse_real_vendor(closed)


def test_operator_hosted_flag_still_refuses_real_vendor() -> None:
    opened = Settings.model_construct(hosted_live_enabled=True)
    assert resolve_hosted_live(settings=opened) is True
    assert (
        resolve_hosted_live(
            settings=opened,
            client_headers={"x-force-live": "false"},
            client_body={"hosted_live_enabled": False},
        )
        is True
    )
    assert may_construct_real_vendor(opened) is False
    with pytest.raises(HostedLiveDisabledError):
        refuse_real_vendor(opened)


def test_operator_approval_is_server_side_only() -> None:
    closed = Settings.model_construct()
    assert resolve_operator_approval(settings=closed).approved is False
    assert client_approval_is_ignored(closed) is True
    opened = Settings.model_construct(operator_approval_enabled=True)
    decision = resolve_operator_approval(
        settings=opened,
        client_payload={"operator_approval": False},
    )
    assert decision.approved is True
    assert decision.source == "server_settings"


def test_spend_threat_guards_see_live_j_fields() -> None:
    hits = client_flags_cannot_authorize(
        {
            "area_id": "phoenix-demo",
            "allowance_cap": 99,
            "budget": 12,
            "key": "secret",
            "force_live": True,
            "operator_approval": True,
            "reservation_state": "CONSUMED",
        }
    )
    for name in (
        "allowance_cap",
        "budget",
        "key",
        "force_live",
        "operator_approval",
        "reservation_state",
    ):
        assert name in hits


def test_secrets_never_logged_or_returned() -> None:
    planted = {
        "job_id": "job_x",
        "api_key": "sk-live-secret-value",
        "nested": {"fortyguard_api_key": "fg-secret", "area_id": "phoenix-demo"},
    }
    redacted = redact_for_log(planted)
    assert redacted["api_key"] == REDACTED
    assert redacted["nested"]["fortyguard_api_key"] == REDACTED
    assert redacted["nested"]["area_id"] == "phoenix-demo"
    assert "sk-live-secret-value" not in str(redacted)
    public = strip_secrets_from_public(planted)
    assert public_payload_leaks_secret_names(public) == []
    assert public_payload_leaks_secrets(public) == []
    assert "api_key" not in public
    assert public["nested"]["area_id"] == "phoenix-demo"
    line = redact_known_values(
        "using key sk-live-secret-value",
        ["sk-live-secret-value"],
    )
    assert "sk-live-secret-value" not in line
    assert REDACTED in line


def test_secret_log_filter_scrubs_values() -> None:
    logger = logging.getLogger("live_j_secret_test")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addFilter(SecretLogFilter(["super-secret-key-99"]))
    logger.propagate = False
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger.addHandler(_Capture())
    logger.info("token=super-secret-key-99")
    assert records
    assert "super-secret-key-99" not in records[0].getMessage()
    logger.handlers.clear()
    logger.filters.clear()


def test_ready_and_openapi_omit_secrets() -> None:
    from app.main import app

    client = TestClient(app)
    body = client.get("/ready").json()
    assert public_payload_leaks_secrets(body) == []
    assert public_payload_leaks_secret_names(body) == []
    assert "fortyguard_api_key" not in body
    assert body["status"] == "ready"
    schema = app.openapi()
    assert public_payload_leaks_secret_names(schema) == []
    blob = str(schema).lower()
    assert "fortyguard_api_key" not in blob


def test_public_safety_middleware_default_on_and_mounted() -> None:
    assert public_safety_middleware_enabled() is True
    from app.main import app

    names = [getattr(item, "cls", type(item)).__name__ for item in app.user_middleware]
    assert "PublicSafetyMiddleware" in names


def test_middleware_rejects_body_query_header_without_echo() -> None:
    inner = FastAPI()

    @inner.post("/api/v1/analysis/jobs")
    def _create() -> dict[str, bool]:
        return {"ok": True}

    @inner.get("/ready")
    def _ready() -> dict[str, str]:
        return {"status": "ready"}

    inner.add_middleware(PublicSafetyMiddleware, enabled=True)
    client = TestClient(inner)

    assert client.get("/ready").status_code == 200

    body = client.post(
        "/api/v1/analysis/jobs",
        json={**_VALID_ANALYSIS, "force_live": True, "api_key": "sk-must-not-echo"},
    )
    assert body.status_code == 422
    payload = body.json()
    assert payload["reason_code"] == REASON_CLIENT_FORBIDDEN_FIELD
    assert "force_live" in payload["fields"]
    assert "sk-must-not-echo" not in str(payload)

    query = client.get("/ready", params={"hosted_live_enabled": "true"})
    assert query.status_code == 422
    assert query.json()["reason_code"] == REASON_CLIENT_FORBIDDEN_FIELD

    header = client.post(
        "/api/v1/analysis/jobs",
        json=_VALID_ANALYSIS,
        headers={"X-Operator-Approval": "true"},
    )
    assert header.status_code == 422
    assert "operator_approval" in header.json()["fields"]


def test_real_app_rejects_client_control_fields() -> None:
    from app.main import app

    client = TestClient(app)
    for field in (
        "allowance_cap",
        "budget",
        "key",
        "force_live",
        "operator_approval",
        "reservation_state",
    ):
        response = client.post(
            "/api/v1/analysis/jobs",
            json={**_VALID_ANALYSIS, field: True},
        )
        assert response.status_code == 422, field
        body = response.json()
        # Middleware or pydantic — never a 2xx, never a secret dump.
        assert "fortyguard_api_key" not in str(body)
        assert public_payload_leaks_secret_names(body) == []


def test_publication_request_rejects_control_fields() -> None:
    base = {
        "contract_version": "hva-signal-two-signal-job-v1",
        "area_id": "phoenix-demo",
        "timezone": "America/Phoenix",
        "granularity_m": 100,
        "data_mode": "replay",
        "signals": {
            "historical": {"analysis_time": "2022-06-30T03:00:00"},
        },
    }
    with pytest.raises(ValidationError):
        TwoSignalPublicationRequest.model_validate({**base, "force_live": True})
    with pytest.raises(ValidationError):
        TwoSignalPublicationRequest.model_validate({**base, "reservation_id": "res_x"})


def test_owned_modules_have_no_vendor_and_keep_live_off() -> None:
    root = Path(__file__).resolve().parents[2]
    for rel in _OWNED:
        source = (root / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "fortyguard" not in alias.name.lower()
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "fortyguard" not in node.module.lower()
        assert "demo_allowance_enabled=True" not in source
        assert "hosted_live_enabled=True" not in source
        assert "hosted_live_real_vendor_enabled=True" not in source


_NF_REMNANTS = (
    "activity_id",
    "vendor_activity_id",
    "cache_bust",
    "bypass_cache",
    "cache_key",
    "no_cache",
    "nocache",
    "spend",
    "force_consume",
    "demo_allowance_store_path",
    "max_open_reservations",
    "reservation_ttl_seconds",
)


@pytest.mark.parametrize("field", _NF_REMNANTS)
def test_live_n_f_names_are_on_live_j_list(field: str) -> None:
    assert classify_client_control_field(field) is not None


def test_wrapped_scenario_privilege_is_422() -> None:
    """Nested extra=allow wrapper must not persist activity_id / cache_bust."""
    from app.main import app

    wrapped = {
        **_VALID_ANALYSIS,
        "scenario": {"wrapper": {"activity_id": "act_stolen", "cache_bust": True}},
    }
    with pytest.raises(ValidationError, match="activity_id|cache_bust"):
        AnalysisRequest.model_validate(wrapped)

    client = TestClient(app)
    response = client.post("/api/v1/analysis/jobs", json=wrapped)
    assert response.status_code == 422
    body = response.json()
    blob = str(body).lower()
    assert "act_stolen" not in blob
    assert "activity_id" in blob or body.get("reason_code") == REASON_CLIENT_FORBIDDEN_FIELD


def test_legitimate_scenario_fields_still_accepted() -> None:
    payload = {
        **_VALID_ANALYSIS,
        "scenario": {"scenario_id": "s1", "intervention_ids": ["i1"]},
    }
    parsed = AnalysisRequest.model_validate(payload)
    assert parsed.scenario is not None
    assert parsed.scenario.scenario_id == "s1"
    assert parsed.scenario.intervention_ids == ["i1"]

