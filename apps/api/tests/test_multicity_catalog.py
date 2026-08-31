from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.multicity.capabilities import negotiate_capabilities
from app.domain.multicity.catalog import get_city, list_cities, public_city_selector_allowlist
from app.domain.multicity.city_config import CapabilityStatus, CityId
from app.domain.multicity.geography import (
    CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
    MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
    audit_phoenix_cross_city_compatibility,
)
from app.main import app


def test_catalog_allowlist_is_frozen_to_four_cities() -> None:
    cities = list_cities()
    assert [city.city_id for city in cities] == [
        CityId.PHOENIX,
        CityId.LAS_VEGAS,
        CityId.TUCSON,
        CityId.LOS_ANGELES,
    ]
    assert get_city("phoenix").area_id == "phoenix-demo"
    assert get_city("phoenix").analysis_geography_version == MULTI_CITY_ANALYSIS_GEOGRAPHY_V1
    assert (
        get_city("phoenix").comparison_geography_version
        == CROSS_CITY_COMPARISON_GEOGRAPHY_V1
    )


def test_public_selector_allowlist_contains_expected_timezones_and_colors() -> None:
    selector = public_city_selector_allowlist()
    assert [item.city_id for item in selector] == [
        CityId.PHOENIX,
        CityId.LAS_VEGAS,
        CityId.TUCSON,
        CityId.LOS_ANGELES,
    ]
    assert get_city("phoenix").timezone == "America/Phoenix"
    assert get_city("tucson").timezone == "America/Phoenix"
    assert get_city("los_angeles").timezone == "America/Los_Angeles"
    assert get_city("phoenix").outline_color == "#2F6FED"
    assert get_city("las_vegas").outline_color == "#0D9488"
    assert get_city("tucson").outline_color == "#7B4DDB"
    assert get_city("los_angeles").outline_color == "#E67E22"


def test_capability_negotiation_stays_conservative_outside_phoenix() -> None:
    phoenix = negotiate_capabilities("phoenix")
    vegas = negotiate_capabilities("las_vegas")
    assert phoenix["selected_time_thermal"] == CapabilityStatus.AVAILABLE
    assert phoenix["local_canopy"] == CapabilityStatus.AVAILABLE
    assert vegas["selected_time_thermal"] == CapabilityStatus.READY_FOR_ACQUISITION
    assert vegas["matched_nighttime"] == CapabilityStatus.UNAVAILABLE
    assert vegas["cross_city_explorer"] == CapabilityStatus.PARTIAL


def test_phoenix_geography_distinction_is_explicit() -> None:
    audit = audit_phoenix_cross_city_compatibility()
    assert audit.phoenix_compatible is False
    assert "PHX_DEMO_AOI_POLICY_V1" in audit.reason
    assert "CROSS_CITY_COMPARISON_GEOGRAPHY_V1" in audit.reason


def test_cities_routes_publish_allowlist_and_capabilities() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/cities")
    assert response.status_code == 200
    body = response.json()
    assert [city["city_id"] for city in body["cities"]] == [
        "phoenix",
        "las_vegas",
        "tucson",
        "los_angeles",
    ]

    detail = client.get("/api/v1/cities/phoenix")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["area_id"] == "phoenix-demo"
    assert payload["local_geography_version"] == "PHX_DEMO_AOI_POLICY_V1"

    caps = client.get("/api/v1/cities/phoenix/capabilities")
    assert caps.status_code == 200
    assert caps.json()["capabilities"]["selected_time_thermal"] == "AVAILABLE"


def test_cross_city_metrics_returns_real_phoenix_rows_and_disclosed_gaps() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/cross-city/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "included_count": 25,
        "omitted_axis_count": 3,
        "missing_fill_count": 25,
    }
    phoenix_rows = [row for row in body["rows"] if row["city_id"] == "phoenix"]
    assert len(phoenix_rows) == 25
    seed = next(row for row in phoenix_rows if row["zone_id"] == "04013107401")
    assert seed["label"] == "Census Tract 1074.01"
    assert seed["temperature_c"] == 42.32812109375
    assert seed["median_household_income"] is not None
    assert seed["population"] is not None
    assert seed["tree_canopy_pct"] is None
    assert seed["comparison_clock"] == {
        "local_date": "2024-07-08",
        "local_time": "15:00",
        "policy": "same_local_date_time",
    }
    assert "not reused" in seed["missing_reasons"]["tree_canopy_pct"]
    missing_city = next(row for row in body["rows"] if row["city_id"] == "las_vegas")
    assert missing_city["zone_id"] is None
    assert "not packaged" in missing_city["missing_reasons"]["temperature_c"]


def test_cross_city_query_validates_axes() -> None:
    client = TestClient(app)
    ok = client.get(
        "/api/v1/cross-city/query",
        params={
            "x": "temperature_c",
            "y": "median_household_income",
            "size": "population",
            "fill": "temperature_c",
        },
    )
    assert ok.status_code == 200
    assert ok.json()["summary"]["missing_fill_count"] == 0

    bad = client.get(
        "/api/v1/cross-city/query",
        params={
            "x": "invalid_axis",
            "y": "median_household_income",
            "size": "population",
            "fill": "temperature_c",
        },
    )
    assert bad.status_code == 422


def test_live_defaults_still_off() -> None:
    assert Settings.model_fields["demo_allowance_enabled"].default is False
    assert Settings.model_fields["hosted_live_enabled"].default is False
    assert Settings.model_fields["hosted_live_real_vendor_enabled"].default is False
    assert Settings.model_fields["hva_public_two_signal"].default is False

