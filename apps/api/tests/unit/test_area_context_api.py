"""Gated GET /areas/{area_id}/context reads cache only. No score. No acquisition."""

from __future__ import annotations

import pytest

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.api.optional_context_router import (
    include_public_context_routes,
    public_context_enabled,
)
from app.main import app as live_app
from app.services.vulnerability_preparedness.cache import EXPECTED_ZONE_COUNT
from app.services.vulnerability_preparedness.paths import context_bundle_path

LIVE_OPENAPI_PATHS = {
    "/health",
    "/ready",
    "/api/v1/areas",
    "/api/v1/areas/{area_id}/geometry",
    "/api/v1/analysis/jobs",
    "/api/v1/analysis/jobs/{job_id}",
    "/api/v1/areas/{area_id}/context",
    "/api/v1/demo/matched-nighttime-window",
    "/api/v1/demo/observed-thermal-instants",
}


def _enabled_app() -> FastAPI:
    application = FastAPI()
    from app.api.routes.area_context import router as context_router

    application.include_router(context_router, prefix="/api/v1")
    return application


def test_public_context_defaults_on() -> None:
    assert public_context_enabled() is True


def test_live_openapi_includes_context_path() -> None:
    paths = set((live_app.openapi().get("paths") or {}))
    assert paths == LIVE_OPENAPI_PATHS
    assert "/api/v1/areas/{area_id}/context" in paths
    assert len(paths) == 9


def test_gated_include_off_adds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HVA_PUBLIC_CONTEXT", "0")
    router = APIRouter()
    include_public_context_routes(router)
    assert [getattr(route, "path", "") for route in router.routes] == []


def test_get_area_context_returns_story_ready_fields() -> None:
    if not context_bundle_path().is_file():
        return
    client = TestClient(_enabled_app())
    response = client.get("/api/v1/areas/phoenix-demo/context")
    assert response.status_code == 200
    body = response.json()
    assert body["area_id"] == "phoenix-demo"
    assert body["combined_score_authorized"] is False
    assert body["vulnerability_score_authorized"] is False
    assert "What is the vulnerability score?" in body["unsupported_questions"]
    assert body["thermal_evidence_status"] == "UNKNOWN"
    assert body["map_modes"] == ["THERMAL", "TREE_CANOPY", "INCOME", "OLDER_HOUSING"]
    assert len(body["zones"]) == EXPECTED_ZONE_COUNT
    assert "acs" not in body
    assert body["cooling_inventory"]["coverage"] == "partial"
    assert body["cooling_inventory"]["sites_in_window"] == 4
    assert "no cooling resource exists" in body["cooling_inventory"]["note"]
    dumped = str(body).lower()
    assert "vulnerability = " not in dumped
    assert "b01001_e001" not in dumped


def test_get_area_context_selected_zone_story() -> None:
    if not context_bundle_path().is_file():
        return
    client = TestClient(_enabled_app())
    response = client.get(
        "/api/v1/areas/phoenix-demo/context",
        params={"zone_id": "04013107401"},
    )
    assert response.status_code == 200
    selected = response.json()["selected"]
    assert selected["census_tract_geoid"] == "04013107401"
    assert selected["thermal_evidence_status"] == "UNKNOWN"
    assert len(selected["context_facts"]) <= 6
    assert selected["vulnerability_score_authorized"] is False
    assert any("verify" in item.lower() or "confirm" in item.lower() for item in selected["direction"])
    text = selected["story"]["thermal_evidence"]
    assert "referenced separately" not in " ".join(text).lower()


def test_unknown_area_and_zone_are_404() -> None:
    client = TestClient(_enabled_app())
    assert client.get("/api/v1/areas/not-an-area/context").status_code == 404
    if not context_bundle_path().is_file():
        return
    assert (
        client.get(
            "/api/v1/areas/phoenix-demo/context",
            params={"zone_id": "99999999999"},
        ).status_code
        == 404
    )


def test_route_module_does_not_acquire() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2] / "app" / "api" / "routes" / "area_context.py"
    ).read_text(encoding="utf-8")
    assert "httpx" not in source
    assert "urlopen" not in source
    assert "fortyguard" not in source.lower()
    assert "ingest_phoenix_context" not in source
