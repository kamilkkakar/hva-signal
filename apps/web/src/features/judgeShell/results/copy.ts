/** Result-card copy. One question, one message, few values. Method stays in accordion. */

export const MAX_QUESTION_WORDS = 18;
export const MAX_MESSAGE_WORDS = 18;
export const MAX_VALUES = 3;

export const SIGNAL_A_KICKER = "Signal A";
export const SIGNAL_A_TITLE = "Nighttime historical";
export const SIGNAL_A_QUESTION =
  "How unusual was each zone at 3 a.m. versus its own past 3 a.m. nights?";

export const SIGNAL_A_MESSAGE_IDLE =
  "No order is shown until this analysis can defend one.";
export const SIGNAL_A_MESSAGE_WORKING =
  "Replay is running. No order is shown yet.";
export const SIGNAL_A_MESSAGE_SHOWN =
  "The night differs enough to show a historical 3 a.m. order.";
export const SIGNAL_A_MESSAGE_WITHHELD =
  "The night is too flat to defend a ranking. Missing is not safe.";
export const SIGNAL_A_MESSAGE_NOT_PREPARED =
  "This window's own 3 a.m. history is not prepared.";
export const SIGNAL_A_MESSAGE_FAILED =
  "Analysis failed closed. An order is not shown.";

export const STAMP_ORDER_SHOWN = "ORDER SHOWN";
export const STAMP_ORDER_WITHHELD = "ORDER WITHHELD";
export const STAMP_HISTORY_NOT_PREPARED = "HISTORY NOT PREPARED";
export const STAMP_NOT_REQUESTED = "NOT REQUESTED";
export const STAMP_WORKING = "WORKING";
export const STAMP_FAILED = "FAILED";

export const SIGNAL_B_KICKER = "Signal B";
export const SIGNAL_B_TITLE = "Selected-time snapshot";
export const SIGNAL_B_QUESTION =
  "What was each zone's temperature at a chosen hour?";
export const SIGNAL_B_STAMP = "NOT ON THIS SURFACE";
export const SIGNAL_B_MESSAGE =
  "Selected-hour snapshot is not published here.";

export const VALUE_CLOCK_LABEL = "Clock";
export const VALUE_CLOCK = "03:00";
export const VALUE_WINDOW_LABEL = "Window";
export const VALUE_WINDOW = "25-zone";
export const VALUE_SOURCE_LABEL = "Source";
export const VALUE_SOURCE = "REPLAY";
export const VALUE_SURFACE_LABEL = "Surface";
export const VALUE_SURFACE = "off";

export const D8_SUMMARY = "Analysis detail";
export const D8_METHOD_NOTE =
  "q_A, Decision 8, and S stay in Method. Cards show the order call only.";

export const FORBIDDEN_CARD_FACE = [
  "q_A",
  "Decision 8",
  "D8",
  "S =",
  "0.10",
  "quantile",
  "ECDF",
  "INSUFFICIENT_EVIDENCE",
  "INSUFFICIENT EVIDENCE",
  "THERMAL_SPATIAL_DIFFERENTIATION",
  "US_CENSUS_TIGERLINE",
  "PHX_NORMALIZED_HAZARD",
  "TOP3_BOTTOM3",
  "fortyguard",
  "city-wide",
  "real-time",
] as const;

export function publishedCardCopy(): string[] {
  return [
    SIGNAL_A_KICKER,
    SIGNAL_A_TITLE,
    SIGNAL_A_QUESTION,
    SIGNAL_A_MESSAGE_IDLE,
    SIGNAL_A_MESSAGE_WORKING,
    SIGNAL_A_MESSAGE_SHOWN,
    SIGNAL_A_MESSAGE_WITHHELD,
    SIGNAL_A_MESSAGE_NOT_PREPARED,
    SIGNAL_A_MESSAGE_FAILED,
    STAMP_ORDER_SHOWN,
    STAMP_ORDER_WITHHELD,
    STAMP_HISTORY_NOT_PREPARED,
    STAMP_NOT_REQUESTED,
    STAMP_WORKING,
    STAMP_FAILED,
    SIGNAL_B_KICKER,
    SIGNAL_B_TITLE,
    SIGNAL_B_QUESTION,
    SIGNAL_B_STAMP,
    SIGNAL_B_MESSAGE,
    VALUE_CLOCK,
    VALUE_WINDOW,
    VALUE_SOURCE,
    VALUE_SURFACE,
  ];
}
