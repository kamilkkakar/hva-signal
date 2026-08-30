"""Two-signal domain contract.

Signal A is the historically normalized nighttime thermal signal (q_A / Decision 8).
Signal B is a selected-time absolute thermal snapshot.

These types are internal. They are not fields on AnalysisResult and are not
served by a public paid endpoint. Do not put Signal B temperatures into q_A.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import DataStatus, ThermalDataSource


class ThermalSignalKind(str, Enum):
    HISTORICAL_NORMALIZED = "historical_normalized"
    SELECTED_TIME_SNAPSHOT = "selected_time_snapshot"


class SignalAvailability(str, Enum):
    READY = "READY"
    FETCHING = "FETCHING"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_PREPARED = "NOT_PREPARED"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"
    D8_INSUFFICIENT = "D8_INSUFFICIENT"
    PARTIAL = "PARTIAL"


class SignalProvenance(BaseModel):
    """Per-signal source truth. Do not collapse A and B into one page badge."""

    model_config = ConfigDict(extra="forbid")

    signal_kind: ThermalSignalKind
    area_id: str
    target_timestamp: datetime | None = None
    timezone: str | None = None
    source: ThermalDataSource | None = None
    data_status: DataStatus | None = None
    geometry_version: str | None = None
    reference_version: str | None = None
    reference_source: str | None = None
    aggregation_spec_version: str | None = None
    vendor_request_fingerprint: str | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("reference_version", "reference_source")
    @classmethod
    def _snapshot_has_no_historical_reference(cls, value: str | None, info):
        kind = info.data.get("signal_kind")
        if kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT and value is not None:
            raise ValueError(
                "selected-time snapshot provenance cannot carry a historical reference"
            )
        return value


class SelectedTimeSnapshotZone(BaseModel):
    """Zone-level absolute thermal value. Not q_A, rank, or Decision 8 state."""

    model_config = ConfigDict(extra="forbid")

    zone_id: str
    mean_temperature_c: float | None
    tile_count: int
    coverage_status: str
    quality_flags: list[str] = Field(default_factory=list)


class SelectedTimeSnapshot(BaseModel):
    """Internal Signal B payload. Zone-level only. Not a public AnalysisResult."""

    model_config = ConfigDict(extra="forbid")

    area_id: str
    target_timestamp: datetime
    timezone: str
    units: Literal["celsius"] = "celsius"
    aggregation_method: Literal["centroid_within_mean"] = "centroid_within_mean"
    aggregation_spec_version: str
    spatial_resolution: Literal["zone"] = "zone"
    user_facing_tile_map: Literal[False] = False
    availability: SignalAvailability
    provenance: SignalProvenance
    zones: list[SelectedTimeSnapshotZone] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)

    @field_validator("provenance")
    @classmethod
    def _provenance_is_snapshot(cls, value: SignalProvenance) -> SignalProvenance:
        if value.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            raise ValueError("snapshot provenance must be selected_time_snapshot")
        return value


class HistoricalNormalizedSignalState(BaseModel):
    """Signal A availability and provenance. q_A values stay on AnalysisResult."""

    model_config = ConfigDict(extra="forbid")

    availability: SignalAvailability
    provenance: SignalProvenance
    decision8_applies: Literal[True] = True

    @field_validator("provenance")
    @classmethod
    def _provenance_is_historical(cls, value: SignalProvenance) -> SignalProvenance:
        if value.signal_kind != ThermalSignalKind.HISTORICAL_NORMALIZED:
            raise ValueError("historical provenance must be historical_normalized")
        return value


class TwoSignalAvailability(BaseModel):
    """Independent per-signal states. D8 insufficient does not suppress Signal B."""

    model_config = ConfigDict(extra="forbid")

    historical: HistoricalNormalizedSignalState
    selected_time: SignalAvailability
    combined_score_authorized: Literal[False] = False
