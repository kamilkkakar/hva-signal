/** First-read product copy. Method tokens stay in disclosure. */

export const WORDMARK = "HVA-SIGNAL";
export const PRODUCT_EXPANSION = "Heat, Vulnerability & Action Signal";
export const HERO_LINE = "From thermal observations to defensible urban heat decisions.";
export const HERO_SUPPORT =
  "Explore how heat conditions compare with history, change over time, and intersect with local context and preparedness.";
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

export const SECTION_NAV = [
  { id: "happening", num: "01", title: "What's happening here?" },
  { id: "history", num: "02", title: "How does this compare with history?" },
  { id: "changed", num: "03", title: "How have conditions changed?" },
  { id: "context", num: "04", title: "What local context matters?" },
  { id: "verify", num: "05", title: "What should be verified next?" },
] as const;

export const PREP_SECTION_TITLE = "What support is identified?";

export const METRIC_TEMP = "Selected thermal observation";
export const METRIC_HISTORY = "Own-area historical position";
export const METRIC_CHANGE = "2024 vs 2022 matched-nighttime change";
export const METRIC_CHANGE_WINDOW = "30 Jun–30 Jul · 03:00 local";

export const HISTORY_UNAVAILABLE =
  "Not available for this observation.";
export const HISTORY_UNAVAILABLE_REASON =
  "A comparable own-area 03:00 historical position is not published for this case.";
export const HISTORY_UNAVAILABLE_WHY = "Why?";
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

export const MATCHED_TITLE = "How have matched nighttime conditions changed?";
export const MATCHED_WINDOW =
  "Mean of matched 03:00 observations, 30 Jun–30 Jul each year · same calendar dates · same hour.";
export const MATCHED_NOT_CLIMATE =
  "These are matched 03:00 nights across three windows, not a long-term climate series.";
export const MATCHED_SELECT = "Select an analysis area to read matched nighttime conditions.";
export const MATCHED_KEY_FINDING = "Key finding";

export const INSTANTS_TITLE = "How did conditions differ across observed times?";
export const INSTANTS_SUBTITLE = "Four discrete observations. Hours between them were not measured.";
export const INSTANTS_GAP =
  "Dashed guides connect observed instants for orientation only. Conditions between these observations were not measured.";
export const INSTANTS_SELECT = "Select an analysis area to read observed instants.";
export const INSTANTS_HIGH_LABEL = "Highest observed instant";
export const INSTANTS_DIFF_LABEL = "Difference between observations";

export const CONTEXT_TITLE = "What local context matters?";
export const PREP_TITLE = "Heat-relief resources";
export const PREP_IDENTIFIED = "Identified in available inventory";
export const PREP_NOT_IDENTIFIED = "Not identified / in available inventory";
export const PREP_UNKNOWN = "Inventory status unknown";
export const PREP_DISCLAIMER =
  "This does not establish that no cooling resource exists. Identification is not proof that cooling is available.";
export const PREP_SOURCE_SUMMARY = "Source & coverage";

export const DECISION_TITLE = "What should be verified next?";
export const DECISION_SHOWS = "What the evidence shows";
export const DECISION_MATTERS = "Why it matters";
export const DECISION_NEXT = "What to verify next";
export const DECISION_NO_RECOMMENDATION =
  "Investigation direction only. Not an automated intervention recommendation.";

export const ABOUT_SUMMARY = "About this evidence";
export const METHOD_SUMMARY = "Method and provenance";

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
