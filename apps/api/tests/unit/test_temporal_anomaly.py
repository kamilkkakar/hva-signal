"""Deterministic tests for Phoenix v1 q_A / temporal_anomaly."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.domain.enums import ReferenceEvidenceQuality, ReferenceRangeStatus
from app.domain.phoenix_v1 import OBS_PER_YEAR, REFERENCE_YEARS
from app.services.temporal_anomaly import (
    ReferenceObservation,
    compute_q_a,
    evaluate_reference_quality,
    midrank_ecdf,
)


def _dates(year: int) -> list[str]:
    start = date(year, 6, 30)
    return [(start + timedelta(days=i)).isoformat() for i in range(OBS_PER_YEAR)]


def _obs(
    geoid: str,
    values_by_year: dict[int, list[float]],
) -> list[ReferenceObservation]:
    rows: list[ReferenceObservation] = []
    for year, values in values_by_year.items():
        dates = _dates(year)
        assert len(values) == len(dates)
        for day, value in zip(dates, values, strict=True):
            rows.append(
                ReferenceObservation(
                    date=day,
                    year=year,
                    geoid=geoid,
                    mean_tcm_c=value,
                )
            )
    return rows


def test_midrank_ecdf_handles_ties() -> None:
    assert midrank_ecdf(2.0, [1.0, 2.0, 2.0, 3.0]) == pytest.approx(0.5)


def test_q_a_is_on_0_1_scale_and_not_percent() -> None:
    rows = _obs(
        "04013100000",
        {year: [10.0] * OBS_PER_YEAR for year in REFERENCE_YEARS},
    )
    result = compute_q_a(
        10.0,
        geoid="04013100000",
        target_date="2025-07-15",
        observations=rows,
    )
    assert result.valid is True
    assert result.q_A == pytest.approx(0.5)
    assert 0.0 <= result.q_A <= 1.0
    assert result.q_A != pytest.approx(50.0)


def test_equal_year_weighting_not_pooled_ecdf() -> None:
    geoid = "04013100000"
    values = {
        2022: [0.0] * OBS_PER_YEAR,
        2023: [100.0] * OBS_PER_YEAR,
        2024: [100.0] * OBS_PER_YEAR,
    }
    rows = _obs(geoid, values)
    target = "2022-07-15"
    result = compute_q_a(50.0, geoid=geoid, target_date=target, observations=rows)
    assert result.valid is True
    assert result.year_n[2022] == 30
    assert result.year_n[2023] == 31
    assert result.year_n[2024] == 31
    assert result.year_components[2022] == pytest.approx(1.0)
    assert result.year_components[2023] == pytest.approx(0.0)
    assert result.year_components[2024] == pytest.approx(0.0)
    assert result.q_A == pytest.approx(1.0 / 3.0)
    pooled_n = 30 + 31 + 31
    pooled = 30 / pooled_n
    assert result.q_A != pytest.approx(pooled)


def test_exclude_target_timestamp_leakage() -> None:
    geoid = "04013100001"
    rows = _obs(geoid, {year: [float(i) for i in range(OBS_PER_YEAR)] for year in REFERENCE_YEARS})
    target = "2023-07-10"
    target_value = next(row.mean_tcm_c for row in rows if row.date == target)
    result = compute_q_a(
        target_value,
        geoid=geoid,
        target_date=target,
        observations=rows,
    )
    assert result.valid is True
    assert result.year_n[2023] == 30
    assert result.year_n[2022] == 31
    assert result.year_n[2024] == 31
    assert sum(result.year_n[year] for year in REFERENCE_YEARS) == 92


def test_q_a_does_not_depend_on_other_tracts() -> None:
    a = _obs("0401310000A", {year: [10.0] * OBS_PER_YEAR for year in REFERENCE_YEARS})
    b = _obs("0401310000B", {year: [90.0] * OBS_PER_YEAR for year in REFERENCE_YEARS})
    mixed = a + b
    left = compute_q_a(10.0, geoid="0401310000A", target_date="2025-07-15", observations=mixed)
    right = compute_q_a(10.0, geoid="0401310000A", target_date="2025-07-15", observations=a)
    assert left.q_A == pytest.approx(right.q_A)
    other = compute_q_a(10.0, geoid="0401310000B", target_date="2025-07-15", observations=mixed)
    assert other.q_A != pytest.approx(left.q_A)


def test_range_status_below_within_above_and_exceedance() -> None:
    geoid = "04013100002"
    rows = _obs(geoid, {year: [20.0] * OBS_PER_YEAR for year in REFERENCE_YEARS})
    below = compute_q_a(18.0, geoid=geoid, target_date="2025-07-15", observations=rows)
    within = compute_q_a(20.0, geoid=geoid, target_date="2025-07-15", observations=rows)
    above = compute_q_a(22.5, geoid=geoid, target_date="2025-07-15", observations=rows)
    assert below.reference_range_status == ReferenceRangeStatus.BELOW.value
    assert below.reference_range_exceedance_c == pytest.approx(2.0)
    assert within.reference_range_status == ReferenceRangeStatus.WITHIN.value
    assert within.reference_range_exceedance_c == pytest.approx(0.0)
    assert above.reference_range_status == ReferenceRangeStatus.ABOVE.value
    assert above.reference_range_exceedance_c == pytest.approx(2.5)


def test_incomplete_reference_is_insufficient_reference() -> None:
    geoid = "04013100003"
    rows = _obs(geoid, {2022: [10.0] * OBS_PER_YEAR, 2023: [10.0] * OBS_PER_YEAR})
    result = compute_q_a(10.0, geoid=geoid, target_date="2025-07-15", observations=rows)
    assert result.valid is False
    assert result.q_A is None
    assert result.reference_quality == ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value


def test_panel_quality_full_and_insufficient() -> None:
    geoids = [f"0401310{i:04d}" for i in range(25)]
    rows: list[ReferenceObservation] = []
    for geoid in geoids:
        rows.extend(_obs(geoid, {year: [30.0] * OBS_PER_YEAR for year in REFERENCE_YEARS}))
    full = evaluate_reference_quality(rows)
    assert full.quality == ReferenceEvidenceQuality.FULL_REFERENCE.value
    dropped = [row for row in rows if not (row.geoid == geoids[0] and row.date == "2022-06-30")]
    incomplete = evaluate_reference_quality(dropped)
    assert incomplete.quality == ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value
