"""Synthetic ALG1 25-tract selector. No Phoenix GEOIDs. No vendor I/O."""

from __future__ import annotations

import itertools
import math
import random

import pytest
from shapely.geometry import Point, Polygon, box

from app.services.national_tract_selection import (
    ALGORITHM_ID,
    ELIGIBILITY_RULE_ID,
    GROWTH_RULE_ID,
    REASON_INSUFFICIENT_CONNECTED_TRACTS,
    REASON_INSUFFICIENT_ELIGIBLE_TRACTS,
    REASON_INSUFFICIENT_RELEVANT_COMPONENT,
    SEED_RULE_NEAREST_INTPT,
    SEED_RULE_PLACE_INTPT,
    TARGET_ZONE_COUNT,
    SupportedSelection,
    TractInput,
    TractSelectionError,
    UnsupportedSelection,
    eligible_geoids,
    polsby_popper,
    rook_adjacency,
    select_national_tracts,
)


def _geoid(row: int, col: int, prefix: str = "99") -> str:
    return f"{prefix}{row:04d}{col:05d}"


def _square(x: float, y: float, size: float = 1.0) -> Polygon:
    return Polygon(
        (
            (x, y),
            (x + size, y),
            (x + size, y + size),
            (x, y + size),
        )
    )


def _tract(
    geoid: str,
    geometry: Polygon,
    *,
    land_area: float | None = 1.0,
    official_intpt: tuple[float, float] | None = None,
) -> TractInput:
    centroid = geometry.centroid
    return TractInput(
        geoid=geoid,
        geometry=geometry,
        official_intpt=official_intpt or (float(centroid.x), float(centroid.y)),
        land_area=land_area,
    )


def _grid(
    rows: int,
    cols: int,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    size: float = 1.0,
    prefix: str = "99",
) -> list[TractInput]:
    ox, oy = origin
    tracts: list[TractInput] = []
    for row, col in itertools.product(range(rows), range(cols)):
        x = ox + col * size
        y = oy + row * size
        tracts.append(
            _tract(
                _geoid(row, col, prefix),
                _square(x, y, size),
                official_intpt=(x + size / 2.0, y + size / 2.0),
            )
        )
    return tracts


def _place_for_grid(rows: int, cols: int, pad: float = 0.1) -> Polygon:
    return box(-pad, -pad, cols + pad, rows + pad)


def _place_intpt_for_grid(rows: int, cols: int, pad: float = 0.1) -> tuple[float, float]:
    return ((cols + pad - pad) / 2.0, (rows + pad - pad) / 2.0)


def _select(place: Polygon, tracts: list[TractInput], place_intpt: tuple[float, float], **kwargs):
    return select_national_tracts(place, tracts, place_intpt=place_intpt, **kwargs)


def _assert_rook_connected(geoids: tuple[str, ...], tracts: list[TractInput]) -> None:
    chosen = [tract for tract in tracts if tract.geoid in set(geoids)]
    graph = rook_adjacency(chosen)
    start = geoids[0]
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for peer in graph[node]:
            if peer not in seen:
                seen.add(peer)
                stack.append(peer)
    assert seen == set(geoids)


def test_supported_grid_returns_exactly_25_unique_geoids() -> None:
    tracts = _grid(7, 7)
    outcome = _select(_place_for_grid(7, 7), tracts, _place_intpt_for_grid(7, 7))
    assert isinstance(outcome, SupportedSelection)
    assert outcome.supported is True
    assert len(outcome.geoids) == TARGET_ZONE_COUNT
    assert len(set(outcome.geoids)) == TARGET_ZONE_COUNT
    assert outcome.geoids_sorted == tuple(sorted(outcome.geoids))
    assert outcome.seed_geoid in outcome.geoids
    assert outcome.geoids[0] == outcome.seed_geoid
    assert outcome.eligible_count == 49
    assert outcome.relevant_component_size == 49
    assert outcome.algorithm_id == ALGORITHM_ID
    assert outcome.eligibility_rule == ELIGIBILITY_RULE_ID
    assert outcome.growth_rule == GROWTH_RULE_ID
    assert outcome.seed_rule == SEED_RULE_PLACE_INTPT
    assert outcome.rook_connected is True
    _assert_rook_connected(outcome.geoids, tracts)


