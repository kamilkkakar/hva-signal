"""ALG1 national exactly-25 tract selection. Geometry-only. No vendor I/O.

Locked algorithm: ALG1_GREEDY_LEX_PLACE_INTPT_V1
Policy: NATIONAL_PLACE_GEOGRAPHY_V1

Caller supplies place/tract official rings plus official TIGER INTPT. Analysis
metrics (rook, Polsby-Popper, planar distance) use EPSG:5070 geometries or a
precomputed I2 rook graph. This module does not fetch Census files, does not
read Phoenix frozen artifacts, and does not register public routes.

Phoenix-demo 25 is not a target. Outside-place expansion is refused.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import pi
from typing import AbstractSet, Mapping, Sequence

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

from app.domain.national_geography_package import (
    NATIONAL_ELIGIBILITY_RULE_ID,
    NATIONAL_ROOK_POLICY_ID,
    NATIONAL_SEED_RULE_ID,
    NATIONAL_TIE_BREAK_POLICY_ID,
)

RESOLVER_POLICY_ID = "NATIONAL_PLACE_GEOGRAPHY_V1"
ALGORITHM_ID = "ALG1_GREEDY_LEX_PLACE_INTPT_V1"
POLICY_VERSION = RESOLVER_POLICY_ID
CENSUS_VINTAGE = "2025"
ANALYSIS_CRS = "EPSG:5070"
TARGET_ZONE_COUNT = 25

ELIGIBILITY_RULE_ID = NATIONAL_ELIGIBILITY_RULE_ID
SEED_RULE_ID = NATIONAL_SEED_RULE_ID
SEED_RULE_PLACE_INTPT = "place_intpt_container"
SEED_RULE_NEAREST_INTPT = "nearest_eligible_intpt"
GROWTH_RULE_ID = "greedy_lex"
ROOK_POLICY_ID = NATIONAL_ROOK_POLICY_ID
TIE_BREAK_POLICY_ID = NATIONAL_TIE_BREAK_POLICY_ID

# I2 contract: linear shared boundary in EPSG:5070, millimetre floor.
ROOK_BOUNDARY_FLOOR_M = 1e-3
LINEAR_TYPES = frozenset({"LineString", "MultiLineString", "LinearRing"})

PP_COMPARE_DECIMALS = 6
SHARED_BOUNDARY_ABS_TOL = 1e-6
DISTANCE_ABS_TOL = 1e-6
AREA_ABS_TOL = 1e-9

REASON_EMPTY_PLACE = "EMPTY_PLACE"
REASON_INSUFFICIENT_ELIGIBLE_TRACTS = "INSUFFICIENT_ELIGIBLE_TRACTS"
REASON_INSUFFICIENT_CONNECTED_TRACTS = "INSUFFICIENT_CONNECTED_TRACTS"
REASON_INSUFFICIENT_RELEVANT_COMPONENT = "INSUFFICIENT_RELEVANT_COMPONENT"
REASON_GROWTH_FRONTIER_EXHAUSTED = "GROWTH_FRONTIER_EXHAUSTED"
REASON_RESOLVER_INVARIANT_VIOLATION = "RESOLVER_INVARIANT_VIOLATION"

__all__ = [
    "ALGORITHM_ID",
    "ANALYSIS_CRS",
    "CENSUS_VINTAGE",
    "ELIGIBILITY_RULE_ID",
    "GROWTH_RULE_ID",
    "POLICY_VERSION",
    "REASON_EMPTY_PLACE",
    "REASON_GROWTH_FRONTIER_EXHAUSTED",
    "REASON_INSUFFICIENT_CONNECTED_TRACTS",
    "REASON_INSUFFICIENT_ELIGIBLE_TRACTS",
    "REASON_INSUFFICIENT_RELEVANT_COMPONENT",
    "REASON_RESOLVER_INVARIANT_VIOLATION",
    "RESOLVER_POLICY_ID",
    "ROOK_BOUNDARY_FLOOR_M",
    "ROOK_POLICY_ID",
    "SEED_RULE_ID",
    "SEED_RULE_NEAREST_INTPT",
    "SEED_RULE_PLACE_INTPT",
    "SupportedSelection",
    "TARGET_ZONE_COUNT",
    "TIE_BREAK_POLICY_ID",
    "TractInput",
    "TractSelectionError",
    "ResolverInvariantViolation",
    "UnsupportedSelection",
    "eligible_geoids",
    "polsby_popper",
    "pp_compare",
    "rook_adjacency",
    "select_national_tracts",
]


class TractSelectionError(ValueError):
    """Caller contract failure. Not an unsupported-geography outcome."""


class ResolverInvariantViolation(RuntimeError):
    """Selected 25 failed uniqueness or single-rook-component postcondition."""

    reason_code = REASON_RESOLVER_INVARIANT_VIOLATION


@dataclass(frozen=True)
class TractInput:
    geoid: str
    geometry: BaseGeometry
    official_intpt: tuple[float, float]
    land_area: float | None = None
    analysis_geometry: BaseGeometry | None = None
    analysis_intpt: tuple[float, float] | None = None


@dataclass(frozen=True)
class PreparedTract:
    geoid: str
    official_geometry: BaseGeometry
    analysis_geometry: BaseGeometry
    official_intpt: Point
    analysis_intpt: Point
    land_area: float | None


@dataclass(frozen=True)
class UnsupportedSelection:
    supported: bool
    reason_code: str
    message: str
    details: dict[str, object]
    policy_version: str = POLICY_VERSION
    algorithm_id: str = ALGORITHM_ID


@dataclass(frozen=True)
class SupportedSelection:
    supported: bool
    geoids: tuple[str, ...]
    geoids_sorted: tuple[str, ...]
    seed_geoid: str
    seed_rule: str
    eligible_count: int
    relevant_component_size: int
    eligibility_rule: str
    growth_rule: str
    rook_connected: bool
    policy_version: str = POLICY_VERSION
    algorithm_id: str = ALGORITHM_ID


SelectionOutcome = SupportedSelection | UnsupportedSelection


def select_national_tracts(
    place: BaseGeometry,
    tracts: Sequence[TractInput],
    *,
    place_intpt: tuple[float, float],
    place_analysis_intpt: tuple[float, float] | None = None,
    adjacency: Mapping[str, AbstractSet[str] | Sequence[str]] | None = None,
    rook_floor: float = ROOK_BOUNDARY_FLOOR_M,
) -> SelectionOutcome:
    """Return exactly 25 unique GEOIDs or a structured unsupported outcome.

    Seed is the official place INTPT container, else nearest eligible tract
    INTPT. Shapely representative_point and graph medoid are not used.
    """
    cleaned = make_valid(place)
    if cleaned.is_empty or float(cleaned.area) <= AREA_ABS_TOL:
        return _unsupported(
            REASON_EMPTY_PLACE,
            "Place geometry is empty after make_valid. No tracts are selected.",
            {"eligible_count": 0, "relevant_component_size": 0},
        )
    place_geom = cleaned
    place_pt = Point(place_intpt)
    place_analysis_pt = (
        Point(place_analysis_intpt) if place_analysis_intpt is not None else place_pt
    )
    prepared = _prepare_tracts(tracts)
    eligible = [tract for tract in prepared if _is_eligible(place_geom, tract)]
    eligible_ids = tuple(sorted(tract.geoid for tract in eligible))
    if len(eligible) < TARGET_ZONE_COUNT:
        return _unsupported(
            REASON_INSUFFICIENT_ELIGIBLE_TRACTS,
            (
                f"Eligible tract count {len(eligible)} is below the required "
                f"{TARGET_ZONE_COUNT}. The place is not expanded."
            ),
            {
                "eligible_count": len(eligible),
                "relevant_component_size": 0,
                "eligibility_rule": ELIGIBILITY_RULE_ID,
                "eligible_geoids_sorted": eligible_ids,
            },
        )

    by_id = {tract.geoid: tract for tract in eligible}
    graph = _eligible_graph(by_id, adjacency, rook_floor)
    seed, seed_rule = _choose_seed(eligible, place_pt, place_analysis_pt)
    component_ids = _component(seed.geoid, graph)
    if len(component_ids) < TARGET_ZONE_COUNT:
        return _unsupported(
            REASON_INSUFFICIENT_CONNECTED_TRACTS,
            (
                f"Seed rook-connected component has {len(component_ids)} "
                f"tracts; {TARGET_ZONE_COUNT} are required. Outside-place "
                "expansion is not performed."
            ),
            {
                "eligible_count": len(eligible),
                "relevant_component_size": len(component_ids),
                "seed_geoid": seed.geoid,
                "seed_rule": seed_rule,
                "eligibility_rule": ELIGIBILITY_RULE_ID,
                "alias_reason_code": REASON_INSUFFICIENT_RELEVANT_COMPONENT,
            },
        )

    component = [by_id[geoid] for geoid in sorted(component_ids)]
    selected = _grow_greedy_lex(
        seed=seed,
        component=component,
        graph=graph,
    )
    if selected is None:
        return _unsupported(
            REASON_GROWTH_FRONTIER_EXHAUSTED,
            "Rook frontier emptied before 25 tracts. This indicates a graph bug.",
            {
                "eligible_count": len(eligible),
                "relevant_component_size": len(component_ids),
                "seed_geoid": seed.geoid,
            },
        )

    geoids = tuple(tract.geoid for tract in selected)
    _assert_postcondition(geoids, selected, component_ids, place_geom, graph)
    return SupportedSelection(
        supported=True,
        geoids=geoids,
        geoids_sorted=tuple(sorted(geoids)),
        seed_geoid=seed.geoid,
        seed_rule=seed_rule,
        eligible_count=len(eligible),
        relevant_component_size=len(component_ids),
        eligibility_rule=ELIGIBILITY_RULE_ID,
        growth_rule=GROWTH_RULE_ID,
        rook_connected=True,
    )


def eligible_geoids(
    place: BaseGeometry,
    tracts: Sequence[TractInput],
) -> tuple[str, ...]:
    place_geom = _require_place(place)
    prepared = _prepare_tracts(tracts)
    return tuple(
        sorted(tract.geoid for tract in prepared if _is_eligible(place_geom, tract))
    )


def rook_adjacency(
    tracts: Sequence[PreparedTract | TractInput],
    *,
    floor: float = ROOK_BOUNDARY_FLOOR_M,
) -> dict[str, frozenset[str]]:
    prepared = [
        tract
        if isinstance(tract, PreparedTract)
        else _prepare_one(tract, seen=set())
        for tract in tracts
    ]
    prepared = [tract for tract in prepared if tract is not None]
    geoids = [tract.geoid for tract in prepared]
    geom = {tract.geoid: tract.analysis_geometry for tract in prepared}
    neighbors: dict[str, set[str]] = {geoid: set() for geoid in geoids}
    for index, left in enumerate(geoids):
        for right in geoids[index + 1 :]:
            shared = _shared_boundary_length(geom[left], geom[right])
            if shared > floor:
                neighbors[left].add(right)
                neighbors[right].add(left)
    return {geoid: frozenset(sorted(peers)) for geoid, peers in neighbors.items()}


def polsby_popper(geometry: BaseGeometry) -> float:
    if geometry.is_empty:
        return 0.0
    perimeter = float(geometry.length)
    if perimeter <= 0.0:
        return 0.0
    area = float(geometry.area)
    if area <= 0.0:
        return 0.0
    return (4.0 * pi * area) / (perimeter * perimeter)


def pp_compare(pp_raw: float) -> float:
    return round(pp_raw, PP_COMPARE_DECIMALS)


def _unsupported(
    reason_code: str, message: str, details: dict[str, object]
) -> UnsupportedSelection:
    return UnsupportedSelection(
        supported=False,
        reason_code=reason_code,
        message=message,
        details=details,
    )


def _require_place(place: BaseGeometry) -> BaseGeometry:
    cleaned = make_valid(place)
    if cleaned.is_empty or float(cleaned.area) <= AREA_ABS_TOL:
        raise TractSelectionError("place geometry is empty after make_valid")
    return cleaned


def _prepare_tracts(tracts: Sequence[TractInput]) -> list[PreparedTract]:
    seen: set[str] = set()
    prepared: list[PreparedTract] = []
    for tract in tracts:
        item = _prepare_one(tract, seen)
        if item is not None:
            prepared.append(item)
    prepared.sort(key=lambda item: item.geoid)
    return prepared


def _prepare_one(tract: TractInput, seen: set[str]) -> PreparedTract | None:
    geoid = tract.geoid
    if not isinstance(geoid, str) or not geoid:
        raise TractSelectionError("tract GEOID must be a non-empty string")
    if geoid in seen:
        raise TractSelectionError(f"duplicate tract GEOID {geoid!r}")
    seen.add(geoid)
    if tract.official_intpt is None:
        raise TractSelectionError(
            f"tract {geoid!r} is missing official TIGER INTPT; "
            "shapely representative_point is not a substitute"
        )
    official = make_valid(tract.geometry)
    if official.is_empty or float(official.area) <= AREA_ABS_TOL:
        return None
    analysis = official
    if tract.analysis_geometry is not None:
        analysis = make_valid(tract.analysis_geometry)
        if analysis.is_empty or float(analysis.area) <= AREA_ABS_TOL:
            return None
    analysis_xy = (
        tract.analysis_intpt
        if tract.analysis_intpt is not None
        else tract.official_intpt
    )
    return PreparedTract(
        geoid=geoid,
        official_geometry=official,
        analysis_geometry=analysis,
        official_intpt=Point(tract.official_intpt),
        analysis_intpt=Point(analysis_xy),
        land_area=tract.land_area,
    )


def _is_eligible(place: BaseGeometry, tract: PreparedTract) -> bool:
    if tract.land_area is not None and tract.land_area <= 0:
        return False
    return bool(place.covers(tract.official_intpt))


def _eligible_graph(
    by_id: Mapping[str, PreparedTract],
    adjacency: Mapping[str, AbstractSet[str] | Sequence[str]] | None,
    rook_floor: float,
) -> dict[str, frozenset[str]]:
    if adjacency is None:
        return rook_adjacency(list(by_id.values()), floor=rook_floor)
    graph: dict[str, set[str]] = {geoid: set() for geoid in by_id}
    for geoid in sorted(by_id):
        peers = adjacency.get(geoid, ())
        for peer in peers:
            if peer in by_id and peer != geoid:
                graph[geoid].add(peer)
                graph[peer].add(geoid)
    return {geoid: frozenset(sorted(peers)) for geoid, peers in graph.items()}


def _choose_seed(
    eligible: Sequence[PreparedTract],
    place_pt: Point,
    place_analysis_pt: Point,
) -> tuple[PreparedTract, str]:
    containers = [
        tract for tract in eligible if tract.official_geometry.covers(place_pt)
    ]
    if containers:
        return min(containers, key=lambda tract: tract.geoid), SEED_RULE_PLACE_INTPT
    nearest = min(
        eligible,
        key=lambda tract: (
            _distance(tract.analysis_intpt, place_analysis_pt),
            tract.geoid,
        ),
    )
    return nearest, SEED_RULE_NEAREST_INTPT


def _component(start: str, graph: Mapping[str, AbstractSet[str]]) -> frozenset[str]:
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for peer in sorted(graph.get(node, ())):
            if peer not in seen:
                seen.add(peer)
                queue.append(peer)
    return frozenset(seen)


def _grow_greedy_lex(
    *,
    seed: PreparedTract,
    component: Sequence[PreparedTract],
    graph: Mapping[str, AbstractSet[str]],
) -> list[PreparedTract] | None:
    by_id = {tract.geoid: tract for tract in component}
    selected = [seed]
    selected_ids = {seed.geoid}
    union = seed.analysis_geometry
    while len(selected) < TARGET_ZONE_COUNT:
        frontier = _frontier(selected_ids, graph, by_id)
        if not frontier:
            return None
        choice = _pick_greedy(selected, selected_ids, union, frontier, seed)
        selected.append(choice)
        selected_ids.add(choice.geoid)
        union = unary_union([union, choice.analysis_geometry])
    return selected


def _frontier(
    selected_ids: set[str],
    graph: Mapping[str, AbstractSet[str]],
    by_id: Mapping[str, PreparedTract],
) -> list[PreparedTract]:
    peers: set[str] = set()
    for geoid in selected_ids:
        peers.update(graph.get(geoid, ()))
    return [by_id[geoid] for geoid in sorted(peers - selected_ids) if geoid in by_id]


def _pick_greedy(
    selected: Sequence[PreparedTract],
    selected_ids: set[str],
    union: BaseGeometry,
    frontier: Sequence[PreparedTract],
    seed: PreparedTract,
) -> PreparedTract:
    ranked = [
        (
            _lex_key(
                selected,
                selected_ids,
                candidate,
                seed,
                unary_union([union, candidate.analysis_geometry]),
            ),
            candidate,
        )
        for candidate in frontier
    ]
    ranked.sort(key=lambda item: item[0])
    return ranked[0][1]


_LexKey = tuple[int, int, int, str]


def _lex_key(
    selected: Sequence[PreparedTract],
    selected_ids: set[str],
    candidate: PreparedTract,
    seed: PreparedTract,
    new_union: BaseGeometry,
) -> _LexKey:
    compactness = pp_compare(polsby_popper(new_union))
    shared = _shared_with_selected(candidate, selected, selected_ids)
    distance = _distance(candidate.analysis_intpt, seed.analysis_intpt)
    return (
        -_quantize(compactness, 10 ** (-PP_COMPARE_DECIMALS)),
        -_quantize(shared, SHARED_BOUNDARY_ABS_TOL),
        _quantize(distance, DISTANCE_ABS_TOL),
        candidate.geoid,
    )


def _shared_with_selected(
    candidate: PreparedTract,
    selected: Sequence[PreparedTract],
    selected_ids: set[str],
) -> float:
    total = 0.0
    for tract in selected:
        if tract.geoid in selected_ids:
            total += _shared_boundary_length(
                candidate.analysis_geometry, tract.analysis_geometry
            )
    return total


def _shared_boundary_length(left: BaseGeometry, right: BaseGeometry) -> float:
    if left.is_empty or right.is_empty:
        return 0.0
    if not left.bounds or not right.bounds:
        return 0.0
    minx = max(left.bounds[0], right.bounds[0])
    miny = max(left.bounds[1], right.bounds[1])
    maxx = min(left.bounds[2], right.bounds[2])
    maxy = min(left.bounds[3], right.bounds[3])
    if minx > maxx or miny > maxy:
        return 0.0
    shared = left.boundary.intersection(right.boundary)
    return _linear_length(shared)


def _linear_length(geom: BaseGeometry) -> float:
    if geom.is_empty:
        return 0.0
    kind = geom.geom_type
    if kind in LINEAR_TYPES:
        return float(geom.length)
    if kind == "GeometryCollection":
        return sum(_linear_length(part) for part in geom.geoms)
    return 0.0


def _distance(left: Point, right: Point) -> float:
    return float(left.distance(right))


def _quantize(value: float, abs_tol: float) -> int:
    if abs_tol <= 0.0:
        raise TractSelectionError("abs_tol must be positive")
    return int(round(value / abs_tol))


def _assert_postcondition(
    geoids: tuple[str, ...],
    selected: Sequence[PreparedTract],
    component_ids: frozenset[str],
    place_geom: BaseGeometry,
    graph: Mapping[str, AbstractSet[str]],
) -> None:
    unique = set(geoids)
    if len(geoids) != TARGET_ZONE_COUNT or len(unique) != TARGET_ZONE_COUNT:
        raise ResolverInvariantViolation(
            "selector violated the exactly-25 unique GEOID contract"
        )
    if any(item.geoid not in component_ids for item in selected):
        raise ResolverInvariantViolation("selector escaped the seed rook component")
    if any(not _is_eligible(place_geom, item) for item in selected):
        raise ResolverInvariantViolation("selector included an ineligible tract")
    if not _selected_is_one_rook_component(geoids, graph):
        raise ResolverInvariantViolation(
            "selected 25 is not a single rook-connected component"
        )


def _selected_is_one_rook_component(
    geoids: tuple[str, ...],
    graph: Mapping[str, AbstractSet[str]],
) -> bool:
    want = set(geoids)
    start = geoids[0]
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for peer in sorted(graph.get(node, ())):
            if peer in want and peer not in seen:
                seen.add(peer)
                queue.append(peer)
    return seen == want
