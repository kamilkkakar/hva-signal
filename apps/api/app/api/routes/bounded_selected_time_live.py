"""Bounded selected-time live acquisition — narrow public POST.

Browser may send only city_id + local_datetime. Server owns AOI, partitions,
fingerprint, spend, vendor identity, and cache.

GENERAL arbitrary vendor stays OFF: may_construct_real_vendor() is always False
and refuse_real_vendor() always raises. HOSTED_LIVE_REAL_VENDOR_ENABLED must
never authorize construction.

ONLY this route may construct FortyGuardHttpClient, via
construct_bounded_selected_time_http_client() → Settings.fortyguard_api_key,
and only when BOUNDED_SELECTED_TIME_LIVE_ENABLED=true (cache-first; miss may pay).
"""

from __future__ import annotations

import threading
from datetime import date, datetime
from typing import Any, Final

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import Settings, get_settings
from app.core.hosted_live_policy import HostedLiveDisabledError
from app.domain.multicity.city_catalog import resolve_city_aoi
from app.domain.multicity.live_zone_aggregation import aggregate_cached_live_zones
from app.domain.multicity.type1_live import (
    Type1LiveClientRequest,
    run_type1_live,
)
from app.integrations.fortyguard.cache import FortyGuardCache

router = APIRouter(tags=["bounded-selected-time-live"])

BOUNDED_ROUTE: Final = "/live/selected-time"
FORBIDDEN_CLIENT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "aoi",
        "polygon",
        "polygon_aoi",
        "geometry",
        "area_id",
        "key",
        "api_key",
        "x_api_key",
        "authorization",
        "fortyguard_api_key",
        "provider_url",
        "vendor_url",
        "base_url",
        "fortyguard_base_url",
        "cache_key",
        "granularity_m",
        "horizon_hours",
        "lookback_hours",
        "data_mode",
        "analysis_mode",
        "key_alias",
    }
)

_flight_lock = threading.Lock()
_inflight: dict[str, threading.Event] = {}
_daily_lock = threading.Lock()
_daily_counts: dict[str, int] = {}


