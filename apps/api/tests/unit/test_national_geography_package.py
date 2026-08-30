"""National geography package identity. No Phoenix mutation, no reference fields."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.national_geography_package import (
    FORBIDDEN_PACKAGE_KEYS,
    LEGACY_PHOENIX_AREA_ID,
    NATIONAL_ALGORITHM_ID,
    NATIONAL_CENSUS_VINTAGE,
    NATIONAL_ELIGIBILITY_RULE_ID,
    NATIONAL_RESOLVER_POLICY_ID,
    NATIONAL_ROOK_POLICY_ID,
    CanonicalPlaceIdentity,
    NationalGeographyError,
    SelectionAuditMetadata,
    assert_area_id_not_legacy_phoenix,
    build_national_area_id,
    canonicalize_geography_geojson,
    geometry_sha256_hex,
    looks_like_national_area_id,
    national_selection_audit,
    resolver_policy_slug,
)
from app.domain.phoenix_v1 import AREA_ID


def _place(**overrides: object) -> CanonicalPlaceIdentity:
    payload = {
        "canonical_place_geoid": "1714000",
        "place_name": "TEST_ONLY Chicago",
        "state_fips": "17",
        "state_abbreviation": "IL",
    }
    payload.update(overrides)
    return CanonicalPlaceIdentity.model_validate(payload)


def _geoids(n: int = 25, *, prefix: str = "17999000") -> tuple[str, ...]:
    return tuple(f"{prefix}{i:03d}" for i in range(n))


def _audit(geoids: tuple[str, ...] | None = None, **overrides: object) -> SelectionAuditMetadata:
    ids = geoids or _geoids()
    if overrides:
        payload = national_selection_audit(
            seed_geoid=ids[0],
            selection_order=ids,
            eligible_tract_count=40,
            connected_component_size=32,
        ).model_dump()
        payload.update(overrides)
        return SelectionAuditMetadata.model_validate(payload)
    return national_selection_audit(
        seed_geoid=ids[0],
        selection_order=ids,
        eligible_tract_count=40,
        connected_component_size=32,
    )


def test_area_id_is_vintage_and_policy_versioned() -> None:
    area_id = build_national_area_id(
        place_geoid="1714000",
        census_vintage="2025",
        resolver_policy_id=NATIONAL_RESOLVER_POLICY_ID,
    )
    assert area_id == "us-place-1714000-2025-national-place-geography-v1"
    assert NATIONAL_CENSUS_VINTAGE == "2025"
    assert looks_like_national_area_id(area_id)
    assert area_id != LEGACY_PHOENIX_AREA_ID
    assert area_id != AREA_ID


def test_weaker_scheme_without_vintage_is_not_used() -> None:
    weaker = f"us-place-1714000-{NATIONAL_RESOLVER_POLICY_ID}"
    assert not looks_like_national_area_id(weaker)
    assert build_national_area_id(
        place_geoid="1714000",
        census_vintage="2025",
        resolver_policy_id=NATIONAL_RESOLVER_POLICY_ID,
    ) != weaker


def test_phoenix_place_geoid_still_is_not_phoenix_demo() -> None:
    area_id = build_national_area_id(
        place_geoid="0455000",
        census_vintage="2025",
        resolver_policy_id=NATIONAL_RESOLVER_POLICY_ID,
    )
    assert area_id == "us-place-0455000-2025-national-place-geography-v1"
    assert area_id != "phoenix-demo"


def test_policy_change_and_vintage_change_new_area_id() -> None:
    v1 = build_national_area_id(
        place_geoid="1714000",
        census_vintage="2025",
        resolver_policy_id="NATIONAL_PLACE_GEOGRAPHY_V1",
    )
    v2 = build_national_area_id(
        place_geoid="1714000",
        census_vintage="2025",
        resolver_policy_id="NATIONAL_PLACE_GEOGRAPHY_V2",
    )
    vintage = build_national_area_id(
        place_geoid="1714000",
        census_vintage="2026",
        resolver_policy_id="NATIONAL_PLACE_GEOGRAPHY_V1",
    )
    assert v1 != v2
    assert v1 != vintage
    assert v2 != vintage


def test_legacy_phoenix_area_id_is_rejected() -> None:
    with pytest.raises(NationalGeographyError, match="phoenix-demo"):
        assert_area_id_not_legacy_phoenix("phoenix-demo")
    with pytest.raises(NationalGeographyError, match="phoenix-demo"):
        assert_area_id_not_legacy_phoenix("PHOENIX-DEMO")


def test_place_identity_rejects_state_mismatch() -> None:
    with pytest.raises(ValidationError):
        _place(state_fips="04")


def test_place_identity_rejects_short_geoid() -> None:
    with pytest.raises(ValidationError):
        _place(canonical_place_geoid="14000")


def test_audit_requires_exactly_25_and_seed() -> None:
    ids = _geoids()
    with pytest.raises(ValidationError):
        _audit(ids[:24])
    with pytest.raises(ValidationError):
        _audit(ids, seed_geoid="17999000999")


def test_audit_requires_algorithm_and_seed_rule_ids() -> None:
    ids = _geoids()
    with pytest.raises(ValidationError):
        SelectionAuditMetadata.model_validate(
            {
                "seed_geoid": ids[0],
                "selection_order": ids,
                "eligible_tract_count": 40,
                "connected_component_size": 32,
                "rook_connected": True,
                "eligibility_rule_id": NATIONAL_ELIGIBILITY_RULE_ID,
                "rook_policy_id": NATIONAL_ROOK_POLICY_ID,
                "projection_crs": "EPSG:5070",
            }
        )
    with pytest.raises(ValidationError, match="legacy Phoenix"):
        _audit(ids, algorithm_id="PHX_DEMO_AOI_POLICY_V1")


def test_resolver_policy_slug_is_mechanical() -> None:
    assert resolver_policy_slug("NATIONAL_PLACE_GEOGRAPHY_V1") == (
        "national-place-geography-v1"
    )


def test_canonical_geojson_is_order_independent() -> None:
    ids = _geoids()
    features = []
    for i, geoid in enumerate(ids):
        features.append(
            {
                "type": "Feature",
                "properties": {"NAME": f"t{i}", "GEOID": geoid},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[i, 0], [i + 1, 0], [i + 1, 1], [i, 1], [i, 0]]
                    ],
                },
            }
        )
    forward = {"type": "FeatureCollection", "features": features}
    reversed_fc = {"type": "FeatureCollection", "features": list(reversed(features))}
    assert geometry_sha256_hex(forward) == geometry_sha256_hex(reversed_fc)
    canonical = canonicalize_geography_geojson(reversed_fc)
    assert [f["properties"]["GEOID"] for f in canonical["features"]] == list(ids)
    assert list(canonical["features"][0]["properties"])[0] == "GEOID"


def test_package_model_forbids_reference_fields() -> None:
    from app.services.national_geography_materializer import (
        ResolverSuccessInput,
        assemble_national_geography_package,
    )

    ids = _geoids()
    features = [
        {
            "type": "Feature",
            "properties": {"GEOID": geoid},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[i, 0], [i + 1, 0], [i + 1, 1], [i, 1], [i, 0]]],
            },
        }
        for i, geoid in enumerate(ids)
    ]
    package = assemble_national_geography_package(
        ResolverSuccessInput(
            place=_place(),
            zone_geoids=ids,
            geometry={"type": "FeatureCollection", "features": features},
            timezone="America/Chicago",
            selection_audit=_audit(ids),
        )
    )
    dumped = package.model_dump(mode="json")
    assert FORBIDDEN_PACKAGE_KEYS.isdisjoint(dumped)
    assert package.resolver_policy_id == NATIONAL_RESOLVER_POLICY_ID
    assert package.selection_audit.algorithm_id == NATIONAL_ALGORITHM_ID
    assert package.selection_audit.seed_geoid == ids[0]
    assert package.selection_audit.seed_rule_id
    assert package.aggregation_spec.version == (
        "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
    )
    with pytest.raises(ValidationError):
        package.model_validate({**dumped, "reference_sha256": "a" * 64})
    with pytest.raises(ValidationError):
        package.model_validate({**dumped, "q_A": 0.12})
    with pytest.raises(ValidationError):
        package.model_validate({**dumped, "hazard_spread_policy": "x"})
    with pytest.raises(ValidationError):
        package.model_validate({**dumped, "area_config_sha256": "b" * 64})


def test_domain_source_has_no_vendor_or_phoenix_loader_imports() -> None:
    source = Path(__file__).resolve().parents[2] / "app" / "domain" / "national_geography_package.py"
    text = source.read_text(encoding="utf-8")
    assert "fortyguard" not in text.lower()
    assert "phoenix_v1_reference" not in text
    assert "resolve_ready_area_package" not in text
    assert "load_frozen_phoenix_v1_area_config" not in text
