"""Phase 2 frozen Phoenix geometry package contract. Non-analytical."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    CANDIDATE_RELATIVE_PATH,
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)
from app.domain.phoenix_v1 import AREA_ID, FROZEN_AREA_CONFIG_SHA256, ZONE_GEOMETRY_VERSION

EXPECTED_GEOMETRY_SHA256 = (
    "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"
)
FROZEN_REFERENCE_SHA256 = (
    "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c"
)
GEOMETRY_RELATIVE = Path("data") / "areas" / "phoenix-demo" / "geometry.geojson"
MANIFEST_RELATIVE = Path("data") / "areas" / "phoenix-demo" / "manifest.json"
REGISTRY_RELATIVE = Path("data") / "areas" / "registry.json"
GEOMETRY_ZONE_ID_PROPERTY = "GEOID"


def _reference_geoids(root: Path) -> set[str]:
    ids: set[str] = set()
    for line in (root / CANONICAL_REFERENCE_RELATIVE_PATH).read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            ids.add(str(json.loads(line)["geoid"]))
    return ids


def _write_registry(root: Path) -> None:
    path = root / REGISTRY_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "AREA_REGISTRY_V1",
                "areas": [{"area_id": AREA_ID, "manifest": MANIFEST_RELATIVE.as_posix()}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_manifest(root: Path, payload: dict) -> None:
    path = root / MANIFEST_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _v2_manifest(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "schema_version": "AREA_PACKAGE_MANIFEST_V2",
        "area_id": AREA_ID,
        "supported": True,
        "area_config_path": CANDIDATE_RELATIVE_PATH.as_posix(),
        "area_config_sha256": FROZEN_AREA_CONFIG_SHA256,
        "reference_path": CANONICAL_REFERENCE_RELATIVE_PATH.as_posix(),
        "reference_sha256": FROZEN_REFERENCE_SHA256,
        "geometry_path": GEOMETRY_RELATIVE.as_posix(),
        "geometry_sha256": EXPECTED_GEOMETRY_SHA256,
    }
    payload.update(overrides)
    return payload


def _seed_package_files(tmp_path: Path, *, geometry: bytes | None = None) -> None:
    src = hackathon_root()
    for rel in (CANDIDATE_RELATIVE_PATH, CANONICAL_REFERENCE_RELATIVE_PATH):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((src / rel).read_bytes())
    dest = tmp_path / GEOMETRY_RELATIVE
    dest.parent.mkdir(parents=True, exist_ok=True)
    if geometry is None:
        dest.write_bytes((src / GEOMETRY_RELATIVE).read_bytes())
    else:
        dest.write_bytes(geometry)
    _write_registry(tmp_path)


def _mutated_feature_collection(*, drop_one: bool = False, duplicate_id: bool = False, rewrite_id: str | None = None) -> bytes:
    payload = json.loads((hackathon_root() / GEOMETRY_RELATIVE).read_text(encoding="utf-8"))
    features = payload["features"]
    if drop_one:
        payload["features"] = features[:-1]
    if duplicate_id:
        features[1]["properties"][GEOMETRY_ZONE_ID_PROPERTY] = features[0]["properties"][
            GEOMETRY_ZONE_ID_PROPERTY
        ]
    if rewrite_id is not None:
        features[0]["properties"][GEOMETRY_ZONE_ID_PROPERTY] = rewrite_id
    return json.dumps(payload).encode("utf-8")


def test_tracked_geometry_matches_reviewed_source_sha256() -> None:
    path = hackathon_root() / GEOMETRY_RELATIVE
    assert path.is_file()
    assert "workforce" not in path.as_posix().replace("\\", "/")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == EXPECTED_GEOMETRY_SHA256


def test_tracked_geometry_semantic_join_uses_geoid_property() -> None:
    root = hackathon_root()
    payload = json.loads((root / GEOMETRY_RELATIVE).read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    features = payload["features"]
    assert len(features) == 25
    zone_ids = [str(feature["properties"][GEOMETRY_ZONE_ID_PROPERTY]) for feature in features]
    assert len(zone_ids) == 25
    assert len(set(zone_ids)) == 25
    reference_ids = _reference_geoids(root)
    assert len(reference_ids) == 25
    assert set(zone_ids) == reference_ids
    config = load_frozen_phoenix_v1_area_config()
    assert config.zone_geometry_version == ZONE_GEOMETRY_VERSION
    manifest = json.loads((root / MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert "zone_geometry_version" not in manifest
    assert manifest["schema_version"] == "AREA_PACKAGE_MANIFEST_V2"


def test_v1_manifest_is_rejected(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    _seed_package_files(tmp_path)
    v1 = _v2_manifest()
    v1["schema_version"] = "AREA_PACKAGE_MANIFEST_V1"
    del v1["geometry_path"]
    del v1["geometry_sha256"]
    _write_manifest(tmp_path, v1)
    with pytest.raises(AreaRegistryError, match="manifest"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_geometry_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    _seed_package_files(tmp_path)
    _write_manifest(tmp_path, _v2_manifest(geometry_sha256="2" * 64))
    with pytest.raises(AreaRegistryError, match="geometry"):
        resolve_area_package(AREA_ID, root=tmp_path)
    assert hashlib.sha256((hackathon_root() / GEOMETRY_RELATIVE).read_bytes()).hexdigest() == (
        EXPECTED_GEOMETRY_SHA256
    )


def test_missing_geometry_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    _seed_package_files(tmp_path)
    (tmp_path / GEOMETRY_RELATIVE).unlink()
    _write_manifest(tmp_path, _v2_manifest())
    with pytest.raises(AreaRegistryError, match="geometry"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_invalid_geojson_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    raw = b"not-a-feature-collection"
    _seed_package_files(tmp_path, geometry=raw)
    _write_manifest(tmp_path, _v2_manifest(geometry_sha256=hashlib.sha256(raw).hexdigest()))
    with pytest.raises(AreaRegistryError, match="GeoJSON"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_wrong_feature_count_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    raw = _mutated_feature_collection(drop_one=True)
    _seed_package_files(tmp_path, geometry=raw)
    _write_manifest(tmp_path, _v2_manifest(geometry_sha256=hashlib.sha256(raw).hexdigest()))
    with pytest.raises(AreaRegistryError, match="feature count"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_duplicate_geometry_zone_ids_fail_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    raw = _mutated_feature_collection(duplicate_id=True)
    _seed_package_files(tmp_path, geometry=raw)
    _write_manifest(tmp_path, _v2_manifest(geometry_sha256=hashlib.sha256(raw).hexdigest()))
    with pytest.raises(AreaRegistryError, match="zone"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_geometry_reference_zone_id_mismatch_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    raw = _mutated_feature_collection(rewrite_id="00000000000")
    _seed_package_files(tmp_path, geometry=raw)
    _write_manifest(tmp_path, _v2_manifest(geometry_sha256=hashlib.sha256(raw).hexdigest()))
    with pytest.raises(AreaRegistryError, match="zone-ID"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_nullable_geometry_fields_are_rejected(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    _seed_package_files(tmp_path)
    _write_manifest(tmp_path, _v2_manifest(geometry_path=None, geometry_sha256=None))
    with pytest.raises(AreaRegistryError, match="manifest"):
        resolve_area_package(AREA_ID, root=tmp_path)