def test_input_order_does_not_change_selected_set_or_growth_order() -> None:
    tracts = _grid(7, 7)
    place = _place_for_grid(7, 7)
    intpt = _place_intpt_for_grid(7, 7)
    baseline = _select(place, tracts, intpt)
    assert isinstance(baseline, SupportedSelection)
    shuffled = list(tracts)
    random.Random(20260830).shuffle(shuffled)
    again = _select(place, shuffled, intpt)
    assert isinstance(again, SupportedSelection)
    assert again.geoids == baseline.geoids
    assert again.geoids_sorted == baseline.geoids_sorted
    assert again.seed_geoid == baseline.seed_geoid


def test_reversed_input_order_is_deterministic() -> None:
    tracts = _grid(7, 7)
    place = _place_for_grid(7, 7)
    intpt = _place_intpt_for_grid(7, 7)
    first = _select(place, tracts, intpt)
    second = _select(place, list(reversed(tracts)), intpt)
    assert isinstance(first, SupportedSelection)
    assert isinstance(second, SupportedSelection)
    assert first.geoids == second.geoids


def test_insufficient_eligible_is_structured_unsupported() -> None:
    tracts = _grid(4, 4)
    outcome = _select(_place_for_grid(4, 4), tracts, _place_intpt_for_grid(4, 4))
    assert isinstance(outcome, UnsupportedSelection)
    assert outcome.supported is False
    assert outcome.reason_code == REASON_INSUFFICIENT_ELIGIBLE_TRACTS
    assert outcome.details["eligible_count"] == 16


def test_zero_eligible_uses_insufficient_eligible() -> None:
    tracts = _grid(6, 6, origin=(50.0, 50.0))
    outcome = _select(box(0, 0, 2, 2), tracts, (1.0, 1.0))
    assert isinstance(outcome, UnsupportedSelection)
    assert outcome.reason_code == REASON_INSUFFICIENT_ELIGIBLE_TRACTS
    assert outcome.details["eligible_count"] == 0


def test_connected_component_below_25_fails_closed_even_if_eligible_ge_25() -> None:
    large = _grid(6, 5, origin=(0.0, 0.0), prefix="88")
    small = _grid(4, 4, origin=(13.0, 13.0), prefix="77")
    place = box(-0.2, -0.2, 30.2, 30.2)
    outcome = _select(place, [*large, *small], (15.0, 15.0))
    assert isinstance(outcome, UnsupportedSelection)
    assert outcome.reason_code == REASON_INSUFFICIENT_CONNECTED_TRACTS
    assert outcome.details["alias_reason_code"] == REASON_INSUFFICIENT_RELEVANT_COMPONENT
    assert outcome.details["eligible_count"] == 46
    assert outcome.details["relevant_component_size"] == 16
    assert str(outcome.details["seed_geoid"]).startswith("77")


def test_synthetic_12_10_8_graph_is_insufficient_connected() -> None:
    block12 = _grid(3, 4, origin=(0.0, 0.0), prefix="12")
    block10 = _grid(2, 5, origin=(20.0, 0.0), prefix="10")
    block8 = _grid(2, 4, origin=(40.0, 0.0), prefix="08")
    place = box(-1.0, -1.0, 50.0, 5.0)
    outcome = _select(place, [*block12, *block10, *block8], (2.0, 1.5))
    assert isinstance(outcome, UnsupportedSelection)
    assert outcome.reason_code == REASON_INSUFFICIENT_CONNECTED_TRACTS
    assert outcome.details["eligible_count"] == 30
    assert outcome.details["relevant_component_size"] == 12


def test_grows_only_inside_the_relevant_component() -> None:
    other = _grid(6, 6, origin=(0.0, 0.0), prefix="55")
    core = _grid(6, 6, origin=(6.0, 6.0), prefix="66")
    place = box(-0.2, -0.2, 18.2, 18.2)
    outcome = _select(place, [*core, *other], (9.0, 9.0))
    assert isinstance(outcome, SupportedSelection)
    assert all(geoid.startswith("66") for geoid in outcome.geoids)
    assert outcome.relevant_component_size == 36
    _assert_rook_connected(outcome.geoids, core)


