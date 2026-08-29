"""Phoenix v1 AreaConfig freeze and contract-defect tests. Decision 9 CLOSED."""

from __future__ import annotations

import inspect
import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.area_config import AreaConfig
from app.core.phoenix_v1_area_config import (
    phoenix_v1_area_config_candidate,
    serialize_phoenix_v1_area_config,
    validate_phoenix_v1_area_config,
)
from app.domain.aggregation import ThermalAggregationSpec, default_thermal_aggregation_spec
from app.domain.enums import (
    ReferenceEvidenceQuality,
    ReferenceFrame,
    TileAssignmentMethod,
    ZoneAggregationStatistic,
)
from app.domain.phoenix_v1 import (
    AREA_CONFIG_VERSION,
    FROZEN_STATUS,
    COVERAGE_POLICY_VERSION,
    DECISION8_POLICY_VERSION,
    EXPECTED_ZONE_COUNT,
    GRANULARITY_M,
    OBS_PER_YEAR,
    PARTITION_POLICY_VERSION,
    REFERENCE_HOUR_LOCAL,
    REFERENCE_SELF_INCLUSION,
    REFERENCE_STATISTIC,
    REFERENCE_VERSION,
    REFERENCE_YEARS,
    SEASONAL_WINDOW,
    THERMAL_AGGREGATION_VERSION,
    ZONE_DEFINITION_VERSION,
    ZONE_GEOMETRY_VERSION,
    assert_runtime_matches_frozen_reference,
    seasonal_window_length_days,
)
from app.domain.policies import (
    ConfidencePolicy,
    CoveragePolicy,
    HazardSpreadPolicy,
    HistoricalReferenceSpec,
    ModuleFlags,
    require_historical_percentile,
)
from app.services.coverage import evaluate_coverage
from app.services.temporal_anomaly import compute_q_a, midrank_ecdf

HACKATHON_ROOT = Path(__file__).resolve().parents[4]
CANDIDATE_PATH = HACKATHON_ROOT / "data" / "demo" / "phoenix" / "area_config.json"


def _generic_unfrozen(**overrides) -> dict:
    payload = {
        "area_id": "example-area",
        "version": "example-not-production",
        "zone_definition_version": "example-zone-def",
        "zone_type": "census_tract",
        "zone_source": "example-source",
        "zone_geometry_version": "example-geometry",
        "expected_zone_count": 2,
        "granularity_m": 100,
        "partition_strategy": "example_partition",
        "partition_policy_version": "example-partition-v1",
        "thermal_aggregation": default_thermal_aggregation_spec(
            version="example-agg",
            minimum_coverage_ratio=None,
        ),
        "default_hazard_reference_frame": ReferenceFrame.HISTORICAL,
        "historical_reference_window": HistoricalReferenceSpec(
            version="example-ref",
            percentile=None,
            seasonal_window="example-window",
        ),
        "coverage_policy": CoveragePolicy(version="example-cov", minimum_coverage_ratio=None),
        "confidence_policy": ConfidencePolicy(status="INACTIVE"),
        "hazard_spread_policy": HazardSpreadPolicy(
            version="example-spread",
            metric="between_zone_hazard_range",
            minimum_useful_spread=None,
        ),
        "intervention_catalog_version": None,
        "intervention_cost_profile": None,
        "intervention_lead_time_profile": None,
        "module_flags": ModuleFlags(),
        "gate0_status": "not_frozen",
    }
    payload.update(overrides)
    return payload


def test_percentile_none_is_valid_for_phoenix_v1() -> None:
    spec = HistoricalReferenceSpec(
        version=REFERENCE_VERSION,
        percentile=None,
        seasonal_window=SEASONAL_WINDOW,
        statistic=REFERENCE_STATISTIC,
    )
    assert spec.percentile is None
    candidate = phoenix_v1_area_config_candidate()
    assert candidate.historical_reference_window.percentile is None


def test_legacy_percentile_path_requires_numeric_value() -> None:
    missing = HistoricalReferenceSpec(version="legacy", seasonal_window="july", percentile=None)
    with pytest.raises(ValueError, match="legacy historical percentile"):
        require_historical_percentile(missing)
    present = HistoricalReferenceSpec(version="legacy", seasonal_window="july", percentile=97.0)
    assert require_historical_percentile(present) == pytest.approx(97.0)


