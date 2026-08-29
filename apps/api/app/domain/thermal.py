"""Thermal observation and zone series contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import (
    HeatmapTemporalMode,
    ThermalDataSource,
    ThermalStatistic,
    UpstreamTimeSemantics,
)


class ThermalObservation(BaseModel):
    valid_time: datetime
    statistic: ThermalStatistic
    value: float | None
    quality_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ZoneThermalSeries(BaseModel):
    zone_id: str
    source: ThermalDataSource
    temporal_mode: HeatmapTemporalMode
    upstream_time_semantics: UpstreamTimeSemantics
    resolution_m: Literal[60, 80, 100] | None = None
    aggregation_spec_version: str
    observations: list[ThermalObservation]
    tile_count: int
    expected_tile_count: float | None = None
    tile_coverage_ratio: float | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
