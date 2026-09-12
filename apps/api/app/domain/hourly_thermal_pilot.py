"""Contracts for the preregistered Phoenix hourly Type-1 pilot.

The pilot verifies an acquisition method. It does not freeze the candidate
thermal event or authorize an operational-outcome, probability, or priority
claim.
"""

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


class HourlyPilotSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal[
        "hourly_event_candidate",
        "area_config",
        "area_manifest",
        "zone_geometry",
        "provider_aoi",
        "expected_tile_coverage",
        "canary_reference_panel",
    ]
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        return _tracked_path(value)


class HourlyPilotRequestContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: Literal["/v1/heatmap"]
    analytic_type: Literal["tcm"]
    temporal_mode: Literal["single_hour"]
    filter_type: Literal[1]
    observation_kind: Literal["instant"]
    upstream_time_semantics: Literal["aoi_local_time"]
    granularity_m: Literal[100]
    partition_strategy: Literal["single_aoi"]
    expected_partition_count: Literal[1]
    window_aggregates_allowed: Literal[False]
    interpolation_allowed: Literal[False]


class HourlyPilotCanaryGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: Literal["2024-07-15T03:00"]
    reference_path: str
    reference_local_time: Literal["2024-07-15T03:00"]
    required_reference_zone_count: Literal[25]
    maximum_mean_absolute_delta_c: float = Field(gt=0, le=0.1)
    maximum_zone_absolute_delta_c: float = Field(gt=0, le=0.2)
    purpose: Literal["same_instant_request_and_aggregation_consistency"]

    @field_validator("reference_path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        return _tracked_path(value)


class HourlyPilotQualityGates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_field_tile_count: Literal[3749]
    expected_zone_count: Literal[25]
    exact_zone_tile_counts_required: Literal[True]
    every_tile_requires_temperature: Literal[True]
    every_zone_requires_temperature: Literal[True]
    complete_assembly_required: Literal[True]
    cache_recheck_required: Literal[True]
    exact_debit_metering_required_for_live_request: Literal[True]
    stop_on_first_failed_slot: Literal[True]
    automatic_retry_allowed: Literal[False]
    aligned_raw_tile_retention_required: Literal[True]
    canary: HourlyPilotCanaryGate


class HourlyPilotExecutionBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canary_must_pass_before_batch: Literal[True]
    maximum_manifest_slots: Literal[72]
    maximum_new_vendor_requests: Literal[72]
    credit_cap: None = None
    scope_is_request_count_not_budget: Literal[True]
    api_key_may_be_persisted: Literal[False]
    hosted_live_may_be_enabled: Literal[False]
    public_route_may_be_added: Literal[False]


class HourlyPilotClaimBoundaries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closes_gate0: Literal[False]
    freezes_hourly_event: Literal[False]
    authorizes_probability: Literal[False]
    authorizes_forecast: Literal[False]
    authorizes_operational_outcome: Literal[False]
    authorizes_health_outcome: Literal[False]
    authorizes_priority_or_intervention: Literal[False]


class HourlyPilotSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordinal: int = Field(ge=1, le=72)
    slot_id: str = Field(pattern=r"^202[234]-07-15T(?:[01]\d|2[0-3]):00$")
    date_local: str = Field(pattern=r"^202[234]-07-15$")
    time_local: str = Field(pattern=r"^(?:[01]\d|2[0-3]):00$")
    phase: Literal["canary", "batch"]
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _slot_parts_agree(self) -> Self:
        if self.slot_id != f"{self.date_local}T{self.time_local}":
            raise ValueError("slot_id must equal date_local + time_local")
        if (self.phase == "canary") != (self.slot_id == "2024-07-15T03:00"):
            raise ValueError("only 2024-07-15T03:00 may be the canary")
        return self


class HourlyThermalPilotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["PHX_HOURLY_THERMAL_PILOT_MANIFEST_V1"]
    manifest_version: Literal["PHX_HOURLY_TYPE1_PILOT_V1"]
    status: Literal["PREREGISTERED"]
    area_id: Literal["phoenix-demo"]
    iana_timezone: Literal["America/Phoenix"]
    purpose: tuple[
        Literal[
            "provider_request_semantics",
            "cache_and_debit_observability",
            "hourly_zone_coverage",
            "aligned_tile_field_retention",
        ],
        ...,
    ]
    pilot_dates_local: tuple[
        Literal["2022-07-15"], Literal["2023-07-15"], Literal["2024-07-15"]
    ]
    pilot_hours_local: tuple[str, ...] = Field(min_length=24, max_length=24)
    request_count: Literal[72]
    request_contract: HourlyPilotRequestContract
    quality_gates: HourlyPilotQualityGates
    execution_boundary: HourlyPilotExecutionBoundary
    claim_boundaries: HourlyPilotClaimBoundaries
    sources: list[HourlyPilotSource] = Field(min_length=7, max_length=7)
    slots: list[HourlyPilotSlot] = Field(min_length=72, max_length=72)

    @model_validator(mode="after")
    def _complete_unique_cartesian_manifest(self) -> Self:
        expected_hours = tuple(f"{hour:02d}:00" for hour in range(24))
        if self.pilot_hours_local != expected_hours:
            raise ValueError("pilot_hours_local must contain every exact hour in order")
        expected_ids = [
            f"{day}T{hour}"
            for day in self.pilot_dates_local
            for hour in self.pilot_hours_local
        ]
        if [slot.ordinal for slot in self.slots] != list(range(1, 73)):
            raise ValueError("slot ordinals must be complete and ordered")
        if [slot.slot_id for slot in self.slots] != expected_ids:
            raise ValueError("slots must be the ordered date-hour Cartesian product")
        if len({slot.request_fingerprint for slot in self.slots}) != 72:
            raise ValueError("every hourly request fingerprint must be unique")
        if sum(slot.phase == "canary" for slot in self.slots) != 1:
            raise ValueError("manifest must contain exactly one canary")
        roles = [source.role for source in self.sources]
        if len(roles) != len(set(roles)):
            raise ValueError("manifest source roles must be unique")
        if self.quality_gates.canary.slot_id not in expected_ids:
            raise ValueError("canary gate must identify a manifest slot")
        return self
