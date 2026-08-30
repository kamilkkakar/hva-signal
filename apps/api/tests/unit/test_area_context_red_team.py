"""Claim red team: score-creep, 0/25 layers, missing=0, cooling, age, year-built, thermal."""

from __future__ import annotations

from app.domain.vulnerability_preparedness.claims import (
    ForbiddenClaimError,
    assert_claim_allowed,
    claim_violations,
)
from app.domain.vulnerability_preparedness.metrics import MetricKind
from app.services.vulnerability_preparedness.public_catalog import (
    QUANTITY_ONLY_KINDS,
    comparison_layer_allowed,
)
from app.services.vulnerability_preparedness.view_model import analysis_area_context_view
from tests.unit.test_vulnerability_preparedness_support import (
    ACS_AS_OF,
    ACS_SOURCE,
    ZONE_ID,
    cooling_preparedness,
    zone_context,
)
from app.domain.vulnerability_preparedness.metrics import DirectMetric


FORBIDDEN_PUBLIC = (
    "Vulnerability = 78",
    "High-risk population",
    "Low resilience score.",
    "no cooling site",
    "individual vulnerability",
    "homes have no AC",
)


def test_public_copy_rejects_score_and_risk_language() -> None:
    for text in FORBIDDEN_PUBLIC:
        assert claim_violations(text) or text.lower() in {
            token.lower() for token in FORBIDDEN_PUBLIC
        }
        try:
            assert_claim_allowed(text)
            raise AssertionError(f"expected rejection of {text!r}")
        except ForbiddenClaimError:
            pass


def test_zero_eligible_variables_are_not_comparison_layers() -> None:
    for kind in QUANTITY_ONLY_KINDS:
        assert comparison_layer_allowed(kind, 0) is False


def test_missing_metric_is_not_zero_filled() -> None:
    context = zone_context()
    assert context.energy is None
    assert context.metric_for(MetricKind.ENERGY_BURDEN_SHARE) is None
    view = analysis_area_context_view(
        context,
        cooling_preparedness(status="UNKNOWN"),
        {},
        {},
    )
    for fact in view.context_facts:
        if fact.quality_status.value == "MISSING":
            assert fact.value is None


def test_dataset_miss_is_not_world_absent() -> None:
    view = analysis_area_context_view(
        zone_context(),
        cooling_preparedness(status="NOT_IDENTIFIED_IN_DATASET"),
        {},
        {},
    )
    blob = " ".join(view.preparedness).lower()
    assert "no cooling site" not in blob
    assert "does not establish that no cooling resource exists" in blob
    assert claim_violations(" ".join(view.preparedness)) == []


def test_year_built_does_not_claim_no_ac() -> None:
    housing = DirectMetric(
        name="median year structure built",
        value=1974.0,
        unit="year",
        kind=MetricKind.MEDIAN_YEAR_BUILT,
        geography=ZONE_ID,
        source=ACS_SOURCE,
        as_of=ACS_AS_OF,
        moe=3.0,
    )
    context = zone_context()
    context = context.model_copy(update={"housing": housing})
    view = analysis_area_context_view(
        context,
        cooling_preparedness(status="UNKNOWN"),
        {MetricKind.MEDIAN_YEAR_BUILT: 1985.0},
        {MetricKind.MEDIAN_YEAR_BUILT: 25},
    )
    blob = " ".join([*[f.plain_language_sentence for f in view.context_facts], *view.uncertainty_notes]).lower()
    assert "no ac" not in blob
    assert "air conditioning is not observed" in blob
    year_fact = next(f for f in view.context_facts if f.kind is MetricKind.MEDIAN_YEAR_BUILT)
    assert "1974" in year_fact.plain_language_sentence


def test_age_is_composition_not_individual_vulnerability() -> None:
    from tests.unit.test_vulnerability_preparedness_support import age_65_plus_metric

    view = analysis_area_context_view(
        zone_context(age=age_65_plus_metric(value=0.31, moe=0.02)),
        cooling_preparedness(status="UNKNOWN"),
        {MetricKind.SHARE_AGE_65_PLUS: 0.18},
        {MetricKind.SHARE_AGE_65_PLUS: 6},
    )
    blob = " ".join([*[f.plain_language_sentence for f in view.context_facts], *view.uncertainty_notes]).lower()
    assert "high-risk" not in blob
    assert "tract composition share" in blob
    assert "not an individual vulnerability" in blob


def test_final_view_has_no_thermal_placeholder() -> None:
    view = analysis_area_context_view(
        zone_context(),
        cooling_preparedness(status="UNKNOWN"),
        {},
        {},
    )
    assert view.thermal_evidence_status == "UNKNOWN"
    text = view.story.as_text().lower()
    assert "referenced separately" not in text
    assert "warrants closer review" not in text
    assert view.story.thermal_evidence == []
