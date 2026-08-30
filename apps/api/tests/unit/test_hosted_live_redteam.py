"""LIVE-N adversarial tests for hosted-live public safety.

No FortyGuard. No real vendor. Does not claim mathematical exactly-once.

These tests first documented holes (nested scenario extras, missing privilege
names, header/query enable, client activity_id, forced UNKNOWN resubmit).
Fixes live in domain/client_privilege.py, requests.py, denylists, routes,
and hosted_live_redteam.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.anonymous_guards import PUBLIC_SERIALIZER_DENYLIST
from app.domain.client_privilege import (
    CLIENT_NEVER_SET_FIELDS,
    HOSTED_LIVE_ENABLE_FIELDS,
)
from app.domain.demo_allowance import (
    DemoAllowanceDecisionCode,
    DemoAllowancePolicy,
    DemoRequestIdentity,
    ReservationState,
)
from app.domain.enums import DataMode
from app.domain.requests import AnalysisRequest, ScenarioRequest
from app.domain.signals import ThermalSignalKind
from app.main import app
from app.schemas.two_signal_public import TwoSignalPublicationRequest
from app.services.demo_allowance_ledger import (
    DemoAllowanceError,
    InMemoryDemoAllowanceLedger,
)
from app.services.hosted_live_redteam import (
    ClientPrivilegeError,
    ForgedActivityError,
    RecoveryAction,
    ReservationStealError,
    ServerActivityRegistry,
    WorkerRecoveryState,
    cache_bust_hits,
    client_tried_to_enable_hosted_live,
    consume_server_reservation,
    decide_unknown_vendor_recovery,
    hosted_live_defaults_remain_off,
    paid_retry_allowed,
    reject_cache_bust,
    reject_client_privilege_surfaces,
    scan_client_surfaces,
    steal_reservation_result,
)
from app.services.secret_boundary import public_payload_leaks_secrets
from app.services.spend_gate import can_execute_paid_acquisition, grant_from_demo_reservation
from app.services.spend_threat_guards import client_flags_cannot_authorize


FP = "aa" * 32
GEO = "bb" * 32
ATTACKER_FP = "cc" * 32

PRIVILEGE_SAMPLE = (
    "allowance",
    "budget",
    "key",
    "force_live",
    "operator_approval",
    "reservation_state",
    "reservation_id",
    "activity_id",
    "hosted_live_enabled",
    "demo_allowance_enabled",
    "demo_allowance_max_total_units",
)


def _analysis(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "area_id": "phoenix-demo",
        "analysis_time": "2022-06-30T03:00:00",
        "analysis_mode": "retrospective",
        "horizon_hours": 0,
        "lookback_hours": 0,
        "granularity_m": 100,
        "data_mode": "replay",
    }
    payload.update(overrides)
    return payload


def _publication(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "contract_version": "hva-signal-two-signal-job-v1",
        "area_id": "phoenix-demo",
        "signals": {
            "historical": {"analysis_time": "2022-06-30T03:00:00"},
        },
        "timezone": "America/Phoenix",
        "granularity_m": 100,
        "data_mode": "replay",
    }
    payload.update(overrides)
    return payload


def _identity(**overrides: object) -> DemoRequestIdentity:
    payload: dict[str, object] = {
        "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        "request_fingerprint": FP,
        "geometry_sha256": GEO,
        "area_id": "phoenix-demo",
    }
    payload.update(overrides)
    return DemoRequestIdentity.model_validate(payload)


def _ledger(total: int = 2) -> InMemoryDemoAllowanceLedger:
    return InMemoryDemoAllowanceLedger(
        DemoAllowancePolicy(
            enabled=True,
            max_total_acquisition_units=total,
            max_units_per_request=1,
            allowed_area_ids=frozenset({"phoenix-demo"}),
        )
    )


# ---------------------------------------------------------------------------
# A. Client privilege injection (body / nested / query / header)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", PRIVILEGE_SAMPLE)
def test_analysis_request_rejects_privilege_fields(field: str) -> None:
    with pytest.raises(ValidationError, match="unpublished"):
        AnalysisRequest.model_validate({**_analysis(), field: True})


@pytest.mark.parametrize("field", PRIVILEGE_SAMPLE)
def test_scenario_nested_privilege_is_rejected(field: str) -> None:
    """Was extra=allow hole: nested force_live/key survived into job.request."""
    with pytest.raises(ValidationError, match="unpublished"):
        AnalysisRequest.model_validate(
            _analysis(scenario={field: True, "scenario_id": "atk"})
        )
    with pytest.raises(ValidationError, match="unpublished"):
        ScenarioRequest.model_validate({field: True})


@pytest.mark.parametrize("field", PRIVILEGE_SAMPLE)
def test_p2_publication_rejects_privilege_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicationRequest.model_validate(_publication(**{field: True}))


@pytest.mark.parametrize("field", PRIVILEGE_SAMPLE)
def test_http_analysis_job_rejects_privilege_body(field: str) -> None:
    client = TestClient(app)
    response = client.post("/api/v1/analysis/jobs", json={**_analysis(), field: True})
    assert response.status_code == 422


def test_http_analysis_job_rejects_force_live_query() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/analysis/jobs?force_live=1",
        json=_analysis(),
    )
    assert response.status_code == 422
    assert "force_live" in str(response.json()).lower()


def test_http_analysis_job_rejects_hosted_live_header() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/analysis/jobs",
        json=_analysis(),
        headers={"X-Force-Live": "true", "X-Hosted-Live-Enabled": "1"},
    )
    assert response.status_code == 422


def test_scan_detects_header_query_and_nested_body() -> None:
    hits = scan_client_surfaces(
        body={"scenario": {"reservation_state": "CONSUMED"}},
        query={"budget": "999", "cache_bust": "1"},
        headers={"X-Force-Live": "1", "X-Reservation-Id": "res_stolen"},
    )
    assert "force_live" in hits
    assert "budget" in hits
    assert "reservation_state" in hits
    assert "reservation_id" in hits
    assert "cache_bust" in hits
    with pytest.raises(ClientPrivilegeError) as exc:
        reject_client_privilege_surfaces(
            body={"key": "fg_live_xxx"},
            query=None,
            headers=None,
        )
    assert "key" in exc.value.hits


def test_client_flags_guard_covers_redteam_names() -> None:
    payload = {name: True for name in PRIVILEGE_SAMPLE}
    hits = client_flags_cannot_authorize(payload)
    for name in PRIVILEGE_SAMPLE:
        assert name in hits


def test_serializer_and_secret_boundary_cover_key_and_budget() -> None:
    assert "key" in PUBLIC_SERIALIZER_DENYLIST
    assert "budget" in PUBLIC_SERIALIZER_DENYLIST
    assert "reservation_state" in PUBLIC_SERIALIZER_DENYLIST
    assert "activity_id" in PUBLIC_SERIALIZER_DENYLIST
    planted = {"ok": True, "key": "x", "budget": 9, "activity_id": "act"}
    assert "key" in public_payload_leaks_secrets(planted) or "key" in planted
    leaks = public_payload_leaks_secrets(planted)
    assert "key" in leaks
    assert "budget" in leaks


# ---------------------------------------------------------------------------
# B. Client tries to enable hosted live
# ---------------------------------------------------------------------------


def test_hosted_live_defaults_off() -> None:
    assert hosted_live_defaults_remain_off() is True
    assert hosted_live_defaults_remain_off(
        Settings.model_construct(
            demo_allowance_enabled=False,
            demo_allowance_max_total_units=0,
        )
    )
    assert (
        hosted_live_defaults_remain_off(
            Settings.model_construct(
                demo_allowance_enabled=True,
                demo_allowance_max_total_units=4,
            )
        )
        is False
    )


@pytest.mark.parametrize("field", sorted(HOSTED_LIVE_ENABLE_FIELDS))
def test_client_cannot_enable_hosted_live(field: str) -> None:
    assert client_tried_to_enable_hosted_live(body={field: True}) is True
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({**_analysis(), field: True})
    with pytest.raises(ValidationError):
        TwoSignalPublicationRequest.model_validate(_publication(**{field: True}))


def test_p2_data_mode_live_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TwoSignalPublicationRequest.model_validate(_publication(data_mode="live"))


def test_legacy_data_mode_live_does_not_enable_allowance() -> None:
    """data_mode=live remains a fetch-mode field; it is not a spend grant."""
    req = AnalysisRequest.model_validate(_analysis(data_mode="live"))
    assert req.data_mode == DataMode.LIVE
    assert hosted_live_defaults_remain_off() is True
    assert client_tried_to_enable_hosted_live(body={"data_mode": "live"}) is False


# ---------------------------------------------------------------------------
# C. Cache-bust / replay / forge activity_id / steal reservation
# ---------------------------------------------------------------------------


def test_cache_bust_keys_are_rejected() -> None:
    for field in ("cache_bust", "nocache", "no_cache", "bypass_cache", "cache_key"):
        assert field in cache_bust_hits({field: "1"})
        with pytest.raises(ClientPrivilegeError):
            reject_cache_bust({field: "1"})
        with pytest.raises(ValidationError):
            AnalysisRequest.model_validate({**_analysis(), field: True})


def test_replay_same_fingerprint_joins_does_not_double_reserve() -> None:
    ledger = _ledger(total=1)
    now = datetime.now(timezone.utc)
    first = ledger.try_reserve(_identity(), planned_units=1, now=now)
    second = ledger.try_reserve(_identity(), planned_units=1, now=now)
    assert first.code == DemoAllowanceDecisionCode.ELIGIBLE
    assert second.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION
    assert first.reservation.reservation_id == second.reservation.reservation_id
    assert ledger.snapshot().reserved_units == 1


def test_forged_activity_id_is_rejected() -> None:
    registry = ServerActivityRegistry()
    real = registry.mint(request_fingerprint=FP, reservation_id="res_1")
    with pytest.raises(ForgedActivityError, match="client_forged"):
        registry.reject_client_claimed_id("act_forged_by_client", request_fingerprint=FP)
    with pytest.raises(ForgedActivityError, match="steal"):
        registry.reject_client_claimed_id(real.activity_id, request_fingerprint=ATTACKER_FP)
    with pytest.raises(ForgedActivityError, match="unknown"):
        registry.lookup("act_unknown", request_fingerprint=FP)
    assert registry.lookup(real.activity_id, request_fingerprint=FP).activity_id == (
        real.activity_id
    )


def test_client_cannot_mint_second_activity_for_same_fingerprint() -> None:
    registry = ServerActivityRegistry()
    first = registry.mint(request_fingerprint=FP)
    second = registry.mint(request_fingerprint=FP)
    assert first.activity_id == second.activity_id


def test_reservation_steal_via_client_id_is_denied() -> None:
    ledger = _ledger()
    now = datetime.now(timezone.utc)
    victim = ledger.try_reserve(_identity(), planned_units=1, now=now)
    assert victim.reservation is not None
    gate = steal_reservation_result(
        ledger,
        victim_reservation_id=victim.reservation.reservation_id,
        attacker_identity=_identity(request_fingerprint=ATTACKER_FP),
        planned_units=1,
        now=now,
    )
    assert gate.allowed is False
    assert "client_supplied_reservation_id" in gate.reason
    assert ledger.get(victim.reservation.reservation_id).state == ReservationState.RESERVED


def test_reservation_identity_mismatch_cannot_consume() -> None:
    ledger = _ledger()
    now = datetime.now(timezone.utc)
    victim = ledger.try_reserve(_identity(), planned_units=1, now=now)
    with pytest.raises(ReservationStealError):
        consume_server_reservation(
            ledger,
            reservation_id=victim.reservation.reservation_id,
            identity=_identity(request_fingerprint=ATTACKER_FP),
            planned_units=1,
            client_supplied_reservation_id=True,
            now=now,
        )
    with pytest.raises(DemoAllowanceError, match="fingerprint"):
        consume_server_reservation(
            ledger,
            reservation_id=victim.reservation.reservation_id,
            identity=_identity(request_fingerprint=ATTACKER_FP),
            planned_units=1,
            client_supplied_reservation_id=False,
            now=now,
        )


# ---------------------------------------------------------------------------
# D. Double-spend and paid-retry
# ---------------------------------------------------------------------------


def test_double_consume_is_terminal() -> None:
    ledger = _ledger()
    now = datetime.now(timezone.utc)
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=now)
    consume_server_reservation(
        ledger,
        reservation_id=reserved.reservation.reservation_id,
        identity=_identity(),
        planned_units=1,
        client_supplied_reservation_id=False,
        now=now,
    )
    with pytest.raises(DemoAllowanceError):
        consume_server_reservation(
            ledger,
            reservation_id=reserved.reservation.reservation_id,
            identity=_identity(),
            planned_units=1,
            client_supplied_reservation_id=False,
            now=now,
        )
    assert ledger.snapshot().consumed_units == 1
    assert ledger.snapshot().remaining_units == 1


def test_distinct_fingerprint_cannot_reuse_grant() -> None:
    ledger = _ledger()
    now = datetime.now(timezone.utc)
    reserved = ledger.try_reserve(_identity(), planned_units=1, now=now)
    grant = grant_from_demo_reservation(reserved.reservation)
    stolen = can_execute_paid_acquisition(
        grant,
        request_fingerprint=ATTACKER_FP,
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        geometry_sha256=GEO,
        planned_units=1,
        now=now,
    )
    assert stolen.allowed is False
    assert stolen.reason == "fingerprint_mismatch"


def test_client_paid_retry_after_consume_is_denied() -> None:
    assert (
        paid_retry_allowed(
            state=WorkerRecoveryState.CONSUMED,
            submit_could_have_occurred=True,
            reservation_state=ReservationState.CONSUMED,
            client_requested_retry=True,
        )
        is False
    )
    assert (
        paid_retry_allowed(
            state=WorkerRecoveryState.FAILED_POST_SUBMIT,
            submit_could_have_occurred=True,
            reservation_state=ReservationState.RESERVED,
            client_requested_retry=False,
        )
        is False
    )
    assert (
        paid_retry_allowed(
            state=WorkerRecoveryState.FAILED_PRE_SUBMIT,
            submit_could_have_occurred=False,
            reservation_state=ReservationState.RESERVED,
            client_requested_retry=False,
        )
        is True
    )


def test_second_area_unit_exhausts_cap() -> None:
    ledger = _ledger(total=1)
    now = datetime.now(timezone.utc)
    first = ledger.try_reserve(_identity(), planned_units=1, now=now)
    other = ledger.try_reserve(
        _identity(request_fingerprint=ATTACKER_FP),
        planned_units=1,
        now=now,
    )
    assert first.spend_authorized is True
    assert other.code == DemoAllowanceDecisionCode.ALLOWANCE_EXHAUSTED


# ---------------------------------------------------------------------------
# E. UNKNOWN_VENDOR_STATE forced resubmit
# ---------------------------------------------------------------------------


def test_unknown_vendor_state_never_auto_resubmits() -> None:
    decision = decide_unknown_vendor_recovery(
        state=WorkerRecoveryState.UNKNOWN_VENDOR_STATE,
        activity_id=None,
        client_force_resubmit=False,
        submit_could_have_occurred=True,
    )
    assert decision.may_submit is False
    assert decision.action == RecoveryAction.RECOVERY_REQUIRED


def test_unknown_vendor_state_with_activity_id_reconciles_only() -> None:
    decision = decide_unknown_vendor_recovery(
        state=WorkerRecoveryState.UNKNOWN_VENDOR_STATE,
        activity_id="act_known",
        client_force_resubmit=False,
        submit_could_have_occurred=True,
    )
    assert decision.may_submit is False
    assert decision.action == RecoveryAction.RECONCILE_ONLY


def test_client_forced_resubmit_is_refused() -> None:
    for state in WorkerRecoveryState:
        decision = decide_unknown_vendor_recovery(
            state=state,
            activity_id="act_x",
            client_force_resubmit=True,
            submit_could_have_occurred=True,
        )
        assert decision.may_submit is False
        assert decision.action == RecoveryAction.REFUSE_RESUBMIT


def test_submit_window_crash_does_not_resubmit() -> None:
    decision = decide_unknown_vendor_recovery(
        state=WorkerRecoveryState.SUBMITTING,
        activity_id=None,
        client_force_resubmit=False,
        submit_could_have_occurred=True,
    )
    assert decision.may_submit is False
    assert "do_not_resubmit" in decision.reason


def test_exactly_once_is_not_claimed() -> None:
    """Honesty fixture: policy is at-most-one-submit, not vendor exactly-once."""
    decision = decide_unknown_vendor_recovery(
        state=WorkerRecoveryState.ACTIVITY_ID_PERSISTED,
        activity_id="act_1",
        client_force_resubmit=False,
        submit_could_have_occurred=True,
    )
    assert decision.may_submit is False
    assert "exactly-once" not in decision.reason
    assert "exactly_once" not in decision.reason


def test_canonical_privilege_set_is_complete_for_program() -> None:
    required = {
        "allowance",
        "budget",
        "key",
        "force_live",
        "operator_approval",
        "reservation_state",
        "activity_id",
        "hosted_live_enabled",
    }
    assert required.issubset(CLIENT_NEVER_SET_FIELDS)
