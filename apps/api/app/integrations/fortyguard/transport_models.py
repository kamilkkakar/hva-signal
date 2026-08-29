"""Transport-layer models for the FortyGuard adapter.

TODO(Agent A): architecture names ThermalObservation, HeatmapTemporalMode,
ThermalDataSource, DataMode, UpstreamTimeSemantics, and UpstreamPartition are
the domain target. Mapper prefers app.domain imports when those contracts land.
These transport copies exist so Agent B can ship without editing domain files.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

ADAPTER_VERSION = "fortyguard-adapter-0.1.0"

TCM_TEMPERATURE_UNIT = "celsius"


def _enum_from_domain(name: str, fallback: type[Enum]) -> type[Enum]:
    import importlib

    for mod_name in ("app.domain.thermal", "app.domain.enums", "app.domain"):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        obj = getattr(mod, name, None)
        if obj is not None:
            return obj
    return fallback


class _HeatmapTemporalMode(str, Enum):
    SINGLE_HOUR = "single_hour"
    HOUR_RANGE = "hour_range"
    FULL_DAY = "full_day"
    DAY_RANGE = "day_range"
    MONTH = "month"


class _ThermalStatistic(str, Enum):
    INSTANT = "instant"
    MIN = "min"
    MEAN = "mean"
    MAX = "max"


class _ThermalDataSource(str, Enum):
    FORTYGUARD_LIVE = "fortyguard_live"
    FORTYGUARD_CACHED = "fortyguard_cached"
    REPLAY = "replay"


class _DataMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    AUTO = "auto"


class _UpstreamTimeSemantics(str, Enum):
    AOI_LOCAL_TIME = "aoi_local_time"


class _DataStatus(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    REPLAY = "replay"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


HeatmapTemporalMode = _enum_from_domain("HeatmapTemporalMode", _HeatmapTemporalMode)
ThermalStatistic = _enum_from_domain("ThermalStatistic", _ThermalStatistic)
ThermalDataSource = _enum_from_domain("ThermalDataSource", _ThermalDataSource)
DataMode = _enum_from_domain("DataMode", _DataMode)
UpstreamTimeSemantics = _enum_from_domain("UpstreamTimeSemantics", _UpstreamTimeSemantics)
DataStatus = _enum_from_domain("DataStatus", _DataStatus)


class TransportThermalObservation(BaseModel):
    """Mirrors architecture ThermalObservation.

    TODO(Agent A): replace construction sites with domain ThermalObservation.
    """

    valid_time: datetime
    statistic: ThermalStatistic  # type: ignore[valid-type]
    value: float | None
    quality_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class HeatmapFetchRequest(BaseModel):
    polygon_aoi: dict[str, Any]
    start_date: str
    start_time: str | None = None
    end_time: str | None = None
    end_date: str | None = None
    temporal_mode: HeatmapTemporalMode  # type: ignore[valid-type]
    granularity: Literal[60, 80, 100] = 100
    analytic_type: Literal["tcm", "time_of_measure", "exceedance", "persistence"] = "tcm"
    threshold: float | None = None
    direction: str | None = None
    data_mode: DataMode = DataMode.REPLAY  # type: ignore[valid-type]
    expected_zone_ids: list[str] = Field(default_factory=list)

    def local_valid_time_label(self) -> str:
        """AOI-local requested instant. Never a UTC conversion."""
        if self.start_time:
            return f"{self.start_date}T{self.start_time}"
        return self.start_date


class TransportTile(BaseModel):
    tile_id: int | str
    geometry: dict[str, Any]
    observations: list[Any]
    temperature_unit: Literal["celsius"] = TCM_TEMPERATURE_UNIT
    partition_id: str | None = None
    source: ThermalDataSource  # type: ignore[valid-type]


class PartitionPlan(BaseModel):
    partition_id: str
    geometry: dict[str, Any]
    area_km2: float


class PartitionFetch(BaseModel):
    partition_id: str
    tiles: list[TransportTile]
    source: ThermalDataSource  # type: ignore[valid-type]
    stats_data: dict[str, Any] = Field(default_factory=dict)


class AssemblyResult(BaseModel):
    tiles: list[TransportTile]
    completeness: Literal["complete", "partial"]
    missing_partition_ids: list[str]
    source: ThermalDataSource  # type: ignore[valid-type]
    data_status: DataStatus
    data_mode_requested: DataMode  # type: ignore[valid-type]
    upstream_payload: dict[str, Any]
    fingerprint: str
    adapter_version: str = ADAPTER_VERSION
    stats_data: dict[str, Any] | None = None
    quality_flags: list[str] = Field(default_factory=list)
    upstream_time_semantics: UpstreamTimeSemantics = (  # type: ignore[valid-type]
        UpstreamTimeSemantics.AOI_LOCAL_TIME
    )
