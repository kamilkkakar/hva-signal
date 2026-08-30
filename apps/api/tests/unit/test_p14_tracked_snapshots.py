"""Tracked Prompt-14 compact snapshots. Activity IDs and 25/25 coverage only."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
SNAP_1500 = REPO / "data" / "phoenix" / "snapshots" / "2024-07-08T15-00.snapshot.json"
SNAP_2100 = REPO / "data" / "phoenix" / "snapshots" / "2024-07-08T21-00.snapshot.json"
DIFFS = REPO / "data" / "phoenix" / "reference" / "four_instant_differences_2024-07-08.json"
OBS = REPO / "data" / "phoenix" / "reference" / "observations.jsonl"
APP = REPO / "apps" / "api" / "app"

ACTIVITY_1500 = "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
ACTIVITY_2100 = "9865bd33-43a0-42b0-bc9b-74b27510002d"
GEOMETRY_SHA = "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_compact_snapshot(
    doc: dict,
    *,
    activity_id: str,
    local_ts: str,
    min_c: float,
    max_c: float,
) -> None:
    assert doc["activity_id"] == activity_id
    assert doc["expected_zone_count"] == 25
    assert doc["valid_zone_count"] == 25
    assert doc["missing_zone_ids"] == []
    assert len(doc["zones"]) == 25
    assert len({row["zone_id"] for row in doc["zones"]}) == 25
    assert all(row["coverage_status"] == "ok" for row in doc["zones"])
    assert all(row["mean_temperature_c"] is not None for row in doc["zones"])
    temps = [float(row["mean_temperature_c"]) for row in doc["zones"]]
    assert min(temps) == pytest.approx(min_c, abs=0.001)
    assert max(temps) == pytest.approx(max_c, abs=0.001)
    assert doc["source"] == "fortyguard_cached"
    assert doc["data_status"] == "cached"
    assert doc["timezone"] == "America/Phoenix"
    assert doc["target_timestamp_local"] == local_ts
    assert doc["geometry_sha256"] == GEOMETRY_SHA
    assert doc["geometry_sha256"].startswith("3f16870f")
    blob = json.dumps(doc)
    assert "q_A" not in blob
    assert "workforce/" not in blob
    assert "api_key" not in blob.lower()
    assert "Authorization" not in blob


def test_1500_activity_id_and_25_of_25_coverage() -> None:
    doc = _load(SNAP_1500)
    _assert_compact_snapshot(
        doc,
        activity_id=ACTIVITY_1500,
        local_ts="2024-07-08T15:00:00",
        min_c=42.31165846153846,
        max_c=42.420428125,
    )


def test_2100_activity_id_and_25_of_25_coverage() -> None:
    doc = _load(SNAP_2100)
    _assert_compact_snapshot(
        doc,
        activity_id=ACTIVITY_2100,
        local_ts="2024-07-08T21:00:00",
        min_c=38.96946484375,
        max_c=39.353381,
    )


def test_four_instant_differences_are_complete_25() -> None:
    doc = _load(DIFFS)
    assert doc["complete_25"] is True
    assert doc["n"] == 25
    assert len(doc["zones"]) == 25
    assert doc["activity_ids"]["2024-07-08T15:00"] == ACTIVITY_1500
    assert doc["activity_ids"]["2024-07-08T21:00"] == ACTIVITY_2100
    assert doc["source"] == "fortyguard_cached"
    assert "cooling rate" in doc["not"]
    blob = json.dumps(doc)
    assert "q_A" not in blob
    assert "workforce/" not in blob


def test_observations_jsonl_stays_03_00_only() -> None:
    text = OBS.read_text(encoding="utf-8")
    assert ACTIVITY_1500 not in text
    assert ACTIVITY_2100 not in text
    times = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        times.add(row["local_time"])
    assert times == {"03:00"}


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