class SelectedTimeLiveBody(BaseModel):
    """Browser contract: city_id + local_datetime only."""

    model_config = ConfigDict(extra="forbid")

    city_id: str = Field(..., min_length=2, max_length=64)
    local_datetime: datetime

    @model_validator(mode="before")
    @classmethod
    def _reject_server_owned(cls, value: object) -> object:
        if isinstance(value, dict):
            hits = sorted(set(value).intersection(FORBIDDEN_CLIENT_FIELDS))
            if hits:
                raise ValueError(
                    "bounded live rejects client-owned fields: " + ", ".join(hits)
                )
        return value

    @field_validator("city_id")
    @classmethod
    def _known_city(cls, value: str) -> str:
        # Public catalog uses underscored ids (las_vegas); Type1 aliases use spaces.
        normalized = value.strip().replace("_", " ")
        resolve_city_aoi(normalized)
        return normalized

    @field_validator("local_datetime")
    @classmethod
    def _hourly_naive(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("local_datetime must be city-local naive time")
        if value.minute != 0 or value.second != 0 or value.microsecond != 0:
            raise ValueError("local_datetime must land on an exact hour")
        return value


def _city_slug_for_type1(city_id: str) -> str:
    config = resolve_city_aoi(city_id)
    return config.city


def _day_key(settings: Settings) -> str:
    return f"{date.today().isoformat()}:{settings.app_env}"


def _daily_limit(settings: Settings) -> int:
    return int(getattr(settings, "bounded_selected_time_daily_limit", 20) or 20)


def _gate_open(settings: Settings) -> bool:
    """Bounded selected-time surface gate — separate from GENERAL vendor."""
    return bool(getattr(settings, "bounded_selected_time_live_enabled", False))


def _public_result(raw: dict[str, Any]) -> dict[str, Any]:
    status_value = str(raw.get("status", "unknown"))
    vendor_attempted = bool(raw.get("vendor_attempted", False))
    provenance = {
        "acquisition_language": (
            "live_acquisition"
            if vendor_attempted and status_value == "live_acquired"
            else (
                "cache_hit"
                if status_value == "cache_hit"
                else "no_vendor_call"
            )
        ),
        "vendor_attempted": vendor_attempted,
        "cache_tier": raw.get("cache_tier"),
        "contract": "BOUNDED_SELECTED_TIME_LIVE_V1",
    }
    body: dict[str, Any] = {
        "status": status_value,
        "provenance": provenance,
        "capability": "selected_time_thermal",
    }
    if status_value == "cache_hit":
        body["result"] = raw.get("result")
        body["message"] = "Served from server cache. No live FortyGuard acquisition."
    elif status_value == "live_acquired":
        body["result"] = raw.get("result")
        body["message"] = (
            "Bounded selected-time live acquisition completed. "
            "GENERAL arbitrary vendor remains OFF."
        )
    elif status_value == "dry_run_preflight":
        body["preflight"] = {
            "city": raw.get("preflight", {}).get("city"),
            "local_time": raw.get("preflight", {}).get("local_time"),
            "cache_fingerprint": raw.get("preflight", {}).get("cache_fingerprint"),
            "hosted_live_enabled": raw.get("preflight", {}).get("hosted_live_enabled"),
            "real_vendor_enabled": raw.get("preflight", {}).get("real_vendor_enabled"),
        }
        body["message"] = "Dry-run only. No live FortyGuard acquisition."
    else:
        body["message"] = "Bounded live acquisition is not available for this request."
    return body


def _attach_zone_analysis(
    public: dict[str, Any],
    *,
    city_id: str,
    local_datetime: datetime,
    settings: Settings,
) -> dict[str, Any]:
    """Attach the same 25-zone aggregation used by the map, from cached tiles only."""
    if public.get("status") not in {"cache_hit", "live_acquired"}:
        return public
    try:
        analysis = aggregate_cached_live_zones(city_id, local_datetime, settings)
    except Exception as exc:  # noqa: BLE001 — fail closed, never leak internals/secrets
        public["analysis"] = {
            "aggregation_contract": "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
            "geometry_zone_count": 0,
            "bindable_temperature_values": 0,
            "zones": [],
        }
        public["message"] = (
            f"{public.get('message', '')} Zone aggregation could not be prepared "
            f"({type(exc).__name__}); no values were invented."
        ).strip()
        return public
    public["analysis"] = analysis
    return public


def _with_single_flight(fingerprint: str, runner: Any) -> dict[str, Any]:
    with _flight_lock:
        existing = _inflight.get(fingerprint)
        if existing is not None:
            waiter = existing
            created = False
        else:
            waiter = threading.Event()
            _inflight[fingerprint] = waiter
            created = True
    if not created:
        waiter.wait(timeout=60)
        # Re-run after join — typically a cache hit.
        return runner()
    try:
        return runner()
    finally:
        with _flight_lock:
            _inflight.pop(fingerprint, None)
            waiter.set()


@router.post(BOUNDED_ROUTE)
def post_selected_time_live(
    body: SelectedTimeLiveBody,
    request: Request,
) -> dict[str, Any]:
    """Narrow POST: city_id + local_datetime only."""
    del request  # request accepted so middleware can inspect; body is the contract
    settings = get_settings()
    if not _gate_open(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "bounded_selected_time_live_disabled",
                "message": (
                    "Bounded selected-time live is OFF. "
                    "GENERAL arbitrary vendor acquisition remains OFF. "
                    "Use replay/cache demonstration paths."
                ),
            },
        )

    day = _day_key(settings)
    limit = _daily_limit(settings)
    with _daily_lock:
        used = _daily_counts.get(day, 0)
        if used >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "bounded_selected_time_daily_limit",
                    "message": f"Daily bounded live budget reached ({limit}).",
                    "used": used,
                    "limit": limit,
                },
            )

    type1 = Type1LiveClientRequest(
        city=_city_slug_for_type1(body.city_id),
        target_local=body.local_datetime,
    )
    cache = FortyGuardCache(settings.cache_dir)

    def _run() -> dict[str, Any]:
        try:
            return run_type1_live(
                type1,
                cache=cache,
                settings=settings,
                bounded_selected_time_authorized=True,
            )
        except HostedLiveDisabledError:
            # Defense: GENERAL refuse path must never become a paid call.
            return {
                "status": "acquisition_unavailable",
                "vendor_attempted": False,
                "message": (
                    "Cache miss. Live vendor construction is refused. "
                    "No FortyGuard Type-1 request was made."
                ),
            }

    # Fingerprint key for single-flight: city + local hour.
    flight_key = f"{type1.city}|{type1.target_local.isoformat()}"
    raw = _with_single_flight(flight_key, _run)

    # Count only vendor attempts toward the daily budget (cache hits free).
    if raw.get("vendor_attempted"):
        with _daily_lock:
            _daily_counts[day] = _daily_counts.get(day, 0) + 1

    if raw.get("status") == "acquisition_unavailable":
        return {
            "status": "acquisition_unavailable",
            "capability": "selected_time_thermal",
            "provenance": {
                "acquisition_language": "no_vendor_call"
                if not raw.get("vendor_attempted")
                else "live_acquisition",
                "vendor_attempted": bool(raw.get("vendor_attempted")),
                "contract": "BOUNDED_SELECTED_TIME_LIVE_V1",
            },
            "message": raw.get("message"),
        }

    public = _public_result(raw)
    return _attach_zone_analysis(
        public,
        city_id=body.city_id,
        local_datetime=body.local_datetime,
        settings=settings,
    )


__all__ = ["BOUNDED_ROUTE", "SelectedTimeLiveBody", "router"]
