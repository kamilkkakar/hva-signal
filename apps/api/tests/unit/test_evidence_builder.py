"""Evidence DAG for the replay vertical slice: request → fixture → adapter → aggregation."""

from __future__ import annotations

import pytest

HOURLY_TCM_FINGERPRINT = (
    "e69dce24b358bb0f80a622e7b38a315b477f9a524c7846811ec8c5eb9ed8c367"
)

GATE0_METADATA = {
    "gate0_ledger_version": "PHX_GATE0_LEDGER_V1_OPEN",
    "gate0_ledger_sha256": "a" * 64,
    "gate0_overall_status": "OPEN",
    "probability_capability_status": "BLOCKED",
}


def _graph():
    from app.services.evidence_builder import build_replay_evidence_graph

    return build_replay_evidence_graph(
        area_id="phoenix-demo",
        fixture_label="heatmap_tcm_hourly_1500.json",
        fixture_fingerprint=HOURLY_TCM_FINGERPRINT,
        adapter_version="fortyguard-adapter-0.1.0",
        zone_ids=["phoenix_demo_west", "phoenix_demo_east"],
    )


def test_replay_graph_includes_request_fixture_adapter_and_aggregation_nodes() -> None:
    graph = _graph()
    types = {node.type for node in graph.nodes}
    assert "request" in types
    assert "replay_fixture" in types
    assert "adapter" in types
    assert "aggregation" in types
    assert graph.nodes, "Evidence graph must have real nodes, not an empty placeholder"


def test_replay_graph_connects_nodes_with_edges() -> None:
    graph = _graph()
    node_ids = {node.id for node in graph.nodes}
    assert graph.edges, "Evidence graph must have real edges"
    for edge in graph.edges:
        assert edge.from_id in node_ids
        assert edge.to_id in node_ids
        assert edge.relation


def test_replay_fixture_node_records_committed_hourly_fingerprint() -> None:
    graph = _graph()
    fixture_nodes = [node for node in graph.nodes if node.type == "replay_fixture"]
    assert fixture_nodes
    assert fixture_nodes[0].metadata.get("fingerprint") == HOURLY_TCM_FINGERPRINT
    assert "heatmap_tcm_hourly_1500" in str(fixture_nodes[0].metadata.get("label") or fixture_nodes[0].label)


def test_replay_graph_records_complete_gate0_provenance() -> None:
    from app.services.evidence_builder import build_replay_evidence_graph

    graph = build_replay_evidence_graph(
        area_id="phoenix-demo",
        fixture_label="heatmap_tcm_hourly_1500.json",
        fixture_fingerprint=HOURLY_TCM_FINGERPRINT,
        adapter_version="fortyguard-adapter-0.1.0",
        zone_ids=["phoenix_demo_west", "phoenix_demo_east"],
        extra_metadata={
            **GATE0_METADATA,
            "reference_quality": "INSUFFICIENT_REFERENCE",
            "decision8_evaluated": False,
        },
    )
    gate = next(node for node in graph.nodes if node.id == "gate0_ledger")
    assert gate.type == "gate0_ledger"
    assert gate.metadata == GATE0_METADATA
    assert any(
        edge.from_id == "analysis_request"
        and edge.to_id == "gate0_ledger"
        and edge.relation == "evaluated_under"
        for edge in graph.edges
    )
    assert any(
        edge.from_id == "gate0_ledger"
        and edge.to_id == "decision8_hazard_spread"
        and edge.relation == "governs"
        for edge in graph.edges
    )


def test_partial_gate0_metadata_is_rejected() -> None:
    from app.services.evidence_builder import build_replay_evidence_graph

    with pytest.raises(ValueError, match="metadata must be complete"):
        build_replay_evidence_graph(
            area_id="phoenix-demo",
            fixture_label="fixture.json",
            fixture_fingerprint="abc",
            adapter_version="adapter-v1",
            zone_ids=["zone-1"],
            extra_metadata={"gate0_overall_status": "OPEN"},
        )


def test_signal_b_graph_has_no_decision1b_or_decision8_nodes() -> None:
    from app.services.evidence_builder import build_selected_time_snapshot_evidence_graph

    graph = build_selected_time_snapshot_evidence_graph(
        area_id="candidate-area",
        geometry_version="GEO_V1",
        timezone="America/Phoenix",
        target_timestamp="2024-07-15T15:00:00",
        source_type="fortyguard_cached",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        zone_ids=[f"geoid-{i:02d}" for i in range(25)],
        vendor_request_fingerprint="abc",
        extra_metadata={"data_status": "cached", "cache_state": "hit"},
    )
    types = {node.type for node in graph.nodes}
    ids = {node.id for node in graph.nodes}
    assert "selected_time_snapshot" in types
    assert "area_geography" in types
    assert "decision1b_reference" not in types
    assert "hazard_spread" not in types
    assert "decision1b_reference" not in ids
    assert "decision8_hazard_spread" not in ids
    assert graph.edges
