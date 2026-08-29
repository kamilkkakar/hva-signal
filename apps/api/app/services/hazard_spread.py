"""Runtime hazard-spread validator.

Phoenix v1 Decision 8 uses TOP3_BOTTOM3_MEAN_DIFFERENCE on q_A.
Legacy between_zone_hazard_range (max−min) is retained only for existing
non-Phoenix-v1 tests/paths. It is not the Phoenix v1 ranking gate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.domain.enums import (
    SystemLimitationCode,
    ThermalDifferentiationState,
)
from app.domain.phoenix_v1 import METRIC_TOP3_BOTTOM3
from app.domain.policies import HazardSpreadPolicy

FLOOR_NOT_FROZEN = "FLOOR_NOT_FROZEN"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
BETWEEN_ZONE_HAZARD_RANGE = "between_zone_hazard_range"
WRONG_ZONE_COUNT = "WRONG_ZONE_COUNT"
INCOMPLETE_Q_A_FIELD = "INCOMPLETE_Q_A_FIELD"
TOP3_BOTTOM3_MEAN_DIFFERENCE = METRIC_TOP3_BOTTOM3

THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT = (
    SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
)

__all__ = [
    "BETWEEN_ZONE_HAZARD_RANGE",
    "FLOOR_NOT_FROZEN",
    "HazardSpreadEvaluation",
    "TOP3_BOTTOM3_MEAN_DIFFERENCE",
    "WRONG_ZONE_COUNT",
    "evaluate_hazard_spread",
]


@dataclass(frozen=True)
class HazardSpreadEvaluation:
    evaluated: bool
    ranked: bool
    observed_spread: float | None
    metric: str
    minimum_useful_spread: float | None
    policy_version: str
    system_limitations: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)
    differentiation_state: str = ThermalDifferentiationState.NOT_EVALUATED.value
    top3_mean: float | None = None
    bottom3_mean: float | None = None
    top_group_size: int | None = None
    bottom_group_size: int | None = None
    comparison_operator: str | None = None
    input_quantity: str | None = None
    suppression_reason: str | None = None
    top3_zone_ids: tuple[str, ...] = ()
    bottom3_zone_ids: tuple[str, ...] = ()


def _present_zone_values(zone_values: Sequence[float | None]) -> list[float]:
    present: list[float] = []
    for value in zone_values:
        if value is None:
            continue
        present.append(float(value))
    return present


def _range_of_zone_means(present: Sequence[float]) -> float | None:
    """Between-zone range. Missing values are omitted; never coerced to 0."""
    if len(present) < 2:
        return None
    return max(present) - min(present)


def _legacy_range_evaluation(
    zone_values: Sequence[float | None],
    policy: HazardSpreadPolicy,
) -> HazardSpreadEvaluation:
    present = _present_zone_values(zone_values)
    observed_spread = _range_of_zone_means(present)
    quality_flags: list[str] = []
    system_limitations: list[str] = []

    if policy.minimum_useful_spread is None:
        quality_flags.append(FLOOR_NOT_FROZEN)
        return HazardSpreadEvaluation(
            evaluated=False,
            ranked=False,
            observed_spread=observed_spread,
            metric=policy.metric,
            minimum_useful_spread=None,
            policy_version=policy.version,
            system_limitations=system_limitations,
            quality_flags=quality_flags,
            differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
            input_quantity=policy.input_quantity,
        )

    if observed_spread is None:
        quality_flags.append(INSUFFICIENT_EVIDENCE)
        return HazardSpreadEvaluation(
            evaluated=True,
            ranked=False,
            observed_spread=None,
            metric=policy.metric,
            minimum_useful_spread=policy.minimum_useful_spread,
            policy_version=policy.version,
            system_limitations=system_limitations,
            quality_flags=quality_flags,
            differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
            input_quantity=policy.input_quantity,
            suppression_reason="fewer than two present zone values",
        )

    if observed_spread < policy.minimum_useful_spread:
        if policy.behavior_below_floor == "surface_system_limitation":
            system_limitations.append(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT)
        return HazardSpreadEvaluation(
            evaluated=True,
            ranked=False,
            observed_spread=observed_spread,
            metric=policy.metric,
            minimum_useful_spread=policy.minimum_useful_spread,
            policy_version=policy.version,
            system_limitations=system_limitations,
            quality_flags=quality_flags,
            differentiation_state=ThermalDifferentiationState.INSUFFICIENT.value,
            input_quantity=policy.input_quantity,
            comparison_operator=">=",
            suppression_reason="observed max-min spread is below the configured floor",
        )

    return HazardSpreadEvaluation(
        evaluated=True,
        ranked=True,
        observed_spread=observed_spread,
        metric=policy.metric,
        minimum_useful_spread=policy.minimum_useful_spread,
        policy_version=policy.version,
        system_limitations=system_limitations,
        quality_flags=quality_flags,
        differentiation_state=ThermalDifferentiationState.SUFFICIENT.value,
        input_quantity=policy.input_quantity,
        comparison_operator=">=",
    )


def _top3_bottom3(
    zone_values: Sequence[float | None],
    zone_ids: Sequence[str] | None,
    policy: HazardSpreadPolicy,
) -> HazardSpreadEvaluation:
    expected = policy.expected_zone_count
    top_n = policy.top_group_size
    bottom_n = policy.bottom_group_size
    if expected is None or top_n is None or bottom_n is None:
        raise ValueError(
            "TOP3_BOTTOM3_MEAN_DIFFERENCE requires expected_zone_count, "
            "top_group_size, and bottom_group_size"
        )
    ids = list(zone_ids) if zone_ids is not None else [str(i) for i in range(len(zone_values))]
    if len(ids) != len(zone_values):
        raise ValueError("zone_ids length must match zone_values")

    pairs: list[tuple[str, float]] = []
    missing = 0
    for zone_id, value in zip(ids, zone_values, strict=True):
        if value is None:
            missing += 1
            continue
        pairs.append((str(zone_id), float(value)))

    quality_flags: list[str] = []
    if policy.minimum_useful_spread is None:
        quality_flags.append(FLOOR_NOT_FROZEN)
        return HazardSpreadEvaluation(
            evaluated=False,
            ranked=False,
            observed_spread=None,
            metric=policy.metric,
            minimum_useful_spread=None,
            policy_version=policy.version,
            quality_flags=quality_flags,
            differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
            input_quantity=policy.input_quantity or "q_A",
            top_group_size=top_n,
            bottom_group_size=bottom_n,
            comparison_operator=policy.comparison_operator or ">=",
            suppression_reason="Decision 8 floor is not present on the supplied policy",
        )

    if len(zone_values) != expected or missing > 0 or len(pairs) != expected:
        quality_flags.append(WRONG_ZONE_COUNT if len(zone_values) != expected else INCOMPLETE_Q_A_FIELD)
        return HazardSpreadEvaluation(
            evaluated=False,
            ranked=False,
            observed_spread=None,
            metric=policy.metric,
            minimum_useful_spread=policy.minimum_useful_spread,
            policy_version=policy.version,
            quality_flags=quality_flags,
            differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
            input_quantity=policy.input_quantity or "q_A",
            top_group_size=top_n,
            bottom_group_size=bottom_n,
            comparison_operator=policy.comparison_operator or ">=",
            suppression_reason=(
                f"Decision 8 requires exactly {expected} valid q_A values; "
                f"received {len(zone_values)} values, {len(pairs)} valid"
            ),
        )

    ordered = sorted(pairs, key=lambda item: (item[1], item[0]))
    bottom = ordered[:bottom_n]
    top = list(reversed(ordered[-top_n:]))
    bottom_mean = sum(v for _, v in bottom) / float(bottom_n)
    top_mean = sum(v for _, v in top) / float(top_n)
    spread = top_mean - bottom_mean
    operator = policy.comparison_operator or ">="
    if operator != ">=":
        raise ValueError(f"Unsupported comparison operator: {operator!r}")

    if spread >= policy.minimum_useful_spread:
        return HazardSpreadEvaluation(
            evaluated=True,
            ranked=True,
            observed_spread=spread,
            metric=policy.metric,
            minimum_useful_spread=policy.minimum_useful_spread,
            policy_version=policy.version,
            differentiation_state=ThermalDifferentiationState.SUFFICIENT.value,
            top3_mean=top_mean,
            bottom3_mean=bottom_mean,
            top_group_size=top_n,
            bottom_group_size=bottom_n,
            comparison_operator=operator,
            input_quantity=policy.input_quantity or "q_A",
            top3_zone_ids=tuple(z for z, _ in top),
            bottom3_zone_ids=tuple(z for z, _ in bottom),
        )

    limitations: list[str] = []
    if policy.behavior_below_floor == "surface_system_limitation":
        limitations.append(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT)
    return HazardSpreadEvaluation(
        evaluated=True,
        ranked=False,
        observed_spread=spread,
        metric=policy.metric,
        minimum_useful_spread=policy.minimum_useful_spread,
        policy_version=policy.version,
        system_limitations=limitations,
        differentiation_state=ThermalDifferentiationState.INSUFFICIENT.value,
        top3_mean=top_mean,
        bottom3_mean=bottom_mean,
        top_group_size=top_n,
        bottom_group_size=bottom_n,
        comparison_operator=operator,
        input_quantity=policy.input_quantity or "q_A",
        suppression_reason=(
            "normalized hazard spread S is below the frozen Decision 8 floor"
        ),
        top3_zone_ids=tuple(z for z, _ in top),
        bottom3_zone_ids=tuple(z for z, _ in bottom),
    )


def evaluate_hazard_spread(
    zone_values: Sequence[float | None],
    policy: HazardSpreadPolicy,
    *,
    zone_ids: Sequence[str] | None = None,
) -> HazardSpreadEvaluation:
    """Validate whether zone hazard values support a spatial thermal ranking.

    A missing ``minimum_useful_spread`` is not a pass: the check is not
    evaluated, ranking is withheld, and ``FLOOR_NOT_FROZEN`` is surfaced.
    No production floor is invented here.
    """
    if policy.metric == BETWEEN_ZONE_HAZARD_RANGE:
        return _legacy_range_evaluation(zone_values, policy)
    if policy.metric == TOP3_BOTTOM3_MEAN_DIFFERENCE:
        return _top3_bottom3(zone_values, zone_ids, policy)
    raise ValueError(f"Unsupported hazard-spread metric: {policy.metric!r}")
