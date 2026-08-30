"""Geography-only cache and footprint helpers for national 25-zone resolution.

Cache identity is (canonical place GEOID, Census vintage, resolver policy
version). It must not include historical reference identity.

No vendor I/O. No Census download at import. No FastAPI route. No Render or
Docker defaults.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Final, Mapping

RESOLVER_CACHE_IDENTITY_VERSION: Final = "hva-signal-national-resolver-cache-v1"
DEFAULT_CENSUS_VINTAGE: Final = "TIGER2025"
FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION: Final = "NATIONAL_PLACE_GEOGRAPHY_V1"
CENSUS_PUBLIC_ORIGIN: Final = "https://www2.census.gov"

CACHE_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "identity_version",
    "canonical_place_geoid",
    "census_vintage",
    "resolver_policy_version",
)

# Geography-only 25-zone record. Statewide TIGER and historical reference stay out.
ALLOWED_RESOLVED_FIELDS: Final[frozenset[str]] = frozenset(
    {"zone_geoids", "geometry_sha256", "timezone"}
)

_PLACE_GEOID_RE = re.compile(r"^[0-9]{7}$")
_VINTAGE_RE = re.compile(r"^TIGER(20[0-9]{2})$")
_YEAR_ONLY_RE = re.compile(r"^(20[0-9]{2})$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Keys that would couple geography cache identity to Signal A / historical
# reference. Forbidden in both the key document and the stored payload.
FORBIDDEN_REFERENCE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "reference",
        "reference_version",
        "reference_path",
        "reference_sha256",
        "reference_protocol_id",
        "historical_reference",
        "historical_reference_window",
        "historical_reference_sha",
        "observations",
        "observations_path",
        "ready_package",
        "q_A",
        "q_a",
        "decision8",
        "decision_8",
        "fortyguard",
        "area_id",
        "target_timestamp",
    }
)

# Statewide TIGER / source archives must never be the cached value.
FORBIDDEN_STATEWIDE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "statewide",
        "statewide_tracts",
        "statewide_geometries",
        "tiger",
        "tiger_zip",
        "tiger_tract_zip",
        "tiger_place_zip",
        "shapefile",
        "shp",
        "eligible_tracts",
        "all_tracts",
        "state_tracts",
        "national_tracts",
        "geometry_collection",
        "features",
    }
)

# Measured 2026-08-30. Public Census.gov HEAD + local AZ TIGER + Phoenix package.
# Local TIGER lives under gitignored workforce/; do not commit those zips.
MEASURED_PHOENIX_25_GEOJSON_BYTES: Final = 62_999
MEASURED_PHOENIX_25_GZIP9_BYTES: Final = 11_301
MEASURED_PHOENIX_ELIGIBLE_TRACTS: Final = 373
MEASURED_PHOENIX_ADJACENCY_S: Final = 0.803
MEASURED_AZ_TRACT_ZIP_BYTES: Final = 8_521_817
MEASURED_AZ_PLACE_ZIP_BYTES: Final = 2_821_601
MEASURED_AZ_TRACT_COUNT: Final = 1_765
MEASURED_AZ_TRACT_LOAD_S: Final = 17.072
MEASURED_AZ_PLACE_LOAD_S: Final = 6.316
MEASURED_GAZETTEER_PLACE_ZIP_BYTES: Final = 1_214_053
MEASURED_GAZETTEER_TRACT_ZIP_BYTES: Final = 2_332_377
MEASURED_NATIONAL_PLACE_COUNT: Final = 32_350
MEASURED_NATIONAL_TRACT_COUNT: Final = 85_396
LISTING_NATIONAL_TRACT_ZIP_SUM_BYTES: Final = 423_880_556
LISTING_NATIONAL_PLACE_ZIP_SUM_BYTES: Final = 145_507_745
HEAD_CA_TRACT_ZIP_BYTES: Final = 32_558_476
HEAD_TX_TRACT_ZIP_BYTES: Final = 32_785_064
HEAD_CB2024_US_TRACT_500K_ZIP_BYTES: Final = 57_829_655

_PHOENIX_ADJ_PAIRS: Final = (
    MEASURED_PHOENIX_ELIGIBLE_TRACTS * (MEASURED_PHOENIX_ELIGIBLE_TRACTS - 1) // 2
)


class ResolverCacheError(ValueError):
    """Invalid geography-cache identity or payload."""


def _reject_reference_fields(document: Mapping[str, Any], *, label: str) -> None:
    forbidden = sorted(set(document) & FORBIDDEN_REFERENCE_FIELDS)
    if forbidden:
        raise ResolverCacheError(
            f"{label} must not include historical reference or non-geography fields: {forbidden}"
        )
    blob = " ".join(str(key) for key in document).lower()
    if "reference" in blob or "fortyguard" in blob:
        raise ResolverCacheError(f"{label} must not mention reference or vendor identity")


def _reject_statewide_fields(document: Mapping[str, Any], *, label: str) -> None:
    forbidden = sorted(set(document) & FORBIDDEN_STATEWIDE_FIELDS)
    if forbidden:
        raise ResolverCacheError(
            f"{label} must persist only the 25-zone package, not statewide TIGER: {forbidden}"
        )
    blob = " ".join(str(key) for key in document).lower()
    if "tiger" in blob or "statewide" in blob or "shapefile" in blob:
        raise ResolverCacheError(
            f"{label} must not include statewide TIGER or shapefile archives"
        )


def _require_identity_match(stored: Any, expected: dict[str, str]) -> None:
    if not isinstance(stored, dict):
        raise ResolverCacheError("cache record identity is missing or invalid")
    _reject_reference_fields(stored, label="cache record identity")
    stored_keys = set(stored)
    expected_keys = set(expected)
    if stored_keys != expected_keys:
        raise ResolverCacheError("cache record identity key mismatch")
    if stored == expected:
        return
    if stored.get("resolver_policy_version") != expected["resolver_policy_version"]:
        raise ResolverCacheError("cache record policy mismatch")
    raise ResolverCacheError("cache record identity does not match request")


def normalize_place_geoid(value: str) -> str:
    """Require a 7-digit Census place GEOID (state FIPS + place FIPS)."""
    text = value.strip()
    if not _PLACE_GEOID_RE.fullmatch(text):
        raise ResolverCacheError(
            "canonical_place_geoid must be a 7-digit Census place GEOID"
        )
    return text


def state_fips_from_place_geoid(place_geoid: str) -> str:
    return normalize_place_geoid(place_geoid)[:2]


def normalize_census_vintage(value: str) -> str:
    text = value.strip()
    year_only = _YEAR_ONLY_RE.fullmatch(text)
    if year_only is not None:
        text = f"TIGER{year_only.group(1)}"
    if not _VINTAGE_RE.fullmatch(text):
        raise ResolverCacheError(
            "census_vintage must look like 2025 or TIGER2025"
        )
    return text


def normalize_policy_version(value: str) -> str:
    text = value.strip()
    if not text or not _TOKEN_RE.fullmatch(text):
        raise ResolverCacheError(
            "resolver_policy_version must be a non-empty token "
            "[A-Za-z0-9._-]+ (no spaces, no reference strings)"
        )
    lowered = text.lower()
    if "reference" in lowered or "fortyguard" in lowered:
        raise ResolverCacheError(
            "resolver_policy_version must not include historical reference or vendor tokens"
        )
    return text


def vintage_year(census_vintage: str) -> int:
    match = _VINTAGE_RE.fullmatch(normalize_census_vintage(census_vintage))
    assert match is not None
    return int(match.group(1))


def resolver_cache_document(
    *,
    canonical_place_geoid: str,
    census_vintage: str,
    resolver_policy_version: str,
) -> dict[str, str]:
    """Canonical cache-identity document. Geography inputs only."""
    document = {
        "identity_version": RESOLVER_CACHE_IDENTITY_VERSION,
        "canonical_place_geoid": normalize_place_geoid(canonical_place_geoid),
        "census_vintage": normalize_census_vintage(census_vintage),
        "resolver_policy_version": normalize_policy_version(resolver_policy_version),
    }
    if tuple(document) != CACHE_IDENTITY_FIELDS:
        raise ResolverCacheError("resolver cache identity fields are not the required set")
    _reject_reference_fields(document, label="resolver cache identity")
    return document


def resolver_cache_fingerprint(
    *,
    canonical_place_geoid: str,
    census_vintage: str,
    resolver_policy_version: str,
) -> str:
    """Stable SHA-256 hex key. Omits historical reference identity."""
    document = resolver_cache_document(
        canonical_place_geoid=canonical_place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )
    blob = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cache_record_path(root: Path, fingerprint: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ResolverCacheError("fingerprint must be a 64-char lowercase hex SHA-256")
    return (
        Path(root)
        / "national_resolver"
        / RESOLVER_CACHE_IDENTITY_VERSION
        / fingerprint[:2]
        / f"{fingerprint}.json"
    )


def validate_resolved_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Accept a geography-only resolved 25-zone record."""
    _reject_reference_fields(payload, label="resolved payload")
    _reject_statewide_fields(payload, label="resolved payload")
    extra = sorted(set(payload) - ALLOWED_RESOLVED_FIELDS)
    if extra:
        raise ResolverCacheError(
            "resolved payload must persist only the 25-zone package; "
            f"unexpected fields: {extra}"
        )
    geoids = payload.get("zone_geoids")
    if not isinstance(geoids, list) or len(geoids) != 25:
        raise ResolverCacheError("resolved payload must contain exactly 25 zone_geoids")
    cleaned: list[str] = []
    for geoid in geoids:
        if not isinstance(geoid, str) or not re.fullmatch(r"[0-9]{11}", geoid):
            raise ResolverCacheError("zone_geoids must be 11-digit Census tract GEOIDs")
        cleaned.append(geoid)
    if len(set(cleaned)) != 25:
        raise ResolverCacheError("zone_geoids must be unique")
    geometry_sha256 = payload.get("geometry_sha256")
    if not isinstance(geometry_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", geometry_sha256
    ):
        raise ResolverCacheError("geometry_sha256 must be a 64-char lowercase hex digest")
    record = {
        "zone_geoids": cleaned,
        "geometry_sha256": geometry_sha256,
    }
    if "timezone" in payload:
        tz = payload["timezone"]
        if not isinstance(tz, str) or not tz:
            raise ResolverCacheError("timezone must be a non-empty string when present")
        record["timezone"] = tz
    return record


