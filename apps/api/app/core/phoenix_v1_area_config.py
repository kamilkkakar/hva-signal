"""Phoenix v1 AreaConfig factory. Decision 9 CLOSED. Gate 0 remains open."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.core.area_config import AreaConfig
from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import (
    ReferenceFrame,
    TileAssignmentMethod,
    ZoneAggregationStatistic,
)
from app.domain.phoenix_v1 import (
    AREA_CONFIG_VERSION,
    AREA_ID,
    FROZEN_AREA_CONFIG_SHA256,
    FROZEN_COMMENT,
    FROZEN_STATUS,
    COVERAGE_POLICY_VERSION,
    DECISION8_POLICY_VERSION,
    EXPECTED_ZONE_COUNT,
    GRANULARITY_M,
    INPUT_QUANTITY,
    METRIC_TOP3_BOTTOM3,
    PARTITION_POLICY_VERSION,
    PARTITION_STRATEGY,
    REFERENCE_STATISTIC,
    REFERENCE_VERSION,
    SEASONAL_WINDOW,
    SPREAD_FLOOR,
    THERMAL_AGGREGATION_VERSION,
    TOP_GROUP_SIZE,
    BOTTOM_GROUP_SIZE,
    COMPARISON_OPERATOR,
    ZONE_DEFINITION_VERSION,
    ZONE_GEOMETRY_VERSION,
    ZONE_SOURCE,
    ZONE_TYPE,
    assert_runtime_matches_frozen_reference,
    decision8_policy_fixture,
)
from app.domain.policies import (
    ConfidencePolicy,
    CoveragePolicy,
    HistoricalReferenceSpec,
    ModuleFlags,
)


def phoenix_v1_area_config_candidate() -> AreaConfig:
    """Phoenix v1 AreaConfig. HUMAN-FROZEN. Decision 9 CLOSED."""
    return AreaConfig(
        schema_comment=FROZEN_COMMENT,
        candidate_status=FROZEN_STATUS,
        area_id=AREA_ID,
        version=AREA_CONFIG_VERSION,
        zone_definition_version=ZONE_DEFINITION_VERSION,
        zone_type=ZONE_TYPE,
        zone_source=ZONE_SOURCE,
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        expected_zone_count=EXPECTED_ZONE_COUNT,
        granularity_m=GRANULARITY_M,
        partition_strategy=PARTITION_STRATEGY,
        partition_policy_version=PARTITION_POLICY_VERSION,
        thermal_aggregation=ThermalAggregationSpec(
            version=THERMAL_AGGREGATION_VERSION,
            assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
            statistic=ZoneAggregationStatistic.MEAN,
            minimum_coverage_ratio=None,
            zero_tile_behavior="insufficient_evidence",
            boundary_behavior="centroid_within_zone",
            notes=[
                "Applies to raw TCM °C before q_A.",
                "Arithmetic mean of valid assigned tile temperatures; missing "
                "temperatures omitted, never coerced to zero.",
            ],
        ),
        default_hazard_reference_frame=ReferenceFrame.HISTORICAL,
        historical_reference_window=HistoricalReferenceSpec(
            version=REFERENCE_VERSION,
            percentile=None,
            seasonal_window=SEASONAL_WINDOW,
            statistic=REFERENCE_STATISTIC,
        ),
        coverage_policy=CoveragePolicy(
            version=COVERAGE_POLICY_VERSION,
            minimum_coverage_ratio=None,
        ),
        confidence_policy=ConfidencePolicy(status="INACTIVE"),
        hazard_spread_policy=decision8_policy_fixture(),
        intervention_catalog_version=None,
        intervention_cost_profile=None,
        intervention_lead_time_profile=None,
        module_flags=ModuleFlags(
            intervention_evidence=False,
            human_thermal_burden=False,
            overnight_recovery=False,
        ),
        gate0_status="frozen",
    )


def validate_phoenix_v1_area_config(config: AreaConfig) -> None:
    """Fail if the Phoenix v1 candidate disagrees with frozen Decision 1B/8 contracts."""
    if config.version != AREA_CONFIG_VERSION:
        raise ValueError(f"unexpected AreaConfig.version: {config.version}")
    if config.area_id != AREA_ID:
        raise ValueError(f"unexpected area_id: {config.area_id}")
    if config.gate0_status != "frozen":
        raise ValueError("Phoenix v1 AreaConfig must have gate0_status=frozen")
    if config.candidate_status != FROZEN_STATUS:
        raise ValueError("Phoenix v1 AreaConfig must be marked HUMAN-FROZEN")
    if config.zone_type != ZONE_TYPE:
        raise ValueError("zone_type must be census_tract")
    if config.zone_definition_version != ZONE_DEFINITION_VERSION:
        raise ValueError("zone_definition_version mismatch")
    if config.zone_geometry_version != ZONE_GEOMETRY_VERSION:
        raise ValueError("zone_geometry_version mismatch")
    if config.expected_zone_count != EXPECTED_ZONE_COUNT:
        raise ValueError("expected_zone_count must be 25")
    if config.granularity_m != GRANULARITY_M:
        raise ValueError("granularity_m must be 100")
    if config.partition_strategy != PARTITION_STRATEGY:
        raise ValueError("partition_strategy must be single_aoi")
    if config.partition_policy_version != PARTITION_POLICY_VERSION:
        raise ValueError("partition_policy_version mismatch")
    agg = config.thermal_aggregation
    if agg.version != THERMAL_AGGREGATION_VERSION:
        raise ValueError("thermal aggregation version mismatch")
    if agg.assignment_method != TileAssignmentMethod.CENTROID_WITHIN:
        raise ValueError("assignment_method must be centroid_within")
    if agg.statistic != ZoneAggregationStatistic.MEAN:
        raise ValueError("statistic must be mean")
    if agg.zero_tile_behavior != "insufficient_evidence":
        raise ValueError("zero_tile_behavior mismatch")
    if agg.boundary_behavior != "centroid_within_zone":
        raise ValueError("boundary_behavior mismatch")
    if agg.minimum_coverage_ratio is not None:
        raise ValueError("Phoenix v1 aggregation must not carry a numeric coverage floor")
    if config.coverage_policy.version != COVERAGE_POLICY_VERSION:
        raise ValueError("coverage policy version mismatch")
    if config.coverage_policy.minimum_coverage_ratio is not None:
        raise ValueError("Phoenix v1 numeric coverage floor must not be operationalized")
    if config.default_hazard_reference_frame != ReferenceFrame.HISTORICAL:
        raise ValueError("default_hazard_reference_frame must be historical")
    hist = config.historical_reference_window
    if hist.version != REFERENCE_VERSION:
        raise ValueError("historical_reference_window.version mismatch")
    if hist.seasonal_window != SEASONAL_WINDOW:
        raise ValueError("seasonal_window mismatch")
    if hist.statistic != REFERENCE_STATISTIC:
        raise ValueError("reference statistic mismatch")
    if hist.percentile is not None:
        raise ValueError("Phoenix v1 percentile must be NOT_APPLICABLE (None)")
    if "min_years" in HistoricalReferenceSpec.model_fields:
        raise ValueError("min_years must not exist on HistoricalReferenceSpec")
    if config.confidence_policy.status != "INACTIVE":
        raise ValueError("confidence_policy must be INACTIVE")
    if config.intervention_catalog_version is not None:
        raise ValueError("intervention catalog must be INACTIVE")
    if config.intervention_cost_profile is not None:
        raise ValueError("intervention cost profile must be INACTIVE")
    if config.intervention_lead_time_profile is not None:
        raise ValueError("intervention lead time profile must be INACTIVE")
    flags = config.module_flags
    if flags.intervention_evidence or flags.human_thermal_burden or flags.overnight_recovery:
        raise ValueError("Phoenix v1 module flags must all be false")
    spread = config.hazard_spread_policy
    if spread.version != DECISION8_POLICY_VERSION:
        raise ValueError("Decision 8 policy version mismatch")
    if spread.input_quantity != INPUT_QUANTITY:
        raise ValueError("Decision 8 input must be q_A")
    if spread.metric != METRIC_TOP3_BOTTOM3:
        raise ValueError("Decision 8 metric mismatch")
    if spread.top_group_size != TOP_GROUP_SIZE or spread.bottom_group_size != BOTTOM_GROUP_SIZE:
        raise ValueError("Decision 8 tail group size mismatch")
    if spread.minimum_useful_spread != SPREAD_FLOOR:
        raise ValueError("Decision 8 floor mismatch")
    if spread.comparison_operator != COMPARISON_OPERATOR:
        raise ValueError("Decision 8 comparison operator mismatch")
    if spread.reference_version != REFERENCE_VERSION:
        raise ValueError("Decision 8 reference_version mismatch")
    if spread.zone_geometry_version != ZONE_GEOMETRY_VERSION:
        raise ValueError("Decision 8 zone_geometry_version mismatch")
    if spread.expected_zone_count != EXPECTED_ZONE_COUNT:
        raise ValueError("Decision 8 expected_zone_count mismatch")
    if spread.metric == "between_zone_hazard_range":
        raise ValueError("raw °C max-min must not be the Phoenix v1 ranking gate")
    assert_runtime_matches_frozen_reference()


def serialize_phoenix_v1_area_config(config: AreaConfig) -> str:
    return json.dumps(config.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"


CANDIDATE_RELATIVE_PATH = Path("data") / "demo" / "phoenix" / "area_config.json"
CANONICAL_REFERENCE_RELATIVE_PATH = (
    Path("data") / "phoenix" / "reference" / "observations.jsonl"
)


def hackathon_root() -> Path:
    return Path(__file__).resolve().parents[4]


def frozen_area_config_path() -> Path:
    return hackathon_root() / CANDIDATE_RELATIVE_PATH


def frozen_area_config_sha256() -> str:
    return hashlib.sha256(frozen_area_config_path().read_bytes()).hexdigest()


def load_frozen_phoenix_v1_area_config() -> AreaConfig:
    """Load the Decision 9 frozen canonical AreaConfig. Refuses a mutated file."""
    path = frozen_area_config_path()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_AREA_CONFIG_SHA256:
        raise ValueError(
            "frozen AreaConfig SHA-256 mismatch; refusing to load a mutated file"
        )
    config = AreaConfig.model_validate(json.loads(raw.decode("utf-8")))
    validate_phoenix_v1_area_config(config)
    return config
