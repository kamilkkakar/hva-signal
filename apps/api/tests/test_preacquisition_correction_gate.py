"""Pre-acquisition correction gate tests — zero vendor calls."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.multicity.city_catalog import resolve_city_aoi
from app.domain.multicity.cross_city_acs import load_city_acs
from app.domain.multicity.cross_city_canopy import (
    CROSS_CITY_CANOPY_STATUS,
    canopy_pct_for,
    cross_city_canopy_contract,
)
from app.domain.multicity.geography import CROSS_CITY_COMPARISON_GEOGRAPHY_V1
from app.domain.multicity.observation_clock import (
    CROSS_CITY_OBSERVATION_V1,
    resolve_city_observation_clock,
)
from app.domain.multicity.type1_live import (
    TYPE1_LOCAL_COMPLEXITY_LABEL,
    dry_run_type1_preflight,
    estimate_type1_local_complexity_units,
)
from app.domain.multicity.validation_package import (
    CROSS_CITY_VALIDATION_PACKAGE_V2,
    PHOENIX_REUSE_PROOF,
    build_cross_city_validation_package,
)
from app.main import app

REPO = Path(__file__).resolve().parents[3]
CROSS_CITY = REPO / "data" / "areas" / "cross-city"
CITIES = ("phoenix", "las_vegas", "tucson", "los_angeles")


def test_geography_determinism_and_frozen_hashes() -> None:
    index = json.loads((CROSS_CITY / "INDEX.json").read_text(encoding="utf-8"))
    assert index["contract"] == CROSS_CITY_COMPARISON_GEOGRAPHY_V1
    for city in index["cities"]:
        assert city["analysis_area_count"] == 25
        assert len(city["exact_tract_geoids"]) == 25
        assert len(city["combined_geometry_hash"]) == 64
        assert len(city["area_config_hash"]) == 64
        freeze = json.loads(
            (CROSS_CITY / city["city_id"] / "freeze.json").read_text(encoding="utf-8")
        )
        assert freeze["combined_geometry_hash"] == city["combined_geometry_hash"]
        geom = json.loads(
            (CROSS_CITY / city["city_id"] / "geometry.geojson").read_text(encoding="utf-8")
        )
        assert len(geom["features"]) == 25


def test_phoenix_reuse_coverage_is_none() -> None:
    assert PHOENIX_REUSE_PROOF["reusable"] == "NO"
    assert PHOENIX_REUSE_PROOF["new_phoenix_call_needed"] is True
    demo = json.loads(
        (REPO / "data" / "areas" / "phoenix-demo" / "geometry.geojson").read_text(
            encoding="utf-8"
        )
    )
    xcity = json.loads(
        (CROSS_CITY / "phoenix" / "geometry.geojson").read_text(encoding="utf-8")
    )
    demo_ids = {f["properties"]["GEOID"] for f in demo["features"]}
    x_ids = {f["properties"]["GEOID"] for f in xcity["features"]}
    assert demo_ids.isdisjoint(x_ids)


def test_cost_estimator_units_are_not_credits() -> None:
    units = estimate_type1_local_complexity_units(
        partition_count=1, expected_tiles_estimate=5617
    )
    assert units == 3
    preflight = dry_run_type1_preflight(
        {"city": "Phoenix", "target_local": datetime(2024, 7, 8, 15, 0, 0)}
    )
    estimate = preflight["local_complexity_estimate"]
    assert estimate["label"] == TYPE1_LOCAL_COMPLEXITY_LABEL
    assert estimate["units"] == "dimensionless_local_complexity_units"
    assert estimate["not_vendor_credits"] is True


def test_mislabelled_credits_regression() -> None:
    package = build_cross_city_validation_package()
    assert package["package_version"] == CROSS_CITY_VALIDATION_PACKAGE_V2
    assert package["total_new_calls_required"] == 4
    for city in package["cities"]:
        assert city["new_vendor_call_required"] is True
        assert city["cost_model_output"]["label"] == TYPE1_LOCAL_COMPLEXITY_LABEL


def test_acs_all_city_coverage() -> None:
    for city_id in CITIES:
        doc = load_city_acs(city_id)
        assert doc["tract_count"] == 25
        assert doc["missing_population_geoids"] == []
        income_present = 0
        for _geoid, row in doc["rows"].items():
            assert row["population"]["vintage"] == "ACS 5-year 2020-2024"
            assert row["population"]["estimate"] is not None
            assert row["homes_built_before_1980"]["estimate"] is not None
            assert row["one_person_households"]["estimate"] is not None
            if row["median_household_income"]["estimate"] is not None:
                income_present += 1
        assert income_present >= 20


def test_national_canopy_all_city() -> None:
    contract = cross_city_canopy_contract()
    assert contract["contract_version"] == "CROSS_CITY_CANOPY_CONTRACT_V1"
    assert contract["status"] == CROSS_CITY_CANOPY_STATUS
    assert contract["silent_substitute_forbidden"] is True
    for city_id in CITIES:
        values = [
            canopy_pct_for(city_id, geoid)
            for geoid in json.loads(
                (CROSS_CITY / city_id / "freeze.json").read_text(encoding="utf-8")
            )["exact_tract_geoids"]
        ]
        assert all(v is not None for v in values)
        assert min(v for v in values if v is not None) >= 0
        assert max(v for v in values if v is not None) <= 100


def test_provider_aoi_is_union_polygon_not_bbox() -> None:
    for name in ("Phoenix", "Las Vegas", "Tucson", "Los Angeles"):
        config = resolve_city_aoi(name)
        assert config.analysis_geography_version == "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1"
        assert config.comparison_geography_version == CROSS_CITY_COMPARISON_GEOGRAPHY_V1
        assert config.polygon_aoi["type"] in {"Polygon", "MultiPolygon"}
        assert "CITY_BBOX" not in config.analysis_geography_version


def test_comparison_clock_dst() -> None:
    phoenix = resolve_city_observation_clock("phoenix")
    vegas = resolve_city_observation_clock("las_vegas")
    assert phoenix.timezone == "America/Phoenix"
    assert vegas.timezone == "America/Los_Angeles"
    assert phoenix.dst_active is False
    assert vegas.dst_active is True
    assert phoenix.provider_payload_local_valid_time == "2024-07-08T15:00"
    assert vegas.utc_timestamp.endswith("+00:00")
    assert vegas.utc_timestamp.startswith("2024-07-08T22:00:00")
    assert CROSS_CITY_OBSERVATION_V1


def test_cross_city_metrics_binds_non_thermal_for_all_cities() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/cross-city/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["axes"] == {
        "x": "temperature_c",
        "y": "median_household_income",
        "size": "population",
        "fill": "tree_canopy_pct",
    }
    assert len(body["rows"]) == 100
    assert body["summary"]["included_count"] >= 20
    for city_id in CITIES:
        rows = [row for row in body["rows"] if row["city_id"] == city_id]
        assert len(rows) == 25
        assert all(row["population"] is not None for row in rows)
        assert sum(row["median_household_income"] is not None for row in rows) >= 20
        assert all(row["tree_canopy_pct"] is not None for row in rows)
        assert all(row["label"].startswith("Comparison Area ") for row in rows)
        if city_id == "los_angeles":
            assert all(row["temperature_c"] is not None for row in rows)
        else:
            assert all(row["temperature_c"] is None for row in rows)

    queried = client.get(
        "/api/v1/cross-city/query",
        params={
            "x": "population",
            "y": "tree_canopy_pct",
            "size": "population",
            "fill": "tree_canopy_pct",
        },
    )
    assert queried.status_code == 200
    qbody = queried.json()
    assert qbody["summary"]["included_count"] == 100
    assert qbody["summary"]["missing_fill_count"] == 0


def test_missing_thermal_is_disclosed_not_fabricated() -> None:
    client = TestClient(app)
    rows = client.get("/api/v1/cross-city/metrics").json()["rows"]
    phoenix = next(row for row in rows if row["city_id"] == "phoenix")
    assert phoenix["temperature_c"] is None
    assert "synthetic" in phoenix["missing_reasons"]["temperature_c"].lower()
    assert phoenix["coverage_flags"]["temperature_c"] is False
    la = next(row for row in rows if row["city_id"] == "los_angeles")
    assert la["temperature_c"] is not None
    assert "temperature_c" not in la["missing_reasons"]
