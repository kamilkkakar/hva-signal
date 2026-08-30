"""Unpublished matched-window GET. Not registered on the public app.

GET never acquires. Compact view only. No FortyGuard HTTP.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.matched_nighttime_window import assemble_matched_nighttime_window_view

router = APIRouter(
    prefix="/internal/v1",
    tags=["matched-nighttime-window-unpublished"],
)


@router.get("/matched-nighttime-window", include_in_schema=False)
def get_matched_nighttime_window(
    geoid: str = Query(default="04013107401"),
    area_id: str = Query(default="phoenix-demo"),
) -> dict:
    try:
        return assemble_matched_nighttime_window_view(geoid, area_id=area_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
