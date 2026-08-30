/** Deterministic public story copy. No LLM. Method tokens stay out of chrome. */

export const COMPARISON_SUFFICIENT =
  "Spatial differences are clear enough to compare";

export const COMPARISON_TOO_SIMILAR =
  "Nighttime patterns are too similar to rank defensibly";

export const REFERENCE_AVAILABLE = "Historical reference available";

export const REFERENCE_NOT_PREPARED = "Historical reference is not prepared";

export const REFERENCE_NOT_STATED = "Historical reference period is not stated";

export const EVIDENCE_LINEAGE_RECORDED = "Evidence lineage recorded";

export const HEADLINE_IDLE = "No night submitted";
export const HEADLINE_AWAITING = "Replay is running. No order is shown yet.";
export const HEADLINE_FAILED = "Analysis failed closed";
export const HEADLINE_HISTORY = "Historical reference is not prepared";
export const HEADLINE_COMPARABLE =
  "Spatial differences are clear enough to compare";
export const HEADLINE_TOO_SIMILAR =
  "Nighttime patterns are too similar to rank defensibly";
export const HEADLINE_NOT_EVALUATED = "Spatial ordering was not evaluated";

export const SUMMARY_IDLE =
  "No spatial comparison is available until a dated 03:00 replay is submitted.";
export const SUMMARY_AWAITING =
  "Replay is running. No nighttime heat order is shown yet.";
export const SUMMARY_FAILED =
  "Analysis failed closed. An order is not shown. Missing data is not treated as safe.";
export const SUMMARY_HISTORY =
  "This window's own 3 a.m. history is not prepared. Unusualness is not computed. An order is not shown. Geography ready is not history ready. Missing history is not treated as safe.";
export const SUMMARY_COMPARABLE =
  "The night differs enough across zones to show a historical 3 a.m. order. Fills are that order. They are not degrees and not a chance of harm.";
export const SUMMARY_TOO_SIMILAR =
  "Unusualness versus each zone's own 3 a.m. history was computed. The difference across zones is not large enough to show an order. Outlines stay. This is the product, not a failure, and not a safety clearance.";
export const SUMMARY_NOT_EVALUATED =
  "Spatial ordering was not evaluated for this result. Missing evaluation is not treated as safe.";

export const EXPLANATION_IDLE =
  "No spatial comparison is available until a dated 03:00 replay is submitted.";
export const EXPLANATION_AWAITING =
  "No spatial comparison is authorized until the replay finishes.";
export const EXPLANATION_FAILED =
  "The analysis failed closed. Missing data is not treated as safe.";
export const EXPLANATION_HISTORY =
  "Historical reference is not prepared. Missing history is not treated as safe.";
export const EXPLANATION_NOT_EVALUATED =
  "Spatial ordering was not evaluated for this result. Missing evaluation is not treated as safe.";

export const CLOCK_FACT =
  "Clock is 03:00 AOI-local. Not a selected hour. Not now.";
export const WINDOW_FACT =
  "This is a 25-zone analysis window, not the municipality.";
export const SOURCE_FACT = "Source is dated replay, not live.";
export const ORDER_FACT =
  "Fills are historical 3 a.m. order, not degrees and not a chance of harm.";
export const WITHHOLD_FACT =
  "Outlines stay. Rankings will not be invented from a flat night.";
export const HISTORY_FACT =
  "Geography ready is not history ready. Missing history is not treated as safe.";
export const SNAPSHOT_OFF_FACT =
  "Selected-hour snapshot is AVAILABLE NOW — CACHED EVIDENCE for 15 Jul 2025 03:00. Not live.";

export const OBSERVATION_TIME_FALLBACK =
  "03:00 AOI-local · dated replay · not live";

export const AREA_WINDOW_SUFFIX = "25-zone analysis window, not the municipality";
export const AREA_GENERIC_SUFFIX = "25-zone analysis window, not a city";

export const SOURCE_SUMMARY =
  "Dated replay. Not live. Not a vendor fetch.";

export const MAP_MEANING_SHOWN =
  "Fills are the historical 3 a.m. order. Rank is not a probability and not a heat-severity class.";
export const MAP_MEANING_WITHHELD =
  "No order is shown. Rankings will not be invented from outlines.";
export const MAP_MEANING_HISTORY =
  "Neutral evidence state. No nighttime order is shown.";
export const MAP_MEANING_IDLE =
  "No order is shown until this analysis can defend one.";
export const MAP_MEANING_AWAITING = "Replay is running. No order is shown yet.";

export const ZONE_EMPTY = "Click a zone. No zone selected.";

export const SUPPORTS_COMPARABLE =
  "Thermal evidence may be used as one input when deciding where further attention or contextual assessment is needed.";
export const SUPPORTS_TOO_SIMILAR =
  "Do not use thermal ranking alone for zone prioritization.";
export const SUPPORTS_HISTORY =
  "Do not use thermal ranking. Missing history is not treated as safe.";
