"""AnalysisAreaContextView: primary facts, MOE UX, no thermal placeholder."""

from __future__ import annotations

from app.domain.vulnerability_preparedness.metrics import (
    UNCERTAIN_COMPARISON_SENTENCE,
    MedianComparison,
    MetricAvailability,
    MetricKind,
)
from app.services.vulnerability_preparedness.view_model import (
    DIRECTION_SENTENCE,
    analysis_area_context_view,
    cope_characteristics,
)
from tests.unit.test_vulnerability_preparedness_support import (
    ACS_AS_OF,
    ACS_SOURCE,
    ZONE_ID,
    age_65_plus_metric,
    cooling_preparedness,
    zone_context,
)
from app.domain.vulnerability_preparedness.metrics import DirectMetric


def _canopy(value: float = 0.15) -> DirectMetric:
    return DirectMetric(
        name="tree canopy cover",
        value=value,
        unit="share",
        kind=MetricKind.CANOPY_COVER_SHARE,
        geography=ZONE_ID,
        source=ACS_SOURCE,
        as_of=ACS_AS_OF,
        moe=None,
    )


def _income(value: float = 52000.0, moe: float | None = 2000.0) -> DirectMetric:
    return DirectMetric(
        name="median household income",
        value=value,
        unit="usd",
        kind=MetricKind.MEDIAN_HOUSEHOLD_INCOME,
        geography=ZONE_ID,
        source=ACS_SOURCE,
        as_of=ACS_AS_OF,
        moe=moe,
    )


def test_view_answers_coping_and_verify_questions_not_score() -> None:
    context = zone_context(
        age=age_65_plus_metric(value=0.30, moe=0.02),
        canopy=_canopy(0.10),
    )
    context = context.model_copy(
        update={"additional_metrics": [_income(40000.0)]}
    )
    counts = {
        MetricKind.CANOPY_COVER_SHARE: 25,
        MetricKind.MEDIAN_HOUSEHOLD_INCOME: 21,
        MetricKind.SHARE_PRE_1980_HOUSING: 19,
        MetricKind.SHARE_ONE_PERSON_HOUSEHOLD: 15,
        MetricKind.MEDIAN_YEAR_BUILT: 25,
        MetricKind.SHARE_AGE_65_PLUS: 6,
    }
    medians = {
        MetricKind.CANOPY_COVER_SHARE: 0.20,
        MetricKind.MEDIAN_HOUSEHOLD_INCOME: 60000.0,
        MetricKind.SHARE_AGE_65_PLUS: 0.18,
    }
    view = analysis_area_context_view(
        context,
        cooling_preparedness(status="NOT_IDENTIFIED_IN_DATASET"),
        medians,
        counts,
    )
    assert view.census_tract_geoid == ZONE_ID
    assert view.vulnerability_score_authorized is False
    assert view.thermal_evidence_status == "UNKNOWN"
    assert view.context_facts
    assert any("65+" in fact.plain_language_sentence for fact in view.context_facts)
    assert any("plantable ground" in fact.plain_language_sentence for fact in view.context_facts)
    assert DIRECTION_SENTENCE in view.direction
    assert any("confirm" in item.lower() for item in view.verify_before_action)
    assert view.cope_characteristics
    assert "referenced separately" not in view.story.as_text().lower()
    assert "warrants closer review" not in view.story.as_text().lower()


def test_unreliable_moe_shows_quantity_without_higher_lower() -> None:
    income = _income(value=40000.0, moe=30000.0)
    assert income.availability is MetricAvailability.MOE_UNRELIABLE
    context = zone_context(canopy=_canopy(0.12))
    context = context.model_copy(update={"additional_metrics": [income]})
    view = analysis_area_context_view(
        context,
        cooling_preparedness(status="UNKNOWN"),
        {MetricKind.CANOPY_COVER_SHARE: 0.20, MetricKind.MEDIAN_HOUSEHOLD_INCOME: 60000.0},
        {
            MetricKind.CANOPY_COVER_SHARE: 25,
            MetricKind.MEDIAN_HOUSEHOLD_INCOME: 21,
        },
    )
    income_fact = next(
        fact
        for fact in view.context_facts
        if fact.kind is MetricKind.MEDIAN_HOUSEHOLD_INCOME
    )
    assert income_fact.comparison_allowed is False
    assert income_fact.comparison is MedianComparison.UNKNOWN
    assert "40,000" in income_fact.plain_language_sentence or "40000" in income_fact.plain_language_sentence.replace(",", "")
    assert UNCERTAIN_COMPARISON_SENTENCE in income_fact.plain_language_sentence
    assert "higher" not in income_fact.plain_language_sentence.lower()
    assert "lower" not in income_fact.plain_language_sentence.lower()
    assert view.map_properties.median_household_income is None


def test_unreliable_age_is_omitted_from_primary_facts() -> None:
    age = age_65_plus_metric(value=0.30, moe=0.20)
    assert age.availability is MetricAvailability.MOE_UNRELIABLE
    view = analysis_area_context_view(
        zone_context(age=age, canopy=_canopy()),
        cooling_preparedness(status="IDENTIFIED"),
        {MetricKind.CANOPY_COVER_SHARE: 0.20, MetricKind.SHARE_AGE_65_PLUS: 0.18},
        {MetricKind.CANOPY_COVER_SHARE: 25, MetricKind.SHARE_AGE_65_PLUS: 6},
    )
    assert all(fact.kind is not MetricKind.SHARE_AGE_65_PLUS for fact in view.context_facts)
    assert any(UNCERTAIN_COMPARISON_SENTENCE in note for note in view.uncertainty_notes)


def test_thermal_intersection_only_when_supported() -> None:
    facts_view = analysis_area_context_view(
        zone_context(canopy=_canopy(0.10)),
        cooling_preparedness(status="UNKNOWN"),
        {MetricKind.CANOPY_COVER_SHARE: 0.20},
        {MetricKind.CANOPY_COVER_SHARE: 25},
        thermal_sentence="Thermal evidence warrants closer review.",
    )
    assert facts_view.thermal_evidence_status == "AVAILABLE"
    assert any("warrants closer review" in line for line in facts_view.cope_characteristics)

    empty = cope_characteristics([], thermal_status="UNKNOWN", thermal_sentence=None)
    assert empty == []


def test_identified_cooling_uses_heat_relief_language() -> None:
    view = analysis_area_context_view(
        zone_context(canopy=_canopy()),
        cooling_preparedness(status="IDENTIFIED"),
        {MetricKind.CANOPY_COVER_SHARE: 0.15},
        {MetricKind.CANOPY_COVER_SHARE: 25},
    )
    blob = " ".join(view.preparedness).lower()
    assert "heat-relief site" in blob
    assert "no cooling site" not in blob
