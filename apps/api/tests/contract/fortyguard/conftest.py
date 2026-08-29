from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "fortyguard"
HOURLY_TCM_FIXTURE = FIXTURE_DIR / "heatmap_tcm_hourly_1500.json"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def hourly_tcm_fixture() -> dict:
    if not HOURLY_TCM_FIXTURE.is_file():
        pytest.fail(f"Missing sanitized fixture: {HOURLY_TCM_FIXTURE}")
    return json.loads(HOURLY_TCM_FIXTURE.read_text(encoding="utf-8"))
