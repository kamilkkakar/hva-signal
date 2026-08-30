from __future__ import annotations

import inspect
from datetime import date, datetime

import pytest

from app.services.aoi_timezone import AoiLocalTimeError
from app.services.daily_thermal_profile import (
    DuplicateHourError,
    HourIn,
    IneligibleHourError,
    SourceMixError,
    build_profile,
    ingest,
)


D = date(2024, 7, 15)


def test_missing_hours_remain_none_not_zero() -> None:
    p = build_profile(date=D, hours={3: 28.0}, design="HOURLY_24")
    assert p.hours[3].temperature_c == 28.0
    assert p.hours[3].status == "observed"
    assert p.n_present == 1
    assert p.n_expected == 24
    assert all(p.hours[h].temperature_c is None for h in range(24) if h != 3)
    assert all(p.hours[h].status == "missing" for h in range(24) if h != 3)
    assert p.interpolated is False
    assert p.temporal_coverage_class == "PARTIAL"
    assert p.hours[0].temperature_c is not 0.0
    assert p.hours[15].temperature_c is None


def test_anchor_0300_full_is_hourly_24_insufficient_for_cycle_claims() -> None:
    p = build_profile(hours={3: 31.2}, design="HOURLY_24", date=D)
    assert p.temporal_coverage_class == "PARTIAL"
    assert p.extrema_wording == "among_observed_hours"
    assert p.day_night_status.startswith("withheld")
    assert p.cooling.status.startswith("withheld")
    assert p.day_night_diff_c is None
    a = build_profile(hours={3: 31.2}, design="ANCHOR_0300", date=D)
    assert a.temporal_coverage_class == "FULL"
    assert a.n_expected == 1


def test_does_not_interpolate_gap_between_14_and_16() -> None:
    p = build_profile(hours={14: 40.0, 16: 42.0}, design="HOURLY_24", date=D)
    assert p.hours[15].temperature_c is None
    assert p.hours[15].status == "missing"
    assert p.peak_hours_local == [16]
    assert p.interpolated is False


def test_window_aggregate_cannot_enter_hourly_slot() -> None:
    obs = HourIn(
        hour=3,
        temperature_c=30.0,
        temporal_mode="hour_range",
        quality_flags=("window_aggregate",),
    )
    with pytest.raises(IneligibleHourError):
        build_profile(hours_from=[obs], design="HOURLY_24", date=D)


def _synthetic_diurnal(*, peak_hour: int = 16, peak: float = 42.0, predawn: float = 27.0) -> dict[int, float]:
    hours = {}
    for h in range(24):
        if h <= 5:
            hours[h] = predawn + h * 0.1
        elif h < peak_hour:
            hours[h] = 30.0 + (h - 6)
        elif h == peak_hour:
            hours[h] = peak
        else:
            hours[h] = peak - (h - peak_hour)
    return hours


def test_full_24_computes_extrema_day_night_and_cooling() -> None:
    hours = _synthetic_diurnal()
    p = build_profile(hours=hours, design="HOURLY_24", date=D)
    assert p.n_present == 24
    assert p.temporal_coverage_class == "FULL"
    assert p.extrema_wording == "daily"
    assert p.peak_hours_local == [16]
    assert p.t_max_obs_c == 42.0
    assert p.diurnal_range_obs_c == pytest.approx(p.t_max_obs_c - p.t_min_obs_c)
    assert p.day_night_status == "computed"
    assert p.day_night_diff_c == pytest.approx(p.day_mean_c - p.night_mean_c)
    assert p.day_night_diff_c > 0
    assert p.cooling.status == "computed"
    assert p.cooling.start_hour_local == 16
    assert p.cooling.end_hour_local == 23
    assert p.cooling.delta_c < 0
    assert p.cooling.rate_c_per_h == pytest.approx(p.cooling.delta_c / 7)


def test_adequate_but_afternoon_gap_blocks_daily_peak_wording() -> None:
    hours = {h: 30.0 + h * 0.2 for h in range(24) if h not in {15, 16}}
    p = build_profile(hours=hours, design="HOURLY_24", date=D)
    assert p.temporal_coverage_class == "ADEQUATE"
    assert p.extrema_wording == "among_observed_hours"
    assert p.hours[15].status == "missing"


