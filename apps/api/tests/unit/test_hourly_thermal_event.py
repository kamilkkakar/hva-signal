"""Candidate persistent relative thermal-event contract and evaluator."""

from __future__ import annotations

import ast
from datetime import date
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.hourly_thermal_event_registry import (
    PHOENIX_HOURLY_EVENT_CONTRACT_SHA256,
    HourlyThermalEventRegistryError,
    load_phoenix_hourly_thermal_event_contract,
)
from app.core.phoenix_v1_area_config import hackathon_root
from app.domain.hourly_thermal_event import (
    HourlyThermalEventObservation,
    HourlyThermalEventState,
    HourlyThermalReferenceObservation,
)
from app.domain.phoenix_v1 import THERMAL_AGGREGATION_VERSION, ZONE_GEOMETRY_VERSION
from app.services.hourly_thermal_event import (
    HourlyThermalEventError,
    evaluate_persistent_relative_exceedance,
)

AREA = "phoenix-demo"
ZONE = "04013107401"
START = datetime(2024, 7, 15, 0)


def _contract():
    return load_phoenix_hourly_thermal_event_contract().contract


def _observations(
    temperatures: dict[int, float | None],
    *,
    start: datetime = START,
) -> list[HourlyThermalEventObservation]:
    return [
        HourlyThermalEventObservation(
            area_id=AREA,
            zone_id=ZONE,
            valid_time_local=start + timedelta(hours=offset),
            temperature_c=value,
            zone_geometry_version=ZONE_GEOMETRY_VERSION,
            aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        )
        for offset, value in temperatures.items()
    ]


def _references(
    *,
    hourly_value: float = 30.0,
    include_target: tuple[datetime, float] | None = None,
) -> list[HourlyThermalReferenceObservation]:
    rows: list[HourlyThermalReferenceObservation] = []
    for hour in range(24):
        for year in (2022, 2023, 2024):
            first = date(year, 6, 30)
            for offset in range(31):
                day = first + timedelta(days=offset)
                timestamp = datetime(day.year, day.month, day.day, hour)
                if include_target and timestamp == include_target[0]:
                    value = include_target[1]
                else:
                    value = hourly_value
                rows.append(
                    HourlyThermalReferenceObservation(
                        area_id=AREA,
                        zone_id=ZONE,
                        valid_time_local=timestamp,
                        temperature_c=value,
                        zone_geometry_version=ZONE_GEOMETRY_VERSION,
                        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
                    )
                )
    return rows


def _evaluate(
    temperatures: dict[int, float | None],
    *,
    start: datetime = START,
    reference: list[HourlyThermalReferenceObservation] | None = None,
):
    return evaluate_persistent_relative_exceedance(
        contract=_contract(),
        area_id=AREA,
        zone_id=ZONE,
        evaluated_start_local=start,
        evaluated_end_local_inclusive=start + timedelta(hours=23),
        observations=_observations(temperatures, start=start),
        reference_observations=reference or _references(),
    )


def test_canonical_candidate_is_hash_locked_and_non_authorizing() -> None:
    resolved = load_phoenix_hourly_thermal_event_contract()
    assert resolved.sha256 == PHOENIX_HOURLY_EVENT_CONTRACT_SHA256
    assert resolved.contract.status == "CANDIDATE"
    assert resolved.contract.threshold.reference_frame == (
        "HISTORICAL_OWN_ZONE_SAME_LOCAL_HOUR"
    )
    assert resolved.contract.threshold.statistic == "YEAR_BALANCED_MIDRANK_ECDF"
    assert resolved.contract.threshold.event_quantile_cutoff == pytest.approx(0.97)
    assert resolved.contract.persistence.minimum_consecutive_hours == 3
    assert resolved.contract.claim_boundaries.calibrated_probability_authorized is False
    assert resolved.contract.claim_boundaries.operational_demand_outcome_claim_authorized is False
    assert resolved.contract.claim_boundaries.degree_hours_authorized is False


def test_candidate_hash_mismatch_fails_closed() -> None:
    with pytest.raises(HourlyThermalEventRegistryError, match="SHA-256 mismatch"):
        load_phoenix_hourly_thermal_event_contract(expected_sha256="0" * 64)


