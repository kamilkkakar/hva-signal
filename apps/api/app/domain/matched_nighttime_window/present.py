"""Story, chart, map, intervention, and unpublished API contracts.

Answers: what changed, relative to what, over what exact period, by how
much, how the rest of the analysis geography changed, and what direction
that suggests. No health alarm. Not Signal A.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.domain.matched_nighttime_window.analysis_geography_change_context import (
    AnalysisGeographyChangeContext,
    analysis_geography_change_context,
)
from app.domain.matched_nighttime_window.claims import (
    CONTRACT_ID,
    HOUR_LOCAL,
    REFERENCE_YEARS,
    SOURCE_FAMILY,
    SOURCE_MODE,
    TEMPERATURE_QUANTITY,
    TIMEZONE,
    WINDOW_DATES,
    WINDOW_LABEL,
    assert_claim_allowed,
    window_period_clause,
)
from app.domain.matched_nighttime_window.matched_date_comparison import (
    MatchedDateComparison,
    matched_date_comparison,
)
from app.domain.matched_nighttime_window.matched_window_summary import (
    ZoneYearSummary,
    matched_window_summary,
)
from app.domain.matched_nighttime_window.panel import NighttimePanel
from app.domain.matched_nighttime_window.year_over_year_zone_change import (
    ZoneYearOverYearChange,
    year_over_year_zone_change,
)


@dataclass(frozen=True)
class ChartContract:
    chart_id: str
    title: str
    window_label: str
    quantity: str
    units: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class MapLayerContract:
    layer_id: str
    title: str
    window_label: str
    quantity: str
    units: str
    comparison: str
    geography_median_delta_c: float | None
    features: tuple[dict[str, Any], ...]
    legend_note: str


@dataclass(frozen=True)
class InterventionReuseAssessment:
    usable_as_future_verification_candidate: bool
    requires_location_intersection_with_hva_zone: Literal[True]
    requires_mechanism_plausibly_affects_0300: Literal[True]
    requires_timing_inside_matched_window: Literal[True]
    daytime_shade_not_evaluable_from_0300_alone: Literal[True]
    not_an_intervention_effect: Literal[True]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class SelectedZoneStory:
    geoid: str
    window_label: str
    what_changed: str
    relative_to_what: str
    exact_period: str
    by_how_much: str
    geography_context: str
    direction: str
    persistence: str
    sentences: tuple[str, ...]


@dataclass(frozen=True)
class ZoneNighttimePacket:
    contract_id: str
    not_signal_a: Literal[True]
    geoid: str
    year_summaries: tuple[ZoneYearSummary, ...]
    year_over_year: tuple[ZoneYearOverYearChange, ...]
    matched_dates: tuple[MatchedDateComparison, ...]
    geography_context: tuple[AnalysisGeographyChangeContext, ...]
    descriptive_three_year_change_c_per_year: float | None
    story: SelectedZoneStory
    charts: tuple[ChartContract, ...]
    map_layers: tuple[MapLayerContract, ...]
    intervention: InterventionReuseAssessment


def _round_c(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.{digits}f}°C"


def descriptive_three_year_change_c_per_year(
    panel: NighttimePanel, geoid: str
) -> float | None:
    """(2024 − 2022) / 2. Descriptive three-year change, not a climate trend."""
    first = matched_window_summary(panel, geoid, 2022)
    last = matched_window_summary(panel, geoid, 2024)
    if (
        not first.coverage_supported
        or not last.coverage_supported
        or first.mean_tcm_c is None
        or last.mean_tcm_c is None
    ):
        return None
    return (last.mean_tcm_c - first.mean_tcm_c) / 2.0


def selected_zone_story(
    panel: NighttimePanel,
    geoid: str,
    *,
    earlier_year: int = 2022,
    later_year: int = 2024,
) -> SelectedZoneStory:
    yoy = year_over_year_zone_change(panel, geoid, earlier_year, later_year)
    paired = matched_date_comparison(panel, geoid, earlier_year, later_year)
    context = analysis_geography_change_context(panel, geoid, earlier_year, later_year)
    summaries = {
        year: matched_window_summary(panel, geoid, year) for year in REFERENCE_YEARS
    }
    period = window_period_clause()
    what = (
        f"Nighttime zone-mean TCM at {HOUR_LOCAL} changed across the three "
        f"matched windows for analysis area {str(geoid).zfill(11)}."
    )
    relative = (
        f"Relative to the same calendar dates at {HOUR_LOCAL} {TIMEZONE}, "
        f"using FortyGuard zone-mean TCM °C (not q_A)."
    )
    exact = (
        f"Exact period: {period}; years {REFERENCE_YEARS[0]}, "
        f"{REFERENCE_YEARS[1]}, and {REFERENCE_YEARS[2]}."
    )
    by_how_much = (
        f"{later_year} matched-window mean {_round_c(yoy.later_mean_tcm_c)} "
        f"versus {earlier_year} {_round_c(yoy.earlier_mean_tcm_c)} "
        f"(Δ {_round_c(yoy.delta_c)}). "
        f"Year means: 2022 {_round_c(summaries[2022].mean_tcm_c)}, "
        f"2023 {_round_c(summaries[2023].mean_tcm_c)}, "
        f"2024 {_round_c(summaries[2024].mean_tcm_c)}."
    )
    geo = context.public_sentence or (
        "Analysis-geography change context is unavailable for this pair."
    )
    if yoy.delta_c is None:
        direction = "Direction is withheld because coverage does not support a pairwise difference."
    else:
        mean_word = "warmer" if yoy.delta_c > 0 else "cooler" if yoy.delta_c < 0 else "unchanged"
        night_agrees = (
            (yoy.delta_c > 0 and paired.n_warmer > paired.n_cooler)
            or (yoy.delta_c < 0 and paired.n_cooler > paired.n_warmer)
            or yoy.delta_c == 0
        )
        direction = (
            f"Direction: the matched-window mean was {mean_word} in "
            f"{later_year} than in {earlier_year}."
        )
        if not night_agrees:
            direction += (
                f" Mean and night-count differ: {later_year} was warmer on "
                f"{paired.n_warmer} of {paired.n_matched} matched nights and "
                f"cooler on {paired.n_cooler}."
            )
        direction += " This is not a climate trend."
    persistence = paired.persistence_sentence or "Matched-date persistence is unavailable."
    sentences = tuple(
        assert_claim_allowed(text)
        for text in (what, relative, exact, by_how_much, geo, direction, persistence)
        if yoy.public_sentence is None or text != yoy.public_sentence
    )
    if yoy.public_sentence:
        sentences = (assert_claim_allowed(yoy.public_sentence),) + sentences
    return SelectedZoneStory(
        geoid=str(geoid).zfill(11),
        window_label=WINDOW_LABEL,
        what_changed=assert_claim_allowed(what),
        relative_to_what=assert_claim_allowed(relative),
        exact_period=assert_claim_allowed(exact),
        by_how_much=assert_claim_allowed(by_how_much),
        geography_context=assert_claim_allowed(geo),
        direction=assert_claim_allowed(direction),
        persistence=assert_claim_allowed(persistence),
        sentences=sentences,
    )


def three_year_nighttime_line(panel: NighttimePanel, geoid: str) -> ChartContract:
    points = []
    for year in REFERENCE_YEARS:
        summary = matched_window_summary(panel, geoid, year)
        points.append(
            {
                "year": year,
                "mean_tcm_c": summary.mean_tcm_c,
                "n_valid_nights": summary.n_valid_nights,
                "coverage_supported": summary.coverage_supported,
            }
        )
    return ChartContract(
        chart_id="three_year_nighttime_line",
        title=f"Three-year nighttime zone-mean TCM ({WINDOW_LABEL})",
        window_label=WINDOW_LABEL,
        quantity=TEMPERATURE_QUANTITY,
        units="°C",
        payload={"geoid": str(geoid).zfill(11), "points": points},
    )


def matched_date_distributions(panel: NighttimePanel, geoid: str) -> ChartContract:
    by_year = {
        str(year): list(matched_window_summary(panel, geoid, year).nightly_tcm_c)
        for year in REFERENCE_YEARS
    }
    return ChartContract(
        chart_id="matched_date_distributions",
        title=f"Matched-date 03:00 TCM distributions ({WINDOW_LABEL})",
        window_label=WINDOW_LABEL,
        quantity=TEMPERATURE_QUANTITY,
        units="°C",
        payload={"geoid": str(geoid).zfill(11), "by_year": by_year},
    )


def selected_zone_matched_date_strip(panel: NighttimePanel, geoid: str) -> ChartContract:
    by_year = {
        year: {row.month_day: row.mean_tcm_c for row in panel.for_zone_year(geoid, year)}
        for year in REFERENCE_YEARS
    }
    month_days = sorted({key for mapping in by_year.values() for key in mapping})
    strip = [
        {
            "month_day": day,
            "tcm_c_2022": by_year[2022].get(day),
            "tcm_c_2023": by_year[2023].get(day),
            "tcm_c_2024": by_year[2024].get(day),
        }
        for day in month_days
    ]
    return ChartContract(
        chart_id="selected_zone_matched_date_strip",
        title=f"Selected-zone matched-date 03:00 TCM strip ({WINDOW_LABEL})",
        window_label=WINDOW_LABEL,
        quantity=TEMPERATURE_QUANTITY,
        units="°C",
        payload={"geoid": str(geoid).zfill(11), "nights": strip},
    )


def analysis_geography_change_distribution(
    panel: NighttimePanel,
    *,
    earlier_year: int = 2022,
    later_year: int = 2024,
) -> ChartContract:
    context = analysis_geography_change_context(
        panel, panel.zone_ids()[0], earlier_year, later_year
    )
    return ChartContract(
        chart_id="analysis_geography_change_distribution",
        title=f"25-area YoY mean TCM change ({WINDOW_LABEL})",
        window_label=WINDOW_LABEL,
        quantity=TEMPERATURE_QUANTITY,
        units="°C",
        payload={
            "earlier_year": earlier_year,
            "later_year": later_year,
            "median_delta_c": context.geography_median_delta_c,
            "deltas": [asdict(item) for item in context.zone_deltas],
        },
    )


def yoy_change_map_layer(
    panel: NighttimePanel,
    *,
    earlier_year: int = 2022,
    later_year: int = 2024,
) -> MapLayerContract:
    context = analysis_geography_change_context(
        panel, panel.zone_ids()[0], earlier_year, later_year
    )
    features = tuple(
        {
            "geoid": item.geoid,
            "delta_c": item.delta_c,
            "quantity": TEMPERATURE_QUANTITY,
        }
        for item in context.zone_deltas
    )
    note = (
        f"Values are {later_year} minus {earlier_year} matched-window mean "
        f"TCM °C. Geography median {context.geography_median_delta_c}. "
        f"{WINDOW_LABEL}. Not an intervention effect."
    )
    return MapLayerContract(
        layer_id="yoy_change_2024_vs_2022" if (earlier_year, later_year) == (2022, 2024) else f"yoy_change_{later_year}_vs_{earlier_year}",
        title=f"YoY change map {later_year} vs {earlier_year} °C",
        window_label=WINDOW_LABEL,
        quantity=TEMPERATURE_QUANTITY,
        units="°C",
        comparison=f"{later_year} minus {earlier_year}",
        geography_median_delta_c=context.geography_median_delta_c,
        features=features,
        legend_note=assert_claim_allowed(note),
    )


def intervention_verification_reuse() -> InterventionReuseAssessment:
    notes = (
        assert_claim_allowed(
            "This panel can support future intervention verification only when "
            "the location intersects an HVA analysis area, the mechanism "
            f"plausibly affects {HOUR_LOCAL} {TIMEZONE} surface temperature, "
            f"and timing falls inside the {WINDOW_LABEL}."
        ),
        assert_claim_allowed(
            "Daytime shade interventions are not evaluable from 03:00 TCM "
            "alone unless an overnight mechanism is stated. This is not an "
            "intervention effect."
        ),
    )
    return InterventionReuseAssessment(
        usable_as_future_verification_candidate=True,
        requires_location_intersection_with_hva_zone=True,
        requires_mechanism_plausibly_affects_0300=True,
        requires_timing_inside_matched_window=True,
        daytime_shade_not_evaluable_from_0300_alone=True,
        not_an_intervention_effect=True,
        notes=notes,
    )


def assemble_zone_packet(panel: NighttimePanel, geoid: str) -> ZoneNighttimePacket:
    pairs = ((2022, 2023), (2023, 2024), (2022, 2024))
    summaries = tuple(matched_window_summary(panel, geoid, year) for year in REFERENCE_YEARS)
    yoy = tuple(
        year_over_year_zone_change(panel, geoid, earlier, later)
        for earlier, later in pairs
    )
    matched = tuple(
        matched_date_comparison(panel, geoid, earlier, later)
        for earlier, later in pairs
    )
    geography = tuple(
        analysis_geography_change_context(panel, geoid, earlier, later)
        for earlier, later in pairs
    )
    charts = (
        three_year_nighttime_line(panel, geoid),
        matched_date_distributions(panel, geoid),
        selected_zone_matched_date_strip(panel, geoid),
        analysis_geography_change_distribution(panel),
    )
    return ZoneNighttimePacket(
        contract_id=CONTRACT_ID,
        not_signal_a=True,
        geoid=str(geoid).zfill(11),
        year_summaries=summaries,
        year_over_year=yoy,
        matched_dates=matched,
        geography_context=geography,
        descriptive_three_year_change_c_per_year=descriptive_three_year_change_c_per_year(
            panel, geoid
        ),
        story=selected_zone_story(panel, geoid),
        charts=charts,
        map_layers=(yoy_change_map_layer(panel),),
        intervention=intervention_verification_reuse(),
    )


def api_contract() -> dict[str, Any]:
    """Unpublished domain/API contract. No public route is mounted."""
    return {
        "contract_id": CONTRACT_ID,
        "unpublished": True,
        "not_signal_a": True,
        "window_label": WINDOW_LABEL,
        "window_dates": WINDOW_DATES,
        "hour_local": HOUR_LOCAL,
        "timezone": TIMEZONE,
        "years": list(REFERENCE_YEARS),
        "quantity": TEMPERATURE_QUANTITY,
        "units": "°C",
        "source_family": SOURCE_FAMILY,
        "source_mode": SOURCE_MODE,
        "operations": [
            "matched_window_summary",
            "year_over_year_zone_change",
            "matched_date_comparison",
            "analysis_geography_change_context",
        ],
        "charts": [
            "three_year_nighttime_line",
            "matched_date_distributions",
            "selected_zone_matched_date_strip",
            "analysis_geography_change_distribution",
        ],
        "map_layers": ["yoy_change_2024_vs_2022"],
        "forbidden_public_labels": [
            "SUMMER TREND",
            "CLIMATE TREND",
            "ANNUAL TREND",
            "HEATDOSE",
            "AFTERHEAT",
            "RECOVERY",
            "PROBABILITY",
            "IMPACT",
        ],
    }
