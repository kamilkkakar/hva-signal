"""Geography can exist without a historical reference. Signal A cannot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core.area_readiness import (
    GeographyReadiness,
    ReferenceReadiness,
    current_registry_requires_reference_for_geometry,
    derive_area_capabilities,
)
from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    CANDIDATE_RELATIVE_PATH,
    hackathon_root,
)
from app.domain.phoenix_v1 import AREA_ID, FROZEN_AREA_CONFIG_SHA256

FROZEN_REFERENCE_SHA256 = (
    "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c"
)
FROZEN_GEOMETRY_SHA256 = (
    "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"
)
MANIFEST_RELATIVE = Path("data") / "areas" / "phoenix-demo" / "manifest.json"
REGISTRY_RELATIVE = Path("data") / "areas" / "registry.json"
GEOMETRY_RELATIVE = Path("data") / "areas" / "phoenix-demo" / "geometry.geojson"


def _write_registry(root: Path) -> None:
    path = root / REGISTRY_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "AREA_REGISTRY_V1",
                "areas": [
                    {"area_id": AREA_ID, "manifest": MANIFEST_RELATIVE.as_posix()}
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


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
        "geometry_sha256": FROZEN_GEOMETRY_SHA256,
    }
    payload.update(overrides)
    return payload


def _seed(tmp_path: Path, *, reference: bytes | None = "keep") -> None:
    src = hackathon_root()
    for rel in (CANDIDATE_RELATIVE_PATH, GEOMETRY_RELATIVE):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((src / rel).read_bytes())
    dest = tmp_path / CANONICAL_REFERENCE_RELATIVE_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    if reference == "keep":
        dest.write_bytes((src / CANONICAL_REFERENCE_RELATIVE_PATH).read_bytes())
    elif reference is None:
        pass
    else:
        dest.write_bytes(reference)
    _write_registry(tmp_path)
    (tmp_path / MANIFEST_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / MANIFEST_RELATIVE).write_text(
        json.dumps(_v2_manifest(), indent=2) + "\n", encoding="utf-8"
    )


def test_geometry_no_longer_requires_a_reference_file() -> None:
    assert current_registry_requires_reference_for_geometry() is False


def test_valid_geography_and_reference_enables_both_signals() -> None:
    from app.core.area_registry import (
        load_verified_area_geometry,
        resolve_area_geography,
        resolve_ready_area_package,
    )

    caps = derive_area_capabilities(AREA_ID)
    assert caps.can_serve_geometry is True
    assert caps.can_process_snapshot is True
    assert caps.can_run_historical_signal is True
    geometry = load_verified_area_geometry(AREA_ID)
    assert hashlib.sha256(geometry.body).hexdigest() == FROZEN_GEOMETRY_SHA256
    assert resolve_area_geography(AREA_ID).timezone == "America/Phoenix"
    assert resolve_ready_area_package(AREA_ID).reference_path is not None


def test_missing_reference_keeps_geometry_and_blocks_signal_a(tmp_path: Path) -> None:
    from app.core.area_registry import (
        AreaRegistryError,
        load_verified_area_geometry,
        resolve_area_geography,
        resolve_ready_area_package,
    )

    _seed(tmp_path, reference=None)
    assert resolve_area_geography(AREA_ID, root=tmp_path).zone_geoids
    geometry = load_verified_area_geometry(AREA_ID, root=tmp_path)
    assert hashlib.sha256(geometry.body).hexdigest() == FROZEN_GEOMETRY_SHA256
    with pytest.raises(AreaRegistryError, match="reference"):
        resolve_ready_area_package(AREA_ID, root=tmp_path)
    caps = derive_area_capabilities(AREA_ID, root=tmp_path)
    assert caps.geography == GeographyReadiness.GEOGRAPHY_READY
    assert caps.reference == ReferenceReadiness.NOT_PREPARED
    assert caps.can_process_snapshot is True
    assert caps.can_run_historical_signal is False


def test_corrupt_reference_keeps_geometry_and_fails_signal_a(tmp_path: Path) -> None:
    from app.core.area_registry import (
        AreaRegistryError,
        load_verified_area_geometry,
        resolve_ready_area_package,
    )

    _seed(tmp_path, reference=b"{}\n")
    geometry = load_verified_area_geometry(AREA_ID, root=tmp_path)
    assert hashlib.sha256(geometry.body).hexdigest() == FROZEN_GEOMETRY_SHA256
    with pytest.raises(AreaRegistryError):
        resolve_ready_area_package(AREA_ID, root=tmp_path)
    caps = derive_area_capabilities(AREA_ID, root=tmp_path)
    assert caps.can_serve_geometry is True
    assert caps.can_process_snapshot is True
    assert caps.can_run_historical_signal is False
    assert caps.reference == ReferenceReadiness.FAILED


def test_corrupt_geometry_blocks_both_signals(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_geography

    _seed(tmp_path)
    (tmp_path / GEOMETRY_RELATIVE).write_bytes(b"not-geojson")
    manifest = json.loads((tmp_path / MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    manifest["geometry_sha256"] = hashlib.sha256(b"not-geojson").hexdigest()
    (tmp_path / MANIFEST_RELATIVE).write_text(json.dumps(manifest, indent=2) + "\n")
    with pytest.raises(AreaRegistryError):
        resolve_area_geography(AREA_ID, root=tmp_path)
    caps = derive_area_capabilities(AREA_ID, root=tmp_path)
    assert caps.can_serve_geometry is False
    assert caps.can_process_snapshot is False
    assert caps.can_run_historical_signal is False


def test_unknown_area_enables_nothing() -> None:
    caps = derive_area_capabilities("not-a-supported-area")
    assert caps.geography == GeographyReadiness.UNRESOLVED
    assert caps.can_serve_geometry is False
    assert caps.can_process_snapshot is False
    assert caps.can_run_historical_signal is False
