"""Evidence DAG for the replay vertical slice."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.evidence import EvidenceEdge, EvidenceGraph, EvidenceNode

__all__ = [
    "build_phoenix_v1_evidence_graph",
    "build_replay_evidence_graph",
    "build_selected_time_snapshot_evidence_graph",
]

_SIGNAL_B_FORBIDDEN_NODE_TYPES = frozenset(
    {
        "decision1b_reference",
        "hazard_spread",
        "normalized_hazard",
        "q_a",
    }
)
_SIGNAL_B_FORBIDDEN_NODE_IDS = frozenset(
    {
        "decision1b_reference",
        "decision8_hazard_spread",
    }
)


def build_replay_evidence_graph(
    *,
    area_id: str,
    fixture_label: str,
    fixture_fingerprint: str,
    adapter_version: str,
    zone_ids: Sequence[str],
    extra_metadata: dict[str, Any] | None = None,
) -> EvidenceGraph:
    """Record request → replay fixture → adapter → aggregation. No probability node."""
    extra = extra_metadata or {}
    request_id = "analysis_request"
    fixture_id = "replay_fixture"
    adapter_id = "fortyguard_adapter"
    aggregation_id = "zone_aggregation"

    request_meta: dict[str, Any] = {"area_id": area_id}
    request_meta.update({key: value for key, value in extra.items() if key.startswith("request_")})

    spread_meta = {
        key: extra[key]
        for key in (
            "reference_quality",
            "decision8_policy_version",
            "decision8_evaluated",
        )
        if key in extra
    }

    nodes = [
        EvidenceNode(
            id=request_id,
            type="request",
            label="Analysis request",
            source_type="user",
            metadata=request_meta,
        ),
        EvidenceNode(
            id=fixture_id,
            type="replay_fixture",
            label=fixture_label,
            source_type="replay",
            metadata={
                "fingerprint": fixture_fingerprint,
                "label": fixture_label,
            },
        ),
        EvidenceNode(
            id=adapter_id,
            type="adapter",
            label="FortyGuard adapter",
            source_type="fortyguard",
            metadata={"adapter_version": adapter_version},
        ),
        EvidenceNode(
            id=aggregation_id,
            type="aggregation",
            label="Tile-to-zone aggregation",
            source_type="engine",
            metadata={"zone_ids": list(zone_ids)},
        ),
    ]
    edges = [
        EvidenceEdge(from_id=request_id, to_id=fixture_id, relation="maps_to"),
        EvidenceEdge(from_id=fixture_id, to_id=adapter_id, relation="served_through"),
        EvidenceEdge(from_id=adapter_id, to_id=aggregation_id, relation="aggregates_to"),
    ]
    if spread_meta:
        spread_id = "decision8_hazard_spread"
        nodes.append(
            EvidenceNode(
                id=spread_id,
                type="hazard_spread",
                label="Decision 8 hazard-spread provenance",
                source_type="engine",
                metadata=spread_meta,
            )
        )
        edges.append(
            EvidenceEdge(
                from_id=aggregation_id,
                to_id=spread_id,
                relation="validates_spread",
            )
        )
    return EvidenceGraph(nodes=nodes, edges=edges)


def build_phoenix_v1_evidence_graph(
    *,
    area_id: str,
    area_config_version: str,
    area_config_sha256: str,
    reference_label: str,
    reference_sha256: str | None,
    reference_quality: str,
    zone_ids: Sequence[str],
    extra_metadata: dict[str, Any] | None = None,
) -> EvidenceGraph:
    """Record frozen config → cached reference → cached tract means → Decision 8."""
    extra = extra_metadata or {}
    request_id = "analysis_request"
    config_id = "area_config"
    reference_id = "decision1b_reference"
    aggregation_id = "zone_aggregation"
    spread_id = "decision8_hazard_spread"

    nodes = [
        EvidenceNode(
            id=request_id,
            type="request",
            label="Analysis request",
            source_type="user",
            metadata={"area_id": area_id, **{
                key: value for key, value in extra.items() if key.startswith("request_")
            }},
        ),
        EvidenceNode(
            id=config_id,
            type="area_config",
            label=area_config_version,
            source_type="config",
            metadata={
                "area_config_version": area_config_version,
                "area_config_sha256": area_config_sha256,
            },
        ),
        EvidenceNode(
            id=reference_id,
            type="decision1b_reference",
            label=reference_label,
            source_type="cached_reference",
            metadata={
                "fingerprint": reference_sha256,
                "reference_quality": reference_quality,
                "label": reference_label,
            },
        ),
        EvidenceNode(
            id=aggregation_id,
            type="aggregation",
            label="Cached tract-level TCM means",
            source_type="engine",
            metadata={
                "zone_ids": list(zone_ids),
                "note": (
                    "Tile-to-zone aggregation was performed at Decision 1B "
                    "reference acquisition; the job consumes those cached means."
                ),
            },
        ),
        EvidenceNode(
            id=spread_id,
            type="hazard_spread",
            label="Decision 8 hazard-spread provenance",
            source_type="engine",
            metadata={
                key: extra[key]
                for key in (
                    "reference_quality",
                    "decision8_policy_version",
                    "decision8_evaluated",
                    "reference_version",
                    "area_config_version",
                )
                if key in extra
            },
        ),
    ]
    edges = [
        EvidenceEdge(from_id=request_id, to_id=config_id, relation="loads"),
        EvidenceEdge(from_id=config_id, to_id=reference_id, relation="requires"),
        EvidenceEdge(from_id=reference_id, to_id=aggregation_id, relation="supplies_target"),
        EvidenceEdge(from_id=aggregation_id, to_id=spread_id, relation="validates_spread"),
    ]
    return EvidenceGraph(nodes=nodes, edges=edges)


def build_selected_time_snapshot_evidence_graph(
    *,
    area_id: str,
    geometry_version: str,
    timezone: str,
    target_timestamp: str,
    source_type: str,
    aggregation_spec_version: str,
    zone_ids: Sequence[str],
    vendor_request_fingerprint: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> EvidenceGraph:
    """Signal B DAG: geography → target acquisition → zone absolute values.

    Must never include Decision 1B reference or Decision 8 nodes.
    """
    extra = extra_metadata or {}
    request_id = "analysis_request"
    geography_id = "area_geography"
    acquisition_id = "selected_time_acquisition"
    aggregation_id = "zone_absolute_aggregation"
    snapshot_id = "selected_time_snapshot"

    nodes = [
        EvidenceNode(
            id=request_id,
            type="request",
            label="Selected-time snapshot request",
            source_type="user",
            metadata={"area_id": area_id, "target_timestamp": target_timestamp},
        ),
        EvidenceNode(
            id=geography_id,
            type="area_geography",
            label="Resolved 25-zone geography",
            source_type="geography",
            metadata={
                "area_id": area_id,
                "geometry_version": geometry_version,
                "timezone": timezone,
            },
        ),
        EvidenceNode(
            id=acquisition_id,
            type="selected_time_acquisition",
            label="Selected-time thermal target",
            source_type=source_type,
            metadata={
                "target_timestamp": target_timestamp,
                "fingerprint": vendor_request_fingerprint,
                **{
                    key: extra[key]
                    for key in ("data_status", "cache_state")
                    if key in extra
                },
            },
        ),
        EvidenceNode(
            id=aggregation_id,
            type="aggregation",
            label="Tile-to-zone absolute mean",
            source_type="engine",
            metadata={
                "zone_ids": list(zone_ids),
                "aggregation_spec_version": aggregation_spec_version,
                "statistic": "centroid_within_mean",
                "user_facing_resolution": "zone",
            },
        ),
        EvidenceNode(
            id=snapshot_id,
            type="selected_time_snapshot",
            label="Zone-level selected-time thermal snapshot",
            source_type="engine",
            metadata={
                "units": "celsius",
                "not_q_a": True,
                "decision8_applies": False,
            },
        ),
    ]
    edges = [
        EvidenceEdge(from_id=request_id, to_id=geography_id, relation="resolves"),
        EvidenceEdge(from_id=geography_id, to_id=acquisition_id, relation="bounds"),
        EvidenceEdge(
            from_id=acquisition_id, to_id=aggregation_id, relation="aggregates_to"
        ),
        EvidenceEdge(
            from_id=aggregation_id, to_id=snapshot_id, relation="produces"
        ),
    ]
    graph = EvidenceGraph(nodes=nodes, edges=edges)
    types = {node.type for node in graph.nodes}
    ids = {node.id for node in graph.nodes}
    if types & _SIGNAL_B_FORBIDDEN_NODE_TYPES:
        raise ValueError("Signal B evidence graph cannot include Signal A nodes")
    if ids & _SIGNAL_B_FORBIDDEN_NODE_IDS:
        raise ValueError("Signal B evidence graph cannot include Signal A node ids")
    return graph
