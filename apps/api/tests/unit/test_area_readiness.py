"""Geography readiness is independent of historical reference readiness."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.area_readiness import (
    AreaCapabilityState,
    GeographyIdentity,
    GeographyReadiness,
    ReferenceReadiness,
    current_registry_requires_reference_for_geometry,
    historical_signal_capable,
    snapshot_capable,
)
from app.core.area_registry import resolve_ready_area_package
from app.domain.phoenix_v1 import AREA_ID


def _identity() -> GeographyIdentity:
    return GeographyIdentity(
        area_id="candidate-area",
        zone_geoids=tuple(f"geoid-{i:02d}" for i in range(25)),
        expected_zone_count=25,
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        area_selection_policy_version="PHX_DEMO_AOI_POLICY_V1",
        geometry_sha256="3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    )


def test_snapshot_capable_without_historical_reference() -> None:
    identity = _identity()
    assert (
        snapshot_capable(
            identity,
            geography=GeographyReadiness.GEOGRAPHY_READY,
            reference=ReferenceReadiness.NOT_PREPARED,
        )
        is True
    )
    assert (
        historical_signal_capable(
            identity,
            geography=GeographyReadiness.GEOGRAPHY_READY,
            reference=ReferenceReadiness.NOT_PREPARED,
        )
        is False
    )


def test_capability_state_splits_snapshot_and_historical() -> None:
    state = AreaCapabilityState(
        geography=GeographyReadiness.GEOGRAPHY_READY,
        reference=ReferenceReadiness.NOT_PREPARED,
    )
    assert state.snapshot_capable is True
    assert state.historical_signal_capable is False


def test_unresolved_geography_is_not_snapshot_capable() -> None:
    identity = _identity()
    assert (
        snapshot_capable(identity, geography=GeographyReadiness.UNRESOLVED)
        is False
    )


def test_geography_identity_rejects_reference_fields() -> None:
    with pytest.raises(ValidationError):
        GeographyIdentity.model_validate(
            {
                **_identity().model_dump(),
                "reference_path": "data/phoenix/reference/observations.jsonl",
            }
        )


def test_production_registry_serves_geometry_without_requiring_reference_resolver() -> None:
    assert current_registry_requires_reference_for_geometry() is False
    package = resolve_ready_area_package(AREA_ID)
    assert package.reference_path is not None
    assert package.manifest.reference_sha256


def test_no_public_snapshot_or_preparation_route() -> None:
    from app.api.router import api_router

    paths = [getattr(route, "path", "") for route in api_router.routes]
    joined = " ".join(paths)
    assert "snapshot" not in joined
    assert "prepare" not in joined
    assert "signal" not in joined
