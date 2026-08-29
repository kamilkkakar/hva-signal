from fastapi import APIRouter

from app.api.routes.analysis_jobs import router as jobs_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(jobs_router, prefix="/api/v1")


def include_health_routes(app) -> None:
    app.include_router(health_router)
