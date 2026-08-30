"""Gated include hook for unpublished Place + Geography routes.

Default OFF. Live OpenAPI stays the six P1 paths unless HVA_PUBLIC_GEOGRAPHY
is an explicit truthy value (1/true/yes/on).
"""

from __future__ import annotations

import os

from fastapi import APIRouter


def public_geography_enabled() -> bool:
    raw = os.environ.get("HVA_PUBLIC_GEOGRAPHY", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def include_public_geography_routes(api_router: APIRouter) -> None:
    if not public_geography_enabled():
        return
    from app.api.routes.geographies import router as geographies_router
    from app.api.routes.places import router as places_router

    api_router.include_router(places_router, prefix="/api/v1")
    api_router.include_router(geographies_router, prefix="/api/v1")
