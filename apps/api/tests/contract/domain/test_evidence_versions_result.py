"""Contract cluster 7: evidence graph, AnalysisVersions, AnalysisResult."""

from datetime import datetime, timezone

from app.domain import (
    AnalysisMode,
    AnalysisResult,
    AnalysisVersions,
    Confidence,
    DataStatus,
    EngineResult,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNode,
    PortfolioRecommendation,
    ResultStatus,
    SystemLimitationCode,
    ZoneDecisionResult,
)


def test_evidence_node_edge_graph_field_names() -> None:
    assert set(EvidenceNode.model_fields) == {
        "id",
        "type",
        "label",
        "source_type",
        "metadata",
    }
    assert set(EvidenceEdge.model_fields) == {"from_id", "to_id", "relation"}
    assert set(EvidenceGraph.model_fields) == {"nodes", "edges"}


def test_evidence_graph_construction() -> None:
    graph = EvidenceGraph(
        nodes=[
            EvidenceNode(
                id="tile-1",
                type="fortyguard_tile",
                label="Tile",
                source_type="replay",
                metadata={"partition_id": "p1"},
            )
        ],
        edges=[
            EvidenceEdge(from_id="tile-1", to_id="zone-obs-1", relation="aggregates_to"),
        ],
    )
    assert graph.nodes[0].type == "fortyguard_tile"
    assert graph.edges[0].relation == "aggregates_to"


def test_analysis_versions_field_names() -> None:
    assert set(AnalysisVersions.model_fields) == {
        "analysis_schema_version",
        "area_config_version",
        "zone_definition_version",
        "zone_geometry_version",
        "thermal_aggregation_version",
        "normalization_registry_version",
        "hazard_spread_policy_version",
        "probability_model_version",
        "consequence_model_version",
        "protection_model_version",
        "priority_model_version",
        "thermal_burden_model_version",
        "intervention_evidence_model_version",
        "recovery_model_version",
        "intervention_catalog_version",
        "context_dataset_version",
        "fortyguard_adapter_version",
        "build_commit_sha",
    }


def test_zone_decision_result_field_names() -> None:
    assert set(ZoneDecisionResult.model_fields) == {
        "zone_id",
        "ranked",
        "probability",
        "consequence",
        "protection",
        "priority",
        "quality_flags",
        "evidence_refs",
        "thermal_observation_valid",
        "q_A",
        "reference_range_status",
        "reference_range_exceedance_c",
        "thermal_ordering_permitted",
    }


def test_analysis_result_field_names() -> None:
    assert set(AnalysisResult.model_fields) == {
        "analysis_id",
        "generated_at",
        "analysis_mode",
        "versions",
        "data_status",
        "system_limitations",
        "zones",
        "portfolio_recommendation",
        "evidence_graph",
        "limitations",
        "reference_quality",
        "thermal_differentiation_state",
        "hazard_spread",
        "area_config_sha256",
        "reference_source_sha256",
    }


def _engine(status: ResultStatus = ResultStatus.INSUFFICIENT_EVIDENCE) -> EngineResult[float]:
    return EngineResult[float](
        status=status,
        value=None,
        confidence=Confidence(score=0.0, band="none"),
        model_version="unbuilt",
    )


def test_analysis_result_can_surface_thermal_differentiation_limitation() -> None:
    versions = AnalysisVersions(
        analysis_schema_version="0.4",
        area_config_version="unfrozen",
        zone_definition_version="unfrozen",
        zone_geometry_version="unfrozen",
        thermal_aggregation_version="agg-v0",
        normalization_registry_version="norm-v0",
        hazard_spread_policy_version="spread-v0",
        probability_model_version="prob-v0",
        consequence_model_version="cons-v0",
        protection_model_version="prot-v0",
        priority_model_version="prio-v0",
        thermal_burden_model_version=None,
        intervention_evidence_model_version=None,
        recovery_model_version=None,
        intervention_catalog_version="catalog-v0",
        context_dataset_version="ctx-v0",
        fortyguard_adapter_version="fg-v0",
        build_commit_sha=None,
    )
    result = AnalysisResult(
        analysis_id="an-1",
        generated_at=datetime(2024, 7, 15, 16, 0, tzinfo=timezone.utc),
        analysis_mode=AnalysisMode.OPERATIONAL,
        versions=versions,
        data_status=DataStatus.REPLAY,
        system_limitations=[
            SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        ],
        zones=[
            ZoneDecisionResult(
                zone_id="tract-001",
                ranked=False,
                probability=_engine(),
                consequence=_engine(),
                protection=_engine(),
                priority=_engine(),
                quality_flags=["insufficient_evidence"],
                evidence_refs=[],
            )
        ],
        portfolio_recommendation=PortfolioRecommendation(),
        evidence_graph=EvidenceGraph(nodes=[], edges=[]),
        limitations=[],
    )
    assert result.zones[0].ranked is False
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        in result.system_limitations
    )
