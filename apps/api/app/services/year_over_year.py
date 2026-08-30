"""T-G year-over-year: fail-closed frames; paired S2 03:00 Δ°C candidate.

Does not change Signal A. Does not call temporal_anomaly.
Labels are S2 / 3 a.m., never summer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

from app.domain.phoenix_v1 import (
    EXPECTED_ZONE_COUNT,
    SEASONAL_END_MONTH_DAY,
    SEASONAL_START_MONTH_DAY,
    THERMAL_AGGREGATION_VERSION,
    ZONE_GEOMETRY_VERSION,
)
from app.domain.temporal import Comparability, TemporalCoverageClass
from app.services.temporal_coverage import classify_year_pair

PHOENIX_GEOMETRY_SHA256 = "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0"


@dataclass(frozen=True)
class YoYFrame:
    window_id: str
    sampling_design: str
    zone_geometry_version: str
    geometry_sha256: str | None
    expected_zone_count: int
    aggregation_spec_version: str
    source_mode: str
    temperature_quantity: str
    timezone: str
    source_family: str = "fortyguard"


@dataclass
class FrameChecks:
    zone_geometry_version: bool
    expected_zone_count: bool
    aggregation_spec_version: bool
    sampling_design: bool
    window_family: bool
    timezone: bool
    source_mode: bool
    temperature_quantity: bool

    def all_pass(self) -> bool:
        return all(
            (
                self.zone_geometry_version,
                self.expected_zone_count,
                self.aggregation_spec_version,
                self.sampling_design,
                self.window_family,
                self.timezone,
                self.source_mode,
                self.temperature_quantity,
            )
        )


@dataclass
class YearSideSlots:
    year: int
    slots: dict[tuple[str, str], float]  # (zone_id, mm-dd) → °C
    coverage_class: TemporalCoverageClass
    coverage_ratio: float


@dataclass
class YearComparisonComputation:
    window_id: str
    left_year: int
    right_year: int
    comparability: str
    fail_closed_reasons: list[str]
    frame_checks: FrameChecks
    pair_coverage_class: str
    mean_difference_c: float | None
    nighttime_difference_c: float | None
    n_paired: int
    n_expected_paired: int
    paired_ratio: float
    public_sentence: str | None
    label: str


def _window_family(window_id: str) -> str:
    if window_id.startswith("S2"):
        return "S2"
    if window_id.startswith("SEASON:JJA"):
        return "JJA"
    if window_id.startswith("SEASON:DJF"):
        return "DJF"
    if window_id.startswith("MONTH:"):
        return "MONTH"
    return window_id.split(":")[0]


def compare_years(
    *,
    left: YoYFrame,
    right: YoYFrame,
    left_slots: YearSideSlots,
    right_slots: YearSideSlots,
    reconciliation_id: str | None = None,
) -> YearComparisonComputation:
    if left.window_id != right.window_id and _window_family(left.window_id) != _window_family(right.window_id):
        window_ok = False
    else:
        window_ok = _window_family(left.window_id) == _window_family(right.window_id)
    if "S2" in (left.window_id, right.window_id) and any(
        "JJA" in item or "summer" in item.lower() for item in (left.window_id, right.window_id)
    ):
        window_ok = False

    checks = FrameChecks(
        zone_geometry_version=left.zone_geometry_version == right.zone_geometry_version
        or reconciliation_id is not None,
        expected_zone_count=left.expected_zone_count == right.expected_zone_count,
        aggregation_spec_version=left.aggregation_spec_version == right.aggregation_spec_version,
        sampling_design=left.sampling_design == right.sampling_design,
        window_family=window_ok,
        timezone=left.timezone == right.timezone,
        source_mode=left.source_family == right.source_family
        and left.temperature_quantity == right.temperature_quantity,
        temperature_quantity=left.temperature_quantity == right.temperature_quantity,
    )
    if left.source_family != right.source_family:
        checks.source_mode = False
        checks.temperature_quantity = False

    reasons: list[str] = []
    if left.zone_geometry_version != right.zone_geometry_version and reconciliation_id is None:
        reasons.append("G-GEO-1")
    if (
        left.geometry_sha256
        and right.geometry_sha256
        and left.geometry_sha256 != right.geometry_sha256
        and reconciliation_id is None
    ):
        reasons.append("G-GEO-2")
        checks.zone_geometry_version = False
    if left.expected_zone_count != right.expected_zone_count:
        reasons.append("G-GEO-3")
    if left.aggregation_spec_version != right.aggregation_spec_version:
        reasons.append("G-AGG-1")
    if not window_ok:
        reasons.append("G-WIN-1")
    if left.sampling_design != right.sampling_design:
        reasons.append("G-DES-1")
    if left.source_family != right.source_family:
        reasons.append("G-SRC-1")
    if left.timezone != right.timezone:
        reasons.append("G-HR-2")

    later, earlier = (
        (right_slots, left_slots)
        if right_slots.year >= left_slots.year
        else (left_slots, right_slots)
    )
    if later.year == earlier.year:
        reasons.append("G-WIN-1")
        checks.window_family = False

    calendar_keys = set(earlier.slots) | set(later.slots)
    expected_paired = [key for key in calendar_keys if key[1] != "02-29"]
    # Prefer intersection of calendars that exist on both sides' expected sets.
    both_calendar = set(earlier.slots) & set(later.slots)
    both_calendar = {key for key in both_calendar if key[1] != "02-29"}
    n_expected = len(set(expected_paired)) if expected_paired else len(both_calendar)
    paired_deltas = [
        later.slots[key] - earlier.slots[key]
        for key in both_calendar
        if key in earlier.slots and key in later.slots
    ]
    n_paired = len(paired_deltas)
    paired_ratio = (n_paired / n_expected) if n_expected else 0.0
    coverage_delta = abs(left_slots.coverage_ratio - right_slots.coverage_ratio)
    pair_class = classify_year_pair(
        left=left_slots.coverage_class,
        right=right_slots.coverage_class,
        paired_ratio=paired_ratio,
        coverage_delta=coverage_delta,
    )

    if not checks.all_pass():
        return YearComparisonComputation(
            window_id=left.window_id,
            left_year=left_slots.year,
            right_year=right_slots.year,
            comparability=Comparability.INCOMPARABLE.value,
            fail_closed_reasons=reasons or ["FRAME"],
            frame_checks=checks,
            pair_coverage_class=pair_class.value,
            mean_difference_c=None,
            nighttime_difference_c=None,
            n_paired=n_paired,
            n_expected_paired=n_expected,
            paired_ratio=paired_ratio,
            public_sentence=None,
            label=_honest_label(left.window_id, left.sampling_design),
        )

    headline_ok = pair_class in {TemporalCoverageClass.FULL, TemporalCoverageClass.ADEQUATE}
    delta = (sum(paired_deltas) / n_paired) if paired_deltas and headline_ok else None
    sentence = None
    if delta is not None:
        sentence = (
            f"On 30 June–30 July, at 03:00 America/Phoenix, the paired-night mean was "
            f"{delta:.2f} °C higher in {later.year} than in {earlier.year} "
            f"(n paired {n_paired} / n expected {n_expected}). Not summer. Not JJA."
        )
    return YearComparisonComputation(
        window_id=left.window_id,
        left_year=left_slots.year,
        right_year=right_slots.year,
        comparability=Comparability.COMPARABLE.value,
        fail_closed_reasons=[],
        frame_checks=checks,
        pair_coverage_class=pair_class.value,
        mean_difference_c=delta,
        nighttime_difference_c=delta if left.sampling_design == "ANCHOR_0300" else None,
        n_paired=n_paired,
        n_expected_paired=n_expected,
        paired_ratio=paired_ratio,
        public_sentence=sentence,
        label=_honest_label(left.window_id, left.sampling_design),
    )


def _honest_label(window_id: str, sampling_design: str) -> str:
    if _window_family(window_id) == "S2" and sampling_design == "ANCHOR_0300":
        return "S2 30 June–30 July 3 a.m. America/Phoenix"
    return f"{window_id} {sampling_design}"


def _in_s2(local_date: date) -> bool:
    start = date(local_date.year, *SEASONAL_START_MONTH_DAY)
    end = date(local_date.year, *SEASONAL_END_MONTH_DAY)
    return start <= local_date <= end


def load_s2_anchor_slots_from_jsonl(
    path: Path,
    *,
    year: int,
) -> YearSideSlots:
    """Read frozen observations.jsonl. Does not compute q_A."""
    slots: dict[tuple[str, str], float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if int(row["year"]) != year:
            continue
        if str(row.get("local_time")) != "03:00":
            continue
        local_date = date.fromisoformat(str(row["date"]))
        if not _in_s2(local_date):
            continue
        value = row.get("mean_tcm_c")
        if value is None:
            continue
        key = (str(row["geoid"]).zfill(11), local_date.strftime("%m-%d"))
        slots[key] = float(value)
    n_expected = 31 * EXPECTED_ZONE_COUNT
    ratio = len(slots) / n_expected if n_expected else 0.0
    coverage = (
        TemporalCoverageClass.FULL
        if len(slots) == n_expected
        else TemporalCoverageClass.ADEQUATE
        if ratio >= 0.80
        else TemporalCoverageClass.PARTIAL
        if slots
        else TemporalCoverageClass.INSUFFICIENT
    )
    return YearSideSlots(year=year, slots=slots, coverage_class=coverage, coverage_ratio=ratio)


def compare_s2_anchor_0300_from_reference_panel(
    path: Path,
    *,
    year_earlier: int,
    year_later: int,
    zone_geometry_version: str = ZONE_GEOMETRY_VERSION,
    geometry_sha256: str = PHOENIX_GEOMETRY_SHA256,
) -> YearComparisonComputation:
    if year_later == 2025 or year_earlier == 2025:
        checks = FrameChecks(
            zone_geometry_version=True,
            expected_zone_count=True,
            aggregation_spec_version=True,
            sampling_design=True,
            window_family=False,
            timezone=True,
            source_mode=True,
            temperature_quantity=True,
        )
        return YearComparisonComputation(
            window_id="S2",
            left_year=year_earlier,
            right_year=year_later,
            comparability=Comparability.INCOMPARABLE.value,
            fail_closed_reasons=["YY-2025", "G-WIN-3"],
            frame_checks=checks,
            pair_coverage_class=TemporalCoverageClass.INSUFFICIENT.value,
            mean_difference_c=None,
            nighttime_difference_c=None,
            n_paired=0,
            n_expected_paired=0,
            paired_ratio=0.0,
            public_sentence=None,
            label="S2 30 June–30 July 3 a.m. America/Phoenix",
        )
    left = load_s2_anchor_slots_from_jsonl(path, year=year_earlier)
    right = load_s2_anchor_slots_from_jsonl(path, year=year_later)
    frame = YoYFrame(
        window_id=f"S2:{year_earlier}",
        sampling_design="ANCHOR_0300",
        zone_geometry_version=zone_geometry_version,
        geometry_sha256=geometry_sha256,
        expected_zone_count=EXPECTED_ZONE_COUNT,
        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        source_mode="replay",
        temperature_quantity="tcm_zone_mean",
        timezone="America/Phoenix",
    )
    right_frame = YoYFrame(
        window_id=f"S2:{year_later}",
        sampling_design="ANCHOR_0300",
        zone_geometry_version=zone_geometry_version,
        geometry_sha256=geometry_sha256,
        expected_zone_count=EXPECTED_ZONE_COUNT,
        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        source_mode="replay",
        temperature_quantity="tcm_zone_mean",
        timezone="America/Phoenix",
    )
    return compare_years(left=frame, right=right_frame, left_slots=left, right_slots=right)
