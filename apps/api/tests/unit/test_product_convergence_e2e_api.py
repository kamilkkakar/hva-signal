"""Product-convergence E2E API pins (10_E2E_MATRIX priority cases).

Gated and mocked. Geography HTTP is unpublished on P1 — ambiguous names are
unit-only against the checked-in Gazetteer excerpt. No live TIGER. No synthetic
°C in product builds. Zero FortyGuard sockets.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.domain.census_place import PlaceIdentityFailure, PlaceLookupQuery
from app.domain.demo_allowance import (
    DemoAllowanceDecisionCode,
    DemoRequestIdentity,
    disabled_demo_policy,
)
from app.domain.phoenix_v1 import AREA_ID, ZONE_GEOMETRY_VERSION
from app.domain.requests import AnalysisRequest
from app.domain.signals import ThermalSignalKind
from app.main import app
from app.services.census_place_lookup import CensusPlaceIndex
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.demo_policy_config import demo_allowance_policy_from_settings
from app.services.secret_boundary import public_payload_leaks_secrets

HACKATHON_ROOT = Path(__file__).resolve().parents[4]
AREA_CONFIG_PATH = HACKATHON_ROOT / "data" / "demo" / "phoenix" / "area_config.json"
REFERENCE_PATH = HACKATHON_ROOT / "data" / "phoenix" / "reference" / "observations.jsonl"
GEOMETRY_PATH = HACKATHON_ROOT / "data" / "areas" / "phoenix-demo" / "geometry.geojson"
ORACLE_CSV = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "decision8"
    / "decision8_policy_impact_by_timestamp.csv"
)
GAZETTEER_EXCERPT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "census_place_gazetteer_2025_excerpt.txt"
)
E2E_PLACE_FIXTURE = (
    HACKATHON_ROOT / "tests" / "e2e" / "fixtures" / "place-search-gazetteer.json"
)

PHOENIX_HASHES = {
    "area_config": "df00333a4df900a9762b7be975ed0c36b6e1749c953e9fb4690d9f6e4e02a60a",
    "reference": "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c",
    "geometry": "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    "d8_oracle": "febd0cdd11451eff16e01fe59d26ffeaf94456d94e422ac45045431de1e0a651",
}

INSUFFICIENT_S = 0.0439665471923536
SUFFICIENT_S = 0.13548387096774192
QA_TOLERANCE = 1e-12

P1_PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/api/v1/areas",
    "/api/v1/areas/{area_id}/geometry",
    "/api/v1/analysis/jobs",
    "/api/v1/analysis/jobs/{job_id}",
    "/api/v1/areas/{area_id}/context",
}

UNPUBLISHED_GEOGRAPHY_PATHS = (
    "/api/v1/places",
    "/api/v1/places/{place_geoid}",
    "/api/v1/geographies",
    "/api/v1/geographies/{geography_id}",
)

UNPUBLISHED_JOB_FIELDS = (
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
    "approved",
    "authorize",
    "skip_approval",
    "spend_authorized",
    "demo",
    "demo_test",
    "live_demo",
    "force_live",
    "allowance",
    "demo_budget",
    "internal_key",
    "acquisition_preference",
    "bypass_limit",
    "allowance_remaining",
)

MALFORMED_GEOIDS = ("12", "abc", "17140000", "12abcde", "000000", "1714000X")


class _ForbiddenAdapter:
    version = "forbidden-adapter"

    def fetch_heatmap(self, *args, **kwargs):
        raise AssertionError("NEW FORTYGUARD CALLS must be 0")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _geography_http_published() -> bool:
    paths = (app.openapi().get("paths") or {}).keys()
    return any(path.startswith("/api/v1/places") for path in paths)


def _historical_payload(day: str) -> dict[str, object]:
    return {
        "area_id": AREA_ID,
        "analysis_time": f"{day}T03:00:00",
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }


def _run_oracle(day: str):
    from app.services.orchestrator import run_replay_analysis

    return run_replay_analysis(
        AnalysisRequest.model_validate(_historical_payload(day)),
        adapter=_ForbiddenAdapter(),
    )


def _ranked_fill_count(zones) -> int:
    return sum(1 for zone in zones if getattr(zone, "ranked", None) is True)


# --- PHX-01 hashes ----------------------------------------------------------


def test_phoenix_frozen_artifact_hashes_unchanged() -> None:
    assert AREA_CONFIG_PATH.is_file()
    assert REFERENCE_PATH.is_file()
    assert GEOMETRY_PATH.is_file()
    assert ORACLE_CSV.is_file()
    assert _sha256(AREA_CONFIG_PATH) == PHOENIX_HASHES["area_config"]
    assert _sha256(REFERENCE_PATH) == PHOENIX_HASHES["reference"]
    assert _sha256(GEOMETRY_PATH) == PHOENIX_HASHES["geometry"]
    assert _sha256(ORACLE_CSV) == PHOENIX_HASHES["d8_oracle"]
    assert ZONE_GEOMETRY_VERSION.endswith("3f16870f")
    for path in (AREA_CONFIG_PATH, REFERENCE_PATH, GEOMETRY_PATH, ORACLE_CSV):
        assert "/workforce/" not in path.as_posix()


# --- PHX-02 / PHX-04 oracles ------------------------------------------------


def test_phoenix_2022_07_01_insufficient_oracle() -> None:
    job = _run_oracle("2022-07-01")
    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state == "INSUFFICIENT"
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert abs(job.hazard_spread.observed_spread - INSUFFICIENT_S) <= QA_TOLERANCE
    assert len(job.zones) == 25
    assert _ranked_fill_count(job.zones) == 0
    assert all(zone.ranked is False for zone in job.zones)
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" in job.system_limitations


def test_phoenix_2022_06_30_sufficient_oracle() -> None:
    job = _run_oracle("2022-06-30")
    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state == "SUFFICIENT"
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert abs(job.hazard_spread.observed_spread - SUFFICIENT_S) <= QA_TOLERANCE
    assert len(job.zones) == 25
    assert _ranked_fill_count(job.zones) == 25
    assert all(zone.ranked is True for zone in job.zones)
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" not in job.system_limitations


@pytest.mark.parametrize(
    ("day", "state", "expected_s", "ranked_fills"),
    [
        ("2022-07-01", "INSUFFICIENT", INSUFFICIENT_S, 0),
        ("2022-06-30", "SUFFICIENT", SUFFICIENT_S, 25),
    ],
)
def test_phoenix_oracles_via_public_jobs_http(
    day: str, state: str, expected_s: float, ranked_fills: int
) -> None:
    from app.core.jobs import job_store

    job_store.reset()
    client = TestClient(app)
    created = client.post("/api/v1/analysis/jobs", json=_historical_payload(day))
    assert created.status_code == 202
    body = client.get(f"/api/v1/analysis/jobs/{created.json()['job_id']}").json()
    assert body["status"] == "complete"
    result = body["result"]
    assert result["thermal_differentiation_state"] == state
    assert result["reference_quality"] == "FULL_REFERENCE"
    assert abs(result["hazard_spread"]["observed_spread"] - expected_s) <= QA_TOLERANCE
    zones = result["zones"]
    assert len(zones) == 25
    assert sum(1 for zone in zones if zone["ranked"] is True) == ranked_fills
    assert result["area_config_sha256"] == PHOENIX_HASHES["area_config"]
    blob = str(body).lower()
    assert "fortyguard_api_key" not in blob
    assert "for fortyguard live" not in blob
    assert "allowance_remaining" not in blob
    job_store.reset()


# --- ACC-01 accountless -----------------------------------------------------


def test_accountless_public_surface_has_no_login() -> None:
    schema = app.openapi()
    paths = schema.get("paths") or {}
    assert set(paths) == P1_PUBLIC_PATHS
    blob = str(schema).lower()
    assert "login" not in blob
    assert "/oauth" not in blob
    assert "signup" not in blob
    assert "fortyguard_api_key" not in blob
    assert "allowance_remaining" not in blob
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
    ready = TestClient(app).get("/ready").json()
    assert public_payload_leaks_secrets(ready) == []
    assert "fortyguard_api_key" not in ready
    assert "allowance_remaining" not in ready


# --- ACC-03 / ACC-04 allowance disabled -------------------------------------


def test_default_demo_allowance_is_disabled() -> None:
    assert Settings.model_fields["demo_allowance_enabled"].default is False
    assert Settings.model_fields["demo_allowance_max_total_units"].default == 0
    policy = disabled_demo_policy()
    assert policy.enabled is False
    assert policy.max_total_acquisition_units == 0
    loaded = demo_allowance_policy_from_settings(
        Settings.model_construct(demo_allowance_enabled=False)
    )
    assert loaded.enabled is False


def test_disabled_allowance_cannot_reserve() -> None:
    ledger = InMemoryDemoAllowanceLedger(disabled_demo_policy())
    decision = ledger.try_reserve(
        DemoRequestIdentity.model_validate(
            {
                "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
                "request_fingerprint": "aa" * 32,
                "geometry_sha256": "bb" * 32,
                "area_id": AREA_ID,
            }
        ),
        planned_units=1,
        now=datetime.now(timezone.utc),
    )
    assert decision.code == DemoAllowanceDecisionCode.ALLOWANCE_DISABLED
    assert decision.spend_authorized is False


# --- NAT-08 public /areas still Phoenix-only --------------------------------


def test_public_areas_remain_phoenix_demo_only() -> None:
    client = TestClient(app)
    body = client.get("/api/v1/areas").json()
    assert [area["area_id"] for area in body["areas"]] == [AREA_ID]
    chicago = "us-place-1714000-2025-national-place-geography-v1"
    assert client.get(f"/api/v1/areas/{chicago}/geometry").status_code == 404
    national_phoenix = "us-place-0455000-2025-national-place-geography-v1"
    assert client.get(f"/api/v1/areas/{national_phoenix}/geometry").status_code == 404


# --- Geography unpublished / SRCH unit-only ---------------------------------


def test_places_and_geographies_unpublished_on_p1() -> None:
    if _geography_http_published():
        pytest.skip("geography HTTP published — HTTP matrix belongs to the publication gate")
    paths = app.openapi().get("paths") or {}
    for path in UNPUBLISHED_GEOGRAPHY_PATHS:
        assert path not in paths
    client = TestClient(app)
    assert client.get("/api/v1/places", params={"q": "Springfield"}).status_code == 404
    assert client.get("/api/v1/places/1714000").status_code == 404
    assert client.post("/api/v1/geographies", json={"place_geoid": "1714000"}).status_code == 404


@pytest.mark.skipif(
    _geography_http_published(),
    reason="geography HTTP published; use HTTP SRCH cases instead of unit-only",
)
def test_ambiguous_springfield_is_unit_only_while_geography_off() -> None:
    index = CensusPlaceIndex.from_path(GAZETTEER_EXCERPT)
    result = index.resolve(PlaceLookupQuery(raw_text="Springfield"))
    assert result.ok is False
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    assert result.identity is None
    geoids = {candidate.place_geoid for candidate in result.candidates}
    assert "1772000" in geoids
    assert "2970000" in geoids


@pytest.mark.skipif(
    _geography_http_published(),
    reason="geography HTTP published; use HTTP SRCH cases instead of unit-only",
)
def test_ambiguous_phoenix_does_not_bind_phoenix_demo() -> None:
    index = CensusPlaceIndex.from_path(GAZETTEER_EXCERPT)
    result = index.resolve(PlaceLookupQuery(raw_text="Phoenix"))
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    assert result.identity is None
    geoids = {candidate.place_geoid for candidate in result.candidates}
    assert "0455000" in geoids
    assert AREA_ID not in geoids
    assert "phoenix-demo" not in {candidate.place_geoid for candidate in result.candidates}


# --- SRCH-05 malformed GEOID ------------------------------------------------


@pytest.mark.parametrize("geoid", MALFORMED_GEOIDS)
def test_malformed_geoid_is_invalid_place_id(geoid: str) -> None:
    from app.domain.census_place import validate_place_geoid_format

    assert validate_place_geoid_format(geoid) is PlaceIdentityFailure.INVALID_PLACE_GEOID
    index = CensusPlaceIndex.from_path(GAZETTEER_EXCERPT)
    result = index.resolve(PlaceLookupQuery(place_geoid=geoid))
    assert result.ok is False
    assert result.failure is PlaceIdentityFailure.INVALID_PLACE_GEOID
    assert result.identity is None


def test_malformed_geoid_http_does_not_resolve_a_place() -> None:
    client = TestClient(app)
    for geoid in MALFORMED_GEOIDS:
        response = client.get(f"/api/v1/places/{geoid}")
        assert response.status_code in {400, 404, 422}


# --- MAL-03 two-signal unpublished still 422 on P1 --------------------------


@pytest.mark.parametrize("field", UNPUBLISHED_JOB_FIELDS)
def test_two_signal_unpublished_fields_still_422_on_p1(field: str) -> None:
    payload = {**_historical_payload("2022-06-30"), field: True}
    with pytest.raises(ValidationError, match="unpublished two-signal"):
        AnalysisRequest.model_validate(payload)
    response = TestClient(app).post("/api/v1/analysis/jobs", json=payload)
    assert response.status_code == 422


# --- Fixture honesty: no fake product °C ------------------------------------


def test_e2e_place_fixture_is_identity_only_no_product_celsius() -> None:
    assert E2E_PLACE_FIXTURE.is_file()
    blob = E2E_PLACE_FIXTURE.read_text(encoding="utf-8")
    text = blob.casefold()
    assert "°c" not in text
    assert "celsius" not in text
    assert "q_a" not in text
    assert "observed_spread" not in text
    assert "hazard_spread" not in text
    assert '"_fortyguard_calls": 0' in blob
    assert '"_not_product_evidence": true' in blob
    assert '"thermal_product_evidence": false' in blob
    assert '"invented_mean_temperature_c": false' in blob
