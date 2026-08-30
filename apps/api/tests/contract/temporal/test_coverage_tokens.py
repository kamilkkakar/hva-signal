from app.services.temporal_coverage import (
    COVERAGE_POLICY_ID,
    CoverageTokenFamily,
    token_family,
)


def test_coverage_policy_is_candidate() -> None:
    assert COVERAGE_POLICY_ID == "PHX_TEMPORAL_COVERAGE_POLICY_V1_CANDIDATE"
    assert "CANDIDATE" in COVERAGE_POLICY_ID


def test_tokens_isolated_from_signal_a_and_decision8() -> None:
    assert token_family("FULL") is CoverageTokenFamily.TEMPORAL
    assert token_family("ADEQUATE") is CoverageTokenFamily.TEMPORAL
    assert token_family("FULL_REFERENCE") is CoverageTokenFamily.SIGNAL_A
    assert token_family("INSUFFICIENT_REFERENCE") is CoverageTokenFamily.SIGNAL_A
    assert token_family("INSUFFICIENT_EVIDENCE") is CoverageTokenFamily.DECISION8
