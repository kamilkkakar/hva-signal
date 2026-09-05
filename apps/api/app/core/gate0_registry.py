"""Integrity-checked Gate 0 ledger loading.

The canonical ledger is deliberately independent from ``AreaConfig``. The
configuration can be frozen while the analytical gate remains open.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.core.gate0_coverage_registry import (
    PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH,
    PHOENIX_COVERAGE_GENERATOR_RELATIVE_PATH,
    Gate0CoverageRegistryError,
    load_phoenix_expected_tile_coverage_evidence,
)
from app.core.hourly_thermal_event_registry import (
    PHOENIX_HOURLY_EVENT_CONTRACT_RELATIVE_PATH,
    HourlyThermalEventRegistryError,
    load_phoenix_hourly_thermal_event_contract,
)
from app.core.phoenix_v1_area_config import (
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)
from app.domain.gate0 import (
    Gate0CapabilityStatus,
    Gate0DecisionStatus,
    Gate0Ledger,
    Gate0OverallStatus,
)
from app.domain.phoenix_v1 import AREA_ID

PHOENIX_GATE0_LEDGER_RELATIVE_PATH = (
    Path("data") / "gate0" / "phoenix-v1" / "ledger.json"
)
PHOENIX_GATE0_LEDGER_SHA256 = (
    "46bce20b28f407ada19b1f00809ecafd91fbe46e0048743f7fc3e1ddac2e2429"
)

REQUIRED_GATE0_DECISIONS = frozenset(
    {
        "adverse_event_definition",
        "demo_zone_type",
        "zone_geometry",
        "expected_zone_count",
        "acquisition_granularity",
        "tile_zone_assignment",
        "zone_aggregation",
        "aoi_partition_plan",
        "expected_tile_coverage_distribution",
        "between_aoi_variance_test",
        "temporal_static_field_test",
        "intervention_evidence_decision",
        "hazard_spread_floor",
        "versioned_area_config",
    }
)

REQUIRED_GATE0_CAPABILITIES = frozenset(
    {
        "descriptive_thermal_ordering",
        "context_inventory",
        "calibrated_event_probability",
        "consequence_scoring",
        "protective_capacity_scoring",
        "priority_ranking",
        "least_regret_scenario",
        "modeled_intervention_evidence",
        "human_thermal_burden",
        "overnight_recovery",
    }
)


class Gate0RegistryError(ValueError):
    """Gate 0 ledger path, schema, hash or cross-contract failure."""


@dataclass(frozen=True)
class ResolvedGate0Ledger:
    ledger: Gate0Ledger
    path: Path
    sha256: str


def _evidence_path(repo: Path, relative: str) -> Path:
    root = repo.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise Gate0RegistryError(
            f"Gate 0 evidence_ref escapes repository root: {relative}"
        ) from exc
    if not path.is_file():
        raise Gate0RegistryError(f"Gate 0 evidence_ref is missing: {relative}")
    return path


def _assert_complete_contract(ledger: Gate0Ledger) -> None:
    decision_ids = {item.decision_id for item in ledger.decisions}
    if decision_ids != REQUIRED_GATE0_DECISIONS:
        missing = sorted(REQUIRED_GATE0_DECISIONS - decision_ids)
        extra = sorted(decision_ids - REQUIRED_GATE0_DECISIONS)
        raise Gate0RegistryError(
            f"Gate 0 decision set mismatch; missing={missing}, extra={extra}"
        )
    capability_ids = {item.capability_id for item in ledger.capabilities}
    if capability_ids != REQUIRED_GATE0_CAPABILITIES:
        missing = sorted(REQUIRED_GATE0_CAPABILITIES - capability_ids)
        extra = sorted(capability_ids - REQUIRED_GATE0_CAPABILITIES)
        raise Gate0RegistryError(
            f"Gate 0 capability set mismatch; missing={missing}, extra={extra}"
        )


def _assert_area_config_separation(ledger: Gate0Ledger) -> None:
    config = load_frozen_phoenix_v1_area_config()
    if config.area_id != ledger.area_id:
        raise Gate0RegistryError("Gate 0 ledger and AreaConfig area_id disagree")
    if ledger.decision("versioned_area_config").status != Gate0DecisionStatus.FROZEN:
        raise Gate0RegistryError("canonical AreaConfig decision must be FROZEN")

    expected_disabled = {
        "modeled_intervention_evidence": config.module_flags.intervention_evidence,
        "human_thermal_burden": config.module_flags.human_thermal_burden,
        "overnight_recovery": config.module_flags.overnight_recovery,
    }
    for capability_id, enabled in expected_disabled.items():
        status = ledger.capability(capability_id).status
        if enabled or status != Gate0CapabilityStatus.DISABLED:
            raise Gate0RegistryError(
                f"{capability_id} must match the disabled Phoenix v1 module flag"
            )


def _assert_expected_tile_coverage_evidence(
    ledger: Gate0Ledger,
    repo: Path,
) -> None:
    decision = ledger.decision("expected_tile_coverage_distribution")
    if decision.status != Gate0DecisionStatus.VERIFIED:
        raise Gate0RegistryError(
            "canonical expected-tile-coverage decision must be VERIFIED"
        )
    required_refs = {
        PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH.as_posix(),
        PHOENIX_COVERAGE_GENERATOR_RELATIVE_PATH.as_posix(),
    }
    if not required_refs.issubset(decision.evidence_refs):
        raise Gate0RegistryError(
            "expected-tile-coverage decision is missing its reproducible evidence refs"
        )
    try:
        resolved = load_phoenix_expected_tile_coverage_evidence(repo)
    except Gate0CoverageRegistryError as exc:
        raise Gate0RegistryError(str(exc)) from exc
    if resolved.evidence.area_id != ledger.area_id:
        raise Gate0RegistryError(
            "Gate 0 ledger and expected-tile-coverage evidence area_id disagree"
        )


def _assert_hourly_event_candidate(ledger: Gate0Ledger, repo: Path) -> None:
    decision = ledger.decision("adverse_event_definition")
    if decision.status != Gate0DecisionStatus.INCOMPLETE:
        raise Gate0RegistryError(
            "hourly event candidate must not freeze the adverse-event decision"
        )
    if PHOENIX_HOURLY_EVENT_CONTRACT_RELATIVE_PATH.as_posix() not in decision.evidence_refs:
        raise Gate0RegistryError(
            "adverse-event decision is missing its tracked candidate contract"
        )
    try:
        resolved = load_phoenix_hourly_thermal_event_contract(root=repo)
    except HourlyThermalEventRegistryError as exc:
        raise Gate0RegistryError(str(exc)) from exc
    if resolved.contract.area_id != ledger.area_id:
        raise Gate0RegistryError(
            "Gate 0 ledger and hourly event candidate area_id disagree"
        )
    if (
        ledger.capability("calibrated_event_probability").status
        != Gate0CapabilityStatus.BLOCKED
    ):
        raise Gate0RegistryError(
            "candidate event contract cannot authorize calibrated probability"
        )


def load_phoenix_gate0_ledger(
    *,
    root: Path | None = None,
    expected_sha256: str | None = None,
) -> ResolvedGate0Ledger:
    """Load the tracked Phoenix ledger and validate every evidence reference.

    When ``root`` is omitted, the production SHA lock is mandatory. Tests may
    pass an explicit root and expected hash for isolated fixtures.
    """

    repo = Path(root) if root is not None else hackathon_root()
    path = repo / PHOENIX_GATE0_LEDGER_RELATIVE_PATH
    if not path.is_file():
        raise Gate0RegistryError("canonical Phoenix Gate 0 ledger is missing")

    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = (
        expected_sha256
        if expected_sha256 is not None
        else PHOENIX_GATE0_LEDGER_SHA256
    )
    if digest != expected:
        raise Gate0RegistryError("Phoenix Gate 0 ledger SHA-256 mismatch")
    try:
        ledger = Gate0Ledger.model_validate(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise Gate0RegistryError(f"invalid Phoenix Gate 0 ledger: {exc}") from exc
    if ledger.area_id != AREA_ID:
        raise Gate0RegistryError("Phoenix Gate 0 ledger area_id mismatch")

    _assert_complete_contract(ledger)
    for item in [*ledger.decisions, *ledger.capabilities]:
        for evidence_ref in item.evidence_refs:
            _evidence_path(repo, evidence_ref)
    if ledger.human_close_approval is not None:
        _evidence_path(repo, ledger.human_close_approval.approval_ref)
    _assert_area_config_separation(ledger)
    _assert_expected_tile_coverage_evidence(ledger, repo)
    _assert_hourly_event_candidate(ledger, repo)
    return ResolvedGate0Ledger(ledger=ledger, path=path, sha256=digest)


def require_capability_status(
    resolved: ResolvedGate0Ledger,
    capability_id: str,
    expected: Gate0CapabilityStatus,
) -> None:
    """Fail closed when a runtime path and the ledger disagree."""

    actual = resolved.ledger.capability(capability_id).status
    if actual != expected:
        raise Gate0RegistryError(
            f"{capability_id} is {actual.value}; runtime path requires {expected.value}"
        )


def require_open_phoenix_runtime_policy(resolved: ResolvedGate0Ledger) -> None:
    """Bind today's Phoenix runtime to the exact fail-closed policy it implements.

    Closing Gate 0 or changing either capability is intentionally a code change,
    not a silent ledger edit.
    """

    if resolved.ledger.overall_status != Gate0OverallStatus.OPEN:
        raise Gate0RegistryError(
            "Phoenix runtime implements the OPEN Gate 0 policy only"
        )
    require_capability_status(
        resolved,
        "calibrated_event_probability",
        Gate0CapabilityStatus.BLOCKED,
    )
    require_capability_status(
        resolved,
        "descriptive_thermal_ordering",
        Gate0CapabilityStatus.CONDITIONAL,
    )
