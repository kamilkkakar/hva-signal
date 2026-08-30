"""AOI timezone resolution and DST-safe local-hour validation.

National geography candidate. Not published. Does not import FortyGuard,
Phoenix frozen AreaConfig, or public request routes.

Lat/lon → IANA lookup is injected. This module does not depend on
timezonefinder or any online geocoder.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

POLICY_VERSION = "HVA_AOI_TIMEZONE_POLICY_V1_CANDIDATE"
RESOLUTION_RULE = "unanimous_selected_tract_representative_points"
DST_RULE = "reject_ambiguous_and_nonexistent"
EXPECTED_ZONE_COUNT = 25
PHOENIX_IANA = "America/Phoenix"

TimezoneLookup = Callable[[float, float], str | None]


class TimezoneFailureCode(StrEnum):
    TIMEZONE_NOT_FOUND = "TIMEZONE_NOT_FOUND"
    MULTI_TIMEZONE_AOI = "MULTI_TIMEZONE_AOI"
    AMBIGUOUS_LOCAL_TIME = "AMBIGUOUS_LOCAL_TIME"
    NONEXISTENT_LOCAL_TIME = "NONEXISTENT_LOCAL_TIME"


# Program-brief aliases. Canonical names are the enum values.
UNSUPPORTED_MULTI_TIMEZONE_AOI = TimezoneFailureCode.MULTI_TIMEZONE_AOI
TIMEZONE_UNRESOLVED = TimezoneFailureCode.TIMEZONE_NOT_FOUND


class LocalTimeStatus(StrEnum):
    UNIQUE = "UNIQUE"
    AMBIGUOUS = "AMBIGUOUS"
    NONEXISTENT = "NONEXISTENT"


class TimezoneMethod(StrEnum):
    PLACE_CENTROID = "place_centroid"
    SEED = "seed"
    TRACT_CENTROIDS = "all_tract_centroids"
    TRACT_REPRESENTATIVE_POINTS = "all_tract_representative_points"


@dataclass(frozen=True, slots=True)
class LonLat:
    """WGS84 lon/lat. Lon first (GeoJSON order)."""

    lon: float
    lat: float

    def __post_init__(self) -> None:
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError("longitude must be within [-180, 180]")
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError("latitude must be within [-90, 90]")


@dataclass(frozen=True, slots=True)
class TimezoneResolution:
    timezone: str
    policy_version: str
    rule: str
    point_timezones: tuple[str, ...]
    zone_ids: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class MethodOutcome:
    method: TimezoneMethod
    timezone: str | None
    code: TimezoneFailureCode | None
    point_timezones: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class TimezoneMethodComparison:
    place_centroid: MethodOutcome | None
    seed: MethodOutcome | None
    tract_centroids: MethodOutcome
    tract_representative_points: MethodOutcome
    methods_agree: bool

    @property
    def production(self) -> MethodOutcome:
        return self.tract_representative_points


class AoiTimezoneError(ValueError):
    def __init__(self, code: TimezoneFailureCode, message: str) -> None:
        self.code = code
        super().__init__(message)


class AoiTimezoneResolutionError(AoiTimezoneError):
    def __init__(
        self,
        code: TimezoneFailureCode,
        message: str,
        *,
        point_timezones: tuple[str | None, ...],
        distinct: tuple[str, ...],
    ) -> None:
        self.point_timezones = point_timezones
        self.distinct = distinct
        super().__init__(code, message)


class AoiLocalTimeError(AoiTimezoneError):
    def __init__(
        self,
        code: TimezoneFailureCode,
        message: str,
        *,
        timestamp: datetime,
        timezone_name: str,
    ) -> None:
        self.timestamp = timestamp
        self.timezone_name = timezone_name
        super().__init__(code, message)


def require_iana_timezone(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise AoiTimezoneResolutionError(
            TimezoneFailureCode.TIMEZONE_NOT_FOUND,
            "IANA timezone is empty",
            point_timezones=(),
            distinct=(),
        )
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise AoiTimezoneResolutionError(
            TimezoneFailureCode.TIMEZONE_NOT_FOUND,
            f"IANA timezone {cleaned!r} is not known to zoneinfo",
            point_timezones=(cleaned,),
            distinct=(cleaned,),
        ) from exc
    return cleaned


def _lookup_one(lookup: TimezoneLookup, point: LonLat) -> str | None:
    raw = lookup(point.lon, point.lat)
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


def _resolve_points(
    points: Sequence[LonLat],
    lookup: TimezoneLookup,
    *,
    method: TimezoneMethod,
) -> MethodOutcome:
    names: list[str | None] = []
    for point in points:
        found = _lookup_one(lookup, point)
        if found is not None:
            try:
                found = require_iana_timezone(found)
            except AoiTimezoneResolutionError:
                found = None
        names.append(found)
    resolved = tuple(names)
    if any(name is None for name in resolved):
        return MethodOutcome(
            method=method,
            timezone=None,
            code=TimezoneFailureCode.TIMEZONE_NOT_FOUND,
            point_timezones=resolved,
        )
    distinct = tuple(sorted(set(resolved)))
    if len(distinct) != 1:
        return MethodOutcome(
            method=method,
            timezone=None,
            code=TimezoneFailureCode.MULTI_TIMEZONE_AOI,
            point_timezones=resolved,
        )
    return MethodOutcome(
        method=method,
        timezone=distinct[0],
        code=None,
        point_timezones=resolved,
    )


def _raise_from_outcome(outcome: MethodOutcome) -> None:
    if outcome.code is TimezoneFailureCode.TIMEZONE_NOT_FOUND:
        raise AoiTimezoneResolutionError(
            TimezoneFailureCode.TIMEZONE_NOT_FOUND,
            "one or more AOI points have no known IANA timezone",
            point_timezones=outcome.point_timezones,
            distinct=tuple(
                sorted({name for name in outcome.point_timezones if name is not None})
            ),
        )
    if outcome.code is TimezoneFailureCode.MULTI_TIMEZONE_AOI:
        distinct = tuple(
            sorted({name for name in outcome.point_timezones if name is not None})
        )
        raise AoiTimezoneResolutionError(
            TimezoneFailureCode.MULTI_TIMEZONE_AOI,
            "selected tract representative points span multiple IANA timezones: "
            + ", ".join(distinct),
            point_timezones=outcome.point_timezones,
            distinct=distinct,
        )


def resolve_aoi_timezone(
    representative_points: Sequence[LonLat],
    lookup: TimezoneLookup,
    *,
    expected_zone_count: int = EXPECTED_ZONE_COUNT,
    zone_ids: Sequence[str] | None = None,
) -> TimezoneResolution:
    """Require unanimous IANA timezone across selected tract representative points."""
    if expected_zone_count <= 0:
        raise ValueError("expected_zone_count must be positive")
    if len(representative_points) != expected_zone_count:
        raise ValueError(
            f"expected {expected_zone_count} representative points, "
            f"got {len(representative_points)}"
        )
    if zone_ids is not None and len(zone_ids) != expected_zone_count:
        raise ValueError("zone_ids length must equal expected_zone_count")
    outcome = _resolve_points(
        representative_points,
        lookup,
        method=TimezoneMethod.TRACT_REPRESENTATIVE_POINTS,
    )
    if outcome.code is not None:
        _raise_from_outcome(outcome)
    assert outcome.timezone is not None
    return TimezoneResolution(
        timezone=outcome.timezone,
        policy_version=POLICY_VERSION,
        rule=RESOLUTION_RULE,
        point_timezones=tuple(name or "" for name in outcome.point_timezones),
        zone_ids=tuple(zone_ids) if zone_ids is not None else None,
    )


def compare_timezone_methods(
    *,
    lookup: TimezoneLookup,
    tract_representative_points: Sequence[LonLat],
    tract_centroids: Sequence[LonLat],
    place_centroid: LonLat | None = None,
    seed: LonLat | None = None,
    expected_zone_count: int = EXPECTED_ZONE_COUNT,
) -> TimezoneMethodComparison:
    """Diagnostic bake-off. Production decision uses representative points only."""
    if len(tract_representative_points) != expected_zone_count:
        raise ValueError("tract_representative_points count mismatch")
    if len(tract_centroids) != expected_zone_count:
        raise ValueError("tract_centroids count mismatch")

    place_outcome = (
        _resolve_points(
            (place_centroid,), lookup, method=TimezoneMethod.PLACE_CENTROID
        )
        if place_centroid is not None
        else None
    )
    seed_outcome = (
        _resolve_points((seed,), lookup, method=TimezoneMethod.SEED)
        if seed is not None
        else None
    )
    centroid_outcome = _resolve_points(
        tract_centroids, lookup, method=TimezoneMethod.TRACT_CENTROIDS
    )
    representative_outcome = _resolve_points(
        tract_representative_points,
        lookup,
        method=TimezoneMethod.TRACT_REPRESENTATIVE_POINTS,
    )
    observed = [
        outcome.timezone
        for outcome in (
            place_outcome,
            seed_outcome,
            centroid_outcome,
            representative_outcome,
        )
        if outcome is not None
    ]
    methods_agree = len(set(observed)) == 1 and observed[0] is not None
    return TimezoneMethodComparison(
        place_centroid=place_outcome,
        seed=seed_outcome,
        tract_centroids=centroid_outcome,
        tract_representative_points=representative_outcome,
        methods_agree=methods_agree,
    )


def classify_aoi_local_datetime(
    timestamp: datetime, iana_timezone: str
) -> LocalTimeStatus:
    """Classify a naive wall time. Nonexistent is detected before ambiguous."""
    if timestamp.tzinfo is not None:
        raise ValueError("timestamp must be AOI-local naive, not timezone-aware")
    tz = ZoneInfo(require_iana_timezone(iana_timezone))
    first = timestamp.replace(tzinfo=tz, fold=0)
    roundtrip = first.astimezone(timezone.utc).astimezone(tz)
    if (
        roundtrip.year != timestamp.year
        or roundtrip.month != timestamp.month
        or roundtrip.day != timestamp.day
        or roundtrip.hour != timestamp.hour
        or roundtrip.minute != timestamp.minute
        or roundtrip.second != timestamp.second
        or roundtrip.microsecond != timestamp.microsecond
    ):
        return LocalTimeStatus.NONEXISTENT
    second = timestamp.replace(tzinfo=tz, fold=1)
    if first.utcoffset() != second.utcoffset():
        return LocalTimeStatus.AMBIGUOUS
    return LocalTimeStatus.UNIQUE


def require_unique_aoi_local_hour(
    timestamp: datetime, iana_timezone: str
) -> datetime:
    """Future Signal B guard. Rejects aware values, minutes, and DST gaps/folds."""
    if timestamp.tzinfo is not None:
        raise ValueError(
            "selected-time timestamp must be AOI-local naive, not timezone-aware"
        )
    if timestamp.minute != 0 or timestamp.second != 0 or timestamp.microsecond != 0:
        raise ValueError("arbitrary minutes are unsupported; do not silently round")
    status = classify_aoi_local_datetime(timestamp, iana_timezone)
    if status is LocalTimeStatus.NONEXISTENT:
        raise AoiLocalTimeError(
            TimezoneFailureCode.NONEXISTENT_LOCAL_TIME,
            f"{timestamp.isoformat(timespec='seconds')} does not exist in {iana_timezone}",
            timestamp=timestamp,
            timezone_name=iana_timezone,
        )
    if status is LocalTimeStatus.AMBIGUOUS:
        raise AoiLocalTimeError(
            TimezoneFailureCode.AMBIGUOUS_LOCAL_TIME,
            f"{timestamp.isoformat(timespec='seconds')} is ambiguous in {iana_timezone}",
            timestamp=timestamp,
            timezone_name=iana_timezone,
        )
    return timestamp


def assert_client_timezone_matches(
    client_timezone: str | None, resolved_timezone: str
) -> str:
    """Future request echo. Geography IANA is authoritative. Not a public code."""
    resolved = require_iana_timezone(resolved_timezone)
    if client_timezone is None:
        return resolved
    client = require_iana_timezone(client_timezone)
    if client != resolved:
        raise ValueError(
            f"client timezone {client!r} does not match geography timezone {resolved!r}"
        )
    return resolved


def try_timezonefinder_lookup() -> TimezoneLookup | None:
    """Optional offline hook. Returns None when timezonefinder is not installed."""
    try:
        from timezonefinder import TimezoneFinder
    except ImportError:
        return None
    finder = TimezoneFinder()

    def lookup(lon: float, lat: float) -> str | None:
        return finder.timezone_at(lng=lon, lat=lat)

    return lookup
