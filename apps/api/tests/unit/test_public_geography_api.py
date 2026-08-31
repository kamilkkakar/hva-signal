"""Unpublished Place + Geography HTTP. Fixtures only. Zero Census download."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.api.optional_geography_router import (
    include_public_geography_routes,
    public_geography_enabled,
)
from app.domain.census_place import PlaceScope
from app.main import app as live_app
from app.schemas.public_geography import (
    FROZEN_RESOLVER_POLICY_ID,
    GeographyIdentityPublic,
    GeographyProvenancePublic,
    GeographyReasonCode,
    PUBLIC_GEOGRAPHY_CONTRACT_VERSION,
    ResolutionOutcome,
)
from app.services.census_place_lookup import CensusPlaceIndex
from app.services.geography_jobs import (
    MaterializeResult,
    area_id_for,
    public_place_from_identity,
    reset_geography_store,
    seed_pending_record,
    seed_terminal_record,
    set_materialize_for_tests,
    set_place_index_for_tests,
    set_tiger_available_for_tests,
    store_size,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "census_place_gazetteer_2025_excerpt.txt"
)
CHICAGO = "1714000"
HONOLULU = "1571550"
PHOENIX_NATIONAL = "0455000"
CHICAGO_AREA = "us-place-1714000-2025-national-place-geography-v1"
PHOENIX_NATIONAL_AREA = "us-place-0455000-2025-national-place-geography-v1"
LIVE_OPENAPI_PATHS = {
    "/health",
    "/ready",
    "/api/v1/areas",
    "/api/v1/areas/{area_id}/geometry",
    "/api/v1/analysis/jobs",
    "/api/v1/analysis/jobs/{job_id}",
    "/api/v1/cities",
    "/api/v1/cities/{city_id}",
    "/api/v1/cities/{city_id}/capabilities",
    "/api/v1/cross-city/metrics",
    "/api/v1/cross-city/query",
    "/api/v1/areas/{area_id}/context",
    "/api/v1/demo/matched-nighttime-window",
    "/api/v1/demo/observed-thermal-instants",
}
OWNED_SOURCES = [
    Path(__file__).resolve().parents[2]
    / "app"
    / "services"
    / "geography_jobs.py",
    Path(__file__).resolve().parents[2] / "app" / "api" / "routes" / "places.py",
    Path(__file__).resolve().parents[2]
    / "app"
    / "api"
    / "routes"
    / "geographies.py",
]


def _enabled_app() -> FastAPI:
    application = FastAPI()
    from app.api.routes.geographies import router as geographies_router
    from app.api.routes.places import router as places_router

    application.include_router(places_router, prefix="/api/v1")
    application.include_router(geographies_router, prefix="/api/v1")
    return application


def _index() -> CensusPlaceIndex:
    return CensusPlaceIndex.from_path(FIXTURE)


def _place(geoid: str):
    identity = _index().get(geoid)
    assert identity is not None
    return public_place_from_identity(identity)


def _zones() -> list[str]:
    return [f"17031{index:06d}" for index in range(1, 26)]


def _supported_identity() -> GeographyIdentityPublic:
    digest_a = "ab" * 32
    digest_b = "cd" * 32
    return GeographyIdentityPublic(
        zone_geoids=_zones(),
        timezone="America/Chicago",
        geometry_sha256=digest_a,
        package_sha256=digest_b,
        zone_geometry_version=(
            "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.PLACE_1714000."
            "NATIONAL_PLACE_GEOGRAPHY_V1.abababab"
        ),
    )


def _supported_provenance() -> GeographyProvenancePublic:
    return GeographyProvenancePublic(
        seed_geoid="17031000001",
        seed_rule_id=(
            "SEED_PLACE_TIGER_INTPT_CONTAINER_ELSE_NEAREST_ELIGIBLE_INTPT_GEOID_ASC_V1"
        ),
    )


def _post_body(place_geoid: str, **extra) -> dict:
    return {
        "contract_version": PUBLIC_GEOGRAPHY_CONTRACT_VERSION,
        "place_geoid": place_geoid,
        **extra,
    }


@pytest.fixture
def geo_client() -> TestClient:
    reset_geography_store()
    set_place_index_for_tests(_index())
    client = TestClient(_enabled_app())
    yield client
    reset_geography_store()


def test_flag_defaults_off() -> None:
    assert public_geography_enabled() is False


def test_live_openapi_unchanged_when_flag_off() -> None:
    schema = live_app.openapi()
    paths = schema.get("paths") or {}
    assert set(paths) == LIVE_OPENAPI_PATHS
    assert "/api/v1/places" not in paths
    assert "/api/v1/geographies" not in paths
    assert "/api/v1/geographies/{area_id}" not in paths


def test_include_hook_is_noop_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HVA_PUBLIC_GEOGRAPHY", "0")
    router = APIRouter()
    include_public_geography_routes(router)
    assert router.routes == []


def test_include_hook_mounts_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HVA_PUBLIC_GEOGRAPHY", "1")
    router = APIRouter()
    include_public_geography_routes(router)
    application = FastAPI()
    application.include_router(router)
    paths = set((application.openapi().get("paths") or {}))
    assert "/api/v1/places" in paths
    assert "/api/v1/places/{place_geoid}" in paths
    assert "/api/v1/geographies" in paths
    assert "/api/v1/geographies/{area_id}" in paths


def test_live_areas_catalog_unchanged() -> None:
    response = TestClient(live_app).get("/api/v1/areas")
    assert response.status_code == 200
    areas = response.json()["areas"]
    assert len(areas) == 1
    assert areas[0]["area_id"] == "phoenix-demo"


def test_search_without_gazetteer_is_503_not_configured() -> None:
    reset_geography_store()
    client = TestClient(_enabled_app())
    response = client.get("/api/v1/places", params={"q": "Chicago"})
    assert response.status_code == 503
    body = response.json()
    assert body["reason"]["code"] == "NOT_CONFIGURED"
    assert store_size() == 0


def test_search_chicago_il_is_identity_only(geo_client: TestClient) -> None:
    before = store_size()
    response = geo_client.get("/api/v1/places", params={"q": "Chicago, IL"})
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == PUBLIC_GEOGRAPHY_CONTRACT_VERSION
    assert len(body["matches"]) == 1
    match = body["matches"][0]
    assert match["place_geoid"] == CHICAGO
    assert match["official_name"] == "Chicago city"
    assert match["resolution_eligible"] is True
    assert body["reason"] is None
    assert store_size() == before


def test_search_springfield_is_ambiguous_200(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/places", params={"q": "Springfield"})
    assert response.status_code == 200
    body = response.json()
    assert body["reason"]["code"] == "AMBIGUOUS_PLACE"
    geoids = {item["place_geoid"] for item in body["matches"]}
    assert "1772000" in geoids
    assert "2970000" in geoids
    assert store_size() == 0


def test_search_phoenix_does_not_collapse_to_demo(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/places", params={"q": "Phoenix"})
    assert response.status_code == 200
    body = response.json()
    assert body["reason"]["code"] == "AMBIGUOUS_PLACE"
    geoids = {item["place_geoid"] for item in body["matches"]}
    assert PHOENIX_NATIONAL in geoids
    assert "phoenix-demo" not in geoids
    assert all(item["place_geoid"] != "phoenix-demo" for item in body["matches"])


def test_search_returns_out_of_scope_honolulu(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/places", params={"q": "1571550"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["place_geoid"] == HONOLULU
    assert body["matches"][0]["scope"] == PlaceScope.HAWAII.value
    assert body["matches"][0]["resolution_eligible"] is False
    assert store_size() == 0


def test_search_empty_matches_is_200(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/places", params={"q": "NotACensusPlace"})
    assert response.status_code == 200
    assert response.json()["matches"] == []
    assert response.json()["reason"] is None


def test_get_place_chicago_predicts_national_area_id(geo_client: TestClient) -> None:
    response = geo_client.get(f"/api/v1/places/{CHICAGO}")
    assert response.status_code == 200
    body = response.json()
    assert body["place"]["place_geoid"] == CHICAGO
    assert body["predicted_area_id"] == CHICAGO_AREA
    assert body["predicted_area_id"] != "phoenix-demo"
    assert store_size() == 0


def test_get_place_unknown_is_404(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/places/1299999")
    assert response.status_code == 404
    assert response.json()["reason"]["code"] == "UNKNOWN_PLACE"


def test_get_place_malformed_is_422(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/places/1714")
    assert response.status_code == 422
    assert response.json()["reason"]["code"] == "INVALID_PLACE_GEOID"


def test_post_honolulu_is_200_unsupported_scope(geo_client: TestClient) -> None:
    response = geo_client.post("/api/v1/geographies", json=_post_body(HONOLULU))
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_outcome"] == "UNSUPPORTED"
    assert body["supported"] is False
    assert body["geography_readiness"] == "UNRESOLVED"
    assert body["reference_readiness"] == "NOT_PREPARED"
    assert body["historical_signal_capable"] is False
    assert body["reason"]["code"] == "UNSUPPORTED_SCOPE"
    assert "city-wide" not in body["reason"]["message"]
    assert "the city" not in body["reason"]["message"].lower()


def test_post_unknown_geoid_is_200_unsupported(geo_client: TestClient) -> None:
    response = geo_client.post("/api/v1/geographies", json=_post_body("1299999"))
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_outcome"] == "UNSUPPORTED"
    assert body["reason"]["code"] == "UNKNOWN_PLACE"
    assert body["reference_readiness"] == "NOT_PREPARED"


def test_post_chicago_without_tiger_is_503_substrate(geo_client: TestClient) -> None:
    response = geo_client.post("/api/v1/geographies", json=_post_body(CHICAGO))
    assert response.status_code == 503
    assert response.json()["reason"]["code"] == "SUBSTRATE_UNAVAILABLE"
    assert store_size() == 0


def test_post_cached_unsupported_is_200_not_500(geo_client: TestClient) -> None:
    seed_terminal_record(
        _place(CHICAGO),
        outcome=ResolutionOutcome.UNSUPPORTED,
        reason_code=GeographyReasonCode.INSUFFICIENT_ELIGIBLE_TRACTS,
    )
    response = geo_client.post("/api/v1/geographies", json=_post_body(CHICAGO))
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_outcome"] == "UNSUPPORTED"
    assert body["reason"]["code"] == "INSUFFICIENT_ELIGIBLE_TRACTS"
    assert body["supported"] is False
    assert body["geography_readiness"] == "UNRESOLVED"
    assert body["reference_readiness"] == "NOT_PREPARED"
    assert "city too small" not in body["reason"]["message"].lower()
    assert "supported city" not in body["reason"]["message"].lower()


def test_post_cached_supported_is_200(geo_client: TestClient) -> None:
    seed_terminal_record(
        _place(CHICAGO),
        outcome=ResolutionOutcome.SUPPORTED,
        reason_code=GeographyReasonCode.GEOGRAPHY_RESOLVED,
        identity=_supported_identity(),
        provenance=_supported_provenance(),
        geometry={"type": "FeatureCollection", "features": []},
    )
    response = geo_client.post("/api/v1/geographies", json=_post_body(CHICAGO))
    assert response.status_code == 200
    body = response.json()
    assert body["area_id"] == CHICAGO_AREA
    assert body["resolution_outcome"] == "SUPPORTED"
    assert body["supported"] is True
    assert body["geography_readiness"] == "GEOGRAPHY_READY"
    assert body["reference_readiness"] == "NOT_PREPARED"
    assert body["snapshot_capable"] is True
    assert body["historical_signal_capable"] is False
    assert body["display_label"].startswith("HVA-Signal 25-zone analysis geography")
    assert "analysis window within" in body["analysis_window_caption"]
    assert FROZEN_RESOLVER_POLICY_ID in body["analysis_window_caption"]
    assert "city-wide" not in body["display_label"]
    assert "the city" not in body["analysis_window_caption"]
    assert body["identity"]["timezone"] == "America/Chicago"
    assert len(body["identity"]["zone_geoids"]) == 25
    assert "ready" not in body
    assert "reference_version" not in body
    assert "q_A" not in body
    assert "fortyguard" not in str(body).lower()


def test_post_joins_in_flight_without_second_worker(geo_client: TestClient) -> None:
    seed_pending_record(_place(CHICAGO))
    first = geo_client.post("/api/v1/geographies", json=_post_body(CHICAGO))
    second = geo_client.post("/api/v1/geographies", json=_post_body(CHICAGO))
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["area_id"] == second.json()["area_id"] == CHICAGO_AREA
    assert first.json()["resolution_outcome"] == "PENDING"
    assert first.json()["geography_readiness"] == "RESOLVING"
    assert first.json()["supported"] is None
    assert first.json()["reference_readiness"] == "NOT_PREPARED"
    assert first.json()["poll"]["interval_ms"] == 1500
    assert store_size() == 1


def test_post_cold_worker_completes_without_census_download(
    geo_client: TestClient,
) -> None:
    def materialize(identity):
        assert identity.place_geoid == CHICAGO
        return MaterializeResult(
            supported=True,
            reason_code=GeographyReasonCode.GEOGRAPHY_RESOLVED,
            message=(
                "Resolved a 25-zone HVA-Signal analysis geography — analysis "
                "window within Chicago city, IL, generated under resolver policy "
                f"{FROZEN_RESOLVER_POLICY_ID}."
            ),
            identity=_supported_identity(),
            provenance=_supported_provenance(),
            geometry={"type": "FeatureCollection", "features": []},
        )

    set_materialize_for_tests(materialize)
    set_tiger_available_for_tests(True)
    response = geo_client.post("/api/v1/geographies", json=_post_body(CHICAGO))
    assert response.status_code == 202
    polled = geo_client.get(f"/api/v1/geographies/{CHICAGO_AREA}")
    assert polled.status_code == 200
    body = polled.json()
    assert body["resolution_outcome"] == "SUPPORTED"
    assert body["geography_readiness"] == "GEOGRAPHY_READY"
    assert body["reference_readiness"] == "NOT_PREPARED"
    assert body["historical_signal_capable"] is False


def test_get_not_started_does_not_enqueue(geo_client: TestClient) -> None:
    response = geo_client.get(f"/api/v1/geographies/{CHICAGO_AREA}")
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_outcome"] == "NOT_STARTED"
    assert body["geography_readiness"] == "UNRESOLVED"
    assert body["supported"] is None
    assert body["reference_readiness"] == "NOT_PREPARED"
    assert store_size() == 0
    again = geo_client.get(f"/api/v1/geographies/{CHICAGO_AREA}")
    assert again.json()["resolution_outcome"] == "NOT_STARTED"
    assert store_size() == 0


def test_get_phoenix_demo_is_404_not_national(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/geographies/phoenix-demo")
    assert response.status_code == 404
    assert response.json()["reason"]["code"] == "AREA_ID_NOT_NATIONAL"


def test_phoenix_national_area_id_never_equals_demo() -> None:
    assert area_id_for(PHOENIX_NATIONAL) == PHOENIX_NATIONAL_AREA
    assert area_id_for(PHOENIX_NATIONAL) != "phoenix-demo"
    assert area_id_for(CHICAGO) == CHICAGO_AREA


def test_get_invalid_area_id_is_422(geo_client: TestClient) -> None:
    response = geo_client.get("/api/v1/geographies/us-place-bad")
    assert response.status_code == 422
    assert response.json()["reason"]["code"] == "INVALID_AREA_ID"


def test_forbidden_post_fields_are_422(geo_client: TestClient) -> None:
    for field, value in (
        ("area_id", CHICAGO_AREA),
        ("spend", 1),
        ("signals", ["historical"]),
        ("fortyguard", True),
        ("reference_version", "x"),
        ("login", "x"),
    ):
        response = geo_client.post(
            "/api/v1/geographies",
            json=_post_body(CHICAGO, **{field: value}),
        )
        assert response.status_code == 422
        assert response.json()["reason"]["code"] == "FORBIDDEN_FIELD"


def test_vintage_and_policy_mismatch_are_422(geo_client: TestClient) -> None:
    vintage = geo_client.post(
        "/api/v1/geographies",
        json=_post_body(CHICAGO, census_vintage="2024"),
    )
    policy = geo_client.post(
        "/api/v1/geographies",
        json=_post_body(CHICAGO, resolver_policy_id="ALG2"),
    )
    version = geo_client.post(
        "/api/v1/geographies",
        json={"contract_version": "nope", "place_geoid": CHICAGO},
    )
    assert vintage.status_code == 422
    assert vintage.json()["reason"]["code"] == "VINTAGE_MISMATCH"
    assert policy.status_code == 422
    assert policy.json()["reason"]["code"] == "UNSUPPORTED_POLICY"
    assert version.status_code == 422
    assert version.json()["reason"]["code"] == "CONTRACT_VERSION_MISMATCH"


def test_copy_fields_follow_01d(geo_client: TestClient) -> None:
    response = geo_client.get(f"/api/v1/geographies/{PHOENIX_NATIONAL_AREA}")
    body = response.json()
    assert body["display_label"] == (
        "HVA-Signal 25-zone analysis geography for Phoenix city, AZ"
    )
    assert body["analysis_window_caption"] == (
        "25-zone HVA-Signal analysis geography — analysis window within "
        "Phoenix city, AZ, generated under resolver policy "
        "NATIONAL_PLACE_GEOGRAPHY_V1"
    )
    blob = f"{body['display_label']} {body['analysis_window_caption']}".lower()
    assert "city-wide" not in blob
    assert "the city" not in blob
    assert "supported city" not in blob


def test_geometry_is_409_before_ready(geo_client: TestClient) -> None:
    response = geo_client.get(f"/api/v1/geographies/{CHICAGO_AREA}/geometry")
    assert response.status_code == 409
    assert response.json()["reason"]["code"] == "GEOGRAPHY_NOT_READY"


def test_geometry_ready_uses_national_path(geo_client: TestClient) -> None:
    seed_terminal_record(
        _place(CHICAGO),
        outcome=ResolutionOutcome.SUPPORTED,
        reason_code=GeographyReasonCode.GEOGRAPHY_RESOLVED,
        identity=_supported_identity(),
        provenance=_supported_provenance(),
        geometry={"type": "FeatureCollection", "features": []},
    )
    response = geo_client.get(f"/api/v1/geographies/{CHICAGO_AREA}/geometry")
    assert response.status_code == 200
    assert response.headers["X-HVA-Area-ID"] == CHICAGO_AREA
    assert response.headers["X-HVA-Area-ID"] != "phoenix-demo"
    assert "application/geo+json" in response.headers["content-type"]


def test_etag_match_returns_304(geo_client: TestClient) -> None:
    seed_terminal_record(
        _place(CHICAGO),
        outcome=ResolutionOutcome.SUPPORTED,
        reason_code=GeographyReasonCode.GEOGRAPHY_RESOLVED,
        identity=_supported_identity(),
        provenance=_supported_provenance(),
    )
    first = geo_client.get(f"/api/v1/geographies/{CHICAGO_AREA}")
    etag = first.headers["etag"]
    second = geo_client.get(
        f"/api/v1/geographies/{CHICAGO_AREA}",
        headers={"If-None-Match": etag},
    )
    assert first.status_code == 200
    assert second.status_code == 304


def test_modules_never_call_vendor_or_analysis_jobs() -> None:
    needles = (
        "process_analysis_job(",
        "execute_job(",
        "from app.core.jobs",
        "from app.integrations",
        "import httpx",
        "urllib.request",
        "requests.get(",
    )
    for path in OWNED_SOURCES:
        text = path.read_text(encoding="utf-8")
        for token in needles:
            assert token not in text, f"{path.name} contains {token}"


def test_reference_readiness_always_not_prepared(geo_client: TestClient) -> None:
    seed_terminal_record(
        _place(CHICAGO),
        outcome=ResolutionOutcome.SUPPORTED,
        reason_code=GeographyReasonCode.GEOGRAPHY_RESOLVED,
        identity=_supported_identity(),
        provenance=_supported_provenance(),
    )
    for path in (
        f"/api/v1/geographies/{CHICAGO_AREA}",
        f"/api/v1/geographies/{PHOENIX_NATIONAL_AREA}",
    ):
        body = geo_client.get(path).json()
        assert body["reference_readiness"] == "NOT_PREPARED"
        assert body["historical_signal_capable"] is False
        if body["geography_readiness"] == "GEOGRAPHY_READY":
            assert body["supported"] is True
