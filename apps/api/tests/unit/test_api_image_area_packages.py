"""API image must ship tracked area packages. No ignored local trees."""

from __future__ import annotations

from app.core.phoenix_v1_area_config import hackathon_root


def test_dockerfile_copies_tracked_area_packages() -> None:
    dockerfile = (hackathon_root() / "apps" / "api" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY data/demo/phoenix" in dockerfile
    assert "COPY data/phoenix/reference" in dockerfile
    assert "COPY data/areas" in dockerfile
    assert "workforce" not in dockerfile
