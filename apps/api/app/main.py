from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, include_health_routes
from app.core.config import get_settings
from app.core.public_safety_middleware import PublicSafetyMiddleware

settings = get_settings()


def _is_loopback_origin(origin: str) -> bool:
    lowered = origin.lower()
    return (
        "://localhost" in lowered
        or "://127.0.0.1" in lowered
        or "://[::1]" in lowered
    )


def cors_origins_for(settings_obj) -> list[str]:
    origins = [
        origin.strip()
        for origin in settings_obj.allowed_origins.split(",")
        if origin.strip()
    ]
    web = settings_obj.web_public_url.strip()
    production = settings_obj.app_env.lower() == "production"
    if web and not (production and _is_loopback_origin(web)) and web not in origins:
        origins.append(web)
    if production:
        origins = [origin for origin in origins if not _is_loopback_origin(origin)]
    elif not origins:
        origins = ["http://localhost:5173"]
    return origins


app = FastAPI(
    title="HVA-Signal API",
    description=(
        "3K Labs — HVA-Signal (Heat, Vulnerability & Action Signal). "
        "Heat plus Action framing: measure the thermal field and authorize "
        "or withhold. Vulnerability is not scored."
    ),
    version="0.1.0",
)

origins = cors_origins_for(settings)
# Public safety is inner: CORS stays outermost for preflight.
app.add_middleware(PublicSafetyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

include_health_routes(app)
app.include_router(api_router)
