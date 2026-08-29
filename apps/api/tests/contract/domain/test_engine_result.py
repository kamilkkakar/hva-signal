"""Contract cluster 6: generic EngineResult[T] and Confidence."""

import pytest
from pydantic import ValidationError

from app.domain import Confidence, EngineResult, ResultStatus


def test_confidence_field_names() -> None:
    assert set(Confidence.model_fields) == {"score", "band"}


def test_confidence_score_is_0_to_1() -> None:
    Confidence(score=0.0, band="low")
    Confidence(score=1.0, band="high")
    with pytest.raises(ValidationError):
        Confidence(score=-0.01, band="low")
    with pytest.raises(ValidationError):
        Confidence(score=1.01, band="high")


def test_engine_result_field_names() -> None:
    assert set(EngineResult.model_fields) == {
        "status",
        "value",
        "confidence",
        "confidence_reasons",
        "evidence_refs",
        "quality_flags",
        "model_version",
    }


def test_engine_result_is_generic_over_value() -> None:
    ok = EngineResult[float](
        status=ResultStatus.OK,
        value=0.42,
        confidence=Confidence(score=0.8, band="high"),
        confidence_reasons=["coverage_ok"],
        evidence_refs=["ev-1"],
        quality_flags=[],
        model_version="prob-v0",
    )
    assert ok.value == pytest.approx(0.42)
    assert ok.status == ResultStatus.OK

    missing = EngineResult[float](
        status=ResultStatus.INSUFFICIENT_EVIDENCE,
        value=None,
        confidence=Confidence(score=0.0, band="none"),
        model_version="prob-v0",
    )
    assert missing.value is None
    assert missing.status == ResultStatus.INSUFFICIENT_EVIDENCE
