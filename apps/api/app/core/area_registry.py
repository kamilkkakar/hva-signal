"""Versioned supported-area registry. Routing and integrity only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.core.area_config import AreaConfig
from app.core.phoenix_v1_area_config import hackathon_root


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


def resolve_area_package(area_id: str, *, root: Path | None = None) -> AreaPackageManifest:
    repo = Path(root) if root is not None else hackathon_root()
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
    config_path = _tracked_file(repo, manifest.area_config_path, label="AreaConfig")
    reference_path = _tracked_file(repo, manifest.reference_path, label="reference")
    config_digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
    if config_digest != manifest.area_config_sha256:
        raise AreaRegistryError("AreaConfig SHA-256 mismatch")
    reference_digest = hashlib.sha256(reference_path.read_bytes()).hexdigest()
    if reference_digest != manifest.reference_sha256:
        raise AreaRegistryError("reference SHA-256 mismatch")
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
    geometry_path = _tracked_file(repo, manifest.geometry_path, label="geometry")
    geometry_raw = geometry_path.read_bytes()
    geometry_digest = hashlib.sha256(geometry_raw).hexdigest()
    if geometry_digest != manifest.geometry_sha256:
        raise AreaRegistryError("geometry SHA-256 mismatch")
    _validate_geometry_artifact(
        geometry_raw,
        config=loaded,
        reference_path=reference_path,
    )
    return manifest


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
    repo = Path(root) if root is not None else hackathon_root()
    manifest = resolve_area_package(area_id, root=repo)
    geometry_path = _tracked_file(repo, manifest.geometry_path, label="geometry")
    config_path = _tracked_file(repo, manifest.area_config_path, label="AreaConfig")
    config = AreaConfig.model_validate(json.loads(config_path.read_text(encoding="utf-8")))
    return AreaGeometryBytes(
        area_id=manifest.area_id,
        zone_geometry_version=config.zone_geometry_version,
        sha256=manifest.geometry_sha256,
        body=geometry_path.read_bytes(),
    )


def list_supported_area_ids(*, root: Path | None = None) -> list[str]:
    registry = load_area_registry(root=root)
    return [
        resolve_area_package(entry.area_id, root=root).area_id
        for entry in registry.areas
    ]


def list_supported_area_summaries(*, root: Path | None = None) -> list[SupportedAreaSummary]:
    repo = Path(root) if root is not None else hackathon_root()
    summaries: list[SupportedAreaSummary] = []
    for area_id in list_supported_area_ids(root=repo):
        package = resolve_area_package(area_id, root=repo)
        config_path = _tracked_file(repo, package.area_config_path, label="AreaConfig")
        config = AreaConfig.model_validate(
            json.loads(config_path.read_text(encoding="utf-8"))
        )
        summaries.append(
            SupportedAreaSummary(
                area_id=package.area_id,
                supported=package.supported,
                expected_zone_count=config.expected_zone_count,
                area_config_version=config.version,
                reference_version=config.historical_reference_window.version,
                zone_geometry_version=config.zone_geometry_version,
            )
        )
    return summaries
