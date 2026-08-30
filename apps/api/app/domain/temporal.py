"""Provider-neutral temporal domain (hva-signal-temporal-domain-v1).

CANDIDATE. Not a FastAPI / public OpenAPI model.
Lifted from T-B. Does NOT replace app.domain.thermal.ThermalObservation /
ZoneThermalSeries (those field sets stay contract-locked).

Replay / cache / live / public normalize into these types.
Signal A (q_A) and Decision 8 are out of scope.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TEMPORAL_DOMAIN_CONTRACT_VERSION = "hva-signal-temporal-domain-v1"
EXPECTED_ZONE_COUNT = 25
PHOENIX_IANA = "America/Phoenix"
CENTROID_WITHIN_MEAN = "centroid_within_mean"
UNITS_CELSIUS = "celsius"
UPSTREAM_AOI_LOCAL = "aoi_local_time"
OBSERVATION_GEOMETRY_ROLE = "thermal_observation_only"


class TemporalSourceMode(str, Enum):
    REPLAY = "replay"
    CACHE = "cache"
    LIVE = "live"
    PUBLIC = "public"


class TemporalSourceFamily(str, Enum):
    FORTYGUARD = "fortyguard"
    PUBLIC = "public"
    FIXTURE = "fixture"


class TemperatureQuantity(str, Enum):
    TCM_ZONE_MEAN = "tcm_zone_mean"
    PUBLIC_2M_AIR_ZONE_MEAN = "public_2m_air_zone_mean"


class ObservationKind(str, Enum):
    INSTANT = "instant"
    WINDOW_AGGREGATE = "window_aggregate"


class SamplingDesign(str, Enum):
    HOURLY_24 = "HOURLY_24"
    SAMPLED_3H = "SAMPLED_3H"
    SAMPLED_4H = "SAMPLED_4H"
    SAMPLED_6H = "SAMPLED_6H"
    ANCHOR_DAY_NIGHT = "ANCHOR_DAY_NIGHT"
    ANCHOR_0300 = "ANCHOR_0300"
    TYPE2_WINDOW = "TYPE2_WINDOW"


class TemporalCoverageClass(str, Enum):
    FULL = "FULL"
    ADEQUATE = "ADEQUATE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class Comparability(str, Enum):
    COMPARABLE = "COMPARABLE"
    INCOMPARABLE = "INCOMPARABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SpatialScope(str, Enum):
    ZONE = "zone"
    AOI = "aoi"


class CoverageStatus(str, Enum):
    OK = "ok"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MISSING = "missing"


class ThermalStatistic(str, Enum):
    INSTANT = "instant"
    MIN = "min"
    MEAN = "mean"
    MAX = "max"


# Existing ThermalDataSource values. Public-family records leave this None.
EXISTING_THERMAL_DATA_SOURCE = Literal["replay", "fortyguard_cached", "fortyguard_live"]
EXISTING_DATA_STATUS = Literal["replay", "cached", "live", "partial", "unavailable"]

SOURCE_MODE_FROM_THERMAL_DATA_SOURCE: dict[str, TemporalSourceMode] = {
    "replay": TemporalSourceMode.REPLAY,
    "fortyguard_cached": TemporalSourceMode.CACHE,
    "fortyguard_live": TemporalSourceMode.LIVE,
}

EXPECTED_HOURS: dict[SamplingDesign, int] = {
    SamplingDesign.HOURLY_24: 24,
    SamplingDesign.SAMPLED_3H: 8,
    SamplingDesign.SAMPLED_4H: 6,
    SamplingDesign.SAMPLED_6H: 4,
    SamplingDesign.ANCHOR_DAY_NIGHT: 2,
    SamplingDesign.ANCHOR_0300: 1,
    SamplingDesign.TYPE2_WINDOW: 1,
}


def local_to_utc(valid_time_local: datetime, iana: str) -> datetime:
    """Naive AOI-local → aware UTC. Does not silently round minutes."""
    if valid_time_local.tzinfo is not None:
        raise ValueError("valid_time_local must be AOI-local naive")
    localized = valid_time_local.replace(tzinfo=ZoneInfo(iana))
    return localized.astimezone(timezone.utc)


class AnalysisGeography(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: str = Field(min_length=1)
    zone_geometry_version: str = Field(min_length=1)
    geometry_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    expected_zone_count: Literal[25] = EXPECTED_ZONE_COUNT
    zone_id_property: Literal["GEOID", "zone_id"] = "GEOID"


class ObservationGeometry(BaseModel):
    """Provider tiles / public grid cells. Never analysis geography."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["thermal_observation_only"] = OBSERVATION_GEOMETRY_ROLE
    provider: Literal["fortyguard", "public_grid", "none"]
    tile_resolution_m: Literal[60, 80, 100] | None = None
    tile_count: int = Field(default=0, ge=0)
    expected_tile_count: float | None = None
    tile_coverage_ratio: float | None = None
    notes: list[str] = Field(default_factory=list)


