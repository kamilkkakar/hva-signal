"""Gated include for analysis-area context. RC-v2 default ON.

Live OpenAPI includes GET /areas/{area_id}/context unless HVA_PUBLIC_CONTEXT
is an explicit falsy value (0/false/no/off). Fail-closed: phoenix-demo
cache only. No acquire. No score.
"""

from __future__ import annotations

import os

from fastapi import APIRouter


def public_context_enabled() -> bool:
    raw = os.environ.get("HVA_PUBLIC_CONTEXT")
    if raw is not None and raw.strip() != "":
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    from app.core.config import get_settings

    return bool(get_settings().hva_public_context)


def include_public_context_routes(api_router: APIRouter) -> None:
    if not public_context_enabled():
        return
    from app.api.routes.area_context import router as context_router

    api_router.include_router(context_router, prefix="/api/v1")
