"""Area-preparation job foundation. No vendor calls. Not durable."""

from __future__ import annotations

import pytest

from app.core.area_preparation import (
    AreaPreparationError,
    AreaPreparationStatus,
    InMemoryAreaPreparationStore,
    PreparationIdentity,
    create_or_join_preparation,
    record_unit_checkpoint,
    fail_preparation,
    mark_ready,
    transition,
)


PROTOCOL_PHOENIX_V1 = (
    "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ."
    "PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15__S2_PM15_CALENDAR_DAYS__"
    "YEARS_2022_2023_2024__HOUR_0300_LOCAL__GRANULARITY_100M"
)
PROTOCOL_OTHER_HOUR = PROTOCOL_PHOENIX_V1.replace("HOUR_0300_LOCAL", "HOUR_1500_LOCAL")
ZONE_SET = "04013107401,04013112700"


def _identity(**overrides: object) -> PreparationIdentity:
    payload = {
        "zone_set_id": ZONE_SET,
        "area_selection_policy_version": "PHX_DEMO_AOI_POLICY_V1",
        "reference_protocol_id": PROTOCOL_PHOENIX_V1,
        "geometry_sha256": "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    }
    payload.update(overrides)
    return PreparationIdentity(**payload)


def test_preparation_key_includes_reference_protocol_identity() -> None:
    key = _identity().key()
    assert PROTOCOL_PHOENIX_V1 in key
    assert "PHX_DEMO_AOI_POLICY_V1" in key
    assert ZONE_SET in key


def test_different_protocol_ids_do_not_dedupe() -> None:
    store = InMemoryAreaPreparationStore()
    first = create_or_join_preparation(
        _identity(),
        required_units=93,
        store=store,
    )
    second = create_or_join_preparation(
        _identity(reference_protocol_id=PROTOCOL_OTHER_HOUR),
        required_units=93,
        store=store,
    )
    assert first.job_id != second.job_id
    assert first.identity.key() != second.identity.key()


def test_seasonal_context_can_live_inside_protocol_identity() -> None:
    summer = _identity()
    may = _identity(
        reference_protocol_id=PROTOCOL_PHOENIX_V1.replace(
            "S2_PM15_CALENDAR_DAYS", "MAY_WINDOW_V0"
        )
    )
    assert summer.key() != may.key()
    assert "S2_PM15_CALENDAR_DAYS" in summer.reference_protocol_id
    assert "MAY_WINDOW_V0" in may.reference_protocol_id


def test_duplicate_in_progress_request_joins_same_job() -> None:
    store = InMemoryAreaPreparationStore()
    first = create_or_join_preparation(_identity(), required_units=93, store=store)
    second = create_or_join_preparation(_identity(), required_units=93, store=store)
    assert first.job_id == second.job_id
    assert second.joined_existing is True
    assert first.status == AreaPreparationStatus.UNRESOLVED


def test_ready_package_is_reused() -> None:
    store = InMemoryAreaPreparationStore()
    job = create_or_join_preparation(_identity(), required_units=2, store=store)
    job = transition(job.job_id, AreaPreparationStatus.RESOLVING, store=store)
    job = transition(job.job_id, AreaPreparationStatus.PREPARING_REFERENCE, store=store)
    job = record_unit_checkpoint(job.job_id, unit_id="u1", store=store)
    job = record_unit_checkpoint(job.job_id, unit_id="u2", store=store)
    job = transition(job.job_id, AreaPreparationStatus.VALIDATING, store=store)
    ready = mark_ready(job.job_id, package_id="pkg_test", store=store)
    assert ready.status == AreaPreparationStatus.READY
    reused = create_or_join_preparation(_identity(), required_units=2, store=store)
    assert reused.job_id == ready.job_id
    assert reused.status == AreaPreparationStatus.READY
    assert reused.package_id == "pkg_test"


def test_progress_uses_protocol_defined_units_not_a_universal_93() -> None:
    store = InMemoryAreaPreparationStore()
    job = create_or_join_preparation(_identity(), required_units=4, store=store)
    assert job.required_units == 4
    assert job.completed_units == 0
    job = transition(job.job_id, AreaPreparationStatus.RESOLVING, store=store)
    job = transition(job.job_id, AreaPreparationStatus.PREPARING_REFERENCE, store=store)
    job = record_unit_checkpoint(job.job_id, unit_id="2022-06-30T03:00", store=store)
    assert job.completed_units == 1
    assert job.required_units == 4
    assert job.progress_ratio() == 0.25


def test_invalid_transition_is_rejected() -> None:
    store = InMemoryAreaPreparationStore()
    job = create_or_join_preparation(_identity(), required_units=1, store=store)
    with pytest.raises(AreaPreparationError, match="invalid transition"):
        transition(job.job_id, AreaPreparationStatus.READY, store=store)
    with pytest.raises(AreaPreparationError, match="invalid transition"):
        transition(job.job_id, AreaPreparationStatus.VALIDATING, store=store)


def test_partial_reference_is_not_ready() -> None:
    store = InMemoryAreaPreparationStore()
    job = create_or_join_preparation(_identity(), required_units=3, store=store)
    job = transition(job.job_id, AreaPreparationStatus.RESOLVING, store=store)
    job = transition(job.job_id, AreaPreparationStatus.PREPARING_REFERENCE, store=store)
    job = record_unit_checkpoint(job.job_id, unit_id="only-one", store=store)
    with pytest.raises(AreaPreparationError, match="incomplete"):
        transition(job.job_id, AreaPreparationStatus.VALIDATING, store=store)
    assert job.status != AreaPreparationStatus.READY
    loaded = store.get(job.job_id)
    assert loaded is not None
    assert loaded.status == AreaPreparationStatus.PREPARING_REFERENCE
    assert loaded.completed_units == 1


def test_failure_is_terminal_and_keeps_checkpoints() -> None:
    store = InMemoryAreaPreparationStore()
    job = create_or_join_preparation(_identity(), required_units=3, store=store)
    job = transition(job.job_id, AreaPreparationStatus.RESOLVING, store=store)
    job = transition(job.job_id, AreaPreparationStatus.PREPARING_REFERENCE, store=store)
    record_unit_checkpoint(job.job_id, unit_id="kept", store=store)
    failed = fail_preparation(job.job_id, reason="unit missing tiles", store=store)
    assert failed.status == AreaPreparationStatus.FAILED
    assert failed.checkpoint_unit_ids == ["kept"]
    assert failed.durable is False
    with pytest.raises(AreaPreparationError, match="terminal"):
        transition(failed.job_id, AreaPreparationStatus.RESOLVING, store=store)


def test_resume_metadata_lists_completed_unit_ids() -> None:
    store = InMemoryAreaPreparationStore()
    job = create_or_join_preparation(_identity(), required_units=3, store=store)
    job = transition(job.job_id, AreaPreparationStatus.RESOLVING, store=store)
    job = transition(job.job_id, AreaPreparationStatus.PREPARING_REFERENCE, store=store)
    record_unit_checkpoint(job.job_id, unit_id="a", store=store)
    record_unit_checkpoint(job.job_id, unit_id="b", store=store)
    loaded = store.get(job.job_id)
    assert loaded is not None
    assert loaded.resume_unit_ids() == ["a", "b"]
    assert loaded.missing_unit_count() == 1


def test_store_is_explicitly_not_durable() -> None:
    store = InMemoryAreaPreparationStore()
    assert store.durable is False
    job = create_or_join_preparation(_identity(), required_units=1, store=store)
    assert job.durable is False


def test_no_public_preparation_route() -> None:
    from app.api.router import api_router

    paths = [getattr(route, "path", "") for route in api_router.routes]
    assert not any("prepare" in path for path in paths)


def test_no_vendor_invocation_surface() -> None:
    from pathlib import Path

    from app.core import area_preparation as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "fetch_heatmap" not in source
    assert "/v1/heatmap" not in source
    assert "FortyGuard" not in source
    assert "FORTYGUARD" not in source
