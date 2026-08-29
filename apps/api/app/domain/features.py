"""Zone feature vector contract."""

from pydantic import BaseModel, Field

from app.domain.normalization import NormalizedFeature


class ZoneFeatureVector(BaseModel):
    zone_id: str
    hazard_peak: NormalizedFeature | None = None
    hazard_anomaly: NormalizedFeature | None = None
    hazard_duration: NormalizedFeature | None = None
    exposure_population: NormalizedFeature | None = None
    exposure_critical_facilities: NormalizedFeature | None = None
    vulnerability_index: NormalizedFeature | None = None
    cooling_access_score: NormalizedFeature | None = None
    thermal_burden_score: NormalizedFeature | None = None
    intervention_evidence_modifier: NormalizedFeature | None = None
    recovery_score: NormalizedFeature | None = None
    coverage_ratio: float
    quality_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
