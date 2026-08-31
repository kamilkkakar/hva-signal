/** First-read product copy. Method tokens stay in disclosure. */

export const WORDMARK = "HVA-SIGNAL";
export const PRODUCT_EXPANSION = "Heat, Vulnerability & Action Signal";
export const HERO_LINE = "From thermal observations to defensible urban heat decisions.";
export const HERO_SUPPORT =
  "See the thermal field, what HVA-Signal found, why it matters, and what to investigate next.";
export const PLACE_LINE = "Phoenix · 25 analysis areas";
export const MODE_LINE = "FortyGuard thermal intelligence";
export const PRODUCT_BADGE = "Cached demonstration";

export const BADGE_KICKER = "FortyGuard thermal intelligence";
export const BADGE_PROVIDER = "FortyGuard · 100 m TCM";
export const BADGE_MODE = "Cached demonstration";

export const SELECTOR_LABEL = "Analysis area";
export const SELECTOR_SEARCH = "Find an analysis area";
export const GEOID_SECONDARY = "Census tract";
export const DEMO_CONTROLS = "Explore another observation";

/** Visual metrics/map first → Decision Brief → interpretation → action → methods. */
export const SECTION_NAV = [
  { id: "happening", num: "01", title: "What did HVA-Signal find?" },
  { id: "brief", num: "02", title: "What are we seeing?" },
  { id: "changed", num: "03", title: "Why does it matter?" },
  { id: "verify", num: "04", title: "What should I investigate next?" },
  { id: "methods", num: "05", title: "Methods & provenance" },
] as const;

export const BRIEF_KICKER = "02 · Decision brief";
export const BRIEF_TITLE = "What are we seeing?";
export const BRIEF_EVIDENCE = "Evidence";
export const BRIEF_WHY = "Why it matters";
export const BRIEF_NEXT = "Suggested direction";

export const MAP_ABOUT_LAYER = "About this layer";
export const MAP_ABOUT_BODY =
  "Absolute °C fills show the selected-time thermal field for analysis areas. Ranking may be withheld when differences are too small to defend.";
export const MAP_CUE_MATCHED = "Matched nighttime change";
export const MAP_CUE_CONTEXT = "Local context";
export const MAP_CUE_VERIFY = "Investigate next";

export const PREP_SECTION_TITLE = "What support is identified?";

export const METRIC_TEMP = "Selected thermal observation";
export const METRIC_HISTORY = "Own-area historical position";
export const METRIC_CHANGE = "2024 vs 2022 matched-nighttime change";
export const METRIC_CHANGE_WINDOW = "30 Jun–30 Jul · 03:00 local";

export const HISTORY_UNAVAILABLE =
  "Not available for this observation.";
export const HISTORY_UNAVAILABLE_REASON =
  "A comparable own-area 03:00 historical position is not published for this case.";
export const HISTORY_UNAVAILABLE_WHY = "Why unavailable?";
export const HISTORY_CARD_TITLE = "Historical position";
export const HISTORY_WITHHELD =
  "The differences across the analysis areas are too small to support a defensible ordering for this observation.";
export const HISTORY_WITHHELD_TRUST =
  "HVA-Signal preserves the evidence rather than exaggerating small differences.";

export const SPATIAL_CARD_TITLE = "Spatial comparison";
export const RANKING_WITHHELD_TITLE = "Ranking withheld";
export const RANKING_WITHHELD_BODY =
  "Thermal differences across the analysis areas are too small to support a defensible ordering for this observation.";
export const RANKING_WITHHELD_NEXT =
  "Use the temporal and contextual evidence to decide what to verify. Do not recreate a hidden thermal ranking.";
export const RANKING_SUPPORTED_TITLE = "Spatial comparison available";
export const RANKING_SUPPORTED_BODY =
  "Thermal differences across the analysis areas are large enough to support a comparison for this observation.";

export const PATTERN_CARD_TITLE = "Evidence pattern";
export const EVIDENCE_SUMMARY_TITLE = "Evidence summary";

export const MATCHED_TITLE = "Matched nighttime change";
export const MATCHED_WINDOW =
  "Mean of matched 03:00 observations, 30 Jun–30 Jul each year · same calendar dates · same hour.";
export const MATCHED_NOT_CLIMATE =
  "Matched 03:00 nights across three windows — not a long-term climate series.";
export const MATCHED_SELECT = "Select an analysis area to read matched nighttime conditions.";
export const MATCHED_KEY_FINDING = "Finding";

export const INSTANTS_TITLE = "Observed thermal instants";
export const INSTANTS_SUBTITLE = "Four discrete observations. Hours between them were not measured.";
export const INSTANTS_GAP =
  "Guides connect observed instants only. Conditions between them were not measured.";
export const INSTANTS_SELECT = "Select an analysis area to read observed instants.";
export const INSTANTS_HIGH_LABEL = "Highest observed";
export const INSTANTS_DIFF_LABEL = "Gaps between observations";

export const CONTEXT_TITLE = "Local context";
export const CONTEXT_LEAD = "Values that can strengthen, weaken, or complicate the thermal reading — not a score.";
export const PREP_TITLE = "Heat-relief inventory";
export const PREP_IDENTIFIED = "Identified in available inventory";
export const PREP_NOT_IDENTIFIED = "Not identified in available inventory";
export const PREP_UNKNOWN = "Inventory status unknown";
export const PREP_DISCLAIMER =
  "Inventory identification is not proof that cooling is open or reachable.";
export const PREP_SOURCE_SUMMARY = "Source & coverage";

export const DECISION_TITLE = "What should I investigate next?";
export const DECISION_SHOWS = "What the evidence shows";
export const DECISION_MATTERS = "Why it matters";
export const DECISION_NEXT = "What to verify next";
export const DECISION_NO_RECOMMENDATION =
  "Investigation direction only. Not an automated intervention recommendation.";

export const ABOUT_SUMMARY = "Methods & provenance";
export const METHOD_SUMMARY = "Collapsed method detail for the evidence above.";

export const FORBIDDEN_FIRST_READ = [
  "q_A",
  "Decision 8",
  "NOT REQUESTED",
  "AWAITING ANALYSIS",
  "24-HOUR CURVE",
  "24-hour curve",
  "climate trend",
  "month/season",
  "intervention effect",
  "OUTLINES ONLY",
  "FILLS WAIT FOR A BOUND LAYER",
  "NO COOLING SITE",
  "no cooling site",
  "SUBMIT ANALYSIS",
  "Submit analysis",
  "not the municipality",
  "not live",
  "activity_id",
] as const;

export function historicalPositionSentence(qA: number): string {
  const percent = Math.round(qA * 100);
  return `Warmer than approximately ${percent}% of comparable historical 03:00 observations.`;
}

export function preparednessLabel(
  status: "IDENTIFIED" | "NOT_IDENTIFIED_IN_DATASET" | "UNKNOWN",
): string {
  if (status === "IDENTIFIED") {
    return PREP_IDENTIFIED;
  }
  if (status === "NOT_IDENTIFIED_IN_DATASET") {
    return PREP_NOT_IDENTIFIED;
  }
  return PREP_UNKNOWN;
}
