"""Materializer: GEOGRAPHY_READY + SNAPSHOT_CAPABLE while reference stays NOT_PREPARED."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.core.area_readiness import (
    GeographyReadiness,
    ReferenceReadiness,
    historical_signal_capable,
    snapshot_capable,
)
from app.core.area_registry import UnsupportedAreaError, load_area_registry, resolve_area_geography
from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import TileAssignmentMethod, ZoneAggregationStatistic
from app.domain.national_geography_package import (
    EXPECTED_ZONE_COUNT,
    LEGACY_PHOENIX_AREA_ID,
    NATIONAL_AGGREGATION_POLICY_ID,
    NATIONAL_ALGORITHM_ID,
    NATIONAL_ELIGIBILITY_RULE_ID,
    NATIONAL_RESOLVER_POLICY_ID,
    NATIONAL_ROOK_POLICY_ID,
    NATIONAL_SEED_RULE_ID,
    CanonicalPlaceIdentity,
    NationalGeographyError,
    NationalGeographyImmutabilityError,
    NationalGeographyLifecycle,
    SelectionAuditMetadata,
    national_selection_audit,
    to_geography_identity,
)
from app.domain.phoenix_v1 import AREA_ID
from app.domain.signals import SignalAvailability
from app.services.national_geography_materializer import (
    InMemoryNationalGeographyStore,
    ResolverSuccessInput,
    assemble_national_geography_package,
    begin_place_resolved,
    fail_geography,
    is_public_registry_area_id,
    materialize_national_geography,
    place_policy_cache_key,
    snapshot_geography_from_national,
    transition_geography,
    write_internal_package_dir,
)
from app.services.snapshot_processor import process_selected_time_snapshot


def _place(*, geoid: str = "1714000", name: str = "TEST_ONLY Chicago", state: str = "IL", fips: str = "17") -> CanonicalPlaceIdentity:
    return CanonicalPlaceIdentity.model_validate(
        {
            "canonical_place_geoid": geoid,
            "place_name": name,
            "state_fips": fips,
            "state_abbreviation": state,
        }
    )


def _geoids(*, prefix: str = "17999000") -> tuple[str, ...]:
    return tuple(f"{prefix}{i:03d}" for i in range(EXPECTED_ZONE_COUNT))


def _audit(
    geoids: tuple[str, ...], **overrides: object
) -> SelectionAuditMetadata:
    if overrides:
        payload = national_selection_audit(
            seed_geoid=geoids[0],
            selection_order=geoids,
            eligible_tract_count=48,
            connected_component_size=40,
        ).model_dump()
        payload.update(overrides)
        return SelectionAuditMetadata.model_validate(payload)
    return national_selection_audit(
        seed_geoid=geoids[0],
        selection_order=geoids,
        eligible_tract_count=48,
        connected_component_size=40,
    )


def _geometry(geoids: tuple[str, ...]) -> dict:
    features = []
    for i, geoid in enumerate(geoids):
        features.append(
            {
                "type": "Feature",
                "properties": {"GEOID": geoid, "NAME": f"tract-{i}"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[float(i), 0.0], [float(i + 1), 0.0], [float(i + 1), 1.0], [float(i), 1.0], [float(i), 0.0]]
                    ],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _success(
    *,
    geoids: tuple[str, ...] | None = None,
    place: CanonicalPlaceIdentity | None = None,
    timezone: str = "America/Chicago",
    resolver_policy_id: str = NATIONAL_RESOLVER_POLICY_ID,
    census_vintage: str = "2025",
    geometry: dict | None = None,
    selection_audit: SelectionAuditMetadata | None = None,
    aggregation_spec: ThermalAggregationSpec | None = None,
) -> ResolverSuccessInput:
    ids = geoids or _geoids()
    return ResolverSuccessInput(
        place=place or _place(),
        zone_geoids=ids,
        geometry=geometry or _geometry(ids),
        timezone=timezone,
        selection_audit=selection_audit or _audit(ids),
        resolver_policy_id=resolver_policy_id,
        census_vintage=census_vintage,
        aggregation_spec=aggregation_spec,
    )


def test_lifecycle_reaches_snapshot_capable_with_reference_not_prepared() -> None:
    prior = begin_place_resolved(_place())
    assert prior.lifecycle == NationalGeographyLifecycle.PLACE_RESOLVED
    assert prior.reference == "NOT_PREPARED"
    assert prior.snapshot_capable is False
    generating = transition_geography(
        prior, NationalGeographyLifecycle.GEOGRAPHY_GENERATING
    )
    record = materialize_national_geography(_success(), prior=generating)
    assert record.lifecycle == NationalGeographyLifecycle.GEOGRAPHY_READY
    assert record.reference == "NOT_PREPARED"
    assert record.snapshot_capable is True
    assert record.historical_signal_capable is False
    caps = record.capability_state()
    assert caps.geography == GeographyReadiness.GEOGRAPHY_READY
    assert caps.reference == ReferenceReadiness.NOT_PREPARED
    assert caps.snapshot_capable is True
    assert caps.historical_signal_capable is False
    identity = to_geography_identity(record.package)
    assert snapshot_capable(
        identity,
        geography=GeographyReadiness.GEOGRAPHY_READY,
        reference=ReferenceReadiness.NOT_PREPARED,
    )
    assert not historical_signal_capable(
        identity,
        geography=GeographyReadiness.GEOGRAPHY_READY,
        reference=ReferenceReadiness.NOT_PREPARED,
    )


def test_materialize_is_idempotent_for_identical_content() -> None:
    store = InMemoryNationalGeographyStore()
    first = materialize_national_geography(_success(), store=store)
    second = materialize_national_geography(_success(), store=store)
    assert first.package.package_sha256 == second.package.package_sha256
    assert first.area_id == second.area_id
    assert store.list_area_ids() == [first.area_id]


def test_policy_change_does_not_mutate_materialized_area() -> None:
    store = InMemoryNationalGeographyStore()
    first = materialize_national_geography(_success(), store=store)
    mutated_ids = _geoids(prefix="17988000")
    with pytest.raises(NationalGeographyImmutabilityError):
        materialize_national_geography(_success(geoids=mutated_ids), store=store)
    kept = store.get(first.area_id)
    assert kept is not None
    assert kept.package.zone_geoids == first.package.zone_geoids
    v2 = materialize_national_geography(
        _success(resolver_policy_id="NATIONAL_PLACE_GEOGRAPHY_V2"),
        store=store,
    )
    assert v2.area_id != first.area_id
    assert first.area_id in store
    assert store.get(first.area_id).package.geometry_sha256 == first.package.geometry_sha256


def test_phoenix_place_materializes_as_distinct_legacy_identity() -> None:
    ids = _geoids(prefix="04999000")
    record = materialize_national_geography(
        _success(
            geoids=ids,
            place=_place(geoid="0455000", name="TEST_ONLY Phoenix", state="AZ", fips="04"),
            timezone="America/Phoenix",
        )
    )
    assert record.area_id == "us-place-0455000-2025-national-place-geography-v1"
    assert record.area_id != LEGACY_PHOENIX_AREA_ID
    assert record.package.resolver_policy_id == NATIONAL_RESOLVER_POLICY_ID
    assert record.package.resolver_policy_id != "PHX_DEMO_AOI_POLICY_V1"
    assert record.package.selection_audit.algorithm_id == NATIONAL_ALGORITHM_ID
    assert "PHX_DEMO" not in record.package.zone_geometry_version


def test_legacy_phoenix_policy_id_is_refused() -> None:
    with pytest.raises(NationalGeographyError, match="legacy Phoenix"):
        assemble_national_geography_package(
            _success(resolver_policy_id="PHX_DEMO_AOI_POLICY_V1")
        )


def test_national_area_is_not_in_public_registry() -> None:
    record = materialize_national_geography(_success())
    assert is_public_registry_area_id(record.area_id) is False
    assert is_public_registry_area_id(AREA_ID) is True
    registry = load_area_registry()
    assert [entry.area_id for entry in registry.areas] == [AREA_ID]
    with pytest.raises(UnsupportedAreaError):
        resolve_area_geography(record.area_id)
    phoenix = resolve_area_geography(AREA_ID)
    assert phoenix.manifest.area_id == AREA_ID
    assert phoenix.timezone == "America/Phoenix"


def test_write_internal_dir_refuses_public_registry_tree(tmp_path: Path) -> None:
    record = materialize_national_geography(_success())
    registry_tree = tmp_path / "areas"
    registry_tree.mkdir()
    (registry_tree / "registry.json").write_text("{}", encoding="utf-8")
    with pytest.raises(NationalGeographyError, match="public area registry"):
        write_internal_package_dir(registry_tree, record.package)
    dest = tmp_path / "national_geography"
    write_internal_package_dir(dest, record.package)
    dumped = json.loads((dest / record.area_id / "package.json").read_text(encoding="utf-8"))
    assert "reference_sha256" not in dumped
    assert "reference_path" not in dumped
    assert dumped["area_id"] == record.area_id


def test_wrong_zone_count_fails() -> None:
    ids = _geoids()
    short = ResolverSuccessInput(
        place=_place(),
        zone_geoids=ids[:24],
        geometry=_geometry(ids[:24]),
        timezone="America/Chicago",
        selection_audit=_audit(ids),
    )
    with pytest.raises(NationalGeographyError, match="exactly 25"):
        assemble_national_geography_package(short)


def test_feature_shuffle_same_package_hash() -> None:
    ids = _geoids()
    geom = _geometry(ids)
    shuffled = {
        "type": "FeatureCollection",
        "features": list(reversed(geom["features"])),
    }
    a = assemble_national_geography_package(_success(geoids=ids, geometry=geom))
    b = assemble_national_geography_package(_success(geoids=ids, geometry=shuffled))
    assert a.geometry_sha256 == b.geometry_sha256
    assert a.package_sha256 == b.package_sha256
    assert a.zone_geoids == tuple(sorted(ids))


def test_snapshot_processor_accepts_national_package_without_thermal_product_claim() -> None:
    record = materialize_national_geography(_success())
    geography = snapshot_geography_from_national(record.package)
    tiles = {"type": "FeatureCollection", "features": []}
    snapshot = process_selected_time_snapshot(
        geography=geography,
        tiles_geojson=tiles,
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        source=ThermalDataSource.REPLAY,
        data_status=DataStatus.REPLAY,
    )
    assert snapshot.area_id == record.area_id
    assert snapshot.availability == SignalAvailability.UNAVAILABLE
    assert snapshot.valid_zone_count == 0
    assert snapshot.expected_zone_count == 25
    assert snapshot.aggregation_spec_version == NATIONAL_AGGREGATION_POLICY_ID


def test_failed_lifecycle_is_not_snapshot_capable() -> None:
    prior = begin_place_resolved(_place())
    failed = fail_geography(prior, reason="INSUFFICIENT_ELIGIBLE_TRACTS")
    assert failed.lifecycle == NationalGeographyLifecycle.FAILED
    assert failed.snapshot_capable is False
    assert failed.capability_state().geography == GeographyReadiness.FAILED
    assert failed.capability_state().reference == ReferenceReadiness.NOT_PREPARED
    with pytest.raises(NationalGeographyError, match="terminal"):
        transition_geography(failed, NationalGeographyLifecycle.GEOGRAPHY_GENERATING)


def test_ready_is_terminal() -> None:
    record = materialize_national_geography(_success())
    with pytest.raises(NationalGeographyError, match="terminal"):
        fail_geography(record, reason="no")


def test_cache_key_omits_reference() -> None:
    key = place_policy_cache_key(
        place_geoid="1714000",
        census_vintage="2025",
        resolver_policy_id=NATIONAL_RESOLVER_POLICY_ID,
    )
    assert "1714000" in key
    assert "2025" in key
    assert "reference" not in key.lower()
    assert "q_a" not in key.lower()


def test_illegal_transition_from_resolved_to_ready() -> None:
    prior = begin_place_resolved(_place())
    with pytest.raises(NationalGeographyError):
        transition_geography(prior, NationalGeographyLifecycle.GEOGRAPHY_READY)


def test_package_stamps_alg1_seed_and_rule_ids() -> None:
    record = materialize_national_geography(_success())
    package = record.package
    assert package.area_id == "us-place-1714000-2025-national-place-geography-v1"
    assert package.schema_version == "NATIONAL_GEOGRAPHY_PACKAGE_V1"
    assert package.resolver_policy_id == NATIONAL_RESOLVER_POLICY_ID
    assert package.selection_audit.algorithm_id == NATIONAL_ALGORITHM_ID
    assert package.selection_audit.seed_geoid == package.zone_geoids[0]
    assert package.selection_audit.seed_rule_id == NATIONAL_SEED_RULE_ID
    assert package.selection_audit.eligibility_rule_id == NATIONAL_ELIGIBILITY_RULE_ID
    assert package.selection_audit.rook_policy_id == NATIONAL_ROOK_POLICY_ID
    assert package.selection_audit.projection_crs == "EPSG:5070"
    assert package.aggregation_spec.version == NATIONAL_AGGREGATION_POLICY_ID
    assert package.zone_geoids == tuple(sorted(package.zone_geoids))
    dumped = package.model_dump(mode="json")
    assert "reference_sha256" not in dumped
    assert "q_A" not in dumped
    assert "hazard_spread_policy" not in dumped
    assert "area_config_sha256" not in dumped


def test_alg2_cannot_use_national_place_geography_v1() -> None:
    ids = _geoids()
    with pytest.raises(NationalGeographyError, match="ALG1"):
        assemble_national_geography_package(
            _success(
                selection_audit=_audit(
                    ids, algorithm_id="ALG2_MEDOID_DISTANCE_LEX_V1"
                )
            )
        )


def test_phoenix_aggregation_identity_is_refused() -> None:
    phoenix_spec = ThermalAggregationSpec(
        version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
        statistic=ZoneAggregationStatistic.MEAN,
        minimum_coverage_ratio=None,
        zero_tile_behavior="insufficient_evidence",
        boundary_behavior="centroid_within_zone",
    )
    with pytest.raises(NationalGeographyError, match="Phoenix aggregation"):
        assemble_national_geography_package(_success(aggregation_spec=phoenix_spec))


def test_write_internal_dir_refuses_data_areas_without_registry(tmp_path: Path) -> None:
    record = materialize_national_geography(_success())
    data_areas = tmp_path / "data" / "areas"
    data_areas.mkdir(parents=True)
    with pytest.raises(NationalGeographyError, match="public area registry"):
        write_internal_package_dir(data_areas, record.package)
    assert list(data_areas.iterdir()) == []


def test_materializer_source_stays_vendor_and_phoenix_write_free() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "national_geography_materializer.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "fortyguard" not in text.lower()
    assert "phoenix_v1_reference" not in text
    assert "resolve_ready_area_package" not in text
    assert "load_frozen_phoenix_v1_area_config" not in text
    assert "data/areas/registry.json" in text
    assert "Does not write data/areas/registry.json" in text
