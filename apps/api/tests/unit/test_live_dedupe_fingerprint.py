"""LIVE-G fingerprint semantics: join key is Signal B snapshot identity."""

from datetime import datetime, timezone

import pytest

from app.domain.live_dedupe import (
    AT_MOST_ONE_SUBMIT,
    LIVE_SUBMIT_FINGERPRINT_EXCLUDED,
    LIVE_SUBMIT_FINGERPRINT_FIELDS,
    LIVE_SUBMIT_FINGERPRINT_VERSION,
    LiveAcquireRequest,
)
from app.services.job_identity import two_signal_job_fingerprint
from app.services.live_dedupe import (
    fingerprint_excludes_client_and_spend_fields,
    live_submit_document,
    live_submit_fingerprint,
)
from app.services.snapshot_identity import snapshot_request_fingerprint


def _req(**overrides: object) -> LiveAcquireRequest:
    payload = {
        "area_id": "phoenix-demo",
        "geometry_sha256": "aa" * 32,
        "zone_geometry_version": "GEO_V1",
        "target_timestamp": datetime(2024, 7, 15, 15, 0, 0),
        "timezone": "America/Phoenix",
        "aggregation_spec_version": "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    }
    payload.update(overrides)
    return LiveAcquireRequest(**payload)  # type: ignore[arg-type]


def test_identical_requests_share_submit_fingerprint() -> None:
    assert live_submit_fingerprint(_req()) == live_submit_fingerprint(_req())
    assert len(live_submit_fingerprint(_req())) == 64


def test_submit_fingerprint_is_snapshot_identity_not_a_fork() -> None:
    request = _req()
    assert live_submit_fingerprint(request) == snapshot_request_fingerprint(
        area_id=request.area_id,
        geometry_sha256=request.geometry_sha256,
        zone_geometry_version=request.zone_geometry_version,
        target_timestamp=request.target_timestamp,
        timezone=request.timezone,
        analytic=request.analytic,
        granularity_m=request.granularity_m,
        aggregation_spec_version=request.aggregation_spec_version,
        temporal_mode=request.temporal_mode,
        adapter_version=request.adapter_version,
    )
    assert live_submit_document(request)["identity_version"] == LIVE_SUBMIT_FINGERPRINT_VERSION


def test_nonce_and_spend_fields_do_not_split_the_join() -> None:
    a = live_submit_fingerprint(_req(request_nonce="client-a"))
    b = live_submit_fingerprint(_req(request_nonce="client-b"))
    assert a == b


def test_hour_geometry_area_analytic_split_the_join() -> None:
    baseline = live_submit_fingerprint(_req())
    assert live_submit_fingerprint(_req(area_id="other-area")) != baseline
    assert live_submit_fingerprint(_req(geometry_sha256="bb" * 32)) != baseline
    assert (
        live_submit_fingerprint(_req(target_timestamp=datetime(2024, 7, 15, 16, 0, 0)))
        != baseline
    )
    assert live_submit_fingerprint(_req(analytic="lst")) != baseline
    assert live_submit_fingerprint(_req(granularity_m=200)) != baseline


def test_document_keys_match_include_exclude_spec() -> None:
    doc = live_submit_document(_req())
    assert tuple(sorted(doc)) == tuple(sorted(LIVE_SUBMIT_FINGERPRINT_FIELDS))
    assert fingerprint_excludes_client_and_spend_fields(doc) is True
    for excluded in LIVE_SUBMIT_FINGERPRINT_EXCLUDED:
        assert excluded not in doc


def test_reference_protocol_is_not_a_submit_join_field() -> None:
    blob = str(live_submit_document(_req()))
    assert "reference" not in blob.lower()


def test_aware_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="naive"):
        live_submit_fingerprint(
            _req(target_timestamp=datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc))
        )


def test_two_signal_job_key_is_not_the_vendor_submit_key() -> None:
    request = _req()
    submit = live_submit_fingerprint(request)
    composed = two_signal_job_fingerprint(
        area_id=request.area_id,
        geometry_sha256=request.geometry_sha256,
        request_historical=False,
        request_selected_time=True,
        selected_time_fingerprint=submit,
    )
    assert composed != submit


def test_at_most_one_submit_claims_are_honest() -> None:
    assert AT_MOST_ONE_SUBMIT.exactly_once_at_vendor is False
    assert AT_MOST_ONE_SUBMIT.vendor_idempotency_assumed is False
    assert AT_MOST_ONE_SUBMIT.vendor_idempotency_required is False
    assert AT_MOST_ONE_SUBMIT.safe_automatic_resubmit_after_crash_during_submit is False
    assert AT_MOST_ONE_SUBMIT.multi_process_without_shared_lock is False
    assert AT_MOST_ONE_SUBMIT.failed_post_submit_may_resubmit is False
    assert AT_MOST_ONE_SUBMIT.unknown_vendor_state_may_resubmit is False
    assert AT_MOST_ONE_SUBMIT.at_most_one_submit_while_join_record_lives is True
    assert AT_MOST_ONE_SUBMIT.dedupe_before_allowance is True
    assert AT_MOST_ONE_SUBMIT.submit_slot_taken_before_vendor_io is True
