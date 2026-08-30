"""Signal B domain types stay off AnalysisResult and carry no q_A / Decision 8."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain import AnalysisResult, ZoneDecisionResult
from app.domain.signals import (
    HistoricalNormalizedSignalState,
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
    TwoSignalAvailability,
)


def _snapshot_provenance(**overrides: object) -> SignalProvenance:
    payload: dict[str, object] = {
        "signal_kind": ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        "area_id": "phoenix-demo",
        "target_timestamp": datetime(2024, 7, 15, 15, 0, 0),
        "timezone": "America/Phoenix",
        "source": "fortyguard_cached",
        "data_status": "cached",
        "geometry_version": "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        "aggregation_spec_version": "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    }
    payload.update(overrides)
    return SignalProvenance.model_validate(payload)


def test_analysis_result_has_no_signal_b_fields() -> None:
    fields = set(AnalysisResult.model_fields)
    assert "selected_time_snapshot" not in fields
    assert "historical_signal" not in fields
    assert "mean_temperature_c" not in fields
    zone_fields = set(ZoneDecisionResult.model_fields)
    assert "mean_temperature_c" not in zone_fields


def test_snapshot_zone_forbids_q_a_and_decision8_fields() -> None:
    zone = SelectedTimeSnapshotZone(
        zone_id="04013107401",
        mean_temperature_c=30.64,
        tile_count=12,
        coverage_status="ok",
    )
    assert set(SelectedTimeSnapshotZone.model_fields) == {
        "zone_id",
        "mean_temperature_c",
        "tile_count",
        "coverage_status",
        "quality_flags",
    }
    with pytest.raises(ValidationError):
        SelectedTimeSnapshotZone.model_validate(
            {
                "zone_id": "04013107401",
                "mean_temperature_c": 30.64,
                "tile_count": 12,
                "coverage_status": "ok",
                "q_A": 0.4,
            }
        )
    dumped = zone.model_dump()
    assert "q_A" not in dumped
    assert "thermal_ordering_permitted" not in dumped


def test_snapshot_cannot_carry_historical_reference_provenance() -> None:
    with pytest.raises(ValidationError, match="historical reference"):
        _snapshot_provenance(reference_version="PHX_ZTSI_REF_V1")


def test_snapshot_is_zone_level_and_not_a_tile_map() -> None:
    snapshot = SelectedTimeSnapshot(
        area_id="phoenix-demo",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=SignalAvailability.READY,
        provenance=_snapshot_provenance(),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="04013107401",
                mean_temperature_c=30.64,
                tile_count=12,
                coverage_status="ok",
            )
        ],
    )
    assert snapshot.spatial_resolution == "zone"
    assert snapshot.user_facing_tile_map is False
    assert snapshot.units == "celsius"
    assert snapshot.aggregation_method == "centroid_within_mean"


def test_two_signal_availability_stays_independent() -> None:
    state = TwoSignalAvailability(
        historical=HistoricalNormalizedSignalState(
            availability=SignalAvailability.NOT_PREPARED,
            provenance=SignalProvenance(
                signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                area_id="new-area",
                timezone="America/Phoenix",
            ),
        ),
        selected_time=SignalAvailability.READY,
    )
    assert state.combined_score_authorized is False
    assert state.historical.decision8_applies is True
    assert state.historical.availability == SignalAvailability.NOT_PREPARED
    assert state.selected_time == SignalAvailability.READY


def test_d8_insufficient_does_not_force_snapshot_unavailable() -> None:
    state = TwoSignalAvailability(
        historical=HistoricalNormalizedSignalState(
            availability=SignalAvailability.D8_INSUFFICIENT,
            provenance=SignalProvenance(
                signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                area_id="phoenix-demo",
                timezone="America/Phoenix",
                reference_version="PHX_ZTSI_REF_V1",
            ),
        ),
        selected_time=SignalAvailability.READY,
    )
    assert state.selected_time == SignalAvailability.READY
