#!/usr/bin/env python3
"""Materialize Yuma's validation-only native tract package from Census TIGER.

This is a free, no-purchase geometry step. It deliberately does not call
FortyGuard and does not add Yuma to the operational city catalog.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from shapely.geometry import Point, mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "apps" / "api"))

from app.services.place_geography_resolver import ELIGIBILITY_RULE_ID  # noqa: E402
from scripts.materialize_cross_city_geographies import (  # noqa: E402
    _download,
    load_place,
    load_tracts,
)

PLACE_GEOID = "0485540"
STATE_FIPS = "04"
CENSUS_VINTAGE = "2025"
SOURCE_RELEASE_DATE = "2025-09-23"
PLACE_URL = "https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_04_place.zip"
TRACT_URL = "https://www2.census.gov/geo/tiger/TIGER2025/TRACT/tl_2025_04_tract.zip"
PLACE_ZIP_SHA256 = "7c52a87725285cd6e6655daf6cf733c37942256bc7e190ac01ddb174a0acd330"
TRACT_ZIP_SHA256 = "5fb6d80990b05811f5b8c6fca80b386611899add7c0178ac06366033f910fd19"
SELECTION_POLICY = f"{ELIGIBILITY_RULE_ID}.RETAIN_ALL"

CACHE = REPO / ".cache" / "geography" / "yuma_native"
OUT = REPO / "data" / "areas" / "validation" / "yuma_az"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _verify_source(path: Path, expected: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        raise RuntimeError(f"source hash mismatch for {path.name}: {actual}")


def materialize() -> dict[str, Any]:
    place_zip = _download(PLACE_URL, CACHE / "tl_2025_04_place.zip")
    tract_zip = _download(TRACT_URL, CACHE / "tl_2025_04_tract.zip")
    _verify_source(place_zip, PLACE_ZIP_SHA256)
    _verify_source(tract_zip, TRACT_ZIP_SHA256)

    place = load_place(place_zip, PLACE_GEOID)
    native = sorted(
        (
            tract
            for tract in load_tracts(tract_zip, STATE_FIPS)
            if tract.aland > 0
            and place.geometry.covers(Point(tract.intpt_lon, tract.intpt_lat))
        ),
        key=lambda tract: tract.geoid,
    )
    if not native:
        raise RuntimeError("Yuma native eligibility resolved no Census tracts")

    place_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "GEOID": PLACE_GEOID,
                    "NAME": "Yuma",
                    "STATEFP": STATE_FIPS,
                    "CENSUS_VINTAGE": CENSUS_VINTAGE,
                    "INTPTLAT": f"{place.intpt_lat:+.7f}",
                    "INTPTLON": f"{place.intpt_lon:+.7f}",
                },
                "geometry": mapping(place.geometry),
            }
        ],
    }
    tract_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "GEOID": tract.geoid,
                    "STATEFP": tract.geoid[:2],
                    "COUNTYFP": tract.geoid[2:5],
                    "TRACTCE": tract.geoid[5:],
                    "ALAND": tract.aland,
                    "INTPTLAT": f"{tract.intpt_lat:+.7f}",
                    "INTPTLON": f"{tract.intpt_lon:+.7f}",
                },
                "geometry": mapping(tract.geometry),
            }
            for tract in native
        ],
    }

    manifest = {
        "schema_version": "YUMA_NATIVE_SMALL_PLACE_VALIDATION_V1",
        "jurisdiction_id": "yuma_az",
        "display_name": "Yuma",
        "place_geoid": PLACE_GEOID,
        "census_vintage": CENSUS_VINTAGE,
        "source_release_date": SOURCE_RELEASE_DATE,
        "selection_policy": SELECTION_POLICY,
        "selection_explanation": (
            "Retain every positive-land-area tract whose official TIGER INTPT is "
            "covered by the official Yuma place geometry. Do not prune disconnected "
            "components, pad, or impose a 25-tract target."
        ),
        "native_eligible_tract_count": len(native),
        "retained_tract_count": len(native),
        "padding_tract_count": 0,
        "target_count_applied": False,
        "exact_tract_geoids": [tract.geoid for tract in native],
        "place_geometry_sha256": _payload_sha256(place_collection),
        "tract_geometry_sha256": _payload_sha256(tract_collection),
        "sources": {
            "place": {"url": PLACE_URL, "zip_sha256": PLACE_ZIP_SHA256},
            "tract": {"url": TRACT_URL, "zip_sha256": TRACT_ZIP_SHA256},
        },
        "operationally_selectable": False,
        "thermal_acquisition_authorized": False,
        "thermal_evidence_state": "NOT_YET_TESTED",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "place_geometry.geojson").write_text(
        json.dumps(place_collection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "native_tracts.geojson").write_text(
        json.dumps(tract_collection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(materialize(), indent=2, sort_keys=True))
