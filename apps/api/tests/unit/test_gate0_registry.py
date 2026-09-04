"""Canonical Phoenix Gate 0 ledger integrity and runtime policy."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from app.core.gate0_registry import (
    PHOENIX_GATE0_LEDGER_RELATIVE_PATH,
    PHOENIX_GATE0_LEDGER_SHA256,
    REQUIRED_GATE0_CAPABILITIES,
    REQUIRED_GATE0_DECISIONS,
    Gate0RegistryError,
    load_phoenix_gate0_ledger,
    require_capability_status,
    require_open_phoenix_runtime_policy,
)
from app.core.phoenix_v1_area_config import load_frozen_phoenix_v1_area_config
from app.domain.gate0 import Gate0CapabilityStatus, Gate0OverallStatus


def test_canonical_ledger_loads_with_locked_sha_and_complete_contract() -> None:
    resolved = load_phoenix_gate0_ledger()
    assert resolved.path.as_posix().endswith(
        PHOENIX_GATE0_LEDGER_RELATIVE_PATH.as_posix()
    )
    assert resolved.sha256 == PHOENIX_GATE0_LEDGER_SHA256
    assert {item.decision_id for item in resolved.ledger.decisions} == set(
        REQUIRED_GATE0_DECISIONS
    )
    assert {item.capability_id for item in resolved.ledger.capabilities} == set(
        REQUIRED_GATE0_CAPABILITIES
    )


def test_frozen_area_config_does_not_close_analytical_gate() -> None:
    config = load_frozen_phoenix_v1_area_config()
    resolved = load_phoenix_gate0_ledger()
    assert config.gate0_status == "frozen"
    assert resolved.ledger.overall_status == Gate0OverallStatus.OPEN
    assert resolved.ledger.incomplete_required_decisions == (
        "adverse_event_definition",
        "between_aoi_variance_test",
        "temporal_static_field_test",
    )


def test_expected_tile_coverage_is_verified_without_authorizing_a_floor() -> None:
    resolved = load_phoenix_gate0_ledger()
    decision = resolved.ledger.decision("expected_tile_coverage_distribution")
    assert decision.status.value == "VERIFIED"
    assert "data/gate0/phoenix-v1/expected_tile_coverage.json" in decision.evidence_refs
    assert resolved.ledger.overall_status == Gate0OverallStatus.OPEN


def test_canonical_evidence_references_are_present_and_not_workforce() -> None:
    resolved = load_phoenix_gate0_ledger()
    refs = [
        ref
        for item in [*resolved.ledger.decisions, *resolved.ledger.capabilities]
        for ref in item.evidence_refs
    ]
    assert refs
    assert all("workforce" not in PurePosixPath(ref).parts for ref in refs)


def test_runtime_policy_requires_open_blocked_conditional_contract() -> None:
    resolved = load_phoenix_gate0_ledger()
    require_open_phoenix_runtime_policy(resolved)
    assert (
        resolved.ledger.capability("calibrated_event_probability").status
        == Gate0CapabilityStatus.BLOCKED
    )
    assert (
        resolved.ledger.capability("descriptive_thermal_ordering").status
        == Gate0CapabilityStatus.CONDITIONAL
    )


def test_sha_mismatch_fails_closed() -> None:
    with pytest.raises(Gate0RegistryError, match="SHA-256 mismatch"):
        load_phoenix_gate0_ledger(expected_sha256="0" * 64)


def test_unexpected_runtime_capability_state_fails_closed() -> None:
    resolved = load_phoenix_gate0_ledger()
    with pytest.raises(Gate0RegistryError, match="runtime path requires AUTHORIZED"):
        require_capability_status(
            resolved,
            "calibrated_event_probability",
            Gate0CapabilityStatus.AUTHORIZED,
        )
