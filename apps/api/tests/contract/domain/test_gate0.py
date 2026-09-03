"""Gate 0 state-machine contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain import Gate0Decision, Gate0Ledger


def _ledger_payload() -> dict:
    return {
        "schema_version": "GATE0_LEDGER_V1",
        "ledger_version": "test-ledger-v1",
        "area_id": "phoenix-demo",
        "overall_status": "OPEN",
        "human_close_approval": None,
        "decisions": [
            {
                "decision_id": "event_definition",
                "label": "Event definition",
                "status": "INCOMPLETE",
                "required_for_closure": True,
                "summary": "Not frozen.",
                "evidence_refs": ["docs/product/GATE0_DECISION_LEDGER.md"],
            }
        ],
        "capabilities": [
            {
                "capability_id": "calibrated_event_probability",
                "status": "BLOCKED",
                "requires_gate0_closed": True,
                "reason": "Event definition is incomplete.",
                "activation_condition": None,
                "evidence_refs": ["apps/api/app/services/orchestrator.py"],
            }
        ],
    }


@pytest.mark.parametrize("status", ["AUTHORIZED", "CONDITIONAL"])
def test_open_gate_cannot_activate_closed_only_capability(status: str) -> None:
    payload = _ledger_payload()
    payload["capabilities"][0]["status"] = status
    with pytest.raises(ValidationError, match=f"cannot be {status}"):
        Gate0Ledger.model_validate(payload)


def test_closed_gate_requires_human_approval() -> None:
    payload = _ledger_payload()
    payload["overall_status"] = "CLOSED"
    payload["decisions"][0]["status"] = "VERIFIED"
    with pytest.raises(ValidationError, match="requires a human close approval"):
        Gate0Ledger.model_validate(payload)


def test_closed_gate_rejects_incomplete_required_decision() -> None:
    payload = _ledger_payload()
    payload["overall_status"] = "CLOSED"
    payload["human_close_approval"] = {
        "approved_by": "test-owner",
        "approved_at": "2026-09-03T00:00:00Z",
        "approval_ref": "docs/product/GATE0_DECISION_LEDGER.md",
    }
    with pytest.raises(ValidationError, match="incomplete required decisions"):
        Gate0Ledger.model_validate(payload)


@pytest.mark.parametrize(
    "evidence_ref",
    [
        "/tmp/evidence.json",
        "../evidence.json",
        "workforce/decisions/private.json",
        "docs/workforce/private.json",
    ],
)
def test_evidence_reference_must_be_repository_relative_and_tracked(
    evidence_ref: str,
) -> None:
    payload = deepcopy(_ledger_payload()["decisions"][0])
    payload["evidence_refs"] = [evidence_ref]
    with pytest.raises(ValidationError, match="evidence_ref"):
        Gate0Decision.model_validate(payload)


def test_decision_requires_at_least_one_evidence_reference() -> None:
    payload = deepcopy(_ledger_payload()["decisions"][0])
    payload["evidence_refs"] = []
    with pytest.raises(ValidationError, match="at least 1 item"):
        Gate0Decision.model_validate(payload)
