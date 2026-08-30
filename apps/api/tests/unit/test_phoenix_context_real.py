"""Real 25-zone Phoenix context: MOE reselection, no combined score, cache only."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.vulnerability_preparedness.claims import claim_violations
from app.domain.vulnerability_preparedness.combination import (
    CombinedIndexUnauthorized,
    compute_combined_index,
)
from app.domain.vulnerability_preparedness.metrics import (
    UNCERTAIN_COMPARISON_SENTENCE,
    MetricAvailability,
    MetricKind,
    moe_allows_publication,
)
from app.domain.vulnerability_preparedness.preparedness import ResourceIdentificationStatus
from app.services.vulnerability_preparedness.acs_ingest import share_and_moe
from app.services.vulnerability_preparedness.cache import (
    AREA_ID,
    EXPECTED_ZONE_COUNT,
    load_context_bundle,
)
from app.services.vulnerability_preparedness.load import (
    intersection_for_zone,
    load_phoenix_context_area,
    map_feature_properties,
    side_by_side_for_zone,
)
from app.services.vulnerability_preparedness.paths import context_bundle_path
from app.services.vulnerability_preparedness.public_catalog import (
    COMPARISON_CAPABLE_KINDS,
    MAP_LAYER_KINDS,
    PRIMARY_FACT_KINDS,
    QUANTITY_ONLY_KINDS,
)
from app.services.vulnerability_preparedness.purity import assert_package_purity
from app.services.vulnerability_preparedness.view_model import PUBLIC_CANDIDATE_KINDS

BUNDLE = context_bundle_path()


@pytest.fixture(scope="module")
def bundle() -> dict:
    if not BUNDLE.is_file():
        pytest.skip("Phoenix context bundle not ingested")
    return load_context_bundle()


@pytest.fixture(scope="module")
def area(bundle: dict):
    return load_phoenix_context_area(bundle=bundle)


def test_bundle_covers_twenty_five_analysis_zones(bundle: dict) -> None:
    zones = bundle["join_audit"]["zone_geoids"]
    assert len(zones) == EXPECTED_ZONE_COUNT
    assert len(set(zones)) == EXPECTED_ZONE_COUNT


def test_acs_join_key_is_tract_geoid_and_coverage_is_complete(bundle: dict, area) -> None:
    assert "1400000US" in bundle["join_key"]["acs"]
    assert area.join_audit.acs_coverage_complete
    assert set(area.join_audit.acs_matched) == set(area.zone_ids)


def test_living_alone_65_uses_2024_alone_lines(bundle: dict, area) -> None:
    geo_id = "1400000US04013107401"
    row = bundle["acs"]["B09020"]["rows"][geo_id]
    total = float(row["B09020_E001"])
    alone = float(row["B09020_E015"]) + float(row["B09020_E018"])
    expected = alone / total
    metric = area.contexts["04013107401"].isolation
    assert metric is not None
    assert metric.value == pytest.approx(expected)
    assert metric.value != pytest.approx(float(row["B09020_E011"]) / total)


def test_public_primary_facts_are_comparison_capable_and_capped(area) -> None:
    assert PUBLIC_CANDIDATE_KINDS == PRIMARY_FACT_KINDS
    assert len(PRIMARY_FACT_KINDS) <= 6
    view = area.views[area.zone_ids[0]]
    assert len(view.context_facts) <= 6
    assert all(fact.kind in COMPARISON_CAPABLE_KINDS for fact in view.context_facts)


def test_zero_of_twenty_five_kinds_are_quantity_only(area) -> None:
    by_kind = {row.kind: row for row in area.metric_quality}
    for kind in QUANTITY_ONLY_KINDS:
        row = by_kind[kind]
        assert row.comparison_eligible_count == 0
        assert row.quantity_only is True
        assert row.comparison_layer_allowed is False


def test_comparison_layers_exclude_zero_eligible_and_age(area) -> None:
    by_kind = {row.kind: row for row in area.metric_quality}
    assert by_kind[MetricKind.SHARE_AGE_65_PLUS].comparison_layer_allowed is False
    assert by_kind[MetricKind.CANOPY_COVER_SHARE].comparison_eligible_count == 25
    assert by_kind[MetricKind.MEDIAN_HOUSEHOLD_INCOME].comparison_eligible_count == 21
    assert by_kind[MetricKind.SHARE_PRE_1980_HOUSING].comparison_eligible_count == 19
    assert set(MAP_LAYER_KINDS) == {
        MetricKind.CANOPY_COVER_SHARE,
        MetricKind.MEDIAN_HOUSEHOLD_INCOME,
        MetricKind.SHARE_PRE_1980_HOUSING,
    }


def test_high_moe_quantity_is_shown_and_comparison_is_qualified(area) -> None:
    qualified = 0
    for view in area.views.values():
        blob = " ".join(view.uncertainty_notes)
        if UNCERTAIN_COMPARISON_SENTENCE.lower() in blob.lower():
            qualified += 1
        for fact in view.context_facts:
            if fact.quality_status is MetricAvailability.MOE_UNRELIABLE:
                assert fact.comparison_allowed is False
                assert UNCERTAIN_COMPARISON_SENTENCE in fact.plain_language_sentence
                assert fact.value is not None
    assert qualified >= 1


def test_map_properties_omit_zero_eligible_variables(area) -> None:
    props = map_feature_properties(area)
    assert len(props) == EXPECTED_ZONE_COUNT
    for row in props:
        assert "share_under_5" not in row
        assert "poverty_rate" not in row
        assert "share_no_vehicle" not in row
        assert "share_65_plus_living_alone_persons" not in row
        assert "share_age_65_plus" not in row
        assert row["combined_score_authorized"] is False
        if row["median_household_income"] is None:
            assert row["income_comparison_allowed"] is False


def test_cooling_language_never_says_no_cooling_site(area) -> None:
    for view in area.views.values():
        blob = " ".join(
            [
                *view.preparedness,
                view.story.as_text(),
                *view.direction,
            ]
        ).lower()
        assert "no cooling site" not in blob
        assert "no cooling center" not in blob
        if view.map_properties.cooling_site_status is (
            ResourceIdentificationStatus.NOT_IDENTIFIED_IN_DATASET
        ):
            assert "no site was identified in this dataset" in blob
            assert "does not establish that no cooling resource exists" in blob


def test_sectioned_story_has_four_sections_and_no_thermal_placeholder(area) -> None:
    view = next(iter(area.views.values()))
    text = view.story.as_text()
    assert text.startswith("THERMAL EVIDENCE")
    assert "\nCONTEXT\n" in text
    assert "\nPREPAREDNESS\n" in text
    assert "\nDIRECTION\n" in text
    assert view.thermal_evidence_status == "UNKNOWN"
    assert "referenced separately" not in text.lower()
    assert "warrants closer review" not in text.lower()
    assert "Review cooling access and local response capacity" in text


def test_no_combined_score_or_placeholder_thermal(area) -> None:
    dumped = area.model_dump(mode="json")
    assert area.combined_score_authorized is False
    assert area.vulnerability_score_authorized is False
    assert area.thermal_evidence_status == "UNKNOWN"
    assert "vulnerability_score" not in str(dumped).lower() or (
        "vulnerability_score_authorized" in str(dumped)
    )
    for view in area.views.values():
        assert view.combined_score_authorized is False
        assert view.vulnerability_score_authorized is False
        assert claim_violations(view.story.as_text()) == []


def test_compute_combined_index_still_unauthorized(area) -> None:
    with pytest.raises(CombinedIndexUnauthorized):
        compute_combined_index(area.contexts[area.zone_ids[0]])


def test_intersection_does_not_invent_thermal_sentence(area) -> None:
    intersection = intersection_for_zone(area, area.zone_ids[0])
    assert intersection.thermal_ref.thermal_sentence is None
    assert intersection.combined_score_authorized is False


def test_side_by_side_uses_real_values(area) -> None:
    zone_id = area.zone_ids[0]
    layers = side_by_side_for_zone(area, zone_id)
    assert layers.combined_score_authorized is False
    assert layers.context.zone_id == zone_id


def test_canopy_source_is_real_phoenix_shade_study(bundle: dict, area) -> None:
    source = bundle["sources"]["canopy"]
    assert "Office of Heat Response" in source["name"]
    assert source["imagery_year"] == 2022
    sample = next(
        ctx.canopy
        for ctx in area.contexts.values()
        if ctx.canopy and ctx.canopy.is_publishable()
    )
    assert sample.kind is MetricKind.CANOPY_COVER_SHARE
    fact = next(
        fact
        for view in area.views.values()
        for fact in view.context_facts
        if fact.kind is MetricKind.CANOPY_COVER_SHARE
    )
    assert "plantable ground" in fact.plain_language_sentence


def test_runtime_cache_is_local_file_not_live_api() -> None:
    assert BUNDLE.is_file()
    source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "vulnerability_preparedness"
        / "cache.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "api.census.gov" not in text
    assert "urlopen" not in text
    assert "httpx" not in text
    route = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "api"
        / "routes"
        / "area_context.py"
    )
    route_text = route.read_text(encoding="utf-8")
    assert "ingest_phoenix_context" not in route_text
    assert "api.census.gov" not in route_text


def test_high_moe_gate_still_fails_closed() -> None:
    assert moe_allows_publication(0.20, 0.10) is False
    share, moe = share_and_moe(20.0, 100.0, 40.0, 5.0)
    assert share == pytest.approx(0.20)
    assert moe is not None
    assert moe_allows_publication(share, moe) is False


def test_energy_burden_is_not_invented(area) -> None:
    for context in area.contexts.values():
        assert context.energy is None


def test_new_modules_stay_vendor_pure() -> None:
    assert_package_purity()


def test_area_identity(area) -> None:
    assert area.area_id == AREA_ID
    assert "25-area" in area.area_label
