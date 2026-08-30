"""T-P provenance + mixing rules. T-Q UTC import (never Z-strip).

FortyGuard and public are juxtaposed as two objects. Mixed family emits no number.
GET / assemble never acquires. No spend fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from zoneinfo import ZoneInfo

from app.domain.temporal import (
    SOURCE_MODE_FROM_THERMAL_DATA_SOURCE,
    TemperatureQuantity,
    TemporalSourceFamily,
    TemporalSourceMode,
)
from app.services.aoi_timezone import (
    AoiLocalTimeError,
    classify_aoi_local_datetime,
    require_unique_aoi_local_hour,
)

TP_WIRE_MODES = (
    "replay",
    "fortyguard_cached",
    "fortyguard_live",
    "public_replay",
    "public_cached",
    "public_live",
)

AcquireMode = Literal["replay", "cached", "live"]


class SourceMixError(ValueError):
    """Silent mix of family, quantity, or acquire banner."""


class UtcImportError(ValueError):
    """UTC / offset timestamps must be converted, never stripped to naive clock digits."""


class TpWireSourceMode(str, Enum):
    REPLAY = "replay"
    FORTYGUARD_CACHED = "fortyguard_cached"
    FORTYGUARD_LIVE = "fortyguard_live"
    PUBLIC_REPLAY = "public_replay"
    PUBLIC_CACHED = "public_cached"
    PUBLIC_LIVE = "public_live"


@dataclass(frozen=True)
class TemporalSourceStamp:
    source_family: TemporalSourceFamily
    source_mode: TemporalSourceMode
    tp_source_mode: TpWireSourceMode
    acquire_mode: AcquireMode
    temperature_quantity: TemperatureQuantity
    variable_id: str
    thermal_data_source: str | None
    data_status: str | None


def map_thermal_data_source(thermal_data_source: str) -> TemporalSourceMode:
    try:
        return SOURCE_MODE_FROM_THERMAL_DATA_SOURCE[thermal_data_source]
    except KeyError as exc:
        raise SourceMixError(f"unknown ThermalDataSource {thermal_data_source!r}") from exc


def stamp_from_thermal_data_source(
    thermal_data_source: str,
    *,
    data_status: str | None = None,
) -> TemporalSourceStamp:
    mode = map_thermal_data_source(thermal_data_source)
    if mode is TemporalSourceMode.REPLAY:
        tp = TpWireSourceMode.REPLAY
        acquire: AcquireMode = "replay"
        status = data_status or "replay"
    elif mode is TemporalSourceMode.CACHE:
        tp = TpWireSourceMode.FORTYGUARD_CACHED
        acquire = "cached"
        status = data_status or "cached"
    else:
        tp = TpWireSourceMode.FORTYGUARD_LIVE
        acquire = "live"
        status = data_status or "live"
    _assert_legal_pair(tp, status)
    return TemporalSourceStamp(
        source_family=TemporalSourceFamily.FORTYGUARD,
        source_mode=mode,
        tp_source_mode=tp,
        acquire_mode=acquire,
        temperature_quantity=TemperatureQuantity.TCM_ZONE_MEAN,
        variable_id="tcm",
        thermal_data_source=thermal_data_source,
        data_status=status,
    )


def stamp_public(*, acquire_mode: AcquireMode, data_status: str | None = None) -> TemporalSourceStamp:
    tp = {
        "replay": TpWireSourceMode.PUBLIC_REPLAY,
        "cached": TpWireSourceMode.PUBLIC_CACHED,
        "live": TpWireSourceMode.PUBLIC_LIVE,
    }[acquire_mode]
    status = data_status or {"replay": "replay", "cached": "cached", "live": "live"}[acquire_mode]
    _assert_legal_pair(tp, status)
    return TemporalSourceStamp(
        source_family=TemporalSourceFamily.PUBLIC,
        source_mode=TemporalSourceMode.PUBLIC,
        tp_source_mode=tp,
        acquire_mode=acquire_mode,
        temperature_quantity=TemperatureQuantity.PUBLIC_2M_AIR_ZONE_MEAN,
        variable_id="fixture_2m_t",
        thermal_data_source=None,
        data_status=status,
    )


def _assert_legal_pair(tp: TpWireSourceMode, data_status: str) -> None:
    forbidden = {
        TpWireSourceMode.REPLAY: {"live", "cached"},
        TpWireSourceMode.FORTYGUARD_CACHED: {"live", "replay"},
        TpWireSourceMode.FORTYGUARD_LIVE: {"cached", "replay"},
        TpWireSourceMode.PUBLIC_REPLAY: {"live", "cached"},
        TpWireSourceMode.PUBLIC_CACHED: {"live", "replay"},
        TpWireSourceMode.PUBLIC_LIVE: {"cached", "replay"},
    }[tp]
    if data_status in forbidden:
        raise SourceMixError(f"{tp.value} cannot be labeled data_status={data_status}")


def assert_homogeneous_series(stamps: list[TemporalSourceStamp]) -> TemporalSourceStamp:
    if not stamps:
        raise SourceMixError("empty series")
    first = stamps[0]
    for stamp in stamps[1:]:
        if stamp.source_family != first.source_family:
            raise SourceMixError("series cannot mix source_family")
        if stamp.source_mode != first.source_mode and stamp.source_family != first.source_family:
            raise SourceMixError("series cannot mix source_mode across families")
        if stamp.temperature_quantity != first.temperature_quantity:
            raise SourceMixError("series cannot mix temperature_quantity")
        if stamp.variable_id != first.variable_id:
            raise SourceMixError("series cannot mix variable_id")
    return first


def acquire_mix(stamps: list[TemporalSourceStamp]) -> str:
    """Same family only. Mixed acquire → MIXED, never LIVE."""
    families = {stamp.source_family for stamp in stamps}
    if len(families) > 1:
        raise SourceMixError("mixed family = two objects; do not blend")
    modes = {stamp.acquire_mode for stamp in stamps}
    if len(modes) > 1:
        return "MIXED"
    only = next(iter(modes))
    return {"replay": "REPLAY", "cached": "CACHED", "live": "LIVE"}[only]


def juxtapose_or_none(
    left_family: TemporalSourceFamily,
    right_family: TemporalSourceFamily,
) -> Literal["single", "juxtapose"]:
    if left_family != right_family:
        return "juxtapose"
    return "single"


def refuse_blend(left_family: TemporalSourceFamily, right_family: TemporalSourceFamily) -> None:
    if left_family != right_family:
        raise SourceMixError("mixed family = two objects; no blended number")


def import_valid_time(
    value: datetime | str,
    *,
    iana: str,
    assume_naive_is: Literal["aoi_local", "forbidden_utc_naive"] = "aoi_local",
) -> tuple[datetime, datetime]:
    """Return (valid_time_local naive, valid_time_utc aware).

    Never strip Z/offset and keep clock digits. A UTC instant is converted
    through IANA. Naive UTC-as-local is rejected when assume_naive_is forbids it.
    """
    parsed = _parse_datetime(value)
    if parsed.tzinfo is not None:
        utc = parsed.astimezone(timezone.utc)
        local_aware = utc.astimezone(ZoneInfo(iana))
        local_naive = local_aware.replace(tzinfo=None)
        if local_naive.minute or local_naive.second or local_naive.microsecond:
            raise UtcImportError("converted local time is not on the hour; do not silently round")
        classify_aoi_local_datetime(local_naive, iana)
        return local_naive, utc
    if assume_naive_is == "forbidden_utc_naive":
        raise UtcImportError(
            "naive datetime cannot be treated as UTC; do not strip Z and keep the hour"
        )
    require_unique_aoi_local_hour(parsed, iana)
    localized = parsed.replace(tzinfo=ZoneInfo(iana))
    return parsed, localized.astimezone(timezone.utc)


def refuse_z_strip_import(raw: str, *, iana: str) -> tuple[datetime, datetime]:
    """Convert a Z/offset string. Fail if the caller already stripped the offset."""
    if isinstance(raw, str) and not raw.endswith("Z") and "+" not in raw[10:]:
        raise UtcImportError("UTC import requires a Z or offset; do not strip and keep the hour")
    parsed = _parse_datetime(raw)
    if parsed.tzinfo is None:
        raise UtcImportError("offset/Z was stripped before import")
    local, utc = import_valid_time(parsed, iana=iana)
    naive_clock = parsed.replace(tzinfo=None)
    if iana == "America/Phoenix" and naive_clock.hour == 10 and local.hour == 10:
        raise UtcImportError("Z-strip import would treat 10:00Z as 10:00 local")
    return local, utc


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    text = value.strip()
    if text.endswith("Z"):
        return datetime.fromisoformat(text[:-1] + "+00:00")
    return datetime.fromisoformat(text)