def write_resolved_geography(
    root: Path,
    *,
    canonical_place_geoid: str,
    census_vintage: str,
    resolver_policy_version: str,
    payload: Mapping[str, Any],
) -> Path:
    """Persist a geography-only resolved package under the identity key."""
    identity = resolver_cache_document(
        canonical_place_geoid=canonical_place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )
    body = validate_resolved_payload(payload)
    fingerprint = resolver_cache_fingerprint(
        canonical_place_geoid=canonical_place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )
    path = cache_record_path(root, fingerprint)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "identity": identity,
        "fingerprint": fingerprint,
        "resolved": body,
    }
    _reject_reference_fields(document, label="cache record")
    _reject_statewide_fields(document, label="cache record")
    path.write_text(
        json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path


def read_resolved_geography(
    root: Path,
    *,
    canonical_place_geoid: str,
    census_vintage: str,
    resolver_policy_version: str,
) -> dict[str, Any] | None:
    fingerprint = resolver_cache_fingerprint(
        canonical_place_geoid=canonical_place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )
    path = cache_record_path(root, fingerprint)
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ResolverCacheError("cache record is not valid JSON") from exc
    if not isinstance(document, dict):
        raise ResolverCacheError("cache record must be a JSON object")
    _reject_reference_fields(document, label="cache record")
    _reject_statewide_fields(document, label="cache record")
    if document.get("fingerprint") != fingerprint:
        raise ResolverCacheError("cache record fingerprint does not match identity")
    expected_identity = resolver_cache_document(
        canonical_place_geoid=canonical_place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )
    _require_identity_match(document.get("identity"), expected_identity)
    resolved = document.get("resolved")
    if not isinstance(resolved, dict):
        raise ResolverCacheError("cache record missing resolved geography")
    return validate_resolved_payload(resolved)


def tiger_tract_zip_url(*, census_vintage: str, state_fips: str) -> str:
    """Deterministic public TIGER/Line tract zip. Does not fetch."""
    vintage = normalize_census_vintage(census_vintage)
    if not re.fullmatch(r"[0-9]{2}", state_fips):
        raise ResolverCacheError("state_fips must be two digits")
    year = vintage_year(vintage)
    return (
        f"{CENSUS_PUBLIC_ORIGIN}/geo/tiger/{vintage}/TRACT/"
        f"tl_{year}_{state_fips}_tract.zip"
    )


def tiger_place_zip_url(*, census_vintage: str, state_fips: str) -> str:
    """Deterministic public TIGER/Line place zip. Does not fetch."""
    vintage = normalize_census_vintage(census_vintage)
    if not re.fullmatch(r"[0-9]{2}", state_fips):
        raise ResolverCacheError("state_fips must be two digits")
    year = vintage_year(vintage)
    return (
        f"{CENSUS_PUBLIC_ORIGIN}/geo/tiger/{vintage}/PLACE/"
        f"tl_{year}_{state_fips}_place.zip"
    )


def gazetteer_place_national_zip_url(*, year: int = 2025) -> str:
    if year < 2020 or year > 2100:
        raise ResolverCacheError("gazetteer year out of range")
    return (
        f"{CENSUS_PUBLIC_ORIGIN}/geo/docs/maps-data/data/gazetteer/"
        f"{year}_Gazetteer/{year}_Gaz_place_national.zip"
    )


def gazetteer_tracts_national_zip_url(*, year: int = 2025) -> str:
    if year < 2020 or year > 2100:
        raise ResolverCacheError("gazetteer year out of range")
    return (
        f"{CENSUS_PUBLIC_ORIGIN}/geo/docs/maps-data/data/gazetteer/"
        f"{year}_Gazetteer/{year}_Gaz_tracts_national.zip"
    )


def estimate_resolved_package_bytes(*, compressed: bool = False) -> int:
    """Phoenix-measured 25-zone GeoJSON size. Urban vertex density is similar."""
    return (
        MEASURED_PHOENIX_25_GZIP9_BYTES
        if compressed
        else MEASURED_PHOENIX_25_GEOJSON_BYTES
    )


def estimate_adjacency_seconds(eligible_tracts: int) -> float:
    """Scale Phoenix rook-adjacency time by pair count (O(n^2) bbox+boundary)."""
    if eligible_tracts < 2:
        return 0.0
    pairs = eligible_tracts * (eligible_tracts - 1) // 2
    return MEASURED_PHOENIX_ADJACENCY_S * (pairs / _PHOENIX_ADJ_PAIRS)


def estimate_state_polygon_load_seconds(state_tract_zip_bytes: int) -> float:
    """Scale naive full-state shapefile parse time from the AZ measurement."""
    if state_tract_zip_bytes <= 0:
        return 0.0
    return MEASURED_AZ_TRACT_LOAD_S * (
        state_tract_zip_bytes / MEASURED_AZ_TRACT_ZIP_BYTES
    )


def strategy_footprints() -> dict[str, dict[str, Any]]:
    """Deploy-facing size model for strategies A–E. Bytes are measured or listed."""
    resolved = estimate_resolved_package_bytes()
    return {
        "A_bundle_full_national": {
            "repo_or_image_bytes": LISTING_NATIONAL_TRACT_ZIP_SUM_BYTES
            + LISTING_NATIONAL_PLACE_ZIP_SUM_BYTES,
            "startup_load": "all states",
            "runtime_network": "none after image pull",
        },
        "B_place_registry_plus_state_tracts": {
            "ship_bytes": MEASURED_GAZETTEER_PLACE_ZIP_BYTES,
            "per_state_tract_zip_bytes_az": MEASURED_AZ_TRACT_ZIP_BYTES,
            "per_state_tract_zip_bytes_ca": HEAD_CA_TRACT_ZIP_BYTES,
            "startup_load": "none (lazy per state)",
            "runtime_network": "optional if state files are not pre-staged",
        },
        "C_preprocessed_national_slim_index": {
            "gazetteer_place_plus_tract_zip_bytes": MEASURED_GAZETTEER_PLACE_ZIP_BYTES
            + MEASURED_GAZETTEER_TRACT_ZIP_BYTES,
            "cartographic_500k_tract_zip_bytes": HEAD_CB2024_US_TRACT_500K_ZIP_BYTES,
            "startup_load": "slim tables only if shipped",
            "runtime_network": "none for index; polygons still needed for rook/PP",
        },
        "D_build_time_preprocessing": {
            "top50_resolved_packages_bytes_est": 50 * resolved,
            "all_places_resolved_packages_bytes_est": MEASURED_NATIONAL_PLACE_COUNT
            * resolved,
            "startup_load": "only pre-resolved packages that are copied into the image",
            "runtime_network": "none for pre-resolved places",
        },
        "E_runtime_census_plus_deterministic_cache": {
            "cold_payload_bytes_az": MEASURED_AZ_TRACT_ZIP_BYTES
            + MEASURED_AZ_PLACE_ZIP_BYTES,
            "warm_payload_bytes": resolved,
            "startup_load": "none",
            "runtime_network": "Census.gov on cache miss",
        },
    }
