"""Multi-city domain exports (catalog, capabilities, Type-1 live, canopy)."""

from app.domain.multicity.capabilities import negotiate_capabilities
from app.domain.multicity.catalog import get_city, list_cities, public_city_selector_allowlist
from app.domain.multicity.city_catalog import (
    MULTICITY_CITY_CONFIG_VERSION,
    SERVER_OWNED_AOI_POLICY,
    CityAoiConfig,
    resolve_city_aoi,
    supported_multicity_names,
)
from app.domain.multicity.city_config import (
    CapabilityKey,
    CapabilityStatus,
    CityConfig,
    CityId,
    CitySelectorEntry,
)
from app.domain.multicity.cross_city_canopy import (
    CROSS_CITY_CANOPY_CONTRACT_V1,
    CROSS_CITY_CANOPY_STATUS,
    cross_city_canopy_contract,
)
from app.domain.multicity.geography import (
    COMPARABLE_SELECTION_ALGORITHM,
    COMPARABLE_ZONE_TARGET,
    CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
    MULTI_CITY_ANALYSIS_GEOGRAPHY_DOC,
    MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
    PHOENIX_LOCAL_GEOGRAPHY_EXPLICIT,
    PhoenixGeographyAudit,
    audit_phoenix_cross_city_compatibility,
)
from app.domain.multicity.type1_live import (
    ALLOWED_KEY_ALIASES,
    TYPE1_LIVE_CONTRACT_VERSION,
    TYPE1_LIVE_CREDIT_ESTIMATE_VERSION,
    Type1LiveClientRequest,
    build_type1_request,
    dry_run_type1_preflight,
    run_type1_live,
    seed_type1_live_cache,
)
from app.domain.multicity.validation_package import (
    CROSS_CITY_VALIDATION_PACKAGE_V1,
    build_cross_city_validation_package,
    render_cross_city_validation_package_markdown,
)

__all__ = [
    "ALLOWED_KEY_ALIASES",
    "COMPARABLE_SELECTION_ALGORITHM",
    "COMPARABLE_ZONE_TARGET",
    "CROSS_CITY_CANOPY_CONTRACT_V1",
    "CROSS_CITY_CANOPY_STATUS",
    "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
    "CROSS_CITY_VALIDATION_PACKAGE_V1",
    "MULTI_CITY_ANALYSIS_GEOGRAPHY_DOC",
    "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
    "MULTICITY_CITY_CONFIG_VERSION",
    "PHOENIX_LOCAL_GEOGRAPHY_EXPLICIT",
    "SERVER_OWNED_AOI_POLICY",
    "TYPE1_LIVE_CONTRACT_VERSION",
    "TYPE1_LIVE_CREDIT_ESTIMATE_VERSION",
    "CapabilityKey",
    "CapabilityStatus",
    "CityAoiConfig",
    "CityConfig",
    "CityId",
    "CitySelectorEntry",
    "PhoenixGeographyAudit",
    "Type1LiveClientRequest",
    "audit_phoenix_cross_city_compatibility",
    "build_cross_city_validation_package",
    "build_type1_request",
    "cross_city_canopy_contract",
    "dry_run_type1_preflight",
    "get_city",
    "list_cities",
    "negotiate_capabilities",
    "public_city_selector_allowlist",
    "render_cross_city_validation_package_markdown",
    "resolve_city_aoi",
    "run_type1_live",
    "seed_type1_live_cache",
    "supported_multicity_names",
]
