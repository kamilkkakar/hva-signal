"""Request fingerprint stability (endpoint, AOI, local valid time, temporal mode,
granularity, filter params, adapter version)."""

from __future__ import annotations

from copy import deepcopy

from app.integrations.fortyguard.fingerprints import fingerprint_request
from app.integrations.fortyguard.transport_models import ADAPTER_VERSION

from .helpers import PHOENIX_HOURLY_AOI

_BASE = {
    "endpoint": "/v1/heatmap",
    "aoi": PHOENIX_HOURLY_AOI,
    "local_valid_time": "2024-07-15T15:00",
    "temporal_mode": "single_hour",
    "granularity": 100,
    "filter_params": {"analytic_type": "tcm", "filter_type": 1},
    "adapter_version": ADAPTER_VERSION,
}


def _fp(**overrides) -> str:
    kwargs = dict(_BASE)
    kwargs.update(overrides)
    return fingerprint_request(**kwargs)


def test_fingerprint_is_stable_for_identical_inputs() -> None:
    assert _fp() == _fp()
    assert len(_fp()) == 64


def test_fingerprint_changes_with_endpoint() -> None:
    assert _fp(endpoint="/v1/heatmap") != _fp(endpoint="/v1/env_params")


def test_fingerprint_changes_with_aoi() -> None:
    other = deepcopy(PHOENIX_HOURLY_AOI)
    other["coordinates"][0][0][0] += 0.01
    assert _fp() != _fp(aoi=other)


def test_fingerprint_changes_with_local_valid_time() -> None:
    assert _fp(local_valid_time="2024-07-15T15:00") != _fp(
        local_valid_time="2024-07-15T16:00"
    )


def test_fingerprint_changes_with_temporal_mode() -> None:
    assert _fp(temporal_mode="single_hour") != _fp(temporal_mode="full_day")


def test_fingerprint_changes_with_granularity() -> None:
    assert _fp(granularity=100) != _fp(granularity=60)


def test_fingerprint_changes_with_filter_params() -> None:
    assert _fp(filter_params={"analytic_type": "tcm", "filter_type": 1}) != _fp(
        filter_params={"analytic_type": "exceedance", "filter_type": 1, "threshold": 30}
    )


def test_fingerprint_changes_with_adapter_version() -> None:
    assert _fp(adapter_version="fortyguard-adapter-0.1.0") != _fp(
        adapter_version="fortyguard-adapter-0.2.0"
    )
