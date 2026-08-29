"""Evidence DAG for the replay vertical slice."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.evidence import EvidenceEdge, EvidenceGraph, EvidenceNode

__all__ = ["build_phoenix_v1_evidence_graph", "build_replay_evidence_graph"]


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
