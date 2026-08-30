"""Materialize resolver success into an immutable national geography package.

Internal only. Does not write data/areas/registry.json, does not mutate
phoenix-demo, does not open a historical reference, and does not expose a
public route. Policy change produces a new area_id; rematerializing a
different payload under the same area_id is refused.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from threading import Lock
from typing import Any, Literal

from app.core.area_readiness import (
    AreaCapabilityState,
    GeographyReadiness,
    ReferenceReadiness,
    snapshot_capable,
)
from app.domain.aggregation import ThermalAggregationSpec
from app.domain.national_geography_package import (
    EXPECTED_ZONE_COUNT,
    FORBIDDEN_PACKAGE_KEYS,
    LEGACY_PHOENIX_AREA_ID,
    NATIONAL_AGGREGATION_POLICY_ID,
    NATIONAL_CENSUS_SOURCE,
    NATIONAL_CENSUS_VINTAGE,
    NATIONAL_RESOLVER_POLICY_ID,
    CanonicalPlaceIdentity,
    NationalGeographyError,
    NationalGeographyImmutabilityError,
    NationalGeographyLifecycle,
    NationalGeographyPackage,
    SelectionAuditMetadata,
    assert_area_id_not_legacy_phoenix,
    assert_frozen_candidate_policy,
    assert_no_forbidden_package_keys,
    assert_not_legacy_phoenix_policy,
    build_national_area_id,
    build_zone_definition_version,
    build_zone_geometry_version,
    canonicalize_geography_geojson,
    geometry_sha256_hex,
    looks_like_national_area_id,
    national_aggregation_spec,
    package_identity_sha256,
    to_geography_identity,
)
from app.services.snapshot_processor import SnapshotGeography

_ALLOWED_TRANSITIONS: dict[
    NationalGeographyLifecycle, frozenset[NationalGeographyLifecycle]
] = {
    NationalGeographyLifecycle.PLACE_RESOLVED: frozenset(
        {
            NationalGeographyLifecycle.GEOGRAPHY_GENERATING,
            NationalGeographyLifecycle.FAILED,
        }
    ),
    NationalGeographyLifecycle.GEOGRAPHY_GENERATING: frozenset(
        {
            NationalGeographyLifecycle.GEOGRAPHY_READY,
            NationalGeographyLifecycle.FAILED,
        }
    ),
    NationalGeographyLifecycle.GEOGRAPHY_READY: frozenset(),
    NationalGeographyLifecycle.FAILED: frozenset(),
}

RESERVED_DISK_AREA_IDS = frozenset({LEGACY_PHOENIX_AREA_ID})


@dataclass(frozen=True)
class ResolverSuccessInput:
    """Successful resolver output. Agents A–D populate this; this layer freezes it."""

    place: CanonicalPlaceIdentity
    zone_geoids: tuple[str, ...]
    geometry: dict[str, Any]
    timezone: str
    selection_audit: SelectionAuditMetadata
    resolver_policy_id: str = NATIONAL_RESOLVER_POLICY_ID
    census_vintage: str = NATIONAL_CENSUS_VINTAGE
    census_source: str = NATIONAL_CENSUS_SOURCE
    aggregation_spec: ThermalAggregationSpec | None = None


@dataclass(frozen=True)
class NationalGeographyRecord:
    area_id: str | None
    place: CanonicalPlaceIdentity
    lifecycle: NationalGeographyLifecycle
    reference: Literal["NOT_PREPARED"]
    package: NationalGeographyPackage | None
    failure_reason: str | None = None

    @property
    def snapshot_capable(self) -> bool:
        if self.lifecycle != NationalGeographyLifecycle.GEOGRAPHY_READY:
            return False
        if self.package is None:
            return False
        return snapshot_capable(
            to_geography_identity(self.package),
            geography=GeographyReadiness.GEOGRAPHY_READY,
            reference=ReferenceReadiness.NOT_PREPARED,
        )

    @property
    def historical_signal_capable(self) -> bool:
        return False

    def capability_state(self) -> AreaCapabilityState:
        if self.lifecycle == NationalGeographyLifecycle.FAILED:
            geography = GeographyReadiness.FAILED
        elif self.lifecycle == NationalGeographyLifecycle.GEOGRAPHY_READY:
            geography = GeographyReadiness.GEOGRAPHY_READY
        elif self.lifecycle in {
            NationalGeographyLifecycle.PLACE_RESOLVED,
            NationalGeographyLifecycle.GEOGRAPHY_GENERATING,
        }:
            geography = GeographyReadiness.RESOLVING
        else:
            geography = GeographyReadiness.UNRESOLVED
        return AreaCapabilityState(
            geography=geography,
            reference=ReferenceReadiness.NOT_PREPARED,
        )


class InMemoryNationalGeographyStore:
    """Process-local write-once store. Not the public AREA_REGISTRY_V1."""

    def __init__(self) -> None:
        self._by_area_id: dict[str, NationalGeographyRecord] = {}
        self._by_place_key: dict[str, str] = {}
        self._lock = Lock()

    def get(self, area_id: str) -> NationalGeographyRecord | None:
        with self._lock:
            return self._by_area_id.get(area_id)

    def get_by_place_key(self, key: str) -> NationalGeographyRecord | None:
        with self._lock:
            area_id = self._by_place_key.get(key)
            if area_id is None:
                return None
            return self._by_area_id.get(area_id)

    def put_once(self, record: NationalGeographyRecord) -> NationalGeographyRecord:
        if record.area_id is None:
            raise NationalGeographyError("READY records require area_id")
        assert_area_id_not_legacy_phoenix(record.area_id)
        with self._lock:
            existing = self._by_area_id.get(record.area_id)
            if existing is not None:
                if (
                    existing.package is not None
                    and record.package is not None
                    and existing.package.package_sha256 == record.package.package_sha256
                ):
                    return existing
                raise NationalGeographyImmutabilityError(
                    f"area_id {record.area_id!r} is already materialized; "
                    "policy or content change must not overwrite it"
                )
            self._by_area_id[record.area_id] = record
            if record.package is not None:
                self._by_place_key[_place_policy_key(record.package)] = record.area_id
            return record

    def list_area_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._by_area_id)

    def __contains__(self, area_id: str) -> bool:
        with self._lock:
            return area_id in self._by_area_id


def _place_policy_key(package: NationalGeographyPackage) -> str:
    return "|".join(
        (
            package.canonical_place_geoid,
            package.census_vintage,
            package.resolver_policy_id,
            package.census_source,
        )
    )


def place_policy_cache_key(
    *,
    place_geoid: str,
    census_vintage: str,
    resolver_policy_id: str,
    census_source: str = NATIONAL_CENSUS_SOURCE,
) -> str:
    """Cache identity for Agent G. Must not include reference SHA or q_A."""
    return "|".join((place_geoid, census_vintage, resolver_policy_id, census_source))


def begin_place_resolved(place: CanonicalPlaceIdentity) -> NationalGeographyRecord:
    return NationalGeographyRecord(
        area_id=None,
        place=place,
        lifecycle=NationalGeographyLifecycle.PLACE_RESOLVED,
        reference="NOT_PREPARED",
        package=None,
    )


def transition_geography(
    record: NationalGeographyRecord,
    next_status: NationalGeographyLifecycle,
    *,
    reason: str | None = None,
) -> NationalGeographyRecord:
    if record.lifecycle in {
        NationalGeographyLifecycle.GEOGRAPHY_READY,
        NationalGeographyLifecycle.FAILED,
    }:
        raise NationalGeographyError(f"terminal lifecycle {record.lifecycle.value}")
    allowed = _ALLOWED_TRANSITIONS[record.lifecycle]
    if next_status not in allowed:
        raise NationalGeographyError(
            f"invalid transition {record.lifecycle.value} -> {next_status.value}"
        )
    if next_status == NationalGeographyLifecycle.GEOGRAPHY_READY:
        raise NationalGeographyError("GEOGRAPHY_READY is reached only by materialize")
    return NationalGeographyRecord(
        area_id=record.area_id,
        place=record.place,
        lifecycle=next_status,
        reference="NOT_PREPARED",
        package=record.package,
        failure_reason=reason if next_status == NationalGeographyLifecycle.FAILED else None,
    )


def assemble_national_geography_package(
    success: ResolverSuccessInput,
) -> NationalGeographyPackage:
    """Build and validate an immutable package from resolver success."""
    assert_not_legacy_phoenix_policy(success.resolver_policy_id)
    assert_frozen_candidate_policy(
        resolver_policy_id=success.resolver_policy_id,
        algorithm_id=success.selection_audit.algorithm_id,
        seed_rule_id=success.selection_audit.seed_rule_id,
        eligibility_rule_id=success.selection_audit.eligibility_rule_id,
        rook_policy_id=success.selection_audit.rook_policy_id,
        projection_crs=success.selection_audit.projection_crs,
    )
    if len(success.zone_geoids) != EXPECTED_ZONE_COUNT:
        raise NationalGeographyError("resolver success must contain exactly 25 GEOIDs")
    if set(success.zone_geoids) != set(success.selection_audit.selection_order):
        raise NationalGeographyError("zone_geoids must match selection_audit.selection_order")
    if not success.selection_audit.rook_connected:
        raise NationalGeographyError("RESOLVER_INVARIANT_VIOLATION: rook_connected is required")

    canonical_geometry = canonicalize_geography_geojson(success.geometry)
    geom_sha = geometry_sha256_hex(canonical_geometry)
    zone_geoids = tuple(sorted(success.zone_geoids))
    area_id = build_national_area_id(
        place_geoid=success.place.canonical_place_geoid,
        census_vintage=success.census_vintage,
        resolver_policy_id=success.resolver_policy_id,
    )
    spec = success.aggregation_spec or national_aggregation_spec()
    if "phx" in spec.version.lower():
        raise NationalGeographyError(
            "national materializer must not emit a Phoenix aggregation identity"
        )
    if spec.version != NATIONAL_AGGREGATION_POLICY_ID:
        raise NationalGeographyError(
            "aggregation_spec.version must be "
            f"{NATIONAL_AGGREGATION_POLICY_ID}"
        )
    zone_definition_version = build_zone_definition_version(
        census_source=success.census_source,
        zone_type="census_tract",
        census_vintage=success.census_vintage,
    )
    zone_geometry_version = build_zone_geometry_version(
        census_source=success.census_source,
        zone_type="census_tract",
        census_vintage=success.census_vintage,
        place_geoid=success.place.canonical_place_geoid,
        resolver_policy_id=success.resolver_policy_id,
        geometry_sha256=geom_sha,
    )
    draft = NationalGeographyPackage.model_construct(
        schema_version="NATIONAL_GEOGRAPHY_PACKAGE_V1",
        area_id=area_id,
        canonical_place_geoid=success.place.canonical_place_geoid,
        place_name=success.place.place_name,
        state_fips=success.place.state_fips,
        state_abbreviation=success.place.state_abbreviation,
        display_name=success.place.resolved_display_name(),
        zone_geoids=zone_geoids,
        geometry=canonical_geometry,
        geometry_sha256=geom_sha,
        census_vintage=success.census_vintage,
        census_source=success.census_source,
        zone_type="census_tract",
        zone_definition_version=zone_definition_version,
        zone_geometry_version=zone_geometry_version,
        resolver_policy_id=success.resolver_policy_id,
        timezone=success.timezone,
        aggregation_spec=spec,
        expected_zone_count=EXPECTED_ZONE_COUNT,
        zone_id_property="GEOID",
        selection_audit=success.selection_audit,
        package_sha256="0" * 64,
    )
    package_sha = package_identity_sha256(draft, ignore_package_sha=True)
    payload = draft.model_dump(mode="python")
    payload["package_sha256"] = package_sha
    payload["aggregation_spec"] = spec
    payload["selection_audit"] = success.selection_audit
    payload["geometry"] = canonical_geometry
    payload["zone_geoids"] = zone_geoids
    assert_no_forbidden_package_keys(payload)
    return NationalGeographyPackage.model_validate(payload)


def materialize_national_geography(
    success: ResolverSuccessInput,
    *,
    store: InMemoryNationalGeographyStore | None = None,
    prior: NationalGeographyRecord | None = None,
) -> NationalGeographyRecord:
    """PLACE_RESOLVED → GEOGRAPHY_GENERATING → GEOGRAPHY_READY, reference NOT_PREPARED."""
    if prior is None:
        record = begin_place_resolved(success.place)
    else:
        if prior.place.canonical_place_geoid != success.place.canonical_place_geoid:
            raise NationalGeographyError("materialize place does not match PLACE_RESOLVED")
        record = prior
    if record.lifecycle == NationalGeographyLifecycle.PLACE_RESOLVED:
        record = transition_geography(
            record, NationalGeographyLifecycle.GEOGRAPHY_GENERATING
        )
    elif record.lifecycle != NationalGeographyLifecycle.GEOGRAPHY_GENERATING:
        raise NationalGeographyError(
            f"cannot materialize from {record.lifecycle.value}"
        )

    package = assemble_national_geography_package(success)
    ready = NationalGeographyRecord(
        area_id=package.area_id,
        place=success.place,
        lifecycle=NationalGeographyLifecycle.GEOGRAPHY_READY,
        reference="NOT_PREPARED",
        package=package,
    )
    if store is None:
        return ready
    return store.put_once(ready)


def fail_geography(
    record: NationalGeographyRecord,
    *,
    reason: str,
) -> NationalGeographyRecord:
    return transition_geography(
        record, NationalGeographyLifecycle.FAILED, reason=reason
    )


def snapshot_geography_from_national(
    package: NationalGeographyPackage,
) -> SnapshotGeography:
    """Signal B processor input. Does not use ResolvedAreaGeography / AreaConfig."""
    return SnapshotGeography(
        area_id=package.area_id,
        timezone=package.timezone,
        zone_geoids=package.zone_geoids,
        expected_zone_count=package.expected_zone_count,
        aggregation_spec=package.aggregation_spec,
        area_selection_policy_version=package.resolver_policy_id,
        zone_geometry_version=package.zone_geometry_version,
        geometry_sha256=package.geometry_sha256,
        zones_geojson=package.geometry,
        zone_id_property=package.zone_id_property,
    )


def _is_public_areas_tree(root) -> bool:
    from pathlib import Path

    dest = Path(root)
    try:
        resolved = dest.resolve()
    except OSError:
        resolved = dest
    parts = [part.lower() for part in resolved.parts]
    for index in range(len(parts) - 1):
        if parts[index] == "data" and parts[index + 1] == "areas":
            return True
    if resolved.name.lower() == "areas":
        return True
    if (resolved / "registry.json").exists() or (dest / "registry.json").exists():
        return True
    return False


def write_internal_package_dir(root, package: NationalGeographyPackage) -> None:
    """Test/internal dump only. Refuses Phoenix paths and public registry writes."""
    from pathlib import Path

    dest_root = Path(root)
    area_id = package.area_id
    assert_area_id_not_legacy_phoenix(area_id)
    if area_id in RESERVED_DISK_AREA_IDS:
        raise NationalGeographyError("refusing to write a reserved legacy area_id")
    if _is_public_areas_tree(dest_root):
        raise NationalGeographyError("refusing to write into the public area registry tree")
    target = dest_root / area_id
    if _is_public_areas_tree(target):
        raise NationalGeographyError("refusing to write into the public area registry tree")
    if "phoenix-demo" in target.as_posix().lower():
        raise NationalGeographyError("refusing a path that mentions phoenix-demo")
    if "data/areas" in target.as_posix().lower() or "data\\areas" in str(target).lower():
        raise NationalGeographyError("refusing to write into the public area registry tree")
    target.mkdir(parents=True, exist_ok=True)
    (target / "geometry.geojson").write_bytes(
        json.dumps(
            package.geometry, ensure_ascii=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )
    dumped = package.model_dump(mode="json")
    assert_no_forbidden_package_keys(dumped)
    (target / "package.json").write_text(
        json.dumps(dumped, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def package_dump_has_forbidden_keys(package: NationalGeographyPackage) -> bool:
    dumped = package.model_dump(mode="json")
    return bool(FORBIDDEN_PACKAGE_KEYS.intersection(dumped))


def is_public_registry_area_id(area_id: str) -> bool:
    """National IDs are not public registry members. Phoenix remains the legacy ID."""
    if looks_like_national_area_id(area_id):
        return False
    return area_id == LEGACY_PHOENIX_AREA_ID
