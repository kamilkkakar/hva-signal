"""Cached analysis-area context. Reads on-disk bundle only. No acquisition."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.area_registry import PHOENIX_DEMO_AREA_ID, UnsupportedAreaError
from app.services.vulnerability_preparedness.cache import (
    ContextCacheError,
    load_context_bundle,
)
from app.services.vulnerability_preparedness.load import load_phoenix_context_area
from app.services.vulnerability_preparedness.public_catalog import (
    AREA_LABEL,
    CENSUS_GEOGRAPHY,
    MAP_MODES,
    WINDOW_SIZE,
)
from app.services.vulnerability_preparedness.view_model import (
    AnalysisAreaContextView,
    MetricQualityRow,
    ZoneMapProperties,
)

router = APIRouter()


class CoolingInventoryStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inventory_id: str
    as_of: str
    coverage: Literal["partial"]
    sites_in_window: int
    note: str


class SourceYears(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acs: str
    canopy: str
    cooling_inventory: str


class AreaContextDocument(BaseModel):
    """Story-ready area context. No raw ACS dump. No combined score."""

    model_config = ConfigDict(extra="forbid")

    area_id: str
    area_label: str
    census_geography: str
    source_years: SourceYears
    metric_quality: list[MetricQualityRow]
    comparison_eligibility: dict[str, int]
    map_modes: list[str]
    cooling_inventory: CoolingInventoryStatus
    thermal_evidence_status: Literal["AVAILABLE", "UNKNOWN"]
    zones: list[ZoneMapProperties]
    selected: AnalysisAreaContextView | None = None
    unsupported_questions: list[str] = Field(
        default_factory=lambda: ["What is the vulnerability score?"]
    )
    vulnerability_score_authorized: Literal[False] = False
    combined_score_authorized: Literal[False] = False


def _document(
    *,
    zone_id: str | None,
    thermal_sentence: str | None = None,
) -> AreaContextDocument:
    try:
        bundle = load_context_bundle()
    except ContextCacheError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    area = load_phoenix_context_area(bundle=bundle, thermal_sentence=thermal_sentence)
    selected = None
    if zone_id:
        if zone_id not in area.views:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown census tract GEOID {zone_id!r} in {area.area_id}.",
            )
        selected = area.views[zone_id]
    sources = bundle.get("sources") or {}
    cooling = bundle.get("cooling") or {}
    return AreaContextDocument(
        area_id=area.area_id,
        area_label=area.area_label,
        census_geography=CENSUS_GEOGRAPHY,
        source_years=SourceYears(
            acs=str((sources.get("acs") or {}).get("vintage") or "ACS 5-year 2020-2024"),
            canopy=str((sources.get("canopy") or {}).get("imagery_year") or "2022"),
            cooling_inventory=str(cooling.get("as_of") or "2026-05-05"),
        ),
        metric_quality=area.metric_quality,
        comparison_eligibility=area.eligible_counts,
        map_modes=list(MAP_MODES),
        cooling_inventory=CoolingInventoryStatus(
            inventory_id=str(cooling.get("inventory_id") or "mag_hrn_2026_v1"),
            as_of=str(cooling.get("as_of") or "2026-05-05"),
            coverage="partial",
            sites_in_window=int(area.join_audit.cooling_sites_in_window),
            note=(
                "Partial regional inventory. A join miss is not a claim that no "
                "cooling resource exists."
            ),
        ),
        thermal_evidence_status=(
            "AVAILABLE" if thermal_sentence else "UNKNOWN"
        ),
        zones=[area.map_properties[zid] for zid in area.zone_ids],
        selected=selected,
    )


@router.get("/areas/{area_id}/context")
def get_area_context(
    area_id: str,
    zone_id: str | None = Query(default=None),
) -> dict[str, Any]:
    if area_id != PHOENIX_DEMO_AREA_ID:
        raise HTTPException(
            status_code=404,
            detail=str(UnsupportedAreaError(area_id)),
        ) from None
    document = _document(zone_id=zone_id)
    dumped = document.model_dump(mode="json")
    if "combined_score" in dumped and dumped["combined_score"] not in {None, False}:
        raise HTTPException(status_code=500, detail="combined score is not authorized")
    return dumped


__all__ = ["AREA_LABEL", "WINDOW_SIZE", "get_area_context", "router"]
