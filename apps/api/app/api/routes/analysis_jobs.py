from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.core.anonymous_guards import strip_denied_public_fields
from app.core.jobs import job_store, process_analysis_job
from app.domain import AnalysisRequest
from app.services.hosted_live_redteam import (
    ClientPrivilegeError,
    reject_client_privilege_surfaces,
)

router = APIRouter()


def _job_payload(job: Any) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "request": strip_denied_public_fields(job.request),
        "created_at": job.created_at.isoformat(),
        "recoverable": job.recoverable,
        "message": job.message,
        "result": job.result,
    }


@router.post("/analysis/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_analysis_job(
    payload: AnalysisRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    try:
        body = payload.model_dump(mode="json")
        reject_client_privilege_surfaces(
            body=body,
            query=dict(request.query_params),
            headers=dict(request.headers),
        )
    except ClientPrivilegeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    job = job_store.create(body)
    snapshot = _job_payload(job)
    background_tasks.add_task(process_analysis_job, job.job_id)
    return snapshot


@router.get("/analysis/jobs/{job_id}")
def get_analysis_job(job_id: str) -> dict[str, Any]:
    job = job_store.get(job_id)
    if job is None:
        return {
            "job_id": job_id,
            "status": "unknown_job",
            "recoverable": True,
            "message": "The analysis job is no longer present on this runtime.",
        }
    return _job_payload(job)