def test_conflicting_coverage_floors_are_rejected() -> None:
    with pytest.raises(ValidationError, match="conflicting coverage floors"):
        AreaConfig.model_validate(
            _generic_unfrozen(
                thermal_aggregation=default_thermal_aggregation_spec(
                    version="example-agg",
                    minimum_coverage_ratio=0.5,
                ),
                coverage_policy=CoveragePolicy(version="example-cov", minimum_coverage_ratio=0.3),
            )
        )


def test_aggregation_cannot_set_independent_coverage_floor() -> None:
    with pytest.raises(ValidationError, match="cannot be set independently"):
        AreaConfig.model_validate(
            _generic_unfrozen(
                thermal_aggregation=default_thermal_aggregation_spec(
                    version="example-agg",
                    minimum_coverage_ratio=0.5,
                ),
                coverage_policy=CoveragePolicy(version="example-cov", minimum_coverage_ratio=None),
            )
        )


def test_coverage_policy_is_canonical_and_copied_onto_aggregation() -> None:
    config = AreaConfig.model_validate(
        _generic_unfrozen(
            thermal_aggregation=default_thermal_aggregation_spec(
                version="example-agg",
                minimum_coverage_ratio=None,
            ),
            coverage_policy=CoveragePolicy(version="example-cov", minimum_coverage_ratio=0.4),
        )
    )
    assert config.coverage_policy.minimum_coverage_ratio == pytest.approx(0.4)
    assert config.thermal_aggregation.minimum_coverage_ratio == pytest.approx(0.4)


def test_phoenix_coverage_has_no_numeric_ratio_floor() -> None:
    candidate = phoenix_v1_area_config_candidate()
    assert candidate.coverage_policy.version == COVERAGE_POLICY_VERSION
    assert candidate.coverage_policy.minimum_coverage_ratio is None
    assert candidate.thermal_aggregation.minimum_coverage_ratio is None
    low_ratio = evaluate_coverage(1, 10, None)
    assert low_ratio.ranked is True
    assert low_ratio.tile_coverage_ratio == pytest.approx(0.1)
    assert low_ratio.result_status == "ok"


def test_zero_tile_remains_insufficient_without_numeric_floor() -> None:
    result = evaluate_coverage(0, 10, None)
    assert result.ranked is False
    assert result.result_status == "insufficient_evidence"


def test_no_min_years_or_reduced_reference() -> None:
    assert "min_years" not in HistoricalReferenceSpec.model_fields
    assert "REDUCED_REFERENCE" not in ReferenceEvidenceQuality.__members__
    assert {member.value for member in ReferenceEvidenceQuality} == {
        "FULL_REFERENCE",
        "INSUFFICIENT_REFERENCE",
    }


def test_inactive_confidence_policy_rejects_fake_bands() -> None:
    with pytest.raises(ValidationError):
        ConfidencePolicy(
            status="INACTIVE",
            version="conf-v0",
            band_cutoffs={"high": 0.8, "medium": 0.5, "low": 0.0},
        )
    policy = ConfidencePolicy(status="INACTIVE")
    assert policy.version is None
    assert policy.band_cutoffs is None


def test_inactive_intervention_fields_are_null() -> None:
    candidate = phoenix_v1_area_config_candidate()
    assert candidate.intervention_catalog_version is None
    assert candidate.intervention_cost_profile is None
    assert candidate.intervention_lead_time_profile is None


def test_area_config_stamps_geometry_version_and_expected_zone_count() -> None:
    candidate = phoenix_v1_area_config_candidate()
    assert candidate.zone_geometry_version == ZONE_GEOMETRY_VERSION
    assert candidate.expected_zone_count == EXPECTED_ZONE_COUNT
    assert candidate.hazard_spread_policy.zone_geometry_version == candidate.zone_geometry_version
    assert candidate.hazard_spread_policy.expected_zone_count == candidate.expected_zone_count


def test_spread_geometry_mismatch_fails_validation() -> None:
    with pytest.raises(ValidationError, match="zone_geometry_version"):
        AreaConfig.model_validate(
            _generic_unfrozen(
                hazard_spread_policy=HazardSpreadPolicy(
                    version="example-spread",
                    metric="between_zone_hazard_range",
                    zone_geometry_version="other-geometry",
                )
            )
        )


def test_phoenix_v1_area_config_is_frozen() -> None:
    config = phoenix_v1_area_config_candidate()
    assert config.gate0_status == "frozen"
    on_disk = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    assert on_disk["gate0_status"] == "frozen"


