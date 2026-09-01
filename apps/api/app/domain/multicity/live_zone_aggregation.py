"""Turn bounded FortyGuard Type-1 cache tiles into the published 25-zone view.

This module is intentionally narrow: it reads only the server-owned cross-city
geometry and the bounded selected-time vendor cache. It does not construct a
vendor client or broaden the public geography contract.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from shapely.geometry import shape

from app.core.config import Settings
from app.domain.multicity.city_catalog import resolve_city_aoi
from app.integrations.fortyguard.cache import FortyGuardCache
from app.integrations.fortyguard.fingerprints import heatmap_fingerprint
from app.integrations.fortyguard.mapper import map_heatmap_result
from app.integrations.fortyguard.partitioning import plan_partitions
from app.integrations.fortyguard.transport_models import (
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode,
    ThermalDataSource,
)

LIVE_ZONE_AGGREGATION_CONTRACT: Final = (
    "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
)
_CITY_DIR: Final[dict[str, str]] = {
    "Phoenix": "phoenix",
    "Las Vegas": "las_vegas",
    "Tucson": "tucson",
    "Los Angeles": "los_angeles",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _observation_value(tile: Any) -> float | None:
    """Prefer the single-hour instant; fall back to the equivalent TCM mean."""
    fallback: float | None = None
    for observation in list(getattr(tile, "observations", None) or []):
        statistic = getattr(observation, "statistic", "")
        name = statistic.value if hasattr(statistic, "value") else str(statistic)
        value = getattr(observation, "value", None)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(number):
            continue
        if name == "instant":
            return number
        if name == "mean":
            fallback = number
    return fallback


def _request(city_name: str, local_datetime: datetime) -> HeatmapFetchRequest:
    config = resolve_city_aoi(city_name)
    return HeatmapFetchRequest(
        polygon_aoi=config.polygon_aoi,
        start_date=local_datetime.strftime("%Y-%m-%d"),
        start_time=local_datetime.strftime("%H:%M"),
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        granularity=100,
        analytic_type="tcm",
        data_mode=DataMode.LIVE,
    )


def _vendor_tiles(
    city_name: str,
    local_datetime: datetime,
    settings: Settings,
) -> list[Any]:
    request = _request(city_name, local_datetime)
    cache = FortyGuardCache(Path(settings.cache_dir) / "bounded_selected_time_vendor")
    tiles: list[Any] = []
    for partition in plan_partitions(request.polygon_aoi):
        fingerprint = heatmap_fingerprint(request, aoi=partition.geometry)
        cached = cache.get(fingerprint)
        if cached is None:
            continue
        bundled, _tier = cached
        result_body = (bundled or {}).get("result") or {}
        tiles.extend(
            map_heatmap_result(
                result_body,
                request=request,
                source=ThermalDataSource.FORTYGUARD_CACHED,
                partition_id=partition.partition_id,
            )
        )
    return tiles


def _zones(city_name: str) -> list[tuple[str, Any]]:
    config = resolve_city_aoi(city_name)
    city_dir = _CITY_DIR[config.city]
    path = _repo_root() / "data" / "areas" / "cross-city" / city_dir / "geometry.geojson"
    document = json.loads(path.read_text(encoding="utf-8"))
    output: list[tuple[str, Any]] = []
    for feature in document.get("features", []):
        properties = feature.get("properties") or {}
        geoid = str(properties.get("GEOID") or "").zfill(11)
        if not geoid.strip("0"):
            continue
        output.append((geoid, shape(feature.get("geometry") or {})))
    return output


def aggregate_cached_live_zones(
    city_name: str,
    local_datetime: datetime,
    settings: Settings,
) -> dict[str, Any]:
    """Aggregate cached Type-1 tiles by centroid-within mean into all 25 zones.

    Missing zones remain explicit with ``temperature_c=None``. Nothing is
    imputed, ranked, or stretched.
    """
    config = resolve_city_aoi(city_name)
    zones = _zones(config.city)
    buckets: dict[str, list[float]] = {geoid: [] for geoid, _geometry in zones}
    tiles = _vendor_tiles(config.city, local_datetime, settings)

    for tile in tiles:
        value = _observation_value(tile)
        if value is None:
            continue
        try:
            centroid = shape(getattr(tile, "geometry", None) or {}).centroid
        except Exception:  # noqa: BLE001 — malformed upstream geometry fails closed
            continue
        for geoid, zone_geometry in zones:
            if zone_geometry.covers(centroid):
                buckets[geoid].append(value)
                break

    rows: list[dict[str, Any]] = []
    bindable = 0
    for geoid, _geometry in zones:
        values = buckets[geoid]
        temperature = sum(values) / len(values) if values else None
        if temperature is not None and math.isfinite(temperature):
            bindable += 1
        else:
            temperature = None
        rows.append(
            {
                "zone_id": geoid,
                "temperature_c": temperature,
                "tile_count": len(values),
                "coverage_status": "valid" if temperature is not None else "missing",
            }
        )

    return {
        "city": config.city,
        "local_datetime": local_datetime.isoformat(timespec="seconds"),
        "timezone": config.timezone,
        "aggregation_contract": LIVE_ZONE_AGGREGATION_CONTRACT,
        "geometry_zone_count": len(zones),
        "bindable_temperature_values": bindable,
        "source_tile_count": len(tiles),
        "zones": rows,
    }


__all__ = ["LIVE_ZONE_AGGREGATION_CONTRACT", "aggregate_cached_live_zones"]
