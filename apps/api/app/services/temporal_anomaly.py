"""Phoenix v1 temporal_anomaly (q_A) construction.

Year-balanced own-tract historical ECDF. Not a probability. Not Component B.
Not current-AOI normalization.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from app.domain.enums import ReferenceEvidenceQuality, ReferenceRangeStatus
from app.domain.phoenix_v1 import OBS_PER_YEAR, REFERENCE_YEARS

__all__ = [
    "ReferenceObservation",
    "ReferenceQualityResult",
    "TemporalAnomalyResult",
    "compute_q_a",
    "evaluate_reference_quality",
    "midrank_ecdf",
]


@dataclass(frozen=True)
class ReferenceObservation:
    date: str
    year: int
    geoid: str
    mean_tcm_c: float


@dataclass(frozen=True)
class ReferenceQualityResult:
    quality: str
    n_timestamps: int
    n_tracts: int
    n_rows: int
    reason: str | None = None


@dataclass(frozen=True)
class TemporalAnomalyResult:
    q_A: float | None
    year_components: dict[int, float]
    year_n: dict[int, int]
    reference_range_status: str | None
    reference_range_exceedance_c: float | None
    reference_quality: str
    valid: bool
    reason: str | None = None


def midrank_ecdf(x: float, sorted_ref: list[float]) -> float:
    n = len(sorted_ref)
    if n == 0:
        raise ValueError("empty ECDF reference")
    n_lt = bisect_left(sorted_ref, x)
    n_le = bisect_right(sorted_ref, x)
    n_eq = n_le - n_lt
    return (n_lt + 0.5 * n_eq) / n


def evaluate_reference_quality(
    observations: Iterable[ReferenceObservation],
    *,
    expected_tracts: int = 25,
    expected_years: tuple[int, ...] = REFERENCE_YEARS,
    expected_obs_per_year: int = OBS_PER_YEAR,
) -> ReferenceQualityResult:
    rows = list(observations)
    dates = {row.date for row in rows}
    geoids = {row.geoid for row in rows}
    years = {row.year for row in rows}
    by_geoid_year: dict[tuple[str, int], int] = defaultdict(int)
    for row in rows:
        by_geoid_year[(row.geoid, row.year)] += 1

    expected_timestamps = expected_obs_per_year * len(expected_years)
    expected_rows = expected_timestamps * expected_tracts
    complete_cells = all(
        by_geoid_year[(geoid, year)] == expected_obs_per_year
        for geoid in geoids
        for year in expected_years
    )
    ok = (
        len(rows) == expected_rows
        and len(dates) == expected_timestamps
        and len(geoids) == expected_tracts
        and years == set(expected_years)
        and complete_cells
    )
    if ok:
        return ReferenceQualityResult(
            quality=ReferenceEvidenceQuality.FULL_REFERENCE.value,
            n_timestamps=len(dates),
            n_tracts=len(geoids),
            n_rows=len(rows),
        )
    return ReferenceQualityResult(
        quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
        n_timestamps=len(dates),
        n_tracts=len(geoids),
        n_rows=len(rows),
        reason="required Phoenix v1 reference panel is incomplete",
    )


def _range_status(
    x: float, ref_values: list[float]
) -> tuple[str, float]:
    lo = min(ref_values)
    hi = max(ref_values)
    if x < lo:
        return ReferenceRangeStatus.BELOW.value, lo - x
    if x > hi:
        return ReferenceRangeStatus.ABOVE.value, x - hi
    return ReferenceRangeStatus.WITHIN.value, 0.0


def compute_q_a(
    x: float,
    *,
    geoid: str,
    target_date: str,
    observations: Iterable[ReferenceObservation],
    years: tuple[int, ...] = REFERENCE_YEARS,
    require_full_year_counts: bool = True,
) -> TemporalAnomalyResult:
    """Year-balanced own-tract ECDF with EXCLUDE_TARGET_TIMESTAMP leakage."""
    tract_rows = [
        row for row in observations if row.geoid == geoid and row.year in years
    ]
    target_year: int | None = None
    for row in tract_rows:
        if row.date == target_date:
            target_year = row.year
            break
    if target_year is None:
        try:
            target_year = int(target_date[:4])
        except ValueError:
            target_year = None

    by_year: dict[int, list[float]] = {year: [] for year in years}
    for row in tract_rows:
        if row.date == target_date:
            continue
        by_year[row.year].append(row.mean_tcm_c)

    year_n = {year: len(by_year[year]) for year in years}
    expected_n = {}
    for year in years:
        if target_year is not None and year == target_year and year in years:
            expected_n[year] = OBS_PER_YEAR - 1
        elif year in years:
            expected_n[year] = OBS_PER_YEAR
        else:
            expected_n[year] = OBS_PER_YEAR

    if require_full_year_counts:
        for year in years:
            need = expected_n[year]
            if year_n[year] != need:
                return TemporalAnomalyResult(
                    q_A=None,
                    year_components={},
                    year_n=year_n,
                    reference_range_status=None,
                    reference_range_exceedance_c=None,
                    reference_quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
                    valid=False,
                    reason=(
                        f"tract {geoid} year {year} has {year_n[year]} "
                        f"reference observations; required {need}"
                    ),
                )

    if any(year_n[year] == 0 for year in years):
        return TemporalAnomalyResult(
            q_A=None,
            year_components={},
            year_n=year_n,
            reference_range_status=None,
            reference_range_exceedance_c=None,
            reference_quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
            valid=False,
            reason="at least one required reference year is empty",
        )

    year_q = {
        year: midrank_ecdf(x, sorted(by_year[year])) for year in years
    }
    q_a = sum(year_q[year] for year in years) / float(len(years))
    ref_values = [value for year in years for value in by_year[year]]
    status, exceedance = _range_status(x, ref_values)
    return TemporalAnomalyResult(
        q_A=q_a,
        year_components=year_q,
        year_n=year_n,
        reference_range_status=status,
        reference_range_exceedance_c=exceedance,
        reference_quality=ReferenceEvidenceQuality.FULL_REFERENCE.value,
        valid=True,
    )
