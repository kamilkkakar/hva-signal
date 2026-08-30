"""Gated include for cache-only temporal story GETs. Default ON.

Does not enable hosted live or FortyGuard HTTP. GET never acquires.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import Settings, get_settings


def public_temporal_stories_enabled(settings: Settings | None = None) -> bool:
    current = settings if settings is not None else get_settings()
    return bool(getattr(current, "hva_public_temporal_stories", False))


def include_public_temporal_story_routes(
    api_router: APIRouter,
    *,
    settings: Settings | None = None,
    enabled: bool | None = None,
) -> None:
    on = (
        public_temporal_stories_enabled(settings)
        if enabled is None
        else bool(enabled)
    )
    if not on:
        return
    from app.api.routes.temporal_stories_demo import router as demo_router

    api_router.include_router(demo_router, prefix="/api/v1")
