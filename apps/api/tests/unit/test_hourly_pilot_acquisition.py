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
    execute_hourly_pilot_canary,
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


def test_executor_submits_and_polls_only_the_prepared_canary() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    prepared = prepare_hourly_pilot_canary(resolved, CANARY_SLOT_ID)
    store, client = Mock(), Mock()
    client.submit.return_value = "pilot-activity"
    client.get_status.return_value = {
        "status": "succeeded",
        "result": {"map_data": {"type": "FeatureCollection", "features": []}},
    }

    def durable_run(path, payload, *, request_fingerprint, submit, poll):
        assert path == prepared.path
        assert payload == prepared.payload
        assert request_fingerprint == prepared.request_fingerprint
        activity_id = submit()
        return {"activity_id": activity_id, "result": poll(activity_id)}, "live"

    store.run.side_effect = durable_run
    bundled, source = execute_hourly_pilot_canary(
        resolved,
        slot_id=CANARY_SLOT_ID,
        store=store,
        client=client,
        poll_interval=0,
    )

    assert source == "live"
    assert bundled["activity_id"] == "pilot-activity"
    client.submit.assert_called_once_with(prepared.path, prepared.payload)
    client.get_status.assert_called_once_with("pilot-activity")


def test_durable_replay_makes_no_vendor_call() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    store, client = Mock(), Mock()
    store.run.return_value = (
        {"activity_id": "saved", "result": {"map_data": {}}},
        "durable_replay",
    )

    assert execute_hourly_pilot_canary(
        resolved,
        slot_id=CANARY_SLOT_ID,
        store=store,
        client=client,
    )[1] == "durable_replay"
    client.submit.assert_not_called()
    client.get_status.assert_not_called()


def test_executor_rejects_batch_before_store_or_vendor() -> None:
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    store, client = Mock(), Mock()
    with pytest.raises(HourlyPilotAcquisitionError, match="canary"):
        execute_hourly_pilot_canary(
            resolved,
            slot_id="2024-07-15T04:00",
            store=store,
            client=client,
        )
    store.run.assert_not_called()
    client.submit.assert_not_called()
