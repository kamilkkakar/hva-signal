"""Preregistered Phoenix hourly pilot and canary-first execution guards."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.core.gate0_coverage_registry import (
    load_phoenix_expected_tile_coverage_evidence,
)
from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    PHOENIX_HOURLY_PILOT_MANIFEST_RELATIVE_PATH,
    PHOENIX_HOURLY_PILOT_MANIFEST_SHA256,
    PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH,
    build_phoenix_hourly_pilot_provider_aoi,
    build_phoenix_hourly_thermal_pilot_manifest,
    load_phoenix_hourly_thermal_pilot_manifest,
    render_phoenix_hourly_pilot_provider_aoi,
    render_phoenix_hourly_thermal_pilot_manifest,
    request_for_hourly_pilot_slot,
)
from app.core.phoenix_v1_area_config import hackathon_root
from app.domain.enums import ThermalDataSource, UpstreamTimeSemantics
from app.integrations.fortyguard.temporal_modes import build_heatmap_payload
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = hackathon_root()
RUNNER_PATH = ROOT / "scripts" / "acquire_phoenix_hourly_pilot.py"


def _runner():
    spec = importlib.util.spec_from_file_location(
        "acquire_phoenix_hourly_pilot", RUNNER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tracked_provider_aoi_and_manifest_reproduce_exactly() -> None:
    provider_path = ROOT / PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH
    manifest_path = ROOT / PHOENIX_HOURLY_PILOT_MANIFEST_RELATIVE_PATH
    assert render_phoenix_hourly_pilot_provider_aoi(ROOT) == provider_path.read_bytes()
    rebuilt = render_phoenix_hourly_thermal_pilot_manifest(
        build_phoenix_hourly_thermal_pilot_manifest(ROOT)
    )
    assert rebuilt == manifest_path.read_bytes()


def test_manifest_is_hash_locked_complete_and_non_authorizing() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    manifest = resolved.manifest
    assert resolved.sha256 == PHOENIX_HOURLY_PILOT_MANIFEST_SHA256
    assert manifest.status == "PREREGISTERED"
    assert manifest.request_count == 72
    assert len(manifest.slots) == 72
    assert len({slot.request_fingerprint for slot in manifest.slots}) == 72
    assert [slot.slot_id for slot in manifest.slots if slot.phase == "canary"] == [
        CANARY_SLOT_ID
    ]
    assert manifest.request_contract.temporal_mode == "single_hour"
    assert manifest.request_contract.filter_type == 1
    assert manifest.request_contract.window_aggregates_allowed is False
    assert manifest.execution_boundary.credit_cap is None
    assert manifest.execution_boundary.maximum_new_vendor_requests == 72
    assert manifest.claim_boundaries.closes_gate0 is False
    assert manifest.claim_boundaries.authorizes_operational_outcome is False
    assert manifest.claim_boundaries.authorizes_probability is False


def test_every_slot_builds_one_distinct_type1_request() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    payloads = []
    for slot in resolved.manifest.slots:
        request = request_for_hourly_pilot_slot(resolved, slot)
        payload = build_heatmap_payload(request)
        payloads.append(json.dumps(payload, sort_keys=True))
        assert payload["date_time"] == {
            "start_date": slot.date_local,
            "filter_type": 1,
            "start_time": slot.time_local,
        }
        assert "end_time" not in payload["date_time"]
        assert "end_date" not in payload["date_time"]
    assert len(set(payloads)) == 72


def test_provider_aoi_is_exact_frozen_zone_dissolve() -> None:
    zones = json.loads(
        (ROOT / "data/areas/phoenix-demo/geometry.geojson").read_text(encoding="utf-8")
    )
    expected = unary_union(
        [shape(feature["geometry"]) for feature in zones["features"]]
    )
    actual = shape(build_phoenix_hourly_pilot_provider_aoi(ROOT))
    assert actual.is_valid
    assert actual.equals(expected)


def test_manifest_builder_cannot_perform_http() -> None:
    paths = (
        ROOT / "apps/api/app/core/hourly_thermal_pilot_registry.py",
        ROOT / "scripts/build_phoenix_hourly_pilot_manifest.py",
    )
    imported: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    assert "httpx" not in imported
    assert all(not name.endswith("fortyguard.adapter") for name in imported)
    assert all(not name.endswith("fortyguard.client") for name in imported)


def test_preflight_needs_no_key_and_performs_no_http(
    tmp_path: Path, monkeypatch
) -> None:
    runner = _runner()
    for name in (
        "FORTYGUARD_API_KEY",
        "FORTYGUARD_API_KEY_VALIDATION_B",
        "FORTYGUARD_VALIDATION_B_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    report = runner._preflight(resolved, tmp_path, None)
    assert report["status"] == "PASS"
    assert report["slot_count"] == 72
    assert report["unique_request_fingerprint_count"] == 72
    assert report["provider_partition_count"] == 1
    assert report["credential_available"] is False
    assert report["execution_ready"] is False
    assert report["live_http_performed"] is False
    assert report["credits_spent"] == 0


def test_missing_key_blocks_paid_phase(tmp_path: Path, monkeypatch) -> None:
    runner = _runner()
    for name in (
        "FORTYGUARD_API_KEY",
        "FORTYGUARD_API_KEY_VALIDATION_B",
        "FORTYGUARD_VALIDATION_B_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(runner.PilotExecutionError, match="no FortyGuard credential"):
        runner._credential(None, required=True)


def test_ambiguous_prior_attempt_cannot_be_retried(tmp_path: Path) -> None:
    runner = _runner()
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    slot = next(slot for slot in resolved.manifest.slots if slot.phase == "canary")
    attempt = runner._slot_dir(tmp_path, slot) / "attempt.json"
    runner._write_json(
        attempt,
        {
            "manifest_sha256": resolved.sha256,
            "slot_id": slot.slot_id,
            "vendor_attempted": True,
            "status": "submitted_or_in_progress",
        },
    )
    with pytest.raises(runner.PilotExecutionError, match="prior vendor attempt"):
        runner._execute_slot(
            resolved=resolved,
            slot=slot,
            state_dir=tmp_path,
            credential=("TEST", "not-a-real-key", "https://invalid.example"),
        )


def _fake_assembly(*, temperature_offset: float = 0.0, filter_type: int = 1):
    coverage = load_phoenix_expected_tile_coverage_evidence(ROOT).evidence
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    zones = json.loads(
        (ROOT / "data/areas/phoenix-demo/geometry.geojson").read_text(encoding="utf-8")
    )
    reference = _runner()._reference_zone_means(
        ROOT / "data/phoenix/reference/observations.jsonl", CANARY_SLOT_ID
    )
    features = {str(f["properties"]["GEOID"]).zfill(11): f for f in zones["features"]}
    tiles = []
    tile_id = 0
    for row in coverage.distribution.zones:
        point = shape(features[row.zone_id]["geometry"]).representative_point()
        delta = 0.000001
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [point.x - delta, point.y - delta],
                    [point.x + delta, point.y - delta],
                    [point.x + delta, point.y + delta],
                    [point.x - delta, point.y + delta],
                    [point.x - delta, point.y - delta],
                ]
            ],
        }
        for _ in range(row.expected_tile_count):
            tile_id += 1
            tiles.append(
                SimpleNamespace(
                    tile_id=tile_id,
                    geometry=geometry,
                    temperature_unit="celsius",
                    observations=[
                        SimpleNamespace(
                            statistic="mean",
                            value=reference[row.zone_id] + temperature_offset,
                        )
                    ],
                )
            )
    return SimpleNamespace(
        tiles=tiles,
        completeness="complete",
        missing_partition_ids=[],
        source=ThermalDataSource.FORTYGUARD_LIVE,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        upstream_payload={
            "date_time": {
                "start_date": "2024-07-15",
                "filter_type": filter_type,
                "start_time": "03:00",
            },
            "analytic_type": "tcm",
            "granularity": 100,
            "polygon_aoi": resolved.provider_aoi,
        },
        fingerprint=next(
            slot.request_fingerprint
            for slot in resolved.manifest.slots
            if slot.phase == "canary"
        ),
    )


def _cache_copy(assembly):
    return SimpleNamespace(
        **{
            **assembly.__dict__,
            "source": ThermalDataSource.FORTYGUARD_CACHED,
        }
    )


def test_canary_validator_passes_exact_same_instant_field() -> None:
    runner = _runner()
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    slot = next(slot for slot in resolved.manifest.slots if slot.phase == "canary")
    assembly = _fake_assembly()
    normalized, _, evidence = runner._field_evidence(
        resolved=resolved,
        slot=slot,
        assembly=assembly,
        cache_recheck=_cache_copy(assembly),
        activity_id="test-activity",
        debit=4220,
        debit_source="cycle_remaining_delta",
    )
    assert all(evidence["checks"].values())
    assert evidence["canary"]["mean_absolute_delta_c"] == pytest.approx(0.0)
    assert evidence["canary"]["maximum_zone_absolute_delta_c"] == pytest.approx(0.0)
    assert normalized["mapped_tile_count"] == 3749
    assert normalized["zone_count"] == 25
    assert normalized["aggregation_spec_version"].startswith("PHX_THERMAL_AGGREGATION")


def test_canary_validator_rejects_drift_and_window_semantics() -> None:
    runner = _runner()
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    slot = next(slot for slot in resolved.manifest.slots if slot.phase == "canary")
    assembly = _fake_assembly(temperature_offset=0.06, filter_type=3)
    _, _, evidence = runner._field_evidence(
        resolved=resolved,
        slot=slot,
        assembly=assembly,
        cache_recheck=_cache_copy(assembly),
        activity_id="test-activity",
        debit=4220,
        debit_source="cycle_remaining_delta",
    )
    assert evidence["checks"]["canary_same_instant_consistent"] is False
    assert evidence["checks"]["request_is_exact_single_hour"] is False


def test_secret_redaction_applies_to_local_state(tmp_path: Path) -> None:
    runner = _runner()
    path = tmp_path / "state.json"
    runner._write_json(
        path,
        {
            "api_key": "secret",
            "nested": {"FORTYGUARD_API_KEY": "secret", "safe": "retained"},
        },
    )
    raw = path.read_text(encoding="utf-8")
    assert "secret" not in raw
    assert json.loads(raw) == {"nested": {"safe": "retained"}}
