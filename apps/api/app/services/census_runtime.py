"""Census place-search runtime: pinned Gazetteer load + resolve-time GEOID checks.

Lazy. No import-time I/O. No Census HTTP. No FortyGuard. No workforce/ reads.

The official 2025 place zip is optional in git. When the zip is present it must
match data/census/2025/SOURCE.json (length + sha256). When it is absent, load
fails closed (GEOGRAPHY_INDEX_INVALID).
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.core.geography_paths import (
    assert_runtime_path_allowed,
    gazetteer_source_path,
    gazetteer_zip_path,
)
from app.domain.census_place import (
    PLACE_IDENTITY_VINTAGE,
    PlaceLookupQuery,
    PlaceLookupResult,
)
from app.services.census_place_lookup import CensusPlaceIndex, parse_gazetteer_places
from app.services.national_resolver_cache import (
    DEFAULT_CENSUS_VINTAGE,
    FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    normalize_place_geoid,
    resolver_cache_document,
    resolver_cache_fingerprint,
)

GEOGRAPHY_INDEX_INVALID: Final = "GEOGRAPHY_INDEX_INVALID"
INVALID_TRACT_GEOID: Final = "INVALID_TRACT_GEOID"
GAZETTEER_LOAD_TIMEOUT_S: Final = 5.0
TRACT_GEOID_RE: Final = re.compile(r"^[0-9]{11}$")
_SHA256_RE: Final = re.compile(r"^[0-9a-f]{64}$")

_INDEX: CensusPlaceIndex | None = None


class CensusRuntimeError(ValueError):
    """Fail-closed geography runtime error with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class GazetteerUnavailable(CensusRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(GEOGRAPHY_INDEX_INVALID, message)


class TractGeoidError(CensusRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(INVALID_TRACT_GEOID, message)


@dataclass(frozen=True)
class GazetteerSourcePin:
    artifact: str
    identity_vintage: str
    url: str
    content_length: int
    sha256: str | None
    row_count_national: int | None
    scope_default: str | None


def reset_place_index_cache() -> None:
    """Test hook. Production callers should not need this."""
    global _INDEX
    _INDEX = None


def load_gazetteer_source_pin(path: Path) -> GazetteerSourcePin:
    assert_runtime_path_allowed(path, label="gazetteer SOURCE.json")
    if not path.is_file():
        raise GazetteerUnavailable(f"gazetteer SOURCE.json is missing at {path.as_posix()}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GazetteerUnavailable("gazetteer SOURCE.json is not valid JSON") from exc
    if not isinstance(document, dict):
        raise GazetteerUnavailable("gazetteer SOURCE.json must be a JSON object")
    artifact = document.get("artifact")
    vintage = document.get("identity_vintage")
    url = document.get("url")
    length = document.get("content_length")
    if not isinstance(artifact, str) or artifact != "2025_Gaz_place_national.zip":
        raise GazetteerUnavailable("SOURCE.json artifact must be 2025_Gaz_place_national.zip")
    if vintage != PLACE_IDENTITY_VINTAGE:
        raise GazetteerUnavailable(
            f"SOURCE.json identity_vintage must be {PLACE_IDENTITY_VINTAGE}"
        )
    if not isinstance(url, str) or "2025_Gaz_place_national.zip" not in url:
        raise GazetteerUnavailable("SOURCE.json url must pin the official 2025 place zip")
    if not isinstance(length, int) or length <= 0:
        raise GazetteerUnavailable("SOURCE.json content_length must be a positive integer")
    row_count = document.get("row_count_national")
    if row_count is not None and (not isinstance(row_count, int) or row_count <= 0):
        raise GazetteerUnavailable("SOURCE.json row_count_national is invalid")
    scope = document.get("scope_default")
    if scope is not None and not isinstance(scope, str):
        raise GazetteerUnavailable("SOURCE.json scope_default is invalid")
    return GazetteerSourcePin(
        artifact=artifact,
        identity_vintage=vintage,
        url=url,
        content_length=length,
        sha256=_pinned_sha256(document.get("sha256")),
        row_count_national=row_count,
        scope_default=scope,
    )


def _pinned_sha256(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text or text in {"pending", "null", "unpinned", "none"}:
        return None
    if "compute" in text:
        return None
    if not _SHA256_RE.fullmatch(text):
        raise GazetteerUnavailable("SOURCE.json sha256 is not a SHA-256 hex digest")
    return text


def _safe_zip_members(zf: zipfile.ZipFile) -> list[str]:
    names: list[str] = []
    for name in zf.namelist():
        posix = name.replace("\\", "/")
        if posix.startswith("/") or ".." in Path(posix).parts:
            raise GazetteerUnavailable("gazetteer zip contains an unsafe member path")
        if not posix.endswith("/") and posix.lower().endswith(".txt"):
            names.append(name)
    return names


def read_gazetteer_text(
    zip_path: Path,
    pin: GazetteerSourcePin,
    *,
    timeout_s: float = GAZETTEER_LOAD_TIMEOUT_S,
) -> str:
    """Read and pin-check the official zip. Fail closed if missing or mismatched."""
    started = time.monotonic()
    assert_runtime_path_allowed(zip_path, label="gazetteer zip")
    if not zip_path.is_file():
        raise GazetteerUnavailable(
            "gazetteer zip is not present; place search is unavailable"
        )
    data = zip_path.read_bytes()
    if time.monotonic() - started > timeout_s:
        raise GazetteerUnavailable("gazetteer load exceeded the local timeout")
    if len(data) != pin.content_length:
        raise GazetteerUnavailable(
            f"gazetteer zip length {len(data)} does not match SOURCE.json "
            f"content_length {pin.content_length}"
        )
    if pin.sha256 is None:
        raise GazetteerUnavailable(
            "gazetteer zip is present but SOURCE.json sha256 is not pinned; "
            "refusing to load an unpinned archive"
        )
    digest = hashlib.sha256(data).hexdigest()
    if digest != pin.sha256:
        raise GazetteerUnavailable("gazetteer zip sha256 does not match SOURCE.json")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if zf.testzip() is not None:
                raise GazetteerUnavailable("gazetteer zip is corrupt")
            members = _safe_zip_members(zf)
            if not members:
                raise GazetteerUnavailable("gazetteer zip has no .txt member")
            text = zf.read(members[0]).decode("utf-8-sig")
    except zipfile.BadZipFile as exc:
        raise GazetteerUnavailable("gazetteer file is not a valid zip") from exc
    if time.monotonic() - started > timeout_s:
        raise GazetteerUnavailable("gazetteer load exceeded the local timeout")
    return text


def load_gazetteer_index(*, repo_root: Path | None = None) -> CensusPlaceIndex:
    """Build CensusPlaceIndex from the pinned shipped zip, or fail closed."""
    pin = load_gazetteer_source_pin(gazetteer_source_path(repo_root=repo_root))
    text = read_gazetteer_text(gazetteer_zip_path(repo_root=repo_root), pin)
    places = parse_gazetteer_places(text, source_vintage=pin.identity_vintage)
    if pin.row_count_national is not None and len(places) != pin.row_count_national:
        raise GazetteerUnavailable(
            f"gazetteer row count {len(places)} does not match "
            f"SOURCE.json row_count_national {pin.row_count_national}"
        )
    return CensusPlaceIndex(places)


def get_place_index(*, repo_root: Path | None = None) -> CensusPlaceIndex:
    """Lazy process cache. Not invoked at import. Not used by /health."""
    global _INDEX
    if _INDEX is None:
        _INDEX = load_gazetteer_index(repo_root=repo_root)
    return _INDEX


def search_census_place(
    raw_text: str,
    *,
    index: CensusPlaceIndex | None = None,
    repo_root: Path | None = None,
) -> PlaceLookupResult:
    """Name/GEOID search over the 2025 Gazetteer index."""
    resolved = index if index is not None else get_place_index(repo_root=repo_root)
    return resolved.resolve(PlaceLookupQuery(raw_text=raw_text))


def geography_cache_identity(
    *,
    place_geoid: str,
    census_vintage: str = DEFAULT_CENSUS_VINTAGE,
    resolver_policy_version: str = FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
) -> dict[str, str]:
    """Cache key document: place GEOID + TIGER vintage + policy. No historical SHA."""
    return resolver_cache_document(
        canonical_place_geoid=place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )


def geography_cache_key(
    *,
    place_geoid: str,
    census_vintage: str = DEFAULT_CENSUS_VINTAGE,
    resolver_policy_version: str = FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
) -> str:
    """SHA-256 of the geography-only identity. Historical reference is not an input."""
    return resolver_cache_fingerprint(
        canonical_place_geoid=place_geoid,
        census_vintage=census_vintage,
        resolver_policy_version=resolver_policy_version,
    )


def extract_tract_geoid(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("geoid", "GEOID", "tract_geoid"):
            raw = value.get(key)
            if raw is not None:
                text = str(raw).strip()
                if text:
                    return text
        return None
    for name in ("geoid", "GEOID", "tract_geoid"):
        if hasattr(value, name):
            raw = getattr(value, name)
            if raw is not None:
                text = str(raw).strip()
                if text:
                    return text
    return None


def validate_tract_geoid(geoid: str, *, place_geoid: str | None = None) -> str:
    """R5 F2 helper: require an 11-digit tract GEOID and optional STATEFP vs place."""
    text = geoid.strip()
    if not TRACT_GEOID_RE.fullmatch(text):
        raise TractGeoidError(
            "tract GEOID must be an 11-digit Census tract identifier"
        )
    if place_geoid is not None:
        place = normalize_place_geoid(place_geoid)
        if text[:2] != place[:2]:
            raise TractGeoidError(
                f"tract GEOID {text} STATEFP {text[:2]} does not match "
                f"place GEOID {place}"
            )
    return text


def validate_tract_geoids_for_resolve(
    census_tracts: Sequence[object],
    *,
    place_geoid: str,
) -> list[str]:
    """Fail-closed 11-digit + STATEFP check before public ingest / ALG1 resolve.

    I-API-GEO / R3 own place_geography_resolver.py. Call this helper (or a thin
    wrapper that owns the call site) instead of editing the resolver.
    """
    place = normalize_place_geoid(place_geoid)
    cleaned: list[str] = []
    for item in census_tracts:
        geoid = extract_tract_geoid(item)
        if geoid is None:
            raise TractGeoidError("census tract is missing GEOID")
        cleaned.append(validate_tract_geoid(geoid, place_geoid=place))
    return cleaned


def require_resolve_tract_geoids(
    census_tracts: Sequence[object],
    *,
    place_geoid: str,
) -> list[str]:
    """Thin I-DATA wrapper around the R5 F2 tract GEOID contract."""
    return validate_tract_geoids_for_resolve(census_tracts, place_geoid=place_geoid)


def validate_resolved_zone_geoids(
    zone_geoids: Sequence[object],
    *,
    place_geoid: str,
) -> list[str]:
    """Same 11-digit + STATEFP rule for a post-resolve 25-zone list."""
    return require_resolve_tract_geoids(zone_geoids, place_geoid=place_geoid)
