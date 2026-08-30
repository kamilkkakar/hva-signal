"""Versioned supported-area registry. Routing and integrity only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.core.area_config import AreaConfig
from app.core.phoenix_v1_area_config import (
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)

GEOMETRY_ZONE_ID_PROPERTY = "GEOID"
PHOENIX_DEMO_AREA_ID = "phoenix-demo"
PHOENIX_AOI_TIMEZONE = "America/Phoenix"
PHOENIX_AREA_SELECTION_POLICY_VERSION = "PHX_DEMO_AOI_POLICY_V1"

# Timezone is a geography asset. It is not stored on frozen AreaConfig.
_AREA_TIMEZONES = {PHOENIX_DEMO_AREA_ID: PHOENIX_AOI_TIMEZONE}
_AREA_SELECTION_POLICIES = {
    PHOENIX_DEMO_AREA_ID: PHOENIX_AREA_SELECTION_POLICY_VERSION,
}


class AreaRegistryError(ValueError):
    """Schema, path, or hash integrity failure in the area package layer."""


class UnsupportedAreaError(ValueError):
    """area_id is not a registered supported production area."""

    def __init__(self, area_id: str) -> None:
        self.area_id = area_id
        super().__init__(f"Unsupported area_id={area_id!r}.")


def _safe_relative_path(value: str) -> str:
    posix = value.replace("\\", "/")
    if posix.startswith("/") or posix.startswith("~") or ":" in posix.split("/", 1)[0]:
        raise ValueError("path must be repository-relative")
    path = Path(posix)
    if path.is_absolute() or path.anchor:
        raise ValueError("path must be repository-relative")
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("path traversal is not allowed")
    return posix


def _tracked_file(root: Path, relative: str, *, label: str) -> Path:
    try:
        safe = _safe_relative_path(relative)
    except ValueError as exc:
        raise AreaRegistryError(f"{label} {exc}") from exc
    root_resolved = root.resolve()
    path = (root_resolved / safe).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise AreaRegistryError(f"{label} escapes repository root") from exc
    if not path.is_file():
        raise AreaRegistryError(f"{label} is missing")
    return path


class AreaRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: str = Field(min_length=1)
    manifest: str

    @field_validator("manifest")
    @classmethod
    def _manifest_is_relative(cls, value: str) -> str:
        return _safe_relative_path(value)


class AreaRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["AREA_REGISTRY_V1"]
    areas: list[AreaRegistryEntry]

    @model_validator(mode="after")
    def _unique_area_ids(self) -> AreaRegistry:
        seen: set[str] = set()
        for entry in self.areas:
            if entry.area_id in seen:
                raise ValueError(f"duplicate area_id={entry.area_id!r}")
            seen.add(entry.area_id)
        return self


class AreaPackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["AREA_PACKAGE_MANIFEST_V2"]
    area_id: str = Field(min_length=1)
    supported: bool
    area_config_path: str
    area_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_path: str
    reference_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    geometry_path: str
    geometry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("area_config_path", "reference_path", "geometry_path")
    @classmethod
    def _artifact_paths_are_relative(cls, value: str) -> str:
        return _safe_relative_path(value)


@dataclass(frozen=True)
class AreaGeometryBytes:
    area_id: str
    zone_geometry_version: str
    sha256: str
    body: bytes


@dataclass(frozen=True)
class ResolvedAreaGeography:
    """Verified geography assets. Does not imply a historical reference exists."""

    manifest: AreaPackageManifest
    config: AreaConfig
    area_config_path: Path
    geometry_path: Path
    geometry_body: bytes
    zone_geoids: tuple[str, ...]
    timezone: str
    area_selection_policy_version: str
    zone_id_property: str = GEOMETRY_ZONE_ID_PROPERTY


@dataclass(frozen=True)
class ResolvedReadyPackage:
    """Verified READY-area artifacts. Integrity only — not an analytical decision."""

    manifest: AreaPackageManifest
    config: AreaConfig
    area_config_path: Path
    reference_path: Path
    geometry_path: Path
    geography: ResolvedAreaGeography | None = None


class SupportedAreaSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: str
    supported: bool
    expected_zone_count: int
    area_config_version: str
    reference_version: str
    zone_geometry_version: str


def load_area_registry(*, root: Path | None = None) -> AreaRegistry:
    repo = Path(root) if root is not None else hackathon_root()
    registry_path = _tracked_file(repo, "data/areas/registry.json", label="registry")
    try:
        return AreaRegistry.model_validate(
            json.loads(registry_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AreaRegistryError(f"invalid registry: {exc}") from exc


def _load_registered_manifest(
    area_id: str, *, repo: Path
) -> tuple[AreaPackageManifest, Path]:
    registry = load_area_registry(root=repo)
    entry = next((item for item in registry.areas if item.area_id == area_id), None)
    if entry is None:
        raise UnsupportedAreaError(area_id)
    manifest_path = _tracked_file(repo, entry.manifest, label="manifest")
    try:
        manifest = AreaPackageManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AreaRegistryError(f"invalid manifest: {exc}") from exc
    if manifest.area_id != entry.area_id:
        raise AreaRegistryError(
            f"manifest area_id={manifest.area_id!r} does not match "
            f"registry area_id={entry.area_id!r}"
        )
    if not manifest.supported:
        raise UnsupportedAreaError(area_id)
    return manifest, manifest_path


def _load_verified_area_config(
    manifest: AreaPackageManifest, *, repo: Path
) -> tuple[AreaConfig, Path]:
    config_path = _tracked_file(repo, manifest.area_config_path, label="AreaConfig")
    config_digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
    if config_digest != manifest.area_config_sha256:
        raise AreaRegistryError("AreaConfig SHA-256 mismatch")
    try:
        loaded = AreaConfig.model_validate(
            json.loads(config_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AreaRegistryError(f"invalid AreaConfig: {exc}") from exc
    if loaded.area_id != manifest.area_id:
        raise AreaRegistryError(
            f"AreaConfig area_id={loaded.area_id!r} does not match "
            f"manifest area_id={manifest.area_id!r}"
        )
    from app.domain.phoenix_v1 import AREA_ID, FROZEN_AREA_CONFIG_SHA256

    if loaded.area_id == AREA_ID and config_digest == FROZEN_AREA_CONFIG_SHA256:
        frozen = load_frozen_phoenix_v1_area_config()
        if frozen.area_id != loaded.area_id or frozen.version != loaded.version:
            raise AreaRegistryError("Phoenix frozen AreaConfig guard mismatch")
    return loaded, config_path


def _geography_zone_ids(
    raw: bytes,
    *,
    expected_zone_count: int,
    zone_id_property: str = GEOMETRY_ZONE_ID_PROPERTY,
) -> tuple[str, ...]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AreaRegistryError("invalid GeoJSON") from exc
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise AreaRegistryError("invalid GeoJSON")
    features = payload.get("features")
    if not isinstance(features, list):
        raise AreaRegistryError("invalid GeoJSON")
    if len(features) != expected_zone_count:
        raise AreaRegistryError(
            f"geometry feature count {len(features)} != expected {expected_zone_count}"
        )
    ids: list[str] = []
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            raise AreaRegistryError("invalid GeoJSON")
        if zone_id_property not in feature["properties"]:
            raise AreaRegistryError("invalid GeoJSON")
        ids.append(str(feature["properties"][zone_id_property]))
    if len(ids) != len(set(ids)):
        raise AreaRegistryError("duplicate geometry zone IDs")
    return tuple(ids)


def resolve_area_geography(
    area_id: str, *, root: Path | None = None
) -> ResolvedAreaGeography:
    """Resolve geography assets without opening the historical reference file."""
    repo = Path(root) if root is not None else hackathon_root()
    manifest, _manifest_path = _load_registered_manifest(area_id, repo=repo)
    loaded, config_path = _load_verified_area_config(manifest, repo=repo)
    geometry_path = _tracked_file(repo, manifest.geometry_path, label="geometry")
    geometry_raw = geometry_path.read_bytes()
    geometry_digest = hashlib.sha256(geometry_raw).hexdigest()
    if geometry_digest != manifest.geometry_sha256:
        raise AreaRegistryError("geometry SHA-256 mismatch")
    zone_geoids = _geography_zone_ids(
        geometry_raw, expected_zone_count=loaded.expected_zone_count
    )
    timezone = _AREA_TIMEZONES.get(manifest.area_id)
    policy = _AREA_SELECTION_POLICIES.get(manifest.area_id)
    if timezone is None or policy is None:
        raise AreaRegistryError(
            f"geography timezone/selection policy is not registered for {manifest.area_id!r}"
        )
    return ResolvedAreaGeography(
        manifest=manifest,
        config=loaded,
        area_config_path=config_path,
        geometry_path=geometry_path,
        geometry_body=geometry_raw,
        zone_geoids=zone_geoids,
        timezone=timezone,
        area_selection_policy_version=policy,
    )


def resolve_ready_area_package(
    area_id: str, *, root: Path | None = None
) -> ResolvedReadyPackage:
    """Resolve a READY package and keep the verified artifact paths.

    Geography is resolved first. Historical callers still must pass the
    reference hash, GEOID join, and — for phoenix-demo analysis —
    load_frozen_phoenix_v1_area_config.
    """
    repo = Path(root) if root is not None else hackathon_root()
    geography = resolve_area_geography(area_id, root=repo)
    reference_path = _tracked_file(
        repo, geography.manifest.reference_path, label="reference"
    )
    reference_digest = hashlib.sha256(reference_path.read_bytes()).hexdigest()
    if reference_digest != geography.manifest.reference_sha256:
        raise AreaRegistryError("reference SHA-256 mismatch")
    _validate_geometry_artifact(
        geography.geometry_body,
        config=geography.config,
        reference_path=reference_path,
    )
    return ResolvedReadyPackage(
        manifest=geography.manifest,
        config=geography.config,
        area_config_path=geography.area_config_path,
        reference_path=reference_path,
        geometry_path=geography.geometry_path,
        geography=geography,
    )


def resolve_area_package(area_id: str, *, root: Path | None = None) -> AreaPackageManifest:
    return resolve_ready_area_package(area_id, root=root).manifest


def _reference_zone_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AreaRegistryError("reference is missing") from exc
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AreaRegistryError("invalid reference") from exc
        if "geoid" not in row:
            raise AreaRegistryError("geometry/reference zone-ID mismatch")
        ids.add(str(row["geoid"]))
    return ids


def _matching_geometry_zone_ids(
    features: list[object],
    reference_ids: set[str],
) -> list[str]:
    if not features:
        raise AreaRegistryError("invalid GeoJSON")
    first = features[0]
    if not isinstance(first, dict) or not isinstance(first.get("properties"), dict):
        raise AreaRegistryError("invalid GeoJSON")
    matches: list[list[str]] = []
    for key in first["properties"]:
        values: list[str] = []
        complete = True
        for feature in features:
            if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
                complete = False
                break
            props = feature["properties"]
            if key not in props:
                complete = False
                break
            values.append(str(props[key]))
        if complete and set(values) == reference_ids:
            matches.append(values)
    if len(matches) != 1:
        raise AreaRegistryError("geometry/reference zone-ID mismatch")
    values = matches[0]
    if len(values) != len(set(values)):
        raise AreaRegistryError("duplicate geometry zone IDs")
    return values


def _validate_geometry_artifact(
    raw: bytes,
    *,
    config: AreaConfig,
    reference_path: Path,
) -> None:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AreaRegistryError("invalid GeoJSON") from exc
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise AreaRegistryError("invalid GeoJSON")
    features = payload.get("features")
    if not isinstance(features, list):
        raise AreaRegistryError("invalid GeoJSON")
    if len(features) != config.expected_zone_count:
        raise AreaRegistryError(
            f"geometry feature count {len(features)} != expected {config.expected_zone_count}"
        )
    _matching_geometry_zone_ids(features, _reference_zone_ids(reference_path))


def load_verified_area_geometry(
    area_id: str,
    *,
    root: Path | None = None,
) -> AreaGeometryBytes:
    geography = resolve_area_geography(area_id, root=root)
    return AreaGeometryBytes(
        area_id=geography.manifest.area_id,
        zone_geometry_version=geography.config.zone_geometry_version,
        sha256=geography.manifest.geometry_sha256,
        body=geography.geometry_body,
    )


def list_supported_area_ids(*, root: Path | None = None) -> list[str]:
    registry = load_area_registry(root=root)
    return [
        resolve_area_geography(entry.area_id, root=root).manifest.area_id
        for entry in registry.areas
    ]


def list_supported_area_summaries(*, root: Path | None = None) -> list[SupportedAreaSummary]:
    repo = Path(root) if root is not None else hackathon_root()
    summaries: list[SupportedAreaSummary] = []
    for area_id in list_supported_area_ids(root=repo):
        geography = resolve_area_geography(area_id, root=repo)
        summaries.append(
            SupportedAreaSummary(
                area_id=geography.manifest.area_id,
                supported=geography.manifest.supported,
                expected_zone_count=geography.config.expected_zone_count,
                area_config_version=geography.config.version,
                reference_version=geography.config.historical_reference_window.version,
                zone_geometry_version=geography.config.zone_geometry_version,
            )
        )
    return summaries
