from __future__ import annotations

from datetime import date

import pytest

from app.services.daily_thermal_profile import HourIn, IneligibleHourError, SourceMixError, build_profile
from app.services.temporal_source import refuse_blend
from app.domain.temporal import TemporalSourceFamily


D = date(2024, 7, 15)


def test_interpolated_always_false() -> None:
    p = build_profile(hours={3: 28.0, 15: 40.0}, date=D)
    assert p.interpolated is False
    assert p.hours[4].temperature_c is None
    assert p.hours[14].temperature_c is None


def test_type2_not_unpacked() -> None:
    with pytest.raises(IneligibleHourError):
        build_profile(
            hours_from=[HourIn(3, 30.0, temporal_mode="full_day", quality_flags=("window_aggregate",))],
            date=D,
        )


def test_mixed_source_ratio_forbidden() -> None:
    with pytest.raises(SourceMixError):
        build_profile(
            raw=[
                HourIn(3, 28.0, source_family="fortyguard"),
                HourIn(15, 41.0, source_family="public"),
            ],
            date=D,
        )
    with pytest.raises(SourceMixError):
        refuse_blend(TemporalSourceFamily.FORTYGUARD, TemporalSourceFamily.PUBLIC)
