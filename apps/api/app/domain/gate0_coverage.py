"""Contracts for reproducible Phoenix Gate 0 tile-coverage evidence."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _tracked_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith(("/", "~"))
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("source path must be repository-relative")
    if "workforce" in path.parts:
        raise ValueError("source path cannot depend on ignored workforce material")
    return path.as_posix()


class Gate0CoverageSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal[
        "area_config",
        "area_manifest",
        "zone_geometry",
        "reference_panel",
        "selected_time_snapshot",
    ]
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_field_count: int = Field(ge=0)
    observed_zone_row_count: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        return _tracked_path(value)


class Gate0ZoneExpectedTileCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str = Field(pattern=r"^\d{11}$")
    expected_tile_count: int = Field(gt=0)
    observed_field_count: int = Field(gt=0)
    minimum_observed_tile_count: int = Field(gt=0)
    maximum_observed_tile_count: int = Field(gt=0)

    @model_validator(mode="after")
    def _count_is_invariant(self) -> Self:
        if not (
            self.minimum_observed_tile_count
            == self.expected_tile_count
            == self.maximum_observed_tile_count
        ):
            raise ValueError("verified zone tile count must be invariant")
        return self


class Gate0CoverageDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_field_tile_count: int = Field(gt=0)
    minimum_zone_tile_count: int = Field(gt=0)
    median_zone_tile_count: float = Field(gt=0)
    maximum_zone_tile_count: int = Field(gt=0)
    zones: list[Gate0ZoneExpectedTileCount] = Field(min_length=1)


class Gate0CoveragePolicyBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zero_tile_behavior: Literal["insufficient_evidence"]
    minimum_coverage_ratio: None = None
    numeric_floor_authorized: Literal[False]
    runtime_effect: Literal["evidence_baseline_only"]


class Gate0ExpectedTileCoverageEvidence(BaseModel):
    """A hashable empirical baseline; it does not create a coverage threshold."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["GATE0_EXPECTED_TILE_COVERAGE_V1"]
    evidence_version: Literal["PHX_EXPECTED_TILE_COVERAGE_V1"]
    status: Literal["VERIFIED"]
    area_id: Literal["phoenix-demo"]
    generated_by: str
    geometry_version: str = Field(min_length=1)
    geometry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    area_config_version: Literal["PHX_AREA_CONFIG_V1"]
    area_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    granularity_m: Literal[100]
    assignment_method: Literal["centroid_within"]
    aggregation_statistic: Literal["mean"]
    expected_zone_count: Literal[25]
    reference_field_count: int = Field(gt=0)
    snapshot_field_count: int = Field(ge=0)
    observed_field_count: int = Field(gt=0)
    observed_zone_row_count: int = Field(gt=0)
    all_fields_complete: Literal[True]
    counts_invariant_per_zone: Literal[True]
    total_count_invariant: Literal[True]
    sources: list[Gate0CoverageSource] = Field(min_length=1)
    distribution: Gate0CoverageDistribution
    policy_boundary: Gate0CoveragePolicyBoundary

    @field_validator("generated_by")
    @classmethod
    def _validate_generator_path(cls, value: str) -> str:
        return _tracked_path(value)

    @model_validator(mode="after")
    def _evidence_is_internally_consistent(self) -> Self:
        zones = self.distribution.zones
        zone_ids = [zone.zone_id for zone in zones]
        if len(zones) != self.expected_zone_count or len(zone_ids) != len(set(zone_ids)):
            raise ValueError("coverage evidence must contain 25 unique zones")
        if self.observed_field_count != self.reference_field_count + self.snapshot_field_count:
            raise ValueError("observed field count does not match its sources")
        if self.observed_zone_row_count != self.observed_field_count * self.expected_zone_count:
            raise ValueError("observed zone-row count is incomplete")
        if any(zone.observed_field_count != self.observed_field_count for zone in zones):
            raise ValueError("each zone must occur in every observed field")

        counts = sorted(zone.expected_tile_count for zone in zones)
        midpoint = len(counts) // 2
        median = float(counts[midpoint])
        if len(counts) % 2 == 0:
            median = (counts[midpoint - 1] + counts[midpoint]) / 2
        if self.distribution.expected_field_tile_count != sum(counts):
            raise ValueError("expected field tile count does not equal the zone sum")
        if self.distribution.minimum_zone_tile_count != counts[0]:
            raise ValueError("minimum zone tile count mismatch")
        if self.distribution.maximum_zone_tile_count != counts[-1]:
            raise ValueError("maximum zone tile count mismatch")
        if self.distribution.median_zone_tile_count != median:
            raise ValueError("median zone tile count mismatch")
        return self
