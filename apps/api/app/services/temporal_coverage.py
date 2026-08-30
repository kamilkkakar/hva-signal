"""T-L completeness classifiers.

POLICY_ID: PHX_TEMPORAL_COVERAGE_POLICY_V1_CANDIDATE
Numeric cuts are CANDIDATE — human lock required. Do not copy onto AreaConfig.
Completeness only: not Decision 8, not FULL_REFERENCE, not heat.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.temporal import SamplingDesign, TemporalCoverageClass

COVERAGE_POLICY_ID = "PHX_TEMPORAL_COVERAGE_POLICY_V1_CANDIDATE"

# --- CANDIDATE numeric cuts (T-L). Do not treat as frozen science. ---
DAILY_HOURLY_24_FULL = 24  # CANDIDATE
DAILY_HOURLY_24_ADEQUATE_MIN = 18  # CANDIDATE
DAILY_BIN_ADEQUATE_MIN = 4  # CANDIDATE: ≥4/6 in each 6-h bin
DAILY_MAX_GAP_HOURS = 3  # CANDIDATE
SPATIAL_FULL = 25  # CANDIDATE / locked geography count
SPATIAL_ADEQUATE_MIN = 20  # CANDIDATE
SPATIAL_PARTIAL_MIN = 13  # CANDIDATE
MONTHLY_ADEQUATE_DAY_RATIO = 0.80  # CANDIDATE
MONTHLY_ADEQUATE_SLOT_RATIO = 0.80  # CANDIDATE
MONTHLY_PARTIAL_RATIO = 0.50  # CANDIDATE
MONTHLY_MAX_GAP_DAYS = 5  # CANDIDATE
SEASONAL_ADEQUATE_DAY_RATIO = 0.80  # CANDIDATE
SEASONAL_PARTIAL_DAY_RATIO = 0.50  # CANDIDATE
SEASONAL_MAX_GAP_DAYS = 7  # CANDIDATE
YOY_PAIR_ADEQUATE_RATIO = 0.80  # CANDIDATE
YOY_PAIR_PARTIAL_RATIO = 0.50  # CANDIDATE
YOY_PAIR_FULL_DELTA = 0.05  # CANDIDATE
YOY_PAIR_ADEQUATE_DELTA = 0.10  # CANDIDATE

NIGHT_HOURS = frozenset({0, 1, 2, 3, 4, 5})
MORNING_HOURS = frozenset({6, 7, 8, 9, 10, 11})
AFTERNOON_HOURS = frozenset({12, 13, 14, 15, 16, 17})
EVENING_HOURS = frozenset({18, 19, 20, 21, 22, 23})
CLOCK_BINS = {
    "night": NIGHT_HOURS,
    "morning": MORNING_HOURS,
    "afternoon": AFTERNOON_HOURS,
    "evening": EVENING_HOURS,
}

SIGNAL_A_REFERENCE_TOKENS = frozenset({"FULL_REFERENCE", "INSUFFICIENT_REFERENCE"})
DECISION8_TOKENS = frozenset({"INSUFFICIENT_EVIDENCE", "SUFFICIENT", "D8_INSUFFICIENT"})


class CoverageClaimError(ValueError):
    """Undefined claim cube — do not classify."""


def bin_present_counts(present_hours: set[int]) -> dict[str, int]:
    return {name: sum(1 for hour in hours if hour in present_hours) for name, hours in CLOCK_BINS.items()}


def longest_linear_gap_hours(present_hours: set[int], n_expected: int = 24) -> int:
    if n_expected <= 0:
        raise CoverageClaimError("n_expected must be > 0")
    if not present_hours:
        return n_expected
    longest = 0
    run = 0
    for hour in range(n_expected):
        if hour not in present_hours:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


def classify_spatial(n_valid_zones: int, n_expected_zones: int = 25) -> TemporalCoverageClass:
    if n_expected_zones != 25:
        # Still classify against the declared count; phoenix-demo is 25.
        pass
    if n_valid_zones <= 0:
        return TemporalCoverageClass.INSUFFICIENT
    if n_valid_zones >= SPATIAL_FULL and n_expected_zones == 25:
        return TemporalCoverageClass.FULL
    if n_valid_zones >= SPATIAL_ADEQUATE_MIN:
        return TemporalCoverageClass.ADEQUATE
    if n_valid_zones >= SPATIAL_PARTIAL_MIN:
        return TemporalCoverageClass.PARTIAL
    return TemporalCoverageClass.INSUFFICIENT


def classify_daily_hourly_24(
    n_present: int,
    bin_present: dict[str, int] | None = None,
    longest_gap: int | None = None,
    present_hours: set[int] | None = None,
) -> TemporalCoverageClass:
    """HOURLY_24 completeness. 0 hours → INSUFFICIENT; 1–17 or unstructured 18+ → PARTIAL."""
    if present_hours is not None:
        n_present = len(present_hours)
        bin_present = bin_present_counts(present_hours)
        longest_gap = longest_linear_gap_hours(present_hours)
    if n_present <= 0:
        return TemporalCoverageClass.INSUFFICIENT
    if n_present == DAILY_HOURLY_24_FULL:
        return TemporalCoverageClass.FULL
    bins = bin_present or {}
    gap = 0 if longest_gap is None else longest_gap
    adequate = (
        n_present >= DAILY_HOURLY_24_ADEQUATE_MIN
        and all(bins.get(name, 0) >= DAILY_BIN_ADEQUATE_MIN for name in CLOCK_BINS)
        and gap <= DAILY_MAX_GAP_HOURS
    )
    if adequate:
        return TemporalCoverageClass.ADEQUATE
    return TemporalCoverageClass.PARTIAL


def classify_sampled_day(n_present: int, n_expected: int, *, has_night: bool, has_day: bool) -> TemporalCoverageClass:
    if n_expected <= 0:
        raise CoverageClaimError("sampled design requires n_expected > 0")
    if n_present <= 0:
        return TemporalCoverageClass.INSUFFICIENT
    if n_present == n_expected:
        return TemporalCoverageClass.FULL
    if n_expected <= 2:
        return TemporalCoverageClass.PARTIAL
    if n_present >= n_expected - 1 and has_night and has_day:
        return TemporalCoverageClass.ADEQUATE
    return TemporalCoverageClass.PARTIAL


def classify_anchor_0300(present: bool) -> TemporalCoverageClass:
    return TemporalCoverageClass.FULL if present else TemporalCoverageClass.INSUFFICIENT


def classify_for_design(
    sampling_design: SamplingDesign | str,
    *,
    n_present: int,
    n_expected: int,
    present_hours: set[int] | None = None,
) -> TemporalCoverageClass:
    design = SamplingDesign(sampling_design)
    if design is SamplingDesign.HOURLY_24:
        return classify_daily_hourly_24(n_present, present_hours=present_hours)
    if design is SamplingDesign.ANCHOR_0300:
        return classify_anchor_0300(n_present >= 1)
    if design is SamplingDesign.TYPE2_WINDOW:
        return TemporalCoverageClass.FULL if n_present >= 1 else TemporalCoverageClass.INSUFFICIENT
    hours = present_hours or set()
    has_night = bool(hours & NIGHT_HOURS)
    has_day = bool(hours & AFTERNOON_HOURS) or bool(hours & MORNING_HOURS)
    return classify_sampled_day(n_present, n_expected, has_night=has_night, has_day=has_day)


def classify_monthly(
    *,
    n_contributing_days: int,
    n_calendar_days: int,
    n_present_slots: int,
    n_expected_slots: int,
    longest_gap_days: int,
) -> TemporalCoverageClass:
    if n_calendar_days <= 0 or n_expected_slots <= 0:
        raise CoverageClaimError("monthly claim cube is undefined")
    day_ratio = n_contributing_days / n_calendar_days
    slot_ratio = n_present_slots / n_expected_slots
    if n_contributing_days == n_calendar_days and n_present_slots == n_expected_slots:
        return TemporalCoverageClass.FULL
    if (
        day_ratio >= MONTHLY_ADEQUATE_DAY_RATIO
        and slot_ratio >= MONTHLY_ADEQUATE_SLOT_RATIO
        and longest_gap_days <= MONTHLY_MAX_GAP_DAYS
    ):
        return TemporalCoverageClass.ADEQUATE
    if day_ratio >= MONTHLY_PARTIAL_RATIO or slot_ratio >= MONTHLY_PARTIAL_RATIO:
        return TemporalCoverageClass.PARTIAL
    return TemporalCoverageClass.INSUFFICIENT


@dataclass(frozen=True)
class MonthCoverageInput:
    coverage_class: TemporalCoverageClass
    n_contributing_days: int
    n_calendar_days: int
    longest_gap_days: int = 0


def classify_seasonal(
    months: list[MonthCoverageInput],
    *,
    n_contributing_days: int,
    n_season_days: int,
    longest_gap_days: int,
) -> TemporalCoverageClass:
    if n_season_days <= 0:
        raise CoverageClaimError("seasonal claim cube is undefined")
    if not months:
        return TemporalCoverageClass.INSUFFICIENT
    if any(month.coverage_class is TemporalCoverageClass.INSUFFICIENT for month in months):
        return TemporalCoverageClass.INSUFFICIENT
    day_ratio = n_contributing_days / n_season_days
    if all(month.coverage_class is TemporalCoverageClass.FULL for month in months) and day_ratio == 1.0:
        return TemporalCoverageClass.FULL
    months_adequate = all(
        month.coverage_class in {TemporalCoverageClass.FULL, TemporalCoverageClass.ADEQUATE}
        and (month.n_calendar_days == 0 or month.n_contributing_days / month.n_calendar_days >= SEASONAL_ADEQUATE_DAY_RATIO)
        for month in months
    )
    if (
        months_adequate
        and day_ratio >= SEASONAL_ADEQUATE_DAY_RATIO
        and longest_gap_days <= SEASONAL_MAX_GAP_DAYS
    ):
        return TemporalCoverageClass.ADEQUATE
    usable = sum(
        1
        for month in months
        if month.coverage_class
        in {TemporalCoverageClass.FULL, TemporalCoverageClass.ADEQUATE, TemporalCoverageClass.PARTIAL}
    )
    if day_ratio >= SEASONAL_PARTIAL_DAY_RATIO and usable >= 2:
        return TemporalCoverageClass.PARTIAL
    return TemporalCoverageClass.INSUFFICIENT


def classify_year_pair(
    *,
    left: TemporalCoverageClass,
    right: TemporalCoverageClass,
    paired_ratio: float,
    coverage_delta: float,
) -> TemporalCoverageClass:
    rank = {
        TemporalCoverageClass.INSUFFICIENT: 0,
        TemporalCoverageClass.PARTIAL: 1,
        TemporalCoverageClass.ADEQUATE: 2,
        TemporalCoverageClass.FULL: 3,
    }
    if rank[left] < 1 or rank[right] < 1 or paired_ratio < YOY_PAIR_PARTIAL_RATIO:
        return TemporalCoverageClass.INSUFFICIENT
    if (
        rank[left] >= 3
        and rank[right] >= 3
        and paired_ratio >= 1.0
        and coverage_delta <= YOY_PAIR_FULL_DELTA
    ):
        return TemporalCoverageClass.FULL
    if (
        rank[left] >= 2
        and rank[right] >= 2
        and paired_ratio >= YOY_PAIR_ADEQUATE_RATIO
        and coverage_delta <= YOY_PAIR_ADEQUATE_DELTA
    ):
        return TemporalCoverageClass.ADEQUATE
    return TemporalCoverageClass.PARTIAL


def assert_not_signal_a_or_decision8_token(token: str) -> None:
    if token in SIGNAL_A_REFERENCE_TOKENS or token in DECISION8_TOKENS:
        raise ValueError(f"coverage class must not reuse {token}")


class CoverageTokenFamily(str, Enum):
    TEMPORAL = "temporal_completeness"
    SIGNAL_A = "signal_a_reference"
    DECISION8 = "decision8_spread"


def token_family(token: str) -> CoverageTokenFamily:
    if token in SIGNAL_A_REFERENCE_TOKENS:
        return CoverageTokenFamily.SIGNAL_A
    if token in DECISION8_TOKENS:
        return CoverageTokenFamily.DECISION8
    return CoverageTokenFamily.TEMPORAL
