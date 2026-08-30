/** SIG-A judge copy. q_A / Decision 8 / S stay in Method. Math unchanged. */

export const SIGA_TITLE = "Nighttime Historical Thermal Signal";
export const SIGA_CHIP = "Historical unusualness at 3:00";
export const SIGA_QUESTION_PRIMARY =
  "How unusual was each zone at 3 a.m. versus its own past 3 a.m. nights?";
export const SIGA_QUESTION_GATE =
  "Is the difference across zones large enough to show an order?";
export const SIGA_ONE_SENTENCE =
  "Each zone is compared with its own 3 a.m. history. An order is shown only when the night differs enough.";
export const SIGA_INDEPENDENCE =
  "This is not a temperature snapshot and not a combined score.";
export const SIGA_CLOCK = "03:00 AOI-local. Not a selected hour. Not “now.”";
export const SIGA_GEOGRAPHY = "25-zone analysis window — not the city.";
export const SIGA_ASSISTIVE_MAP = "Nighttime historical thermal map";

export const STAMP_ORDER_SHOWN = "ORDER SHOWN";
export const STAMP_ORDER_WITHHELD = "ORDER WITHHELD";
export const STAMP_HISTORY_NOT_PREPARED = "HISTORY NOT PREPARED";
export const STAMP_HISTORY_TOO_THIN = "HISTORY TOO THIN";
export const STAMP_NOT_REQUESTED = "NOT REQUESTED";
export const STAMP_PENDING = "PENDING";
export const STAMP_FAILED = "FAILED";

export const MAP_LAYER_ORDER_SHOWN = "Nighttime heat order";
export const MAP_LAYER_ORDER_WITHHELD = "Order withheld — night too flat";

export const BODY_ORDER_SHOWN =
  "The night differs enough across zones to show a historical 3 a.m. order. Fills are that order. They are not degrees and not a chance of harm.";
export const BODY_ORDER_WITHHELD =
  "Unusualness versus each zone's own 3 a.m. history was computed. The difference across zones is not large enough to show an order. Outlines stay. This is the product, not a failure, and not a safety clearance.";
export const BODY_HISTORY_NOT_PREPARED =
  "This window's own 3 a.m. history is not prepared. Unusualness is not computed. An order is not shown. Geography ready is not history ready. Missing history is not treated as safe.";
export const BODY_HISTORY_TOO_THIN =
  "There is not enough of this window's own 3 a.m. history to compute unusualness. An order is not shown. Missing history is not treated as safe.";
export const BODY_NOT_REQUESTED =
  "Signal A is inert until a 25-zone analysis geography is ready. Geography ready is not history ready.";
export const BODY_PENDING =
  "Signal A is pending only if this window's 3 a.m. history already exists. A new place does not start history collection.";
export const BODY_FAILED =
  "Signal A failed closed. An order is not shown. This is not a safety clearance.";
export const BODY_IDLE = "No order is shown until this analysis can defend one.";
export const BODY_LOADING = "Loading the analysis window.";

export const FEATURE_WITHHOLD =
  "Withholding the order is how Signal A stays honest. A flat night does not get a manufactured ranking.";

export const RAIL_ORDER_SHOWN =
  "Nighttime order is shown. Fills are historical 3 a.m. order, not degrees.";
export const RAIL_ORDER_WITHHELD =
  "Nighttime order is withheld. The night is too flat to defend a ranking. Missing data is not treated as safe.";
export const RAIL_HISTORY_LOCK =
  "Historical 3 a.m. comparison is not available. Missing history is not treated as safe.";
export const RAIL_NOT_REQUESTED = BODY_NOT_REQUESTED;
export const RAIL_PENDING = BODY_PENDING;
export const RAIL_FAILED = BODY_FAILED;
export const RAIL_IDLE = BODY_IDLE;
export const RAIL_LOADING = BODY_LOADING;

