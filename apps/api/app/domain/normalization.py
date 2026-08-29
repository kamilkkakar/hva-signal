"""Normalization registry contracts. Hazard is never AOI min-max."""

from pydantic import BaseModel, Field

from app.domain.enums import ReferenceFrame


class NormalizedFeature(BaseModel):
    raw_value: float | None
    normalized_value: float | None
    unit: str | None
    reference_frame: ReferenceFrame
    reference_definition: str
    evidence_refs: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
