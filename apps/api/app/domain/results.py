"""Engine output, zone decision, and analysis result contracts."""

from datetime import datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AnalysisMode, DataStatus, ResultStatus
from app.domain.evidence import EvidenceGraph
from app.domain.versions import AnalysisVersions

T = TypeVar("T")


class Confidence(BaseModel):
    score: Annotated[float, Field(ge=0, le=1)]
    band: str


class EngineResult(BaseModel, Generic[T]):
    status: ResultStatus
    value: T | None = None
    confidence: Confidence
    confidence_reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    model_version: str


class HazardSpreadProvenance(BaseModel):
    """First-class Decision 8 / hazard-spread evidence. Not developer-only metadata."""

    policy_version: str
    reference_version: str | None = None
    zone_geometry_version: str | None = None
    input_quantity: str | None = None
    metric: str
    top_group_size: int | None = None
    bottom_group_size: int | None = None
    floor: float | None = None
    comparison_operator: str | None = None
    observed_spread: float | None = None
    differentiation_state: str
    reference_quality: str
    suppression_reason: str | None = None
    historical_years: list[int] | None = None
    reference_hour: str | None = None


class ZoneDecisionResult(BaseModel):
    zone_id: str
    ranked: bool
    probability: EngineResult[Any]
    consequence: EngineResult[Any]
    protection: EngineResult[Any]
    priority: EngineResult[Any]
    quality_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    thermal_observation_valid: bool = False
    q_A: float | None = None
    reference_range_status: str | None = None
    reference_range_exceedance_c: float | None = None
    thermal_ordering_permitted: bool = False


class PortfolioRecommendation(BaseModel):
    """Optional typed stub until the least-regret / portfolio engine is implemented."""

    model_config = ConfigDict(extra="allow")

    summary: str | None = None
    recommended_intervention_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    analysis_id: str
    generated_at: datetime
    analysis_mode: AnalysisMode
    versions: AnalysisVersions
    data_status: DataStatus
    system_limitations: list[str] = Field(default_factory=list)
    zones: list[ZoneDecisionResult]
    portfolio_recommendation: PortfolioRecommendation | None = None
    evidence_graph: EvidenceGraph
    limitations: list[str] = Field(default_factory=list)
    reference_quality: str | None = None
    thermal_differentiation_state: str | None = None
    hazard_spread: HazardSpreadProvenance | None = None
    area_config_sha256: str | None = None
    reference_source_sha256: str | None = None
