"""Evidence DAG contracts."""

from typing import Any

from pydantic import BaseModel, Field


class EvidenceNode(BaseModel):
    id: str
    type: str
    label: str
    source_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceEdge(BaseModel):
    from_id: str
    to_id: str
    relation: str


class EvidenceGraph(BaseModel):
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]
