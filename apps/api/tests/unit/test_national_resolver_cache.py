"""National resolver cache identity is geography-only and deploy-sized."""

import json
from pathlib import Path

import pytest

from app.services.national_resolver_cache import (
    CACHE_IDENTITY_FIELDS,
    DEFAULT_CENSUS_VINTAGE,
    FORBIDDEN_REFERENCE_FIELDS,
    FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    MEASURED_PHOENIX_25_GEOJSON_BYTES,
    RESOLVER_CACHE_IDENTITY_VERSION,
    ResolverCacheError,
    cache_record_path,
    estimate_adjacency_seconds,
    estimate_resolved_package_bytes,
    estimate_state_polygon_load_seconds,
    gazetteer_place_national_zip_url,
    gazetteer_tracts_national_zip_url,
    read_resolved_geography,
    resolver_cache_document,
    resolver_cache_fingerprint,
    state_fips_from_place_geoid,
    strategy_footprints,
    tiger_place_zip_url,
    tiger_tract_zip_url,
    write_resolved_geography,
)

_PHOENIX = "0455000"
_POLICY = "NR_AOI_POLICY_TEST_V1"
_TRACTS = [f"0401310{i:04d}" for i in range(25)]
_SHA = "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"
_PHOENIX_REFERENCE_SHA = "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c"


def _fp(**overrides: object) -> str:
    payload = {
        "canonical_place_geoid": _PHOENIX,
        "census_vintage": DEFAULT_CENSUS_VINTAGE,
        "resolver_policy_version": _POLICY,
    }
    payload.update(overrides)
    return resolver_cache_fingerprint(**payload)


def _payload() -> dict[str, object]:
    return {"zone_geoids": list(_TRACTS), "geometry_sha256": _SHA}


def test_identical_geography_inputs_share_a_fingerprint() -> None:
    assert _fp() == _fp()
    assert len(_fp()) == 64


def test_cache_identity_fields_are_exactly_the_required_set() -> None:
    doc = resolver_cache_document(
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
    )
    assert tuple(doc) == CACHE_IDENTITY_FIELDS
    assert set(doc) == {
        "identity_version",
        "canonical_place_geoid",
        "census_vintage",
        "resolver_policy_version",
    }
    assert doc["identity_version"] == RESOLVER_CACHE_IDENTITY_VERSION
    assert doc["canonical_place_geoid"] == _PHOENIX
    assert "reference" not in str(doc).lower()


def test_place_vintage_or_policy_changes_the_key() -> None:
    baseline = _fp()
    assert _fp(canonical_place_geoid="0644000") != baseline
    assert _fp(census_vintage="TIGER2024") != baseline
    assert _fp(resolver_policy_version="NR_AOI_POLICY_TEST_V2") != baseline


def test_historical_reference_is_not_part_of_the_key() -> None:
    names = resolver_cache_fingerprint.__code__.co_varnames
    assert "reference" not in names
    assert "reference_sha256" not in names
    assert "canonical_place_geoid" in names
    assert "census_vintage" in names
    assert "resolver_policy_version" in names
    for field in FORBIDDEN_REFERENCE_FIELDS:
        assert field not in names
    with pytest.raises(TypeError):
        resolver_cache_fingerprint(  # type: ignore[call-arg]
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
            reference_sha256=_PHOENIX_REFERENCE_SHA,
        )


def test_policy_or_place_cannot_smuggle_reference_tokens() -> None:
    with pytest.raises(ResolverCacheError, match="reference"):
        _fp(resolver_policy_version="USES_HISTORICAL_REFERENCE_V1")
    with pytest.raises(ResolverCacheError, match="7-digit"):
        _fp(canonical_place_geoid="phoenix-demo")
    with pytest.raises(ResolverCacheError, match="TIGER"):
        _fp(census_vintage="2025")


def test_state_fips_and_census_urls_are_deterministic() -> None:
    assert state_fips_from_place_geoid(_PHOENIX) == "04"
    assert tiger_tract_zip_url(
        census_vintage=DEFAULT_CENSUS_VINTAGE, state_fips="04"
    ) == "https://www2.census.gov/geo/tiger/TIGER2025/TRACT/tl_2025_04_tract.zip"
    assert tiger_place_zip_url(
        census_vintage=DEFAULT_CENSUS_VINTAGE, state_fips="06"
    ) == "https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_06_place.zip"
    assert gazetteer_place_national_zip_url(year=2025).endswith(
        "2025_Gazetteer/2025_Gaz_place_national.zip"
    )
    assert gazetteer_tracts_national_zip_url(year=2025).endswith(
        "2025_Gazetteer/2025_Gaz_tracts_national.zip"
    )


