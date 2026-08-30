"""In-process geography create-or-join store.

Reuses the analysis-job BackgroundTasks + fingerprint-join *pattern*.
Never starts thermal jobs. Never downloads TIGER (I-DATA owns acquisition).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from app.core.area_readiness import GeographyReadiness, ReferenceReadiness
from app.domain.census_place import (
    FIPS_TO_USPS,
    CensusPlaceIdentity,
    PlaceScope,
    normalize_place_name,
    parse_user_place_text,
    scope_for_state_fips,
    validate_place_geoid_format,
)
from app.domain.national_geography_package import (
    NATIONAL_CENSUS_VINTAGE,
    NATIONAL_RESOLVER_POLICY_ID,
    build_national_area_id,
    looks_like_national_area_id,
)
from app.schemas.public_geography import (
    EXPECTED_ZONE_COUNT,
    FROZEN_CENSUS_VINTAGE,
    FROZEN_RESOLVER_POLICY_ID,
    LEGACY_PHOENIX_AREA_ID,
    POLL_HORIZON_MS,
    POLL_INTERVAL_MS,
    PUBLIC_GEOGRAPHY_CONTRACT_VERSION,
    AnalysisWindowFlags,
    GeographyIdentityPublic,
    GeographyPollHint,
    GeographyProvenancePublic,
    GeographyReasonCode,
    GeographyResource,
    PlaceCandidate,
    PlaceIdentityResponse,
    PlaceSearchResponse,
    PublicGeographyError,
    PublicReason,
    ResolutionOutcome,
)
from app.services.census_place_lookup import CensusPlaceIndex
from app.services.national_resolver_cache import (
    FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    resolver_cache_fingerprint,
)

AREA_ID_RE = re.compile(
    r"^us-place-([0-9]{7})-([0-9]{4})-([a-z0-9]+(?:-[a-z0-9]+)*)$"
)
PLACE_GEOID_RE = re.compile(r"^[0-9]{7}$")
CACHE_CONTROL_TERMINAL = "public, max-age=86400"
CACHE_CONTROL_EPHEMERAL = "no-store"
CACHE_CONTROL_PLACES = "public, max-age=3600"
GAZETTEER_BASENAMES = (
    "2025_Gaz_place_national.txt",
    "2025_Gaz_place_national.zip",
)

MaterializeFn = Callable[[CensusPlaceIdentity], "MaterializeResult"]


class GeographySubstrateError(RuntimeError):
    """Gazetteer or TIGER substrate is missing. Not an unsupported geography."""


@dataclass(frozen=True)
class MaterializeResult:
    """Worker output. Unsupported is a product result, not a 500."""

    supported: bool
    reason_code: GeographyReasonCode
    message: str
    identity: GeographyIdentityPublic | None = None
    provenance: GeographyProvenancePublic | None = None
    geometry: Mapping[str, Any] | None = None


@dataclass
class GeographyStoreRecord:
    fingerprint: str
    area_id: str
    place: PlaceCandidate
    census_vintage: str
    resolver_policy_id: str
    resolution_outcome: ResolutionOutcome
    supported: bool | None
    reason: PublicReason | None
    identity: GeographyIdentityPublic | None = None
    provenance: GeographyProvenancePublic | None = None
    geometry: dict[str, Any] | None = None
    worker_started: bool = False


@dataclass(frozen=True)
class GeographyHttpResult:
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)


_lock = Lock()
_records: dict[str, GeographyStoreRecord] = {}
_place_index_override: CensusPlaceIndex | None = None
_materialize_fn: MaterializeFn | None = None
_tiger_override: bool | None = None


def reset_geography_store() -> None:
    """Test hook. Process-local store, same family as analysis job_store.reset."""
    global _place_index_override, _materialize_fn, _tiger_override
    with _lock:
        _records.clear()
    _place_index_override = None
    _materialize_fn = None
    _tiger_override = None


def set_place_index_for_tests(index: CensusPlaceIndex | None) -> None:
    global _place_index_override
    _place_index_override = index


def set_materialize_for_tests(fn: MaterializeFn | None) -> None:
    """Inject a zero-network materializer. Does not download TIGER."""
    global _materialize_fn
    _materialize_fn = fn


def set_tiger_available_for_tests(available: bool | None) -> None:
    global _tiger_override
    _tiger_override = available


def public_geography_enabled() -> bool:
    raw = os.environ.get("HVA_PUBLIC_GEOGRAPHY", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _repo_roots() -> list[Path]:
    here = Path(__file__).resolve()
    return [here.parents[4], here.parents[2]]


def discover_gazetteer_path() -> Path | None:
    """Local Gazetteer only. Never downloads. Never reads workforce/."""
    env_path = os.environ.get("HVA_GAZETTEER_PATH", "").strip()
    if env_path:
        path = Path(env_path)
        return path if path.is_file() else None
    for root in _repo_roots():
        census = root / "data" / "census" / "2025"
        for name in GAZETTEER_BASENAMES:
            candidate = census / name
            if candidate.is_file():
                return candidate
    return None


def _index_from_path(path: Path) -> CensusPlaceIndex:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".txt") and not name.endswith("/")
            ]
            if not names:
                raise GeographySubstrateError("gazetteer zip has no place table")
            text = archive.read(names[0]).decode("utf-8-sig")
        return CensusPlaceIndex.from_gazetteer_text(text)
    return CensusPlaceIndex.from_path(path)


def load_place_index() -> CensusPlaceIndex | None:
    if _place_index_override is not None:
        return _place_index_override
    path = discover_gazetteer_path()
    if path is None:
        return None
    return _index_from_path(path)


def local_tiger_present(state_fips: str) -> bool:
    """True only when I-DATA (or a test hook) staged local TIGER. No download."""
    if _tiger_override is not None:
        return _tiger_override
    if _materialize_fn is not None:
        return True
    year = FROZEN_CENSUS_VINTAGE
    names = (
        f"tl_{year}_{state_fips}_tract.zip",
        f"tl_{year}_{state_fips}_place.zip",
    )
    for root in _repo_roots():
        census = root / "data" / "census" / year
        if all((census / name).is_file() for name in names):
            return True
    return False


def fingerprint_for(place_geoid: str) -> str:
    return resolver_cache_fingerprint(
        canonical_place_geoid=place_geoid,
        census_vintage="TIGER2025",
        resolver_policy_version=FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    )


def area_id_for(place_geoid: str) -> str:
    return build_national_area_id(
        place_geoid=place_geoid,
        census_vintage=NATIONAL_CENSUS_VINTAGE,
        resolver_policy_id=NATIONAL_RESOLVER_POLICY_ID,
    )


def public_place_from_identity(identity: CensusPlaceIdentity) -> PlaceCandidate:
    return PlaceCandidate(
        place_geoid=identity.place_geoid,
        official_name=identity.official_name,
        place_name=identity.place_name,
        display_name=identity.display_name,
        state_fips=identity.state_fips,
        state_abbreviation=identity.state_abbreviation,
        place_type=identity.place_type.value,
        scope=identity.scope.value,
        resolution_eligible=identity.scope is PlaceScope.CONUS_PLUS_DC,
    )


def _synthetic_place(place_geoid: str) -> PlaceCandidate:
    state_fips = place_geoid[:2]
    abbr = FIPS_TO_USPS.get(state_fips, "XX")
    try:
        scope = scope_for_state_fips(state_fips)
    except ValueError:
        scope = PlaceScope.ISLAND_AREA
    official = f"place GEOID {place_geoid}"
    return PlaceCandidate(
        place_geoid=place_geoid,
        official_name=official,
        place_name=place_geoid,
        display_name=f"{official}, {abbr}",
        state_fips=state_fips,
        state_abbreviation=abbr,
        place_type="incorporated",
        scope=scope.value,
        resolution_eligible=scope is PlaceScope.CONUS_PLUS_DC,
    )


def resolve_place_candidate(place_geoid: str) -> PlaceCandidate | None:
    index = load_place_index()
    if index is None:
        return None
    identity = index.get(place_geoid)
    if identity is None:
        return None
    return public_place_from_identity(identity)


def display_label_for(place: PlaceCandidate) -> str:
    return (
        "HVA-Signal 25-zone analysis geography for "
        f"{place.official_name}, {place.state_abbreviation}"
    )


def analysis_window_caption_for(place: PlaceCandidate) -> str:
    return (
        "25-zone HVA-Signal analysis geography — analysis window within "
        f"{place.official_name}, {place.state_abbreviation}, generated under "
        f"resolver policy {FROZEN_RESOLVER_POLICY_ID}"
    )


def reason_message(code: GeographyReasonCode, place: PlaceCandidate) -> str:
    namelsad = place.official_name
    state = place.state_abbreviation
    policy = FROZEN_RESOLVER_POLICY_ID
    if code is GeographyReasonCode.GEOGRAPHY_RESOLVED:
        return (
            "Resolved a 25-zone HVA-Signal analysis geography — analysis window "
            f"within {namelsad}, {state}, generated under resolver policy {policy}."
        )
    if code is GeographyReasonCode.INSUFFICIENT_ELIGIBLE_TRACTS:
        return (
            f"{namelsad}, {state} has fewer than 25 eligible census tracts under "
            f"resolver policy {policy}. HVA-Signal will not invent zones. "
            "This does not mean the place is or is not a city."
        )
    if code is GeographyReasonCode.INSUFFICIENT_CONNECTED_TRACTS:
        return (
            f"The seed-component analysis window within {namelsad}, {state} has "
            f"fewer than 25 connected eligible tracts under resolver policy {policy}. "
            "HVA-Signal does not jump to another island or add land outside the "
            "Census Place."
        )
    if code is GeographyReasonCode.UNSUPPORTED_SCOPE:
        return (
            f"{namelsad} is outside the CONUS+DC analysis scope under "
            f"resolver policy {policy}."
        )
    if code is GeographyReasonCode.UNKNOWN_PLACE:
        return (
            f"Census Place GEOID {place.place_geoid} is not in the 2025 Gazetteer. "
            "This is not an unsupported-city claim."
        )
    if code is GeographyReasonCode.EMPTY_PLACE:
        return (
            f"{namelsad}, {state} has no official Census rings or INTPT under "
            f"resolver policy {policy}."
        )
    if code is GeographyReasonCode.MULTI_TIMEZONE_AOI:
        return (
            f"The 25-zone analysis window within {namelsad}, {state} spans more "
            "than one IANA timezone. HVA-Signal does not majority-vote a timezone. "
            f"This analysis window is not supported under resolver policy {policy}."
        )
    if code is GeographyReasonCode.TIMEZONE_NOT_FOUND:
        return (
            "Timezone lookup failed for one or more zones in this analysis window. "
            "HVA-Signal does not substitute a state default."
        )
    if code is GeographyReasonCode.AMBIGUOUS_PLACE:
        return (
            "More than one Census Place matches that name. HVA-Signal does not "
            "pick a largest city. Specify a state (Name, ST) or a 7-digit place GEOID."
        )
    if code is GeographyReasonCode.NOT_CONFIGURED:
        return (
            "2025 Census Gazetteer is not configured. Place identity is unavailable."
        )
    if code is GeographyReasonCode.SUBSTRATE_UNAVAILABLE:
        return (
            "Census geography substrate is unavailable for this analysis window. "
            "HVA-Signal will not invent zones. This is not an unsupported result."
        )
    if code is GeographyReasonCode.GEOGRAPHY_STORE_CORRUPT:
        return "Stored geography document failed an integrity check."
    if code is GeographyReasonCode.RESOLVER_INVARIANT_VIOLATION:
        return "Geography resolution hit an invariant violation."
    if code is GeographyReasonCode.GROWTH_FRONTIER_EXHAUSTED:
        return (
            f"The analysis window within {namelsad}, {state} exhausted the growth "
            f"frontier under resolver policy {policy}."
        )
    return f"{code.value} under resolver policy {policy}."


def geography_error(
    code: GeographyReasonCode,
    message: str | None = None,
    *,
    place: PlaceCandidate | None = None,
) -> PublicGeographyError:
    text = message
    if text is None and place is not None:
        text = reason_message(code, place)
    if text is None:
        text = code.value
    return PublicGeographyError(reason=PublicReason(code=code, message=text))


def error_http(
    status_code: int,
    code: GeographyReasonCode,
    message: str | None = None,
    *,
    place: PlaceCandidate | None = None,
) -> GeographyHttpResult:
    return GeographyHttpResult(
        status_code=status_code,
        body=geography_error(code, message, place=place).model_dump(mode="json"),
        headers={"Cache-Control": CACHE_CONTROL_EPHEMERAL},
    )


def _readiness(outcome: ResolutionOutcome) -> tuple[str, bool | None]:
    if outcome is ResolutionOutcome.NOT_STARTED:
        return GeographyReadiness.UNRESOLVED.value, None
    if outcome is ResolutionOutcome.PENDING:
        return GeographyReadiness.RESOLVING.value, None
    if outcome is ResolutionOutcome.SUPPORTED:
        return GeographyReadiness.GEOGRAPHY_READY.value, True
    if outcome is ResolutionOutcome.UNSUPPORTED:
        return GeographyReadiness.UNRESOLVED.value, False
    return GeographyReadiness.FAILED.value, None


def _snapshot_capable(
    outcome: ResolutionOutcome,
    identity: GeographyIdentityPublic | None,
) -> bool:
    if outcome is not ResolutionOutcome.SUPPORTED or identity is None:
        return False
    return (
        len(identity.zone_geoids) == EXPECTED_ZONE_COUNT
        and bool(identity.timezone)
        and bool(identity.geometry_sha256)
        and bool(identity.package_sha256)
        and bool(identity.aggregation_spec_version)
    )


def _etag_for(record: GeographyStoreRecord) -> str | None:
    if record.resolution_outcome is ResolutionOutcome.SUPPORTED and record.identity:
        return record.identity.package_sha256
    if record.resolution_outcome is ResolutionOutcome.UNSUPPORTED and record.reason:
        blob = json.dumps(
            {"area_id": record.area_id, "reason.code": record.reason.code.value},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return None


def build_resource(
    record: GeographyStoreRecord,
    *,
    include_poll: bool = False,
) -> GeographyResource:
    readiness, supported = _readiness(record.resolution_outcome)
    if record.supported is not None:
        supported = record.supported
    if readiness == GeographyReadiness.GEOGRAPHY_READY.value and supported is not True:
        raise RuntimeError("illegal GEOGRAPHY_READY with supported false")
    snapshot = _snapshot_capable(record.resolution_outcome, record.identity)
    poll = None
    if include_poll and record.resolution_outcome is ResolutionOutcome.PENDING:
        poll = GeographyPollHint(
            path=f"/api/v1/geographies/{record.area_id}",
            interval_ms=POLL_INTERVAL_MS,
            horizon_ms=POLL_HORIZON_MS,
        )
    return GeographyResource(
        area_id=record.area_id,
        place=record.place,
        census_vintage=FROZEN_CENSUS_VINTAGE,
        resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
        resolution_outcome=record.resolution_outcome,
        supported=supported,
        geography_readiness=readiness,  # type: ignore[arg-type]
        reference_readiness=ReferenceReadiness.NOT_PREPARED.value,  # type: ignore[arg-type]
        snapshot_capable=snapshot,
        historical_signal_capable=False,
        display_label=display_label_for(record.place),
        analysis_window_caption=analysis_window_caption_for(record.place),
        analysis_window=AnalysisWindowFlags(),
        identity=record.identity if record.resolution_outcome is ResolutionOutcome.SUPPORTED else None,
        provenance=(
            record.provenance
            if record.resolution_outcome is ResolutionOutcome.SUPPORTED
            else None
        ),
        reason=record.reason,
        poll=poll,
    )


def resource_http(
    record: GeographyStoreRecord,
    *,
    status_code: int,
    include_poll: bool = False,
) -> GeographyHttpResult:
    document = build_resource(record, include_poll=include_poll)
    headers = {"Cache-Control": CACHE_CONTROL_EPHEMERAL}
    if record.resolution_outcome in {
        ResolutionOutcome.SUPPORTED,
        ResolutionOutcome.UNSUPPORTED,
    }:
        headers["Cache-Control"] = CACHE_CONTROL_TERMINAL
        etag = _etag_for(record)
        if etag:
            headers["ETag"] = f'"{etag}"'
    return GeographyHttpResult(
        status_code=status_code,
        body=document.model_dump(mode="json"),
        headers=headers,
    )


def _not_started_record(area_id: str, place_geoid: str) -> GeographyStoreRecord:
    place = resolve_place_candidate(place_geoid) or _synthetic_place(place_geoid)
    return GeographyStoreRecord(
        fingerprint=fingerprint_for(place_geoid),
        area_id=area_id,
        place=place,
        census_vintage=FROZEN_CENSUS_VINTAGE,
        resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
        resolution_outcome=ResolutionOutcome.NOT_STARTED,
        supported=None,
        reason=None,
    )


def parse_national_area_id(area_id: str) -> tuple[str, str, str] | None:
    match = AREA_ID_RE.fullmatch(area_id)
    if match is None:
        return None
    return match.group(1), match.group(2), match.group(3)


def classify_area_id(area_id: str) -> GeographyReasonCode | None:
    """None means well-formed national id. Otherwise a request error code."""
    if area_id.strip().lower() == LEGACY_PHOENIX_AREA_ID or not looks_like_national_area_id(
        area_id
    ):
        if AREA_ID_RE.fullmatch(area_id):
            return None
        if area_id.strip().lower() == LEGACY_PHOENIX_AREA_ID or not area_id.startswith(
            "us-place-"
        ):
            return GeographyReasonCode.AREA_ID_NOT_NATIONAL
        return GeographyReasonCode.INVALID_AREA_ID
    return None


def search_places(query: str, *, limit: int = 10) -> GeographyHttpResult:
    """Gazetteer identity only. Never starts geography resolve."""
    index = load_place_index()
    if index is None:
        return error_http(
            503,
            GeographyReasonCode.NOT_CONFIGURED,
            "2025 Census Gazetteer is not configured. Place search is unavailable.",
        )
    text = query.strip()
    if not text:
        return error_http(
            422,
            GeographyReasonCode.INVALID_PLACE_GEOID,
            "Query q must be a Census Place name, Name, ST, or 7-digit GEOID.",
        )
    if limit < 1 or limit > 25:
        return error_http(
            422,
            GeographyReasonCode.FORBIDDEN_FIELD,
            "limit must be between 1 and 25.",
        )
    name, state, geoid = parse_user_place_text(text)
    found: list[CensusPlaceIdentity] = []
    if geoid is not None:
        failure = validate_place_geoid_format(geoid)
        if failure is not None:
            return error_http(
                422,
                GeographyReasonCode.INVALID_PLACE_GEOID,
                "place_geoid must be the 7-digit Census place identifier.",
            )
        identity = index.get(geoid)
        if identity is not None:
            found = [identity]
    elif name:
        key = normalize_place_name(name)
        for identity in index.by_geoid.values():
            if normalize_place_name(identity.official_name, identity.lsad) != key:
                continue
            if state and identity.state_abbreviation != state:
                continue
            found.append(identity)
    found.sort(key=lambda item: item.place_geoid)
    matches = [public_place_from_identity(item) for item in found[:limit]]
    reason = None
    if len(found) > 1:
        reason = PublicReason(
            code=GeographyReasonCode.AMBIGUOUS_PLACE,
            message=reason_message(
                GeographyReasonCode.AMBIGUOUS_PLACE,
                matches[0],
            ),
        )
    body = PlaceSearchResponse(query=text, matches=matches, reason=reason)
    return GeographyHttpResult(
        status_code=200,
        body=body.model_dump(mode="json"),
        headers={"Cache-Control": CACHE_CONTROL_PLACES},
    )


def get_place(place_geoid: str) -> GeographyHttpResult:
    raw = place_geoid.strip()
    if not PLACE_GEOID_RE.fullmatch(raw) or validate_place_geoid_format(raw) is not None:
        return error_http(
            422,
            GeographyReasonCode.INVALID_PLACE_GEOID,
            "place_geoid must be the 7-digit Census place identifier.",
        )
    index = load_place_index()
    if index is None:
        return error_http(
            503,
            GeographyReasonCode.NOT_CONFIGURED,
            "2025 Census Gazetteer is not configured. Place identity is unavailable.",
        )
    identity = index.get(raw)
    if identity is None:
        return error_http(
            404,
            GeographyReasonCode.UNKNOWN_PLACE,
            f"Census Place GEOID {raw} is not in the 2025 Gazetteer.",
        )
    place = public_place_from_identity(identity)
    predicted = area_id_for(raw)
    body = PlaceIdentityResponse(place=place, predicted_area_id=predicted)
    return GeographyHttpResult(
        status_code=200,
        body=body.model_dump(mode="json"),
        headers={"Cache-Control": CACHE_CONTROL_PLACES},
    )


def seed_terminal_record(
    place: PlaceCandidate,
    *,
    outcome: ResolutionOutcome,
    reason_code: GeographyReasonCode | None = None,
    identity: GeographyIdentityPublic | None = None,
    provenance: GeographyProvenancePublic | None = None,
    geometry: Mapping[str, Any] | None = None,
    message: str | None = None,
) -> GeographyStoreRecord:
    """Test / cache-injection helper. Does not start TIGER."""
    area_id = area_id_for(place.place_geoid)
    reason = None
    if reason_code is not None:
        reason = PublicReason(
            code=reason_code,
            message=message or reason_message(reason_code, place),
        )
    record = GeographyStoreRecord(
        fingerprint=fingerprint_for(place.place_geoid),
        area_id=area_id,
        place=place,
        census_vintage=FROZEN_CENSUS_VINTAGE,
        resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
        resolution_outcome=outcome,
        supported=True if outcome is ResolutionOutcome.SUPPORTED else (
            False if outcome is ResolutionOutcome.UNSUPPORTED else None
        ),
        reason=reason,
        identity=identity,
        provenance=provenance,
        geometry=dict(geometry) if geometry is not None else None,
        worker_started=False,
    )
    with _lock:
        _records[record.fingerprint] = record
    return record


def seed_pending_record(place: PlaceCandidate) -> GeographyStoreRecord:
    area_id = area_id_for(place.place_geoid)
    record = GeographyStoreRecord(
        fingerprint=fingerprint_for(place.place_geoid),
        area_id=area_id,
        place=place,
        census_vintage=FROZEN_CENSUS_VINTAGE,
        resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
        resolution_outcome=ResolutionOutcome.PENDING,
        supported=None,
        reason=None,
        worker_started=True,
    )
    with _lock:
        _records[record.fingerprint] = record
    return record


def get_record_by_area_id(area_id: str) -> GeographyStoreRecord | None:
    with _lock:
        for record in _records.values():
            if record.area_id == area_id:
                return record
    return None


def store_size() -> int:
    with _lock:
        return len(_records)


def run_geography_worker(fingerprint: str) -> None:
    """BackgroundTasks target. Must never call process_analysis_job."""
    with _lock:
        record = _records.get(fingerprint)
        if record is None:
            return
        if record.resolution_outcome in {
            ResolutionOutcome.SUPPORTED,
            ResolutionOutcome.UNSUPPORTED,
            ResolutionOutcome.FAILED,
        }:
            return
        place_geoid = record.place.place_geoid
    index = load_place_index()
    identity = index.get(place_geoid) if index is not None else None
    if identity is None:
        with _lock:
            current = _records.get(fingerprint)
            if current is not None and current.resolution_outcome is ResolutionOutcome.PENDING:
                del _records[fingerprint]
        return
    try:
        if _materialize_fn is None:
            with _lock:
                current = _records.get(fingerprint)
                if current is not None and current.resolution_outcome is ResolutionOutcome.PENDING:
                    del _records[fingerprint]
            return
        result = _materialize_fn(identity)
        _apply_materialize(fingerprint, public_place_from_identity(identity), result)
    except Exception:
        place = public_place_from_identity(identity)
        with _lock:
            current = _records.get(fingerprint)
            if current is None:
                return
            current.resolution_outcome = ResolutionOutcome.FAILED
            current.supported = None
            current.reason = PublicReason(
                code=GeographyReasonCode.RESOLVER_INVARIANT_VIOLATION,
                message=reason_message(
                    GeographyReasonCode.RESOLVER_INVARIANT_VIOLATION, place
                ),
            )


def _apply_materialize(
    fingerprint: str,
    place: PlaceCandidate,
    result: MaterializeResult,
) -> None:
    with _lock:
        current = _records.get(fingerprint)
        if current is None:
            return
        if result.supported:
            if current.resolution_outcome is ResolutionOutcome.SUPPORTED and current.identity:
                incoming = result.identity.package_sha256 if result.identity else None
                if incoming and incoming != current.identity.package_sha256:
                    current.resolution_outcome = ResolutionOutcome.FAILED
                    current.supported = None
                    current.reason = PublicReason(
                        code=GeographyReasonCode.GEOGRAPHY_STORE_CORRUPT,
                        message=reason_message(
                            GeographyReasonCode.GEOGRAPHY_STORE_CORRUPT, place
                        ),
                    )
                return
            current.resolution_outcome = ResolutionOutcome.SUPPORTED
            current.supported = True
            current.identity = result.identity
            current.provenance = result.provenance
            current.geometry = dict(result.geometry) if result.geometry else None
            current.reason = PublicReason(
                code=GeographyReasonCode.GEOGRAPHY_RESOLVED,
                message=result.message or reason_message(
                    GeographyReasonCode.GEOGRAPHY_RESOLVED, place
                ),
            )
            return
        current.resolution_outcome = ResolutionOutcome.UNSUPPORTED
        current.supported = False
        current.identity = None
        current.provenance = None
        current.geometry = None
        current.reason = PublicReason(code=result.reason_code, message=result.message)


def create_or_join(
    place_geoid: str,
    *,
    enqueue: Callable[[str], None] | None = None,
) -> GeographyHttpResult:
    """Idempotent create-or-join. Search/GET never call this."""
    failure = validate_place_geoid_format(place_geoid)
    if failure is not None or not PLACE_GEOID_RE.fullmatch(place_geoid):
        return error_http(
            422,
            GeographyReasonCode.INVALID_PLACE_GEOID,
            "place_geoid must be the 7-digit Census place identifier.",
        )
    index = load_place_index()
    if index is None:
        return error_http(
            503,
            GeographyReasonCode.NOT_CONFIGURED,
            "2025 Census Gazetteer is not configured. Geography resolve is unavailable.",
        )
    identity = index.get(place_geoid)
    if identity is None:
        place = _synthetic_place(place_geoid)
        record = GeographyStoreRecord(
            fingerprint=fingerprint_for(place_geoid),
            area_id=area_id_for(place_geoid),
            place=place,
            census_vintage=FROZEN_CENSUS_VINTAGE,
            resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
            resolution_outcome=ResolutionOutcome.UNSUPPORTED,
            supported=False,
            reason=PublicReason(
                code=GeographyReasonCode.UNKNOWN_PLACE,
                message=reason_message(GeographyReasonCode.UNKNOWN_PLACE, place),
            ),
        )
        with _lock:
            _records[record.fingerprint] = record
        return resource_http(record, status_code=200)

    place = public_place_from_identity(identity)
    area_id = area_id_for(place_geoid)
    key = fingerprint_for(place_geoid)

    if identity.scope is not PlaceScope.CONUS_PLUS_DC:
        record = GeographyStoreRecord(
            fingerprint=key,
            area_id=area_id,
            place=place,
            census_vintage=FROZEN_CENSUS_VINTAGE,
            resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
            resolution_outcome=ResolutionOutcome.UNSUPPORTED,
            supported=False,
            reason=PublicReason(
                code=GeographyReasonCode.UNSUPPORTED_SCOPE,
                message=reason_message(GeographyReasonCode.UNSUPPORTED_SCOPE, place),
            ),
        )
        with _lock:
            _records[key] = record
        return resource_http(record, status_code=200)

    with _lock:
        existing = _records.get(key)
        if existing is not None:
            if existing.resolution_outcome in {
                ResolutionOutcome.SUPPORTED,
                ResolutionOutcome.UNSUPPORTED,
                ResolutionOutcome.FAILED,
            }:
                return resource_http(existing, status_code=200)
            if existing.resolution_outcome is ResolutionOutcome.PENDING:
                return resource_http(existing, status_code=202, include_poll=True)
        if not local_tiger_present(identity.state_fips):
            return error_http(
                503,
                GeographyReasonCode.SUBSTRATE_UNAVAILABLE,
                place=place,
            )
        pending = GeographyStoreRecord(
            fingerprint=key,
            area_id=area_id,
            place=place,
            census_vintage=FROZEN_CENSUS_VINTAGE,
            resolver_policy_id=FROZEN_RESOLVER_POLICY_ID,
            resolution_outcome=ResolutionOutcome.PENDING,
            supported=None,
            reason=None,
            worker_started=True,
        )
        _records[key] = pending
        should_enqueue = True
        snapshot = pending

    if should_enqueue and enqueue is not None:
        enqueue(key)
    return resource_http(snapshot, status_code=202, include_poll=True)


def get_geography(area_id: str, *, if_none_match: str | None = None) -> GeographyHttpResult:
    """Side-effect free poll. GET never starts resolve."""
    code = classify_area_id(area_id)
    if code is GeographyReasonCode.AREA_ID_NOT_NATIONAL:
        return error_http(
            404,
            code,
            "area_id is not a national us-place identity. phoenix-demo is a different catalog.",
        )
    if code is GeographyReasonCode.INVALID_AREA_ID:
        return error_http(
            422,
            code,
            "area_id must match us-place-{geoid}-{vintage}-{policy_slug}.",
        )
    parsed = parse_national_area_id(area_id)
    if parsed is None:
        return error_http(
            422,
            GeographyReasonCode.INVALID_AREA_ID,
            "area_id must match us-place-{geoid}-{vintage}-{policy_slug}.",
        )
    record = get_record_by_area_id(area_id)
    if record is None:
        record = _not_started_record(area_id, parsed[0])
        return resource_http(record, status_code=200)
    result = resource_http(record, status_code=200)
    if if_none_match and "ETag" in result.headers:
        incoming = if_none_match.strip()
        if incoming == result.headers["ETag"] or incoming.strip('"') == result.headers[
            "ETag"
        ].strip('"'):
            return GeographyHttpResult(
                status_code=304,
                body={},
                headers=result.headers,
            )
    return result


def get_geography_geometry(area_id: str) -> GeographyHttpResult:
    code = classify_area_id(area_id)
    if code is GeographyReasonCode.AREA_ID_NOT_NATIONAL:
        return error_http(
            404,
            code,
            "area_id is not a national us-place identity. phoenix-demo is a different catalog.",
        )
    if code is not None or parse_national_area_id(area_id) is None:
        return error_http(
            422,
            GeographyReasonCode.INVALID_AREA_ID,
            "area_id must match us-place-{geoid}-{vintage}-{policy_slug}.",
        )
    record = get_record_by_area_id(area_id)
    if (
        record is None
        or record.resolution_outcome is not ResolutionOutcome.SUPPORTED
        or record.identity is None
    ):
        return error_http(
            409,
            GeographyReasonCode.GEOGRAPHY_NOT_READY,
            "Geometry is available only when geography_readiness is GEOGRAPHY_READY.",
        )
    geometry = record.geometry or {
        "type": "FeatureCollection",
        "features": [],
    }
    headers = {
        "Cache-Control": CACHE_CONTROL_TERMINAL,
        "ETag": f'"{record.identity.geometry_sha256}"',
        "X-HVA-Area-ID": record.area_id,
        "X-HVA-Zone-Geometry-Version": record.identity.zone_geometry_version,
        "X-HVA-Geometry-SHA256": record.identity.geometry_sha256,
        "Content-Type": "application/geo+json",
    }
    return GeographyHttpResult(status_code=200, body=dict(geometry), headers=headers)


assert PUBLIC_GEOGRAPHY_CONTRACT_VERSION
