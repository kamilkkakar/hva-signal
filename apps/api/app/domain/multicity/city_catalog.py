"""Server-owned city AOIs for the multicity explorer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MULTICITY_CITY_CONFIG_VERSION: Final = "MULTICITY_CITY_CONFIG_V1"
SERVER_OWNED_AOI_POLICY: Final = "SERVER_OWNED_MULTICITY_AOI_V1"


def _rectangle_polygon(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> dict[str, object]:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }


@dataclass(frozen=True, slots=True)
class CityAoiConfig:
    city: str
    slug: str
    timezone: str
    city_config_version: str
    analysis_geography_version: str
    polygon_aoi: dict[str, object]
    aoi_policy_version: str = SERVER_OWNED_AOI_POLICY


_CITY_CONFIGS: Final[dict[str, CityAoiConfig]] = {
    "phoenix": CityAoiConfig(
        city="Phoenix",
        slug="phoenix",
        timezone="America/Phoenix",
        city_config_version=MULTICITY_CITY_CONFIG_VERSION,
        analysis_geography_version="PHOENIX_CITY_BBOX_V1",
        polygon_aoi=_rectangle_polygon(-112.40, 33.22, -111.93, 33.75),
    ),
    "las vegas": CityAoiConfig(
        city="Las Vegas",
        slug="las-vegas",
        timezone="America/Los_Angeles",
        city_config_version=MULTICITY_CITY_CONFIG_VERSION,
        analysis_geography_version="LAS_VEGAS_CITY_BBOX_V1",
        polygon_aoi=_rectangle_polygon(-115.37, 35.95, -114.93, 36.35),
    ),
    "tucson": CityAoiConfig(
        city="Tucson",
        slug="tucson",
        timezone="America/Phoenix",
        city_config_version=MULTICITY_CITY_CONFIG_VERSION,
        analysis_geography_version="TUCSON_CITY_BBOX_V1",
        polygon_aoi=_rectangle_polygon(-111.15, 32.10, -110.70, 32.38),
    ),
    "los angeles": CityAoiConfig(
        city="Los Angeles",
        slug="los-angeles",
        timezone="America/Los_Angeles",
        city_config_version=MULTICITY_CITY_CONFIG_VERSION,
        analysis_geography_version="LOS_ANGELES_CITY_BBOX_V1",
        polygon_aoi=_rectangle_polygon(-118.67, 33.70, -118.12, 34.34),
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
    if canonical is None or canonical not in _CITY_CONFIGS:
        supported = ", ".join(sorted(config.city for config in _CITY_CONFIGS.values()))
        raise ValueError(f"unsupported city {city!r}; supported: {supported}")
    return _CITY_CONFIGS[canonical]


def supported_multicity_names() -> tuple[str, ...]:
    return tuple(sorted(config.city for config in _CITY_CONFIGS.values()))