class Quality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interpolated: Literal[False] = False
    silent_fill: Literal[False] = False
    flags: list[str] = Field(default_factory=list)


class TemporalProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    source_mode: TemporalSourceMode
    source_family: TemporalSourceFamily
    source_dataset: str | None = None
    thermal_data_source: EXISTING_THERMAL_DATA_SOURCE | None = None
    data_status: EXISTING_DATA_STATUS | None = None
    temperature_quantity: TemperatureQuantity
    analytic: str | None = None
    timezone: str = Field(min_length=1)
    geometry_version: str = Field(min_length=1)
    geometry_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    aggregation_spec_version: str = Field(min_length=1)
    aggregation_method: Literal["centroid_within_mean"] = CENTROID_WITHIN_MEAN
    units: Literal["celsius"] = UNITS_CELSIUS
    request_fingerprint: str | None = None
    vendor_request_fingerprint: str | None = None
    activity_id: str | None = None
    reference_version: str | None = None
    reference_source: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _source_pairs(self) -> TemporalProvenance:
        if self.source_family == TemporalSourceFamily.PUBLIC:
            if self.thermal_data_source is not None:
                raise ValueError("public-family provenance cannot carry ThermalDataSource")
            if self.source_mode != TemporalSourceMode.PUBLIC:
                raise ValueError("public family requires source_mode=public")
            if self.temperature_quantity != TemperatureQuantity.PUBLIC_2M_AIR_ZONE_MEAN:
                raise ValueError("public family cannot claim tcm_zone_mean")
            if self.analytic == "tcm":
                raise ValueError("public analytic cannot be labeled tcm")
        if self.source_family == TemporalSourceFamily.FORTYGUARD:
            if self.source_mode == TemporalSourceMode.PUBLIC:
                raise ValueError("fortyguard family cannot use source_mode=public")
            if self.temperature_quantity != TemperatureQuantity.TCM_ZONE_MEAN:
                raise ValueError("fortyguard family must use tcm_zone_mean")
        if self.source_mode == TemporalSourceMode.LIVE and self.data_status == "cached":
            raise ValueError("live source_mode cannot be labeled cached")
        if self.source_mode == TemporalSourceMode.CACHE and self.data_status == "live":
            raise ValueError("cached source_mode cannot be labeled live")
        if self.source_mode == TemporalSourceMode.REPLAY and self.data_status in {
            "live",
            "cached",
        }:
            raise ValueError("replay cannot be labeled live or cached")
        return self


class ClaimPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_polyline: bool = False
    count_among_observed: bool = False
    min_max_among_observed: bool = False
    min_max_as_period: bool = False
    time_of_peak_as_extremum: bool = False
    time_of_min_as_extremum: bool = False
    day_night_difference: bool = False
    cooling_trajectory: bool = False
    headline_mean_as_period: bool = False
    headline_year_difference: bool = False


class TemporalCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["TemporalCoverage"] = "TemporalCoverage"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str | None = None
    spatial_scope: SpatialScope = SpatialScope.ZONE
    coverage_class: TemporalCoverageClass
    spatial_coverage_class: TemporalCoverageClass | None = None
    comparability: Comparability = Comparability.NOT_APPLICABLE
    sampling_design: SamplingDesign
    window_id: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    temperature_quantity: TemperatureQuantity | None = None
    n_present: int = Field(ge=0)
    n_expected: int = Field(ge=1)
    coverage_ratio: float | None = Field(default=None, ge=0, le=1)
    n_contributing_days: int | None = Field(default=None, ge=0)
    n_calendar_days: int | None = Field(default=None, ge=0)
    n_valid_zones: int | None = Field(default=None, ge=0, le=25)
    n_expected_zones: Literal[25] = EXPECTED_ZONE_COUNT
    n_valid_zones_min: int | None = Field(default=None, ge=0, le=25)
    n_valid_zones_mean: float | None = None
    longest_gap_hours: int | None = Field(default=None, ge=0)
    longest_gap_days: int | None = Field(default=None, ge=0)
    paired_n_present: int | None = Field(default=None, ge=0)
    paired_n_expected: int | None = Field(default=None, ge=0)
    paired_ratio: float | None = Field(default=None, ge=0, le=1)
    interpolated: Literal[False] = False
    silent_fill: Literal[False] = False
    geometry_version: str = Field(min_length=1)
    aggregation_version: str = Field(min_length=1)
    missing_slot_ids: list[str] = Field(default_factory=list)
    missing_zone_ids: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ratio_and_scope(self) -> TemporalCoverage:
        expected_ratio = self.n_present / float(self.n_expected)
        if self.coverage_ratio is None:
            object.__setattr__(self, "coverage_ratio", expected_ratio)
        elif abs(self.coverage_ratio - expected_ratio) > 1e-9:
            raise ValueError("coverage_ratio must equal n_present / n_expected")
        if self.spatial_scope == SpatialScope.ZONE and not self.zone_id:
            raise ValueError("zone-scoped coverage requires zone_id")
        if self.spatial_scope == SpatialScope.AOI and self.zone_id is not None:
            raise ValueError("AOI coverage must not carry a zone_id")
        if self.n_present > self.n_expected:
            raise ValueError("n_present cannot exceed n_expected")
        if self.n_valid_zones == 0 and "downtown_0_25_not_a_day" not in self.quality_flags:
            # Flag is optional; zero valid zones is still INSUFFICIENT, never 0 °C.
            pass
        return self


class ZoneThermalObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["ZoneThermalObservation"] = "ZoneThermalObservation"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    valid_time_local: datetime
    valid_time_utc: datetime
    timezone: str = Field(min_length=1)
    local_date: date
    local_hour: int | None = Field(default=None, ge=0, le=23)
    upstream_time_semantics: Literal["aoi_local_time"] = UPSTREAM_AOI_LOCAL
    temperature_c: float | None = None
    temperature_quantity: TemperatureQuantity
    units: Literal["celsius"] = UNITS_CELSIUS
    statistic: ThermalStatistic
    observation_kind: ObservationKind
    temporal_mode: str | None = None
    sampling_design: SamplingDesign | None = None
    window_start_local: datetime | None = None
    window_end_local: datetime | None = None
    source_mode: TemporalSourceMode
    coverage_status: CoverageStatus
    coverage: TemporalCoverage
    analysis_geography: AnalysisGeography
    observation_geometry: ObservationGeometry
    aggregation_spec_version: str = Field(min_length=1)
    aggregation_method: Literal["centroid_within_mean"] = CENTROID_WITHIN_MEAN
    quality: Quality
    provenance: TemporalProvenance
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("valid_time_local")
    @classmethod
    def _naive_local(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("valid_time_local must be AOI-local naive")
        return value

    @field_validator("valid_time_utc")
    @classmethod
    def _utc_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("valid_time_utc must be timezone-aware")
        if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
            raise ValueError("valid_time_utc must be UTC")
        return value

    @model_validator(mode="after")
    def _invariants(self) -> ZoneThermalObservation:
        if self.local_date != self.valid_time_local.date():
            raise ValueError("local_date must match valid_time_local")
        if (
            self.observation_kind == ObservationKind.INSTANT
            and self.local_hour != self.valid_time_local.hour
        ):
            raise ValueError("local_hour must match valid_time_local for instants")
        derived = local_to_utc(self.valid_time_local, self.timezone)
        if derived.replace(microsecond=0) != self.valid_time_utc.replace(microsecond=0):
            raise ValueError("valid_time_utc must be the UTC conversion of local+timezone")
        present = self.temperature_c is not None and self.temperature_c == self.temperature_c
        if present and self.coverage_status != CoverageStatus.OK:
            raise ValueError("finite temperature_c requires coverage_status=ok")
        if not present and self.coverage_status == CoverageStatus.OK:
            raise ValueError("coverage_status=ok requires finite temperature_c")
        if not present and self.temperature_c == 0:
            raise ValueError("missing must be null, not 0")
        if self.quality.interpolated or self.quality.silent_fill:
            raise ValueError("interpolated/silent_fill records are invalid")
        if self.observation_kind == ObservationKind.WINDOW_AGGREGATE:
            if self.statistic == ThermalStatistic.INSTANT:
                raise ValueError("window_aggregate cannot claim statistic=instant")
            if "window_aggregate" not in self.quality.flags:
                raise ValueError("window_aggregate requires quality flag window_aggregate")
        if self.analysis_geography.area_id != self.area_id:
            raise ValueError("analysis_geography.area_id must match")
        if self.provenance.geometry_version != self.analysis_geography.zone_geometry_version:
            raise ValueError("provenance.geometry_version is analysis geography only")
        if self.provenance.source_mode != self.source_mode:
            raise ValueError("provenance.source_mode must match observation")
        if self.aggregation_spec_version != self.provenance.aggregation_spec_version:
            raise ValueError("aggregation version must be stamped once")
        if self.observation_geometry.role != OBSERVATION_GEOMETRY_ROLE:
            raise ValueError("observation geometry cannot become analysis geography")
        return self


class ZoneThermalTimeSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["ZoneThermalTimeSeries"] = "ZoneThermalTimeSeries"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    spatial_scope: Literal["zone"] = "zone"
    timezone: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    temperature_quantity: TemperatureQuantity
    sampling_design: SamplingDesign
    temporal_mode: str | None = None
    upstream_time_semantics: Literal["aoi_local_time"] = UPSTREAM_AOI_LOCAL
    window_id: str | None = None
    analysis_geography: AnalysisGeography
    aggregation_spec_version: str = Field(min_length=1)
    aggregation_method: Literal["centroid_within_mean"] = CENTROID_WITHIN_MEAN
    resolution_m: Literal[60, 80, 100] | None = 100
    coverage: TemporalCoverage
    observations: list[ZoneThermalObservation] = Field(default_factory=list)
    expected_slot_count: int = Field(ge=1)
    present_slot_count: int = Field(ge=0)
    quality: Quality
    provenance: TemporalProvenance
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _homogeneous(self) -> ZoneThermalTimeSeries:
        present = 0
        seen: set[datetime] = set()
        for obs in self.observations:
            if obs.area_id != self.area_id or obs.zone_id != self.zone_id:
                raise ValueError("series observations must share area_id and zone_id")
            if obs.source_mode != self.source_mode:
                raise ValueError("series cannot mix source_mode")
            if obs.temperature_quantity != self.temperature_quantity:
                raise ValueError("series cannot mix temperature_quantity")
            if obs.analysis_geography.zone_geometry_version != (
                self.analysis_geography.zone_geometry_version
            ):
                raise ValueError("series cannot mix zone_geometry_version")
            if obs.aggregation_spec_version != self.aggregation_spec_version:
                raise ValueError("series cannot mix aggregation_spec_version")
            if obs.valid_time_local in seen:
                raise ValueError("duplicate valid_time_local in series")
            seen.add(obs.valid_time_local)
            if obs.coverage_status == CoverageStatus.OK:
                present += 1
        if present != self.present_slot_count:
            raise ValueError("present_slot_count must count coverage_status=ok")
        if self.present_slot_count > self.expected_slot_count:
            raise ValueError("present_slot_count cannot exceed expected_slot_count")
        return self


class DailySlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_hour: int = Field(ge=0, le=23)
    valid_time_local: datetime | None = None
    valid_time_utc: datetime | None = None
    present: bool
    temperature_c: float | None = None
    n_valid_zones: int | None = Field(default=None, ge=0, le=25)
    spatial_coverage_class: TemporalCoverageClass | None = None
    observation: ZoneThermalObservation | None = None

    @model_validator(mode="after")
    def _slot_presence(self) -> DailySlot:
        if self.present:
            if self.temperature_c is None:
                raise ValueError("present slot requires finite temperature_c")
        else:
            if self.temperature_c is not None:
                raise ValueError("missing slot temperature_c must be null")
        return self


class DailyThermalProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["DailyThermalProfile"] = "DailyThermalProfile"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str | None = None
    spatial_scope: SpatialScope
    local_date: date
    timezone: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    temperature_quantity: TemperatureQuantity
    sampling_design: SamplingDesign
    window_id: str = Field(min_length=1)
    analysis_geography: AnalysisGeography
    aggregation_spec_version: str = Field(min_length=1)
    aggregation_method: Literal["centroid_within_mean"] = CENTROID_WITHIN_MEAN
    slots: list[DailySlot]
    min_temperature_c_among_observed: float | None = None
    max_temperature_c_among_observed: float | None = None
    mean_temperature_c_among_observed: float | None = None
    min_temperature_c_as_day: float | None = None
    max_temperature_c_as_day: float | None = None
    time_of_minimum_local: str | None = None
    time_of_peak_local: str | None = None
    day_night_difference_c: float | None = None
    cooling_drop_c: float | None = None
    coverage: TemporalCoverage
    claim_permissions: ClaimPermissions
    quality: Quality
    provenance: TemporalProvenance

    @model_validator(mode="after")
    def _day_rules(self) -> DailyThermalProfile:
        expected = EXPECTED_HOURS[self.sampling_design]
        if len(self.slots) != expected:
            raise ValueError("slots length must equal sampling_design expected hours")
        hours = [slot.local_hour for slot in self.slots]
        if len(hours) != len(set(hours)):
            raise ValueError("duplicate local_hour in daily slots")
        if self.spatial_scope == SpatialScope.ZONE and not self.zone_id:
            raise ValueError("zone daily profile requires zone_id")
        if self.spatial_scope == SpatialScope.AOI and self.zone_id is not None:
            raise ValueError("AOI daily profile must not carry zone_id")
        if not self.claim_permissions.min_max_as_period:
            if self.min_temperature_c_as_day is not None or self.max_temperature_c_as_day is not None:
                raise ValueError("as-day min/max require claim_permissions.min_max_as_period")
        if not self.claim_permissions.time_of_peak_as_extremum and self.time_of_peak_local is not None:
            raise ValueError("time_of_peak_local requires permission")
        if not self.claim_permissions.time_of_min_as_extremum and self.time_of_minimum_local is not None:
            raise ValueError("time_of_minimum_local requires permission")
        if not self.claim_permissions.day_night_difference and self.day_night_difference_c is not None:
            raise ValueError("day_night_difference_c requires permission")
        if self.sampling_design == SamplingDesign.TYPE2_WINDOW:
            if any(slot.present and slot.observation and slot.observation.observation_kind == ObservationKind.INSTANT for slot in self.slots):
                raise ValueError("TYPE2_WINDOW cannot emit instant hourly slots")
        return self


class MonthlyThermalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["MonthlyThermalSummary"] = "MonthlyThermalSummary"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str | None = None
    spatial_scope: SpatialScope
    year: int = Field(ge=1900)
    month: int = Field(ge=1, le=12)
    window_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    temperature_quantity: TemperatureQuantity
    sampling_design: SamplingDesign
    n_calendar_days: int = Field(ge=28, le=31)
    analysis_geography: AnalysisGeography
    aggregation_spec_version: str = Field(min_length=1)
    aggregation_method: Literal["centroid_within_mean"] = CENTROID_WITHIN_MEAN
    mean_temperature_c: float | None = None
    nighttime_mean_temperature_c: float | None = None
    min_temperature_c_among_observed: float | None = None
    max_temperature_c_among_observed: float | None = None
    coverage: TemporalCoverage
    claim_permissions: ClaimPermissions
    quality: Quality
    provenance: TemporalProvenance

    @model_validator(mode="after")
    def _month_mean_gate(self) -> MonthlyThermalSummary:
        if (
            self.mean_temperature_c is not None
            and self.claim_permissions.headline_mean_as_period is False
        ):
            # Value may still be stored as among-observed only when labeled via coverage.
            if self.coverage.coverage_class in {
                TemporalCoverageClass.PARTIAL,
                TemporalCoverageClass.INSUFFICIENT,
            }:
                pass
        if self.mean_temperature_c == 0 and self.coverage.n_present == 0:
            raise ValueError("empty month mean cannot be 0")
        return self


class SeasonalThermalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["SeasonalThermalSummary"] = "SeasonalThermalSummary"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str | None = None
    spatial_scope: SpatialScope
    season_id: str = Field(min_length=1)
    window_id: str = Field(min_length=1)
    year_label: int
    local_start_date: date | None = None
    local_end_date: date | None = None
    timezone: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    temperature_quantity: TemperatureQuantity
    sampling_design: SamplingDesign
    analysis_geography: AnalysisGeography
    aggregation_spec_version: str = Field(min_length=1)
    aggregation_method: Literal["centroid_within_mean"] = CENTROID_WITHIN_MEAN
    mean_temperature_c: float | None = None
    nighttime_mean_temperature_c: float | None = None
    daytime_mean_temperature_c: float | None = None
    day_night_difference_c: float | None = None
    months: list[MonthlyThermalSummary] = Field(default_factory=list)
    coverage: TemporalCoverage
    claim_permissions: ClaimPermissions
    quality: Quality
    provenance: TemporalProvenance

    @model_validator(mode="after")
    def _child_months(self) -> SeasonalThermalSummary:
        for month in self.months:
            if month.source_mode != self.source_mode:
                raise ValueError("season cannot mix source_mode across months")
            if month.temperature_quantity != self.temperature_quantity:
                raise ValueError("season cannot mix temperature_quantity")
            if (
                month.analysis_geography.zone_geometry_version
                != self.analysis_geography.zone_geometry_version
            ):
                raise ValueError("season cannot mix zone_geometry_version")
        return self


class YearSide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int
    window_id: str = Field(min_length=1)
    mean_temperature_c: float | None = None
    nighttime_mean_temperature_c: float | None = None
    coverage: TemporalCoverage
    zone_geometry_version: str = Field(min_length=1)
    aggregation_spec_version: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    sampling_design: SamplingDesign
    temperature_quantity: TemperatureQuantity
    timezone: str = Field(min_length=1)


class FrameChecks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_geometry_version: bool
    expected_zone_count: bool
    aggregation_spec_version: bool
    sampling_design: bool
    window_family: bool
    timezone: bool
    source_mode: bool
    temperature_quantity: bool

    def all_pass(self) -> bool:
        return all(
            (
                self.zone_geometry_version,
                self.expected_zone_count,
                self.aggregation_spec_version,
                self.sampling_design,
                self.window_family,
                self.timezone,
                self.source_mode,
                self.temperature_quantity,
            )
        )


class YearComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["YearComparisonResult"] = "YearComparisonResult"
    contract_version: Literal["hva-signal-temporal-domain-v1"] = (
        TEMPORAL_DOMAIN_CONTRACT_VERSION
    )
    area_id: str = Field(min_length=1)
    zone_id: str | None = None
    spatial_scope: SpatialScope
    window_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    source_mode: TemporalSourceMode
    temperature_quantity: TemperatureQuantity
    sampling_design: SamplingDesign
    analysis_geography: AnalysisGeography | None = None
    aggregation_spec_version: str | None = None
    left: YearSide
    right: YearSide
    comparability: Comparability
    fail_closed_reasons: list[str] = Field(default_factory=list)
    frame_checks: FrameChecks
    coverage: TemporalCoverage
    mean_difference_c: float | None = None
    nighttime_difference_c: float | None = None
    persistence_n_of_m_left: int | None = Field(default=None, ge=0)
    persistence_m_left: int | None = Field(default=None, ge=0)
    persistence_n_of_m_right: int | None = Field(default=None, ge=0)
    persistence_m_right: int | None = Field(default=None, ge=0)
    persistence_n_difference: int | None = None
    cumulative_departure_difference: float | None = None
    claim_permissions: ClaimPermissions
    quality: Quality
    provenance: TemporalProvenance

    @model_validator(mode="after")
    def _yoy_fail_closed(self) -> YearComparisonResult:
        if not self.frame_checks.all_pass():
            if self.comparability != Comparability.INCOMPARABLE:
                raise ValueError("failed frame check requires INCOMPARABLE")
            if self.mean_difference_c is not None:
                raise ValueError("INCOMPARABLE cannot emit mean_difference_c")
        if self.comparability == Comparability.INCOMPARABLE and (
            self.mean_difference_c is not None or self.nighttime_difference_c is not None
        ):
            raise ValueError("INCOMPARABLE forbids headline differences")
        pair = self.coverage.coverage_class
        if self.claim_permissions.headline_year_difference:
            if self.comparability != Comparability.COMPARABLE:
                raise ValueError("headline YoY requires COMPARABLE")
            if pair not in {TemporalCoverageClass.FULL, TemporalCoverageClass.ADEQUATE}:
                raise ValueError("headline YoY requires pair FULL or ADEQUATE")
        if (
            not self.claim_permissions.headline_year_difference
            and self.mean_difference_c is not None
        ):
            raise ValueError("mean_difference_c requires headline_year_difference")
        if self.left.zone_geometry_version != self.right.zone_geometry_version:
            if self.frame_checks.zone_geometry_version:
                raise ValueError("geometry mismatch cannot pass frame_checks")
        return self
