"""Client flags and data_mode cannot authorize spend."""

from app.domain.enums import DataMode
from app.domain.signals import ThermalSignalKind
from app.services.spend_gate import waiting_grant
from app.services.spend_threat_guards import (
    client_flags_cannot_authorize,
    data_mode_cannot_authorize,
    grant_may_cover_request,
)


def test_client_approval_flags_are_detected() -> None:
    hits = client_flags_cannot_authorize(
        {"area_id": "phoenix-demo", "approved": True, "skip_approval": True}
    )
    assert hits == ["approved", "skip_approval"]


def test_live_mode_is_still_not_authorization() -> None:
    assert data_mode_cannot_authorize(DataMode.LIVE) is True
    assert data_mode_cannot_authorize(DataMode.REPLAY) is True


def test_grant_does_not_cover_other_area_fingerprint() -> None:
    grant = waiting_grant(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint="aa" * 32,
        geometry_sha256="bb" * 32,
        requested_units=1,
        planned_acquisition_units=1,
    )
    assert (
        grant_may_cover_request(
            grant,
            signal_kind="selected_time_snapshot",
            request_fingerprint="cc" * 32,
            geometry_sha256="bb" * 32,
        )
        is False
    )
