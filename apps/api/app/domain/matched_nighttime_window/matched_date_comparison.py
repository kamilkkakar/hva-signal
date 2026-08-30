"""Same-calendar-day TCM pairs. Night counts, not a persistence index."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median

from app.domain.matched_nighttime_window.claims import (
    HOUR_LOCAL,
    TEMPERATURE_QUANTITY,
    TIMEZONE,
    WINDOW_LABEL,
)
from app.domain.matched_nighttime_window.panel import NighttimePanel


@dataclass(frozen=True)
class MatchedDatePair:
    month_day: str
    earlier_tcm_c: float
    later_tcm_c: float
    delta_c: float


@dataclass(frozen=True)
class MatchedDateComparison:
    geoid: str
    earlier_year: int
    later_year: int
    window_label: str
    hour_local: str
    timezone: str
    temperature_quantity: str
    n_matched: int
    n_warmer: int
    n_cooler: int
    n_equal: int
    median_delta_c: float | None
    mean_delta_c: float | None
    pairs: tuple[MatchedDatePair, ...]
    persistence_sentence: str | None


def matched_date_comparison(
    panel: NighttimePanel,
    geoid: str,
    earlier_year: int,
    later_year: int,
) -> MatchedDateComparison:
    if later_year == earlier_year:
        raise ValueError("matched-date comparison requires two different years")
    earlier = {row.month_day: row.mean_tcm_c for row in panel.for_zone_year(geoid, earlier_year)}
    later = {row.month_day: row.mean_tcm_c for row in panel.for_zone_year(geoid, later_year)}
    keys = tuple(sorted(set(earlier) & set(later)))
    pairs = tuple(
        MatchedDatePair(
            month_day=key,
            earlier_tcm_c=earlier[key],
            later_tcm_c=later[key],
            delta_c=later[key] - earlier[key],
        )
        for key in keys
    )
    diffs = [pair.delta_c for pair in pairs]
    n_warmer = sum(1 for delta in diffs if delta > 0)
    n_cooler = sum(1 for delta in diffs if delta < 0)
    n_equal = sum(1 for delta in diffs if delta == 0)
    sentence = None
    if pairs:
        sentence = (
            f"{later_year} was warmer than {earlier_year} on {n_warmer} of "
            f"{len(pairs)} matched {HOUR_LOCAL} observations "
            f"(baseline: same calendar day, {HOUR_LOCAL} {TIMEZONE}, "
            f"{WINDOW_LABEL}). {later_year} was cooler on {n_cooler} of "
            f"{len(pairs)}. This is not a persistence index."
        )
    return MatchedDateComparison(
        geoid=str(geoid).zfill(11),
        earlier_year=earlier_year,
        later_year=later_year,
        window_label=WINDOW_LABEL,
        hour_local=HOUR_LOCAL,
        timezone=TIMEZONE,
        temperature_quantity=TEMPERATURE_QUANTITY,
        n_matched=len(pairs),
        n_warmer=n_warmer,
        n_cooler=n_cooler,
        n_equal=n_equal,
        median_delta_c=median(diffs) if diffs else None,
        mean_delta_c=mean(diffs) if diffs else None,
        pairs=pairs,
        persistence_sentence=sentence,
    )
