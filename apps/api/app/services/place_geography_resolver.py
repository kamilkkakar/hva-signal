"""I3 entry: resolve_place_geography — pure deterministic ALG1 resolver.

Census-geometry only. No vendor client, no historical reference, no demo
ledger. Phoenix-demo 25 is not a target. Outside-place expansion is refused.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform
from shapely.ops import unary_union
from shapely.validation import make_valid

from app.services.aoi_timezone import (
    POLICY_VERSION as TIMEZONE_POLICY_VERSION,
    AoiTimezoneResolutionError,
    TimezoneFailureCode,
    TimezoneLookup,
)
from app.services.geography_timezone_gate import (
    GeographyTimezoneError,
    representative_points_from_geometries,
    resolve_selected_geography_timezone,
)
from app.services.national_tract_selection import (
    ALGORITHM_ID,
    ANALYSIS_CRS,
    CENSUS_VINTAGE,
    ELIGIBILITY_RULE_ID,
    SEED_RULE_ID,
    GROWTH_RULE_ID,
    REASON_EMPTY_PLACE,
    REASON_INSUFFICIENT_CONNECTED_TRACTS,
    REASON_INSUFFICIENT_ELIGIBLE_TRACTS,
    REASON_INSUFFICIENT_RELEVANT_COMPONENT,
    RESOLVER_POLICY_ID,
    ROOK_BOUNDARY_FLOOR_M,
    ROOK_POLICY_ID,
    SupportedSelection,
    TARGET_ZONE_COUNT,
    TIE_BREAK_POLICY_ID,
    TractInput,
    TractSelectionError,
    UnsupportedSelection,
    polsby_popper,
    select_national_tracts,
)

RESOLVER_POLICY_SLUG = "national-place-geography-v1"
LEGACY_PHOENIX_AREA_ID = "phoenix-demo"
UNSUPPORTED_STATEFP = frozenset({"02", "15", "60", "66", "69", "72", "78"})
CONUS_DC_STATEFP = frozenset(
    {
        "01",
        "04",
        "05",
        "06",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "53",
        "54",
        "55",
        "56",
    }
)

REASON_INVALID_PLACE_ID = "INVALID_PLACE_ID"
REASON_UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
REASON_UNSUPPORTED_POLICY = "UNSUPPORTED_POLICY"
REASON_MULTI_TIMEZONE_AOI = TimezoneFailureCode.MULTI_TIMEZONE_AOI.value
REASON_TIMEZONE_NOT_FOUND = TimezoneFailureCode.TIMEZONE_NOT_FOUND.value

# GRS80 / EPSG:5070 Albers Equal Area (NAD83 / Conus Albers). I2 analysis CRS.
_A = 6378137.0
_INV_F = 298.257222101
_F = 1.0 / _INV_F
_E2 = 2.0 * _F - _F * _F
_E = math.sqrt(_E2)
_PHI1 = math.radians(29.5)
_PHI2 = math.radians(45.5)
_PHI0 = math.radians(23.0)
_LAM0 = math.radians(-96.0)


def _albers_m(phi: float) -> float:
    s = math.sin(phi)
    return math.cos(phi) / math.sqrt(1.0 - _E2 * s * s)


def _albers_q(phi: float) -> float:
    s = math.sin(phi)
    es = _E * s
    return (1.0 - _E2) * (
        s / (1.0 - _E2 * s * s) - (1.0 / (2.0 * _E)) * math.log((1.0 - es) / (1.0 + es))
    )


_M1 = _albers_m(_PHI1)
_M2 = _albers_m(_PHI2)
_Q0 = _albers_q(_PHI0)
_Q1 = _albers_q(_PHI1)
_Q2 = _albers_q(_PHI2)
_N = (_M1 * _M1 - _M2 * _M2) / (_Q2 - _Q1)
_C = _M1 * _M1 + _N * _Q1
_RHO0 = _A * math.sqrt(_C - _N * _Q0) / _N

__all__ = [
    "CensusPlaceGeometry",
    "CensusTractRecord",
    "PlaceGeographySuccess",
    "PlaceGeographyUnsupported",
    "ResolverPolicy",
    "ResolverPolicyError",
    "build_national_area_id",
    "lonlat_to_5070",
    "resolve_place_geography",
]


class ResolverPolicyError(ValueError):
    """Caller supplied a resolver policy that is not the locked ALG1 default."""


@dataclass(frozen=True)
class CensusPlaceGeometry:
    geometry: BaseGeometry
    intpt_lon: float
    intpt_lat: float
    analysis_geometry: BaseGeometry | None = None


@dataclass(frozen=True)
class CensusTractRecord:
    geoid: str
    geometry: BaseGeometry
    intpt_lon: float
    intpt_lat: float
    aland: float
    analysis_geometry: BaseGeometry | None = None


@dataclass(frozen=True)
class ResolverPolicy:
    resolver_policy_id: str = RESOLVER_POLICY_ID
    algorithm_id: str = ALGORITHM_ID
    census_vintage: str = CENSUS_VINTAGE
    analysis_crs: str = ANALYSIS_CRS
    rook_floor_m: float = ROOK_BOUNDARY_FLOOR_M
    rook_graph: Mapping[str, Sequence[str] | set[str] | frozenset[str]] | None = None
    geometries_are_analysis_crs: bool = False
    timezone_lookup: TimezoneLookup | None = None


@dataclass(frozen=True)
class PlaceGeographySuccess:
    supported: bool
    canonical_place_geoid: str
    resolver_policy_id: str
    algorithm_id: str
    census_vintage: str
    area_id: str
    seed_geoid: str
    seed_rule: str
    seed_rule_id: str
    geoids: tuple[str, ...]
    geoids_sorted: tuple[str, ...]
    eligible_count: int
    relevant_component_size: int
    rook_connected: bool
    eligibility_rule_id: str
    rook_policy_id: str
    projection_crs: str
    growth_rule: str
    tie_break_policy_id: str
    timezone: str
    compactness: float | None = None
    area_m2: float | None = None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PlaceGeographyUnsupported:
    supported: bool
    reason_code: str
    message: str
    details: dict[str, object]
    canonical_place_geoid: str | None
    resolver_policy_id: str
    algorithm_id: str
    census_vintage: str


PlaceGeographyOutcome = PlaceGeographySuccess | PlaceGeographyUnsupported


def build_national_area_id(
    place_geoid: str,
    *,
    census_vintage: str = CENSUS_VINTAGE,
    resolver_policy_id: str = RESOLVER_POLICY_ID,
) -> str:
    slug = resolver_policy_id.strip().lower().replace("_", "-")
    area_id = f"us-place-{place_geoid}-{census_vintage}-{slug}"
    if area_id.strip().lower() == LEGACY_PHOENIX_AREA_ID:
        raise ResolverPolicyError("national geography must not use phoenix-demo")
    return area_id


def lonlat_to_5070(lon: float, lat: float) -> tuple[float, float]:
    lam = math.radians(lon)
    phi = math.radians(lat)
    rho = _A * math.sqrt(_C - _N * _albers_q(phi)) / _N
    theta = _N * (lam - _LAM0)
    return rho * math.sin(theta), _RHO0 - rho * math.cos(theta)


def resolve_place_geography(
    canonical_place: object,
    census_place_geometry: object,
    census_tracts: Sequence[object],
    resolver_policy: object | None = None,
) -> PlaceGeographyOutcome:
    """Deterministic ALG1 25-tract geography, or a structured unsupported fail.

    Eligibility: official TIGER INTPT covered by the place; ALAND <= 0 out.
    Seed: official place TIGER INTPT container; else nearest eligible INTPT
    in EPSG:5070; GEOID ASC. Growth: greedy_lex PP_COMPARE → shared →
    distance → GEOID. Rook: I2 contract (EPSG:5070, linear shared > 1e-3 m),
    or a caller-supplied precomputed graph.
    """
    policy = _normalize_policy(resolver_policy)
    place_geoid, state_fips = _normalize_place(canonical_place)
    if place_geoid is None:
        return _fail(
            REASON_INVALID_PLACE_ID,
            "canonical_place must carry a 7-digit Census place GEOID.",
            {},
            None,
            policy,
        )
    if state_fips in UNSUPPORTED_STATEFP or state_fips not in CONUS_DC_STATEFP:
        return _fail(
            REASON_UNSUPPORTED_SCOPE,
            (
                f"STATEFP={state_fips} is outside CONUS+DC; "
                "Alaska, Hawaii, and territories are not resolved."
            ),
            {"state_fips": state_fips},
            place_geoid,
            policy,
        )

    place_geom, place_intpt, place_analysis_geom, place_analysis_intpt = (
        _normalize_place_geometry(census_place_geometry, policy)
    )
    if place_geom is None or place_intpt is None:
        return _fail(
            REASON_EMPTY_PLACE,
            "census_place_geometry must include official rings and TIGER INTPT.",
            {},
            place_geoid,
            policy,
        )

    try:
        tract_inputs = [
            _normalize_tract(item, policy) for item in census_tracts
        ]
    except TractSelectionError as exc:
        raise TractSelectionError(str(exc)) from exc

    outcome = select_national_tracts(
        place_geom,
        tract_inputs,
        place_intpt=place_intpt,
        place_analysis_intpt=place_analysis_intpt,
        adjacency=policy.rook_graph,
        rook_floor=policy.rook_floor_m,
    )
    if isinstance(outcome, UnsupportedSelection):
        return _fail(
            outcome.reason_code,
            outcome.message,
            dict(outcome.details),
            place_geoid,
            policy,
        )
    return _success_with_timezone(
        place_geoid,
        policy,
        outcome,
        tract_inputs,
        place_analysis_geom,
        place_analysis_intpt,
    )


def _normalize_policy(resolver_policy: object | None) -> ResolverPolicy:
    if resolver_policy is None:
        return ResolverPolicy()
    if isinstance(resolver_policy, ResolverPolicy):
        policy = resolver_policy
    elif isinstance(resolver_policy, str):
        policy = ResolverPolicy(resolver_policy_id=resolver_policy)
    elif isinstance(resolver_policy, Mapping):
        allowed = {
            "resolver_policy_id",
            "algorithm_id",
            "census_vintage",
            "analysis_crs",
            "rook_floor_m",
            "rook_graph",
            "geometries_are_analysis_crs",
            "timezone_lookup",
        }
        kwargs = {key: resolver_policy[key] for key in allowed if key in resolver_policy}
        policy = ResolverPolicy(**kwargs)
    else:
        kwargs: dict[str, Any] = {}
        for key in (
            "resolver_policy_id",
            "algorithm_id",
            "census_vintage",
            "analysis_crs",
            "rook_floor_m",
            "rook_graph",
            "geometries_are_analysis_crs",
            "timezone_lookup",
        ):
            if hasattr(resolver_policy, key):
                value = getattr(resolver_policy, key)
                if value is not None:
                    kwargs[key] = value
        policy = ResolverPolicy(**kwargs)

    policy_id = policy.resolver_policy_id.strip()
    algorithm = policy.algorithm_id.strip()
    allowed_ids = {RESOLVER_POLICY_ID, ALGORITHM_ID, RESOLVER_POLICY_SLUG}
    if policy_id not in allowed_ids and policy_id.lower() not in {
        RESOLVER_POLICY_ID.lower(),
        RESOLVER_POLICY_SLUG,
    }:
        raise ResolverPolicyError(
            f"resolver_policy_id {policy_id!r} is not {RESOLVER_POLICY_ID}"
        )
    if algorithm not in {ALGORITHM_ID, RESOLVER_POLICY_ID}:
        raise ResolverPolicyError(
            f"algorithm {algorithm!r} is not {ALGORITHM_ID}"
        )
    if policy.analysis_crs != ANALYSIS_CRS:
        raise ResolverPolicyError(
            f"analysis CRS must be {ANALYSIS_CRS}, not {policy.analysis_crs!r}"
        )
    if abs(policy.rook_floor_m - ROOK_BOUNDARY_FLOOR_M) > 0.0:
        raise ResolverPolicyError(
            f"rook floor must be {ROOK_BOUNDARY_FLOOR_M} m (I2 contract)"
        )
    return policy


def _normalize_place(canonical_place: object) -> tuple[str | None, str | None]:
    geoid: str | None = None
    state_fips: str | None = None
    if isinstance(canonical_place, str):
        geoid = canonical_place.strip()
    elif isinstance(canonical_place, Mapping):
        geoid = _first_str(
            canonical_place,
            "canonical_place_geoid",
            "place_geoid",
            "geoid",
        )
        state_fips = _first_str(canonical_place, "state_fips", "STATEFP")
    else:
        geoid = _first_attr(
            canonical_place,
            "canonical_place_geoid",
            "place_geoid",
            "geoid",
        )
        state_fips = _first_attr(canonical_place, "state_fips", "STATEFP")
    if geoid is None or not geoid.isdigit() or len(geoid) != 7:
        return None, state_fips
    if state_fips is None:
        state_fips = geoid[:2]
    elif len(state_fips) == 1:
        state_fips = state_fips.zfill(2)
    return geoid, state_fips


def _normalize_place_geometry(
    value: object, policy: ResolverPolicy
) -> tuple[
    BaseGeometry | None,
    tuple[float, float] | None,
    BaseGeometry | None,
    tuple[float, float] | None,
]:
    geom = _geometry_of(value)
    intpt = _intpt_of(value)
    if geom is None or intpt is None:
        return None, None, None, None
    official = make_valid(geom)
    if official.is_empty:
        return None, None, None, None
    analysis = _optional_analysis_geometry(value)
    if policy.geometries_are_analysis_crs:
        analysis_geom = analysis if analysis is not None else official
        analysis_intpt = _optional_analysis_intpt(value) or intpt
        return official, intpt, analysis_geom, analysis_intpt
    analysis_geom = analysis if analysis is not None else _project_5070(official)
    analysis_intpt = _optional_analysis_intpt(value) or lonlat_to_5070(*intpt)
    return official, intpt, analysis_geom, analysis_intpt


def _normalize_tract(value: object, policy: ResolverPolicy) -> TractInput:
    geoid = None
    if isinstance(value, TractInput):
        geoid = value.geoid
        geom = value.geometry
        intpt = value.official_intpt
        aland = value.land_area
        analysis = value.analysis_geometry
        analysis_intpt = value.analysis_intpt
    else:
        geoid = _first_attr(value, "geoid", "GEOID") if not isinstance(value, Mapping) else _first_str(value, "geoid", "GEOID")
        geom = _geometry_of(value)
        intpt = _intpt_of(value)
        aland = _aland_of(value)
        analysis = _optional_analysis_geometry(value)
        analysis_intpt = _optional_analysis_intpt(value)
    if not geoid:
        raise TractSelectionError("census tract is missing GEOID")
    if geom is None:
        raise TractSelectionError(f"tract {geoid!r} is missing official geometry")
    if intpt is None:
        raise TractSelectionError(
            f"tract {geoid!r} is missing official TIGER INTPT; "
            "shapely representative_point is not a substitute"
        )
    land_area = 0.0 if aland is None else float(aland)
    official = make_valid(geom)
    if policy.geometries_are_analysis_crs:
        analysis_geom = analysis if analysis is not None else official
        analysis_xy = analysis_intpt if analysis_intpt is not None else intpt
    else:
        analysis_geom = analysis if analysis is not None else _project_5070(official)
        analysis_xy = (
            analysis_intpt if analysis_intpt is not None else lonlat_to_5070(*intpt)
        )
    return TractInput(
        geoid=str(geoid),
        geometry=official,
        official_intpt=intpt,
        land_area=land_area,
        analysis_geometry=analysis_geom,
        analysis_intpt=analysis_xy,
    )


def _geometry_of(value: object) -> BaseGeometry | None:
    if isinstance(value, BaseGeometry):
        return value
    if isinstance(value, Mapping):
        geom = value.get("geometry") or value.get("geom")
        return geom if isinstance(geom, BaseGeometry) else None
    for name in ("geometry", "geom"):
        if hasattr(value, name):
            geom = getattr(value, name)
            if isinstance(geom, BaseGeometry):
                return geom
    return None


def _intpt_of(value: object) -> tuple[float, float] | None:
    if isinstance(value, Mapping):
        pair = value.get("official_intpt") or value.get("intpt") or value.get("representative_xy")
        if _is_xy(pair):
            return float(pair[0]), float(pair[1])
        lon = value.get("intpt_lon", value.get("INTPTLON"))
        lat = value.get("intpt_lat", value.get("INTPTLAT"))
        if lon is not None and lat is not None:
            return float(lon), float(lat)
        return None
    for name in ("official_intpt", "intpt", "representative_xy"):
        if hasattr(value, name):
            pair = getattr(value, name)
            if _is_xy(pair):
                return float(pair[0]), float(pair[1])
    lon = _maybe_float(getattr(value, "intpt_lon", None))
    lat = _maybe_float(getattr(value, "intpt_lat", None))
    if lon is None:
        lon = _maybe_float(getattr(value, "INTPTLON", None))
    if lat is None:
        lat = _maybe_float(getattr(value, "INTPTLAT", None))
    if lon is not None and lat is not None:
        return lon, lat
    return None


def _optional_analysis_geometry(value: object) -> BaseGeometry | None:
    if isinstance(value, Mapping):
        geom = value.get("analysis_geometry")
        return geom if isinstance(geom, BaseGeometry) else None
    geom = getattr(value, "analysis_geometry", None)
    return geom if isinstance(geom, BaseGeometry) else None


def _optional_analysis_intpt(value: object) -> tuple[float, float] | None:
    if isinstance(value, Mapping):
        pair = value.get("analysis_intpt") or value.get("intpt_xy5070")
        return (float(pair[0]), float(pair[1])) if _is_xy(pair) else None
    pair = getattr(value, "analysis_intpt", None) or getattr(value, "intpt_xy5070", None)
    return (float(pair[0]), float(pair[1])) if _is_xy(pair) else None


def _aland_of(value: object) -> float | None:
    if isinstance(value, Mapping):
        raw = value.get("aland", value.get("ALAND", value.get("land_area")))
        return None if raw is None else float(raw)
    for name in ("aland", "ALAND", "land_area"):
        if hasattr(value, name):
            raw = getattr(value, name)
            if raw is not None:
                return float(raw)
    return None


def _is_xy(value: object) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == 2
    )


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _first_str(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return str(mapping[key]).strip()
    return None


def _first_attr(obj: object, *names: str) -> str | None:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return str(value).strip()
    return None


def _project_5070(geom: BaseGeometry) -> BaseGeometry:
    if geom.is_empty:
        return geom
    projected = shp_transform(lambda x, y, z=None: lonlat_to_5070(x, y), geom)
    if not projected.is_valid:
        projected = make_valid(projected)
    return projected


def _fail(
    reason_code: str,
    message: str,
    details: dict[str, object],
    place_geoid: str | None,
    policy: ResolverPolicy,
) -> PlaceGeographyUnsupported:
    if reason_code == REASON_INSUFFICIENT_RELEVANT_COMPONENT:
        reason_code = REASON_INSUFFICIENT_CONNECTED_TRACTS
        details = {**details, "alias_reason_code": REASON_INSUFFICIENT_RELEVANT_COMPONENT}
    return PlaceGeographyUnsupported(
        supported=False,
        reason_code=reason_code,
        message=message,
        details=details,
        canonical_place_geoid=place_geoid,
        resolver_policy_id=policy.resolver_policy_id,
        algorithm_id=policy.algorithm_id,
        census_vintage=policy.census_vintage,
    )


def _success_with_timezone(
    place_geoid: str,
    policy: ResolverPolicy,
    outcome: SupportedSelection,
    tracts: Sequence[TractInput],
    place_analysis_geom: BaseGeometry | None,
    place_analysis_intpt: tuple[float, float] | None,
) -> PlaceGeographyOutcome:
    geometries = {tract.geoid: tract.geometry for tract in tracts}
    try:
        points = representative_points_from_geometries(outcome.geoids, geometries)
        resolved = resolve_selected_geography_timezone(
            points,
            policy.timezone_lookup,
            zone_ids=outcome.geoids,
        )
    except AoiTimezoneResolutionError as exc:
        return _fail(
            exc.code.value,
            str(exc),
            {
                "point_timezones": list(exc.point_timezones),
                "distinct": list(exc.distinct),
                "timezone_policy_version": TIMEZONE_POLICY_VERSION,
            },
            place_geoid,
            policy,
        )
    except GeographyTimezoneError as exc:
        return _fail(
            exc.code.value,
            str(exc),
            {"timezone_policy_version": TIMEZONE_POLICY_VERSION},
            place_geoid,
            policy,
        )
    return _success(
        place_geoid,
        policy,
        outcome,
        tracts,
        place_analysis_geom,
        place_analysis_intpt,
        timezone=resolved.timezone,
    )


def _success(
    place_geoid: str,
    policy: ResolverPolicy,
    outcome: SupportedSelection,
    tracts: Sequence[TractInput],
    place_analysis_geom: BaseGeometry | None,
    place_analysis_intpt: tuple[float, float] | None,
    *,
    timezone: str,
) -> PlaceGeographySuccess:
    del place_analysis_geom, place_analysis_intpt
    by_id = {tract.geoid: tract for tract in tracts}
    selected_geoms = [
        (tract.analysis_geometry or tract.geometry)
        for geoid in outcome.geoids
        if (tract := by_id.get(geoid)) is not None
    ]
    union = unary_union(selected_geoms) if selected_geoms else Point()
    area_id = build_national_area_id(
        place_geoid,
        census_vintage=policy.census_vintage,
        resolver_policy_id=RESOLVER_POLICY_ID,
    )
    return PlaceGeographySuccess(
        supported=True,
        canonical_place_geoid=place_geoid,
        resolver_policy_id=RESOLVER_POLICY_ID,
        algorithm_id=ALGORITHM_ID,
        census_vintage=policy.census_vintage,
        area_id=area_id,
        seed_geoid=outcome.seed_geoid,
        seed_rule=outcome.seed_rule,
        seed_rule_id=SEED_RULE_ID,
        geoids=outcome.geoids,
        geoids_sorted=outcome.geoids_sorted,
        eligible_count=outcome.eligible_count,
        relevant_component_size=outcome.relevant_component_size,
        rook_connected=outcome.rook_connected,
        eligibility_rule_id=ELIGIBILITY_RULE_ID,
        rook_policy_id=ROOK_POLICY_ID,
        projection_crs=ANALYSIS_CRS,
        growth_rule=GROWTH_RULE_ID,
        tie_break_policy_id=TIE_BREAK_POLICY_ID,
        timezone=timezone,
        compactness=polsby_popper(union) if selected_geoms else None,
        area_m2=float(union.area) if selected_geoms else None,
        details={
            "target_zone_count": TARGET_ZONE_COUNT,
            "timezone": timezone,
            "timezone_policy_version": TIMEZONE_POLICY_VERSION,
        },
    )
