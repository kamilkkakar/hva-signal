from __future__ import annotations

from app.integrations.fortyguard.partitioning import AOI_AREA_CEILING_KM2, plan_partitions
from app.integrations.fortyguard.temporal_modes import to_filter_type
from app.integrations.fortyguard.transport_models import HeatmapTemporalMode

from .helpers import PHOENIX_HOURLY_AOI


def test_temporal_mode_maps_to_filter_type_1_through_4() -> None:
    assert to_filter_type(HeatmapTemporalMode.SINGLE_HOUR) == 1
    assert to_filter_type(HeatmapTemporalMode.HOUR_RANGE) == 2
    assert to_filter_type(HeatmapTemporalMode.FULL_DAY) == 3
    assert to_filter_type(HeatmapTemporalMode.DAY_RANGE) == 4
    # API has no month filter; month is a 31-day filter_type=4 window.
    assert to_filter_type(HeatmapTemporalMode.MONTH) == 4


def test_small_aoi_is_a_single_partition() -> None:
    plans = plan_partitions(PHOENIX_HOURLY_AOI)
    assert len(plans) == 1
    assert plans[0].area_km2 < AOI_AREA_CEILING_KM2


def test_large_aoi_splits_under_ceiling() -> None:
    big = {
        "type": "Polygon",
        "coordinates": [
            [
                [-113.0, 33.0],
                [-111.0, 33.0],
                [-111.0, 35.0],
                [-113.0, 35.0],
                [-113.0, 33.0],
            ]
        ],
    }
    plans = plan_partitions(big)
    assert len(plans) > 1
    assert all(p.area_km2 <= AOI_AREA_CEILING_KM2 + 1e-3 for p in plans)
