"""Timezone policy is wired into resolve/materialize. No public route. No vendor."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

from app.core.area_registry import resolve_area_geography
from app.domain.phoenix_v1 import AREA_ID
from app.services.aoi_timezone import PHOENIX_IANA
from app.services.snapshot_identity import require_dst_safe_requested_hour


def test_legacy_phoenix_demo_keeps_america_phoenix() -> None:
    geography = resolve_area_geography(AREA_ID)
    assert geography.manifest.area_id == "phoenix-demo"
    assert geography.timezone == PHOENIX_IANA


def test_dst_safe_hour_rejects_gap_and_fold() -> None:
    gap = datetime(2026, 3, 8, 2, 0)
    fold = datetime(2026, 11, 1, 1, 0)
    try:
        require_dst_safe_requested_hour(gap, "America/New_York")
        raise AssertionError("nonexistent hour must fail closed")
    except ValueError as exc:
        assert "does not exist" in str(exc)
    try:
        require_dst_safe_requested_hour(fold, "America/New_York")
        raise AssertionError("ambiguous hour must fail closed")
    except ValueError as exc:
        assert "ambiguous" in str(exc)


def test_dst_safe_hour_keeps_phoenix_transition_hours() -> None:
    spring = datetime(2026, 3, 8, 2, 0)
    fall = datetime(2026, 11, 1, 1, 0)
    assert require_dst_safe_requested_hour(spring, PHOENIX_IANA) == spring
    assert require_dst_safe_requested_hour(fall, PHOENIX_IANA) == fall


def test_wiring_sources_have_no_phoenix_national_exception() -> None:
    root = Path(__file__).resolve().parents[2] / "app" / "services"
    for name in (
        "place_geography_resolver.py",
        "national_geography_materializer.py",
        "geography_timezone_gate.py",
        "aoi_timezone.py",
    ):
        text = (root / name).read_text(encoding="utf-8")
        assert "if phoenix" not in text.lower()
        assert "/api/v1/" not in text
        imported: set[str] = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert all("fortyguard" not in name.lower() for name in imported)


def test_no_new_public_route_was_added() -> None:
    router = Path(__file__).resolve().parents[2] / "app" / "api" / "router.py"
    text = router.read_text(encoding="utf-8")
    assert "timezone" not in text.lower()
    assert "include_router(jobs_router" in text
    assert "include_router(areas_router" in text
