"""Multi-city comparison geography policy stamps.

Phoenix local production geography remains the checked-in Phoenix demo package.
Cross-city comparison is explicitly a separate layer so callers do not conflate
the Phoenix local AOI with a future comparable national selection.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.area_registry import (
    PHOENIX_AREA_SELECTION_POLICY_VERSION,
    PHOENIX_DEMO_AREA_ID,
    resolve_area_geography,
)

MULTI_CITY_ANALYSIS_GEOGRAPHY_V1 = "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1"
CROSS_CITY_COMPARISON_GEOGRAPHY_V1 = "CROSS_CITY_COMPARISON_GEOGRAPHY_V1"
MULTI_CITY_ANALYSIS_GEOGRAPHY_DOC = (
    "Comparable-city analysis targets about 25 Census tracts per city. "
    "Selection algorithm family: ALG1. This policy stamp is for cross-city "
    "comparison only and does not replace Phoenix local production geography."
)
COMPARABLE_ZONE_TARGET = 25
COMPARABLE_SELECTION_ALGORITHM = "ALG1"
PHOENIX_LOCAL_GEOGRAPHY_EXPLICIT = PHOENIX_AREA_SELECTION_POLICY_VERSION


class PhoenixGeographyAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    phoenix_compatible: bool
    reason: str = Field(min_length=1)


def audit_phoenix_cross_city_compatibility() -> PhoenixGeographyAudit:
    """Audit the explicit distinction between Phoenix local and cross-city layers."""
    phoenix = resolve_area_geography(PHOENIX_DEMO_AREA_ID)
    if phoenix.area_selection_policy_version == CROSS_CITY_COMPARISON_GEOGRAPHY_V1:
        return PhoenixGeographyAudit(
            phoenix_compatible=True,
            reason=(
                "Phoenix local geography already matches the cross-city comparison layer."
            ),
        )
    return PhoenixGeographyAudit(
        phoenix_compatible=False,
        reason=(
            "Phoenix local geography remains "
            f"{phoenix.area_selection_policy_version} on area_id={PHOENIX_DEMO_AREA_ID!r}; "
            "cross-city comparisons use CROSS_CITY_COMPARISON_GEOGRAPHY_V1 as a "
            "distinct comparable layer until a national comparable Phoenix package is "
            "materialized."
        ),
    )

