"""Exact-manifest preparation and durable-store delegation for the pilot canary."""

from unittest.mock import Mock

import pytest

from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    load_phoenix_hourly_thermal_pilot_manifest,
)
from app.services.hourly_pilot_acquisition import (
    HOURLY_PILOT_VENDOR_PATH,
    HourlyPilotAcquisitionError,
    prepare_hourly_pilot_canary,
    run_hourly_pilot_canary,
)


def test_canary_preparation_uses_exact_frozen_aoi_and_fingerprint() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    prepared = prepare_hourly_pilot_canary(resolved, CANARY_SLOT_ID)
    slot = next(item for item in resolved.manifest.slots if item.slot_id == CANARY_SLOT_ID)

    assert prepared.manifest_sha256 == resolved.sha256
    assert prepared.request_fingerprint == slot.request_fingerprint
    assert prepared.path == HOURLY_PILOT_VENDOR_PATH
    assert prepared.payload == {
        "polygon_aoi": resolved.provider_aoi,
        "date_time": {
            "start_date": "2024-07-15",
            "filter_type": 1,
            "start_time": "03:00",
        },
        "granularity": 100,
        "analytic_type": "tcm",
    }


def test_non_canary_slot_cannot_reach_durable_execution() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    with pytest.raises(HourlyPilotAcquisitionError, match="canary"):
        prepare_hourly_pilot_canary(resolved, "2024-07-15T04:00")


def test_durable_run_is_keyed_by_manifest_request_fingerprint() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    prepared = prepare_hourly_pilot_canary(resolved, CANARY_SLOT_ID)
    store = Mock()
    store.run.return_value = ({"activity_id": "saved", "result": {}}, "durable_resume")
    submit, poll = Mock(), Mock()

    assert run_hourly_pilot_canary(
        resolved,
        slot_id=CANARY_SLOT_ID,
        store=store,
        submit=submit,
        poll=poll,
    ) == ({"activity_id": "saved", "result": {}}, "durable_resume")
    store.run.assert_called_once_with(
        prepared.path,
        prepared.payload,
        request_fingerprint=prepared.request_fingerprint,
        submit=submit,
        poll=poll,
    )
