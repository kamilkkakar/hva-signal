from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.area_registry import resolve_area_geography
from app.domain.phoenix_v1 import AREA_ID

TEMPORAL = Path(__file__).resolve().parents[2] / "fixtures" / "temporal"


def require_synthetic_banner(path: Path) -> dict:
    source = json.loads((path / "SOURCE.json").read_text(encoding="utf-8"))
    assert source["kind"] == "SYNTHETIC_FIXTURE"
    return source


@pytest.fixture
def phoenix_demo_geometry() -> dict:
    resolved = resolve_area_geography(AREA_ID)
    return json.loads(resolved.geometry_body.decode("utf-8"))


@pytest.fixture
def temporal_root() -> Path:
    require_synthetic_banner(TEMPORAL)
    return TEMPORAL
