"""Structured evidence behind multi-city capability states.

Operational cities and validation-only jurisdictions are deliberately separate:
the latter document national-readiness gaps without making those places selectable.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.multicity.city_config import CapabilityStatus, CityConfig


class EvidenceState(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_YET_TESTED = "NOT_YET_TESTED"


class CapabilityEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: EvidenceState
    reason: str = Field(min_length=1)
    affected_scope: str = Field(min_length=1)
    next_check: str = Field(min_length=1)


class ValidationJurisdiction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    jurisdiction_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    region_code: str | None = None
    validation_class: Literal["SMALL_PLACE", "ALASKA", "HAWAII", "UNSUPPORTED"]
    selectable: Literal[False] = False
    state: EvidenceState
    reason: str = Field(min_length=1)
    affected_scope: list[str] = Field(min_length=1)
    next_check: str = Field(min_length=1)
    capabilities: dict[str, CapabilityEvidence]


def operational_capability_evidence(
    city: CityConfig,
) -> dict[str, CapabilityEvidence]:
    """Explain every status without interpreting it as heat severity."""

    evidence: dict[str, CapabilityEvidence] = {}
    for capability, status in city.capabilities.items():
        scope = capability.value
        if status is CapabilityStatus.AVAILABLE:
            item = CapabilityEvidence(
                state=EvidenceState.VERIFIED,
                reason=(
                    f"{city.display_name} publishes the server-owned artifacts required "
                    f"by {scope} under {city.city_config_version}."
                ),
                affected_scope=scope,
                next_check="Re-run contract and artifact-integrity checks after a source or schema change.",
            )
        elif status is CapabilityStatus.PARTIAL:
            item = CapabilityEvidence(
                state=EvidenceState.PARTIAL,
                reason=(
                    f"{city.display_name} has some published {scope} evidence, but the full "
                    "capability contract is not closed."
                ),
                affected_scope=scope,
                next_check="Close the missing contract checks before presenting this capability as complete.",
            )
        elif status is CapabilityStatus.READY_FOR_ACQUISITION:
            item = CapabilityEvidence(
                state=EvidenceState.NOT_YET_TESTED,
                reason=(
                    f"{city.display_name} has a server-owned identity for {scope}, but catalog "
                    "readiness alone is not evidence of a completed request."
                ),
                affected_scope=scope,
                next_check="Reconcile durable activity evidence before any new acquisition attempt.",
            )
        elif status is CapabilityStatus.INSUFFICIENT_EVIDENCE:
            item = CapabilityEvidence(
                state=EvidenceState.VALIDATION_FAILED,
                reason=(
                    f"{city.display_name} does not meet the published evidence threshold for {scope}."
                ),
                affected_scope=scope,
                next_check="Repair or add evidence, then repeat the capability acceptance test.",
            )
        else:
            item = CapabilityEvidence(
                state=EvidenceState.UNAVAILABLE,
                reason=f"The current server package has no usable {scope} evidence for {city.display_name}.",
                affected_scope=scope,
                next_check="Validate and package the required source before enabling this capability.",
            )
        evidence[scope] = item
    return evidence


def _untested(
    *, reason: str, scope: str, next_check: str
) -> CapabilityEvidence:
    return CapabilityEvidence(
        state=EvidenceState.NOT_YET_TESTED,
        reason=reason,
        affected_scope=scope,
        next_check=next_check,
    )


VALIDATION_JURISDICTIONS: tuple[ValidationJurisdiction, ...] = (
    ValidationJurisdiction(
        jurisdiction_id="yuma_az",
        display_name="Yuma",
        region_code="AZ",
        validation_class="SMALL_PLACE",
        state=EvidenceState.NOT_YET_TESTED,
        reason=(
            "No Yuma evidence package has been validated. A place is not incapable merely "
            "because it contains fewer than 25 Census tracts."
        ),
        affected_scope=["place_geometry", "tract_aggregation", "reference_layers", "thermal_source"],
        next_check=(
            "Materialize the native place geometry and test every available tract without "
            "padding or imposing a 25-tract minimum."
        ),
        capabilities={
            "place_geometry": _untested(
                reason="Native small-place geometry has not been materialized.",
                scope="place_geometry",
                next_check="Resolve the Census place and retain every intersecting native tract.",
            ),
            "selected_time_thermal": _untested(
                reason="Provider coverage has not been tested against the native small-place AOI.",
                scope="selected_time_thermal",
                next_check="Run a no-purchase provider-coverage check before authorizing acquisition.",
            ),
        },
    ),
    ValidationJurisdiction(
        jurisdiction_id="anchorage_ak",
        display_name="Anchorage",
        region_code="AK",
        validation_class="ALASKA",
        state=EvidenceState.NOT_YET_TESTED,
        reason="Alaska projection, source coverage, and timezone assumptions are not validated.",
        affected_scope=["projection", "multipart_geometry", "timezone", "thermal_source"],
        next_check="Validate Alaska geometry and source coverage independently of CONUS assumptions.",
        capabilities={
            "place_geometry": _untested(
                reason="Alaska projection and multipart geometry handling are unverified.",
                scope="place_geometry",
                next_check="Materialize and visually inspect the resolved geometry in an Alaska-appropriate CRS.",
            ),
            "selected_time_thermal": _untested(
                reason="Thermal provider coverage for the resolved Alaska AOI is unknown.",
                scope="selected_time_thermal",
                next_check="Verify provider coverage and UTC conversion without purchasing an activity.",
            ),
        },
    ),
    ValidationJurisdiction(
        jurisdiction_id="honolulu_hi",
        display_name="Honolulu",
        region_code="HI",
        validation_class="HAWAII",
        state=EvidenceState.NOT_YET_TESTED,
        reason="Island geometry, source coverage, and Hawaii timezone assumptions are not validated.",
        affected_scope=["island_geometry", "antimeridian", "timezone", "thermal_source"],
        next_check="Validate island geometry and provider coverage independently of CONUS assumptions.",
        capabilities={
            "place_geometry": _untested(
                reason="Island and antimeridian-safe geometry handling are unverified.",
                scope="place_geometry",
                next_check="Materialize and inspect all geometry parts before creating an AOI manifest.",
            ),
            "selected_time_thermal": _untested(
                reason="Thermal provider coverage for the resolved Hawaii AOI is unknown.",
                scope="selected_time_thermal",
                next_check="Verify provider coverage and local-to-UTC conversion without purchasing an activity.",
            ),
        },
    ),
    ValidationJurisdiction(
        jurisdiction_id="outside_catalog",
        display_name="Outside the server catalog",
        validation_class="UNSUPPORTED",
        state=EvidenceState.UNAVAILABLE,
        reason="No server-owned jurisdiction identity or evidence manifest exists for this request.",
        affected_scope=["all_capabilities"],
        next_check="Add and validate a versioned jurisdiction manifest before exposing the place as selectable.",
        capabilities={
            "catalog_entry": CapabilityEvidence(
                state=EvidenceState.UNAVAILABLE,
                reason="The request is outside the explicit server allowlist.",
                affected_scope="all_capabilities",
                next_check="Create a reviewed jurisdiction entry; do not substitute a public city boundary.",
            )
        },
    ),
)
