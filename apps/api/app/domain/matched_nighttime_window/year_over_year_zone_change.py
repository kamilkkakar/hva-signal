"""Pairwise year-over-year zone TCM change. Degrees Celsius, not an index."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.matched_nighttime_window.claims import (
    TEMPERATURE_QUANTITY,
    WINDOW_LABEL,
    window_period_clause,
)
from app.domain.matched_nighttime_window.matched_window_summary import (
    ZoneYearSummary,
    matched_window_summary,
)
from app.domain.matched_nighttime_window.panel import NighttimePanel


@dataclass(frozen=True)
class ZoneYearOverYearChange:
    geoid: str
    earlier_year: int
    later_year: int
    window_label: str
    temperature_quantity: str
    earlier_mean_tcm_c: float | None
    later_mean_tcm_c: float | None
    delta_c: float | None
    coverage_supported: bool
    earlier: ZoneYearSummary
    later: ZoneYearSummary
    public_sentence: str | None


def year_over_year_zone_change(
    panel: NighttimePanel,
    geoid: str,
    earlier_year: int,
    later_year: int,
) -> ZoneYearOverYearChange:
    if later_year == earlier_year:
        raise ValueError("year-over-year requires two different years")
    earlier = matched_window_summary(panel, geoid, earlier_year)
    later = matched_window_summary(panel, geoid, later_year)
    supported = earlier.coverage_supported and later.coverage_supported
    delta = None
    sentence = None
    if (
        supported
        and earlier.mean_tcm_c is not None
        and later.mean_tcm_c is not None
    ):
        delta = later.mean_tcm_c - earlier.mean_tcm_c
        direction = "warmer" if delta > 0 else "cooler" if delta < 0 else "unchanged"
        magnitude = abs(delta)
        sentence = (
            f"Across the {window_period_clause()}, this analysis area "
            f"averaged {magnitude:.1f}°C {direction} at {later.hour_local} in "
            f"{later_year} than in {earlier_year}. Comparison baseline: the same "
            f"calendar dates and the same hour. Quantity: zone-mean TCM °C. "
            f"This is not a climate trend and not Signal A."
        )
    return ZoneYearOverYearChange(
        geoid=str(geoid).zfill(11),
        earlier_year=earlier_year,
        later_year=later_year,
        window_label=WINDOW_LABEL,
        temperature_quantity=TEMPERATURE_QUANTITY,
        earlier_mean_tcm_c=earlier.mean_tcm_c,
        later_mean_tcm_c=later.mean_tcm_c,
        delta_c=delta,
        coverage_supported=supported,
        earlier=earlier,
        later=later,
        public_sentence=sentence,
    )
