"""Zone YoY change versus the 25-area analysis-geography median.

Not an intervention effect. Not a targeting score.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from app.domain.matched_nighttime_window.claims import WINDOW_LABEL, window_period_clause
from app.domain.matched_nighttime_window.panel import NighttimePanel
from app.domain.matched_nighttime_window.year_over_year_zone_change import (
    year_over_year_zone_change,
)

AT_MEDIAN_ABS_C = 0.05


@dataclass(frozen=True)
class ZoneDelta:
    geoid: str
    delta_c: float


@dataclass(frozen=True)
class AnalysisGeographyChangeContext:
    geoid: str
    earlier_year: int
    later_year: int
    window_label: str
    n_zones: int
    n_zones_with_delta: int
    zone_delta_c: float | None
    geography_median_delta_c: float | None
    geography_min_delta_c: float | None
    geography_max_delta_c: float | None
    zone_minus_median_c: float | None
    relative_side: str
    zone_deltas: tuple[ZoneDelta, ...]
    public_sentence: str | None


def analysis_geography_change_context(
    panel: NighttimePanel,
    geoid: str,
    earlier_year: int,
    later_year: int,
) -> AnalysisGeographyChangeContext:
    key = str(geoid).zfill(11)
    deltas: list[ZoneDelta] = []
    selected: float | None = None
    for zone_id in panel.zone_ids():
        change = year_over_year_zone_change(panel, zone_id, earlier_year, later_year)
        if not change.coverage_supported or change.delta_c is None:
            continue
        deltas.append(ZoneDelta(geoid=zone_id, delta_c=change.delta_c))
        if zone_id == key:
            selected = change.delta_c

    values = [item.delta_c for item in deltas]
    geo_median = median(values) if values else None
    minus = None
    side = "unknown"
    sentence = None
    if selected is not None and geo_median is not None:
        minus = selected - geo_median
        if abs(minus) <= AT_MEDIAN_ABS_C:
            side = "near_median"
            side_text = "near"
        elif minus > 0:
            side = "above_median"
            side_text = "above"
        else:
            side = "below_median"
            side_text = "below"
        sentence = (
            f"This analysis area's {later_year}–{earlier_year} matched-window "
            f"mean change was {minus:+.2f}°C {side_text} the {len(values)}-area "
            f"analysis-geography median change of {geo_median:+.2f}°C "
            f"({window_period_clause()}). This is not an intervention effect."
        )
    return AnalysisGeographyChangeContext(
        geoid=key,
        earlier_year=earlier_year,
        later_year=later_year,
        window_label=WINDOW_LABEL,
        n_zones=len(panel.zone_ids()),
        n_zones_with_delta=len(deltas),
        zone_delta_c=selected,
        geography_median_delta_c=geo_median,
        geography_min_delta_c=min(values) if values else None,
        geography_max_delta_c=max(values) if values else None,
        zone_minus_median_c=minus,
        relative_side=side,
        zone_deltas=tuple(sorted(deltas, key=lambda item: item.geoid)),
        public_sentence=sentence,
    )
