"""Machine-readable Gate 0 decision and capability contracts.

AreaConfig freeze state is deliberately separate from the system-wide Gate 0
state. A frozen configuration must never authorize an analytical capability on
its own.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Gate0OverallStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Gate0DecisionStatus(StrEnum):
    FROZEN = "FROZEN"
    VERIFIED = "VERIFIED"
    INCOMPLETE = "INCOMPLETE"
    DISABLED = "DISABLED"


class Gate0CapabilityStatus(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"


def _tracked_evidence_ref(value: str) -> str:
    """Require a repository-relative, tracked evidence reference.

    ``workforce/`` is intentionally ignored by Git and cannot be the evidence
    source for a reproducible runtime decision.
    """

    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith(("/", "~"))
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("evidence_ref must be a repository-relative path")
    if "workforce" in path.parts:
        raise ValueError("evidence_ref cannot depend on ignored workforce material")
    return path.as_posix()


class Gate0Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: Gate0DecisionStatus
    required_for_closure: bool
    summary: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def _validate_evidence_refs(cls, refs: list[str]) -> list[str]:
        return [_tracked_evidence_ref(ref) for ref in refs]


class Gate0Capability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str = Field(min_length=1)
    status: Gate0CapabilityStatus
    requires_gate0_closed: bool
    reason: str = Field(min_length=1)
    activation_condition: str | None = None
    evidence_refs: list[str] = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def _validate_evidence_refs(cls, refs: list[str]) -> list[str]:
        return [_tracked_evidence_ref(ref) for ref in refs]


class Gate0HumanCloseApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_by: str = Field(min_length=1)
    approved_at: str = Field(min_length=1)
    approval_ref: str

    @field_validator("approval_ref")
    @classmethod
    def _validate_approval_ref(cls, value: str) -> str:
        return _tracked_evidence_ref(value)


class Gate0Ledger(BaseModel):
    """Versioned Gate 0 state with fail-closed capability authorization."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["GATE0_LEDGER_V1"]
    ledger_version: str = Field(min_length=1)
    area_id: str = Field(min_length=1)
    overall_status: Gate0OverallStatus
    human_close_approval: Gate0HumanCloseApproval | None = None
    decisions: list[Gate0Decision]
    capabilities: list[Gate0Capability]

    @model_validator(mode="after")
    def _state_is_fail_closed(self) -> Self:
        decision_ids = [item.decision_id for item in self.decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("Gate 0 decision_id values must be unique")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("Gate 0 capability_id values must be unique")

        incomplete_required = [
            item.decision_id
            for item in self.decisions
            if item.required_for_closure
            and item.status == Gate0DecisionStatus.INCOMPLETE
        ]
        if self.overall_status == Gate0OverallStatus.CLOSED:
            if self.human_close_approval is None:
                raise ValueError("CLOSED Gate 0 requires a human close approval")
            if incomplete_required:
                raise ValueError(
                    "CLOSED Gate 0 cannot contain incomplete required decisions: "
                    + ", ".join(incomplete_required)
                )

        for capability in self.capabilities:
            if (
                capability.status
                in {
                    Gate0CapabilityStatus.AUTHORIZED,
                    Gate0CapabilityStatus.CONDITIONAL,
                }
                and capability.requires_gate0_closed
                and self.overall_status != Gate0OverallStatus.CLOSED
            ):
                raise ValueError(
                    f"{capability.capability_id} cannot be "
                    f"{capability.status.value} while Gate 0 is OPEN"
                )
        return self

    def decision(self, decision_id: str) -> Gate0Decision:
        for item in self.decisions:
            if item.decision_id == decision_id:
                return item
        raise KeyError(f"unknown Gate 0 decision_id={decision_id!r}")

    def capability(self, capability_id: str) -> Gate0Capability:
        for item in self.capabilities:
            if item.capability_id == capability_id:
                return item
        raise KeyError(f"unknown Gate 0 capability_id={capability_id!r}")

    @property
    def incomplete_required_decisions(self) -> tuple[str, ...]:
        return tuple(
            item.decision_id
            for item in self.decisions
            if item.required_for_closure
            and item.status == Gate0DecisionStatus.INCOMPLETE
        )