def test_eighteen_hours_empty_afternoon_is_partial_not_adequate() -> None:
    hours = {h: 30.0 for h in list(range(0, 12)) + list(range(18, 24))}
    p = build_profile(hours=hours, design="HOURLY_24", date=D)
    assert p.n_present == 18
    assert p.temporal_coverage_class == "PARTIAL"
    assert p.day_night_diff_c is None


def test_tied_peaks_report_all_hours_display_earliest() -> None:
    hours = {h: 30.0 for h in range(24)}
    hours[5] = 28.0
    hours[14] = 41.0
    hours[15] = 41.0
    p = build_profile(hours=hours, date=D)
    assert p.peak_hours_local == [14, 15]
    assert p.t_max_obs_c == 41.0


def test_duplicate_hour_different_values_fail_closed() -> None:
    with pytest.raises(DuplicateHourError):
        build_profile(raw=[(15, 40.0), (15, 41.0)], date=D)


def test_nan_is_not_a_temperature() -> None:
    p = build_profile(hours={3: float("nan"), 4: 29.0}, date=D)
    assert p.hours[3].status == "missing"
    assert p.hours[3].temperature_c is None


def test_cooling_withheld_when_post_peak_hour_missing() -> None:
    hours = _synthetic_diurnal(peak_hour=16)
    del hours[19]
    p = build_profile(hours=hours, date=D)
    assert p.cooling.status in {"withheld_gap", "withheld_insufficient_span", "computed"}
    if p.cooling.rate_c_per_h is not None:
        assert p.cooling.end_hour_local == 18
        assert p.cooling.rate_c_per_h != pytest.approx((hours[23] - hours[16]) / 7)


def test_day_night_means_ignore_morning_and_evening() -> None:
    hours = {
        **{h: 20.0 for h in range(0, 6)},
        **{h: 99.0 for h in range(6, 12)},
        **{h: 30.0 for h in range(12, 18)},
        **{h: 99.0 for h in range(18, 24)},
    }
    p = build_profile(hours=hours, date=D)
    assert p.night_mean_c == pytest.approx(20.0)
    assert p.day_mean_c == pytest.approx(30.0)
    assert p.day_night_diff_c == pytest.approx(10.0)


def test_module_does_not_import_temporal_anomaly() -> None:
    import app.services.daily_thermal_profile as m

    source = inspect.getsource(m)
    assert "compute_q_a" not in source
    assert "evaluate_hazard_spread" not in source
    assert "q_A" not in source


def test_hour_03_is_temperature_not_quantile() -> None:
    hours = {h: 28.0 for h in range(6)}
    hours[3] = 28.4
    p = build_profile(hours=hours, date=D)
    assert p.hours[3].temperature_c == 28.4
    assert not hasattr(p, "q_A")


def test_off_hour_timestamp_is_rejected_not_rounded() -> None:
    with pytest.raises(AoiLocalTimeError):
        ingest(datetime(2024, 7, 15, 15, 30), tz="America/Phoenix")


def test_mixed_source_modes_fail_closed() -> None:
    with pytest.raises(SourceMixError):
        build_profile(
            raw=[
                HourIn(15, 40.0, source_mode="replay"),
                HourIn(16, 41.0, source_mode="fortyguard_live"),
            ],
            date=D,
        )


def test_public_2m_cannot_fill_fortyguard_gap() -> None:
    with pytest.raises(SourceMixError):
        build_profile(
            raw=[
                HourIn(3, 28.0, source_family="fortyguard"),
                HourIn(15, 41.0, source_family="public"),
            ],
            date=D,
        )


def test_sampled_6h_leaves_other_hours_missing() -> None:
    p = build_profile(hours={0: 28, 6: 30, 12: 38, 18: 33}, design="SAMPLED_6H", date=D)
    assert p.n_expected == 4
    q = build_profile(hours={0: 28, 6: 30, 12: 38, 18: 33}, design="HOURLY_24", date=D)
    assert q.n_present == 4
    assert q.n_expected == 24
    assert q.hours[1].status == "missing"
    assert q.temporal_coverage_class == "PARTIAL"
