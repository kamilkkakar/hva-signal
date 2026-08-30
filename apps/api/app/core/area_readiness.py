"""Geography readiness versus historical-reference readiness.

Signal B (selected-time snapshot) needs a resolved 25-zone geography.
Signal A (historical q_A / Decision 8) needs that geography plus a prepared
reference package.

This module does not change AreaPackageManifest V2, does not serve geometry
without a READY reference, and does not call a vendor. It is the typed
lifecycle that production registry resolution does not yet implement.

Current production: resolve_ready_area_package / GET geometry still require a
validated reference file. SNAPSHOT_CAPABLE is therefore not a live API state.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GeographyReadiness(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVING = "RESOLVING"
    GEOGRAPHY_READY = "GEOGRAPHY_READY"
    FAILED = "FAILED"


class ReferenceReadiness(StrEnum):
    NOT_PREPARED = "NOT_PREPARED"
    PREPARING = "PREPARING"
    READY = "READY"
    INSUFFICIENT = "INSUFFICIENT"
    FAILED = "FAILED"


class AreaCapabilityState(BaseModel):
    """Independent geography and reference states. Not a single READY bit."""

    model_config = ConfigDict(extra="forbid")

    geography: GeographyReadiness
    reference: ReferenceReadiness

    @property
    def snapshot_capable(self) -> bool:
        return self.geography == GeographyReadiness.GEOGRAPHY_READY

    @property
    def historical_signal_capable(self) -> bool:
        return (
            self.geography == GeographyReadiness.GEOGRAPHY_READY
            and self.reference == ReferenceReadiness.READY
        )


class GeographyIdentity(BaseModel):
    """Minimum assets for a zone-level selected-time snapshot.

    No historical panel. No AreaConfig Decision 1B block. No fake READY package.
    """

    model_config = ConfigDict(extra="forbid")

    area_id: str = Field(min_length=1)
    zone_geoids: tuple[str, ...]
    expected_zone_count: int = Field(gt=0)
    timezone: str = Field(min_length=1)
    aggregation_spec_version: str = Field(min_length=1)
    area_selection_policy_version: str = Field(min_length=1)
    geometry_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _zone_count_matches(self) -> GeographyIdentity:
        if len(self.zone_geoids) != self.expected_zone_count:
            raise ValueError(
                "zone_geoids length must equal expected_zone_count"
            )
        if len(set(self.zone_geoids)) != len(self.zone_geoids):
            raise ValueError("zone_geoids must be unique")
        return self


def snapshot_capable(
    identity: GeographyIdentity,
    *,
    geography: GeographyReadiness,
    reference: ReferenceReadiness | None = None,
) -> bool:
    """Signal B may proceed when geography is ready. Reference is irrelevant."""
    del reference
    if geography != GeographyReadiness.GEOGRAPHY_READY:
        return False
    return bool(
        identity.area_id
        and identity.timezone
        and identity.aggregation_spec_version
        and identity.area_selection_policy_version
        and identity.expected_zone_count > 0
        and len(identity.zone_geoids) == identity.expected_zone_count
    )


def historical_signal_capable(
    identity: GeographyIdentity,
    *,
    geography: GeographyReadiness,
    reference: ReferenceReadiness,
) -> bool:
    """Signal A requires geography plus a prepared historical reference."""
    return snapshot_capable(
        identity, geography=geography
    ) and reference == ReferenceReadiness.READY


def current_registry_requires_reference_for_geometry() -> bool:
    """Production geometry delivery still validates a reference file."""
    return True
