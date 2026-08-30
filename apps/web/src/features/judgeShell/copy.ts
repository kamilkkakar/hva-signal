/** UX-A V1 + UX-B Hybrid IA first-paint copy. No vendor, city-wide, live, or %. */

export const EYEBROW = "3K Labs";
export const WORDMARK = "HVA-Signal";
export const PRODUCT_EXPANSION = "Heat, Vulnerability & Action Signal";

export const HERO_LINE =
  "Shows a nighttime heat order only when the thermal field can defend it.";

export const HERO_SUPPORT =
  "A snapshot is temperature at a chosen hour. Historical is unusualness at 3 a.m. versus each zone's own nights. If the night is too flat, the map keeps outlines and withholds the ranking.";

export const HERO_HONESTY =
  "Vulnerability is not scored. Action means rank or withhold — not a treatment plan.";

export const HERO_TAGLINE =
  "Thermal evidence for defensible urban heat decisions — only when the field can support an order.";

export const TITLE_CARD = "Rank the night only when the night earns it.";

export const CHIP_WINDOW_ID = "Phoenix demonstration area";
export const CHIP_WINDOW = "25-zone analysis window";
export const CHIP_CLOCK = "03:00";
export const CHIP_SOURCE = "replay";
export const CHIP_NOT_LIVE = "not live";
export const CHIP_NOT_CITY = "not the municipality";

export const CONTEXT_ARIA = "Analysis window and time";

export const HAPPENING_NOT_REQUESTED =
  "No night submitted. Replay a dated 03:00 window.";
export const HAPPENING_WORKING = "Replay is running. No order is shown yet.";
export const HAPPENING_ORDER_SHOWN =
  "The night differs enough to show a historical 3 a.m. order.";
export const HAPPENING_ORDER_WITHHELD =
  "Unusualness computed. Spatial difference too small to show an order.";
export const HAPPENING_HISTORY_NOT_PREPARED =
  "This window's 3 a.m. history is not prepared.";
export const HAPPENING_JOB_LOST =
  "The analysis job is no longer on this runtime.";
export const HAPPENING_STALLED = "The analysis job stalled. Resubmit the last replay.";
export const HAPPENING_FAILED = "Analysis failed closed. An order is not shown.";

export const SIGNAL_A_QUESTION =
  "How unusual was each zone at 3 a.m. versus its own past 3 a.m. nights?";
export const SIGNAL_A_FACT_IDLE = "Historical unusualness at 03:00. Not a snapshot.";
export const SIGNAL_A_FACT_SHOWN = "Fills are that order. Not degrees. Not chance.";
export const SIGNAL_A_FACT_WITHHELD =
  "Withholding the order is the product, not a failure.";
export const SIGNAL_A_FACT_NOT_PREPARED =
  "History is not prepared. Missing is not treated as safe.";

export const SIGNAL_B_QUESTION = "What was each zone’s temperature at a chosen hour?";
export const SIGNAL_B_STAMP = "AVAILABLE NOW — CACHED EVIDENCE";
export const SIGNAL_B_FACT = "Cached 15 Jul 03:00 reading. 25 of 25 zones. Not live.";

export const SELECTED_ZONE_EMPTY = "Click a zone. No zone selected.";

export const SUPPORTS_TITLE = "What evidence supports";
export const DOES_NOT_TITLE = "What evidence does not";

export const SUPPORTS_BULLETS = [
  "Show or withhold this night’s order",
  "Name the window and the clock",
  "Use an authorized order as one input",
] as const;

export const DOES_NOT_BULLETS = [
  "Vulnerability score",
  "Treatment or deploy here",
  "Combined A+B score",
  "Live now, forecast, or overnight",
] as const;

export const SUPPORTS_CONTEXT =
  "Vulnerability, operations, and local context still required.";

export const CAPABILITY_TITLE = "Active capability expansion";
export const CAPABILITY_ON = "On this surface";
export const CAPABILITY_NEXT = "Next / gated";
export const CAPABILITY_NOT = "Not this product";

export const CAPABILITY_ON_ITEMS = [
  { noun: "Signal A replay", status: "AVAILABLE NOW" },
  { noun: "Rank or withhold", status: "AVAILABLE NOW" },
  { noun: "Action framing", status: "AVAILABLE NOW — DECISION FRAMING" },
  { noun: "Signal B snapshot", status: "AVAILABLE NOW — CACHED EVIDENCE" },
] as const;

export const CAPABILITY_NEXT_ITEMS = [
  { noun: "Place search / geo", status: "DISABLED" },
  { noun: "Hosted live", status: "DISABLED" },
] as const;

export const CAPABILITY_NOT_ITEMS = [
  { noun: "HeatDose", status: "ANALYTICAL DEVELOPMENT" },
  { noun: "AfterHeat", status: "ACTIVE DEVELOPMENT & VALIDATION" },
  { noun: "WBGT", status: "INTEGRATION PATHWAY / BLOCKED" },
  { noun: "Calibrated chance", status: "MODEL DEVELOPMENT — numeric BLOCKED" },
] as const;

export const RUN_KICKER = "Replay a night";
export const RUN_SUFFICIENT = "30 Jun 2022 · order can appear";
export const RUN_INSUFFICIENT = "1 Jul 2022 · order can vanish";
export const RUN_SUBMIT = "Submit replay";
export const RUN_RESUBMIT = "Resubmit";
export const RUN_CLOCK_LOCK = "03:00 AOI-local locked. Replay only.";

export const SUFFICIENT_NIGHT_DATE = "2022-06-30";
export const INSUFFICIENT_NIGHT_DATE = "2022-07-01";

export const PROVENANCE_L1_ARIA = "Provenance";
export const PROVENANCE_L2_SUMMARY = "Method and versions";

export const FORBIDDEN_FIRST_PAINT = [
  "city-wide",
  "citywide",
  "real-time",
  "realtime",
  "current conditions",
  "copilot",
  "fortyguard",
  "intervention priority",
  "contextual preparedness",
  "phoenix-demo",
  "geoid",
  "log in",
  "login",
  "sign up",
] as const;

export function publishedJudgeCopy(): string[] {
  return [
    EYEBROW,
    WORDMARK,
    PRODUCT_EXPANSION,
    HERO_LINE,
    HERO_SUPPORT,
    HERO_HONESTY,
    HERO_TAGLINE,
    TITLE_CARD,
    CHIP_WINDOW_ID,
    CHIP_WINDOW,
    CHIP_CLOCK,
    CHIP_SOURCE,
    CHIP_NOT_LIVE,
    CHIP_NOT_CITY,
    HAPPENING_NOT_REQUESTED,
    HAPPENING_WORKING,
    HAPPENING_ORDER_SHOWN,
    HAPPENING_ORDER_WITHHELD,
    HAPPENING_HISTORY_NOT_PREPARED,
    SIGNAL_A_QUESTION,
    SIGNAL_B_QUESTION,
    SIGNAL_B_STAMP,
    SIGNAL_B_FACT,
    SELECTED_ZONE_EMPTY,
    ...SUPPORTS_BULLETS,
    ...DOES_NOT_BULLETS,
    SUPPORTS_CONTEXT,
    CAPABILITY_TITLE,
    RUN_SUFFICIENT,
    RUN_INSUFFICIENT,
    RUN_CLOCK_LOCK,
  ];
}
