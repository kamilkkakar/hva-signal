from app.core.area_registry import (
    UnsupportedAreaError,
    list_supported_area_summaries,
    load_verified_area_geometry,
)
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()


@router.get("/areas")
def list_areas() -> dict[str, list[dict[str, object]]]:
    return {"areas": [item.model_dump() for item in list_supported_area_summaries()]}


@router.get("/areas/{area_id}/geometry")
def get_area_geometry(area_id: str) -> Response:
    try:
        geometry = load_verified_area_geometry(area_id)
    except UnsupportedAreaError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=geometry.body,
        media_type="application/geo+json",
        headers={
            "X-HVA-Area-ID": geometry.area_id,
            "X-HVA-Zone-Geometry-Version": geometry.zone_geometry_version,
            "X-HVA-Geometry-SHA256": geometry.sha256,
            "ETag": f'"{geometry.sha256}"',
        },
    )
