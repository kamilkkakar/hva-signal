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

import math
import threading
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Final

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import Settings, get_settings
from app.core.hosted_live_policy import HostedLiveDisabledError
from app.domain.multicity.city_catalog import resolve_city_aoi
from app.domain.multicity.live_zone_aggregation import aggregate_cached_live_zones
from app.domain.multicity.type1_live import (
    Type1LiveClientRequest,
    dry_run_type1_preflight,
    run_type1_live,
)
from app.integrations.fortyguard.cache import FortyGuardCache
from app.integrations.fortyguard.exceptions import AcquisitionAllowanceExceeded

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
_inflight: dict[tuple[str, ...], Future[dict[str, Any]]] = {}
_flight_wait_seconds = 60.0
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
    return f"{datetime.now(timezone.utc).date().isoformat()}:{settings.app_env}"


def _daily_limit(settings: Settings) -> int:
    return max(0, int(settings.bounded_selected_time_daily_limit))


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
    # Acquisition provenance describes transport/cache use, not usable evidence.
    public["acquisition_status"] = public["status"]
    try:
        analysis = aggregate_cached_live_zones(city_id, local_datetime, settings)
    except Exception:  # noqa: BLE001 — preserve the acquisition, never retry it here
        analysis = {
            "aggregation_contract": "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
            "geometry_zone_count": 0,
            "bindable_temperature_values": 0,
            "source_tile_count": 0,
            "zones": [],
        }
    public["analysis"] = analysis
    config = resolve_city_aoi(city_id)
    valid_identity = (
        analysis.get("city") == config.city
        and analysis.get("local_datetime") == local_datetime.isoformat(timespec="seconds")
        and analysis.get("timezone") == config.timezone
    )
    rows = analysis.get("zones", [])
    finite_rows = [
        row
        for row in rows
        if isinstance(row.get("temperature_c"), (int, float))
        and not isinstance(row.get("temperature_c"), bool)
        and math.isfinite(row["temperature_c"])
        and row.get("coverage_status") == "valid"
        and isinstance(row.get("tile_count"), int)
        and row["tile_count"] > 0
    ]
    count = len(finite_rows)
    total = analysis.get("geometry_zone_count", 0)
    valid_counts = (
        total == len(rows)
        and len({row.get("zone_id") for row in rows}) == total
        and analysis.get("bindable_temperature_values") == count
        and analysis.get("source_tile_count", 0) >= sum(row["tile_count"] for row in finite_rows)
    )
    if not valid_identity or not valid_counts or count == 0:
        public["status"] = "observation_unavailable"
        public["observation_status"] = "unavailable"
        public["message"] = (
            "No usable zone temperatures are available for this request. "
            "The saved result needs review. No repeat acquisition was made."
        )
    elif count < total:
        public["status"] = "partial_observation"
        public["observation_status"] = "partial"
        public["message"] = (
            f"Temperatures are available for {count} of {total} zones. "
            "Missing zones remain unavailable."
        )
    else:
        public["observation_status"] = "available"
    return public


def _reserve_submission(settings: Settings) -> None:
    """Reserve each vendor POST atomically within this API process."""
    day = _day_key(settings)
    limit = _daily_limit(settings)
    with _daily_lock:
        used = _daily_counts.get(day, 0)
        if used >= limit:
            raise AcquisitionAllowanceExceeded(used, limit)
        # A failed submission may still have reached the provider; do not refund it.
        _daily_counts[day] = used + 1


def _with_single_flight(
    fingerprint: tuple[str, ...], runner: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    with _flight_lock:
        flight = _inflight.get(fingerprint)
        owner = flight is None
        if owner:
            flight = Future()
            _inflight[fingerprint] = flight
    assert flight is not None
    if not owner:
        try:
            return deepcopy(flight.result(timeout=_flight_wait_seconds))
        except FutureTimeoutError:
            if flight.done():
                return deepcopy(flight.result())
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "code": "bounded_selected_time_in_progress",
                    "message": "Acquisition is still running. No duplicate request was submitted.",
                },
            ) from None
    try:
        result = runner()
        flight.set_result(deepcopy(result))
        return result
    except BaseException as exc:
        flight.set_exception(exc)
        raise
    finally:
        with _flight_lock:
            _inflight.pop(fingerprint, None)


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
                before_submit=lambda: _reserve_submission(settings),
            )
        except AcquisitionAllowanceExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "bounded_selected_time_daily_limit",
                    "message": str(exc),
                    "used": exc.used,
                    "limit": exc.limit,
                },
            ) from None
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

    preflight = dry_run_type1_preflight(type1, settings=settings)
    flight_key = (
        settings.app_env,
        str(Path(settings.cache_dir).resolve()),
        str(settings.fortyguard_base_url),
        preflight["cache_fingerprint"],
    )
    raw = _with_single_flight(flight_key, _run)

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
