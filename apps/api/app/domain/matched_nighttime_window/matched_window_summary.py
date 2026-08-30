"""Per-zone matched-window TCM summary. Uses mean_tcm_c, not q_A."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median, stdev

from app.domain.matched_nighttime_window.claims import (
    HOUR_LOCAL,
    TEMPERATURE_QUANTITY,
    TIMEZONE,
    WINDOW_LABEL,
)
from app.domain.matched_nighttime_window.panel import (
    NighttimePanel,
    expected_month_days,
)


@dataclass(frozen=True)
class ZoneYearSummary:
    geoid: str
    year: int
    window_label: str
    hour_local: str
    timezone: str
    temperature_quantity: str
    n_valid_nights: int
    n_expected_nights: int
    coverage_ratio: float
    coverage_supported: bool
    mean_tcm_c: float | None
    median_tcm_c: float | None
    min_tcm_c: float | None
    max_tcm_c: float | None
    stdev_tcm_c: float | None
    mean_contributing_tiles: float | None
    min_contributing_tiles: int | None
    nightly_tcm_c: tuple[float, ...]


def matched_window_summary(
    panel: NighttimePanel,
    geoid: str,
    year: int,
    *,
    min_coverage_ratio: float = 0.80,
) -> ZoneYearSummary:
    rows = panel.for_zone_year(geoid, year)
    expected = expected_month_days(year)
    values = tuple(row.mean_tcm_c for row in rows)
    tiles = [row.contributing_tiles for row in rows if row.contributing_tiles is not None]
    n_valid = len(values)
    n_expected = len(expected)
    ratio = (n_valid / n_expected) if n_expected else 0.0
    supported = n_valid >= 1 and ratio >= min_coverage_ratio
    return ZoneYearSummary(
        geoid=str(geoid).zfill(11),
        year=year,
        window_label=WINDOW_LABEL,
        hour_local=HOUR_LOCAL,
        timezone=TIMEZONE,
        temperature_quantity=TEMPERATURE_QUANTITY,
        n_valid_nights=n_valid,
        n_expected_nights=n_expected,
        coverage_ratio=ratio,
        coverage_supported=supported,
        mean_tcm_c=mean(values) if values else None,
        median_tcm_c=median(values) if values else None,
        min_tcm_c=min(values) if values else None,
        max_tcm_c=max(values) if values else None,
        stdev_tcm_c=stdev(values) if n_valid >= 2 else None,
        mean_contributing_tiles=mean(tiles) if tiles else None,
        min_contributing_tiles=min(tiles) if tiles else None,
        nightly_tcm_c=values,
    )


def matched_window_summaries(
    panel: NighttimePanel,
    *,
    years: tuple[int, ...] | None = None,
) -> tuple[ZoneYearSummary, ...]:
    selected = years if years is not None else panel.years
    return tuple(
        matched_window_summary(panel, geoid, year)
        for geoid in panel.zone_ids()
        for year in selected
    )
