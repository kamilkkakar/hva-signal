"""Live Type-1 architecture with hosted-live hard-disabled.

GENERAL real vendor stays refused via may_construct_real_vendor() / refuse_real_vendor().
The ONLY construction path for FortyGuardHttpClient in this program is the bounded
selected-time surface: construct_bounded_selected_time_http_client(), reachable from
POST /api/v1/live/selected-time when BOUNDED_SELECTED_TIME_LIVE_ENABLED=true.
HOSTED_LIVE_REAL_VENDOR_ENABLED must never authorize GENERAL construction.
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Mapping

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.config import Settings
from app.core.hosted_live_policy import (
    HostedLiveDisabledError,
    hosted_live_defaults_are_off,
    may_construct_real_vendor,
    refuse_real_vendor,
    resolve_hosted_live,
)
from app.domain.multicity.city_catalog import (
    CityAoiConfig,
    resolve_city_aoi,
)
from app.domain.signals import ThermalSignalKind
from app.integrations.fortyguard.adapter import FortyGuardAdapter
from app.integrations.fortyguard.cache import FortyGuardCache
from app.integrations.fortyguard.client import DEFAULT_BASE_URL, FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import MissingApiKeyError
from app.integrations.fortyguard.fingerprints import fingerprint_request
from app.integrations.fortyguard.partitioning import plan_partitions, polygon_area_km2
from app.integrations.fortyguard.transport_models import (
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode,
)

TYPE1_LIVE_CONTRACT_VERSION: Final = "MULTICITY_TYPE1_LIVE_V1"
TYPE1_LIVE_COST_MODEL_VERSION: Final = "LOCAL_COMPLEXITY_HEURISTIC_V2"
# Legacy alias retained only so imports fail closed on the new name in tests.
TYPE1_LIVE_CREDIT_ESTIMATE_VERSION: Final = TYPE1_LIVE_COST_MODEL_VERSION
TYPE1_LOCAL_COMPLEXITY_LABEL: Final = "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS"
TYPE1_ENDPOINT: Final = "/v1/heatmap"
TYPE1_TEMPORAL_MODE: Final = "single_hour"
TYPE1_FILTER_TYPE: Final = 1
TYPE1_RESOLUTION_M: Final = 100
TYPE1_METRIC: Final = "TCM mean"
TYPE1_ROLLBACK_BEHAVIOR: Final = (
    "Dry-run and refusal paths consume no spend, make no vendor call, and persist no "
    "vendor output. Only an explicit server-seeded safe cache payload may be stored."
)
DEFAULT_CACHE_DIR: Final = ".cache/multicity/type1_live"
ALLOWED_KEY_ALIASES: Final[frozenset[str]] = frozenset({"PRIMARY", "VALIDATION_B"})
FORBIDDEN_CLIENT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "aoi",
        "polygon",
        "polygon_aoi",
        "geometry",
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
    }
)
PUBLIC_DENYLIST_FIELDS: Final[frozenset[str]] = frozenset(
    {
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
    }
)


class Type1LiveRequestError(ValueError):
    """Invalid multicity Type-1 request."""


class Type1LiveClientRequest(BaseModel):
    """Client-facing request. AOI and provider identity stay server-owned."""

    model_config = ConfigDict(extra="forbid")

    city: str
    target_local: datetime
    key_alias: str = "PRIMARY"

    @model_validator(mode="before")
    @classmethod
    def _reject_forbidden_client_fields(cls, value: object) -> object:
        if isinstance(value, Mapping):
            hits = sorted(set(value).intersection(FORBIDDEN_CLIENT_FIELDS))
            if hits:
                joined = ", ".join(hits)
                raise ValueError(
                    "server-owned multicity Type-1 request rejects client-owned fields: "
                    + joined
                )
        return value

    @field_validator("city")
    @classmethod
    def _supported_city(cls, value: str) -> str:
        config = resolve_city_aoi(value)
        return config.city

    @field_validator("target_local")
    @classmethod
    def _target_local_is_hourly_naive(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("target_local must be AOI-local naive time")
        if value.minute != 0 or value.second != 0 or value.microsecond != 0:
            raise ValueError("target_local must land on an exact hour")
        return value

    @field_validator("key_alias")
    @classmethod
    def _known_alias_only(cls, value: str) -> str:
        alias = value.strip().upper()
        if alias not in ALLOWED_KEY_ALIASES:
            supported = ", ".join(sorted(ALLOWED_KEY_ALIASES))
            raise ValueError(f"key_alias must be one of {supported}")
        return alias


def _default_cache(cache: FortyGuardCache | None = None) -> FortyGuardCache:
    return cache if cache is not None else FortyGuardCache(DEFAULT_CACHE_DIR)


def _safe_local_valid_time(target_local: datetime) -> str:
    return target_local.strftime("%Y-%m-%dT%H:%M")


def _request_filter_params() -> dict[str, Any]:
    return {
        "analytic_type": "tcm",
        "filter_type": TYPE1_FILTER_TYPE,
        "statistic": "mean",
    }


def _cache_filter_params(city_config: CityAoiConfig) -> dict[str, Any]:
    return {
        **_request_filter_params(),
        "analysis_geography_version": city_config.analysis_geography_version,
        "city": city_config.slug,
        "city_config_version": city_config.city_config_version,
    }


def build_type1_request(request: Type1LiveClientRequest | Mapping[str, Any]) -> dict[str, Any]:
    parsed = (
        request
        if isinstance(request, Type1LiveClientRequest)
        else Type1LiveClientRequest.model_validate(request)
    )
    city_config = resolve_city_aoi(parsed.city)
    time_label = _safe_local_valid_time(parsed.target_local)
    return {
        "contract_version": TYPE1_LIVE_CONTRACT_VERSION,
        "city": city_config.city,
        "aoi_owner": "server",
        "aoi_policy_version": city_config.aoi_policy_version,
        "city_config_version": city_config.city_config_version,
        "analysis_geography_version": city_config.analysis_geography_version,
        "endpoint": TYPE1_ENDPOINT,
        "polygon_aoi": city_config.polygon_aoi,
        "date_time": {
            "start_date": parsed.target_local.strftime("%Y-%m-%d"),
            "start_time": parsed.target_local.strftime("%H:%M"),
        },
        "temporal_mode": TYPE1_TEMPORAL_MODE,
        "granularity_m": TYPE1_RESOLUTION_M,
        "metric": TYPE1_METRIC,
        "filter_params": _request_filter_params(),
        "local_valid_time": time_label,
        "key_alias": parsed.key_alias,
    }


def request_fingerprint_for(request: Type1LiveClientRequest | Mapping[str, Any]) -> str:
    doc = build_type1_request(request)
    return fingerprint_request(
        endpoint=doc["endpoint"],
        aoi=doc["polygon_aoi"],
        local_valid_time=doc["local_valid_time"],
        temporal_mode=doc["temporal_mode"],
        granularity=int(doc["granularity_m"]),
        filter_params=dict(doc["filter_params"]),
    )


def cache_fingerprint_for(request: Type1LiveClientRequest | Mapping[str, Any]) -> str:
    doc = build_type1_request(request)
    city_config = resolve_city_aoi(str(doc["city"]))
    return fingerprint_request(
        endpoint="/internal/multicity/type1_live/cache",
        aoi=doc["polygon_aoi"],
        local_valid_time=doc["local_valid_time"],
        temporal_mode=doc["temporal_mode"],
        granularity=int(doc["granularity_m"]),
        filter_params=_cache_filter_params(city_config),
    )


def estimate_type1_local_complexity_units(
    *, partition_count: int, expected_tiles_estimate: int
) -> int:
    """Local complexity heuristic — NOT FortyGuard credits / debit.

    Units: dimensionless local complexity units (LCU).
    Formula: partition_count + ceil(expected_tiles_estimate / 5000).
    This is a request-shape complexity score for preflight UX only. It must not
    be labelled or compared as vendor credits. Empirical Phoenix debit (~4220 for
    3749 tiles) does not calibrate this formula into a credit quote.
    """
    return max(1, partition_count + math.ceil(expected_tiles_estimate / 5000.0))


def estimate_type1_credits(*, partition_count: int, expected_tiles_estimate: int) -> int:
    """Deprecated alias. Returns local complexity units, not credits."""
    return estimate_type1_local_complexity_units(
        partition_count=partition_count,
        expected_tiles_estimate=expected_tiles_estimate,
    )


def spend_gate_check(
    request: Type1LiveClientRequest | Mapping[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    parsed = (
        request
        if isinstance(request, Type1LiveClientRequest)
        else Type1LiveClientRequest.model_validate(request)
    )
    city_config = resolve_city_aoi(parsed.city)
    preflight = dry_run_type1_preflight(parsed, settings=settings)
    hosted_live_enabled = resolve_hosted_live(settings=settings)
    real_vendor_enabled = may_construct_real_vendor(settings)
    return {
        "city": city_config.city,
        "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT.value,
        "server_controls_spend": True,
        "hosted_live_enabled": hosted_live_enabled,
        "real_vendor_enabled": real_vendor_enabled,
        "vendor_submit_allowed": bool(hosted_live_enabled and real_vendor_enabled),
        "reason": "hosted_live_disabled" if not hosted_live_enabled else "real_vendor_refused",
        "request_fingerprint": preflight["request_fingerprint"],
        "cache_fingerprint": preflight["cache_fingerprint"],
        "local_complexity_estimate": preflight["local_complexity_estimate"],
        "estimated_credits": preflight["local_complexity_estimate"],
        "rollback_behavior": preflight["rollback_behavior"],
    }


def dry_run_type1_preflight(
    request: Type1LiveClientRequest | Mapping[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    parsed = (
        request
        if isinstance(request, Type1LiveClientRequest)
        else Type1LiveClientRequest.model_validate(request)
    )
    city_config = resolve_city_aoi(parsed.city)
    built = build_type1_request(parsed)
    area_km2 = polygon_area_km2(city_config.polygon_aoi)
    partitions = plan_partitions(city_config.polygon_aoi)
    expected_tiles = max(
        len(partitions),
        math.ceil((area_km2 * 1_000_000.0) / float(TYPE1_RESOLUTION_M * TYPE1_RESOLUTION_M)),
    )
    request_fp = request_fingerprint_for(parsed)
    cache_fp = cache_fingerprint_for(parsed)
    local_complexity_units = estimate_type1_local_complexity_units(
        partition_count=len(partitions),
        expected_tiles_estimate=expected_tiles,
    )
    complexity = {
        "value": local_complexity_units,
        "variable_name": "local_complexity_units",
        "units": "dimensionless_local_complexity_units",
        "heuristic_version": TYPE1_LIVE_COST_MODEL_VERSION,
        "label": TYPE1_LOCAL_COMPLEXITY_LABEL,
        "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "mislabelled_as_credits_historically": True,
        "estimate_type": "LOCAL_MODEL",
        "not_vendor_credits": True,
    }
    hosted_live_enabled = resolve_hosted_live(settings=settings)
    real_vendor_enabled = may_construct_real_vendor(settings)
    return {
        "contract_version": TYPE1_LIVE_CONTRACT_VERSION,
        "city": city_config.city,
        "city_config_version": city_config.city_config_version,
        "analysis_geography_version": city_config.analysis_geography_version,
        "comparison_geography_version": city_config.comparison_geography_version,
        "local_time": parsed.target_local.isoformat(timespec="seconds"),
        "provider_resolved_time": {
            "provider_payload_local_valid_time": built["local_valid_time"],
            "timezone": city_config.timezone,
            "note": (
                "Modeled as AOI-local wall time for single_hour/filter_type 1; "
                "no UTC conversion is sent by this disabled architecture."
            ),
        },
        "aoi_area_estimate_km2": round(area_km2, 3),
        "partition_count": len(partitions),
        "resolution": "100m",
        "metric": TYPE1_METRIC,
        "expected_tiles_estimate": expected_tiles,
        "local_complexity_estimate": complexity,
        # Compatibility key retained but explicitly not credits.
        "estimated_credits": complexity,
        "cache_fingerprint": cache_fp,
        "request_fingerprint": request_fp,
        "key_alias": parsed.key_alias,
        "rollback_behavior": TYPE1_ROLLBACK_BEHAVIOR,
        "hosted_live_enabled": hosted_live_enabled,
        "real_vendor_enabled": real_vendor_enabled,
        "vendor_stage": "disabled_refuse_real_vendor",
        "aoi_owner": "server",
    }


def _sanitize_public_payload(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in PUBLIC_DENYLIST_FIELDS:
                continue
            safe[key] = _sanitize_public_payload(item)
        return safe
    if isinstance(value, list):
        return [_sanitize_public_payload(item) for item in value]
    return value


def seed_type1_live_cache(
    request: Type1LiveClientRequest | Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    cache: FortyGuardCache | None = None,
) -> dict[str, Any]:
    parsed = (
        request
        if isinstance(request, Type1LiveClientRequest)
        else Type1LiveClientRequest.model_validate(request)
    )
    city_config = resolve_city_aoi(parsed.city)
    preflight = dry_run_type1_preflight(parsed)
    safe_payload = _sanitize_public_payload(dict(payload))
    record = {
        "city": city_config.city,
        "request_fingerprint": preflight["request_fingerprint"],
        "cache_fingerprint": preflight["cache_fingerprint"],
        "cached_via": "server_seed",
        "payload": safe_payload,
    }
    active_cache = _default_cache(cache)
    active_cache.put(preflight["cache_fingerprint"], record)
    return record


def construct_vendor_stage(*, settings: Settings | None = None) -> None:
    """GENERAL vendor construction — always refuses (may_construct_real_vendor)."""
    refuse_real_vendor(settings)


def construct_bounded_selected_time_http_client(
    *,
    settings: Settings,
    transport: Any | None = None,
) -> FortyGuardHttpClient:
    """Narrow construction for POST /api/v1/live/selected-time only.

    Requires BOUNDED_SELECTED_TIME_LIVE_ENABLED. Does not consult
    may_construct_real_vendor() or HOSTED_LIVE_REAL_VENDOR_ENABLED.
    Reads Settings.fortyguard_api_key (server env only). Never returns the key.
    """
    if not bool(getattr(settings, "bounded_selected_time_live_enabled", False)):
        raise HostedLiveDisabledError(
            "bounded selected-time live gate is OFF; "
            "GENERAL may_construct_real_vendor remains False"
        )
    # Defense: GENERAL real-vendor flag must never be the construction authority.
    if may_construct_real_vendor(settings) is not False:
        raise HostedLiveDisabledError(
            "invariant broken: may_construct_real_vendor must stay False"
        )
    key = str(getattr(settings, "fortyguard_api_key", "") or "").strip()
    if not key:
        raise MissingApiKeyError(
            "BOUNDED selected-time live requires FORTYGUARD_API_KEY on the backend."
        )
    base = str(
        getattr(settings, "fortyguard_base_url", "") or DEFAULT_BASE_URL
    ).strip().rstrip("/") or DEFAULT_BASE_URL
    kwargs: dict[str, Any] = {"api_key": key, "base_url": base}
    if transport is not None:
        kwargs["transport"] = transport
    return FortyGuardHttpClient(**kwargs)


def _bounded_selected_time_acquire(
    parsed: Type1LiveClientRequest,
    *,
    settings: Settings,
    cache: FortyGuardCache,
    preflight: dict[str, Any],
    transport: Any | None = None,
    poll_interval: float = 3.0,
    poll_timeout: float = 600.0,
) -> dict[str, Any]:
    """Cache-miss acquisition owned by the bounded selected-time surface."""
    try:
        client = construct_bounded_selected_time_http_client(
            settings=settings, transport=transport
        )
    except MissingApiKeyError:
        return {
            "status": "acquisition_unavailable",
            "vendor_attempted": False,
            "message": (
                "Cache miss. Bounded live gate is open but the server secret is "
                "not configured. No FortyGuard Type-1 request was made."
            ),
            "preflight": preflight,
        }
    except HostedLiveDisabledError:
        return {
            "status": "acquisition_unavailable",
            "vendor_attempted": False,
            "message": (
                "Cache miss. Bounded selected-time live gate is OFF. "
                "No FortyGuard Type-1 request was made."
            ),
            "preflight": preflight,
        }

    city_config = resolve_city_aoi(parsed.city)
    sleep_fn = (lambda _dt: None) if poll_interval <= 0 else time.sleep
    # Adapter requires a non-empty api_key for _has_key even with injected client.
    # The key never leaves process memory into public responses (sanitize below).
    adapter = FortyGuardAdapter(
        api_key=str(settings.fortyguard_api_key).strip(),
        base_url=str(settings.fortyguard_base_url or DEFAULT_BASE_URL).rstrip("/"),
        http_client=client,
        cache_dir=Path(settings.cache_dir) / "bounded_selected_time_vendor",
        poll_interval=poll_interval,
        poll_timeout=poll_timeout,
        sleep=sleep_fn,
    )
    heatmap_req = HeatmapFetchRequest(
        polygon_aoi=city_config.polygon_aoi,
        start_date=parsed.target_local.strftime("%Y-%m-%d"),
        start_time=parsed.target_local.strftime("%H:%M"),
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        granularity=TYPE1_RESOLUTION_M,
        analytic_type="tcm",
        data_mode=DataMode.LIVE,
    )
    assembly = None
    try:
        assembly = adapter.fetch_heatmap(heatmap_req)
    except Exception as exc:  # noqa: BLE001 — sanitize; never leak secrets
        return {
            "status": "acquisition_unavailable",
            "vendor_attempted": True,
            "message": (
                "Bounded live acquisition failed. No secret material is returned. "
                f"error_type={type(exc).__name__}"
            ),
            "preflight": preflight,
        }
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass

    assert assembly is not None
    vendor_cache_hit = adapter.cache.get(assembly.fingerprint)
    raw_payload = vendor_cache_hit[0] if vendor_cache_hit else {}
    if not isinstance(raw_payload, dict):
        raw_payload = {}
    activity_id = raw_payload.get("activity_id")
    record_payload = {
        "activity_id": activity_id,
        "city": city_config.city,
        "tile_count": len(assembly.tiles),
        "source": str(assembly.source),
        "data_status": str(assembly.data_status),
        "adapter_fingerprint": assembly.fingerprint,
        "contract": "BOUNDED_SELECTED_TIME_LIVE_V1",
    }
    seeded = seed_type1_live_cache(parsed, payload=record_payload, cache=cache)
    return {
        "status": "live_acquired",
        "vendor_attempted": True,
        "cache_tier": None,
        "preflight": preflight,
        "result": _sanitize_public_payload(seeded),
    }


def run_type1_live(
    request: Type1LiveClientRequest | Mapping[str, Any],
    *,
    dry_run: bool = False,
    cache: FortyGuardCache | None = None,
    settings: Settings | None = None,
    bounded_selected_time_authorized: bool = False,
    vendor_transport: Any | None = None,
    poll_interval: float = 3.0,
    poll_timeout: float = 600.0,
) -> dict[str, Any]:
    """Cache-first Type-1 runner.

    Without bounded_selected_time_authorized: GENERAL refuse on miss (no vendor).
    With bounded_selected_time_authorized=True (selected-time route only): may
    construct FortyGuardHttpClient when BOUNDED_SELECTED_TIME_LIVE_ENABLED and
    Settings.fortyguard_api_key are present. may_construct_real_vendor stays False.
    """
    parsed = (
        request
        if isinstance(request, Type1LiveClientRequest)
        else Type1LiveClientRequest.model_validate(request)
    )
    preflight = dry_run_type1_preflight(parsed, settings=settings)
    active_cache = _default_cache(cache)
    cached = active_cache.get(preflight["cache_fingerprint"])
    if cached is not None:
        payload, tier = cached
        return {
            "status": "cache_hit",
            "cache_tier": tier,
            "vendor_attempted": False,
            "preflight": preflight,
            "result": _sanitize_public_payload(payload),
        }
    if dry_run:
        return {
            "status": "dry_run_preflight",
            "vendor_attempted": False,
            "preflight": preflight,
        }
    if bounded_selected_time_authorized:
        current = settings if settings is not None else Settings()
        return _bounded_selected_time_acquire(
            parsed,
            settings=current,
            cache=active_cache,
            preflight=preflight,
            transport=vendor_transport,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
        )
    _gate = spend_gate_check(parsed, settings=settings)
    del _gate
    raise _vendor_stage_disabled(settings=settings)


def _vendor_stage_disabled(*, settings: Settings | None = None) -> HostedLiveDisabledError:
    try:
        construct_vendor_stage(settings=settings)
    except HostedLiveDisabledError as exc:
        return exc
    raise HostedLiveDisabledError("live vendor stage unexpectedly became reachable")


def default_cache_root(root: str | Path | None = None) -> Path:
    return Path(DEFAULT_CACHE_DIR if root is None else root)


__all__ = [
    "ALLOWED_KEY_ALIASES",
    "DEFAULT_CACHE_DIR",
    "FORBIDDEN_CLIENT_FIELDS",
    "HostedLiveDisabledError",
    "TYPE1_FILTER_TYPE",
    "TYPE1_LIVE_CONTRACT_VERSION",
    "TYPE1_LIVE_COST_MODEL_VERSION",
    "TYPE1_LIVE_CREDIT_ESTIMATE_VERSION",
    "TYPE1_LOCAL_COMPLEXITY_LABEL",
    "TYPE1_METRIC",
    "TYPE1_RESOLUTION_M",
    "TYPE1_ROLLBACK_BEHAVIOR",
    "Type1LiveClientRequest",
    "build_type1_request",
    "cache_fingerprint_for",
    "construct_bounded_selected_time_http_client",
    "construct_vendor_stage",
    "default_cache_root",
    "dry_run_type1_preflight",
    "estimate_type1_credits",
    "estimate_type1_local_complexity_units",
    "hosted_live_defaults_are_off",
    "request_fingerprint_for",
    "run_type1_live",
    "seed_type1_live_cache",
    "spend_gate_check",
]
