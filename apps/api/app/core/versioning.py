"""Analysis version-stamp helpers. Schema version tracks architecture, not geography."""

from typing import Any

from app.domain.versions import AnalysisVersions

ANALYSIS_SCHEMA_VERSION = "0.4"


def stamp_analysis_versions(**fields: Any) -> AnalysisVersions:
    payload: dict[str, Any] = {
        "analysis_schema_version": ANALYSIS_SCHEMA_VERSION,
        "thermal_burden_model_version": None,
        "intervention_evidence_model_version": None,
        "recovery_model_version": None,
        "build_commit_sha": None,
    }
    payload.update(fields)
    return AnalysisVersions.model_validate(payload)
