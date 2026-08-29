"""Replay orchestrator: fetch TCM fixture, block P(event), do not rank without a frozen floor."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.domain.enums import AnalysisMode, DataMode, DataStatus, JobStatus, ResultStatus
from app.domain.requests import AnalysisRequest

HOURLY_TCM_FINGERPRINT = (
    "e69dce24b358bb0f80a622e7b38a315b477f9a524c7846811ec8c5eb9ed8c367"
)
EVENT_PROBABILITY_BLOCKED = "EVENT_PROBABILITY_BLOCKED_PENDING_GATE0"
FORBIDDEN_PROBABILITY_CLAIMS = ("72% probability", "0.72")


def _replay_request(**overrides) -> AnalysisRequest:
    payload = {
        "area_id": "phoenix-demo",
        "analysis_time": datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
        "analysis_mode": AnalysisMode.OPERATIONAL,
        "horizon_hours": 12,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": DataMode.REPLAY,
    }
    payload.update(overrides)
    return AnalysisRequest.model_validate(payload)


def _run(**overrides):
    from app.services.orchestrator import run_replay_analysis

    return run_replay_analysis(_replay_request(**overrides))


def test_replay_analysis_uses_committed_hourly_tcm_fixture() -> None:
    result = _run()
    fixture_nodes = [
        node for node in result.evidence_graph.nodes if node.type == "replay_fixture"
    ]
    assert fixture_nodes
    assert fixture_nodes[0].metadata.get("fingerprint") == HOURLY_TCM_FINGERPRINT
    assert result.zones
    covered = [zone for zone in result.zones if zone.zone_id != "phoenix_demo_empty"]
    assert covered, "Fixture tiles must aggregate onto unfrozen demo zones"


def test_probability_engine_result_is_blocked_with_null_value() -> None:
    result = _run()
    assert result.zones
    for zone in result.zones:
        assert zone.probability.status == ResultStatus.INSUFFICIENT_EVIDENCE
        assert zone.probability.value is None
        assert EVENT_PROBABILITY_BLOCKED in zone.probability.quality_flags


def test_replay_result_does_not_emit_calibrated_probability() -> None:
    result = _run()
    dumped = result.model_dump(mode="json")
    blob = json.dumps(dumped)
    for claim in FORBIDDEN_PROBABILITY_CLAIMS:
        assert claim not in blob
    for zone in dumped["zones"]:
        assert zone["probability"]["value"] is None
        assert zone["probability"]["status"] == "insufficient_evidence"


def test_zones_are_not_ranked_when_decision1b_reference_is_absent() -> None:
    result = _run()
    assert result.zones
    assert all(zone.ranked is False for zone in result.zones)
    assert all(zone.thermal_ordering_permitted is False for zone in result.zones)
    assert result.reference_quality == "INSUFFICIENT_REFERENCE"
    assert result.thermal_differentiation_state == "NOT_EVALUATED"
    assert "INSUFFICIENT_REFERENCE" in result.system_limitations
    assert (
        "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
        not in result.system_limitations
    )
    assert result.hazard_spread is not None
    assert result.hazard_spread.observed_spread is None
    assert result.hazard_spread.metric == "TOP3_BOTTOM3_MEAN_DIFFERENCE"


def test_replay_data_status_is_replay() -> None:
    result = _run()
    assert result.data_status == DataStatus.REPLAY


def test_utc_analysis_time_is_flagged_as_not_aoi_local() -> None:
    result = _run(analysis_time=datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc))
    flags = [flag for zone in result.zones for flag in zone.quality_flags]
    assert "ANALYSIS_TIME_NOT_AOI_LOCAL" in flags


def test_naive_analysis_time_is_treated_as_aoi_local() -> None:
    result = _run(analysis_time=datetime(2024, 7, 15, 15, 0))
    flags = [flag for zone in result.zones for flag in zone.quality_flags]
    assert "ANALYSIS_TIME_NOT_AOI_LOCAL" not in flags


def test_replay_emits_normalizing_before_hazard_spread_validation() -> None:
    from app.services.orchestrator import run_replay_analysis

    seen: list[JobStatus] = []
    run_replay_analysis(_replay_request(), status_callback=seen.append)
    assert seen.index(JobStatus.NORMALIZING) < seen.index(
        JobStatus.VALIDATING_HAZARD_SPREAD
    )


def test_replay_does_not_gate_ranking_on_raw_tcm_max_min() -> None:
    result = _run()
    blob = result.model_dump(mode="json")
    assert result.hazard_spread is not None
    assert result.hazard_spread.input_quantity == "q_A"
    assert result.hazard_spread.differentiation_state == "NOT_EVALUATED"
    assert "between_zone_hazard_range" not in json.dumps(blob["hazard_spread"])


def test_missing_hazard_spread_module_does_not_crash_and_does_not_rank() -> None:
    from app.services.orchestrator import run_replay_analysis

    result = run_replay_analysis(_replay_request(), hazard_spread_module=None)
    assert result.zones
    assert all(zone.ranked is False for zone in result.zones)
    flags = [flag for zone in result.zones for flag in zone.quality_flags]
    assert "HAZARD_SPREAD_MODULE_UNAVAILABLE" in flags
    assert all(zone.probability.value is None for zone in result.zones)


def test_zone_without_tiles_is_insufficient_not_safe() -> None:
    result = _run()
    empty = next(zone for zone in result.zones if zone.zone_id == "phoenix_demo_empty")
    assert empty.ranked is False
    assert empty.probability.value is None
    assert empty.probability.value != 0
    assert empty.probability.value != 0.0
    assert empty.probability.status == ResultStatus.INSUFFICIENT_EVIDENCE


def test_orchestrator_source_does_not_freeze_production_zones_geojson() -> None:
    src = (
        Path(__file__).resolve().parents[2] / "app" / "services" / "orchestrator.py"
    )
    text = src.read_text(encoding="utf-8")
    assert "data/demo/phoenix/zones.geojson" not in text.replace("\\", "/")


def test_execute_job_leaves_terminal_status_not_queued() -> None:
    from app.core.jobs import job_store
    from app.services.orchestrator import execute_job

    job_store.reset()
    job = job_store.create(_replay_request().model_dump(mode="json"))
    assert job.status == JobStatus.QUEUED
    execute_job(job.job_id)
    stored = job_store.get(job.job_id)
    assert stored is not None
    assert stored.status in {JobStatus.COMPLETE, JobStatus.PARTIAL}
    assert stored.status != JobStatus.QUEUED
    assert stored.result is not None
    for zone in stored.result["zones"]:
        assert zone["probability"]["value"] is None
    job_store.reset()
