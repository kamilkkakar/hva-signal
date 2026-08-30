"""National geography package identity — Census-only, reference-free.

Successful resolver output becomes an immutable HVA-Signal geography.
This module does not load AreaConfig, historical reference, q_A, or Decision 8.
It does not register cities on the public Phoenix area registry.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import TileAssignmentMethod, ZoneAggregationStatistic

PACKAGE_SCHEMA_VERSION = "NATIONAL_GEOGRAPHY_PACKAGE_V1"
LEGACY_PHOENIX_AREA_ID = "phoenix-demo"
NATIONAL_AREA_ID_PREFIX = "us-place"
NATIONAL_RESOLVER_POLICY_ID = "NATIONAL_PLACE_GEOGRAPHY_V1"
NATIONAL_CENSUS_SOURCE = "US_CENSUS_TIGERLINE"
NATIONAL_ZONE_TYPE = "census_tract"
NATIONAL_CENSUS_VINTAGE_CANDIDATE = "2025"
NATIONAL_AGGREGATION_POLICY_ID = (
    "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
)
ZONE_ID_PROPERTY = "GEOID"
EXPECTED_ZONE_COUNT = 25
PLACE_GEOID_PATTERN = re.compile(r"^[0-9]{7}$")
STATE_FIPS_PATTERN = re.compile(r"^[0-9]{2}$")
STATE_ABBR_PATTERN = re.compile(r"^[A-Z]{2}$")
CENSUS_VINTAGE_PATTERN = re.compile(r"^[0-9]{4}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TRACT_GEOID_PATTERN = re.compile(r"^[0-9]{11}$")
IANA_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+)+$")
POLICY_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
AREA_ID_PATTERN = re.compile(
    r"^us-place-[0-9]{7}-[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*$"
)

FORBIDDEN_PACKAGE_KEYS = frozenset(
    {
        "reference_path",
        "reference_sha256",
        "reference_version",
        "historical_reference",
        "historical_reference_window",
        "historical_protocol",
        "reference_protocol_id",
        "q_A",
        "q_a",
        "decision8",
        "decision_8",
        "hazard_spread_policy",
        "area_config_path",
        "area_config_sha256",
    }
)


class NationalGeographyLifecycle(StrEnum):
    """Stored geography lifecycle. SNAPSHOT_CAPABLE is derived, not stored."""

    PLACE_RESOLVED = "PLACE_RESOLVED"
    GEOGRAPHY_GENERATING = "GEOGRAPHY_GENERATING"
    GEOGRAPHY_READY = "GEOGRAPHY_READY"
    FAILED = "FAILED"


class NationalGeographyError(ValueError):
    """Illegal national geography identity, package, or transition."""


class NationalGeographyImmutabilityError(NationalGeographyError):
    """A materialized area_id cannot be silently replaced with different content."""


def national_aggregation_spec() -> ThermalAggregationSpec:
    """Centroid-within mean. Not a Phoenix AreaConfig historical block."""
    return ThermalAggregationSpec(
        version=NATIONAL_AGGREGATION_POLICY_ID,
        assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
        statistic=ZoneAggregationStatistic.MEAN,
        minimum_coverage_ratio=None,
        zero_tile_behavior="insufficient_evidence",
        boundary_behavior="centroid_within_zone",
        notes=[
            "National geography aggregation contract.",
            "Reuses centroid-within mean. Does not carry Decision 1B or Decision 8.",
        ],
    )


def resolver_policy_slug(resolver_policy_id: str) -> str:
    """Mechanical slug for area_id. Policy ID change yields a new area_id."""
    slug = resolver_policy_id.strip().lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug or not POLICY_SLUG_PATTERN.fullmatch(slug):
        raise NationalGeographyError(
            f"resolver_policy_id {resolver_policy_id!r} does not yield a stable slug"
        )
    return slug


def build_national_area_id(
    *,
    place_geoid: str,
    census_vintage: str,
    resolver_policy_id: str,
) -> str:
    """Stronger than us-place-{geoid}-{resolver_version}: vintage is explicit.

    Form: us-place-{place_geoid}-{census_vintage}-{policy_slug}
    Example: us-place-1714000-2025-national-place-geography-v1
    Never equals phoenix-demo.
    """
    if not PLACE_GEOID_PATTERN.fullmatch(place_geoid):
        raise NationalGeographyError("canonical_place_geoid must be a 7-digit PLACE GEOID")
    if not CENSUS_VINTAGE_PATTERN.fullmatch(census_vintage):
        raise NationalGeographyError("census_vintage must be a 4-digit year")
    area_id = (
        f"{NATIONAL_AREA_ID_PREFIX}-{place_geoid}-{census_vintage}-"
        f"{resolver_policy_slug(resolver_policy_id)}"
    )
    assert_area_id_not_legacy_phoenix(area_id)
    if not AREA_ID_PATTERN.fullmatch(area_id):
        raise NationalGeographyError(f"produced area_id is not canonical: {area_id!r}")
    return area_id


def assert_area_id_not_legacy_phoenix(area_id: str) -> None:
    if area_id.strip().lower() == LEGACY_PHOENIX_AREA_ID:
        raise NationalGeographyError(
            "national geography must not use the legacy phoenix-demo area_id"
        )


def looks_like_national_area_id(area_id: str) -> bool:
    return bool(AREA_ID_PATTERN.fullmatch(area_id))


def geometry_hash8(geometry_sha256: str) -> str:
    if not SHA256_PATTERN.fullmatch(geometry_sha256):
        raise NationalGeographyError("geometry_sha256 must be 64 lowercase hex chars")
    return geometry_sha256[:8]


def build_zone_geometry_version(
    *,
    census_source: str,
    zone_type: str,
    census_vintage: str,
    place_geoid: str,
    resolver_policy_id: str,
    geometry_sha256: str,
) -> str:
    """Content-addressed geometry identity. Distinct from Phoenix zone_geometry_version."""
    return (
        f"{census_source}.{zone_type.upper()}.{census_vintage}."
        f"PLACE_{place_geoid}.{resolver_policy_id}.{geometry_hash8(geometry_sha256)}"
    )


def build_zone_definition_version(
    *,
    census_source: str,
    zone_type: str,
    census_vintage: str,
) -> str:
    return f"{census_source}.{zone_type.upper()}.{census_vintage}"


class CanonicalPlaceIdentity(BaseModel):
    """Census PLACE identity. Not a metro, county subdivision, or free polygon."""

    model_config = ConfigDict(extra="forbid")

    canonical_place_geoid: str
    place_name: str = Field(min_length=1)
    state_fips: str
    state_abbreviation: str
    display_name: str | None = None
    place_type: str | None = None

    @field_validator("canonical_place_geoid")
    @classmethod
    def _place_geoid(cls, value: str) -> str:
        if not PLACE_GEOID_PATTERN.fullmatch(value):
            raise ValueError("canonical_place_geoid must be a 7-digit PLACE GEOID")
        return value

    @field_validator("state_fips")
    @classmethod
    def _state_fips(cls, value: str) -> str:
        if not STATE_FIPS_PATTERN.fullmatch(value):
            raise ValueError("state_fips must be 2 digits")
        return value

    @field_validator("state_abbreviation")
    @classmethod
    def _state_abbr(cls, value: str) -> str:
        if not STATE_ABBR_PATTERN.fullmatch(value):
            raise ValueError("state_abbreviation must be 2 uppercase letters")
        return value

    @model_validator(mode="after")
    def _state_prefix_matches(self) -> CanonicalPlaceIdentity:
        if self.canonical_place_geoid[:2] != self.state_fips:
            raise ValueError("canonical_place_geoid must start with state_fips")
        return self

    def resolved_display_name(self) -> str:
        if self.display_name:
            return self.display_name
        return f"{self.place_name}, {self.state_abbreviation}"


class SelectionAuditMetadata(BaseModel):
    """Audit of how the 25 tracts were chosen. Not a historical protocol."""

    model_config = ConfigDict(extra="forbid")

    seed_geoid: str
    selection_order: tuple[str, ...]
    eligible_tract_count: int = Field(ge=EXPECTED_ZONE_COUNT)
    connected_component_size: int = Field(ge=EXPECTED_ZONE_COUNT)
    rook_connected: Literal[True]
    eligibility_rule_id: str = Field(min_length=1)
    rook_policy_id: str = Field(min_length=1)
    projection_crs: str = Field(min_length=1)
    tie_break_policy_id: str | None = None
    compactness: float | None = None
    area_km2: float | None = None

    @field_validator("seed_geoid", "selection_order")
    @classmethod
    def _tract_ids(cls, value: str | tuple[str, ...]) -> str | tuple[str, ...]:
        if isinstance(value, str):
            if not TRACT_GEOID_PATTERN.fullmatch(value):
                raise ValueError("seed_geoid must be an 11-digit tract GEOID")
            return value
        if len(value) != EXPECTED_ZONE_COUNT:
            raise ValueError("selection_order must contain exactly 25 GEOIDs")
        if len(set(value)) != EXPECTED_ZONE_COUNT:
            raise ValueError("selection_order GEOIDs must be unique")
        for item in value:
            if not TRACT_GEOID_PATTERN.fullmatch(item):
                raise ValueError("selection_order entries must be 11-digit tract GEOIDs")
        return value

    @model_validator(mode="after")
    def _seed_in_selection(self) -> SelectionAuditMetadata:
        if self.seed_geoid not in self.selection_order:
            raise ValueError("seed_geoid must appear in selection_order")
        return self


class NationalGeographyPackage(BaseModel):
    """Immutable Census geography. Reference / q_A / Decision 8 are forbidden."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["NATIONAL_GEOGRAPHY_PACKAGE_V1"] = PACKAGE_SCHEMA_VERSION
    area_id: str
    canonical_place_geoid: str
    place_name: str = Field(min_length=1)
    state_fips: str
    state_abbreviation: str
    display_name: str = Field(min_length=1)
    zone_geoids: tuple[str, ...]
    geometry: dict[str, Any]
    geometry_sha256: str
    census_vintage: str
    census_source: str = Field(min_length=1)
    zone_type: Literal["census_tract"] = NATIONAL_ZONE_TYPE
    zone_definition_version: str = Field(min_length=1)
    zone_geometry_version: str = Field(min_length=1)
    resolver_policy_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    aggregation_spec: ThermalAggregationSpec
    expected_zone_count: Literal[25] = EXPECTED_ZONE_COUNT
    zone_id_property: Literal["GEOID"] = ZONE_ID_PROPERTY
    selection_audit: SelectionAuditMetadata
    package_sha256: str

    @field_validator("area_id")
    @classmethod
    def _area_id(cls, value: str) -> str:
        assert_area_id_not_legacy_phoenix(value)
        if not AREA_ID_PATTERN.fullmatch(value):
            raise ValueError("area_id must be us-place-{geoid}-{vintage}-{policy_slug}")
        return value

    @field_validator("canonical_place_geoid")
    @classmethod
    def _place(cls, value: str) -> str:
        if not PLACE_GEOID_PATTERN.fullmatch(value):
            raise ValueError("canonical_place_geoid must be a 7-digit PLACE GEOID")
        return value

    @field_validator("state_fips")
    @classmethod
    def _state_fips(cls, value: str) -> str:
        if not STATE_FIPS_PATTERN.fullmatch(value):
            raise ValueError("state_fips must be 2 digits")
        return value

    @field_validator("state_abbreviation")
    @classmethod
    def _state_abbr(cls, value: str) -> str:
        if not STATE_ABBR_PATTERN.fullmatch(value):
            raise ValueError("state_abbreviation must be 2 uppercase letters")
        return value

    @field_validator("zone_geoids")
    @classmethod
    def _zones(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != EXPECTED_ZONE_COUNT:
            raise ValueError("zone_geoids must contain exactly 25 GEOIDs")
        if len(set(value)) != EXPECTED_ZONE_COUNT:
            raise ValueError("zone_geoids must be unique")
        for item in value:
            if not TRACT_GEOID_PATTERN.fullmatch(item):
                raise ValueError("zone_geoids must be 11-digit tract GEOIDs")
        if tuple(sorted(value)) != value:
            raise ValueError("zone_geoids must be in lexicographic ascending order")
        return value

    @field_validator("geometry_sha256", "package_sha256")
    @classmethod
    def _sha(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("digest must be 64 lowercase hex chars")
        return value

    @field_validator("census_vintage")
    @classmethod
    def _vintage(cls, value: str) -> str:
        if not CENSUS_VINTAGE_PATTERN.fullmatch(value):
            raise ValueError("census_vintage must be a 4-digit year")
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str) -> str:
        if not IANA_TIMEZONE_PATTERN.fullmatch(value):
            raise ValueError("timezone must be an IANA Area/Location name")
        return value

    @model_validator(mode="after")
    def _identity_consistency(self) -> NationalGeographyPackage:
        expected_area_id = build_national_area_id(
            place_geoid=self.canonical_place_geoid,
            census_vintage=self.census_vintage,
            resolver_policy_id=self.resolver_policy_id,
        )
        if self.area_id != expected_area_id:
            raise ValueError(
                f"area_id {self.area_id!r} does not match canonical {expected_area_id!r}"
            )
        if self.canonical_place_geoid[:2] != self.state_fips:
            raise ValueError("canonical_place_geoid must start with state_fips")
        if set(self.zone_geoids) != set(self.selection_audit.selection_order):
            raise ValueError("zone_geoids must match selection_audit.selection_order as a set")
        expected_geom_version = build_zone_geometry_version(
            census_source=self.census_source,
            zone_type=self.zone_type,
            census_vintage=self.census_vintage,
            place_geoid=self.canonical_place_geoid,
            resolver_policy_id=self.resolver_policy_id,
            geometry_sha256=self.geometry_sha256,
        )
        if self.zone_geometry_version != expected_geom_version:
            raise ValueError("zone_geometry_version does not match geometry SHA / policy")
        feature_ids = _feature_geoids(self.geometry, zone_id_property=self.zone_id_property)
        if feature_ids != self.zone_geoids:
            raise ValueError("geometry feature GEOIDs must equal canonical zone_geoids")
        if geometry_sha256_hex(self.geometry) != self.geometry_sha256:
            raise ValueError("geometry_sha256 does not match canonical geometry bytes")
        expected_package = package_identity_sha256(self, ignore_package_sha=True)
        if self.package_sha256 != expected_package:
            raise ValueError("package_sha256 does not match canonical identity document")
        return self


def _feature_geoids(
    geometry: dict[str, Any], *, zone_id_property: str = ZONE_ID_PROPERTY
) -> tuple[str, ...]:
    if not isinstance(geometry, dict) or geometry.get("type") != "FeatureCollection":
        raise ValueError("geometry must be a GeoJSON FeatureCollection")
    features = geometry.get("features")
    if not isinstance(features, list) or len(features) != EXPECTED_ZONE_COUNT:
        raise ValueError("geometry must contain exactly 25 features")
    ids: list[str] = []
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            raise ValueError("invalid GeoJSON feature")
        if zone_id_property not in feature["properties"]:
            raise ValueError(f"feature missing {zone_id_property}")
        geoid = str(feature["properties"][zone_id_property])
        if not TRACT_GEOID_PATTERN.fullmatch(geoid):
            raise ValueError("feature GEOID must be an 11-digit tract GEOID")
        ids.append(geoid)
    if len(set(ids)) != EXPECTED_ZONE_COUNT:
        raise ValueError("geometry feature GEOIDs must be unique")
    return tuple(ids)


def canonicalize_geography_geojson(
    geometry: dict[str, Any], *, zone_id_property: str = ZONE_ID_PROPERTY
) -> dict[str, Any]:
    """Deterministic FeatureCollection: features by GEOID ASC, GEOID-first properties."""
    ids = _feature_geoids(geometry, zone_id_property=zone_id_property)
    by_id: dict[str, dict[str, Any]] = {}
    features = geometry["features"]
    for feature, geoid in zip(features, ids, strict=True):
        props = feature["properties"]
        ordered_props: dict[str, Any] = {ZONE_ID_PROPERTY: geoid}
        for key in sorted(props):
            if key == zone_id_property or key == ZONE_ID_PROPERTY:
                continue
            ordered_props[key] = props[key]
        geom = feature.get("geometry")
        if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
            raise ValueError("feature geometry is invalid")
        by_id[geoid] = {
            "type": "Feature",
            "properties": ordered_props,
            "geometry": geom,
        }
    ordered = tuple(sorted(ids))
    return {
        "type": "FeatureCollection",
        "features": [by_id[geoid] for geoid in ordered],
    }


def canonical_geojson_bytes(geometry: dict[str, Any]) -> bytes:
    canonical = canonicalize_geography_geojson(geometry)
    return json.dumps(
        canonical, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def geometry_sha256_hex(geometry: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_geojson_bytes(geometry)).hexdigest()


def _identity_document(package: NationalGeographyPackage, *, ignore_package_sha: bool) -> dict[str, Any]:
    aggregation = package.aggregation_spec.model_dump(mode="json")
    document: dict[str, Any] = {
        "aggregation_spec": aggregation,
        "area_id": package.area_id,
        "canonical_place_geoid": package.canonical_place_geoid,
        "census_source": package.census_source,
        "census_vintage": package.census_vintage,
        "display_name": package.display_name,
        "expected_zone_count": package.expected_zone_count,
        "geometry_sha256": package.geometry_sha256,
        "place_name": package.place_name,
        "resolver_policy_id": package.resolver_policy_id,
        "schema_version": package.schema_version,
        "selection_audit": package.selection_audit.model_dump(mode="json"),
        "state_abbreviation": package.state_abbreviation,
        "state_fips": package.state_fips,
        "timezone": package.timezone,
        "zone_definition_version": package.zone_definition_version,
        "zone_geoids": list(package.zone_geoids),
        "zone_geometry_version": package.zone_geometry_version,
        "zone_id_property": package.zone_id_property,
        "zone_type": package.zone_type,
    }
    if not ignore_package_sha:
        document["package_sha256"] = package.package_sha256
    return document


def package_identity_sha256(
    package: NationalGeographyPackage, *, ignore_package_sha: bool = False
) -> str:
    document = _identity_document(package, ignore_package_sha=ignore_package_sha)
    blob = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def assert_no_forbidden_package_keys(payload: dict[str, Any]) -> None:
    present = FORBIDDEN_PACKAGE_KEYS.intersection(payload)
    if present:
        raise NationalGeographyError(
            "geography package must not carry reference / q_A / Decision 8 fields: "
            + ", ".join(sorted(present))
        )


def to_geography_identity(package: NationalGeographyPackage):
    """Adapt to the existing GeographyIdentity without fabricating AreaConfig."""
    from app.core.area_readiness import GeographyIdentity

    return GeographyIdentity(
        area_id=package.area_id,
        zone_geoids=package.zone_geoids,
        expected_zone_count=package.expected_zone_count,
        timezone=package.timezone,
        aggregation_spec_version=package.aggregation_spec.version,
        area_selection_policy_version=package.resolver_policy_id,
        geometry_sha256=package.geometry_sha256,
    )
