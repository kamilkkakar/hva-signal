"""I3 resolve_place_geography unit tests. No Phoenix 25 target. No vendor I/O."""

from __future__ import annotations

import inspect
import itertools
import random

import pytest
from shapely.geometry import Polygon, box

from app.services.national_tract_selection import (
    ALGORITHM_ID,
    REASON_INSUFFICIENT_CONNECTED_TRACTS,
    REASON_INSUFFICIENT_ELIGIBLE_TRACTS,
    TARGET_ZONE_COUNT,
    TractInput,
    TractSelectionError,
    rook_adjacency,
)
from app.services.place_geography_resolver import (
    CensusPlaceGeometry,
    CensusTractRecord,
    PlaceGeographySuccess,
    PlaceGeographyUnsupported,
    ResolverPolicy,
    ResolverPolicyError,
    build_national_area_id,
    lonlat_to_5070,
    resolve_place_geography,
)


def _geoid(row: int, col: int, prefix: str = "99") -> str:
    return f"{prefix}{row:04d}{col:05d}"


def _square(x: float, y: float, size: float = 1.0) -> Polygon:
    return Polygon(((x, y), (x + size, y), (x + size, y + size), (x, y + size)))


def _grid_tracts(
    rows: int,
    cols: int,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    size: float = 1.0,
    prefix: str = "99",
    aland: float = 100.0,
) -> list[CensusTractRecord]:
    ox, oy = origin
    tracts: list[CensusTractRecord] = []
    for row, col in itertools.product(range(rows), range(cols)):
        x = ox + col * size
        y = oy + row * size
        tracts.append(
            CensusTractRecord(
                geoid=_geoid(row, col, prefix),
                geometry=_square(x, y, size),
                intpt_lon=x + size / 2.0,
                intpt_lat=y + size / 2.0,
                aland=aland,
            )
        )
    return tracts


def _metric_policy() -> ResolverPolicy:
    return ResolverPolicy(geometries_are_analysis_crs=True)


def test_resolve_place_geography_signature_is_locked() -> None:
    params = list(inspect.signature(resolve_place_geography).parameters)
    assert params == [
        "canonical_place",
        "census_place_geometry",
        "census_tracts",
        "resolver_policy",
    ]


def test_supported_place_returns_25_unique_and_one_rook_component() -> None:
    tracts = _grid_tracts(7, 7)
    place = CensusPlaceGeometry(
        geometry=box(-0.1, -0.1, 7.1, 7.1),
        intpt_lon=3.5,
        intpt_lat=3.5,
    )
    outcome = resolve_place_geography(
        {"canonical_place_geoid": "1714000", "state_fips": "17"},
        place,
        tracts,
        _metric_policy(),
    )
    assert isinstance(outcome, PlaceGeographySuccess)
    assert outcome.supported is True
    assert len(outcome.geoids) == TARGET_ZONE_COUNT
    assert len(set(outcome.geoids)) == TARGET_ZONE_COUNT
    assert outcome.geoids[0] == outcome.seed_geoid
    assert outcome.geoids_sorted == tuple(sorted(outcome.geoids))
    assert outcome.algorithm_id == ALGORITHM_ID
    assert outcome.resolver_policy_id == "NATIONAL_PLACE_GEOGRAPHY_V1"
    assert outcome.area_id == "us-place-1714000-2025-national-place-geography-v1"
    assert outcome.area_id.lower() != "phoenix-demo"
    assert outcome.rook_connected is True
    assert outcome.projection_crs == "EPSG:5070"
    graph = rook_adjacency(
        [
            TractInput(
                geoid=item.geoid,
                geometry=item.geometry,
                official_intpt=(item.intpt_lon, item.intpt_lat),
                land_area=item.aland,
            )
            for item in tracts
            if item.geoid in set(outcome.geoids)
        ]
    )
    start = outcome.geoids[0]
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for peer in graph[node]:
            if peer not in seen:
                seen.add(peer)
                stack.append(peer)
    assert seen == set(outcome.geoids)


def test_shuffled_and_reversed_tracts_match() -> None:
    tracts = _grid_tracts(7, 7)
    place = CensusPlaceGeometry(box(-0.1, -0.1, 7.1, 7.1), 3.5, 3.5)
    identity = "1714000"
    policy = _metric_policy()
    baseline = resolve_place_geography(identity, place, tracts, policy)
    shuffled = list(tracts)
    random.Random(20260830).shuffle(shuffled)
    again = resolve_place_geography(identity, place, shuffled, policy)
    reversed_order = resolve_place_geography(identity, place, list(reversed(tracts)), policy)
    assert isinstance(baseline, PlaceGeographySuccess)
    assert isinstance(again, PlaceGeographySuccess)
    assert isinstance(reversed_order, PlaceGeographySuccess)
    assert again.geoids == baseline.geoids == reversed_order.geoids
    assert again.seed_geoid == baseline.seed_geoid == reversed_order.seed_geoid


