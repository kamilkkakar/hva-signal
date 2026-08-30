"""A vs B public provenance field guarantees (07_PROVENANCE_CONTRACT.md)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.signals import SignalAvailability, SignalProvenance, ThermalSignalKind
from app.schemas.signal_provenance import (
    A_REQUIRED_WHEN_COMPUTED,
    B_FORBIDDEN_FIELDS,
    B_REQUIRED_WHEN_PATH_KNOWN,
    NATIONAL_AGGREGATION_SPEC,
    PHOENIX_AGGREGATION_SPEC,
    PublicSignalProvenanceView,
)
from app.services.signal_provenance import (
    A_NOT_PREPARED_COPY,
    B_FORBIDDEN_COPY,
    SignalProvenanceError,
    a_is_computed,
    active_signal_view,
    assert_ab_field_guarantees,
    assert_b_has_no_reference,
    assert_national_b_stamps,
    decision8_panel_permitted,
    display_state,
    historical_lines,
    legacy_thermal_source,
    provenance_banner,
    qa_hover_permitted,
    reference_fields_permitted,
    refuse_areas_catalog_as_b_provenance,
    refuse_collapsed_source_tape,
    refuse_preference_as_source,
    selected_time_lines,
    view_from_internal,
)

SHA = "ab" * 32
PHOENIX_GEOM = (
    "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f"
)
NATIONAL_GEOM = (
    "US_CENSUS_TIGERLINE.census_tract.2025.PLACE_1714000."
    "NATIONAL_PLACE_GEOGRAPHY_V1.aaaaaaaa"
)
PHOENIX_REF = (
    "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ."
    "PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15"
)
NATIONAL_AREA = "us-place-1714000-2025-national-place-geography-v1"
A_TS = datetime(2022, 6, 30, 3, 0, 0)
B_TS = datetime(2024, 7, 15, 15, 0, 0)

A_VS_B_FIELD_MATRIX = (
    ("source", True, True),
    ("data_status", True, True),
    ("target_timestamp", True, True),
    ("timezone", True, True),
    ("geometry_version", True, True),
    ("geometry_sha256", False, True),
    ("aggregation_spec_version", True, True),
    ("reference_source", True, False),
    ("reference_version", True, False),
    ("request_fingerprint", False, True),
)


def _a_kwargs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "signal_kind": ThermalSignalKind.HISTORICAL_NORMALIZED,
        "source": ThermalDataSource.REPLAY,
        "data_status": DataStatus.REPLAY,
        "target_timestamp": A_TS,
        "timezone": "America/Phoenix",
        "geometry_version": PHOENIX_GEOM,
        "aggregation_spec_version": PHOENIX_AGGREGATION_SPEC,
        "reference_source": "cached_reference",
        "reference_version": PHOENIX_REF,
        "request_fingerprint": "cd" * 32,
    }
    payload.update(overrides)
    return payload


def _b_kwargs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        "source": ThermalDataSource.FORTYGUARD_CACHED,
        "data_status": DataStatus.CACHED,
        "target_timestamp": B_TS,
        "timezone": "America/Chicago",
        "geometry_version": NATIONAL_GEOM,
        "geometry_sha256": SHA,
        "aggregation_spec_version": NATIONAL_AGGREGATION_SPEC,
        "request_fingerprint": "ef" * 32,
    }
    payload.update(overrides)
    return payload


def _a(**overrides: object) -> PublicSignalProvenanceView:
    return PublicSignalProvenanceView.model_validate(_a_kwargs(**overrides))


def _b(**overrides: object) -> PublicSignalProvenanceView:
    return PublicSignalProvenanceView.model_validate(_b_kwargs(**overrides))


def test_field_matrix_a_requires_reference_b_requires_geometry_hash() -> None:
    assert "reference_version" in A_REQUIRED_WHEN_COMPUTED
    assert "reference_source" in A_REQUIRED_WHEN_COMPUTED
    assert "geometry_sha256" not in A_REQUIRED_WHEN_COMPUTED
    assert "reference_version" not in B_REQUIRED_WHEN_PATH_KNOWN
    assert "reference_source" not in B_REQUIRED_WHEN_PATH_KNOWN
    assert "geometry_sha256" in B_REQUIRED_WHEN_PATH_KNOWN
    for field, a_required, b_required in A_VS_B_FIELD_MATRIX:
        assert (field in A_REQUIRED_WHEN_COMPUTED) is a_required or field in {
            "geometry_sha256",
            "request_fingerprint",
        }
        if b_required and field != "request_fingerprint":
            assert field in B_REQUIRED_WHEN_PATH_KNOWN
        if not b_required:
            assert field not in B_REQUIRED_WHEN_PATH_KNOWN


def test_b_rejects_reference_version() -> None:
    with pytest.raises(ValidationError, match="historical reference"):
        _b(reference_version=PHOENIX_REF)


def test_b_rejects_reference_source() -> None:
    with pytest.raises(ValidationError, match="historical reference"):
        _b(reference_source="cached_reference")


def test_b_public_dump_omits_reference_keys() -> None:
    dumped = _b().public_dump()
    assert "reference_version" not in dumped
    assert "reference_source" not in dumped
    for forbidden in B_FORBIDDEN_FIELDS:
        assert forbidden not in dumped


def test_b_rejects_forbidden_extra_fields() -> None:
    for extra in ("hazard_spread", "q_A", "historical_result", "decision8"):
        with pytest.raises(ValidationError):
            PublicSignalProvenanceView.model_validate({**_b_kwargs(), extra: "leak"})


def test_a_computed_without_reference_version_is_rejected() -> None:
    view = _a(reference_version=None)
    with pytest.raises(SignalProvenanceError, match="Signal A computed"):
        assert_ab_field_guarantees(view, None, a_computed=True)


def test_a_not_prepared_does_not_invent_reference() -> None:
    view = PublicSignalProvenanceView(
        signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
        timezone="America/Chicago",
    )
    lines = historical_lines(view, availability=SignalAvailability.NOT_PREPARED)
    assert A_NOT_PREPARED_COPY in lines
    assert all("Reference:" not in line for line in lines)
    assert a_is_computed(SignalAvailability.NOT_PREPARED) is False
    assert a_is_computed(SignalAvailability.INSUFFICIENT_REFERENCE) is False
    assert a_is_computed(SignalAvailability.READY) is True


def test_cached_b_never_labels_live() -> None:
    banner, _stem = provenance_banner(
        ThermalDataSource.FORTYGUARD_CACHED, DataStatus.CACHED
    )
    assert banner == "FORTYGUARD CACHED"
    assert banner != "FORTYGUARD LIVE"
    with pytest.raises(ValidationError, match="live does not beat cached"):
        _b(source=ThermalDataSource.FORTYGUARD_CACHED, data_status=DataStatus.LIVE)
    with pytest.raises(SignalProvenanceError, match="live does not beat cached"):
        provenance_banner(ThermalDataSource.FORTYGUARD_CACHED, DataStatus.LIVE)


def test_live_source_does_not_beat_cached_status() -> None:
    with pytest.raises(ValidationError, match="live does not beat cached"):
        _b(source=ThermalDataSource.FORTYGUARD_LIVE, data_status=DataStatus.CACHED)
    with pytest.raises(SignalProvenanceError, match="live does not beat cached"):
        provenance_banner(ThermalDataSource.FORTYGUARD_LIVE, DataStatus.CACHED)


def test_cached_b_never_labels_replay() -> None:
    with pytest.raises(ValidationError, match="live does not beat cached"):
        _b(source=ThermalDataSource.FORTYGUARD_CACHED, data_status=DataStatus.REPLAY)
    with pytest.raises(SignalProvenanceError, match="live does not beat cached"):
        provenance_banner(ThermalDataSource.FORTYGUARD_CACHED, DataStatus.REPLAY)
    with pytest.raises(ValidationError, match="live does not beat cached"):
        _b(source=ThermalDataSource.REPLAY, data_status=DataStatus.CACHED)


def test_legal_source_status_pairs() -> None:
    assert provenance_banner(ThermalDataSource.FORTYGUARD_LIVE, DataStatus.LIVE)[0] == (
        "FORTYGUARD LIVE"
    )
    assert provenance_banner(ThermalDataSource.REPLAY, DataStatus.REPLAY)[0] == "REPLAY"
    banner, stem = provenance_banner(
        ThermalDataSource.FORTYGUARD_CACHED, DataStatus.PARTIAL
    )
    assert banner == "PARTIAL"
    assert stem == "FORTYGUARD CACHED"
    assert provenance_banner(
        ThermalDataSource.FORTYGUARD_CACHED, DataStatus.UNAVAILABLE
    )[0] == "UNAVAILABLE"


def test_no_d8_or_qa_on_b_rail() -> None:
    assert decision8_panel_permitted(ThermalSignalKind.SELECTED_TIME_SNAPSHOT) is False
    assert qa_hover_permitted(ThermalSignalKind.SELECTED_TIME_SNAPSHOT) is False
    assert reference_fields_permitted(ThermalSignalKind.SELECTED_TIME_SNAPSHOT) is False
    assert decision8_panel_permitted(ThermalSignalKind.HISTORICAL_NORMALIZED) is True
    assert qa_hover_permitted(ThermalSignalKind.HISTORICAL_NORMALIZED) is True
    assert reference_fields_permitted(ThermalSignalKind.HISTORICAL_NORMALIZED) is True
    state_b = display_state(_b(), selected_time_requested=True)
    assert state_b.show_decision8 is False
    assert state_b.show_qa_hover is False
    assert state_b.show_reference is False
    state_a = display_state(_a(), selected_time_requested=True)
    assert state_a.show_decision8 is True
    assert state_a.legacy_thermal_source is None


def test_legacy_thermal_source_null_when_b_requested() -> None:
    assert (
        legacy_thermal_source(
            selected_time_requested=True,
            historical_source=ThermalDataSource.REPLAY,
        )
        is None
    )
    assert (
        legacy_thermal_source(
            selected_time_requested=False,
            historical_source=ThermalDataSource.REPLAY,
        )
        == "replay"
    )


def test_b_lines_never_include_reference_or_d8_copy() -> None:
    lines = selected_time_lines(_b())
    text = "\n".join(lines)
    assert lines[0] == "Selected-Time Thermal Snapshot"
    assert "Target source: FORTYGUARD CACHED" in text
    assert "Aggregation:" in text
    assert "Geometry:" in text
    for token in B_FORBIDDEN_COPY:
        assert token not in text
    a_text = "\n".join(historical_lines(_a()))
    assert "Reference:" in a_text
    assert "03:00" in a_text
    assert "Nighttime Historical Thermal Signal" in a_text


def test_a_and_b_do_not_share_a_banner() -> None:
    a_state = display_state(_a())
    b_state = display_state(_b(), selected_time_requested=True)
    assert a_state.banner == "REPLAY"
    assert b_state.banner == "FORTYGUARD CACHED"
    assert a_state.banner != b_state.banner
    with pytest.raises(SignalProvenanceError, match="never collapse"):
        refuse_collapsed_source_tape()
    active = active_signal_view(ThermalSignalKind.SELECTED_TIME_SNAPSHOT, _a(), _b())
    assert active is not None
    assert active.signal_kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT
    assert active.reference_version is None


def test_national_b_rejects_phoenix_stamps() -> None:
    view = _b()
    assert_national_b_stamps(area_id=NATIONAL_AREA, view=view)
    with pytest.raises(SignalProvenanceError, match="Phoenix"):
        assert_national_b_stamps(
            area_id=NATIONAL_AREA,
            view=_b(geometry_version=PHOENIX_GEOM),
        )
    with pytest.raises(SignalProvenanceError, match="Phoenix aggregation"):
        assert_national_b_stamps(
            area_id=NATIONAL_AREA,
            view=_b(aggregation_spec_version=PHOENIX_AGGREGATION_SPEC),
        )


def test_areas_catalog_reference_is_not_b_provenance() -> None:
    with pytest.raises(SignalProvenanceError, match="not B provenance"):
        refuse_areas_catalog_as_b_provenance(PHOENIX_REF)


def test_acquisition_preference_is_not_source() -> None:
    with pytest.raises(SignalProvenanceError, match="not source"):
        refuse_preference_as_source("allow_hosted_live_demo")


def test_a_hour_frozen_b_hour_precision() -> None:
    with pytest.raises(ValidationError, match="frozen at 03:00"):
        _a(target_timestamp=datetime(2022, 6, 30, 15, 0, 0))
    with pytest.raises(ValidationError, match="hour precision"):
        _b(target_timestamp=datetime(2024, 7, 15, 15, 30, 0))


def test_b_path_known_requires_geometry_sha256() -> None:
    view = _b(geometry_sha256=None)
    with pytest.raises(SignalProvenanceError, match="Signal B path-known"):
        assert_ab_field_guarantees(None, view, b_path_known=True)
    with pytest.raises(ValidationError, match="64 lowercase hex"):
        _b(geometry_sha256="not-a-hash")


def test_view_from_internal_projects_a_and_rejects_b_reference() -> None:
    internal_a = SignalProvenance(
        signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
        area_id="phoenix-demo",
        target_timestamp=A_TS,
        timezone="America/Phoenix",
        source=ThermalDataSource.REPLAY,
        data_status=DataStatus.REPLAY,
        geometry_version=PHOENIX_GEOM,
        aggregation_spec_version=PHOENIX_AGGREGATION_SPEC,
        reference_version=PHOENIX_REF,
        reference_source="cached_reference",
        vendor_request_fingerprint="11" * 32,
    )
    view_a = view_from_internal(
        internal_a, availability=SignalAvailability.READY, computed=True
    )
    assert view_a.reference_version == PHOENIX_REF
    internal_b = SignalProvenance(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        area_id=NATIONAL_AREA,
        target_timestamp=B_TS,
        timezone="America/Chicago",
        source=ThermalDataSource.FORTYGUARD_CACHED,
        data_status=DataStatus.CACHED,
        geometry_version=NATIONAL_GEOM,
        aggregation_spec_version=NATIONAL_AGGREGATION_SPEC,
        vendor_request_fingerprint="22" * 32,
    )
    view_b = view_from_internal(
        internal_b,
        geometry_sha256=SHA,
        snapshot_present=True,
        area_id=NATIONAL_AREA,
    )
    assert_b_has_no_reference(view_b)
    assert_ab_field_guarantees(
        view_a,
        view_b,
        a_computed=True,
        b_path_known=True,
        selected_time_requested=True,
        national_area_id=NATIONAL_AREA,
    )
    assert view_a.request_fingerprint != view_b.request_fingerprint


def test_identical_request_fingerprints_are_rejected() -> None:
    shared = "99" * 32
    with pytest.raises(SignalProvenanceError, match="fingerprints"):
        assert_ab_field_guarantees(
            _a(request_fingerprint=shared),
            _b(request_fingerprint=shared),
        )
