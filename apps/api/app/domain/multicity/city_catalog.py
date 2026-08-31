"""Server-owned city AOIs for the multicity explorer.

Provisional whole-city bbox polygons are retired. Type-1 request geometry is the
dissolved CROSS_CITY_COMPARISON_GEOGRAPHY_V1 analysis-union per city.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from app.domain.multicity.geography import (
    CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
    MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
)

MULTICITY_CITY_CONFIG_VERSION: Final = "MULTICITY_CITY_CONFIG_V1"
SERVER_OWNED_AOI_POLICY: Final = "SERVER_OWNED_MULTICITY_AOI_V1"


def _repo_root() -> Path:
    # apps/api/app/domain/multicity/city_catalog.py → repo root
    return Path(__file__).resolve().parents[5]


@dataclass(frozen=True, slots=True)
class CityAoiConfig:
    city: str
    slug: str
    timezone: str
    city_config_version: str
    analysis_geography_version: str
    comparison_geography_version: str
    polygon_aoi: dict[str, object]
    aoi_policy_version: str = SERVER_OWNED_AOI_POLICY
    freeze_path: str | None = None


def _load_provider_aoi(city_id: str) -> tuple[dict[str, object], str]:
    root = _repo_root()
    freeze_rel = f"data/areas/cross-city/{city_id}/freeze.json"
    aoi_rel = f"data/areas/cross-city/{city_id}/provider_polygon_aoi.geojson"
    aoi_path = root / aoi_rel
    if not aoi_path.is_file():
        raise FileNotFoundError(
            f"cross-city provider AOI missing for {city_id}: {aoi_rel}"
        )
    polygon = json.loads(aoi_path.read_text(encoding="utf-8"))
    if polygon.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"provider AOI for {city_id} must be Polygon/MultiPolygon")
    return polygon, freeze_rel


@lru_cache(maxsize=1)
def _city_configs() -> dict[str, CityAoiConfig]:
    phoenix_aoi, phoenix_freeze = _load_provider_aoi("phoenix")
    vegas_aoi, vegas_freeze = _load_provider_aoi("las_vegas")
    tucson_aoi, tucson_freeze = _load_provider_aoi("tucson")
    la_aoi, la_freeze = _load_provider_aoi("los_angeles")
    return {
        "phoenix": CityAoiConfig(
            city="Phoenix",
            slug="phoenix",
            timezone="America/Phoenix",
            city_config_version=MULTICITY_CITY_CONFIG_VERSION,
            analysis_geography_version=MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
            comparison_geography_version=CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
            polygon_aoi=phoenix_aoi,
            freeze_path=phoenix_freeze,
        ),
        "las vegas": CityAoiConfig(
            city="Las Vegas",
            slug="las-vegas",
            timezone="America/Los_Angeles",
            city_config_version=MULTICITY_CITY_CONFIG_VERSION,
            analysis_geography_version=MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
            comparison_geography_version=CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
            polygon_aoi=vegas_aoi,
            freeze_path=vegas_freeze,
        ),
        "tucson": CityAoiConfig(
            city="Tucson",
            slug="tucson",
            timezone="America/Phoenix",
            city_config_version=MULTICITY_CITY_CONFIG_VERSION,
            analysis_geography_version=MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
            comparison_geography_version=CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
            polygon_aoi=tucson_aoi,
            freeze_path=tucson_freeze,
        ),
        "los angeles": CityAoiConfig(
            city="Los Angeles",
            slug="los-angeles",
            timezone="America/Los_Angeles",
            city_config_version=MULTICITY_CITY_CONFIG_VERSION,
            analysis_geography_version=MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
            comparison_geography_version=CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
            polygon_aoi=la_aoi,
            freeze_path=la_freeze,
        ),
    }


_ALIASES: Final[dict[str, str]] = {
    "phx": "phoenix",
    "phoenix": "phoenix",
    "las vegas": "las vegas",
    "vegas": "las vegas",
    "lv": "las vegas",
    "tucson": "tucson",
    "los angeles": "los angeles",
    "la": "los angeles",
    "l.a.": "los angeles",
}


def _normalize_city(value: str) -> str:
    return " ".join(part for part in value.strip().lower().replace("-", " ").split())


def resolve_city_aoi(city: str) -> CityAoiConfig:
    normalized = _normalize_city(city)
    canonical = _ALIASES.get(normalized)
    configs = _city_configs()
    if canonical is None or canonical not in configs:
        supported = ", ".join(sorted(config.city for config in configs.values()))
        raise ValueError(f"unsupported city {city!r}; supported: {supported}")
    return configs[canonical]


def supported_multicity_names() -> tuple[str, ...]:
    return tuple(sorted(config.city for config in _city_configs().values()))