export const OVERLAY_ORDER_SHOWN =
  "Fill shows the historical 3 a.m. order. Rank is not a probability and not a heat-severity class.";
export const OVERLAY_ORDER_WITHHELD =
  "No order is shown. Rankings will not be invented from outlines.";
export const OVERLAY_HISTORY_LOCK =
  "Neutral evidence state. No nighttime order is shown.";
export const OVERLAY_IDLE = BODY_IDLE;
export const OVERLAY_LOADING = BODY_LOADING;

export const METHOD_TITLE = "Method";
export const METHOD_QA =
  "q_A is the own-zone historical unusualness index at 03:00. Experience says how unusual versus this zone's own 3 a.m. nights.";
export const METHOD_D8 =
  "Decision 8 (D8) is the gate that asks whether the difference is large enough to show an order. Experience shows ORDER SHOWN or ORDER WITHHELD.";
export const METHOD_S =
  "S is the normalized spread of that unusualness field. Experience says the night differs enough or the night is too flat.";

export const FORBIDDEN_CHROME_METHOD = [
  "q_A",
  "Decision 8",
  "D8",
  "S =",
  "0.10",
  "quantile",
  "ECDF",
] as const;

export const FORBIDDEN_JUDGE_PHRASES = [
  "INSUFFICIENT EVIDENCE",
  "INTERVENTION PRIORITY",
  "CONTEXTUAL PREPAREDNESS PRIORITY",
  "low risk",
  "low-risk",
  "all-clear",
  "all clear",
  "this place is fine",
  "overnight recovery",
  "AfterHeat",
  "HeatDose",
  "current risk",
  "chance of harm",
  "first to treat",
  "certified cooling",
  "city-wide",
  "Phoenix's heat",
  "combined score:",
  "FortyGuard",
] as const;

export function publishedChromeCopy(): string[] {
  return [
    SIGA_TITLE,
    SIGA_CHIP,
    SIGA_QUESTION_PRIMARY,
    SIGA_QUESTION_GATE,
    SIGA_ONE_SENTENCE,
    SIGA_INDEPENDENCE,
    SIGA_CLOCK,
    SIGA_GEOGRAPHY,
    SIGA_ASSISTIVE_MAP,
    STAMP_ORDER_SHOWN,
    STAMP_ORDER_WITHHELD,
    STAMP_HISTORY_NOT_PREPARED,
    STAMP_HISTORY_TOO_THIN,
    STAMP_NOT_REQUESTED,
    STAMP_PENDING,
    STAMP_FAILED,
    MAP_LAYER_ORDER_SHOWN,
    MAP_LAYER_ORDER_WITHHELD,
    BODY_ORDER_SHOWN,
    BODY_ORDER_WITHHELD,
    BODY_HISTORY_NOT_PREPARED,
    BODY_HISTORY_TOO_THIN,
    BODY_NOT_REQUESTED,
    BODY_PENDING,
    BODY_FAILED,
    BODY_IDLE,
    BODY_LOADING,
    FEATURE_WITHHOLD,
    RAIL_ORDER_SHOWN,
    RAIL_ORDER_WITHHELD,
    RAIL_HISTORY_LOCK,
    OVERLAY_ORDER_SHOWN,
    OVERLAY_ORDER_WITHHELD,
    OVERLAY_HISTORY_LOCK,
  ];
}

export function publishedMethodCopy(): string[] {
  return [METHOD_TITLE, METHOD_QA, METHOD_D8, METHOD_S];
}

export function formatOrderHover(zoneId: string, order: number): string {
  return `Zone ${zoneId} · Nighttime order ${order} of 25 · Versus this zone's own 3 a.m. nights`;
}

export function chromeUsesForbiddenPhrase(blob: string, phrase: string): boolean {
  if (!blob.includes(phrase)) {
    return false;
  }
  if (phrase === "chance of harm" && blob.includes("not a chance of harm")) {
    return false;
  }
  return true;
}
