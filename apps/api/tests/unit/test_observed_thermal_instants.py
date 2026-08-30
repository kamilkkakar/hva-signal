"""Explicit Prompt-15 P14 tests for four observed thermal instants."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.observed_thermal_instants import (
    ACTIVITY_1500,
    ACTIVITY_2100,
    assemble_observed_thermal_sequence,
)
from app.main import app as public_app

SEED = "04013107401"
APP = Path(__file__).resolve().parents[2] / "app"
REPO = Path(__file__).resolve().parents[4]


def _client() -> TestClient:
    from app.api.routes.observed_thermal_instants import router

    application = FastAPI()
    application.include_router(router)
    return TestClient(application)


def test_1500_activity_id_exactly() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    instant = next(item for item in seq.observations if item.instant_id == "15:00")
    assert instant.activity_id == "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
    assert instant.activity_id == ACTIVITY_1500


def test_2100_activity_id_exactly() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    instant = next(item for item in seq.observations if item.instant_id == "21:00")
    assert instant.activity_id == "9865bd33-43a0-42b0-bc9b-74b27510002d"
    assert instant.activity_id == ACTIVITY_2100


def test_1500_is_25_of_25() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    instant = next(item for item in seq.observations if item.instant_id == "15:00")
    assert instant.coverage.valid_zone_count == 25
    assert instant.coverage.expected_zone_count == 25
    assert instant.coverage.label == "25/25"


def test_2100_is_25_of_25() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    instant = next(item for item in seq.observations if item.instant_id == "21:00")
    assert instant.coverage.valid_zone_count == 25
    assert instant.coverage.expected_zone_count == 25
    assert instant.coverage.label == "25/25"


def test_held_0300_d_not_reacquired() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    instant = next(item for item in seq.observations if item.instant_id == "03:00_D")
    assert instant.date == "2024-07-08"
    assert instant.local_time == "03:00"
    assert instant.activity_id is None
    assert instant.observation_status == "held_not_reacquired"
    assert instant.source_mode == "replay"
    assert instant.coverage.label == "25/25"


def test_held_0300_d_plus_1_not_reacquired() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    instant = next(item for item in seq.observations if item.instant_id == "03:00_D+1")
    assert instant.date == "2024-07-09"
    assert instant.local_time == "03:00"
    assert instant.activity_id is None
    assert instant.observation_status == "held_not_reacquired"
    assert instant.source_mode == "replay"
    assert instant.coverage.label == "25/25"


def test_ordering_is_d_then_1500_then_2100_then_d_plus_1() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    assert tuple(item.instant_id for item in seq.observations) == (
        "03:00_D",
        "15:00",
        "21:00",
        "03:00_D+1",
    )


def test_d_versus_d_plus_1_are_correctly_labeled() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    by_id = {item.instant_id: item for item in seq.observations}
    assert by_id["03:00_D"].label == "03:00 D"
    assert by_id["03:00_D+1"].label == "03:00 D+1"
    assert by_id["03:00_D"].date != by_id["03:00_D+1"].date


def test_no_interpolation_or_forbidden_claims() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    blob = json.dumps(seq.as_dict())
    assert len(seq.observations) == 4
    assert len(seq.direct_differences) == 3
    assert "No interpolation" in seq.method_note
    assert "cooling rate" in seq.not_claims
    assert "24-hour profile" in seq.not_claims
    assert "AfterHeat" in seq.not_claims
    assert "q_A" in seq.not_claims
    assert "workforce/" not in blob
    assert seq.method_note.startswith("TEMPERATURE DIFFERENCE BETWEEN OBSERVED INSTANTS")
    hours = [item.local_time for item in seq.observations]
    assert hours == ["03:00", "15:00", "21:00", "03:00"]
    assert "16:00" not in blob and "17:00" not in blob


def test_no_q_a_at_1500_or_2100() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    dumped = seq.as_dict()
    for instant in dumped["observations"]:
        if instant["instant_id"] in {"15:00", "21:00"}:
            assert "q_A" not in instant
            assert instant["temperature_c"] is not None


def test_seed_zone_matches_prompt15_example() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    by_id = {item.instant_id: item for item in seq.observations}
    assert by_id["03:00_D"].temperature_c == pytest.approx(34.520, abs=0.01)
    assert by_id["15:00"].temperature_c == pytest.approx(42.328, abs=0.01)
    assert by_id["21:00"].temperature_c == pytest.approx(39.256, abs=0.01)
    assert by_id["03:00_D+1"].temperature_c == pytest.approx(34.676, abs=0.01)
    diffs = {item.to_instant_id: item.delta_c for item in seq.direct_differences}
    assert diffs["15:00"] == pytest.approx(7.808, abs=0.01)
    assert diffs["21:00"] == pytest.approx(-3.072, abs=0.01)
    assert diffs["03:00_D+1"] == pytest.approx(-4.581, abs=0.01)


def test_provider_provenance_remains_recoverable() -> None:
    seq = assemble_observed_thermal_sequence(SEED)
    assert seq.geometry_sha256.startswith("3f16870f")
    assert seq.snapshot_fingerprints["15:00"]
    assert seq.snapshot_fingerprints["21:00"]
    assert (REPO / "data/phoenix/snapshots/2024-07-08T15-00.snapshot.json").is_file()
    assert (REPO / "data/phoenix/snapshots/2024-07-08T21-00.snapshot.json").is_file()
    assert (REPO / "data/phoenix/reference/four_instant_differences_2024-07-08.json").is_file()


def test_production_app_does_not_import_workforce() -> None:
    offenders: list[str] = []
    for path in APP.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "workforce" or alias.name.startswith("workforce."):
                        offenders.append(f"{path.as_posix()}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "workforce" or node.module.startswith("workforce."):
                    offenders.append(f"{path.as_posix()}: from {node.module}")
    assert offenders == []


def test_public_app_does_not_mount_observed_instants() -> None:
    response = TestClient(public_app).get(
        "/internal/v1/observed-thermal-instants",
        params={"geoid": SEED},
    )
    assert response.status_code == 404


def test_internal_get_returns_four_instants() -> None:
    response = _client().get(
        "/internal/v1/observed-thermal-instants",
        params={"area_id": "phoenix-demo", "geoid": SEED},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["unpublished"] is True
    assert body["not_signal_a"] is True
    assert [item["instant_id"] for item in body["observations"]] == [
        "03:00_D",
        "15:00",
        "21:00",
        "03:00_D+1",
    ]
    assert "spend" not in body
    assert "acquire" not in body
