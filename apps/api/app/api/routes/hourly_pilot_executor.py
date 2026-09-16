"""Authenticated control plane for the frozen Phoenix hourly pilot.

This first slice resolves a server-owned manifest slot only. It performs no
vendor I/O, creates no reservation, and is intentionally absent from public
OpenAPI. Later execution must retain these authentication and identity guards.
"""

from __future__ import annotations

import secrets
from typing import Any, Final

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.core.config import Settings, get_settings
from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    HourlyThermalPilotRegistryError,
    load_phoenix_hourly_thermal_pilot_manifest,
)
from app.services.hourly_pilot_acquisition import (
    HourlyPilotAcquisitionError,
    prepare_hourly_pilot_canary,
)

router = APIRouter(prefix="/internal/v1", tags=["hourly-pilot-internal"])

HOURLY_PILOT_CONTRACT_ROUTE: Final = "/hourly-pilot/slot-contract"
HOURLY_PILOT_CREDENTIAL_HEADER: Final = "X-HVA-Pilot-Executor"


class HourlyPilotSlotContractBody(BaseModel):
    """Caller confirmation only; request geometry and parameters stay server-owned."""

    model_config = ConfigDict(extra="forbid")

    manifest_sha256: str
    slot_id: str

    @field_validator("manifest_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("manifest_sha256 must be a lowercase SHA-256 digest")
        return value

    @field_validator("slot_id")
    @classmethod
    def _bounded_slot_id(cls, value: str) -> str:
        if not value or len(value) > 32:
            raise ValueError("slot_id is invalid")
        return value


def _authenticate(request: Request, settings: Settings) -> None:
    if not settings.hourly_pilot_executor_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "hourly_pilot_executor_disabled"},
        )
    configured = settings.hourly_pilot_executor_credential
    supplied = request.headers.get(HOURLY_PILOT_CREDENTIAL_HEADER, "")
    if not configured or not supplied or not secrets.compare_digest(supplied, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "hourly_pilot_authentication_failed"},
        )


async def _validated_body(request: Request) -> HourlyPilotSlotContractBody:
    try:
        payload: Any = await request.json()
        return HourlyPilotSlotContractBody.model_validate(payload)
    except (ValueError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_hourly_pilot_slot_contract"},
        ) from None


@router.post(HOURLY_PILOT_CONTRACT_ROUTE, include_in_schema=False)
async def post_hourly_pilot_slot_contract(request: Request) -> dict[str, Any]:
    """Resolve one exact frozen slot after authenticating the internal caller."""

    settings = get_settings()
    _authenticate(request, settings)
    body = await _validated_body(request)

    try:
        resolved = load_phoenix_hourly_thermal_pilot_manifest()
    except HourlyThermalPilotRegistryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "hourly_pilot_manifest_unavailable"},
        ) from exc
    if body.manifest_sha256 != resolved.sha256:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "hourly_pilot_manifest_mismatch",
                "expected_manifest_sha256": resolved.sha256,
            },
        )

    slot = next(
        (candidate for candidate in resolved.manifest.slots if candidate.slot_id == body.slot_id),
        None,
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "hourly_pilot_slot_not_found"},
        )
    try:
        prepared = prepare_hourly_pilot_canary(resolved, slot.slot_id)
    except HourlyPilotAcquisitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "hourly_pilot_canary_required"},
        ) from exc
    return {
        "status": "slot_contract_verified",
        "manifest_sha256": resolved.sha256,
        "manifest_version": resolved.manifest.manifest_version,
        "slot_id": slot.slot_id,
        "phase": slot.phase,
        "ordinal": slot.ordinal,
        "request_fingerprint": prepared.request_fingerprint,
        "canary_slot_id": CANARY_SLOT_ID,
        "vendor_attempted": False,
        "reservation_created": False,
    }
