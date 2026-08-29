"""Analysis version stamps."""

from pydantic import BaseModel


class AnalysisVersions(BaseModel):
    analysis_schema_version: str
    area_config_version: str
    zone_definition_version: str
    zone_geometry_version: str
    thermal_aggregation_version: str
    normalization_registry_version: str
    hazard_spread_policy_version: str
    probability_model_version: str
    consequence_model_version: str
    protection_model_version: str
    priority_model_version: str
    thermal_burden_model_version: str | None = None
    intervention_evidence_model_version: str | None = None
    recovery_model_version: str | None = None
    intervention_catalog_version: str
    context_dataset_version: str
    fortyguard_adapter_version: str
    build_commit_sha: str | None = None
