"""Sibling two-signal job HTTP. Included only when HVA_PUBLIC_TWO_SIGNAL is on."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.two_signal_public import (
    TwoSignalPublicationRequest,
    TwoSignalPublicJob,
    TwoSignalUnknownJob,
)
from app.services.hosted_live_redteam import (
    ClientPrivilegeError,
    reject_client_privilege_surfaces,
)
from app.services.two_signal_jobs import (
    TwoSignalRequestError,
    two_signal_job_service,
)

router = APIRouter()


@router.post(
    "/analysis/two-signal-jobs",
    status_code=status.HTTP_202_ACCEPTED,
)
def create_two_signal_job(
    payload: TwoSignalPublicationRequest,
    request: Request,
) -> dict[str, Any]:
    try:
        reject_client_privilege_surfaces(
            query=dict(request.query_params),
            headers=dict(request.headers),
        )
    except ClientPrivilegeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    try:
        job = two_signal_job_service.create(payload)
    except TwoSignalRequestError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return job.model_dump(mode="json")


@router.get("/analysis/two-signal-jobs/{job_id}")
def get_two_signal_job(job_id: str) -> dict[str, Any]:
    document = two_signal_job_service.get(job_id)
    return document.model_dump(mode="json")


__all__ = [
    "create_two_signal_job",
    "get_two_signal_job",
    "router",
    "TwoSignalPublicJob",
    "TwoSignalUnknownJob",
]