def test_queen_only_touch_is_not_rook_adjacency() -> None:
    a = _tract("99000000001", _square(0, 0))
    b = _tract("99000000002", _square(1, 1))
    graph = rook_adjacency([a, b])
    assert graph["99000000001"] == frozenset()
    assert graph["99000000002"] == frozenset()


def test_never_adds_ineligible_tract_outside_place() -> None:
    inside = _grid(6, 6, prefix="44")
    outsider = _tract("33000000001", _square(40.0, 40.0))
    place = _place_for_grid(6, 6)
    outcome = _select(place, [*inside, outsider], _place_intpt_for_grid(6, 6))
    assert isinstance(outcome, SupportedSelection)
    assert "33000000001" not in outcome.geoids
    assert all(geoid in {tract.geoid for tract in inside} for geoid in outcome.geoids)


def test_official_intpt_excludes_c_shaped_ring_whose_centroid_is_inside() -> None:
    donut = box(0, 0, 6, 6).difference(box(2, 2, 4, 4))
    place = box(2.2, 2.2, 3.8, 3.8)
    ring = _tract("99000000010", donut, official_intpt=(0.5, 0.5))
    assert place.covers(donut.centroid)
    assert not place.covers(Point(0.5, 0.5))
    assert eligible_geoids(place, [ring]) == ()


def test_official_intpt_excludes_sliver_giant_outside_place() -> None:
    core = _grid(6, 6, prefix="61")
    giant = _tract("61999999999", box(5.95, 0.0, 20.0, 14.0), official_intpt=(13.0, 7.0))
    place = _place_for_grid(6, 6)
    outcome = _select(place, [*core, giant], _place_intpt_for_grid(6, 6))
    assert isinstance(outcome, SupportedSelection)
    assert "61999999999" not in outcome.geoids
    assert "61999999999" not in eligible_geoids(place, [*core, giant])


def test_majority_straddle_with_intpt_outside_is_ineligible() -> None:
    place = box(0, 0, 2, 2)
    straddle = _tract(
        "99000000021",
        _square(0.0, 0.0, 2.4),
        official_intpt=(2.3, 2.3),
    )
    assert eligible_geoids(place, [straddle]) == ()


def test_zero_land_area_is_never_eligible() -> None:
    place = box(0, 0, 2, 2)
    water = _tract("99000000022", _square(0.2, 0.2), land_area=0.0)
    assert eligible_geoids(place, [water]) == ()


def test_negative_land_area_is_never_eligible() -> None:
    place = box(0, 0, 2, 2)
    water = _tract("99000000023", _square(0.2, 0.2), land_area=-1.0)
    assert eligible_geoids(place, [water]) == ()


def test_duplicate_geoid_is_caller_error() -> None:
    tracts = [
        _tract("99000000001", _square(0, 0)),
        _tract("99000000001", _square(1, 0)),
    ]
    with pytest.raises(TractSelectionError, match="duplicate"):
        _select(box(-0.1, -0.1, 3, 2), tracts, (0.5, 0.5))


def test_missing_official_intpt_is_caller_error() -> None:
    with pytest.raises(TractSelectionError, match="official TIGER INTPT"):
        _select(
            box(-0.1, -0.1, 2, 2),
            [
                TractInput(
                    geoid="99000000001",
                    geometry=_square(0, 0),
                    official_intpt=None,  # type: ignore[arg-type]
                )
            ],
            (0.5, 0.5),
        )


def test_first_step_tie_breaks_by_geoid_not_input_order() -> None:
    seed = _tract("99000000050", _square(1, 1))
    low = _tract("99000000010", _square(2, 1))
    high = _tract("99000000090", _square(0, 1))
    fillers = [
        _tract(_geoid(row, col, "81"), _square(col + 3, row))
        for row, col in itertools.product(range(5), range(5))
    ]
    place = box(-5.0, -3.0, 8.1, 6.0)
    first = _select(place, [seed, high, low, *fillers], (1.5, 1.5))
    second = _select(place, [high, seed, *fillers, low], (1.5, 1.5))
    assert isinstance(first, SupportedSelection)
    assert isinstance(second, SupportedSelection)
    assert first.seed_geoid == "99000000050"
    assert first.geoids[1] == second.geoids[1] == "99000000010"


