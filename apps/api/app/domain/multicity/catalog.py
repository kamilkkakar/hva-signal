"""Frozen server-owned allowlist of supported city catalog entries."""

from __future__ import annotations

from app.core.area_registry import PHOENIX_AREA_SELECTION_POLICY_VERSION
from app.domain.multicity.city_config import (
    CapabilityKey,
    CapabilityStatus,
    CityConfig,
    CityId,
    CitySelectorEntry,
)

CITY_ALLOWLIST: tuple[CityConfig, ...] = (
    CityConfig(
        city_id=CityId.PHOENIX,
        display_name="Phoenix",
        state="AZ",
        place_geoid="0455000",
        timezone="America/Phoenix",
        area_id="phoenix-demo",
        outline_color="#2F6FED",
        local_geography_version=PHOENIX_AREA_SELECTION_POLICY_VERSION,
        city_config_version="CITY_CONFIG_PHOENIX_V1",
        capabilities={
            CapabilityKey.LOCAL_STORY: CapabilityStatus.AVAILABLE,
            CapabilityKey.SELECTED_TIME_THERMAL: CapabilityStatus.AVAILABLE,
            CapabilityKey.MATCHED_NIGHTTIME: CapabilityStatus.AVAILABLE,
            CapabilityKey.OBSERVED_INSTANTS: CapabilityStatus.AVAILABLE,
            CapabilityKey.ACS_CONTEXT: CapabilityStatus.AVAILABLE,
            CapabilityKey.LOCAL_CANOPY: CapabilityStatus.AVAILABLE,
            CapabilityKey.CROSS_CITY_CANOPY: CapabilityStatus.AVAILABLE,
            CapabilityKey.CROSS_CITY_EXPLORER: CapabilityStatus.PARTIAL,
            CapabilityKey.TYPE1_LIVE: CapabilityStatus.READY_FOR_ACQUISITION,
        },
    ),
    CityConfig(
        city_id=CityId.LAS_VEGAS,
        display_name="Las Vegas",
        state="NV",
        place_geoid="3240000",
        timezone="America/Los_Angeles",
        area_id="las-vegas-demo",
        outline_color="#0D9488",
        city_config_version="CITY_CONFIG_LAS_VEGAS_V1",
        capabilities={
            CapabilityKey.LOCAL_STORY: CapabilityStatus.PARTIAL,
            CapabilityKey.SELECTED_TIME_THERMAL: CapabilityStatus.READY_FOR_ACQUISITION,
            CapabilityKey.MATCHED_NIGHTTIME: CapabilityStatus.UNAVAILABLE,
            CapabilityKey.OBSERVED_INSTANTS: CapabilityStatus.READY_FOR_ACQUISITION,
            CapabilityKey.ACS_CONTEXT: CapabilityStatus.AVAILABLE,
            CapabilityKey.LOCAL_CANOPY: CapabilityStatus.UNAVAILABLE,
            CapabilityKey.CROSS_CITY_CANOPY: CapabilityStatus.AVAILABLE,
            CapabilityKey.CROSS_CITY_EXPLORER: CapabilityStatus.PARTIAL,
            CapabilityKey.TYPE1_LIVE: CapabilityStatus.READY_FOR_ACQUISITION,
        },
    ),
    CityConfig(
        city_id=CityId.TUCSON,
        display_name="Tucson",
        state="AZ",
        place_geoid="0477000",
        timezone="America/Phoenix",
        area_id="tucson-demo",
        outline_color="#7B4DDB",
        city_config_version="CITY_CONFIG_TUCSON_V1",
        capabilities={
            CapabilityKey.LOCAL_STORY: CapabilityStatus.PARTIAL,
            CapabilityKey.SELECTED_TIME_THERMAL: CapabilityStatus.READY_FOR_ACQUISITION,
            CapabilityKey.MATCHED_NIGHTTIME: CapabilityStatus.UNAVAILABLE,
            CapabilityKey.OBSERVED_INSTANTS: CapabilityStatus.READY_FOR_ACQUISITION,
            CapabilityKey.ACS_CONTEXT: CapabilityStatus.AVAILABLE,
            CapabilityKey.LOCAL_CANOPY: CapabilityStatus.UNAVAILABLE,
            CapabilityKey.CROSS_CITY_CANOPY: CapabilityStatus.AVAILABLE,
            CapabilityKey.CROSS_CITY_EXPLORER: CapabilityStatus.PARTIAL,
            CapabilityKey.TYPE1_LIVE: CapabilityStatus.READY_FOR_ACQUISITION,
        },
    ),
    CityConfig(
        city_id=CityId.LOS_ANGELES,
        display_name="Los Angeles",
        state="CA",
        place_geoid="0644000",
        timezone="America/Los_Angeles",
        area_id="los-angeles-demo",
        outline_color="#E67E22",
        city_config_version="CITY_CONFIG_LOS_ANGELES_V1",
        capabilities={
            CapabilityKey.LOCAL_STORY: CapabilityStatus.PARTIAL,
            CapabilityKey.SELECTED_TIME_THERMAL: CapabilityStatus.READY_FOR_ACQUISITION,
            CapabilityKey.MATCHED_NIGHTTIME: CapabilityStatus.UNAVAILABLE,
            CapabilityKey.OBSERVED_INSTANTS: CapabilityStatus.READY_FOR_ACQUISITION,
            CapabilityKey.ACS_CONTEXT: CapabilityStatus.AVAILABLE,
            CapabilityKey.LOCAL_CANOPY: CapabilityStatus.UNAVAILABLE,
            CapabilityKey.CROSS_CITY_CANOPY: CapabilityStatus.AVAILABLE,
            CapabilityKey.CROSS_CITY_EXPLORER: CapabilityStatus.PARTIAL,
            CapabilityKey.TYPE1_LIVE: CapabilityStatus.READY_FOR_ACQUISITION,
        },
    ),
)

_CITY_BY_ID = {city.city_id.value: city for city in CITY_ALLOWLIST}


def list_cities() -> tuple[CityConfig, ...]:
    return CITY_ALLOWLIST


def get_city(city_id: CityId | str) -> CityConfig:
    key = city_id.value if isinstance(city_id, CityId) else str(city_id)
    try:
        return _CITY_BY_ID[key]
    except KeyError as exc:
        raise KeyError(f"Unsupported city_id={key!r}.") from exc


def public_city_selector_allowlist() -> tuple[CitySelectorEntry, ...]:
    return tuple(city.selector_entry() for city in CITY_ALLOWLIST)

