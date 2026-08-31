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

export const METRIC_TEMP = "Selected thermal observation";
export const METRIC_HISTORY = "Historical 03:00 position";
export const METRIC_CHANGE = "Matched nighttime change vs 2022";

export const HISTORY_UNAVAILABLE =
  "A historical 03:00 position is not published for this observation.";
export const HISTORY_WITHHELD =
  "The differences across the 25 analysis areas are too small to support a defensible ordering for this observation.";
export const HISTORY_WITHHELD_TRUST =
  "HVA-Signal preserves the evidence rather than exaggerating small differences.";

export const RANKING_WITHHELD_TITLE = "Spatial ranking withheld";
export const RANKING_WITHHELD_BODY =
  "The differences across the 25 analysis areas are too small to support a defensible ordering for this observation.";
export const RANKING_WITHHELD_NEXT =
  "Use the temporal and contextual evidence to decide what to verify. Do not recreate a hidden thermal ranking.";
export const RANKING_SUPPORTED_TITLE = "Spatial comparison available";
export const RANKING_SUPPORTED_BODY =
  "Nighttime historical positions differ enough across the 25 areas to support a comparison for this observation.";

export const MATCHED_TITLE = "How have nighttime conditions changed?";
export const MATCHED_WINDOW = "30 Jun–30 Jul, 03:00 local · same calendar dates · same hour";
export const MATCHED_NOT_CLIMATE =
  "These are matched 03:00 nights across three summers, not a long-term climate series.";
export const MATCHED_SELECT = "Select an analysis area to read matched nighttime conditions.";

export const INSTANTS_TITLE = "How did conditions differ across observed times?";
export const INSTANTS_SUBTITLE = "Four discrete observations. Hours between them were not measured.";
export const INSTANTS_GAP = "Interval not observed";
export const INSTANTS_SELECT = "Select an analysis area to read observed instants.";

export const CONTEXT_TITLE = "Local context";
export const PREP_TITLE = "Preparedness";
export const PREP_IDENTIFIED = "Identified";
export const PREP_NOT_IDENTIFIED = "Not identified in this dataset";
export const PREP_UNKNOWN = "Unknown";
export const PREP_DISCLAIMER =
  "Partial regional inventory. A dataset miss does not establish that no cooling resource exists.";

export const DECISION_TITLE = "What to verify next";
export const DECISION_SHOWS = "What the evidence shows";
export const DECISION_MATTERS = "Why it matters";
export const DECISION_NEXT = "What to verify next";
export const DECISION_NO_RECOMMENDATION =
  "This is investigation direction, not an automated intervention recommendation.";

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
  "NO COOLING SITE",
  "no cooling site",
  "SUBMIT ANALYSIS",
  "Submit analysis",
  "not the municipality",
  "not live",
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
