"""Typed candidate contract for a persistent hourly thermal state.

This contract describes a retrospective thermal condition. It does not define
an observed health or service-demand outcome, a forecast, or a probability
model.
"""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HourlyThermalEventState(StrEnum):
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class HourlyThermalHourState(StrEnum):
    READY = "READY"
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"


class HistoricalThresholdRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_frame: Literal["HISTORICAL_OWN_ZONE_SAME_LOCAL_HOUR"]
    statistic: Literal["YEAR_BALANCED_MIDRANK_ECDF"]
    event_quantile_cutoff: float = Field(gt=0.5, lt=1.0)
    comparison_operator: Literal[">="]
    reference_window_start_month_day: str = Field(pattern=r"^\d{2}-\d{2}$")
    reference_window_end_month_day: str = Field(pattern=r"^\d{2}-\d{2}$")
    reference_years: tuple[int, ...] = Field(min_length=1)
    target_self_inclusion: Literal["EXCLUDE_TARGET_TIMESTAMP"]
    expected_reference_observations_per_year_hour: int = Field(ge=1)
    aoi_relative_normalization_allowed: Literal[False]

    @field_validator("reference_years")
    @classmethod
    def _years_are_unique_and_ordered(cls, years: tuple[int, ...]) -> tuple[int, ...]:
        if tuple(sorted(set(years))) != years:
            raise ValueError("reference_years must be unique and ascending")
        return years


class PersistenceRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_consecutive_hours: int = Field(ge=2, le=24)
    maximum_gap_hours: Literal[0]
    missing_observation_breaks_run: Literal[True]
    interpolation_allowed: Literal[False]
    cross_midnight_runs_allowed: Literal[True]


class HourlyEventCoverageRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sampling_design: Literal["HOURLY_24"]
    observation_kind: Literal["instant"]
    temporal_mode: Literal["single_hour"]
    window_aggregates_allowed: Literal[False]
    negative_finding_requires_complete_evaluated_interval: Literal[True]


class HourlyEventClaimBoundaries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calibrated_probability_authorized: Literal[False]
    forecast_authorized: Literal[False]
    health_outcome_claim_authorized: Literal[False]
    operational_demand_outcome_claim_authorized: Literal[False]
    priority_or_intervention_authorized: Literal[False]
    degree_hours_authorized: Literal[False]


class HourlyThermalEventContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["HOURLY_THERMAL_EVENT_CONTRACT_V1"]
    contract_version: str = Field(min_length=1)
    status: Literal["CANDIDATE"]
    event_id: Literal["persistent_relative_thermal_exceedance"]
    event_label: str = Field(min_length=1)
    event_sentence: str = Field(min_length=1)
    area_id: Literal["phoenix-demo"]
    iana_timezone: Literal["America/Phoenix"]
    spatial_unit: Literal["frozen_phoenix_v1_census_tract"]
    zone_geometry_version: str = Field(min_length=1)
    temperature_quantity: Literal["tcm_zone_mean"]
    aggregation_spec_version: str = Field(min_length=1)
    threshold: HistoricalThresholdRule
    persistence: PersistenceRule
    coverage: HourlyEventCoverageRule
    claim_boundaries: HourlyEventClaimBoundaries
    human_freeze_approval: None = None

    @model_validator(mode="after")
    def _candidate_is_not_runtime_authorization(self) -> Self:
        if not self.contract_version.endswith("_CANDIDATE"):
            raise ValueError("candidate contract_version must end in _CANDIDATE")
        if self.human_freeze_approval is not None:
            raise ValueError("candidate contract cannot contain a freeze approval")
        return self


