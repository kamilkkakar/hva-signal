"""Reproducible expected-tile-coverage evidence for Phoenix Gate 0."""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest

from app.core.gate0_coverage_registry import (
    PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH,
    PHOENIX_COVERAGE_EVIDENCE_SHA256,
    Gate0CoverageRegistryError,
    build_phoenix_expected_tile_coverage_evidence,
    load_phoenix_expected_tile_coverage_evidence,
    render_phoenix_expected_tile_coverage_evidence,
)
from app.core.phoenix_v1_area_config import hackathon_root


def test_tracked_coverage_evidence_reproduces_exactly() -> None:
    root = hackathon_root()
    rebuilt = build_phoenix_expected_tile_coverage_evidence(root)
    canonical = root / PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH

    assert render_phoenix_expected_tile_coverage_evidence(rebuilt) == canonical.read_bytes()
    assert rebuilt.reference_field_count == 93
    assert rebuilt.snapshot_field_count == 2
    assert rebuilt.observed_field_count == 95
    assert rebuilt.observed_zone_row_count == 2_375
    assert rebuilt.distribution.expected_field_tile_count == 3_749
    assert rebuilt.distribution.minimum_zone_tile_count == 32
    assert rebuilt.distribution.median_zone_tile_count == 128
    assert rebuilt.distribution.maximum_zone_tile_count == 355
    assert len(rebuilt.distribution.zones) == 25
    assert all(
        zone.minimum_observed_tile_count
        == zone.expected_tile_count
        == zone.maximum_observed_tile_count
        for zone in rebuilt.distribution.zones
    )


def test_canonical_coverage_evidence_is_hash_locked_and_source_bound() -> None:
    resolved = load_phoenix_expected_tile_coverage_evidence(hackathon_root())
    assert resolved.sha256 == PHOENIX_COVERAGE_EVIDENCE_SHA256
    assert resolved.evidence.status == "VERIFIED"
    assert resolved.evidence.policy_boundary.minimum_coverage_ratio is None
    assert resolved.evidence.policy_boundary.numeric_floor_authorized is False
    assert resolved.evidence.policy_boundary.runtime_effect == "evidence_baseline_only"
    assert {source.role for source in resolved.evidence.sources} == {
        "area_config",
        "area_manifest",
        "zone_geometry",
        "reference_panel",
        "selected_time_snapshot",
    }


def _copy_coverage_tree(tmp_path: Path) -> Path:
    root = hackathon_root()
    for relative in (
        Path("data/gate0"),
        Path("data/demo/phoenix"),
        Path("data/areas/phoenix-demo"),
        Path("data/phoenix/reference"),
        Path("data/phoenix/snapshots"),
    ):
        shutil.copytree(root / relative, tmp_path / relative, dirs_exist_ok=True)
    return tmp_path


def test_changed_source_fails_closed_even_when_artifact_is_unchanged(
    tmp_path: Path,
) -> None:
    root = _copy_coverage_tree(tmp_path)
    source = root / "data/phoenix/snapshots/2024-07-08T15-00.snapshot.json"
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(Gate0CoverageRegistryError, match="source SHA-256 mismatch"):
        load_phoenix_expected_tile_coverage_evidence(root)


def test_changed_artifact_fails_closed_before_parsing(tmp_path: Path) -> None:
    root = _copy_coverage_tree(tmp_path)
    artifact = root / PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(Gate0CoverageRegistryError, match="evidence SHA-256 mismatch"):
        load_phoenix_expected_tile_coverage_evidence(root)


def test_coverage_builder_has_no_network_or_vendor_dependency() -> None:
    source = (
        hackathon_root()
        / "apps/api/app/core/gate0_coverage_registry.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "httpx" not in imported
    assert all("fortyguard" not in name for name in imported)
