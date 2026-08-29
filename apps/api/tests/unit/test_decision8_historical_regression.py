"""Production-path regression against the frozen Decision 8 audit oracle.

The audit CSV is the expected-values source. The production q_A + Decision 8
path is the system under test. The audit script is not imported.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from app.services.phoenix_v1_thermal import (
    evaluate_phoenix_v1_timestamp,
    observations_from_jsonl_rows,
)
from app.services.temporal_anomaly import evaluate_reference_quality

HACKATHON_ROOT = Path(__file__).resolve().parents[4]
OBS_PATH = (
    HACKATHON_ROOT
    / "data"
    / "phoenix"
    / "reference"
    / "observations.jsonl"
)
ORACLE_CSV = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "decision8"
    / "decision8_policy_impact_by_timestamp.csv"
)


def test_production_path_matches_frozen_decision8_audit_oracle() -> None:
    assert OBS_PATH.is_file(), f"missing reference panel {OBS_PATH}"
    assert ORACLE_CSV.is_file(), f"missing audit oracle {ORACLE_CSV}"

    raw_rows = [
        json.loads(line)
        for line in OBS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    observations = observations_from_jsonl_rows(raw_rows)
    quality = evaluate_reference_quality(observations)
    assert quality.quality == "FULL_REFERENCE"

    oracle = {}
    with ORACLE_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            oracle[row["date"]] = row

    mismatches: list[dict] = []
    sufficient = 0
    insufficient = 0
    dates = sorted(oracle)
    assert len(dates) == 93

    for day in dates:
        evaluation = evaluate_phoenix_v1_timestamp(day, observations)
        expected_s = float(oracle[day]["normalized_hazard_spread"])
        expected_state = oracle[day]["result"]
        actual_s = evaluation.observed_spread
        actual_state = evaluation.differentiation_state
        if actual_state == "SUFFICIENT":
            sufficient += 1
        elif actual_state == "INSUFFICIENT":
            insufficient += 1
        if actual_s is None or abs(actual_s - expected_s) > 1e-12 or actual_state != expected_state:
            mismatches.append(
                {
                    "date": day,
                    "expected_s": expected_s,
                    "actual_s": actual_s,
                    "expected_state": expected_state,
                    "actual_state": actual_state,
                }
            )

    if mismatches:
        pytest.fail(
            "production Decision 8 path diverged from frozen audit oracle: "
            + json.dumps(mismatches[:5])
        )
    assert sufficient == 25
    assert insufficient == 68
    assert sufficient + insufficient == 93
