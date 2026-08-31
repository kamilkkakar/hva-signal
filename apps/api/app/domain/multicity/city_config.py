"""Server-owned multi-city catalog definitions.

Phoenix keeps its existing local geography identity. Cross-city comparison
uses a separate comparable-layer stamp so callers do not confuse the Phoenix
demo AOI with the multi-city comparison contract.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.area_registry import PHOENIX_AREA_SELECTION_POLICY_VERSION
from app.domain.multicity.geography import (
    CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
    MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
)

PLACE_GEOID_PATTERN = re.compile(r"^[0-9]{7}$")
IANA_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+)+$")


class CityId(StrEnum):
    PHOENIX = "phoenix"
    LAS_VEGAS = "las_vegas"
    TUCSON = "tucson"
    LOS_ANGELES = "los_angeles"


class CapabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    READY_FOR_ACQUISITION = "READY_FOR_ACQUISITION"


class CapabilityKey(StrEnum):
    LOCAL_STORY = "local_story"
    SELECTED_TIME_THERMAL = "selected_time_thermal"
    MATCHED_NIGHTTIME = "matched_nighttime"
    OBSERVED_INSTANTS = "observed_instants"
    ACS_CONTEXT = "acs_context"
    LOCAL_CANOPY = "local_canopy"
    CROSS_CITY_CANOPY = "cross_city_canopy"
    CROSS_CITY_EXPLORER = "cross_city_explorer"
    TYPE1_LIVE = "type1_live"


class CitySelectorEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    city_id: CityId
    display_name: str = Field(min_length=1)
    state: str = Field(min_length=2)
    outline_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class CityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    city_id: CityId
    display_name: str = Field(min_length=1)
    state: str = Field(min_length=2)
    place_geoid: str
    timezone: str
    area_id: str = Field(min_length=1)
    outline_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    analysis_geography_version: Literal["MULTI_CITY_ANALYSIS_GEOGRAPHY_V1"] = (
        MULTI_CITY_ANALYSIS_GEOGRAPHY_V1
    )
    comparison_geography_version: Literal["CROSS_CITY_COMPARISON_GEOGRAPHY_V1"] = (
        CROSS_CITY_COMPARISON_GEOGRAPHY_V1
    )
    local_geography_version: str | None = None
    city_config_version: str = Field(min_length=1)
    capabilities: dict[CapabilityKey, CapabilityStatus]

    @field_validator("place_geoid")
    @classmethod
    def _place_geoid_is_census_place(cls, value: str) -> str:
        if not PLACE_GEOID_PATTERN.fullmatch(value):
            raise ValueError("place_geoid must be a 7-digit Census place GEOID")
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone_is_iana(cls, value: str) -> str:
        if not IANA_TIMEZONE_PATTERN.fullmatch(value):
            raise ValueError("timezone must be an IANA Area/Location name")
        return value

    @model_validator(mode="after")
    def _phoenix_local_identity_stays_explicit(self) -> CityConfig:
        if self.city_id == CityId.PHOENIX:
            if self.area_id != "phoenix-demo":
                raise ValueError("Phoenix area_id must stay bound to phoenix-demo")
            if self.local_geography_version != PHOENIX_AREA_SELECTION_POLICY_VERSION:
                raise ValueError(
                    "Phoenix local_geography_version must keep the PHX demo policy identity"
                )
        elif self.local_geography_version is not None:
            raise ValueError("non-Phoenix cities must not claim a Phoenix local geography")
        return self

    def selector_entry(self) -> CitySelectorEntry:
        return CitySelectorEntry(
            city_id=self.city_id,
            display_name=self.display_name,
            state=self.state,
            outline_color=self.outline_color,
        )