def test_key_west_family_insufficient_eligible() -> None:
    tracts = _grid_tracts(2, 3, prefix="12")
    place = CensusPlaceGeometry(box(-0.1, -0.1, 3.1, 2.1), 1.5, 1.0)
    outcome = resolve_place_geography("1236550", place, tracts, _metric_policy())
    assert isinstance(outcome, PlaceGeographyUnsupported)
    assert outcome.reason_code == REASON_INSUFFICIENT_ELIGIBLE_TRACTS
    assert outcome.details["eligible_count"] == 6


def test_yuma_family_nearest_intpt_lands_in_small_island() -> None:
    large = _grid_tracts(4, 5, origin=(0.0, 0.0), prefix="20")
    small = _grid_tracts(2, 3, origin=(30.0, 0.0), prefix="06")
    place = CensusPlaceGeometry(box(-0.2, -0.2, 34.2, 4.2), 24.0, 1.5)
    outcome = resolve_place_geography("0485540", place, [*large, *small], _metric_policy())
    assert isinstance(outcome, PlaceGeographyUnsupported)
    assert outcome.reason_code == REASON_INSUFFICIENT_CONNECTED_TRACTS
    assert outcome.details["eligible_count"] == 26
    assert outcome.details["relevant_component_size"] == 6
    assert str(outcome.details["seed_geoid"]).startswith("06")
    assert outcome.details["alias_reason_code"] == "INSUFFICIENT_RELEVANT_COMPONENT"


def test_aland_le_zero_is_dropped() -> None:
    land = _grid_tracts(6, 5, prefix="41")
    water = CensusTractRecord(
        geoid="41999999999",
        geometry=_square(2.0, 2.0),
        intpt_lon=2.5,
        intpt_lat=2.5,
        aland=0,
    )
    place = CensusPlaceGeometry(box(-0.1, -0.1, 5.1, 6.1), 2.5, 2.5)
    outcome = resolve_place_geography("1714000", place, [*land, water], _metric_policy())
    assert isinstance(outcome, PlaceGeographySuccess)
    assert "41999999999" not in outcome.geoids
    assert outcome.eligible_count == 30


def test_missing_aland_is_treated_as_zero_and_ineligible() -> None:
    land = _grid_tracts(5, 5, prefix="51")
    missing = {
        "geoid": "51999999999",
        "geometry": _square(2.0, 2.0),
        "intpt_lon": 2.5,
        "intpt_lat": 2.5,
    }
    place = CensusPlaceGeometry(box(-0.1, -0.1, 5.1, 5.1), 2.5, 2.5)
    outcome = resolve_place_geography("1714000", place, [*land, missing], _metric_policy())
    assert isinstance(outcome, PlaceGeographySuccess)
    assert "51999999999" not in outcome.geoids


def test_never_expands_outside_place() -> None:
    inside = _grid_tracts(6, 6, prefix="44")
    outsider = CensusTractRecord(
        geoid="33000000001",
        geometry=_square(40.0, 40.0),
        intpt_lon=40.5,
        intpt_lat=40.5,
        aland=100.0,
    )
    place = CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0)
    outcome = resolve_place_geography("1714000", place, [*inside, outsider], _metric_policy())
    assert isinstance(outcome, PlaceGeographySuccess)
    assert "33000000001" not in outcome.geoids


def test_precomputed_rook_graph_is_accepted() -> None:
    tracts = _grid_tracts(6, 6)
    inputs = [
        TractInput(
            geoid=item.geoid,
            geometry=item.geometry,
            official_intpt=(item.intpt_lon, item.intpt_lat),
            land_area=item.aland,
        )
        for item in tracts
    ]
    graph = rook_adjacency(inputs)
    policy = ResolverPolicy(geometries_are_analysis_crs=True, rook_graph=graph)
    place = CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0)
    first = resolve_place_geography("1714000", place, tracts, policy)
    flipped = ResolverPolicy(
        geometries_are_analysis_crs=True,
        rook_graph={k: list(reversed(list(v))) for k, v in graph.items()},
    )
    second = resolve_place_geography("1714000", place, list(reversed(tracts)), flipped)
    assert isinstance(first, PlaceGeographySuccess)
    assert isinstance(second, PlaceGeographySuccess)
    assert first.geoids == second.geoids


def test_alaska_is_unsupported_scope() -> None:
    tracts = _grid_tracts(6, 6)
    place = CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0)
    outcome = resolve_place_geography("0228000", place, tracts, _metric_policy())
    assert isinstance(outcome, PlaceGeographyUnsupported)
    assert outcome.reason_code == "UNSUPPORTED_SCOPE"


def test_invalid_place_geoid_fails_closed() -> None:
    tracts = _grid_tracts(6, 6)
    place = CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0)
    outcome = resolve_place_geography("chicago", place, tracts, _metric_policy())
    assert isinstance(outcome, PlaceGeographyUnsupported)
    assert outcome.reason_code == "INVALID_PLACE_ID"


