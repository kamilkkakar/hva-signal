"""Phoenix v1 production path: reference quality → q_A → Decision 8.

This is the implementation under test for the historical regression.
It does not freeze AreaConfig and does not call FortyGuard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.enums import (
    ReferenceEvidenceQuality,
    SystemLimitationCode,
    ThermalDifferentiationState,
)
from app.domain.phoenix_v1 import (
    INPUT_QUANTITY,
    REFERENCE_HOUR_LOCAL,
    REFERENCE_VERSION,
    REFERENCE_YEARS,
    ZONE_GEOMETRY_VERSION,
    decision8_policy_fixture,
)
from app.domain.policies import HazardSpreadPolicy
from app.domain.results import HazardSpreadProvenance
from app.services.hazard_spread import evaluate_hazard_spread
from app.services.temporal_anomaly import (
    ReferenceObservation,
    TemporalAnomalyResult,
    compute_q_a,
    evaluate_reference_quality,
)

INSUFFICIENT_REFERENCE = SystemLimitationCode.INSUFFICIENT_REFERENCE.value
THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT = (
    SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
)


@dataclass(frozen=True)
class ZoneThermalState:
    geoid: str
    mean_tcm_c: float
    q_A: float | None
    reference_range_status: str | None
    reference_range_exceedance_c: float | None
    thermal_state_valid: bool
    year_n: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PhoenixV1TimestampEvaluation:
    reference_quality: str
    differentiation_state: str
    thermal_ordering_permitted: bool
    observed_spread: float | None
    bottom3_mean: float | None
    top3_mean: float | None
    system_limitations: list[str]
    zones: list[ZoneThermalState]
    provenance: HazardSpreadProvenance
    suppression_reason: str | None = None


def _provenance(
    *,
    policy: HazardSpreadPolicy,
    reference_quality: str,
    differentiation_state: str,
    observed_spread: float | None,
    suppression_reason: str | None,
) -> HazardSpreadProvenance:
    return HazardSpreadProvenance(
        policy_version=policy.version,
        reference_version=policy.reference_version or REFERENCE_VERSION,
        zone_geometry_version=policy.zone_geometry_version or ZONE_GEOMETRY_VERSION,
        input_quantity=policy.input_quantity or INPUT_QUANTITY,
        metric=policy.metric,
        top_group_size=policy.top_group_size,
        bottom_group_size=policy.bottom_group_size,
        floor=policy.minimum_useful_spread,
        comparison_operator=policy.comparison_operator,
        observed_spread=observed_spread,
        differentiation_state=differentiation_state,
        reference_quality=reference_quality,
        suppression_reason=suppression_reason,
        historical_years=list(REFERENCE_YEARS),
        reference_hour=REFERENCE_HOUR_LOCAL,
    )


def _not_evaluated(
    *,
    policy: HazardSpreadPolicy,
    reference_quality: str,
    reason: str,
    zones: list[ZoneThermalState] | None = None,
    system_limitations: list[str] | None = None,
) -> PhoenixV1TimestampEvaluation:
    return PhoenixV1TimestampEvaluation(
        reference_quality=reference_quality,
        differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
        thermal_ordering_permitted=False,
        observed_spread=None,
        bottom3_mean=None,
        top3_mean=None,
        system_limitations=list(system_limitations or [INSUFFICIENT_REFERENCE]),
        zones=list(zones or []),
        provenance=_provenance(
            policy=policy,
            reference_quality=reference_quality,
            differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
            observed_spread=None,
            suppression_reason=reason,
        ),
        suppression_reason=reason,
    )


def _select_target_rows(
    target_date: str,
    observations: list[ReferenceObservation],
    target_observations: list[ReferenceObservation] | None,
) -> list[ReferenceObservation] | str:
    """Return target tract rows, or a suppression reason if they are unusable."""
    if target_observations is None:
        by_date: dict[str, list[ReferenceObservation]] = {}
        for row in observations:
            by_date.setdefault(row.date, []).append(row)
        if target_date not in by_date:
            return f"target timestamp {target_date} is not present in the reference panel"
        return sorted(by_date[target_date], key=lambda row: row.geoid)

    rows = sorted(target_observations, key=lambda row: row.geoid)
    geoids = [row.geoid for row in rows]
    if len(rows) != 25 or len(set(geoids)) != 25:
        return (
            "target observations must contain exactly 25 distinct tract means; "
            "Decision 8 was not evaluated"
        )
    return rows


def evaluate_phoenix_v1_timestamp(
    target_date: str,
    observations: list[ReferenceObservation],
    *,
    policy: HazardSpreadPolicy | None = None,
    target_observations: list[ReferenceObservation] | None = None,
) -> PhoenixV1TimestampEvaluation:
    """Production Decision 1B + Decision 8 evaluation for one timestamp.

    ``observations`` is the historical FULL_REFERENCE panel only. Optional
    ``target_observations`` supplies out-of-panel target tract means (the
    2025-07-15 demo target) without appending them to the reference.
    """
    spread_policy = policy or decision8_policy_fixture()
    quality = evaluate_reference_quality(observations)
    if quality.quality != ReferenceEvidenceQuality.FULL_REFERENCE.value:
        reason = (
            quality.reason
            or "required historical reference is incomplete; Decision 8 was not evaluated"
        )
        return _not_evaluated(
            policy=spread_policy,
            reference_quality=quality.quality,
            reason=reason,
        )

    selected = _select_target_rows(target_date, observations, target_observations)
    if isinstance(selected, str):
        # In-panel missing date remains the historical fail-closed path.
        # Out-of-panel incomplete targets keep FULL_REFERENCE on the panel.
        panel_quality = (
            quality.quality
            if target_observations is not None
            else ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value
        )
        limitations = (
            []
            if target_observations is not None
            else [INSUFFICIENT_REFERENCE]
        )
        return _not_evaluated(
            policy=spread_policy,
            reference_quality=panel_quality,
            reason=selected,
            system_limitations=limitations,
        )

    target_rows = selected
    zones: list[ZoneThermalState] = []
    q_values: list[float | None] = []
    geoids: list[str] = []
    for row in target_rows:
        anomaly: TemporalAnomalyResult = compute_q_a(
            row.mean_tcm_c,
            geoid=row.geoid,
            target_date=target_date,
            observations=observations,
        )
        q_values.append(anomaly.q_A)
        geoids.append(row.geoid)
        zones.append(
            ZoneThermalState(
                geoid=row.geoid,
                mean_tcm_c=row.mean_tcm_c,
                q_A=anomaly.q_A,
                reference_range_status=anomaly.reference_range_status,
                reference_range_exceedance_c=anomaly.reference_range_exceedance_c,
                thermal_state_valid=anomaly.valid and anomaly.q_A is not None,
                year_n=anomaly.year_n,
            )
        )

    if any(value is None for value in q_values):
        reason = "q_A could not be produced for every required tract under FULL_REFERENCE"
        return PhoenixV1TimestampEvaluation(
            reference_quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
            differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
            thermal_ordering_permitted=False,
            observed_spread=None,
            bottom3_mean=None,
            top3_mean=None,
            system_limitations=[INSUFFICIENT_REFERENCE],
            zones=zones,
            provenance=_provenance(
                policy=spread_policy,
                reference_quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
                differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
                observed_spread=None,
                suppression_reason=reason,
            ),
            suppression_reason=reason,
        )

    evaluation = evaluate_hazard_spread(q_values, spread_policy, zone_ids=geoids)
    return PhoenixV1TimestampEvaluation(
        reference_quality=quality.quality,
        differentiation_state=evaluation.differentiation_state,
        thermal_ordering_permitted=bool(evaluation.ranked),
        observed_spread=evaluation.observed_spread,
        bottom3_mean=evaluation.bottom3_mean,
        top3_mean=evaluation.top3_mean,
        system_limitations=list(evaluation.system_limitations),
        zones=zones,
        provenance=_provenance(
            policy=spread_policy,
            reference_quality=quality.quality,
            differentiation_state=evaluation.differentiation_state,
            observed_spread=evaluation.observed_spread,
            suppression_reason=evaluation.suppression_reason,
        ),
        suppression_reason=evaluation.suppression_reason,
    )


def observations_from_jsonl_rows(rows: list[dict]) -> list[ReferenceObservation]:
    return [
        ReferenceObservation(
            date=str(row["date"]),
            year=int(row["year"]),
            geoid=str(row["geoid"]).zfill(11),
            mean_tcm_c=float(row["mean_tcm_c"]),
        )
        for row in rows
    ]
