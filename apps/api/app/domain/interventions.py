"""Intervention catalog stub. Cost and lead-time values live in versioned AreaConfig."""

from pydantic import BaseModel, ConfigDict, Field


class InterventionDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    intervention_id: str
    name: str
    catalog_version: str
    cost_profile_key: str | None = None
    lead_time_profile_key: str | None = None
    reversibility: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
