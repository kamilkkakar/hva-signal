"""T-F season policy + withheld seasonal summaries.

JJA/DJF are the product calendar. S2 is Decision 1B only — never summer.
S2-only evidence → NOT_PREPARED for JJA/DJF. Missing ≠ 0.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal

from app.domain.temporal import SamplingDesign, TemporalCoverageClass
from app.services.temporal_coverage import MonthCoverageInput, classify_monthly, classify_seasonal

SEASON_POLICY_ID = "PHX_TEMPORAL_SEASON_POLICY_V1"
Availability = Literal["READY", "NOT_PREPARED", "WITHHELD"]


@dataclass(frozen=True)
class SeasonWindow:
    window_id: str
    kind: str
    year_label: int
    start: date
    end: date
    expected_days: int
    child_months: tuple[tuple[int, int], ...]  # (year, month)


def parse_window_id(window_id: str) -> SeasonWindow:
    if window_id.startswith("SEASON:JJA:"):
        year = int(window_id.rsplit(":", 1)[1])
        start = date(year, 6, 1)
        end = date(year, 8, 31)
        return SeasonWindow(
            window_id=window_id,
            kind="JJA",
            year_label=year,
            start=start,
            end=end,
            expected_days=92,
            child_months=((year, 6), (year, 7), (year, 8)),
        )
    if window_id.startswith("SEASON:DJF:"):
        end_year = int(window_id.rsplit(":", 1)[1])
        start = date(end_year - 1, 12, 1)
        last = monthrange(end_year, 2)[1]
        end = date(end_year, 2, last)
        days = (end - start).days + 1
        return SeasonWindow(
            window_id=window_id,
            kind="DJF",
            year_label=end_year,
            start=start,
            end=end,
            expected_days=days,
            child_months=((end_year - 1, 12), (end_year, 1), (end_year, 2)),
        )
    if window_id.startswith("S2:"):
        year = int(window_id.rsplit(":", 1)[1])
        start = date(year, 6, 30)
        end = date(year, 7, 30)
        return SeasonWindow(
            window_id=window_id,
            kind="S2",
            year_label=year,
            start=start,
            end=end,
            expected_days=31,
            child_months=((year, 6), (year, 7)),
        )
    if window_id.startswith("MONTH:"):
        yyyy_mm = window_id.split(":", 1)[1]
        year, month = (int(part) for part in yyyy_mm.split("-"))
        last = monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last)
        return SeasonWindow(
            window_id=window_id,
            kind="MONTH",
            year_label=year,
            start=start,
            end=end,
            expected_days=last,
            child_months=((year, month),),
        )
    raise ValueError(f"unknown window_id {window_id!r}")


def jja_minus_djf_label(year: int) -> str:
    return f"SEASON:JJA:{year} − SEASON:DJF:{year}"


def is_s2_alias_of_summer(label: str) -> bool:
    lowered = label.lower()
    return "s2" in lowered and any(word in lowered for word in ("jja", "summer", "july"))


@dataclass
class SlotValue:
    local_date: date
    temperature_c: float | None
    local_hour: int = 3


@dataclass
class SeasonalComputation:
    window_id: str
    kind: str
    availability: Availability
    withhold_reason: str | None
    sampling_design: str
    mean_temperature_c: float | None
    n_present: int
    n_expected: int
    coverage_class: str
    public_label: str
    months_missing: list[str]


def held_evidence_kind(slots: Iterable[SlotValue], *, declared_hour: int = 3) -> str:
    days = {slot.local_date for slot in slots if slot.temperature_c is not None}
    if not days:
        return "EMPTY"
    hours = {slot.local_hour for slot in slots}
    june_july_anchor = all(slot.local_hour == declared_hour for slot in slots) and all(
        (d.month == 6 and d.day >= 30) or (d.month == 7 and d.day <= 30) for d in days
    )
    has_august = any(d.month == 8 for d in days)
    has_early_june = any(d.month == 6 and d.day < 30 for d in days)
    has_djf = any(d.month in {12, 1, 2} for d in days)
    if june_july_anchor and not has_august and not has_early_june and not has_djf and hours <= {declared_hour}:
        return "S2_ANCHOR_0300"
    return "OTHER"


def assemble_seasonal_summary(
    *,
    window_id: str,
    slots: list[SlotValue],
    sampling_design: str = "ANCHOR_0300",
    allow_s2_as_summer: bool = False,
) -> SeasonalComputation:
    window = parse_window_id(window_id)
    if allow_s2_as_summer or is_s2_alias_of_summer(window_id):
        return SeasonalComputation(
            window_id=window_id,
            kind=window.kind,
            availability="WITHHELD",
            withhold_reason="SE-ALIAS",
            sampling_design=sampling_design,
            mean_temperature_c=None,
            n_present=0,
            n_expected=window.expected_days,
            coverage_class=TemporalCoverageClass.INSUFFICIENT.value,
            public_label=_public_label(window),
            months_missing=[],
        )
    evidence = held_evidence_kind(slots)
    if window.kind in {"JJA", "DJF"} and evidence == "S2_ANCHOR_0300":
        return SeasonalComputation(
            window_id=window_id,
            kind=window.kind,
            availability="NOT_PREPARED",
            withhold_reason="S2_ONLY_NOT_SEASON",
            sampling_design=sampling_design,
            mean_temperature_c=None,
            n_present=_present_in_window(slots, window),
            n_expected=window.expected_days,
            coverage_class=TemporalCoverageClass.INSUFFICIENT.value,
            public_label=_public_label(window),
            months_missing=_missing_months(slots, window),
        )
    if window.kind == "DJF" and not any(
        slot.local_date.month in {12, 1, 2} and slot.temperature_c is not None for slot in slots
    ):
        return SeasonalComputation(
            window_id=window_id,
            kind="DJF",
            availability="NOT_PREPARED",
            withhold_reason="DJF_EMPTY",
            sampling_design=sampling_design,
            mean_temperature_c=None,
            n_present=0,
            n_expected=window.expected_days,
            coverage_class=TemporalCoverageClass.INSUFFICIENT.value,
            public_label=_public_label(window),
            months_missing=["12", "01", "02"],
        )

    present_vals = [
        slot.temperature_c
        for slot in slots
        if slot.temperature_c is not None and window.start <= slot.local_date <= window.end
    ]
    n_present = len(present_vals)
    mean = (sum(present_vals) / n_present) if present_vals else None
    month_inputs = []
    for year, month in window.child_months:
        last = monthrange(year, month)[1]
        month_slots = [
            slot
            for slot in slots
            if slot.local_date.year == year and slot.local_date.month == month
        ]
        contributing = sum(1 for slot in month_slots if slot.temperature_c is not None)
        expected_slots = last if sampling_design == "ANCHOR_0300" else last * 24
        month_class = classify_monthly(
            n_contributing_days=contributing,
            n_calendar_days=last,
            n_present_slots=contributing,
            n_expected_slots=expected_slots,
            longest_gap_days=last - contributing,
        )
        month_inputs.append(
            MonthCoverageInput(
                coverage_class=month_class,
                n_contributing_days=contributing,
                n_calendar_days=last,
            )
        )
    coverage = classify_seasonal(
        month_inputs,
        n_contributing_days=n_present,
        n_season_days=window.expected_days,
        longest_gap_days=0,
    )
    headline = mean if coverage in {TemporalCoverageClass.FULL, TemporalCoverageClass.ADEQUATE} else None
    availability: Availability = "READY" if headline is not None else "WITHHELD"
    return SeasonalComputation(
        window_id=window_id,
        kind=window.kind,
        availability=availability,
        withhold_reason=None if headline is not None else "COVERAGE",
        sampling_design=sampling_design,
        mean_temperature_c=headline,
        n_present=n_present,
        n_expected=window.expected_days,
        coverage_class=coverage.value,
        public_label=_public_label(window),
        months_missing=_missing_months(slots, window),
    )


def seasonal_mean_among_observed(slots: Iterable[SlotValue]) -> float | None:
    vals = [slot.temperature_c for slot in slots if slot.temperature_c is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _present_in_window(slots: Iterable[SlotValue], window: SeasonWindow) -> int:
    return sum(
        1
        for slot in slots
        if slot.temperature_c is not None and window.start <= slot.local_date <= window.end
    )


def _missing_months(slots: Iterable[SlotValue], window: SeasonWindow) -> list[str]:
    present = {
        (slot.local_date.year, slot.local_date.month)
        for slot in slots
        if slot.temperature_c is not None
    }
    return [f"{year:04d}-{month:02d}" for year, month in window.child_months if (year, month) not in present]


def _public_label(window: SeasonWindow) -> str:
    if window.kind == "JJA":
        return f"June–August {window.year_label}"
    if window.kind == "DJF":
        return f"December–February ending {window.year_label}"
    if window.kind == "S2":
        return f"30 June–30 July {window.year_label} at 3 a.m."
    return window.window_id
