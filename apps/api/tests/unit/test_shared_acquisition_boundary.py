"""The durable path must fail closed and preserve public error contracts."""

from datetime import datetime
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException

from app.api.routes import bounded_selected_time_live as route
from app.core.config import Settings
from app.core.postgres_acquisition import (
    AcquisitionIdentityMismatch, AcquisitionInProgress, AcquisitionNeedsRecovery,
    AcquisitionStorageUnavailable, PostgresAcquisitionStore, store_from_settings,
)
from app.domain.multicity.type1_live import construct_bounded_selected_time_http_client
from app.integrations.fortyguard.client import FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import FortyGuardHttpError


@pytest.mark.parametrize("error,code,status", [
    (AcquisitionInProgress, "bounded_selected_time_in_progress", 409),
    (AcquisitionNeedsRecovery, "bounded_selected_time_recovery_required", 409),
    (AcquisitionStorageUnavailable, "bounded_selected_time_storage_unavailable", 503),
])
def test_public_error_does_not_leak_storage_details(monkeypatch, error, code, status, tmp_path):
    settings = Settings(_env_file=None, bounded_selected_time_live_enabled=True, cache_dir=str(tmp_path))
    monkeypatch.setattr(route, "get_settings", lambda: settings)

    def fail(*_, **__):
        raise error("private-database-host-and-credential")

    monkeypatch.setattr(route, "run_type1_live", fail)
    body = route.SelectedTimeLiveBody(city_id="phoenix", local_datetime=datetime(2024, 7, 8, 3))
    with pytest.raises(HTTPException) as exc:
        route.post_selected_time_live(body, None)
    assert exc.value.status_code == status
    assert exc.value.detail["code"] == code
    assert "private-database" not in str(exc.value.detail)


def test_enabled_but_unconfigured_storage_cannot_fall_back():
    settings = Settings(_env_file=None, shared_acquisition_enabled=True, bounded_selected_time_live_enabled=True,
                        fortyguard_api_key="test-only")
    with pytest.raises(AcquisitionStorageUnavailable):
        construct_bounded_selected_time_http_client(settings=settings)


def test_disabled_shared_storage_keeps_existing_path():
    assert store_from_settings(Settings(_env_file=None)) is None


def test_database_outage_never_invokes_submit():
    store = PostgresAcquisitionStore("postgresql://localhost:1/unavailable", scope="test", daily_limit=1)
    submit = Mock()
    with pytest.raises(AcquisitionStorageUnavailable):
        store.run("/v1/heatmap", {}, submit=submit, poll=Mock())
    submit.assert_not_called()


def test_invalid_caller_supplied_fingerprint_never_opens_database_or_submits():
    store = PostgresAcquisitionStore(
        "postgresql://localhost:1/unavailable", scope="test", daily_limit=1,
    )
    submit = Mock()
    with pytest.raises(AcquisitionIdentityMismatch):
        store.run(
            "/v1/heatmap", {}, request_fingerprint="not-a-sha", submit=submit,
            poll=Mock(),
        )
    submit.assert_not_called()


@pytest.mark.parametrize("activity_id", [None, "", " ", False, 0])
def test_invalid_activity_id_is_not_accepted(activity_id):
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"data": {"activity_id": activity_id}}))
    with FortyGuardHttpClient("test-only", transport=transport) as client:
        with pytest.raises(FortyGuardHttpError, match="no usable activity"):
            client.submit("/v1/heatmap", {})


def test_durable_client_replays_without_post_or_local_reservation():
    store = Mock()
    store.run.return_value = ({"activity_id": "saved", "result": {}}, "durable_replay")
    before_submit = Mock()
    transport = httpx.MockTransport(lambda _: pytest.fail("Replay must not call the vendor"))
    with FortyGuardHttpClient("test-only", acquisition_store=store, before_submit=before_submit,
                              transport=transport) as client:
        assert client.submit_and_wait("/v1/heatmap", {})["activity_id"] == "saved"
        assert client.last_acquisition_source == "durable_replay"
        assert client.submission_count == 0
        with pytest.raises(RuntimeError, match="submit_and_wait"):
            client.submit("/v1/heatmap", {})
    before_submit.assert_not_called()
