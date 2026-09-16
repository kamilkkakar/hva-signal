"""Authenticated control plane for the frozen Phoenix hourly pilot.

The contract route resolves server-owned identity without side effects. The
canary route is default-closed and, when explicitly enabled, can execute only
through shared durable storage. Both remain absent from public OpenAPI.
"""

from __future__ import annotations

import secrets
from contextlib import suppress
from typing import Any, Final

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    HourlyThermalPilotRegistryError,
    load_phoenix_hourly_thermal_pilot_manifest,
)
from app.core.postgres_acquisition import (
    AcquisitionIdentityMismatch,
    AcquisitionInProgress,
    AcquisitionNeedsRecovery,
    AcquisitionStorageUnavailable,
    PostgresAcquisitionStore,
    store_from_settings,
)
from app.integrations.fortyguard.client import FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import (
    AcquisitionAllowanceExceeded,
    FortyGuardAdapterError,
    MissingApiKeyError,
    TaskFailedError,
    TaskTimeoutError,
)
from app.services.hourly_pilot_acquisition import (
    HourlyPilotAcquisitionError,
    execute_hourly_pilot_canary,
    prepare_hourly_pilot_canary,
)

router = APIRouter(prefix="/internal/v1", tags=["hourly-pilot-internal"])

HOURLY_PILOT_CONTRACT_ROUTE: Final = "/hourly-pilot/slot-contract"
HOURLY_PILOT_EXECUTE_ROUTE: Final = "/hourly-pilot/canary"
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


def _resolved_canary(body: HourlyPilotSlotContractBody):
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
    return resolved, slot, prepared


def _execution_dependencies(
    settings: Settings,
) -> tuple[PostgresAcquisitionStore, FortyGuardHttpClient]:
    store = store_from_settings(settings)
    if store is None:
        raise AcquisitionStorageUnavailable(
            "Shared acquisition storage must be enabled for the hourly pilot."
        )
    if not settings.fortyguard_api_key.strip():
        raise MissingApiKeyError("The hourly pilot vendor credential is not configured.")
    client = FortyGuardHttpClient(
        settings.fortyguard_api_key,
        base_url=settings.fortyguard_base_url,
    )
    return store, client


def _execution_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AcquisitionAllowanceExceeded):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "hourly_pilot_daily_limit",
                "used": exc.used,
                "limit": exc.limit,
            },
        )
    if isinstance(exc, AcquisitionInProgress):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "hourly_pilot_in_progress"},
        )
    if isinstance(exc, AcquisitionNeedsRecovery):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "hourly_pilot_recovery_required"},
        )
    if isinstance(exc, AcquisitionIdentityMismatch):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "hourly_pilot_identity_mismatch"},
        )
    if isinstance(exc, (AcquisitionStorageUnavailable, MissingApiKeyError)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "hourly_pilot_execution_unavailable"},
        )
    if isinstance(exc, TaskTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "hourly_pilot_poll_timeout"},
        )
    if isinstance(exc, TaskFailedError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hourly_pilot_vendor_failed"},
        )
    if isinstance(exc, (FortyGuardAdapterError, httpx.HTTPError)):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hourly_pilot_vendor_communication_interrupted"},
        )
    raise exc


@router.post(HOURLY_PILOT_CONTRACT_ROUTE, include_in_schema=False)
async def post_hourly_pilot_slot_contract(request: Request) -> dict[str, Any]:
    """Resolve one exact frozen slot after authenticating the internal caller."""

    settings = get_settings()
    _authenticate(request, settings)
    body = await _validated_body(request)

    resolved, slot, prepared = _resolved_canary(body)
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


@router.post(HOURLY_PILOT_EXECUTE_ROUTE, include_in_schema=False)
async def post_hourly_pilot_canary(request: Request) -> dict[str, Any]:
    """Execute or recover only the frozen canary through shared durability."""

    settings = get_settings()
    _authenticate(request, settings)
    body = await _validated_body(request)
    resolved, slot, prepared = _resolved_canary(body)

    client: FortyGuardHttpClient | None = None
    try:
        store, client = _execution_dependencies(settings)
        bundled, source = await run_in_threadpool(
            execute_hourly_pilot_canary,
            resolved,
            slot_id=slot.slot_id,
            store=store,
            client=client,
        )
    except Exception as exc:
        raise _execution_error(exc) from None
    finally:
        if client is not None:
            # Cleanup must not replace the bounded execution result or its
            # sanitized error with a transport-specific close failure.
            with suppress(Exception):
                client.close()

    activity_id = bundled.get("activity_id")
    if not isinstance(activity_id, str) or not activity_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hourly_pilot_result_invalid"},
        )
    return {
        "status": "canary_execution_completed",
        "manifest_sha256": resolved.sha256,
        "slot_id": slot.slot_id,
        "request_fingerprint": prepared.request_fingerprint,
        "activity_id": activity_id,
        "acquisition_source": source,
        "vendor_submission_attempted": source == "live",
        "durable_recovery": source == "durable_resume",
        "durable_replay": source == "durable_replay",
        "result_stored": True,
    }
