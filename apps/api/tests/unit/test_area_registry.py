"""Phase 1 area registry / package contract. Non-analytical."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    CANDIDATE_RELATIVE_PATH,
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)
from app.domain.phoenix_v1 import AREA_ID, FROZEN_AREA_CONFIG_SHA256, ZONE_GEOMETRY_VERSION
from app.domain.requests import AnalysisRequest

FROZEN_REFERENCE_SHA256 = (
    "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c"
)
FROZEN_GEOMETRY_SHA256 = (
    "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"
)
MANIFEST_RELATIVE = Path("data") / "areas" / "phoenix-demo" / "manifest.json"
REGISTRY_RELATIVE = Path("data") / "areas" / "registry.json"
GEOMETRY_RELATIVE = Path("data") / "areas" / "phoenix-demo" / "geometry.geojson"
FORBIDDEN_GEOMETRY_FIELDS = {
    "geometry_url",
    "geometry_endpoint",
    "geometry_available",
    "geometry_status",
    "zone_geometry_version",
}


def _historical_request(area_id: str, day: str = "2022-07-01") -> AnalysisRequest:
    year, month, day_n = (int(part) for part in day.split("-"))
    return AnalysisRequest.model_validate(
        {
            "area_id": area_id,
            "analysis_time": datetime(year, month, day_n, 3, 0),
            "analysis_mode": "retrospective",
            "horizon_hours": 0,
            "lookback_hours": 0,
            "granularity_m": 100,
            "data_mode": "replay",
        }
    )


def _write_registry(root: Path, entries: list[dict]) -> None:
    path = root / REGISTRY_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": "AREA_REGISTRY_V1", "areas": entries}, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _write_manifest(root: Path, payload: dict, *, area_id: str = "phoenix-demo") -> Path:
    path = root / "data" / "areas" / area_id / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _seed_frozen_aliases(tmp_path: Path) -> None:
    src_root = hackathon_root()
    for rel in (CANDIDATE_RELATIVE_PATH, CANONICAL_REFERENCE_RELATIVE_PATH, GEOMETRY_RELATIVE):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((src_root / rel).read_bytes())


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


def test_production_registry_loads_exactly_one_supported_phoenix_area() -> None:
    from app.core.area_registry import (
        AreaPackageManifest,
        list_supported_area_ids,
        load_area_registry,
        resolve_area_package,
    )

    registry = load_area_registry()
    assert registry.schema_version == "AREA_REGISTRY_V1"
    assert list_supported_area_ids() == [AREA_ID]
    package = resolve_area_package(AREA_ID)
    assert isinstance(package, AreaPackageManifest)
    assert package.area_id == AREA_ID
    assert package.supported is True
    assert package.schema_version == "AREA_PACKAGE_MANIFEST_V2"
    assert package.area_config_path == CANDIDATE_RELATIVE_PATH.as_posix()
    assert package.reference_path == CANONICAL_REFERENCE_RELATIVE_PATH.as_posix()
    assert package.geometry_path == GEOMETRY_RELATIVE.as_posix()
    assert package.area_config_sha256 == FROZEN_AREA_CONFIG_SHA256
    assert package.reference_sha256 == FROZEN_REFERENCE_SHA256
    assert package.geometry_sha256 == FROZEN_GEOMETRY_SHA256


def test_manifest_v2_requires_geometry_artifact_fields_only() -> None:
    from app.core.area_registry import AreaPackageManifest, resolve_area_package

    fields = set(AreaPackageManifest.model_fields)
    assert "geometry_path" in fields
    assert "geometry_sha256" in fields
    assert fields.isdisjoint(FORBIDDEN_GEOMETRY_FIELDS)
    package = resolve_area_package(AREA_ID)
    dumped = package.model_dump()
    assert dumped["geometry_path"] == GEOMETRY_RELATIVE.as_posix()
    assert dumped["geometry_sha256"] == FROZEN_GEOMETRY_SHA256
    assert set(dumped).isdisjoint(FORBIDDEN_GEOMETRY_FIELDS)
    assert dumped["geometry_path"] is not None
    assert dumped["geometry_sha256"] is not None


def test_manifest_hashes_match_frozen_bytes() -> None:
    from app.core.area_registry import resolve_area_package

    root = hackathon_root()
    package = resolve_area_package(AREA_ID)
    config_bytes = (root / package.area_config_path).read_bytes()
    ref_bytes = (root / package.reference_path).read_bytes()
    geometry_bytes = (root / package.geometry_path).read_bytes()
    assert hashlib.sha256(config_bytes).hexdigest() == package.area_config_sha256
    assert hashlib.sha256(ref_bytes).hexdigest() == package.reference_sha256
    assert hashlib.sha256(geometry_bytes).hexdigest() == package.geometry_sha256
    assert package.geometry_sha256 == FROZEN_GEOMETRY_SHA256
    config = load_frozen_phoenix_v1_area_config()
    assert config.area_id == package.area_id
    assert config.zone_geometry_version == ZONE_GEOMETRY_VERSION


def test_unknown_area_fails_closed_and_never_resolves_phoenix() -> None:
    from app.core.area_registry import UnsupportedAreaError, resolve_area_package

    with pytest.raises(UnsupportedAreaError, match="not-a-supported-area"):
        resolve_area_package("not-a-supported-area")
    with pytest.raises(UnsupportedAreaError):
        resolve_area_package("new-york")
    with pytest.raises(UnsupportedAreaError):
        resolve_area_package(str(MANIFEST_RELATIVE))


def test_user_area_id_is_never_used_as_a_filesystem_path() -> None:
    from app.core.area_registry import UnsupportedAreaError, resolve_area_package

    for area_id in (
        "../etc/passwd",
        "data/areas/phoenix-demo",
        "data/areas/phoenix-demo/manifest.json",
        str(hackathon_root() / MANIFEST_RELATIVE),
        "phoenix-demo/../../data/demo/phoenix/area_config.json",
    ):
        with pytest.raises(UnsupportedAreaError):
            resolve_area_package(area_id)


def test_hash_mismatch_area_config_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    root = hackathon_root()
    _seed_frozen_aliases(tmp_path)
    config_rel = CANDIDATE_RELATIVE_PATH.as_posix()
    ref_rel = CANONICAL_REFERENCE_RELATIVE_PATH.as_posix()
    _write_registry(
        tmp_path,
        [{"area_id": AREA_ID, "manifest": MANIFEST_RELATIVE.as_posix()}],
    )
    _write_manifest(
        tmp_path,
        _v2_manifest(
            area_config_path=config_rel,
            area_config_sha256="0" * 64,
            reference_path=ref_rel,
        ),
    )
    with pytest.raises(AreaRegistryError, match="AreaConfig"):
        resolve_area_package(AREA_ID, root=tmp_path)
    # Isolated test data must not rewrite production frozen files.
    assert hashlib.sha256((root / CANDIDATE_RELATIVE_PATH).read_bytes()).hexdigest() == (
        FROZEN_AREA_CONFIG_SHA256
    )


def test_hash_mismatch_reference_fails_closed(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    _seed_frozen_aliases(tmp_path)
    _write_registry(
        tmp_path,
        [{"area_id": AREA_ID, "manifest": MANIFEST_RELATIVE.as_posix()}],
    )
    _write_manifest(
        tmp_path,
        _v2_manifest(reference_sha256="1" * 64),
    )
    with pytest.raises(AreaRegistryError, match="reference"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_duplicate_area_ids_are_rejected(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, load_area_registry

    _write_registry(
        tmp_path,
        [
            {"area_id": AREA_ID, "manifest": MANIFEST_RELATIVE.as_posix()},
            {"area_id": AREA_ID, "manifest": MANIFEST_RELATIVE.as_posix()},
        ],
    )
    with pytest.raises(AreaRegistryError, match="duplicate"):
        load_area_registry(root=tmp_path)


def test_registry_manifest_area_id_mismatch_is_rejected(tmp_path: Path) -> None:
    from app.core.area_registry import AreaRegistryError, resolve_area_package

    _seed_frozen_aliases(tmp_path)
    _write_registry(
        tmp_path,
        [{"area_id": AREA_ID, "manifest": "data/areas/other/manifest.json"}],
    )
    _write_manifest(
        tmp_path,
        _v2_manifest(area_id="other"),
        area_id="other",
    )
    with pytest.raises(AreaRegistryError, match="area_id"):
        resolve_area_package(AREA_ID, root=tmp_path)


def test_unregistered_manifest_cannot_be_loaded_through_user_area_id() -> None:
    from app.core.area_registry import UnsupportedAreaError, resolve_area_package

    with pytest.raises(UnsupportedAreaError):
        resolve_area_package("phoenix-demo-unregistered")


def test_registry_and_manifest_have_no_workforce_dependency() -> None:
    from app.core import area_registry as module

    root = hackathon_root()
    registry_text = (root / REGISTRY_RELATIVE).read_text(encoding="utf-8")
    manifest_text = (root / MANIFEST_RELATIVE).read_text(encoding="utf-8")
    source = Path(module.__file__).read_text(encoding="utf-8")
    for blob in (registry_text, manifest_text, source):
        assert "workforce" not in blob.replace("\\", "/")


def test_inner_phoenix_loader_guard_still_refuses_non_phoenix_area_id() -> None:
    from app.core.phoenix_v1_area_config import validate_phoenix_v1_area_config

    config = load_frozen_phoenix_v1_area_config()
    mutated = config.model_copy(update={"area_id": "other-city"})
    with pytest.raises(ValueError, match="unexpected area_id"):
        validate_phoenix_v1_area_config(mutated)


def test_unknown_analysis_area_does_not_reach_phoenix_loader_or_decision8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.area_registry import UnsupportedAreaError
    from app.services import orchestrator

    loader_calls: list[str] = []
    eval_calls: list[str] = []

    def _blocked_loader() -> None:
        loader_calls.append("load")
        raise AssertionError("inner Phoenix loader must not run for unknown areas")

    def _blocked_eval(*_args, **_kwargs) -> None:
        eval_calls.append("eval")
        raise AssertionError("Decision 8 must not run for unknown areas")

    monkeypatch.setattr(orchestrator, "load_frozen_phoenix_v1_area_config", _blocked_loader)
    monkeypatch.setattr(orchestrator, "evaluate_phoenix_v1_timestamp", _blocked_eval)

    with pytest.raises(UnsupportedAreaError, match="not-a-supported-area"):
        orchestrator.run_replay_analysis(_historical_request("not-a-supported-area"))
    assert loader_calls == []
    assert eval_calls == []


def test_phoenix_insufficient_regression_after_registry() -> None:
    from app.services.orchestrator import run_replay_analysis

    job = run_replay_analysis(_historical_request(AREA_ID, "2022-07-01"))
    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state == "INSUFFICIENT"
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert abs(job.hazard_spread.observed_spread - 0.0439665471923536) <= 1e-12
    assert len(job.zones) == 25
    assert all(zone.thermal_ordering_permitted is False for zone in job.zones)
    assert (
        "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE"
        in job.limitations
    )


def test_phoenix_sufficient_regression_after_registry() -> None:
    from app.services.orchestrator import run_replay_analysis

    job = run_replay_analysis(_historical_request(AREA_ID, "2022-06-30"))
    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state == "SUFFICIENT"
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert abs(job.hazard_spread.observed_spread - 0.13548387096774192) <= 1e-12
    assert len(job.zones) == 25
    assert all(zone.thermal_ordering_permitted is True for zone in job.zones)
    assert all(zone.ranked is True for zone in job.zones)
