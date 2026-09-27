from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, shape

REPO = Path(__file__).resolve().parents[3]
PACKAGE = REPO / "data" / "areas" / "validation" / "yuma_az"

EXPECTED_GEOIDS = [
    "04027000200",
    "04027000301",
    "04027000302",
    "04027000402",
    "04027000502",
    "04027000600",
    "04027000700",
    "04027000800",
    "04027000901",
    "04027000902",
    "04027000903",
    "04027000907",
    "04027000909",
    "04027000910",
    "04027001001",
    "04027001003",
    "04027001004",
    "04027001100",
    "04027001200",
    "04027010911",
    "04027011116",
    "04027011117",
    "04027011120",
    "04027011121",
    "04027011700",
    "04027980006",
]


def _load(name: str) -> dict:
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def _canonical_sha256(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_yuma_manifest_retains_every_native_eligible_tract_without_padding() -> None:
    manifest = _load("manifest.json")
    tracts = _load("native_tracts.geojson")

    assert manifest["schema_version"] == "YUMA_NATIVE_SMALL_PLACE_VALIDATION_V1"
    assert manifest["jurisdiction_id"] == "yuma_az"
    assert manifest["place_geoid"] == "0485540"
    assert manifest["census_vintage"] == "2025"
    assert manifest["native_eligible_tract_count"] == 26
    assert manifest["retained_tract_count"] == 26
    assert manifest["padding_tract_count"] == 0
    assert manifest["target_count_applied"] is False

    geoids = [feature["properties"]["GEOID"] for feature in tracts["features"]]
    assert geoids == EXPECTED_GEOIDS
    assert manifest["exact_tract_geoids"] == EXPECTED_GEOIDS
    assert len(geoids) == len(set(geoids))


def test_yuma_tracts_follow_official_intpt_within_place_contract() -> None:
    place = _load("place_geometry.geojson")
    tracts = _load("native_tracts.geojson")
    place_shape = shape(place["features"][0]["geometry"])

    for feature in tracts["features"]:
        properties = feature["properties"]
        intpt = Point(float(properties["INTPTLON"]), float(properties["INTPTLAT"]))
        assert float(properties["ALAND"]) > 0
        assert place_shape.covers(intpt), properties["GEOID"]


def test_yuma_package_is_versioned_and_cannot_authorize_operations() -> None:
    manifest = _load("manifest.json")
    place = _load("place_geometry.geojson")
    tracts = _load("native_tracts.geojson")

    assert manifest["operationally_selectable"] is False
    assert manifest["thermal_acquisition_authorized"] is False
    assert manifest["thermal_evidence_state"] == "NOT_YET_TESTED"
    assert manifest["place_geometry_sha256"] == _canonical_sha256(place)
    assert manifest["tract_geometry_sha256"] == _canonical_sha256(tracts)
    assert manifest["sources"]["place"]["url"].startswith(
        "https://www2.census.gov/geo/tiger/TIGER2025/"
    )
    assert manifest["sources"]["tract"]["url"].startswith(
        "https://www2.census.gov/geo/tiger/TIGER2025/"
    )