def test_wrong_algorithm_is_rejected() -> None:
    tracts = _grid_tracts(6, 6)
    place = CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0)
    with pytest.raises(ResolverPolicyError, match="ALG2"):
        resolve_place_geography(
            "1714000",
            place,
            tracts,
            ResolverPolicy(
                algorithm_id="ALG2_MEDOID_DISTANCE_LEX_V1",
                geometries_are_analysis_crs=True,
            ),
        )


def test_phoenix_utm_analysis_crs_is_rejected() -> None:
    with pytest.raises(ResolverPolicyError, match="32612"):
        resolve_place_geography(
            "1714000",
            CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0),
            _grid_tracts(6, 6),
            ResolverPolicy(analysis_crs="EPSG:32612", geometries_are_analysis_crs=True),
        )


def test_national_phoenix_place_is_not_phoenix_demo() -> None:
    tracts = _grid_tracts(6, 6)
    place = CensusPlaceGeometry(box(-0.1, -0.1, 6.1, 6.1), 3.0, 3.0)
    outcome = resolve_place_geography("0455000", place, tracts, _metric_policy())
    assert isinstance(outcome, PlaceGeographySuccess)
    assert outcome.area_id == "us-place-0455000-2025-national-place-geography-v1"
    assert outcome.area_id != "phoenix-demo"
    assert "phoenix-demo" not in outcome.geoids


def test_build_national_area_id_never_equals_phoenix_demo() -> None:
    assert build_national_area_id("0455000") != "phoenix-demo"
    assert build_national_area_id("1714000").startswith("us-place-1714000-2025-")


def test_duplicate_geoid_is_caller_error() -> None:
    dup = _grid_tracts(1, 2)
    dup[1] = CensusTractRecord(
        geoid=dup[0].geoid,
        geometry=_square(1, 0),
        intpt_lon=1.5,
        intpt_lat=0.5,
        aland=1.0,
    )
    fillers = _grid_tracts(6, 6, origin=(3.0, 0.0), prefix="88")
    with pytest.raises(TractSelectionError, match="duplicate"):
        resolve_place_geography(
            "1714000",
            CensusPlaceGeometry(box(-0.1, -0.1, 12.1, 6.1), 4.0, 3.0),
            [*dup, *fillers],
            _metric_policy(),
        )


def test_official_intpt_is_source_crs_and_growth_uses_supplied_5070_geoms() -> None:
    origin_lon, origin_lat = -112.10, 33.40
    step = 0.01
    tracts: list[dict[str, object]] = []
    for row, col in itertools.product(range(6), range(6)):
        lon0 = origin_lon + col * step
        lat0 = origin_lat + row * step
        ax, ay = float(col), float(row)
        tracts.append(
            {
                "geoid": _geoid(row, col, "04"),
                "geometry": box(lon0, lat0, lon0 + step, lat0 + step),
                "intpt_lon": lon0 + step / 2.0,
                "intpt_lat": lat0 + step / 2.0,
                "aland": 1_000_000,
                "analysis_geometry": _square(ax, ay),
                "analysis_intpt": (ax + 0.5, ay + 0.5),
            }
        )
    outsider = {
        "geoid": "04999999999",
        "geometry": box(-111.00, 33.40, -110.99, 33.41),
        "intpt_lon": -110.995,
        "intpt_lat": 33.405,
        "aland": 1_000_000,
        "analysis_geometry": _square(20.0, 20.0),
        "analysis_intpt": (20.5, 20.5),
    }
    place = CensusPlaceGeometry(
        geometry=box(
            origin_lon - 0.001,
            origin_lat - 0.001,
            origin_lon + 0.061,
            origin_lat + 0.061,
        ),
        intpt_lon=origin_lon + 0.025,
        intpt_lat=origin_lat + 0.025,
        analysis_geometry=box(-0.1, -0.1, 6.1, 6.1),
    )
    outcome = resolve_place_geography(
        "0455000",
        place,
        [*tracts, outsider],
        ResolverPolicy(),
    )
    assert isinstance(outcome, PlaceGeographySuccess)
    assert len(outcome.geoids) == TARGET_ZONE_COUNT
    assert outcome.rook_connected is True
    assert "04999999999" not in outcome.geoids
    assert outcome.projection_crs == "EPSG:5070"
    x, y = lonlat_to_5070(-96.0, 23.0)
    assert abs(x) < 1e-6
    assert abs(y) < 1e-6


def test_module_does_not_import_forbidden_surfaces() -> None:
    import ast

    import app.services.national_tract_selection as selection
    import app.services.place_geography_resolver as resolver

    forbidden = {
        "demo_allowance",
        "demo_allowance_ledger",
        "phoenix_v1_reference",
        "reference_loader",
        "decision8",
        "q_a",
    }
    for module in (selection, resolver):
        tree = ast.parse(inspect.getsource(module))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0].lower() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[-1].lower())
                imported.update(alias.name.lower() for alias in node.names)
        assert forbidden.isdisjoint(imported)