def test_equal_temperature_uses_midrank_not_an_exceedance() -> None:
    result = _evaluate({hour: 30.0 for hour in range(24)})
    assert result.state == HourlyThermalEventState.NOT_DETECTED
    assert result.hour_assessments[0].historical_quantile == pytest.approx(0.5)
    assert result.hour_assessments[0].year_components == {
        2022: pytest.approx(0.5),
        2023: pytest.approx(0.5),
        2024: pytest.approx(0.5),
    }


def test_three_consecutive_exceeding_hours_detect_event() -> None:
    temperatures = {hour: 29.0 for hour in range(24)}
    temperatures.update({14: 31.0, 15: 32.0, 16: 33.0})
    result = _evaluate(temperatures)
    assert result.state == HourlyThermalEventState.DETECTED
    assert result.complete_evaluated_interval is True
    assert result.negative_finding_supported is False
    assert len(result.qualifying_runs) == 1
    run = result.qualifying_runs[0]
    assert run.start_time_local == datetime(2024, 7, 15, 14)
    assert run.end_time_local_inclusive == datetime(2024, 7, 15, 16)
    assert run.consecutive_hour_count == 3
    assert run.peak_historical_quantile == pytest.approx(1.0)
    assert "probability" not in result.model_dump()
    assert "degree_hours" not in result.model_dump()


def test_two_hour_spike_is_not_an_event_when_interval_is_complete() -> None:
    temperatures = {hour: 29.0 for hour in range(24)}
    temperatures.update({14: 31.0, 15: 31.0})
    result = _evaluate(temperatures)
    assert result.state == HourlyThermalEventState.NOT_DETECTED
    assert result.negative_finding_supported is True
    assert result.qualifying_runs == []


def test_missing_hour_breaks_run_and_withholds_negative_finding() -> None:
    temperatures = {hour: 29.0 for hour in range(24) if hour != 15}
    temperatures.update({14: 31.0, 16: 31.0, 17: 31.0})
    result = _evaluate(temperatures)
    assert result.state == HourlyThermalEventState.INSUFFICIENT_EVIDENCE
    assert result.negative_finding_supported is False
    assert result.qualifying_runs == []
    assert result.evidence_limitations == ["MISSING_OBSERVATION"]


def test_positive_run_survives_unrelated_missing_hour_transparently() -> None:
    temperatures = {hour: 29.0 for hour in range(24) if hour != 2}
    temperatures.update({14: 31.0, 15: 31.0, 16: 31.0})
    result = _evaluate(temperatures)
    assert result.state == HourlyThermalEventState.DETECTED
    assert result.complete_evaluated_interval is False
    assert result.evidence_limitations == ["MISSING_OBSERVATION"]


def test_insufficient_same_hour_reference_is_not_a_negative_finding() -> None:
    references = [row for row in _references() if row.valid_time_local.hour != 9]
    result = _evaluate({hour: 29.0 for hour in range(24)}, reference=references)
    assert result.state == HourlyThermalEventState.INSUFFICIENT_EVIDENCE
    assert result.n_reference_ready_hours == 23
    assert result.evidence_limitations == ["INSUFFICIENT_SAME_HOUR_REFERENCE"]


def test_target_timestamp_is_excluded_from_its_own_threshold() -> None:
    target = datetime(2024, 7, 15, 3)
    references = _references(include_target=(target, 100.0))
    result = evaluate_persistent_relative_exceedance(
        contract=_contract(),
        area_id=AREA,
        zone_id=ZONE,
        evaluated_start_local=target,
        evaluated_end_local_inclusive=target,
        observations=_observations({0: 31.0}, start=target),
        reference_observations=references,
    )
    hour = result.hour_assessments[0]
    assert hour.reference_n == 92
    assert hour.historical_quantile == pytest.approx(1.0)
    assert hour.year_components == {
        2022: pytest.approx(1.0),
        2023: pytest.approx(1.0),
        2024: pytest.approx(1.0),
    }
    assert hour.qualifies is True


