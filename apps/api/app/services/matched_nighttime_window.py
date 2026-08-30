"""Unpublished assembler for the matched-window nighttime TCM package.

Replay panel only. Does not call FortyGuard. Does not compute q_A.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.matched_nighttime_window import (
    ZoneNighttimePacket,
    assemble_zone_packet,
    load_fortyguard_nighttime_panel,
)
from app.domain.matched_nighttime_window.analysis_geography_change_context import (
    analysis_geography_change_context,
)
from app.domain.matched_nighttime_window.claims import (
    HOUR_LOCAL,
    REFERENCE_YEARS,
    WINDOW_LABEL,
)
from app.domain.matched_nighttime_window.matched_date_comparison import (
    matched_date_comparison,
)
from app.domain.matched_nighttime_window.matched_window_summary import (
    matched_window_summary,
)
from app.domain.matched_nighttime_window.panel import NighttimePanel
from app.domain.matched_nighttime_window.year_over_year_zone_change import (
    year_over_year_zone_change,
)

AREA_ID = "phoenix-demo"
WINDOW_START = "06-30"
WINDOW_END = "07-30"
WINDOW_DATES_PUBLIC = "30 Jun-30 Jul"
METHOD = "matched same-calendar dates / same local hour"


def load_canonical_nighttime_panel(path: Path | None = None) -> NighttimePanel:
    return load_fortyguard_nighttime_panel(path)


def assemble_selected_zone(
    geoid: str, *, path: Path | None = None
) -> ZoneNighttimePacket:
    return assemble_zone_packet(load_fortyguard_nighttime_panel(path), geoid)


@lru_cache(maxsize=1)
def cached_nighttime_panel(path: str | None = None) -> NighttimePanel:
    """Compact in-process cache. GET never acquires. Does not dump the panel."""
    return load_fortyguard_nighttime_panel(Path(path) if path else None)


def assemble_matched_nighttime_window_view(
    geoid: str,
    *,
    area_id: str = AREA_ID,
    path: Path | None = None,
) -> dict[str, Any]:
    """Compact cache/read-only view. Not Signal A. Not 2,325 rows."""
    if area_id != AREA_ID:
        raise ValueError("matched nighttime window is phoenix-demo only")
    panel = cached_nighttime_panel(str(path) if path else None)
    key = str(geoid).zfill(11)
    if key not in panel.zone_ids():
        raise KeyError(f"unknown analysis area {key}")
    means = {
        str(year): matched_window_summary(panel, key, year).mean_tcm_c
        for year in REFERENCE_YEARS
    }
    yoy = year_over_year_zone_change(panel, key, 2022, 2024)
    paired = matched_date_comparison(panel, key, 2022, 2024)
    geo = analysis_geography_change_context(panel, key, 2022, 2024)
    return {
        "unpublished": True,
        "not_signal_a": True,
        "window_label": WINDOW_LABEL,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "window_dates": WINDOW_DATES_PUBLIC,
        "local_time": HOUR_LOCAL,
        "years": list(REFERENCE_YEARS),
        "selected_area": {
            "area_id": area_id,
            "geoid": key,
            "mean_by_year": means,
            "change_2024_vs_2022": yoy.delta_c,
            "matched_nights": paired.n_matched,
            "matched_nights_warmer": paired.n_warmer,
            "matched_nights_cooler": paired.n_cooler,
        },
        "analysis_geography": {
            "median_change_2024_vs_2022": geo.geography_median_delta_c,
        },
        "source": "FortyGuard",
        "method": METHOD,
    }
