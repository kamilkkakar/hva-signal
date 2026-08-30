"""Hosted hackathon demo allowance. Server authorization, not user identity.

Disabled by default. No vendor price. No login. No public route.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.signals import ThermalSignalKind

DEMO_ALLOWANCE_POLICY_VERSION = "hva-signal-demo-allowance-v1"


class AcquisitionPreference(str, Enum):
    """User intent only. Never spend authority."""

    REUSE_ONLY = "reuse_only"
    ALLOW_HOSTED_LIVE_DEMO = "allow_hosted_live_demo"


class SpendAuthorizationSource(str, Enum):
    DEMO_ALLOWANCE = "demo_allowance"
    MANUAL_OPERATOR_FUTURE = "manual_operator_future"


class DemoAllowanceDecisionCode(str, Enum):
    NOT_REQUIRED_REUSE = "NOT_REQUIRED_REUSE"
    JOIN_IN_FLIGHT = "JOIN_IN_FLIGHT"
    JOIN_EXISTING_RESERVATION = "JOIN_EXISTING_RESERVATION"
    LIVE_DEMO_NOT_REQUESTED = "LIVE_DEMO_NOT_REQUESTED"
    ELIGIBLE = "ELIGIBLE"
    ALLOWANCE_DISABLED = "ALLOWANCE_DISABLED"
    ALLOWANCE_EXHAUSTED = "ALLOWANCE_EXHAUSTED"
    ALLOWANCE_EXPIRED = "ALLOWANCE_EXPIRED"
    REQUEST_UNIT_CAP_EXCEEDED = "REQUEST_UNIT_CAP_EXCEEDED"
    UNSUPPORTED_REQUEST = "UNSUPPORTED_REQUEST"
    NOT_SNAPSHOT_CAPABLE = "NOT_SNAPSHOT_CAPABLE"
    LIVE_ACQUISITION_UNAVAILABLE = "LIVE_ACQUISITION_UNAVAILABLE"
    POLICY_INVALID = "POLICY_INVALID"


class ReservationState(str, Enum):
    RESERVED = "RESERVED"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class DemoAllowancePolicy(BaseModel):
    """Pre-authorized hosted-demo cap. Not a subscription or login permission."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["hva-signal-demo-allowance-v1"] = DEMO_ALLOWANCE_POLICY_VERSION
    enabled: bool = False
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_total_acquisition_units: int = Field(default=0, ge=0)
    max_units_per_request: int = Field(default=1, ge=0)
    allowed_signal_kinds: frozenset[ThermalSignalKind] = Field(
        default_factory=lambda: frozenset({ThermalSignalKind.SELECTED_TIME_SNAPSHOT})
    )
    allowed_analytics: frozenset[str] = Field(default_factory=lambda: frozenset({"tcm"}))
    allowed_granularities_m: frozenset[int] = Field(default_factory=lambda: frozenset({100}))
    allowed_temporal_modes: frozenset[str] = Field(
        default_factory=lambda: frozenset({"single_hour"})
    )
    allowed_area_ids: frozenset[str] = Field(default_factory=frozenset)

    @model_validator(mode="after")
    def _window_order(self) -> DemoAllowancePolicy:
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("demo allowance valid_from must precede valid_until")
        return self

    def is_structurally_valid(self) -> bool:
        try:
            self.model_validate(self.model_dump())
        except ValueError:
            return False
        return self.max_units_per_request >= 0 and self.max_total_acquisition_units >= 0


class DemoAllowanceState(BaseModel):
    """Internal ledger snapshot. Never serialize remaining units to clients."""

    model_config = ConfigDict(extra="forbid")

    authorized_total_units: int
    reserved_units: int
    consumed_units: int
    remaining_units: int
    restart_resets_remaining: Literal[True] = True
    durability: Literal["J0_PROCESS_LOCAL_NOT_DURABLE"] = "J0_PROCESS_LOCAL_NOT_DURABLE"


class DemoReservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: str
    state: ReservationState
    signal_kind: ThermalSignalKind
    request_fingerprint: str
    geometry_sha256: str
    area_id: str
    planned_units: int = Field(gt=0)
    created_at: datetime
    expires_at: datetime | None = None


class DemoRequestIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_kind: ThermalSignalKind
    request_fingerprint: str
    geometry_sha256: str
    area_id: str
    analytic: str = "tcm"
    granularity_m: int = 100
    temporal_mode: str = "single_hour"


class DemoAllowanceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: DemoAllowanceDecisionCode
    reservation: DemoReservation | None = None
    approval_required: bool = False
    spend_authorized: bool = False


def disabled_demo_policy() -> DemoAllowancePolicy:
    """Fail-closed default. Hosted live spend is off until a human freezes values."""
    return DemoAllowancePolicy()
