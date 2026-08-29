"""Tile→zone aggregation contract (policy only; aggregation is owned by Agent C)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import TileAssignmentMethod, ZoneAggregationStatistic


class ThermalAggregationSpec(BaseModel):
    version: str
    assignment_method: TileAssignmentMethod
    statistic: ZoneAggregationStatistic
    minimum_coverage_ratio: float | None = None
    zero_tile_behavior: Literal["insufficient_evidence"]
    boundary_behavior: str
    notes: list[str] = Field(default_factory=list)


def default_thermal_aggregation_spec(
    version: str,
    minimum_coverage_ratio: float | None = None,
    *,
    boundary_behavior: str = "centroid_within_zone",
    notes: list[str] | None = None,
) -> ThermalAggregationSpec:
    """Architecture default bias: CENTROID_WITHIN + MEAN; zero tiles → insufficient_evidence.

    ``minimum_coverage_ratio`` is not independently configurable once an AreaConfig
    is assembled: CoveragePolicy is canonical. ``None`` means no numeric floor.
    """
    return ThermalAggregationSpec(
        version=version,
        assignment_method=TileAssignmentMethod.CENTROID_WITHIN,
        statistic=ZoneAggregationStatistic.MEAN,
        minimum_coverage_ratio=minimum_coverage_ratio,
        zero_tile_behavior="insufficient_evidence",
        boundary_behavior=boundary_behavior,
        notes=list(notes) if notes is not None else [],
    )
