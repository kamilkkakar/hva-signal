"""Signal B request identity omits historical reference protocol IDs."""

from datetime import datetime

import pytest

from app.services.snapshot_identity import (
    SNAPSHOT_IDENTITY_VERSION,
    snapshot_request_document,
    snapshot_request_fingerprint,
)


def _fp(**overrides: object) -> str:
    payload = {
        "area_id": "phoenix-demo",
        "geometry_sha256": "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
        "zone_geometry_version": "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        "target_timestamp": datetime(2024, 7, 15, 15, 0, 0),
        "timezone": "America/Phoenix",
        "aggregation_spec_version": "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    }
    payload.update(overrides)
    return snapshot_request_fingerprint(**payload)


def test_identical_snapshot_requests_share_a_fingerprint() -> None:
    assert _fp() == _fp()
    assert len(_fp()) == 64


def test_reference_protocol_is_not_in_the_identity() -> None:
    doc = snapshot_request_document(
        area_id="phoenix-demo",
        geometry_sha256="aa" * 32,
        zone_geometry_version="GEO_V1",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        analytic="tcm",
        granularity_m=100,
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    )
    blob = str(doc)
    assert SNAPSHOT_IDENTITY_VERSION in blob
    assert "reference" not in blob.lower()
    assert "PHX_ZTSI_REF" not in blob


def test_geometry_or_time_or_timezone_changes_the_key() -> None:
    baseline = _fp()
    assert _fp(geometry_sha256="bb" * 32) != baseline
    assert _fp(target_timestamp=datetime(2024, 7, 15, 3, 0, 0)) != baseline
    assert _fp(timezone="America/Denver") != baseline
    assert _fp(analytic="exceedance") != baseline


def test_reference_readiness_is_not_part_of_the_key() -> None:
    # Identity helper has no reference argument; this documents the contract.
    assert "reference" not in snapshot_request_fingerprint.__code__.co_varnames


def test_nonzero_minutes_cannot_be_fingerprinted() -> None:
    with pytest.raises(ValueError, match="minutes"):
        _fp(target_timestamp=datetime(2024, 7, 15, 15, 30, 0))
