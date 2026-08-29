"""Contract cluster 8: AreaConfig schema (values remain unfrozen)."""

import app.core.area_config as area_config_module
from app.core.area_config import AreaConfig
from app.core.versioning import ANALYSIS_SCHEMA_VERSION, stamp_analysis_versions
from app.domain import (
    ConfidencePolicy,
    CoveragePolicy,
    HazardSpreadPolicy,
    HistoricalReferenceSpec,
    ModuleFlags,
    ReferenceFrame,
    default_thermal_aggregation_spec,
)


def test_area_config_field_names() -> None:
    assert set(AreaConfig.model_fields) >= {
        "area_id",
        "version",
        "zone_definition_version",
        "zone_type",
        "zone_source",
        "zone_geometry_version",
        "expected_zone_count",
        "granularity_m",
        "partition_strategy",
        "partition_policy_version",
        "thermal_aggregation",
        "default_hazard_reference_frame",
        "historical_reference_window",
        "coverage_policy",
        "confidence_policy",
        "hazard_spread_policy",
        "intervention_catalog_version",
        "intervention_cost_profile",
        "intervention_lead_time_profile",
        "module_flags",
        "gate0_status",
        "candidate_status",
    }


def test_gate0_status_defaults_to_not_frozen() -> None:
    assert AreaConfig.model_fields["gate0_status"].default == "not_frozen"


def test_no_module_level_areaconfig_instance() -> None:
    instances = [
        value for value in vars(area_config_module).values() if isinstance(value, AreaConfig)
    ]
    assert instances == []


def test_example_areaconfig_dict_is_not_frozen() -> None:
    example = {
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
            behavior_below_floor="surface_system_limitation",
        ),
        "intervention_catalog_version": None,
        "intervention_cost_profile": None,
        "intervention_lead_time_profile": None,
        "module_flags": ModuleFlags(
            intervention_evidence=False,
            human_thermal_burden=False,
            overnight_recovery=False,
        ),
        "gate0_status": "not_frozen",
    }
    config = AreaConfig.model_validate(example)
    assert config.gate0_status == "not_frozen"
    assert config.hazard_spread_policy.minimum_useful_spread is None
    assert config.default_hazard_reference_frame == ReferenceFrame.HISTORICAL
    assert config.thermal_aggregation.assignment_method == "centroid_within"
    assert config.thermal_aggregation.statistic == "mean"
    assert config.historical_reference_window.percentile is None
    assert config.confidence_policy.status == "INACTIVE"


def test_hazard_spread_minimum_useful_spread_may_be_none_while_unfrozen() -> None:
    policy = HazardSpreadPolicy(
        version="spread-v0",
        metric="between_zone_hazard_range",
        minimum_useful_spread=None,
        behavior_below_floor="surface_system_limitation",
    )
    assert policy.minimum_useful_spread is None


def test_versioning_helper_stamps_architecture_schema() -> None:
    versions = stamp_analysis_versions(
        area_config_version="unfrozen",
        zone_definition_version="unfrozen",
        zone_geometry_version="unfrozen",
        thermal_aggregation_version="agg-v0",
        normalization_registry_version="norm-v0",
        hazard_spread_policy_version="spread-v0",
        probability_model_version="prob-v0",
        consequence_model_version="cons-v0",
        protection_model_version="prot-v0",
        priority_model_version="prio-v0",
        intervention_catalog_version="catalog-v0",
        context_dataset_version="ctx-v0",
        fortyguard_adapter_version="fg-v0",
    )
    assert versions.analysis_schema_version == ANALYSIS_SCHEMA_VERSION
    assert ANALYSIS_SCHEMA_VERSION == "0.4"
    assert versions.build_commit_sha is None
    assert versions.intervention_evidence_model_version is None
