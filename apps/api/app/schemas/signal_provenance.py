"""Per-signal public provenance view. Unpublished. Not in live OpenAPI.

Contract: hva-signal-public-provenance-v1 (07_PROVENANCE_CONTRACT.md).
Signal B never carries reference_version or reference_source.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.signals import SignalAvailability, ThermalSignalKind

BannerLabel = Literal[
    "FORTYGUARD LIVE",
    "FORTYGUARD CACHED",
    "REPLAY",
    "PARTIAL",
    "UNAVAILABLE",
]

PUBLIC_PROVENANCE_CONTRACT_VERSION: Final = "hva-signal-public-provenance-v1"
FROZEN_SIGNAL_A_HOUR: Final = 3
GEOMETRY_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")

PHOENIX_AGGREGATION_SPEC: Final = "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
NATIONAL_AGGREGATION_SPEC: Final = (
    "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
)
PHOENIX_REFERENCE_TOKEN: Final = "PHX_ZTSI_REF"
PHOENIX_GEOMETRY_TOKEN: Final = "PHX_DEMO_AOI"
NATIONAL_AREA_PREFIX: Final = "us-place-"

A_REQUIRED_WHEN_COMPUTED: Final[frozenset[str]] = frozenset(
    {
        "source",
        "data_status",
        "target_timestamp",
        "timezone",
        "geometry_version",
        "aggregation_spec_version",
        "reference_source",
        "reference_version",
    }
)
B_REQUIRED_WHEN_PATH_KNOWN: Final[frozenset[str]] = frozenset(
    {
        "source",
        "data_status",
        "target_timestamp",
        "timezone",
        "geometry_version",
        "geometry_sha256",
        "aggregation_spec_version",
    }
)
B_FORBIDDEN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "reference_version",
        "reference_source",
        "reference_source_sha256",
        "hazard_spread",
        "q_A",
        "historical_result",
        "decision8",
        "legacy_thermal_source",
    }
)
SOURCE_STATUS_PAIRS: Final[dict[ThermalDataSource, frozenset[DataStatus]]] = {
    ThermalDataSource.REPLAY: frozenset(
        {DataStatus.REPLAY, DataStatus.PARTIAL, DataStatus.UNAVAILABLE}
    ),
    ThermalDataSource.FORTYGUARD_CACHED: frozenset(
        {DataStatus.CACHED, DataStatus.PARTIAL, DataStatus.UNAVAILABLE}
    ),
    ThermalDataSource.FORTYGUARD_LIVE: frozenset(
        {DataStatus.LIVE, DataStatus.PARTIAL, DataStatus.UNAVAILABLE}
    ),
}

A_UNCOMPUTED_AVAILABILITY: Final[frozenset[SignalAvailability]] = frozenset(
    {
        SignalAvailability.NOT_PREPARED,
        SignalAvailability.INSUFFICIENT_REFERENCE,
        SignalAvailability.NOT_REQUESTED,
        SignalAvailability.PENDING,
        SignalAvailability.FETCHING,
        SignalAvailability.WAITING_FOR_APPROVAL,
        SignalAvailability.AUTHORIZATION_INSUFFICIENT,
    }
)


class PublicSignalProvenanceView(BaseModel):
    """Display/API helper for one signal. extra=forbid. Not a FastAPI response model."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["hva-signal-public-provenance-v1"] = (
        PUBLIC_PROVENANCE_CONTRACT_VERSION
    )
    signal_kind: ThermalSignalKind
    source: ThermalDataSource | None = None
    data_status: DataStatus | None = None
    target_timestamp: datetime | None = None
    timezone: str | None = None
    geometry_version: str | None = None
    geometry_sha256: str | None = None
    aggregation_spec_version: str | None = None
    reference_version: str | None = None
    reference_source: str | None = None
    request_fingerprint: str | None = None

    @field_validator("geometry_sha256")
    @classmethod
    def _geometry_sha256_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not GEOMETRY_SHA256_PATTERN.fullmatch(value):
            raise ValueError("geometry_sha256 must be 64 lowercase hex chars")
        return value

    @field_validator("reference_version", "reference_source")
    @classmethod
    def _b_has_no_reference(cls, value: str | None, info):
        kind = info.data.get("signal_kind")
        if kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT and value is not None:
            raise ValueError("Signal B provenance cannot carry a historical reference")
        return value

    @model_validator(mode="after")
    def _pair_source_and_status(self) -> PublicSignalProvenanceView:
        if self.source is None or self.data_status is None:
            return self
        allowed = SOURCE_STATUS_PAIRS[self.source]
        if self.data_status not in allowed:
            raise ValueError(
                "illegal source/data_status pair; live does not beat cached"
            )
        return self

    @model_validator(mode="after")
    def _a_hour_frozen(self) -> PublicSignalProvenanceView:
        if (
            self.signal_kind == ThermalSignalKind.HISTORICAL_NORMALIZED
            and self.target_timestamp is not None
        ):
            ts = self.target_timestamp
            if ts.tzinfo is not None:
                raise ValueError("Signal A target_timestamp must be AOI-local naive")
            if (
                ts.hour != FROZEN_SIGNAL_A_HOUR
                or ts.minute != 0
                or ts.second != 0
                or ts.microsecond != 0
            ):
                raise ValueError("Signal A time is frozen at 03:00; do not silently change it")
        if (
            self.signal_kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT
            and self.target_timestamp is not None
        ):
            ts = self.target_timestamp
            if ts.tzinfo is not None:
                raise ValueError("Signal B target_timestamp must be AOI-local naive")
            if ts.minute != 0 or ts.second != 0 or ts.microsecond != 0:
                raise ValueError("Signal B time is hour precision only")
        return self

    def public_dump(self) -> dict[str, object]:
        """Wire-shaped dict. B omits reference keys entirely (absent, not null)."""
        data = self.model_dump(mode="json")
        if self.signal_kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            data.pop("reference_version", None)
            data.pop("reference_source", None)
        return data


class ProvenanceDisplayState(BaseModel):
    """UI helper derived from one signal view. Never a blended A+B badge."""

    model_config = ConfigDict(extra="forbid")

    signal_kind: ThermalSignalKind
    banner: BannerLabel
    path_stem: str | None = None
    lines: tuple[str, ...] = Field(default_factory=tuple)
    show_reference: bool
    show_decision8: bool
    show_qa_hover: bool
    legacy_thermal_source: str | None = None
