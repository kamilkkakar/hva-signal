"""T-E daily thermal profile algorithm.

POLICY_ID: PHX_DAILY_THERMAL_PROFILE_V1_CANDIDATE
Missing hours stay missing. No interpolation. Hour 03 is temperature, not unusualness.
Do not build a 24h curve from phoenix-demo 03:00 replay.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable

from app.domain.temporal import EXPECTED_HOURS, SamplingDesign, TemporalCoverageClass
from app.services.aoi_timezone import AoiLocalTimeError, require_unique_aoi_local_hour
from app.services.temporal_coverage import (
    AFTERNOON_HOURS,
    CLOCK_BINS,
    EVENING_HOURS,
    NIGHT_HOURS,
    bin_present_counts,
    classify_for_design,
    longest_linear_gap_hours,
)
from app.services.temporal_source import SourceMixError

DAILY_PROFILE_POLICY_ID = "PHX_DAILY_THERMAL_PROFILE_V1_CANDIDATE"
DAYPART_CLOCK_V1_CANDIDATE = "DAYPART_CLOCK_V1_CANDIDATE"
COVERAGE_POLICY_ID = "PHX_TEMPORAL_COVERAGE_POLICY_V1_CANDIDATE"
MIN_COOLING_DURATION_H = 4

NOTE_COMPUTED = (
    "Same-calendar-day change after the observed peak, consecutive observed hours only. "
    "Truncates at 23:00 local. Not overnight cooling. Not recovery."
)
NOTE_GAP = "A single cooling rate is withheld because a missing hour breaks the post-peak span."
NOTE_TRUNCATED = "Overnight cooling past midnight is not computed on a single calendar date."


class ProfileBuildError(ValueError):
    pass


class DuplicateHourError(ProfileBuildError):
    pass


class IneligibleHourError(ProfileBuildError):
    pass


@dataclass(frozen=True)
class HourIn:
    hour: int
    temperature_c: float
    source_mode: str = "replay"
    source_family: str = "fortyguard"
    temporal_mode: str = "single_hour"
    quality_flags: tuple[str, ...] = ()
    valid_time_local: datetime | None = None


@dataclass
class HourSlot:
    hour_local: int
    temperature_c: float | None
    status: str
    valid_time_utc: datetime | None = None
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class CoolingTrajectory:
    status: str
    start_hour_local: int | None = None
    end_hour_local: int | None = None
    delta_c: float | None = None
    duration_h: int | None = None
    rate_c_per_h: float | None = None
    n_hours_in_span: int | None = None
    note: str = ""


@dataclass
class DailyProfileComputation:
    local_date: date
    iana_timezone: str
    sampling_design: str
    source_mode: str
    source_family: str
    interpolated: bool
    hours: list[HourSlot]
    n_present: int
    n_expected: int
    temporal_coverage_class: str
    longest_gap_hours: int
    bin_present: dict[str, int]
    t_min_obs_c: float | None
    t_max_obs_c: float | None
    min_hours_local: list[int]
    peak_hours_local: list[int]
    diurnal_range_obs_c: float | None
    extrema_wording: str
    day_night_diff_c: float | None
    day_mean_c: float | None
    night_mean_c: float | None
    day_n: int
    night_n: int
    day_night_status: str
    cooling: CoolingTrajectory
    daypart_policy_version: str = DAYPART_CLOCK_V1_CANDIDATE
    coverage_policy_version: str = COVERAGE_POLICY_ID


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def build_profile(
    *,
    local_date: date | None = None,
    date: date | None = None,
    hours: dict[int, float] | None = None,
    hours_from: Iterable[HourIn] | None = None,
    raw: Iterable[tuple[int, float] | HourIn] | None = None,
    design: str = "HOURLY_24",
    iana_timezone: str = "America/Phoenix",
    source_mode: str | None = None,
    source_family: str | None = None,
) -> DailyProfileComputation:
    """Build a daily profile. Missing hours stay None. Never interpolates."""
    local_date = local_date or date
    if local_date is None:
        raise ProfileBuildError("local_date is required")
    sampling = SamplingDesign(design)
    expected_n = EXPECTED_HOURS[sampling]
    expected_hours = _expected_hours(sampling)

    incoming: list[HourIn] = []
    if hours:
        incoming.extend(HourIn(hour=h, temperature_c=t) for h, t in hours.items())
    if hours_from:
        incoming.extend(hours_from)
    if raw:
        for item in raw:
            if isinstance(item, HourIn):
                incoming.append(item)
            else:
                incoming.append(HourIn(hour=item[0], temperature_c=item[1]))

    slots = {
        hour: HourSlot(hour_local=hour, temperature_c=None, status="missing")
        for hour in expected_hours
    }
    modes: set[str] = set()
    families: set[str] = set()

    for item in incoming:
        if "window_aggregate" in item.quality_flags or item.temporal_mode in {
            "hour_range",
            "full_day",
            "day_range",
            "month",
        }:
            raise IneligibleHourError("window aggregates cannot enter hourly slots")
        if item.valid_time_local is not None:
            require_unique_aoi_local_hour(item.valid_time_local, iana_timezone)
        if not _finite(item.temperature_c):
            continue
        if item.hour not in slots:
            if sampling is SamplingDesign.HOURLY_24:
                raise ProfileBuildError(f"hour {item.hour} outside expected set")
            continue
        existing = slots[item.hour]
        if existing.status == "observed":
            if existing.temperature_c != item.temperature_c:
                raise DuplicateHourError(f"duplicate hour {item.hour} with conflicting values")
            continue
        slots[item.hour] = HourSlot(
            hour_local=item.hour,
            temperature_c=float(item.temperature_c),
            status="observed",
        )
        modes.add(item.source_mode)
        families.add(item.source_family)

    if source_mode:
        modes.add(source_mode)
    if source_family:
        families.add(source_family)
    if len(modes) > 1:
        raise SourceMixError("mixed source_mode on one daily curve")
    if len(families) > 1:
        raise SourceMixError("public 2m cannot fill a FortyGuard gap")

    ordered = [slots[hour] for hour in expected_hours]
    present_hours = {slot.hour_local for slot in ordered if slot.status == "observed"}
    n_present = len(present_hours)
    bins = bin_present_counts(present_hours) if sampling is SamplingDesign.HOURLY_24 else {
        name: 0 for name in CLOCK_BINS
    }
    if sampling is SamplingDesign.HOURLY_24:
        for name, members in CLOCK_BINS.items():
            bins[name] = sum(1 for hour in members if hour in present_hours)
    longest_gap = (
        longest_linear_gap_hours(present_hours, 24)
        if sampling is SamplingDesign.HOURLY_24
        else (0 if n_present == expected_n else expected_n - n_present)
    )
    coverage = classify_for_design(
        sampling,
        n_present=n_present,
        n_expected=expected_n,
        present_hours=present_hours if sampling is SamplingDesign.HOURLY_24 else None,
    )

    obs = [(slot.hour_local, slot.temperature_c) for slot in ordered if slot.status == "observed"]
    if not obs:
        t_min = t_max = rng = None
        min_hours: list[int] = []
        peak_hours: list[int] = []
        extrema = "withheld"
    else:
        t_min = min(t for _, t in obs if t is not None)
        t_max = max(t for _, t in obs if t is not None)
        min_hours = sorted(h for h, t in obs if t == t_min)
        peak_hours = sorted(h for h, t in obs if t == t_max)
        rng = 0.0 if len(obs) < 2 else float(t_max) - float(t_min)
        if coverage is TemporalCoverageClass.FULL:
            extrema = "daily"
        elif coverage in {TemporalCoverageClass.ADEQUATE, TemporalCoverageClass.PARTIAL}:
            extrema = "among_observed_hours"
        else:
            extrema = "withheld"

    day_vals = [t for h, t in obs if h in AFTERNOON_HOURS and t is not None]
    night_vals = [t for h, t in obs if h in NIGHT_HOURS and t is not None]
    day_mean = _mean(day_vals)
    night_mean = _mean(night_vals)
    publish_dn = (
        coverage in {TemporalCoverageClass.ADEQUATE, TemporalCoverageClass.FULL}
        and len(night_vals) >= 4
        and bins.get("afternoon", 0) >= 4
        and len(day_vals) >= 4
    )
    if not publish_dn or day_mean is None or night_mean is None:
        day_night_diff = None
        day_night_status = "withheld_coverage"
    else:
        day_night_diff = day_mean - night_mean
        day_night_status = "computed"

    cooling = _cooling(
        ordered,
        peak_hours,
        coverage,
        bins,
        sampling,
    )

    return DailyProfileComputation(
        local_date=local_date,
        iana_timezone=iana_timezone,
        sampling_design=sampling.value,
        source_mode=source_mode or (next(iter(modes)) if modes else "replay"),
        source_family=source_family or (next(iter(families)) if families else "fortyguard"),
        interpolated=False,
        hours=ordered,
        n_present=n_present,
        n_expected=expected_n,
        temporal_coverage_class=coverage.value,
        longest_gap_hours=longest_gap,
        bin_present=bins,
        t_min_obs_c=t_min,
        t_max_obs_c=t_max,
        min_hours_local=min_hours,
        peak_hours_local=peak_hours,
        diurnal_range_obs_c=rng,
        extrema_wording=extrema,
        day_night_diff_c=day_night_diff,
        day_mean_c=day_mean,
        night_mean_c=night_mean,
        day_n=len(day_vals),
        night_n=len(night_vals),
        day_night_status=day_night_status,
        cooling=cooling,
    )


def ingest(timestamp: datetime, tz: str = "America/Phoenix") -> datetime:
    try:
        return require_unique_aoi_local_hour(timestamp, tz)
    except ValueError as exc:
        if "minutes" in str(exc):
            from app.services.aoi_timezone import TimezoneFailureCode

            raise AoiLocalTimeError(
                TimezoneFailureCode.NONEXISTENT_LOCAL_TIME,
                str(exc),
                timestamp=timestamp,
                timezone_name=tz,
            ) from exc
        raise


def _expected_hours(design: SamplingDesign) -> list[int]:
    if design is SamplingDesign.HOURLY_24:
        return list(range(24))
    if design is SamplingDesign.SAMPLED_3H:
        return [0, 3, 6, 9, 12, 15, 18, 21]
    if design is SamplingDesign.SAMPLED_4H:
        return [0, 4, 8, 12, 16, 20]
    if design is SamplingDesign.SAMPLED_6H:
        return [0, 6, 12, 18]
    if design is SamplingDesign.ANCHOR_DAY_NIGHT:
        return [3, 15]
    if design is SamplingDesign.ANCHOR_0300:
        return [3]
    return [0]


def _cooling(
    ordered: list[HourSlot],
    peak_hours: list[int],
    coverage: TemporalCoverageClass,
    bins: dict[str, int],
    sampling: SamplingDesign,
) -> CoolingTrajectory:
    if sampling is not SamplingDesign.HOURLY_24:
        return CoolingTrajectory(status="withheld_coverage")
    evening_gap = _longest_gap_in(ordered, EVENING_HOURS)
    eligible = (
        coverage in {TemporalCoverageClass.ADEQUATE, TemporalCoverageClass.FULL}
        and bins.get("evening", 0) >= 4
        and evening_gap <= 1
    )
    if not eligible:
        return CoolingTrajectory(status="withheld_coverage")
    if not peak_hours:
        return CoolingTrajectory(status="withheld_no_peak")
    anchor = peak_hours[0]
    if anchor >= 23:
        return CoolingTrajectory(status="withheld_insufficient_span")
    by_hour = {slot.hour_local: slot for slot in ordered}
    span: list[int] = []
    for hour in range(anchor, 24):
        slot = by_hour[hour]
        if slot.status != "observed":
            break
        span.append(hour)
    if not span:
        return CoolingTrajectory(status="withheld_no_peak")
    start, end = span[0], span[-1]
    duration = end - start
    t0 = by_hour[start].temperature_c
    t1 = by_hour[end].temperature_c
    if duration < MIN_COOLING_DURATION_H:
        status = "withheld_gap" if end < 23 and by_hour.get(end + 1) and by_hour[end + 1].status == "missing" else "withheld_insufficient_span"
        return CoolingTrajectory(status=status)
    if t0 is None or t1 is None or t1 >= t0:
        return CoolingTrajectory(status="withheld_not_cooling")
    return CoolingTrajectory(
        status="computed",
        start_hour_local=start,
        end_hour_local=end,
        delta_c=t1 - t0,
        duration_h=duration,
        rate_c_per_h=(t1 - t0) / duration,
        n_hours_in_span=len(span),
        note=NOTE_COMPUTED,
    )


def _longest_gap_in(ordered: list[HourSlot], hours: frozenset[int]) -> int:
    longest = run = 0
    for slot in ordered:
        if slot.hour_local not in hours:
            continue
        if slot.status != "observed":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


# Re-export for tests that catch AoiLocalTimeError on ingest.
__all__ = [
    "AoiLocalTimeError",
    "CoolingTrajectory",
    "DAILY_PROFILE_POLICY_ID",
    "DailyProfileComputation",
    "DuplicateHourError",
    "HourIn",
    "HourSlot",
    "IneligibleHourError",
    "ProfileBuildError",
    "SourceMixError",
    "build_profile",
    "ingest",
]
