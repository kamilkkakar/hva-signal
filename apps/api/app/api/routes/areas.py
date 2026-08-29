from app.core.area_registry import list_supported_area_summaries
from fastapi import APIRouter

router = APIRouter()


@router.get("/areas")
def list_areas() -> dict[str, list[dict[str, object]]]:
    return {"areas": [item.model_dump() for item in list_supported_area_summaries()]}
