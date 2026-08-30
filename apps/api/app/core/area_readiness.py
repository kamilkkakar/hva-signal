"""Geography readiness versus historical-reference readiness.

Signal B (selected-time snapshot) needs a resolved 25-zone geography.
Signal A (historical q_A / Decision 8) needs that geography plus a prepared
reference package.

Geometry serving now uses resolve_area_geography and does not open the
historical reference file. Historical analysis still uses
resolve_ready_area_package plus the frozen Phoenix AreaConfig guard.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

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

    @property
    def can_serve_geometry(self) -> bool:
        return self.geography == GeographyReadiness.GEOGRAPHY_READY

    @property
    def can_process_snapshot(self) -> bool:
        return self.snapshot_capable

    @property
    def can_run_historical_signal(self) -> bool:
        return self.historical_signal_capable


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
    """Geometry serving uses the geography resolver and does not open reference."""
    return False


def derive_area_capabilities(
    area_id: str,
    *,
    root: Path | None = None,
) -> AreaCapabilityState:
    """Derive geography vs reference capability from stored artifacts."""
    from app.core.area_registry import (
        AreaRegistryError,
        UnsupportedAreaError,
        resolve_area_geography,
        resolve_ready_area_package,
    )

    try:
        resolve_area_geography(area_id, root=root)
    except UnsupportedAreaError:
        return AreaCapabilityState(
            geography=GeographyReadiness.UNRESOLVED,
            reference=ReferenceReadiness.NOT_PREPARED,
        )
    except AreaRegistryError:
        return AreaCapabilityState(
            geography=GeographyReadiness.FAILED,
            reference=ReferenceReadiness.NOT_PREPARED,
        )

    try:
        resolve_ready_area_package(area_id, root=root)
    except AreaRegistryError as exc:
        message = str(exc).lower()
        if "missing" in message:
            reference = ReferenceReadiness.NOT_PREPARED
        else:
            reference = ReferenceReadiness.FAILED
        return AreaCapabilityState(
            geography=GeographyReadiness.GEOGRAPHY_READY,
            reference=reference,
        )
    return AreaCapabilityState(
        geography=GeographyReadiness.GEOGRAPHY_READY,
        reference=ReferenceReadiness.READY,
    )
