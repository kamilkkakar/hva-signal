"""Gated include for unpublished analysis-area context. Default OFF.

Live OpenAPI stays the six P1 paths unless HVA_PUBLIC_CONTEXT is an
explicit truthy value (1/true/yes/on).
"""

from __future__ import annotations

import os

from fastapi import APIRouter


def public_context_enabled() -> bool:
    raw = os.environ.get("HVA_PUBLIC_CONTEXT", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def include_public_context_routes(api_router: APIRouter) -> None:
    if not public_context_enabled():
        return
    from app.api.routes.area_context import router as context_router

    api_router.include_router(context_router, prefix="/api/v1")
