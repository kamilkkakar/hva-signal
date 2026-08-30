"""Unpublished Place catalog routes. Gazetteer identity only.

Mounted only when HVA_PUBLIC_GEOGRAPHY is enabled. Search never starts resolve.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.public_geography import GeographyReasonCode
from app.services.geography_jobs import error_http, get_place, search_places

router = APIRouter()


def _as_response(result) -> JSONResponse:
    return JSONResponse(
        status_code=result.status_code,
        content=result.body,
        headers=result.headers,
    )


@router.get("/places")
def search_census_places(
    q: str | None = Query(default=None),
    limit: int = Query(default=10),
) -> JSONResponse:
    if q is None:
        return _as_response(
            error_http(
                422,
                GeographyReasonCode.INVALID_PLACE_GEOID,
                "Query q must be a Census Place name, Name, ST, or 7-digit GEOID.",
            )
        )
    return _as_response(search_places(q, limit=limit))


@router.get("/places/{place_geoid}")
def get_census_place(place_geoid: str) -> JSONResponse:
    return _as_response(get_place(place_geoid))
