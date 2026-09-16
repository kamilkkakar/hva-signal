"""Exercise real database sessions, process death, and lost vendor responses."""

import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event
from uuid import uuid4

import httpx
import pytest

from app.core.postgres_acquisition import (
    AcquisitionIdentityMismatch, AcquisitionInProgress, AcquisitionNeedsRecovery,
    AcquisitionStorageUnavailable, PostgresAcquisitionStore,
)
from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    load_phoenix_hourly_thermal_pilot_manifest,
)
from app.integrations.fortyguard.exceptions import AcquisitionAllowanceExceeded, TaskFailedError
from app.services.hourly_pilot_acquisition import (
    prepare_hourly_pilot_canary,
    run_hourly_pilot_canary,
)


PAYLOAD = {"date_time": {"start_date": "2024-07-08", "start_time": "03:00"}}
RESULT = {"map_data": {"type": "FeatureCollection", "features": []}}


@pytest.fixture
def store():
    dsn = os.environ.get("HVA_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("HVA_TEST_POSTGRES_DSN is required; CI provisions PostgreSQL")
    store = PostgresAcquisitionStore(dsn, scope=f"test-{uuid4()}", daily_limit=1)
    store.migrate()
    yield store
    with store._connect() as conn:
        conn.execute("DELETE FROM hva_acquisitions WHERE scope = %s", (store.scope,))


def run(store, payload=None, submit=None, poll=None):
    return store.run(
        "/v1/heatmap", payload or PAYLOAD,
        submit=submit or (lambda: "activity-1"), poll=poll or (lambda _: RESULT),
    )


def forbidden(*_):
    pytest.fail("An existing acquisition must not purchase again")


def _resolved_canary():
    resolved = load_phoenix_hourly_thermal_pilot_manifest()
    return resolved, prepare_hourly_pilot_canary(resolved, CANARY_SLOT_ID)


def test_hourly_canary_replays_by_manifest_fingerprint_after_restart(store):
    resolved, prepared = _resolved_canary()
    first, source = run_hourly_pilot_canary(
        resolved,
        slot_id=CANARY_SLOT_ID,
        store=store,
        submit=lambda: "pilot-activity",
        poll=lambda _: RESULT,
    )
    assert source == "live"
    with store._connect() as conn:
        saved = conn.execute(
            "SELECT fingerprint, request_payload FROM hva_acquisitions WHERE scope = %s",
            (store.scope,),
        ).fetchone()
    assert saved["fingerprint"] == prepared.request_fingerprint
    assert saved["request_payload"]["payload"] == prepared.payload

    fresh = PostgresAcquisitionStore(store._dsn, scope=store.scope, daily_limit=0)
    assert run_hourly_pilot_canary(
        resolved,
        slot_id=CANARY_SLOT_ID,
        store=fresh,
        submit=forbidden,
        poll=forbidden,
    ) == (first, "durable_replay")


def test_hourly_canary_concurrent_session_cannot_duplicate(store):
    resolved, _prepared = _resolved_canary()
    entered, release = Event(), Event()

    def submit():
        entered.set()
        assert release.wait(10)
        return "pilot-activity"

    with ThreadPoolExecutor(1) as pool:
        owner = pool.submit(
            run_hourly_pilot_canary,
            resolved,
            slot_id=CANARY_SLOT_ID,
            store=store,
            submit=submit,
            poll=lambda _: RESULT,
        )
        try:
            assert entered.wait(10)
            other = PostgresAcquisitionStore(
                store._dsn, scope=store.scope, daily_limit=1,
            )
            with pytest.raises(AcquisitionInProgress):
                run_hourly_pilot_canary(
                    resolved,
                    slot_id=CANARY_SLOT_ID,
                    store=other,
                    submit=forbidden,
                    poll=forbidden,
                )
        finally:
            release.set()
        assert owner.result(timeout=10)[1] == "live"


def test_hourly_canary_ambiguous_submission_is_held_across_restart(store):
    resolved, _prepared = _resolved_canary()

    def lost_response():
        raise httpx.ReadTimeout("The vendor may have accepted the pilot POST")

    with pytest.raises(httpx.ReadTimeout):
        run_hourly_pilot_canary(
            resolved,
            slot_id=CANARY_SLOT_ID,
            store=store,
            submit=lost_response,
            poll=forbidden,
        )
    fresh = PostgresAcquisitionStore(store._dsn, scope=store.scope, daily_limit=100)
    with pytest.raises(AcquisitionNeedsRecovery):
        run_hourly_pilot_canary(
            resolved,
            slot_id=CANARY_SLOT_ID,
            store=fresh,
            submit=forbidden,
            poll=forbidden,
        )


def test_manifest_fingerprint_cannot_be_reused_for_altered_pilot_payload(store):
    resolved, prepared = _resolved_canary()
    run_hourly_pilot_canary(
        resolved,
        slot_id=CANARY_SLOT_ID,
        store=store,
        submit=lambda: "pilot-activity",
        poll=lambda _: RESULT,
    )
    altered = {**prepared.payload, "granularity": 80}
    with pytest.raises(AcquisitionIdentityMismatch):
        store.run(
            prepared.path,
            altered,
            request_fingerprint=prepared.request_fingerprint,
            submit=forbidden,
            poll=forbidden,
        )


def test_replay_survives_new_store_with_zero_allowance(store):
    result, source = run(store)
    assert source == "live"
    fresh = PostgresAcquisitionStore(store._dsn, scope=store.scope, daily_limit=0)
    assert run(fresh, submit=forbidden, poll=forbidden) == (result, "durable_replay")


def test_identical_sessions_do_not_duplicate(store):
    entered, release = Event(), Event()

    def submit():
        entered.set()
        assert release.wait(10)
        return "activity-1"

    with ThreadPoolExecutor(1) as pool:
        owner = pool.submit(run, store, submit=submit)
        try:
            assert entered.wait(10)
            other = PostgresAcquisitionStore(store._dsn, scope=store.scope, daily_limit=1)
            with pytest.raises(AcquisitionInProgress):
                run(other, submit=forbidden)
        finally:
            release.set()
        assert owner.result(timeout=10)[1] == "live"
    assert run(store, submit=forbidden)[1] == "durable_replay"


def _contend(dsn, scope, hour, ready, start, output):
    store = PostgresAcquisitionStore(dsn, scope=scope, daily_limit=1)
    ready.put(True)
    start.wait(10)
    payload = {"date_time": {"start_date": "2024-07-08", "start_time": hour}}
    try:
        run(store, payload)
        output.put("submitted")
    except AcquisitionAllowanceExceeded:
        output.put("limited")


def test_distinct_processes_share_atomic_allowance(store):
    ctx = multiprocessing.get_context("spawn")
    ready, output, start = ctx.Queue(), ctx.Queue(), ctx.Event()
    processes = [ctx.Process(target=_contend, args=(store._dsn, store.scope, hour, ready, start, output))
                 for hour in ("03:00", "04:00")]
    try:
        for process in processes:
            process.start()
        for _ in processes:
            assert ready.get(timeout=15)
        start.set()
        assert sorted(output.get(timeout=15) for _ in processes) == ["limited", "submitted"]
    finally:
        start.set()
        for process in processes:
            process.join(10)
            if process.is_alive():
                process.terminate()
                process.join(5)
    assert all(process.exitcode == 0 for process in processes)


def _crash(dsn, scope, point):
    store = PostgresAcquisitionStore(dsn, scope=scope, daily_limit=1)

    def submit():
        if point == "submit":
            os._exit(17)
        return "saved-before-crash"

    def poll(_):
        os._exit(18)

    run(store, submit=submit, poll=poll)


@pytest.mark.parametrize("point", ["submit", "poll"])
def test_process_death_releases_lock_without_repurchase(store, point):
    process = multiprocessing.get_context("spawn").Process(target=_crash, args=(store._dsn, store.scope, point))
    process.start()
    process.join(15)
    if process.is_alive():
        process.terminate()
        process.join(5)
        pytest.fail("Crash worker did not finish")
    assert process.exitcode == (17 if point == "submit" else 18)
    if point == "submit":
        with pytest.raises(AcquisitionNeedsRecovery):
            run(store, submit=forbidden)
    else:
        polled = []
        result, source = run(store, submit=forbidden, poll=lambda activity: polled.append(activity) or RESULT)
        assert polled == ["saved-before-crash"]
        assert source == "durable_resume"
        assert result["activity_id"] == "saved-before-crash"


def test_lost_post_response_is_held_across_restart_and_day_change(store):
    def lost():
        raise httpx.ReadTimeout("The vendor may have accepted the POST")

    with pytest.raises(httpx.ReadTimeout):
        run(store, submit=lost)
    with store._connect() as conn:
        conn.execute("UPDATE hva_acquisitions SET reserved_day = reserved_day - 1 WHERE scope = %s", (store.scope,))
    fresh = PostgresAcquisitionStore(store._dsn, scope=store.scope, daily_limit=100)
    with pytest.raises(AcquisitionNeedsRecovery):
        run(fresh, submit=forbidden)


def test_poll_failure_resumes_existing_activity_without_allowance(store):
    def lost(_):
        raise httpx.ReadTimeout("Temporary status failure")

    with pytest.raises(httpx.ReadTimeout):
        run(store, poll=lost)
    store.daily_limit = 0
    assert run(store, submit=forbidden)[1] == "durable_resume"


def test_terminal_vendor_failure_cannot_repurchase(store):
    def failed(_):
        raise TaskFailedError("Failed activity")

    with pytest.raises(TaskFailedError):
        run(store, poll=failed)
    with pytest.raises(AcquisitionNeedsRecovery):
        run(store, submit=forbidden, poll=forbidden)


def test_result_write_failure_keeps_activity_for_recovery(store):
    # Invalid JSON cannot be persisted. The earlier activity-ID commit must survive.
    with pytest.raises(TypeError):
        run(store, poll=lambda _: {"unserializable": object()})
    assert run(store, submit=forbidden)[1] == "durable_resume"


def test_empty_result_is_retained_without_repeat_purchase(store):
    first = run(store, poll=lambda _: {})[0]
    assert run(store, submit=forbidden, poll=forbidden)[0] == first


def test_secrets_are_removed_before_storage(store):
    payload = {**PAYLOAD, "api_key": "must-not-persist"}
    run(store, payload, poll=lambda _: {"authorization": "must-not-persist", "nested": {"key": "must-not-persist"}})
    with store._connect() as conn:
        row = conn.execute("SELECT request_payload, result_payload FROM hva_acquisitions WHERE scope = %s", (store.scope,)).fetchone()
    assert "must-not-persist" not in str(row)


def test_operational_refresh_keeps_prior_generation(store):
    payload = {"date_time": {"start_date": datetime.now(timezone.utc).date().isoformat(), "start_time": "03:00"}}
    run(store, payload)
    with store._connect() as conn:
        conn.execute("UPDATE hva_acquisitions SET expires_at = clock_timestamp() - interval '1 second' WHERE scope = %s", (store.scope,))
    with pytest.raises(AcquisitionAllowanceExceeded):
        run(store, payload, submit=forbidden)
    store.daily_limit = 2
    assert run(store, payload, submit=lambda: "activity-2")[0]["activity_id"] == "activity-2"
    with store._connect() as conn:
        rows = conn.execute("SELECT generation, activity_id FROM hva_acquisitions WHERE scope = %s ORDER BY generation", (store.scope,)).fetchall()
    assert rows == [{"generation": 1, "activity_id": "activity-1"}, {"generation": 2, "activity_id": "activity-2"}]


def test_database_loss_after_reservation_never_submits_again(store):
    def disconnect():
        with store._connect() as killer:
            owner = killer.execute(
                """SELECT pid FROM pg_locks WHERE locktype = 'advisory'
                   AND pid <> pg_backend_pid() AND granted""",
            ).fetchone()["pid"]
            killer.execute("SELECT pg_terminate_backend(%s)", (owner,))
        return "vendor-accepted"

    with pytest.raises(AcquisitionStorageUnavailable):
        run(store, submit=disconnect)
    with pytest.raises(AcquisitionNeedsRecovery):
        run(store, submit=forbidden)


def test_schema_is_idempotent_and_reservation_commits_before_post(store):
    store.migrate()

    def submit():
        with store._connect() as conn:
            row = conn.execute("SELECT state, reservation_id FROM hva_acquisitions WHERE scope = %s", (store.scope,)).fetchone()
        assert row["state"] == "SUBMITTING"
        assert row["reservation_id"]
        return "activity-1"

    run(store, submit=submit)


def test_type1_rehydrates_lost_disk_cache_from_database(store, tmp_path):
    from app.core.config import Settings
    from app.domain.multicity.type1_live import run_type1_live
    from app.integrations.fortyguard.cache import FortyGuardCache

    calls = []

    def transport(request):
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"activity_id": "activity-1"}})
        return httpx.Response(200, json={"data": {"status": "succeeded", "result": RESULT}})

    settings = Settings(
        _env_file=None, shared_acquisition_enabled=True,
        acquisition_database_url=store._dsn, acquisition_account_scope=store.scope,
        app_env="integration", bounded_selected_time_live_enabled=True,
        fortyguard_api_key="test-only-key", bounded_selected_time_daily_limit=1,
    )
    request = {"city": "Phoenix", "target_local": "2024-07-08T03:00:00"}
    try:
        responses = []
        for name in ("first-instance", "replacement-instance"):
            settings.cache_dir = str(tmp_path / name)
            responses.append(run_type1_live(
                request, cache=FortyGuardCache(settings.cache_dir), settings=settings,
                bounded_selected_time_authorized=True, vendor_transport=httpx.MockTransport(transport),
                before_submit=forbidden, poll_interval=0,
            ))
            settings.bounded_selected_time_daily_limit = 0
        assert responses[0]["status"] == "live_acquired"
        assert responses[1]["status"] == "cache_hit"
        assert responses[1]["cache_tier"] == "durable"
        assert not responses[1]["vendor_attempted"]
        assert calls == ["POST", "GET"]
        assert list((tmp_path / "replacement-instance" / "bounded_selected_time_vendor").glob("*.json"))
    finally:
        with store._connect() as conn:
            conn.execute("DELETE FROM hva_acquisitions WHERE scope = %s", (f"{store.scope}:integration:https://api.fortyguard.com",))
