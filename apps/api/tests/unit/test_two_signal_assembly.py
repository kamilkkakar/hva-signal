"""Internal two-signal assembly stays independent and unpublished."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain import AnalysisResult
from app.domain.signals import (
    HistoricalNormalizedSignalState,
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
    TwoSignalAssembly,
)
from app.api.router import api_router


def test_analysis_result_and_routes_do_not_expose_assembly() -> None:
    assert "selected_time_snapshot" not in AnalysisResult.model_fields
    paths = " ".join(getattr(route, "path", "") for route in api_router.routes)
    assert "snapshot" not in paths
    assert "prepare" not in paths


def test_a_unprepared_b_ready_is_representable() -> None:
    snapshot = SelectedTimeSnapshot(
        area_id="candidate-area",
        target_timestamp=datetime(2024, 7, 15, 15, 0, 0),
        timezone="America/Phoenix",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        availability=SignalAvailability.READY,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id="candidate-area",
            timezone="America/Phoenix",
        ),
        zones=[
            SelectedTimeSnapshotZone(
                zone_id="z1",
                mean_temperature_c=30.1,
                tile_count=2,
                coverage_status="ok",
            )
        ],
    )
    assembly = TwoSignalAssembly(
        area_id="candidate-area",
        historical=HistoricalNormalizedSignalState(
            availability=SignalAvailability.NOT_PREPARED,
            provenance=SignalProvenance(
                signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                area_id="candidate-area",
                timezone="America/Phoenix",
            ),
        ),
        selected_time=snapshot,
        selected_time_availability=SignalAvailability.READY,
    )
    assert assembly.combined_score_authorized is False
    assert assembly.historical.availability == SignalAvailability.NOT_PREPARED
    assert assembly.selected_time_availability == SignalAvailability.READY


def test_b_not_requested_has_no_snapshot() -> None:
    assembly = TwoSignalAssembly(
        area_id="phoenix-demo",
        historical=HistoricalNormalizedSignalState(
            availability=SignalAvailability.READY,
            provenance=SignalProvenance(
                signal_kind=ThermalSignalKind.HISTORICAL_NORMALIZED,
                area_id="phoenix-demo",
                timezone="America/Phoenix",
                reference_version="PHX_ZTSI_REF_V1",
            ),
        ),
        selected_time=None,
        selected_time_availability=SignalAvailability.NOT_REQUESTED,
    )
    assert assembly.selected_time is None
    with pytest.raises(ValidationError):
        TwoSignalAssembly(
            area_id="phoenix-demo",
            historical=assembly.historical,
            selected_time=None,
            selected_time_availability=SignalAvailability.READY,
        )