class HourlyThermalEventObservation(BaseModel):
    """One observed or explicitly missing AOI-local hourly slot."""

    model_config = ConfigDict(extra="forbid")

    area_id: str = Field(min_length=1)
    zone_id: str = Field(pattern=r"^\d{11}$")
    valid_time_local: datetime
    temperature_c: float | None
    source_mode: Literal["replay", "cache", "live"] = "replay"
    source_family: Literal["fortyguard"] = "fortyguard"
    temperature_quantity: Literal["tcm_zone_mean"] = "tcm_zone_mean"
    zone_geometry_version: str = Field(min_length=1)
    aggregation_spec_version: str = Field(min_length=1)
    observation_kind: Literal["instant"] = "instant"
    temporal_mode: Literal["single_hour"] = "single_hour"
    interpolated: Literal[False] = False

    @field_validator("valid_time_local")
    @classmethod
    def _exact_naive_local_hour(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("valid_time_local must be AOI-local naive")
        if any((value.minute, value.second, value.microsecond)):
            raise ValueError("valid_time_local must be an exact local hour")
        return value

    @field_validator("temperature_c")
    @classmethod
    def _finite_temperature(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("temperature_c must be finite when present")
        return value


class HourlyThermalReferenceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: str = Field(min_length=1)
    zone_id: str = Field(pattern=r"^\d{11}$")
    valid_time_local: datetime
    temperature_c: float
    source_mode: Literal["replay"] = "replay"
    source_family: Literal["fortyguard"] = "fortyguard"
    temperature_quantity: Literal["tcm_zone_mean"] = "tcm_zone_mean"
    zone_geometry_version: str = Field(min_length=1)
    aggregation_spec_version: str = Field(min_length=1)
    observation_kind: Literal["instant"] = "instant"
    temporal_mode: Literal["single_hour"] = "single_hour"
    interpolated: Literal[False] = False

    @field_validator("valid_time_local")
    @classmethod
    def _exact_naive_local_hour(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("valid_time_local must be AOI-local naive")
        if any((value.minute, value.second, value.microsecond)):
            raise ValueError("valid_time_local must be an exact local hour")
        return value

    @field_validator("temperature_c")
    @classmethod
    def _finite_temperature(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("temperature_c must be finite")
        return value


class HourlyThermalHourAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_time_local: datetime
    state: HourlyThermalHourState
    temperature_c: float | None = None
    reference_n: int = Field(ge=0)
    historical_quantile: float | None = Field(default=None, ge=0, le=1)
    year_components: dict[int, float] = Field(default_factory=dict)
    qualifies: bool | None = None


class HourlyThermalEventRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time_local: datetime
    end_time_local_inclusive: datetime
    consecutive_hour_count: int = Field(ge=1)
    peak_historical_quantile: float = Field(ge=0, le=1)


class HourlyThermalEventEvaluation(BaseModel):
    """Deterministic event-state output with no probability field."""

    model_config = ConfigDict(extra="forbid")

    contract_version: str
    event_id: str
    area_id: str
    zone_id: str
    source_mode: str | None
    temperature_quantity: str
    zone_geometry_version: str
    aggregation_spec_version: str
    evaluated_start_local: datetime
    evaluated_end_local_inclusive: datetime
    state: HourlyThermalEventState
    n_expected_hours: int = Field(ge=1)
    n_observed_hours: int = Field(ge=0)
    n_reference_ready_hours: int = Field(ge=0)
    complete_evaluated_interval: bool
    negative_finding_supported: bool
    hour_assessments: list[HourlyThermalHourAssessment]
    qualifying_runs: list[HourlyThermalEventRun]
    evidence_limitations: list[str]

    @model_validator(mode="after")
    def _negative_finding_is_fail_closed(self) -> Self:
        if self.state == HourlyThermalEventState.NOT_DETECTED:
            if not self.complete_evaluated_interval or not self.negative_finding_supported:
                raise ValueError("NOT_DETECTED requires a complete evaluated interval")
        elif self.negative_finding_supported:
            raise ValueError("negative_finding_supported is only valid for NOT_DETECTED")
        if self.state == HourlyThermalEventState.DETECTED and not self.qualifying_runs:
            raise ValueError("DETECTED requires at least one qualifying run")
        return self
