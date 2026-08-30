"""Unpublished public Place + Geography DTOs.

Bound only when HVA_PUBLIC_GEOGRAPHY is explicitly enabled. extra=forbid.
Zero vendor fields. National reference_readiness is always NOT_PREPARED.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PUBLIC_GEOGRAPHY_CONTRACT_VERSION = "hva-signal-public-geography-v1"
FROZEN_CENSUS_VINTAGE = "2025"
FROZEN_RESOLVER_POLICY_ID = "NATIONAL_PLACE_GEOGRAPHY_V1"
NATIONAL_AGGREGATION_SPEC_VERSION = (
    "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
)
NATIONAL_ALGORITHM_ID = "ALG1_GREEDY_LEX_PLACE_INTPT_V1"
LEGACY_PHOENIX_AREA_ID = "phoenix-demo"
ANALYSIS_WINDOW_KIND = "compact_25_tract_window"
EXPECTED_ZONE_COUNT = 25
POLL_INTERVAL_MS = 1500
POLL_HORIZON_MS = 180_000

FORBIDDEN_GEOGRAPHY_BODY_FIELDS = frozenset(
    {
        "area_id",
        "city",
        "login",
        "user",
        "approved",
        "signals",
        "spend",
        "fortyguard",
        "phoenix-demo",
        "phoenix_demo",
        "q_A",
        "q_a",
    }
)


class ResolutionOutcome(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class GeographyReasonCode(StrEnum):
    GEOGRAPHY_RESOLVED = "GEOGRAPHY_RESOLVED"
    UNKNOWN_PLACE = "UNKNOWN_PLACE"
    AMBIGUOUS_PLACE = "AMBIGUOUS_PLACE"
    INVALID_PLACE_GEOID = "INVALID_PLACE_GEOID"
    INVALID_AREA_ID = "INVALID_AREA_ID"
    AREA_ID_NOT_NATIONAL = "AREA_ID_NOT_NATIONAL"
    CONTRACT_VERSION_MISMATCH = "CONTRACT_VERSION_MISMATCH"
    VINTAGE_MISMATCH = "VINTAGE_MISMATCH"
    UNSUPPORTED_POLICY = "UNSUPPORTED_POLICY"
    FORBIDDEN_FIELD = "FORBIDDEN_FIELD"
    UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
    EMPTY_PLACE = "EMPTY_PLACE"
    INSUFFICIENT_ELIGIBLE_TRACTS = "INSUFFICIENT_ELIGIBLE_TRACTS"
    INSUFFICIENT_CONNECTED_TRACTS = "INSUFFICIENT_CONNECTED_TRACTS"
    GROWTH_FRONTIER_EXHAUSTED = "GROWTH_FRONTIER_EXHAUSTED"
    MULTI_TIMEZONE_AOI = "MULTI_TIMEZONE_AOI"
    TIMEZONE_NOT_FOUND = "TIMEZONE_NOT_FOUND"
    GEOGRAPHY_STORE_CORRUPT = "GEOGRAPHY_STORE_CORRUPT"
    RESOLVER_INVARIANT_VIOLATION = "RESOLVER_INVARIANT_VIOLATION"
    SUBSTRATE_UNAVAILABLE = "SUBSTRATE_UNAVAILABLE"
    GEOGRAPHY_NOT_READY = "GEOGRAPHY_NOT_READY"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class PublicReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: GeographyReasonCode
    message: str


class PublicGeographyError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-geography-v1"] = (
        PUBLIC_GEOGRAPHY_CONTRACT_VERSION
    )
    reason: PublicReason


class PlaceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    place_geoid: str = Field(pattern=r"^[0-9]{7}$")
    official_name: str
    place_name: str
    display_name: str
    state_fips: str = Field(pattern=r"^[0-9]{2}$")
    state_abbreviation: str = Field(pattern=r"^[A-Z]{2}$")
    place_type: Literal["incorporated", "cdp", "consolidated_city_balance"]
    scope: Literal["conus_plus_dc", "alaska", "hawaii", "puerto_rico", "island_area"]
    resolution_eligible: bool


class PlaceSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-geography-v1"] = (
        PUBLIC_GEOGRAPHY_CONTRACT_VERSION
    )
    query: str
    matches: list[PlaceCandidate]
    reason: PublicReason | None = None


class PlaceIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-geography-v1"] = (
        PUBLIC_GEOGRAPHY_CONTRACT_VERSION
    )
    place: PlaceCandidate
    predicted_area_id: str


class GeographyResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-geography-v1"]
    place_geoid: str = Field(pattern=r"^[0-9]{7}$")
    census_vintage: Literal["2025"] | None = None
    resolver_policy_id: Literal["NATIONAL_PLACE_GEOGRAPHY_V1"] | None = None

    @field_validator("place_geoid")
    @classmethod
    def _digits(cls, value: str) -> str:
        geoid = value.strip()
        if not geoid.isdigit() or len(geoid) != 7:
            raise ValueError("place_geoid must be a 7-digit Census place GEOID")
        return geoid


class AnalysisWindowFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["compact_25_tract_window"] = ANALYSIS_WINDOW_KIND
    expected_zone_count: Literal[25] = EXPECTED_ZONE_COUNT
    not_city_coverage: Literal[True] = True
    not_heat_district: Literal[True] = True


class GeographyIdentityPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_geoids: list[str] = Field(min_length=25, max_length=25)
    expected_zone_count: Literal[25] = EXPECTED_ZONE_COUNT
    timezone: str
    geometry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    zone_geometry_version: str
    aggregation_spec_version: Literal[
        "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
    ] = NATIONAL_AGGREGATION_SPEC_VERSION


class GeographyProvenancePublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm_id: Literal["ALG1_GREEDY_LEX_PLACE_INTPT_V1"] = NATIONAL_ALGORITHM_ID
    seed_geoid: str = Field(pattern=r"^[0-9]{11}$")
    seed_rule_id: str


class GeographyPollHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    interval_ms: Literal[1500] = POLL_INTERVAL_MS
    horizon_ms: Literal[180000] = POLL_HORIZON_MS


class GeographyResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-geography-v1"] = (
        PUBLIC_GEOGRAPHY_CONTRACT_VERSION
    )
    area_id: str
    place: PlaceCandidate
    census_vintage: Literal["2025"] = FROZEN_CENSUS_VINTAGE
    resolver_policy_id: Literal["NATIONAL_PLACE_GEOGRAPHY_V1"] = (
        FROZEN_RESOLVER_POLICY_ID
    )
    resolution_outcome: ResolutionOutcome
    supported: bool | None
    geography_readiness: Literal[
        "UNRESOLVED", "RESOLVING", "GEOGRAPHY_READY", "FAILED"
    ]
    reference_readiness: Literal["NOT_PREPARED"] = "NOT_PREPARED"
    snapshot_capable: bool
    historical_signal_capable: Literal[False] = False
    display_label: str
    analysis_window_caption: str
    analysis_window: AnalysisWindowFlags = Field(default_factory=AnalysisWindowFlags)
    identity: GeographyIdentityPublic | None = None
    provenance: GeographyProvenancePublic | None = None
    reason: PublicReason | None = None
    poll: GeographyPollHint | None = None