def test_disk_cache_roundtrip_is_geography_only(tmp_path: Path) -> None:
    path = write_resolved_geography(
        tmp_path,
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
        payload=_payload(),
    )
    loaded = read_resolved_geography(
        tmp_path,
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
    )
    assert loaded is not None
    assert loaded["zone_geoids"] == _TRACTS
    assert loaded["geometry_sha256"] == _SHA
    blob = path.read_text(encoding="utf-8").lower()
    assert "reference" not in blob
    assert "fortyguard" not in blob
    assert (
        read_resolved_geography(
            tmp_path,
            canonical_place_geoid="0644000",
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
        )
        is None
    )


def test_payload_rejects_reference_and_wrong_zone_count(tmp_path: Path) -> None:
    with pytest.raises(ResolverCacheError, match="reference"):
        write_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
            payload={**_payload(), "reference_version": "PHX_ZTSI_REF_V1"},
        )
    with pytest.raises(ResolverCacheError, match="exactly 25"):
        write_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
            payload={"zone_geoids": _TRACTS[:3], "geometry_sha256": _SHA},
        )


def test_footprint_estimates_keep_national_bundle_off_the_hot_path() -> None:
    footprints = strategy_footprints()
    assert (
        footprints["A_bundle_full_national"]["repo_or_image_bytes"]
        > footprints["B_place_registry_plus_state_tracts"]["ship_bytes"] * 100
    )
    assert estimate_resolved_package_bytes() == MEASURED_PHOENIX_25_GEOJSON_BYTES
    assert estimate_resolved_package_bytes(compressed=True) < 20_000
    assert estimate_adjacency_seconds(373) == pytest.approx(0.803, abs=0.001)
    assert estimate_adjacency_seconds(2327) > 20
    assert estimate_state_polygon_load_seconds(MEASURED_PHOENIX_25_GEOJSON_BYTES) < 1
    assert estimate_state_polygon_load_seconds(32_558_476) > 40


def test_frozen_candidate_policy_token_is_accepted() -> None:
    fp = _fp(resolver_policy_version=FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION)
    assert fp != _fp()
    assert len(fp) == 64
    doc = resolver_cache_document(
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    )
    assert doc["resolver_policy_version"] == "NATIONAL_PLACE_GEOGRAPHY_V1"
    assert "reference_sha256" not in doc


def test_payload_rejects_statewide_tiger(tmp_path: Path) -> None:
    with pytest.raises(ResolverCacheError, match="statewide TIGER"):
        write_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
            payload={**_payload(), "tiger_tract_zip": "tl_2025_04_tract.zip"},
        )
    statewide = list(_TRACTS) + [f"0401399{i:04d}" for i in range(26, 1766)]
    with pytest.raises(ResolverCacheError, match="exactly 25"):
        write_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
            payload={"zone_geoids": statewide, "geometry_sha256": _SHA},
        )


def test_policy_change_is_a_miss_not_a_reuse(tmp_path: Path) -> None:
    write_resolved_geography(
        tmp_path,
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
        payload=_payload(),
    )
    assert (
        read_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
        )
        is None
    )


def _tamper_record(tmp_path: Path, **patches: object) -> None:
    fingerprint = _fp()
    path = cache_record_path(tmp_path, fingerprint)
    document = json.loads(path.read_text(encoding="utf-8"))
    document.update(patches)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def test_read_fails_closed_on_fingerprint_mismatch(tmp_path: Path) -> None:
    write_resolved_geography(
        tmp_path,
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
        payload=_payload(),
    )
    _tamper_record(tmp_path, fingerprint="0" * 64)
    with pytest.raises(ResolverCacheError, match="fingerprint does not match"):
        read_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
        )


def test_read_fails_closed_on_policy_mismatch(tmp_path: Path) -> None:
    write_resolved_geography(
        tmp_path,
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
        payload=_payload(),
    )
    fingerprint = _fp()
    path = cache_record_path(tmp_path, fingerprint)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["identity"]["resolver_policy_version"] = (
        FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION
    )
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ResolverCacheError, match="policy mismatch"):
        read_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
        )


def test_read_fails_closed_on_identity_key_mismatch(tmp_path: Path) -> None:
    write_resolved_geography(
        tmp_path,
        canonical_place_geoid=_PHOENIX,
        census_vintage=DEFAULT_CENSUS_VINTAGE,
        resolver_policy_version=_POLICY,
        payload=_payload(),
    )
    fingerprint = _fp()
    path = cache_record_path(tmp_path, fingerprint)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["identity"]["reference_sha256"] = _PHOENIX_REFERENCE_SHA
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ResolverCacheError, match="reference"):
        read_resolved_geography(
            tmp_path,
            canonical_place_geoid=_PHOENIX,
            census_vintage=DEFAULT_CENSUS_VINTAGE,
            resolver_policy_version=_POLICY,
        )