def test_compactness_first_swallows_adjacent_giant() -> None:
    core = _grid(8, 8, origin=(10.0, 0.0), prefix="70")
    giant = _tract("70999999999", box(0.0, 0.0, 10.0, 10.0), official_intpt=(5.0, 5.0))
    place = box(2.0, 0.0, 19.0, 9.0)
    greedy = _select(place, [*core, giant], (10.5, 4.5))
    assert isinstance(greedy, SupportedSelection)
    assert greedy.seed_geoid.startswith("70")
    assert greedy.seed_geoid != "70999999999"
    assert "70999999999" in greedy.geoids


def test_place_intpt_container_uses_lowest_geoid_on_corner_tie() -> None:
    tracts = _grid(6, 6)
    place = box(0.0, 0.0, 6.0, 6.0)
    outcome = _select(place, tracts, (3.0, 3.0))
    assert isinstance(outcome, SupportedSelection)
    assert outcome.seed_geoid == _geoid(2, 2)
    assert outcome.seed_rule == SEED_RULE_PLACE_INTPT


def test_seed_uses_official_place_intpt_not_shapely_representative_point() -> None:
    core = _grid(6, 6, origin=(0.0, 0.0), prefix="21")
    arm = _grid(6, 6, origin=(0.0, 10.0), prefix="22")
    place = box(-0.1, -0.1, 6.1, 6.1).union(box(-0.1, 9.9, 6.1, 16.1))
    shapely_rp = place.representative_point()
    official = (3.0, 13.0)
    assert not Point(official).equals(shapely_rp)
    outcome = _select(place, [*core, *arm], official)
    assert isinstance(outcome, SupportedSelection)
    assert outcome.seed_rule == SEED_RULE_PLACE_INTPT
    assert outcome.seed_geoid.startswith("22")
    rp_outcome = _select(place, [*core, *arm], (float(shapely_rp.x), float(shapely_rp.y)))
    assert isinstance(rp_outcome, SupportedSelection)
    assert rp_outcome.seed_geoid != outcome.seed_geoid


def test_nearest_eligible_intpt_fallback_is_geoid_stable() -> None:
    left = _grid(6, 5, origin=(0.0, 0.0), prefix="31")
    right = _grid(3, 2, origin=(20.0, 0.0), prefix="32")
    place = box(-0.2, -0.2, 24.2, 6.2)
    # Official place INTPT sits in a hole between the islands.
    hole = (12.0, 3.0)
    first = _select(place, [*left, *right], hole)
    second = _select(place, [*right, *left], hole)
    assert isinstance(first, SupportedSelection)
    assert isinstance(second, SupportedSelection)
    assert first.seed_rule == second.seed_rule == SEED_RULE_NEAREST_INTPT
    assert first.seed_geoid == second.seed_geoid
    assert first.geoids == second.geoids


def test_empty_place_is_structured_unsupported() -> None:
    tracts = _grid(6, 6)
    outcome = _select(Polygon(), tracts, (0.5, 0.5))
    assert isinstance(outcome, UnsupportedSelection)
    assert outcome.reason_code == "EMPTY_PLACE"
    assert outcome.supported is False


def test_supplied_adjacency_is_honored_and_still_deterministic() -> None:
    tracts = _grid(6, 6)
    place = _place_for_grid(6, 6)
    intpt = _place_intpt_for_grid(6, 6)
    graph = rook_adjacency(tracts)
    flipped = {geoid: frozenset(reversed(tuple(peers))) for geoid, peers in graph.items()}
    first = _select(place, tracts, intpt, adjacency=graph)
    second = _select(place, list(reversed(tracts)), intpt, adjacency=flipped)
    assert isinstance(first, SupportedSelection)
    assert isinstance(second, SupportedSelection)
    assert first.geoids == second.geoids


def test_polsby_popper_unit_square_is_stable() -> None:
    value = polsby_popper(_square(0, 0))
    assert math.isclose(value, math.pi / 4.0, rel_tol=0.0, abs_tol=1e-12)
