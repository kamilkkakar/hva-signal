"""Normal job-path wiring of frozen PHX_AREA_CONFIG_V1 + Decision 1B reference.

Oracle CSV is expected values only. Analytics stay in evaluate_phoenix_v1_timestamp.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.domain.enums import JobStatus
from app.domain.phoenix_v1 import (
    AREA_CONFIG_VERSION,
    DECISION8_POLICY_VERSION,
    REFERENCE_VERSION,
    ZONE_GEOMETRY_VERSION,
)
from app.domain.requests import AnalysisRequest
from app.services.phoenix_v1_thermal import evaluate_phoenix_v1_timestamp

HACKATHON_ROOT = Path(__file__).resolve().parents[4]
AREA_CONFIG_PATH = HACKATHON_ROOT / "data" / "demo" / "phoenix" / "area_config.json"
EXPECTED_AREA_CONFIG_SHA256 = (
    "df00333a4df900a9762b7be975ed0c36b6e1749c953e9fb4690d9f6e4e02a60a"
)
OBS_PATH = (
    HACKATHON_ROOT
    / "data"
    / "phoenix"
    / "reference"
    / "observations.jsonl"
)
ORACLE_CSV = (
    HACKATHON_ROOT
    / "workforce"
    / "gate0"
    / "decision8"
    / "decision8_policy_impact_by_timestamp.csv"
)
QA_TOLERANCE = 1e-12

FORBIDDEN_ANALYTICAL_SYMBOLS = (
    "def compute_q_a",
    "def midrank_ecdf",
    "def evaluate_hazard_spread",
    "0.5 * n_eq",
)


class _ForbiddenAdapter:
    version = "forbidden-adapter"

    def fetch_heatmap(self, *args, **kwargs):
        raise AssertionError("NEW FORTYGUARD CALLS must be 0")


def _oracle_rows() -> list[dict[str, str]]:
    with ORACLE_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _earliest(state: str) -> dict[str, str]:
    for row in _oracle_rows():
        if row["result"] == state:
            return row
    raise AssertionError(f"no {state} row in audit oracle")


def _historical_request(date_yyyy_mm_dd: str) -> AnalysisRequest:
    year, month, day = (int(part) for part in date_yyyy_mm_dd.split("-"))
    return AnalysisRequest.model_validate(
        {
            "area_id": "phoenix-demo",
            "analysis_time": datetime(year, month, day, 3, 0),
            "analysis_mode": "retrospective",
            "horizon_hours": 0,
            "lookback_hours": 0,
            "granularity_m": 100,
            "data_mode": "replay",
        }
    )


def _run(date_yyyy_mm_dd: str, **overrides):
    from app.services.orchestrator import run_replay_analysis

    kwargs = {"adapter": _ForbiddenAdapter(), **overrides}
    return run_replay_analysis(_historical_request(date_yyyy_mm_dd), **kwargs)


def test_frozen_area_config_bytes_match_decision9_hash() -> None:
    digest = hashlib.sha256(AREA_CONFIG_PATH.read_bytes()).hexdigest()
    assert digest == EXPECTED_AREA_CONFIG_SHA256


def test_freeze_time_files_did_not_change_analytical_semantics() -> None:
    phoenix_v1 = (
        HACKATHON_ROOT / "apps" / "api" / "app" / "domain" / "phoenix_v1.py"
    ).read_text(encoding="utf-8")
    factory = (
        HACKATHON_ROOT / "apps" / "api" / "app" / "core" / "phoenix_v1_area_config.py"
    ).read_text(encoding="utf-8")
    assert "REFERENCE_YEARS = (2022, 2023, 2024)" in phoenix_v1
    assert 'REFERENCE_HOUR_LOCAL = "03:00"' in phoenix_v1
    assert "EXCLUDE_TARGET_TIMESTAMP" in phoenix_v1
    assert "SPREAD_FLOOR = 0.10" in phoenix_v1
    assert "TOP3_BOTTOM3_MEAN_DIFFERENCE" in phoenix_v1
    assert "def compute_q_a" not in phoenix_v1
    assert "def compute_q_a" not in factory
    assert "def midrank_ecdf" not in factory
    assert "def evaluate_hazard_spread" not in factory


def test_canonical_reference_loader_validates_full_reference() -> None:
    from app.core.phoenix_v1_area_config import load_frozen_phoenix_v1_area_config
    from app.services.phoenix_v1_reference import load_phoenix_v1_reference_panel

    config = load_frozen_phoenix_v1_area_config()
    panel = load_phoenix_v1_reference_panel(config)
    assert panel.quality == "FULL_REFERENCE"
    assert panel.row_count == 2325
    assert panel.timestamp_count == 93
    assert panel.tract_count == 25
    assert panel.reference_version == REFERENCE_VERSION
    assert panel.zone_geometry_version == ZONE_GEOMETRY_VERSION
    assert panel.source_path.resolve() == OBS_PATH.resolve()
    assert panel.source_sha256 == hashlib.sha256(OBS_PATH.read_bytes()).hexdigest()
    assert panel.source_sha256 == (
        "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c"
    )
    assert "workforce" not in panel.source_path.as_posix().replace("\\", "/")


def test_loader_and_orchestrator_do_not_duplicate_analytics() -> None:
    loader_path = (
        HACKATHON_ROOT / "apps" / "api" / "app" / "services" / "phoenix_v1_reference.py"
    )
    assert loader_path.is_file()
    loader = loader_path.read_text(encoding="utf-8")
    orch = (
        HACKATHON_ROOT / "apps" / "api" / "app" / "services" / "orchestrator.py"
    ).read_text(encoding="utf-8")
    for text in (loader, orch):
        for symbol in FORBIDDEN_ANALYTICAL_SYMBOLS:
            assert symbol not in text, f"analytical duplication: {symbol}"
    assert "evaluate_phoenix_v1_timestamp" in orch
    assert "compute_q_a(" not in orch
    assert "evaluate_hazard_spread(" not in orch
    assert "workforce/gate0/decision1b/reference_instance" not in loader
    assert "workforce/gate0/decision1b/reference_instance" not in orch


def test_selected_historical_timestamps_are_earliest_oracle_states() -> None:
    sufficient = _earliest("SUFFICIENT")
    insufficient = _earliest("INSUFFICIENT")
    assert sufficient["date"] == "2022-06-30"
    assert insufficient["date"] == "2022-07-01"


def test_sufficient_historical_job_matches_evaluator_and_oracle() -> None:
    from app.core.phoenix_v1_area_config import load_frozen_phoenix_v1_area_config
    from app.services.phoenix_v1_reference import load_phoenix_v1_reference_panel

    row = _earliest("SUFFICIENT")
    day = row["date"]
    expected_s = float(row["normalized_hazard_spread"])
    config = load_frozen_phoenix_v1_area_config()
    panel = load_phoenix_v1_reference_panel(config)
    direct = evaluate_phoenix_v1_timestamp(
        day,
        panel.observations,
        policy=config.hazard_spread_policy,
    )
    job = _run(day)

    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state == "SUFFICIENT"
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert abs(job.hazard_spread.observed_spread - expected_s) <= QA_TOLERANCE
    assert abs(direct.observed_spread - expected_s) <= QA_TOLERANCE
    assert abs(job.hazard_spread.observed_spread - direct.observed_spread) <= QA_TOLERANCE
    assert job.thermal_differentiation_state == direct.differentiation_state
    assert {zone.zone_id for zone in job.zones} == {zone.geoid for zone in direct.zones}
    assert len(job.zones) == 25
    for zone in job.zones:
        match = next(item for item in direct.zones if item.geoid == zone.zone_id)
        assert zone.q_A is not None and match.q_A is not None
        assert abs(zone.q_A - match.q_A) <= QA_TOLERANCE
        assert zone.thermal_observation_valid is True
        assert zone.thermal_ordering_permitted is True
        assert zone.ranked is True
        assert zone.probability.value is None
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" not in job.system_limitations
    assert "INSUFFICIENT_REFERENCE" not in job.system_limitations
    _assert_frozen_provenance(job, panel.source_sha256)


def test_insufficient_historical_job_is_fallback_not_failure() -> None:
    from app.core.phoenix_v1_area_config import load_frozen_phoenix_v1_area_config
    from app.services.phoenix_v1_reference import load_phoenix_v1_reference_panel

    row = _earliest("INSUFFICIENT")
    day = row["date"]
    expected_s = float(row["normalized_hazard_spread"])
    config = load_frozen_phoenix_v1_area_config()
    panel = load_phoenix_v1_reference_panel(config)
    direct = evaluate_phoenix_v1_timestamp(
        day,
        panel.observations,
        policy=config.hazard_spread_policy,
    )
    job = _run(day)

    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state == "INSUFFICIENT"
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert job.hazard_spread.observed_spread < 0.10
    assert abs(job.hazard_spread.observed_spread - expected_s) <= QA_TOLERANCE
    assert abs(direct.observed_spread - expected_s) <= QA_TOLERANCE
    assert job.thermal_differentiation_state == direct.differentiation_state
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" in job.system_limitations
    assert "INSUFFICIENT_REFERENCE" not in job.system_limitations
    assert all(zone.thermal_observation_valid for zone in job.zones)
    assert all(zone.q_A is not None for zone in job.zones)
    assert all(zone.thermal_ordering_permitted is False for zone in job.zones)
    assert all(zone.ranked is False for zone in job.zones)
    assert (
        "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE"
        in job.limitations
    )
    blob = json.dumps(job.model_dump(mode="json"))
    assert "between_zone_hazard_range" not in blob
    assert "q_B" not in blob
    _assert_frozen_provenance(job, panel.source_sha256)


def test_job_status_emits_normalizing_before_hazard_spread() -> None:
    from app.services.orchestrator import run_replay_analysis

    seen: list[JobStatus] = []
    run_replay_analysis(
        _historical_request("2022-06-30"),
        adapter=_ForbiddenAdapter(),
        status_callback=seen.append,
    )
    required = [
        JobStatus.LOADING_CONTEXT,
        JobStatus.FETCHING_THERMAL,
        JobStatus.AGGREGATING_ZONES,
        JobStatus.NORMALIZING,
        JobStatus.VALIDATING_HAZARD_SPREAD,
        JobStatus.COMPUTING,
    ]
    for status in required:
        assert status in seen
    assert seen.index(JobStatus.LOADING_CONTEXT) < seen.index(JobStatus.FETCHING_THERMAL)
    assert seen.index(JobStatus.FETCHING_THERMAL) < seen.index(JobStatus.AGGREGATING_ZONES)
    assert seen.index(JobStatus.AGGREGATING_ZONES) < seen.index(JobStatus.NORMALIZING)
    assert seen.index(JobStatus.NORMALIZING) < seen.index(JobStatus.VALIDATING_HAZARD_SPREAD)
    assert seen.index(JobStatus.VALIDATING_HAZARD_SPREAD) < seen.index(JobStatus.COMPUTING)


def test_missing_reference_fails_closed_as_insufficient_reference(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "absent.jsonl"
    job = _run("2022-06-30", reference_source_path=missing)
    assert job.reference_quality == "INSUFFICIENT_REFERENCE"
    assert job.thermal_differentiation_state == "NOT_EVALUATED"
    assert "INSUFFICIENT_REFERENCE" in job.system_limitations
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" not in job.system_limitations
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is None
    assert job.hazard_spread.differentiation_state == "NOT_EVALUATED"
    assert all(zone.ranked is False for zone in job.zones)
    assert all(zone.q_A is None for zone in job.zones)
    blob = json.dumps(job.model_dump(mode="json"))
    assert "between_zone_hazard_range" not in blob
    assert "REDUCED_REFERENCE" not in blob
    assert "q_B" not in blob


def test_incomplete_reference_fails_closed(tmp_path: Path) -> None:
    incomplete = tmp_path / "incomplete.jsonl"
    incomplete.write_text(
        json.dumps(
            {
                "date": "2022-06-30",
                "year": 2022,
                "local_time": "03:00",
                "geoid": "04013107401",
                "mean_tcm_c": 31.5,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    job = _run("2022-06-30", reference_source_path=incomplete)
    assert job.reference_quality == "INSUFFICIENT_REFERENCE"
    assert job.thermal_differentiation_state == "NOT_EVALUATED"
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" not in job.system_limitations


def test_api_serializations_distinguish_three_reference_states() -> None:
    sufficient = _run("2022-06-30").model_dump(mode="json")
    insufficient = _run("2022-07-01").model_dump(mode="json")
    missing = _run(
        "2022-06-30",
        reference_source_path=Path("this-file-does-not-exist.jsonl"),
    ).model_dump(mode="json")

    assert sufficient["reference_quality"] == "FULL_REFERENCE"
    assert sufficient["thermal_differentiation_state"] == "SUFFICIENT"
    assert sufficient["hazard_spread"]["differentiation_state"] == "SUFFICIENT"
    ref_label = next(
        node["label"]
        for node in sufficient["evidence_graph"]["nodes"]
        if node["id"] == "decision1b_reference"
    )
    assert ref_label == "data/phoenix/reference/observations.jsonl"
    assert all(zone["thermal_ordering_permitted"] is True for zone in sufficient["zones"])

    assert insufficient["reference_quality"] == "FULL_REFERENCE"
    assert insufficient["thermal_differentiation_state"] == "INSUFFICIENT"
    assert "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT" in insufficient["system_limitations"]
    assert all(zone["thermal_ordering_permitted"] is False for zone in insufficient["zones"])
    assert all(zone["q_A"] is not None for zone in insufficient["zones"])

    assert missing["reference_quality"] == "INSUFFICIENT_REFERENCE"
    assert missing["thermal_differentiation_state"] == "NOT_EVALUATED"
    assert "INSUFFICIENT_REFERENCE" in missing["system_limitations"]
    assert missing["hazard_spread"]["observed_spread"] is None

    assert sufficient["thermal_differentiation_state"] != insufficient["thermal_differentiation_state"]
    assert insufficient["reference_quality"] != missing["reference_quality"]
    assert insufficient["system_limitations"] != missing["system_limitations"]


def test_out_of_panel_target_observations_serialize_through_job_path() -> None:
    from app.core.phoenix_v1_area_config import load_frozen_phoenix_v1_area_config
    from app.services.phoenix_v1_reference import load_phoenix_v1_reference_panel
    from app.services.temporal_anomaly import ReferenceObservation

    config = load_frozen_phoenix_v1_area_config()
    panel = load_phoenix_v1_reference_panel(config)
    geoids = sorted({row.geoid for row in panel.observations})
    assert len(geoids) == 25
    target = [
        ReferenceObservation(
            date="2025-07-15",
            year=2025,
            geoid=geoid,
            mean_tcm_c=20.0 + (index * 0.5),
        )
        for index, geoid in enumerate(geoids)
    ]
    from app.services.orchestrator import run_replay_analysis

    job = run_replay_analysis(
        _historical_request("2025-07-15"),
        adapter=_ForbiddenAdapter(),
        target_observations=target,
    )
    dumped = job.model_dump(mode="json")
    assert job.reference_quality == "FULL_REFERENCE"
    assert job.thermal_differentiation_state in {"SUFFICIENT", "INSUFFICIENT"}
    assert job.hazard_spread is not None
    assert job.hazard_spread.observed_spread is not None
    assert len(job.zones) == 25
    assert all(zone.q_A is not None for zone in job.zones)
    assert "q_B" not in json.dumps(dumped)
    assert dumped["hazard_spread"]["input_quantity"] == "q_A"
    _assert_frozen_provenance(job, panel.source_sha256)


def test_phoenix_v1_evaluator_is_the_shared_production_call() -> None:
    source = (
        HACKATHON_ROOT / "apps" / "api" / "app" / "services" / "orchestrator.py"
    ).read_text(encoding="utf-8")
    assert "evaluate_phoenix_v1_timestamp(" in source
    assert "def compute_q_a" not in source
    assert "evaluate_hazard_spread(" not in source


def _assert_frozen_provenance(job, reference_sha: str) -> None:
    dumped = job.model_dump(mode="json")
    blob = json.dumps(dumped)
    assert "unfrozen" not in blob
    assert "unfrozen-demo-fixture" not in blob
    assert job.versions.area_config_version == AREA_CONFIG_VERSION
    assert job.versions.zone_geometry_version == ZONE_GEOMETRY_VERSION
    assert job.versions.hazard_spread_policy_version == DECISION8_POLICY_VERSION
    assert job.area_config_sha256 == EXPECTED_AREA_CONFIG_SHA256
    assert job.reference_source_sha256 == reference_sha
    assert job.hazard_spread is not None
    assert job.hazard_spread.reference_version == REFERENCE_VERSION
    assert job.hazard_spread.policy_version == DECISION8_POLICY_VERSION
    assert job.hazard_spread.zone_geometry_version == ZONE_GEOMETRY_VERSION
    assert job.hazard_spread.input_quantity == "q_A"
    assert job.hazard_spread.metric == "TOP3_BOTTOM3_MEAN_DIFFERENCE"
    assert job.hazard_spread.top_group_size == 3
    assert job.hazard_spread.bottom_group_size == 3
    assert job.hazard_spread.floor == pytest.approx(0.10)
    assert job.hazard_spread.comparison_operator == ">="
    blob_paths = json.dumps(dumped)
    assert "workforce/gate0/decision1b/reference_instance" not in blob_paths
    ref_nodes = [
        node
        for node in (dumped.get("evidence_graph") or {}).get("nodes") or []
        if node.get("id") == "decision1b_reference"
    ]
    assert ref_nodes
    assert ref_nodes[0]["label"] == "data/phoenix/reference/observations.jsonl"
