"""Hazard-spread validator: unfrozen floor is not a pass; missing values are not zero."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.enums import SystemLimitationCode
from app.domain.policies import HazardSpreadPolicy

# Fixture floor only — not a Phoenix probe number and not a production constant.
FIXTURE_FLOOR = 1.25
METRIC = "between_zone_hazard_range"
PHOENIX_PROBE_STRINGS = ("0.003", "0.0003", "0.074")


def _policy(*, floor: float | None) -> HazardSpreadPolicy:
    return HazardSpreadPolicy(
        version="test-spread-v0",
        metric=METRIC,
        minimum_useful_spread=floor,
        behavior_below_floor="surface_system_limitation",
    )


def test_unfrozen_floor_is_not_evaluated_does_not_rank_and_is_not_a_pass() -> None:
    from app.services.hazard_spread import FLOOR_NOT_FROZEN, evaluate_hazard_spread

    # Wide contrast must not be treated as a pass while the floor is unset.
    result = evaluate_hazard_spread([10.0, 20.0, 40.0], _policy(floor=None))

    assert result.evaluated is False
    assert result.ranked is False
    assert result.minimum_useful_spread is None
    assert FLOOR_NOT_FROZEN in result.quality_flags
    assert SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value not in (
        result.system_limitations
    )


def test_unfrozen_floor_does_not_invent_a_numeric_floor() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    result = evaluate_hazard_spread([12.0, 18.0], _policy(floor=None))

    assert result.evaluated is False
    assert result.minimum_useful_spread is None
    assert result.ranked is False


def test_below_fixture_floor_surfaces_limitation_and_does_not_rank() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    # Range of zone means = 1.0, fixture floor = 1.25.
    result = evaluate_hazard_spread([30.0, 30.5, 31.0], _policy(floor=FIXTURE_FLOOR))

    assert result.evaluated is True
    assert result.observed_spread == pytest.approx(1.0)
    assert result.ranked is False
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        in result.system_limitations
    )


def test_at_or_above_fixture_floor_allows_spatial_ranking() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    at_floor = evaluate_hazard_spread([30.0, 31.25], _policy(floor=FIXTURE_FLOOR))
    above_floor = evaluate_hazard_spread([30.0, 32.0], _policy(floor=FIXTURE_FLOOR))

    assert at_floor.evaluated is True
    assert at_floor.observed_spread == pytest.approx(1.25)
    assert at_floor.ranked is True
    assert at_floor.system_limitations == []

    assert above_floor.evaluated is True
    assert above_floor.observed_spread == pytest.approx(2.0)
    assert above_floor.ranked is True
    assert above_floor.system_limitations == []


def test_missing_zone_values_are_never_treated_as_zero() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    # If None became 0, range would be 11.0 and would incorrectly pass the 1.25 floor.
    result = evaluate_hazard_spread([None, 10.0, 11.0], _policy(floor=FIXTURE_FLOOR))

    assert result.observed_spread == pytest.approx(1.0)
    assert result.observed_spread != pytest.approx(11.0)
    assert result.ranked is False
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        in result.system_limitations
    )


def test_all_missing_zone_values_do_not_yield_zero_spread() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    result = evaluate_hazard_spread([None, None], _policy(floor=FIXTURE_FLOOR))

    assert result.observed_spread is None
    assert result.observed_spread != 0
    assert result.ranked is False
    assert "insufficient_evidence" in result.quality_flags
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        not in result.system_limitations
    )


def test_fewer_than_two_present_values_cannot_support_spatial_ranking() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    result = evaluate_hazard_spread([None, 42.0], _policy(floor=FIXTURE_FLOOR))

    assert result.observed_spread is None
    assert result.observed_spread != 42.0
    assert result.ranked is False
    assert "insufficient_evidence" in result.quality_flags


def test_production_hazard_spread_does_not_embed_phoenix_probe_numbers() -> None:
    src = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "hazard_spread.py"
    )
    text = src.read_text(encoding="utf-8")
    for needle in PHOENIX_PROBE_STRINGS:
        assert needle not in text


def _decision8_policy():
    from app.domain.phoenix_v1 import decision8_policy_fixture

    return decision8_policy_fixture()


def _twenty_five(values: list[float], prefix: str = "0401310") -> tuple[list[float], list[str]]:
    assert len(values) == 25
    geoids = [f"{prefix}{i:04d}" for i in range(25)]
    return values, geoids


def test_top3_bottom3_computes_tail_means_and_s() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    values = [0.40 + i * 0.01 for i in range(25)]
    qs, geoids = _twenty_five(values)
    result = evaluate_hazard_spread(qs, _decision8_policy(), zone_ids=geoids)
    bottom = sum(values[:3]) / 3.0
    top = sum(values[-3:]) / 3.0
    assert result.bottom3_mean == pytest.approx(bottom)
    assert result.top3_mean == pytest.approx(top)
    assert result.observed_spread == pytest.approx(top - bottom)
    assert result.metric == "TOP3_BOTTOM3_MEAN_DIFFERENCE"
    assert result.policy_version == (
        "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10"
    )


def test_one_extreme_tract_does_not_behave_like_max_min() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    values = [0.05] * 24 + [0.20]
    qs, geoids = _twenty_five(values)
    result = evaluate_hazard_spread(qs, _decision8_policy(), zone_ids=geoids)
    max_min = 0.20 - 0.05
    assert max_min >= 0.10
    assert result.observed_spread == pytest.approx((0.20 + 0.05 + 0.05) / 3.0 - 0.05)
    assert result.observed_spread < 0.10
    assert result.ranked is False
    assert result.differentiation_state == "INSUFFICIENT"
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        in result.system_limitations
    )


def test_s_at_floor_passes_and_just_below_fails() -> None:
    from app.services.hazard_spread import evaluate_hazard_spread

    at_floor = [0.00] * 3 + [0.05] * 19 + [0.10] * 3
    below = [0.00] * 3 + [0.05] * 19 + [0.099] * 3
    geoids = [f"0401310{i:04d}" for i in range(25)]
    passed = evaluate_hazard_spread(at_floor, _decision8_policy(), zone_ids=geoids)
    failed = evaluate_hazard_spread(below, _decision8_policy(), zone_ids=geoids)
    assert passed.observed_spread == pytest.approx(0.10)
    assert passed.ranked is True
    assert passed.differentiation_state == "SUFFICIENT"
    assert passed.system_limitations == []
    assert failed.observed_spread < 0.10
    assert failed.ranked is False
    assert failed.differentiation_state == "INSUFFICIENT"


def test_wrong_zone_count_does_not_silently_apply_25_zone_policy() -> None:
    from app.services.hazard_spread import WRONG_ZONE_COUNT, evaluate_hazard_spread

    result = evaluate_hazard_spread(
        [0.0, 0.5, 1.0],
        _decision8_policy(),
        zone_ids=["a", "b", "c"],
    )
    assert result.evaluated is False
    assert result.ranked is False
    assert result.observed_spread is None
    assert result.differentiation_state == "NOT_EVALUATED"
    assert WRONG_ZONE_COUNT in result.quality_flags
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        not in result.system_limitations
    )


def test_legacy_max_min_metric_is_not_phoenix_v1_policy() -> None:
    from app.domain.phoenix_v1 import decision8_policy_fixture
    from app.services.hazard_spread import BETWEEN_ZONE_HAZARD_RANGE

    policy = decision8_policy_fixture()
    assert policy.metric != BETWEEN_ZONE_HAZARD_RANGE
    assert policy.metric == "TOP3_BOTTOM3_MEAN_DIFFERENCE"
    assert policy.input_quantity == "q_A"
    assert policy.minimum_useful_spread == pytest.approx(0.10)
