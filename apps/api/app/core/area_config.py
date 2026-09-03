"""Versioned AreaConfig model. Do not freeze Phoenix instance values here."""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.aggregation import ThermalAggregationSpec
from app.domain.enums import ReferenceFrame
from app.domain.policies import (
    ConfidencePolicy,
    CoveragePolicy,
    HazardSpreadPolicy,
    HistoricalReferenceSpec,
    ModuleFlags,
)


class AreaConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_comment: str | None = Field(default=None, alias="_comment")
    candidate_status: str | None = None

    area_id: str
    version: str

    zone_definition_version: str
    zone_type: str
    zone_source: str
    zone_geometry_version: str
    expected_zone_count: int

    granularity_m: Literal[60, 80, 100] = Field(
        description=(
            "FortyGuard acquisition/request granularity in meters. "
            "Not validated effective 100 m localization, targeting, decision "
            "precision, or block-level thermal attribution. "
            "S2 remains NOT ESTABLISHED."
        )
    )
    partition_strategy: str
    partition_policy_version: str

    thermal_aggregation: ThermalAggregationSpec

    default_hazard_reference_frame: ReferenceFrame = ReferenceFrame.HISTORICAL
    historical_reference_window: HistoricalReferenceSpec

    coverage_policy: CoveragePolicy
    confidence_policy: ConfidencePolicy
    hazard_spread_policy: HazardSpreadPolicy

    intervention_catalog_version: str | None = None
    intervention_cost_profile: dict[str, Any] | None = None
    intervention_lead_time_profile: dict[str, Any] | None = None

    module_flags: ModuleFlags

    gate0_status: Literal["not_frozen", "frozen"] = Field(
        default="not_frozen",
        description=(
            "Legacy AreaConfig freeze marker. A frozen configuration does not "
            "close the system-wide analytical Gate 0 or authorize capabilities; "
            "the versioned Gate 0 ledger is authoritative for those decisions."
        ),
    )

    @model_validator(mode="after")
    def _coverage_policy_is_canonical(self) -> Self:
        agg_floor = self.thermal_aggregation.minimum_coverage_ratio
        cov_floor = self.coverage_policy.minimum_coverage_ratio
        if agg_floor is not None and cov_floor is None:
            raise ValueError(
                "CoveragePolicy is the canonical coverage source; "
                "thermal_aggregation.minimum_coverage_ratio cannot be set independently"
            )
        if (
            agg_floor is not None
            and cov_floor is not None
            and agg_floor != cov_floor
        ):
            raise ValueError(
                "conflicting coverage floors: CoveragePolicy."
                "minimum_coverage_ratio and thermal_aggregation."
                "minimum_coverage_ratio disagree"
            )
        if cov_floor is not None and agg_floor is None:
            self.thermal_aggregation.minimum_coverage_ratio = cov_floor
        return self

    @model_validator(mode="after")
    def _spread_dependencies_match_geography_and_reference(self) -> Self:
        spread = self.hazard_spread_policy
        if (
            spread.zone_geometry_version is not None
            and spread.zone_geometry_version != self.zone_geometry_version
        ):
            raise ValueError(
                "hazard_spread_policy.zone_geometry_version must equal "
                "AreaConfig.zone_geometry_version"
            )
        if (
            spread.expected_zone_count is not None
            and spread.expected_zone_count != self.expected_zone_count
        ):
            raise ValueError(
                "hazard_spread_policy.expected_zone_count must equal "
                "AreaConfig.expected_zone_count"
            )
        if (
            spread.reference_version is not None
            and spread.reference_version != self.historical_reference_window.version
        ):
            raise ValueError(
                "hazard_spread_policy.reference_version must equal "
                "historical_reference_window.version"
            )
        return self
