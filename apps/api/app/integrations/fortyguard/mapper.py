"""Map FortyGuard heatmap JSON to typed tile observations.

TODO(Agent A): domain ThermalObservation is the mapping target. This module
constructs app.domain.thermal.ThermalObservation when importable.

tcm tile temperatures are Celsius despite the official client docstring (°F).
exceedance values are hour counts, not degree-hours.
"""

from __future__ import annotations

import importlib
from datetime import date, datetime
from typing import Any

from app.integrations.fortyguard.transport_models import (
    HeatmapFetchRequest,
    ThermalDataSource,
    ThermalStatistic,
    TransportThermalObservation,
    TransportTile,
)

_CELSIUS_FLAG = "tcm_unit:celsius"


def requested_valid_time(start_date: str, start_time: str | None) -> datetime:
    """AOI-local naive datetime from the request clock. Does not convert to UTC."""
    day = date.fromisoformat(start_date)
    if not start_time:
        return datetime(day.year, day.month, day.day, 0, 0, 0)
    cleaned = start_time.strip().replace("Z", "").replace("z", "")
    if "T" in cleaned:
        cleaned = cleaned.split("T", 1)[1]
    if "+" in cleaned:
        cleaned = cleaned.split("+", 1)[0]
    parts = cleaned.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(float(parts[2])) if len(parts) > 2 else 0
    return datetime(day.year, day.month, day.day, hour, minute, second)


def _observation_cls() -> type:
    for mod_name in ("app.domain.thermal", "app.domain"):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        cls = getattr(mod, "ThermalObservation", None)
        if cls is not None:
            return cls
    return TransportThermalObservation


def _statistic(name: str) -> Any:
    try:
        return ThermalStatistic(name)
    except Exception:
        return name


def _make_observation(
    *,
    valid_time: datetime,
    statistic: str,
    value: float | None,
    quality_flags: list[str],
    evidence_refs: list[str] | None = None,
) -> Any:
    cls = _observation_cls()
    kwargs = {
        "valid_time": valid_time,
        "statistic": _statistic(statistic),
        "value": value,
        "quality_flags": quality_flags,
        "evidence_refs": evidence_refs or [],
    }
    try:
        return cls(**kwargs)
    except Exception:
        return TransportThermalObservation(
            valid_time=valid_time,
            statistic=_statistic(statistic),
            value=value,
            quality_flags=quality_flags,
            evidence_refs=evidence_refs or [],
        )


def _coerce_source(source: ThermalDataSource | str) -> ThermalDataSource:
    if isinstance(source, ThermalDataSource):
        return source
    return ThermalDataSource(source)


def map_heatmap_result(
    result: dict[str, Any],
    *,
    request: HeatmapFetchRequest,
    source: ThermalDataSource | str,
    partition_id: str,
) -> list[TransportTile]:
    source_enum = _coerce_source(source)
    valid_time = requested_valid_time(request.start_date, request.start_time)
    features = (result.get("map_data") or {}).get("features") or []
    tiles: list[TransportTile] = []
    analytic = request.analytic_type
    mode = (
        request.temporal_mode.value
        if hasattr(request.temporal_mode, "value")
        else str(request.temporal_mode)
    )

    for feature in features:
        props = dict(feature.get("properties") or {})
        tile_id = props.get("tile_id", feature.get("id"))
        geometry = feature.get("geometry") or {}
        observations: list[Any] = []
        flags = [_CELSIUS_FLAG] if analytic == "tcm" else []
        if analytic == "tcm":
            # Pass through Celsius values. Do not convert as if they were °F.
            avg = props.get("average_temperature")
            lo = props.get("min_temperature")
            hi = props.get("max_temperature")
            observations.append(
                _make_observation(
                    valid_time=valid_time,
                    statistic="mean",
                    value=None if avg is None else float(avg),
                    quality_flags=list(flags),
                )
            )
            observations.append(
                _make_observation(
                    valid_time=valid_time,
                    statistic="min",
                    value=None if lo is None else float(lo),
                    quality_flags=list(flags),
                )
            )
            observations.append(
                _make_observation(
                    valid_time=valid_time,
                    statistic="max",
                    value=None if hi is None else float(hi),
                    quality_flags=list(flags),
                )
            )
            if mode == "single_hour":
                observations.append(
                    _make_observation(
                        valid_time=valid_time,
                        statistic="instant",
                        value=None if avg is None else float(avg),
                        quality_flags=list(flags),
                    )
                )
        else:
            raw = props.get("value")
            extra = list(flags)
            units = (result.get("stats_data") or {}).get("units")
            if units:
                extra.append(f"units:{units}")
            if analytic == "exceedance":
                extra.append("exceedance:hour_count")
            observations.append(
                _make_observation(
                    valid_time=valid_time,
                    statistic="mean",
                    value=None if raw is None else float(raw),
                    quality_flags=extra,
                )
            )
        tiles.append(
            TransportTile(
                tile_id=tile_id if tile_id is not None else len(tiles),
                geometry=geometry,
                observations=observations,
                temperature_unit="celsius",
                partition_id=partition_id,
                source=source_enum,
            )
        )
    return tiles
