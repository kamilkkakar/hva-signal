"""Cross-city observation clock — local civil time freeze."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

CROSS_CITY_OBSERVATION_V1: Final = "CROSS_CITY_OBSERVATION_V1"
TARGET_LOCAL_CIVIL: Final = datetime(2024, 7, 8, 15, 0, 0)
TIMEZONE_SOURCE: Final = "CITY_ALLOWLIST_IANA_V1"

CITY_TIMEZONES: Final[dict[str, str]] = {
    "phoenix": "America/Phoenix",
    "tucson": "America/Phoenix",
    "las_vegas": "America/Los_Angeles",
    "los_angeles": "America/Los_Angeles",
}


@dataclass(frozen=True, slots=True)
class CityObservationClock:
    city_id: str
    timezone: str
    timezone_source: str
    local_timestamp: str
    utc_timestamp: str
    provider_payload_local_valid_time: str
    dst_active: bool
    dst_note: str


def resolve_city_observation_clock(city_id: str) -> CityObservationClock:
    key = city_id.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in CITY_TIMEZONES:
        raise KeyError(f"unsupported city_id={city_id!r}")
    iana = CITY_TIMEZONES[key]
    tz = ZoneInfo(iana)
    local = TARGET_LOCAL_CIVIL.replace(tzinfo=tz)
    utc = local.astimezone(ZoneInfo("UTC"))
    dst_active = bool(local.dst()) and local.dst().total_seconds() != 0
    return CityObservationClock(
        city_id=key,
        timezone=iana,
        timezone_source=TIMEZONE_SOURCE,
        local_timestamp=local.isoformat(timespec="seconds"),
        utc_timestamp=utc.isoformat(timespec="seconds"),
        provider_payload_local_valid_time=TARGET_LOCAL_CIVIL.strftime("%Y-%m-%dT%H:%M"),
        dst_active=dst_active,
        dst_note=(
            "America/Los_Angeles observes PDT on 2024-07-08 (UTC-7). "
            "America/Phoenix does not observe DST (UTC-7 year-round)."
            if iana == "America/Los_Angeles"
            else "America/Phoenix does not observe DST; offset stays UTC-7."
        ),
    )


def all_observation_clocks() -> dict[str, CityObservationClock]:
    return {city_id: resolve_city_observation_clock(city_id) for city_id in CITY_TIMEZONES}


__all__ = [
    "CITY_TIMEZONES",
    "CROSS_CITY_OBSERVATION_V1",
    "CityObservationClock",
    "TARGET_LOCAL_CIVIL",
    "TIMEZONE_SOURCE",
    "all_observation_clocks",
    "resolve_city_observation_clock",
]
