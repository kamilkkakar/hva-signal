"""Inspect production modules for J3/J4 crash-matrix coverage.

Does not import FortyGuard. Reports missing transitions honestly.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.job_store import AnalysisJob
from app.domain.job_lifecycle import ExecutionState
from app.domain.live_crash_matrix.states import (
    CRASH_POINTS,
    DURABLE_WORKER_STATES,
    DurableWorkerState,
)

_APP_ROOT = Path(__file__).resolve().parents[2]


class ProductionGapReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    j3_j4_worker_implemented: bool
    unknown_vendor_state_in_production: bool
    job_persists_activity_id: bool
    consume_happens_before_submit_in_recheck: bool
    production_execution_states: list[str]
    missing_durable_states: list[str]
    missing_crash_points_in_production: list[str]
    unimplemented_transitions: list[str]
    harness_covers_all_nine_points: Literal[True] = True
    notes: list[str] = Field(default_factory=list)


def _read(rel: str) -> str:
    return (_APP_ROOT / rel).read_text(encoding="utf-8")


def _mentions_crash_points(source: str) -> set[str]:
    found: set[str] = set()
    for point in CRASH_POINTS:
        if point.value in source or point.name in source:
            found.add(point.value)
    return found


def inspect_production_gaps() -> ProductionGapReport:
    """Static inspection of existing live/job/allowance code in this tree."""
    execution_states = [member.value for member in ExecutionState]
    durable_values = {state.value for state in DURABLE_WORKER_STATES}
    missing_states = sorted(durable_values - set(execution_states))

    job_fields = {field.name for field in dataclasses.fields(AnalysisJob)}
    job_persists_activity_id = "vendor_activity_id" in job_fields

    recheck_src = _read("services/demo_acquisition.py")
    consume_before_submit = (
        "def recheck_demo_reservation_before_paid_submission" in recheck_src
        and "ledger.consume" in recheck_src
    )

    tree_sources = []
    for rel in (
        "domain/job_lifecycle.py",
        "core/job_store.py",
        "services/demo_acquisition.py",
        "services/demo_allowance_ledger.py",
        "services/two_signal_jobs.py",
    ):
        tree_sources.append(_read(rel))
    combined = "\n".join(tree_sources)

    unknown_in_prod = "UNKNOWN_VENDOR_STATE" in combined
    mentioned = _mentions_crash_points(combined)
    missing_points = [point.value for point in CRASH_POINTS if point.value not in mentioned]

    unimplemented: list[str] = []
    for state in DURABLE_WORKER_STATES:
        if state.value not in execution_states:
            unimplemented.append(f"state:{state.value}")
    for point in CRASH_POINTS:
        unimplemented.append(f"crash:{point.value}")

    notes = [
        "Production ExecutionState is J0/J1/J2 process language, not the 17-state worker SM.",
        "AnalysisJob has no vendor_activity_id field — LIVE-A/D must add durable persistence.",
        "recheck_demo_reservation_before_paid_submission consumes before vendor submit, "
        "which inverts crash points 8–9 (cache then consume).",
        "InMemoryDemoAllowanceLedger is J0; process death wipes reservations.",
        "This worktree's CrashMatrixRunner implements all nine points against fakes.",
    ]
    if consume_before_submit:
        notes.append(
            "GAP: consume-before-submit is still the production recheck path."
        )

    return ProductionGapReport(
        j3_j4_worker_implemented=False,
        unknown_vendor_state_in_production=unknown_in_prod,
        job_persists_activity_id=job_persists_activity_id,
        consume_happens_before_submit_in_recheck=consume_before_submit,
        production_execution_states=execution_states,
        missing_durable_states=missing_states,
        missing_crash_points_in_production=missing_points,
        unimplemented_transitions=unimplemented,
        notes=notes,
    )


def assert_no_fortyguard_import(package_dir: Path) -> list[str]:
    """Parse isolated package files and reject fortyguard imports."""
    offenders: list[str] = []
    for path in package_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "fortyguard" in alias.name.lower():
                        offenders.append(f"{path.name}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if "fortyguard" in node.module.lower():
                    offenders.append(f"{path.name}:{node.module}")
    return offenders
