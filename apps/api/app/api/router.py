from fastapi import APIRouter

from app.api.optional_context_router import include_public_context_routes
from app.api.optional_geography_router import include_public_geography_routes
from app.api.optional_temporal_stories_router import include_public_temporal_story_routes
from app.api.optional_two_signal_router import include_optional_two_signal_routes
from app.api.routes.analysis_jobs import router as jobs_router
from app.api.routes.areas import router as areas_router
from app.api.routes.bounded_selected_time_live import router as bounded_live_router
from app.api.routes.health import router as health_router
from app.api.routes.multicity import router as multicity_router

api_router = APIRouter()
api_router.include_router(jobs_router, prefix="/api/v1")
api_router.include_router(areas_router, prefix="/api/v1")
api_router.include_router(multicity_router, prefix="/api/v1")
api_router.include_router(bounded_live_router, prefix="/api/v1")
include_public_geography_routes(api_router)
include_public_context_routes(api_router)
include_optional_two_signal_routes(api_router)
include_public_temporal_story_routes(api_router)


def include_health_routes(app) -> None:
    app.include_router(health_router)
