"""Evaluate the candidate persistent relative hourly thermal state.

The evaluator is held-data only. It has no vendor, HTTP, forecast, probability,
or priority dependency.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable

from app.domain.hourly_thermal_event import (
    HourlyThermalEventContract,
    HourlyThermalEventEvaluation,
    HourlyThermalEventObservation,
    HourlyThermalEventRun,
    HourlyThermalEventState,
    HourlyThermalHourAssessment,
    HourlyThermalHourState,
    HourlyThermalReferenceObservation,
)
from app.services.temporal_anomaly import midrank_ecdf


class HourlyThermalEventError(ValueError):
    """Inputs violate the candidate event contract."""


def _exact_local_hour(value: datetime, label: str) -> None:
    if value.tzinfo is not None or any((value.minute, value.second, value.microsecond)):
        raise HourlyThermalEventError(f"{label} must be an exact AOI-local naive hour")


def _expected_hours(start: datetime, end: datetime) -> list[datetime]:
    _exact_local_hour(start, "evaluated_start_local")
    _exact_local_hour(end, "evaluated_end_local_inclusive")
    if end < start:
        raise HourlyThermalEventError("evaluated interval end precedes start")
    count = int((end - start).total_seconds() // 3600) + 1
    if start + timedelta(hours=count - 1) != end:
        raise HourlyThermalEventError("evaluated interval must advance in whole hours")
    return [start + timedelta(hours=offset) for offset in range(count)]


def _month_day_in_window(value: datetime, start: str, end: str) -> bool:
    month_day = value.strftime("%m-%d")
    if start <= end:
        return start <= month_day <= end
    return month_day >= start or month_day <= end


def _validate_identity(
    *,
    contract: HourlyThermalEventContract,
    area_id: str,
    zone_id: str,
    observed: Iterable[HourlyThermalEventObservation],
    reference: Iterable[HourlyThermalReferenceObservation],
) -> None:
    if area_id != contract.area_id:
        raise HourlyThermalEventError("evaluation area_id disagrees with contract")
    if not (zone_id.isdigit() and len(zone_id) == 11):
        raise HourlyThermalEventError("zone_id must be an 11-digit census tract GEOID")
    for row in [*observed, *reference]:
        if row.area_id != area_id or row.zone_id != zone_id:
            raise HourlyThermalEventError("all observations must match evaluation identity")
        if row.temperature_quantity != contract.temperature_quantity:
            raise HourlyThermalEventError("temperature quantity disagrees with contract")
        if row.zone_geometry_version != contract.zone_geometry_version:
            raise HourlyThermalEventError("zone geometry version disagrees with contract")
        if row.aggregation_spec_version != contract.aggregation_spec_version:
            raise HourlyThermalEventError("aggregation version disagrees with contract")
    source_modes = {row.source_mode for row in observed}
    if len(source_modes) > 1:
        raise HourlyThermalEventError("mixed source_mode on one evaluated interval")


def _unique_by_time(rows: Iterable[object], *, label: str) -> dict[datetime, object]:
    indexed: dict[datetime, object] = {}
    for row in rows:
        timestamp = row.valid_time_local  # type: ignore[attr-defined]
        if timestamp in indexed:
            raise HourlyThermalEventError(f"duplicate {label} timestamp: {timestamp.isoformat()}")
        indexed[timestamp] = row
    return indexed


def evaluate_persistent_relative_exceedance(
    *,
    contract: HourlyThermalEventContract,
    area_id: str,
    zone_id: str,
    evaluated_start_local: datetime,
    evaluated_end_local_inclusive: datetime,
    observations: Iterable[HourlyThermalEventObservation],
    reference_observations: Iterable[HourlyThermalReferenceObservation],
) -> HourlyThermalEventEvaluation:
    """Evaluate one zone over an explicitly bounded consecutive-hour interval.

    A qualifying run is positive evidence even when hours elsewhere in the
    interval are missing. A negative finding is emitted only when every hour
    has both an observation and a sufficient same-hour historical reference.
    """

    expected = _expected_hours(evaluated_start_local, evaluated_end_local_inclusive)
    if (
        not contract.persistence.cross_midnight_runs_allowed
        and evaluated_start_local.date() != evaluated_end_local_inclusive.date()
    ):
        raise HourlyThermalEventError("contract does not permit cross-midnight runs")

    observed_rows = list(observations)
    reference_rows = list(reference_observations)
    _validate_identity(
        contract=contract,
        area_id=area_id,
        zone_id=zone_id,
        observed=observed_rows,
        reference=reference_rows,
    )
    observed_by_time = _unique_by_time(observed_rows, label="observation")
    outside = sorted(set(observed_by_time) - set(expected))
    if outside:
        raise HourlyThermalEventError("observation falls outside the evaluated interval")
    _unique_by_time(reference_rows, label="reference")

    threshold_rule = contract.threshold
    reference_by_hour: dict[int, list[HourlyThermalReferenceObservation]] = defaultdict(list)
    for row in reference_rows:
        if row.valid_time_local.year not in threshold_rule.reference_years:
            continue
        if not _month_day_in_window(
            row.valid_time_local,
            threshold_rule.reference_window_start_month_day,
            threshold_rule.reference_window_end_month_day,
        ):
            continue
        reference_by_hour[row.valid_time_local.hour].append(row)

    assessments: list[HourlyThermalHourAssessment] = []
    for timestamp in expected:
        observed = observed_by_time.get(timestamp)
        if observed is None or observed.temperature_c is None:  # type: ignore[union-attr]
            assessments.append(
                HourlyThermalHourAssessment(
                    valid_time_local=timestamp,
                    state=HourlyThermalHourState.MISSING_OBSERVATION,
                    reference_n=0,
                )
            )
            continue

        raw_rows_by_year: dict[int, list[HourlyThermalReferenceObservation]] = {
            year: [] for year in threshold_rule.reference_years
        }
        for row in reference_by_hour.get(timestamp.hour, []):
            raw_rows_by_year[row.valid_time_local.year].append(row)
        target_belongs_to_reference = (
            timestamp.year in threshold_rule.reference_years
            and _month_day_in_window(
                timestamp,
                threshold_rule.reference_window_start_month_day,
                threshold_rule.reference_window_end_month_day,
            )
        )
        reference_complete = all(
            len(raw_rows_by_year[year])
            == threshold_rule.expected_reference_observations_per_year_hour
            for year in threshold_rule.reference_years
        )
        if target_belongs_to_reference:
            reference_complete = reference_complete and any(
                row.valid_time_local == timestamp
                for row in raw_rows_by_year[timestamp.year]
            )
        rows_by_year = {
            year: [
                row.temperature_c
                for row in raw_rows_by_year[year]
                if row.valid_time_local != timestamp
            ]
            for year in threshold_rule.reference_years
        }
        reference_n = sum(len(values) for values in rows_by_year.values())
        if not reference_complete:
            assessments.append(
                HourlyThermalHourAssessment(
                    valid_time_local=timestamp,
                    state=HourlyThermalHourState.INSUFFICIENT_REFERENCE,
                    temperature_c=observed.temperature_c,  # type: ignore[union-attr]
                    reference_n=reference_n,
                )
            )
            continue

        temperature = float(observed.temperature_c)  # type: ignore[union-attr]
        year_components = {
            year: midrank_ecdf(temperature, sorted(rows_by_year[year]))
            for year in threshold_rule.reference_years
        }
        historical_quantile = sum(year_components.values()) / len(year_components)
        qualifies = historical_quantile >= threshold_rule.event_quantile_cutoff
        assessments.append(
            HourlyThermalHourAssessment(
                valid_time_local=timestamp,
                state=HourlyThermalHourState.READY,
                temperature_c=temperature,
                reference_n=reference_n,
                historical_quantile=historical_quantile,
                year_components=year_components,
                qualifies=qualifies,
            )
        )

    minimum_run = contract.persistence.minimum_consecutive_hours
    qualifying_runs: list[HourlyThermalEventRun] = []
    current: list[HourlyThermalHourAssessment] = []

    def finish_run() -> None:
        if len(current) < minimum_run:
            current.clear()
            return
        qualifying_runs.append(
            HourlyThermalEventRun(
                start_time_local=current[0].valid_time_local,
                end_time_local_inclusive=current[-1].valid_time_local,
                consecutive_hour_count=len(current),
                peak_historical_quantile=max(
                    float(item.historical_quantile or 0.0) for item in current
                ),
            )
        )
        current.clear()

    for item in assessments:
        if item.state == HourlyThermalHourState.READY and item.qualifies is True:
            current.append(item)
        else:
            finish_run()
    finish_run()

    n_observed = sum(
        item.state != HourlyThermalHourState.MISSING_OBSERVATION for item in assessments
    )
    n_reference_ready = sum(
        item.state == HourlyThermalHourState.READY for item in assessments
    )
    interval_long_enough = len(expected) >= minimum_run
    complete = (
        interval_long_enough
        and n_observed == len(expected)
        and n_reference_ready == len(expected)
    )
    limitations: list[str] = []
    if n_observed != len(expected):
        limitations.append("MISSING_OBSERVATION")
    if n_reference_ready != n_observed:
        limitations.append("INSUFFICIENT_SAME_HOUR_REFERENCE")
    if not interval_long_enough:
        limitations.append("EVALUATED_INTERVAL_TOO_SHORT")

    if qualifying_runs:
        state = HourlyThermalEventState.DETECTED
    elif complete:
        state = HourlyThermalEventState.NOT_DETECTED
    else:
        state = HourlyThermalEventState.INSUFFICIENT_EVIDENCE

    return HourlyThermalEventEvaluation(
        contract_version=contract.contract_version,
        event_id=contract.event_id,
        area_id=area_id,
        zone_id=zone_id,
        source_mode=(next(iter({row.source_mode for row in observed_rows}), None)),
        temperature_quantity=contract.temperature_quantity,
        zone_geometry_version=contract.zone_geometry_version,
        aggregation_spec_version=contract.aggregation_spec_version,
        evaluated_start_local=evaluated_start_local,
        evaluated_end_local_inclusive=evaluated_end_local_inclusive,
        state=state,
        n_expected_hours=len(expected),
        n_observed_hours=n_observed,
        n_reference_ready_hours=n_reference_ready,
        complete_evaluated_interval=complete,
        negative_finding_supported=state == HourlyThermalEventState.NOT_DETECTED,
        hour_assessments=assessments,
        qualifying_runs=qualifying_runs,
        evidence_limitations=limitations,
    )
