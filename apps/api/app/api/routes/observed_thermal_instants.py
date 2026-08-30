"""Unpublished observed-instant GET. Not registered on the public app.

GET never acquires. Four named instants only. No FortyGuard HTTP.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.observed_thermal_instants import load_observed_thermal_sequence

router = APIRouter(
    prefix="/internal/v1",
    tags=["observed-thermal-instants-unpublished"],
)


@router.get("/observed-thermal-instants", include_in_schema=False)
def get_observed_thermal_instants(
    geoid: str = Query(default="04013107401"),
    area_id: str = Query(default="phoenix-demo"),
) -> dict:
    try:
        return load_observed_thermal_sequence(geoid, area_id=area_id).as_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
