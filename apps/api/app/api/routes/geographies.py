"""Unpublished Geography create-or-join + poll.

Mounted only when HVA_PUBLIC_GEOGRAPHY is enabled.
POST is the only write. GET never starts resolve. Zero vendor.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import JSONResponse, Response

from app.schemas.public_geography import (
    FROZEN_CENSUS_VINTAGE,
    FROZEN_RESOLVER_POLICY_ID,
    GeographyReasonCode,
    GeographyResolveRequest,
    PUBLIC_GEOGRAPHY_CONTRACT_VERSION,
)
from app.services.geography_jobs import (
    create_or_join,
    error_http,
    get_geography,
    get_geography_geometry,
    run_geography_worker,
)

router = APIRouter()


def _as_response(result) -> JSONResponse:
    return JSONResponse(
        status_code=result.status_code,
        content=result.body,
        headers=result.headers,
    )


def _validate_body(payload: Any):
    if not isinstance(payload, dict):
        return error_http(
            422,
            GeographyReasonCode.FORBIDDEN_FIELD,
            "Request body must be a JSON object.",
        )
    extras = sorted(
        set(payload)
        - {"contract_version", "place_geoid", "census_vintage", "resolver_policy_id"}
    )
    if extras:
        return error_http(
            422,
            GeographyReasonCode.FORBIDDEN_FIELD,
            f"Forbidden or unknown field(s): {', '.join(extras)}.",
        )
    version = payload.get("contract_version")
    if version != PUBLIC_GEOGRAPHY_CONTRACT_VERSION:
        return error_http(
            422,
            GeographyReasonCode.CONTRACT_VERSION_MISMATCH,
            "contract_version must be hva-signal-public-geography-v1.",
        )
    if "census_vintage" in payload and payload["census_vintage"] != FROZEN_CENSUS_VINTAGE:
        return error_http(
            422,
            GeographyReasonCode.VINTAGE_MISMATCH,
            "census_vintage must equal 2025.",
        )
    if (
        "resolver_policy_id" in payload
        and payload["resolver_policy_id"] != FROZEN_RESOLVER_POLICY_ID
    ):
        return error_http(
            422,
            GeographyReasonCode.UNSUPPORTED_POLICY,
            "resolver_policy_id must equal NATIONAL_PLACE_GEOGRAPHY_V1.",
        )
    try:
        return GeographyResolveRequest.model_validate(payload)
    except Exception:
        return error_http(
            422,
            GeographyReasonCode.INVALID_PLACE_GEOID,
            "place_geoid must be the 7-digit Census place identifier.",
        )


@router.post("/geographies")
async def create_or_join_geography(
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return _as_response(
            error_http(
                422,
                GeographyReasonCode.FORBIDDEN_FIELD,
                "Request body must be JSON.",
            )
        )
    parsed = _validate_body(payload)
    if not isinstance(parsed, GeographyResolveRequest):
        return _as_response(parsed)
    return _as_response(
        create_or_join(
            parsed.place_geoid,
            enqueue=lambda fingerprint: background_tasks.add_task(
                run_geography_worker, fingerprint
            ),
        )
    )


@router.get("/geographies/{area_id}")
def poll_geography(
    area_id: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
) -> Response:
    result = get_geography(area_id, if_none_match=if_none_match)
    if result.status_code == 304:
        return Response(status_code=304, headers=result.headers)
    return _as_response(result)


@router.get("/geographies/{area_id}/geometry")
def geography_geometry(area_id: str) -> Response:
    result = get_geography_geometry(area_id)
    if result.status_code == 200:
        return Response(
            content=json.dumps(result.body),
            status_code=200,
            media_type="application/geo+json",
            headers={
                key: value
                for key, value in result.headers.items()
                if key.lower() != "content-type"
            },
        )
    return _as_response(result)
