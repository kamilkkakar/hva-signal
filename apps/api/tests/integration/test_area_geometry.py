"""Versioned geometry delivery. Metadata headers + exact-byte body."""

from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)
from app.domain.phoenix_v1 import AREA_ID, ZONE_GEOMETRY_VERSION
from app.main import app

client = TestClient(app)

EXPECTED_GEOMETRY_SHA256 = (
    "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"
)
GEOMETRY_ZONE_ID_PROPERTY = "GEOID"


def _reference_geoids() -> set[str]:
    ids: set[str] = set()
    path = hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(str(json.loads(line)["geoid"]))
    return ids


def test_phoenix_geometry_endpoint_returns_exact_frozen_bytes() -> None:
    response = client.get(f"/api/v1/areas/{AREA_ID}/geometry")
    assert response.status_code == 200
    content_type = response.headers["content-type"]
    assert content_type.startswith("application/geo+json")
    tracked = (
        hackathon_root() / "data" / "areas" / "phoenix-demo" / "geometry.geojson"
    ).read_bytes()
    assert response.content == tracked
    assert hashlib.sha256(response.content).hexdigest() == EXPECTED_GEOMETRY_SHA256
    payload = json.loads(response.content.decode("utf-8"))
    assert payload["type"] == "FeatureCollection"
    features = payload["features"]
    assert len(features) == 25
    zone_ids = [str(feature["properties"][GEOMETRY_ZONE_ID_PROPERTY]) for feature in features]
    assert len(set(zone_ids)) == 25
    assert set(zone_ids) == _reference_geoids()
    config = load_frozen_phoenix_v1_area_config()
    assert response.headers["x-hva-area-id"] == AREA_ID
    assert response.headers["x-hva-zone-geometry-version"] == config.zone_geometry_version
    assert response.headers["x-hva-zone-geometry-version"] == ZONE_GEOMETRY_VERSION
    assert response.headers["x-hva-geometry-sha256"] == EXPECTED_GEOMETRY_SHA256
    blob = response.content.decode("utf-8", errors="replace")
    assert "workforce" not in blob


def test_unknown_area_geometry_fails_closed() -> None:
    response = client.get("/api/v1/areas/not-a-supported-area/geometry")
    assert response.status_code == 404
    body = response.content
    assert EXPECTED_GEOMETRY_SHA256.encode() not in body
    assert b"FeatureCollection" not in body
    assert b"04013107401" not in body