export const SUPPORTS_AWAITING = "No spatial order is authorized yet.";
export const SUPPORTS_NOT_EVALUATED =
  "Do not use thermal ranking. Missing evaluation is not treated as safe.";
export const SUPPORTS_FAILED =
  "Do not use thermal ranking. A failed analysis is not a safety clearance.";
export const SUPPORTS_IDLE = "No spatial order is authorized yet.";

export const DOES_NOT_DEPLOY =
  "This does not authorize automatic deployment of resources.";
export const DOES_NOT_VULNERABILITY = "Vulnerability is not scored.";
export const DOES_NOT_COMBINED = "A combined score is not authorized.";
export const DOES_NOT_LIVE =
  "This is not live, not a forecast, and not overnight recovery.";
export const DOES_NOT_CLEARANCE =
  "Withholding an order is not a safety clearance and does not mean zones have equal need.";
export const DOES_NOT_CONTEXT =
  "Vulnerability, preparedness, operational constraints, and local context remain necessary for actual intervention decisions.";
export const DOES_NOT_MISSING_SAFE = "Missing data is not treated as safe.";

export const METHOD_QA =
  "q_A is the own-zone historical unusualness index at 03:00. Experience says how unusual versus this zone's own 3 a.m. nights.";
export const METHOD_D8 =
  "Decision 8 (D8) is the gate that asks whether the difference is large enough to show an order. Experience shows order shown or order withheld.";
export const METHOD_S =
  "S is the normalized spread of that unusualness field. Experience says the night differs enough or the night is too flat.";

export const FORBIDDEN_PUBLIC_TOKENS = [
  "q_A",
  "Decision 8",
  "D8",
  "S =",
  "GRAPH_POPULATED",
  "GRAPH_ABSENT",
  "GRAPH_EMPTY",
  "INSUFFICIENT_EVIDENCE",
  "INSUFFICIENT EVIDENCE",
  "THERMAL_SPATIAL_DIFFERENTIATION",
  "FULL_REFERENCE",
  "INSUFFICIENT_REFERENCE",
  "FortyGuard",
  "fortyguard",
  "city-wide",
  "citywide",
  "Phoenix's heat",
  "combined score:",
  "low risk",
  "low-risk",
  "all-clear",
  "all clear",
  "intervention priority",
  "contextual preparedness",
] as const;

export function formatObservationTime(analysisTime: string | null | undefined): string {
  if (!analysisTime) {
    return OBSERVATION_TIME_FALLBACK;
  }
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(analysisTime.trim());
  if (!match?.[1]) {
    return OBSERVATION_TIME_FALLBACK;
  }
  return `${match[1]} · 03:00 AOI-local · dated replay · not live`;
}

export function formatAreaLabel(areaId: string | null | undefined): string {
  if (!areaId) {
    return AREA_GENERIC_SUFFIX;
  }
  if (areaId === "phoenix-demo") {
    return `Phoenix demonstration area — ${AREA_WINDOW_SUFFIX}`;
  }
  return `${areaId} — ${AREA_GENERIC_SUFFIX}`;
}

export function formatReferenceYears(years: readonly number[] | null | undefined): string | null {
  if (!years || years.length === 0) {
    return null;
  }
  const sorted = [...years].sort((left, right) => left - right);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  if (first === last) {
    return String(first);
  }
  return `${first}–${last}`;
}

export function formatOrderHover(zoneId: string, order: number): string {
  return `Zone ${zoneId} · Nighttime order ${order} of 25 · Versus this zone's own 3 a.m. nights`;
}

export function publishedStoryCopy(): string[] {
  return [
    COMPARISON_SUFFICIENT,
    COMPARISON_TOO_SIMILAR,
    REFERENCE_AVAILABLE,
    REFERENCE_NOT_PREPARED,
    EVIDENCE_LINEAGE_RECORDED,
    HEADLINE_IDLE,
    HEADLINE_AWAITING,
    HEADLINE_FAILED,
    HEADLINE_HISTORY,
    HEADLINE_COMPARABLE,
    HEADLINE_TOO_SIMILAR,
    HEADLINE_NOT_EVALUATED,
    SUMMARY_IDLE,
    SUMMARY_AWAITING,
    SUMMARY_FAILED,
    SUMMARY_HISTORY,
    SUMMARY_COMPARABLE,
    SUMMARY_TOO_SIMILAR,
    SUMMARY_NOT_EVALUATED,
    CLOCK_FACT,
    WINDOW_FACT,
    SOURCE_FACT,
    ORDER_FACT,
    WITHHOLD_FACT,
    HISTORY_FACT,
    SNAPSHOT_OFF_FACT,
    SOURCE_SUMMARY,
    SUPPORTS_COMPARABLE,
    SUPPORTS_TOO_SIMILAR,
    DOES_NOT_DEPLOY,
    DOES_NOT_CLEARANCE,
  ];
}
