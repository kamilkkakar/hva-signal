"""Gated demo GETs for temporal stories. Cache/read-only. No acquire."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.matched_nighttime_window import assemble_matched_nighttime_window_view
from app.services.observed_thermal_instants import load_observed_thermal_sequence

router = APIRouter()


@router.get("/demo/matched-nighttime-window")
def get_demo_matched_nighttime_window(
    geoid: str = Query(default="04013107401"),
    area_id: str = Query(default="phoenix-demo"),
) -> dict:
    try:
        return assemble_matched_nighttime_window_view(geoid, area_id=area_id)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/demo/observed-thermal-instants")
def get_demo_observed_thermal_instants(
    geoid: str = Query(default="04013107401"),
    area_id: str = Query(default="phoenix-demo"),
) -> dict:
    try:
        return load_observed_thermal_sequence(geoid, area_id=area_id).as_dict()
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
