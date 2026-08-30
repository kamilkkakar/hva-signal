"""Gated include for the unpublished two-signal sibling. Default off."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.core.config import Settings, get_settings

AppRouter = APIRouter | FastAPI


def public_two_signal_enabled(settings: Settings | None = None) -> bool:
    current = settings if settings is not None else get_settings()
    return bool(getattr(current, "hva_public_two_signal", False))


def include_optional_two_signal_routes(
    api_router: AppRouter,
    *,
    settings: Settings | None = None,
    enabled: bool | None = None,
    prefix: str = "/api/v1",
) -> None:
    """Attach POST/GET ``/analysis/two-signal-jobs`` only when the flag is on."""
    on = public_two_signal_enabled(settings) if enabled is None else bool(enabled)
    if not on:
        return
    from app.api.routes.two_signal_jobs import router as two_signal_router

    api_router.include_router(two_signal_router, prefix=prefix)
