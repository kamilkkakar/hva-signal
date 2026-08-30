from __future__ import annotations

from app.domain.enums import ReferenceEvidenceQuality
from app.domain.temporal import SamplingDesign, TemporalCoverageClass
from app.services.temporal_coverage import (
    COVERAGE_POLICY_ID,
    DAILY_HOURLY_24_ADEQUATE_MIN,
    classify_daily_hourly_24,
    classify_for_design,
    classify_spatial,
    classify_year_pair,
    token_family,
)


def test_candidate_constants_are_commented_policy() -> None:
    assert COVERAGE_POLICY_ID.endswith("CANDIDATE")
    assert DAILY_HOURLY_24_ADEQUATE_MIN == 18


def test_hourly_24_classes() -> None:
    assert classify_daily_hourly_24(0) is TemporalCoverageClass.INSUFFICIENT
    assert classify_daily_hourly_24(24, present_hours=set(range(24))) is TemporalCoverageClass.FULL
    unbalanced = set(range(0, 12)) | set(range(18, 24))
    assert classify_daily_hourly_24(18, present_hours=unbalanced) is TemporalCoverageClass.PARTIAL
    almost = set(range(24)) - {15, 16}
    assert classify_daily_hourly_24(22, present_hours=almost) is TemporalCoverageClass.ADEQUATE


def test_anchor_full_is_not_hourly_full() -> None:
    assert classify_for_design(SamplingDesign.ANCHOR_0300, n_present=1, n_expected=1) is TemporalCoverageClass.FULL
    assert (
        classify_for_design(SamplingDesign.HOURLY_24, n_present=1, n_expected=24, present_hours={3})
        is TemporalCoverageClass.PARTIAL
    )


def test_spatial_cuts() -> None:
    assert classify_spatial(25) is TemporalCoverageClass.FULL
    assert classify_spatial(20) is TemporalCoverageClass.ADEQUATE
    assert classify_spatial(13) is TemporalCoverageClass.PARTIAL
    assert classify_spatial(0) is TemporalCoverageClass.INSUFFICIENT


def test_yoy_pair_delta_coverage() -> None:
    pair = classify_year_pair(
        left=TemporalCoverageClass.ADEQUATE,
        right=TemporalCoverageClass.FULL,
        paired_ratio=0.82,
        coverage_delta=0.17,
    )
    assert pair is TemporalCoverageClass.PARTIAL


def test_signal_a_stays_binary() -> None:
    assert ReferenceEvidenceQuality.FULL_REFERENCE.value == "FULL_REFERENCE"
    assert token_family("FULL_REFERENCE").value == "signal_a_reference"
    assert token_family("FULL").value == "temporal_completeness"
