"""Internal temporal routers. NOT registered on the public app / OpenAPI.

Do not import this module from app.api.router or app.main.
GET never acquires. No spend fields.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.temporal_assemble import ASSEMBLE_FROM, AssembleAcquireError

# Isolated router — include_router is the caller's responsibility and must not
# happen on the default public application this wave.
router = APIRouter(prefix="/internal/v1/temporal", tags=["temporal-internal-unpublished"])


class AssembleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assemble_from: str = Field(default=ASSEMBLE_FROM)
    document_kind: str
    document_id: str | None = None


class AssembleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: str
    publication_status: str = "UNPUBLISHED"
    document_id: str | None = None


@router.post("/documents:assemble", include_in_schema=False)
def assemble_document(body: AssembleRequest) -> AssembleResponse:
    if body.assemble_from != ASSEMBLE_FROM:
        raise HTTPException(status_code=400, detail="assemble_from must be held_only")
    return AssembleResponse(availability="NOT_PREPARED", document_id=body.document_id)


@router.get("/catalog", include_in_schema=False)
def catalog() -> dict:
    return {"publication_status": "UNPUBLISHED", "documents": []}


def refuse_acquire() -> None:
    raise AssembleAcquireError("GET never acquires")