def test_missing_target_reference_cannot_pose_as_leave_one_out() -> None:
    target = datetime(2024, 7, 15, 3)
    references = [
        row for row in _references() if row.valid_time_local != target
    ]
    result = evaluate_persistent_relative_exceedance(
        contract=_contract(),
        area_id=AREA,
        zone_id=ZONE,
        evaluated_start_local=target,
        evaluated_end_local_inclusive=target,
        observations=_observations({0: 31.0}, start=target),
        reference_observations=references,
    )
    assert result.state == HourlyThermalEventState.INSUFFICIENT_EVIDENCE
    assert result.hour_assessments[0].state.value == "INSUFFICIENT_REFERENCE"
    assert result.evidence_limitations == [
        "INSUFFICIENT_SAME_HOUR_REFERENCE",
        "EVALUATED_INTERVAL_TOO_SHORT",
    ]


def test_short_complete_interval_cannot_support_negative_finding() -> None:
    result = evaluate_persistent_relative_exceedance(
        contract=_contract(),
        area_id=AREA,
        zone_id=ZONE,
        evaluated_start_local=START,
        evaluated_end_local_inclusive=START + timedelta(hours=1),
        observations=_observations({0: 29.0, 1: 29.0}),
        reference_observations=_references(),
    )
    assert result.state == HourlyThermalEventState.INSUFFICIENT_EVIDENCE
    assert result.evidence_limitations == ["EVALUATED_INTERVAL_TOO_SHORT"]


def test_cross_midnight_run_is_consecutive() -> None:
    start = datetime(2024, 7, 15, 12)
    temperatures = {offset: 29.0 for offset in range(24)}
    temperatures.update({10: 31.0, 11: 31.0, 12: 31.0})
    result = _evaluate(temperatures, start=start)
    assert result.state == HourlyThermalEventState.DETECTED
    assert result.qualifying_runs[0].start_time_local == datetime(2024, 7, 15, 22)
    assert result.qualifying_runs[0].end_time_local_inclusive == datetime(2024, 7, 16, 0)


def test_window_aggregate_and_interpolation_are_rejected_at_input() -> None:
    base = {
        "area_id": AREA,
        "zone_id": ZONE,
        "valid_time_local": START,
        "temperature_c": 30.0,
        "zone_geometry_version": ZONE_GEOMETRY_VERSION,
        "aggregation_spec_version": THERMAL_AGGREGATION_VERSION,
    }
    with pytest.raises(ValidationError):
        HourlyThermalEventObservation(**base, temporal_mode="hour_range")
    with pytest.raises(ValidationError):
        HourlyThermalEventObservation(**base, interpolated=True)


def test_identity_mismatch_and_duplicate_hours_fail_closed() -> None:
    observation = HourlyThermalEventObservation(
        area_id=AREA,
        zone_id=ZONE,
        valid_time_local=START,
        temperature_c=31.0,
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
    )
    with pytest.raises(HourlyThermalEventError, match="duplicate observation"):
        evaluate_persistent_relative_exceedance(
            contract=_contract(),
            area_id=AREA,
            zone_id=ZONE,
            evaluated_start_local=START,
            evaluated_end_local_inclusive=START,
            observations=[observation, observation],
            reference_observations=_references(),
        )


def test_mixed_source_modes_fail_closed() -> None:
    observations = _observations({0: 29.0, 1: 29.0, 2: 29.0})
    observations[1] = observations[1].model_copy(update={"source_mode": "cache"})
    with pytest.raises(HourlyThermalEventError, match="mixed source_mode"):
        evaluate_persistent_relative_exceedance(
            contract=_contract(),
            area_id=AREA,
            zone_id=ZONE,
            evaluated_start_local=START,
            evaluated_end_local_inclusive=START + timedelta(hours=2),
            observations=observations,
            reference_observations=_references(),
        )


def test_evaluator_has_no_network_vendor_or_probability_dependency() -> None:
    source = (
        hackathon_root() / "apps/api/app/services/hourly_thermal_event.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "httpx" not in imported
    assert all("fortyguard" not in name for name in imported)
    assert all("probability" not in name for name in imported)
