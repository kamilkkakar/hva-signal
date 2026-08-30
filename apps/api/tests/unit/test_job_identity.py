"""Job identity stays signal-specific."""

from datetime import datetime

import pytest

from app.services.job_identity import (
    historical_request_fingerprint,
    snapshot_fingerprint_ignores_reference_protocol,
    two_signal_job_fingerprint,
)
from app.services.snapshot_identity import snapshot_request_fingerprint


def _hist(**overrides: object) -> str:
    payload = {
        "area_id": "phoenix-demo",
        "analysis_time": datetime(2022, 6, 30, 3, 0, 0),
        "timezone": "America/Phoenix",
        "analysis_mode": "retrospective",
        "granularity_m": 100,
        "data_mode": "replay",
        "geometry_sha256": "aa" * 32,
        "zone_geometry_version": "GEO_V1",
        "reference_protocol_id": "PHX_ZTSI_REF_V1",
        "area_config_version": "PHX_AREA_CONFIG_V1",
    }
    payload.update(overrides)
    return historical_request_fingerprint(**payload)


def _snap(**overrides: object) -> str:
    payload = {
        "area_id": "phoenix-demo",
        "geometry_sha256": "aa" * 32,
        "zone_geometry_version": "GEO_V1",
        "target_timestamp": datetime(2024, 7, 15, 15, 0, 0),
        "timezone": "America/Phoenix",
        "aggregation_spec_version": "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    }
    payload.update(overrides)
    return snapshot_request_fingerprint(**payload)


def test_reference_protocol_changes_a_not_b() -> None:
    a1 = _hist()
    a2 = _hist(reference_protocol_id="PHX_ZTSI_REF_V2")
    assert a1 != a2
    assert snapshot_fingerprint_ignores_reference_protocol() is True
    assert _snap() == _snap()


def test_geometry_or_hour_changes_b() -> None:
    assert _snap(geometry_sha256="bb" * 32) != _snap()
    assert _snap(target_timestamp=datetime(2024, 7, 15, 3, 0, 0)) != _snap()


def test_two_signal_job_key_composes_requested_signals() -> None:
    key = two_signal_job_fingerprint(
        area_id="phoenix-demo",
        geometry_sha256="aa" * 32,
        request_historical=True,
        request_selected_time=True,
        historical_fingerprint=_hist(),
        selected_time_fingerprint=_snap(),
    )
    only_b = two_signal_job_fingerprint(
        area_id="phoenix-demo",
        geometry_sha256="aa" * 32,
        request_historical=False,
        request_selected_time=True,
        selected_time_fingerprint=_snap(),
    )
    assert key != only_b


def test_historical_fingerprint_rejects_aware_time() -> None:
    from datetime import timezone

    with pytest.raises(ValueError, match="naive"):
        _hist(analysis_time=datetime(2022, 6, 30, 3, 0, tzinfo=timezone.utc))
