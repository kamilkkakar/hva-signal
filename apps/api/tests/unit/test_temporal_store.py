from __future__ import annotations

import pytest

from app.services.temporal_assemble import assemble_season_summary
from app.services.seasonal_thermal import SlotValue
from app.services.temporal_store import (
    InMemoryTemporalStore,
    SqliteTemporalStore,
    ZoneHourRow,
    open_temporal_store,
)
from datetime import date


def _row(temp: float | None = 31.0) -> ZoneHourRow:
    return ZoneHourRow(
        area_id="phoenix-demo",
        zone_id="04013107401",
        valid_time_utc="2024-07-15T10:00:00Z",
        valid_time_local="2024-07-15T03:00:00",
        timezone="America/Phoenix",
        temperature_c=temp,
        source_mode="replay",
        source_family="fortyguard",
        temperature_quantity="tcm_zone_mean",
        sampling_design="ANCHOR_0300",
        zone_geometry_version="US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        aggregation_spec_version="PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        observation_kind="instant",
        coverage_status="ok" if temp is not None else "insufficient_evidence",
    )


def test_memory_and_sqlite_round_trip() -> None:
    memory = open_temporal_store()
    assert isinstance(memory, InMemoryTemporalStore)
    memory.put_zone_hour(_row())
    got = memory.get_zone_hours(area_id="phoenix-demo", zone_id="04013107401")
    assert got[0].temperature_c == 31.0

    sqlite = SqliteTemporalStore(":memory:")
    sqlite.put_zone_hour(_row(None))
    missing = sqlite.get_zone_hours(area_id="phoenix-demo")
    assert missing[0].temperature_c is None
    sqlite.put_season_summary(
        {
            "area_id": "phoenix-demo",
            "zone_id": "04013107401",
            "window_id": "SEASON:JJA:2024",
            "sampling_design": "ANCHOR_0300",
            "source_mode": "replay",
            "availability": "NOT_PREPARED",
            "mean_c": None,
            "n_present": 3,
            "n_expected": 92,
            "coverage_class": "INSUFFICIENT",
        }
    )
    season = sqlite.get_season_summary(
        area_id="phoenix-demo",
        zone_id="04013107401",
        window_id="SEASON:JJA:2024",
        sampling_design="ANCHOR_0300",
        source_mode="replay",
    )
    assert season is not None
    assert season["mean_c"] is None
    sqlite.close()


def test_store_refuses_job_file() -> None:
    with pytest.raises(ValueError):
        SqliteTemporalStore("analysis_jobs.sqlite")


def test_assemble_unpublished_and_no_spend() -> None:
    doc = assemble_season_summary(
        area_id="phoenix-demo",
        zone_id="04013107401",
        window_id="SEASON:JJA:2024",
        slots=[SlotValue(local_date=date(2024, 7, 15), temperature_c=33.0)],
    )
    assert doc.publication_status == "UNPUBLISHED"
    assert doc.availability == "NOT_PREPARED"
    dumped = doc.public_projection()
    assert "spend" not in dumped