def test_candidate_human_ratified_defaults() -> None:
    candidate = phoenix_v1_area_config_candidate()
    validate_phoenix_v1_area_config(candidate)
    assert candidate.thermal_aggregation.assignment_method == TileAssignmentMethod.CENTROID_WITHIN
    assert candidate.thermal_aggregation.statistic == ZoneAggregationStatistic.MEAN
    assert candidate.thermal_aggregation.zero_tile_behavior == "insufficient_evidence"
    assert candidate.thermal_aggregation.boundary_behavior == "centroid_within_zone"
    assert candidate.default_hazard_reference_frame == ReferenceFrame.HISTORICAL
    assert candidate.granularity_m == GRANULARITY_M
    assert candidate.partition_strategy == "single_aoi"
    assert candidate.partition_policy_version == PARTITION_POLICY_VERSION
    assert candidate.thermal_aggregation.version == THERMAL_AGGREGATION_VERSION
    assert candidate.version == AREA_CONFIG_VERSION
    assert candidate.gate0_status == "frozen"
    assert candidate.candidate_status == FROZEN_STATUS
    assert candidate.zone_definition_version == ZONE_DEFINITION_VERSION


def test_on_disk_candidate_matches_factory() -> None:
    assert CANDIDATE_PATH.is_file()
    candidate = phoenix_v1_area_config_candidate()
    on_disk = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    assert on_disk == json.loads(serialize_phoenix_v1_area_config(candidate))
    loaded = AreaConfig.model_validate(on_disk)
    validate_phoenix_v1_area_config(loaded)


def test_decision1b_runtime_matches_frozen_reference_contract() -> None:
    assert_runtime_matches_frozen_reference()
    assert REFERENCE_YEARS == (2022, 2023, 2024)
    assert SEASONAL_WINDOW == "06-30 through 07-30 inclusive"
    assert seasonal_window_length_days() == 31
    assert OBS_PER_YEAR == 31
    start = date(2022, 6, 30)
    days = [(start + timedelta(days=i)).strftime("%m-%d") for i in range(31)]
    assert days[0] == "06-30"
    assert days[-1] == "07-30"
    assert REFERENCE_HOUR_LOCAL == "03:00"
    assert REFERENCE_SELF_INCLUSION == "EXCLUDE_TARGET_TIMESTAMP"
    assert REFERENCE_STATISTIC == "YEAR_BALANCED_OWN_TRACT_MIDRANK_ECDF"
    source = inspect.getsource(compute_q_a)
    assert "if row.date == target_date" in source
    assert "continue" in source
    assert "/ float(len(years))" in source
    assert "row.geoid == geoid" in source
    assert inspect.getsource(midrank_ecdf)
    assert "0.5 * n_eq" in inspect.getsource(midrank_ecdf)
    candidate = phoenix_v1_area_config_candidate()
    assert candidate.historical_reference_window.version == REFERENCE_VERSION
    assert "GRANULARITY_100M" in REFERENCE_VERSION
    assert candidate.granularity_m == 100
    assert "REDUCED_REFERENCE" not in ReferenceEvidenceQuality.__members__


def test_decision8_candidate_dependencies() -> None:
    candidate = phoenix_v1_area_config_candidate()
    spread = candidate.hazard_spread_policy
    assert spread.version == DECISION8_POLICY_VERSION
    assert spread.input_quantity == "q_A"
    assert spread.metric == "TOP3_BOTTOM3_MEAN_DIFFERENCE"
    assert spread.top_group_size == 3
    assert spread.bottom_group_size == 3
    assert spread.minimum_useful_spread == pytest.approx(0.10)
    assert spread.comparison_operator == ">="
    assert spread.expected_zone_count == 25
    assert spread.reference_version == REFERENCE_VERSION
    assert spread.zone_geometry_version == ZONE_GEOMETRY_VERSION
    assert spread.metric != "between_zone_hazard_range"


def test_unknown_module_flags_cannot_activate_silently() -> None:
    with pytest.raises(ValidationError):
        ModuleFlags.model_validate({"intervention_evidence": False, "extra_module": True})


def test_granularity_field_documents_acquisition_not_localization() -> None:
    description = AreaConfig.model_fields["granularity_m"].description or ""
    assert "acquisition" in description.lower() or "request" in description.lower()
    assert "localization" in description.lower()
    assert "NOT ESTABLISHED" in description
