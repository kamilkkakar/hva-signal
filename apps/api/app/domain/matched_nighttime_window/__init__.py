"""Matched summer nighttime window — FortyGuard zone-mean TCM.

Isolated package. Not re-exported from app.domain. Does not compute q_A
and does not change Signal A.
"""

from app.domain.matched_nighttime_window.analysis_geography_change_context import (
    AnalysisGeographyChangeContext,
    analysis_geography_change_context,
)
from app.domain.matched_nighttime_window.claims import (
    CONTRACT_ID,
    WINDOW_LABEL,
    ForbiddenClaimError,
    assert_claim_allowed,
)
from app.domain.matched_nighttime_window.matched_date_comparison import (
    MatchedDateComparison,
    matched_date_comparison,
)
from app.domain.matched_nighttime_window.matched_window_summary import (
    ZoneYearSummary,
    matched_window_summary,
    matched_window_summaries,
)
from app.domain.matched_nighttime_window.panel import (
    NighttimePanel,
    NighttimeTcmObservation,
    load_fortyguard_nighttime_panel,
)
from app.domain.matched_nighttime_window.present import (
    ZoneNighttimePacket,
    api_contract,
    assemble_zone_packet,
    intervention_verification_reuse,
    selected_zone_story,
    yoy_change_map_layer,
)
from app.domain.matched_nighttime_window.year_over_year_zone_change import (
    ZoneYearOverYearChange,
    year_over_year_zone_change,
)

__all__ = [
    "CONTRACT_ID",
    "WINDOW_LABEL",
    "AnalysisGeographyChangeContext",
    "ForbiddenClaimError",
    "MatchedDateComparison",
    "NighttimePanel",
    "NighttimeTcmObservation",
    "ZoneNighttimePacket",
    "ZoneYearOverYearChange",
    "ZoneYearSummary",
    "analysis_geography_change_context",
    "api_contract",
    "assemble_zone_packet",
    "assert_claim_allowed",
    "intervention_verification_reuse",
    "load_fortyguard_nighttime_panel",
    "matched_date_comparison",
    "matched_window_summaries",
    "matched_window_summary",
    "selected_zone_story",
    "year_over_year_zone_change",
    "yoy_change_map_layer",
]
