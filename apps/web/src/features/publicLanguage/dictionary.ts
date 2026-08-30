/**
 * RESCUE-G canonical public-language dictionary.
 * View models import these strings. Backend tokens stay under Technical details.
 * Do not invent statuses. Math is unchanged.
 */

export const PUBLIC_STATUS = {
  ANALYSIS_COMPLETE: "ANALYSIS COMPLETE",
  SPATIAL_ORDERING_SUPPORTED: "SPATIAL ORDERING SUPPORTED",
  SPATIAL_ORDERING_WITHHELD: "SPATIAL ORDERING WITHHELD",
  HISTORICAL_REFERENCE_AVAILABLE: "HISTORICAL REFERENCE AVAILABLE",
  SNAPSHOT_UNAVAILABLE: "SNAPSHOT UNAVAILABLE",
  REPLAY_EVIDENCE: "REPLAY EVIDENCE",
} as const;

export type PublicStatus = (typeof PUBLIC_STATUS)[keyof typeof PUBLIC_STATUS];

export const PUBLIC_STATUSES: readonly PublicStatus[] = [
  PUBLIC_STATUS.ANALYSIS_COMPLETE,
  PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED,
  PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD,
  PUBLIC_STATUS.HISTORICAL_REFERENCE_AVAILABLE,
  PUBLIC_STATUS.SNAPSHOT_UNAVAILABLE,
  PUBLIC_STATUS.REPLAY_EVIDENCE,
];

/**
 * Already-shipped JudgeShell stamps. Same meaning as the matching public status.
 * Not invented by this rescue. Keep until Lead stitches chrome.
 */
export const SHIPPED_ALIAS = {
  ORDER_SHOWN: "ORDER SHOWN",
  ORDER_WITHHELD: "ORDER WITHHELD",
} as const;

export const PUBLIC_NOUN = {
  DECISION_8: "Spatial differentiation check",
  Q_A: "Historical position",
  S: "Observed separation across zones",
  DECISION_8_FLOOR: "Minimum separation required by the analysis policy",
  BACKEND_ORDER: "Relative order within this analysis",
  EVIDENCE_LINEAGE: "Evidence lineage",
  FULL_REFERENCE: "Historical reference available",
} as const;

export const PUBLIC_SENTENCE = {
  INSUFFICIENT_EVIDENCE:
    "Not enough spatial differentiation to support ordering",
  Q_A_GLOSS:
    "How unusual this zone is versus its own past 3 a.m. nights.",
  DECISION_8_GLOSS:
    "Whether the difference across zones is large enough to show an order.",
  S_GLOSS: "How far zones sit apart on historical position.",
  FLOOR_GLOSS:
    "The smallest observed separation the analysis policy requires before an order may be shown.",
  BACKEND_ORDER_GLOSS:
    "This zone’s place in the authorized order for this analysis only. Not a treatment rank.",
  EVIDENCE_LINEAGE_GLOSS:
    "Methodology and provenance of recorded evidence. Does not authorize a spatial thermal claim.",
  WITHHOLD_IS_PRODUCT:
    "Withholding the order is the product, not a failure, and not a safety clearance.",
} as const;

export type DictionarySurface =
  | "primary"
  | "technical_details"
  | "never"
  | "remove";

export type DictionaryGate = "ordering_allowed";

export type DictionaryRow = {
  internal: string;
  publicLabel: string | null;
  publicStatus: PublicStatus | null;
  surface: DictionarySurface;
  gate?: DictionaryGate;
  notes: string;
};

const ROWS: DictionaryRow[] = [
  {
    internal: "Decision 8",
    publicLabel: PUBLIC_NOUN.DECISION_8,
    publicStatus: null,
    surface: "primary",
    notes:
      "Public noun only. Raw Decision 8 / D8 stays under Technical details. Not a stamp.",
  },
  {
    internal: "q_A",
    publicLabel: PUBLIC_NOUN.Q_A,
    publicStatus: null,
    surface: "primary",
    notes:
      "Public noun: historical position. Not a probability. Raw q_A stays under Technical details.",
  },
  {
    internal: "S",
    publicLabel: PUBLIC_NOUN.S,
    publicStatus: null,
    surface: "primary",
    notes:
      "Public noun for observed separation. Do not print S = on chrome. Token stays under Technical details.",
  },
  {
    internal: "Decision 8 floor",
    publicLabel: PUBLIC_NOUN.DECISION_8_FLOOR,
    publicStatus: null,
    surface: "primary",
    notes:
      "Do not print 0.10 as 10% or as a chance. Floor value may appear in Technical details with units named there.",
  },
  {
    internal: "FULL_REFERENCE",
    publicLabel: PUBLIC_NOUN.FULL_REFERENCE,
    publicStatus: PUBLIC_STATUS.HISTORICAL_REFERENCE_AVAILABLE,
    surface: "primary",
    notes: "Reference quality is not geography-ready and not order-shown.",
  },
  {
    internal: "INSUFFICIENT_EVIDENCE",
    publicLabel: PUBLIC_SENTENCE.INSUFFICIENT_EVIDENCE,
    publicStatus: PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD,
    surface: "primary",
    notes:
      "Stamp is SPATIAL ORDERING WITHHELD. Do not stamp INSUFFICIENT EVIDENCE — that reads as missing data. History-not-prepared is a different question.",
  },
  {
    internal: "SUFFICIENT",
    publicLabel: PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED,
    publicStatus: PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED,
    surface: "primary",
    notes:
      "Differentiation_state SUFFICIENT means an order may be shown. Not a safety claim.",
  },
  {
    internal: "ZoneFeatureVector",
    publicLabel: null,
    publicStatus: null,
    surface: "never",
    notes:
      "Type-only. Carries unpublished scores (vulnerability, recovery, intervention_evidence). Never show the name or those fields.",
  },
  {
    internal: "GRAPH_POPULATED",
    publicLabel: PUBLIC_NOUN.EVIDENCE_LINEAGE,
    publicStatus: null,
    surface: "technical_details",
    notes:
      "Evidence lineage / methodology / provenance only. Never a primary stamp. Does not authorize ordering.",
  },
  {
    internal: "INTERVENTION PRIORITY",
    publicLabel: null,
    publicStatus: null,
    surface: "remove",
    notes:
      "Not justified. Command Center leftover in mapLayer.ts. JudgeShell remaps. Do not restore.",
  },
  {
    internal: "backend order",
    publicLabel: PUBLIC_NOUN.BACKEND_ORDER,
    publicStatus: null,
    surface: "primary",
    gate: "ordering_allowed",
    notes:
      "Only when spatial ordering is supported and a number is useful. Not a priority rank.",
  },
  {
    internal: "READY",
    publicLabel: null,
    publicStatus: null,
    surface: "remove",
    notes:
      "Ambiguous. Use publicStatusForReady(context). Never print READY as a stamp.",
  },
];

export const DICTIONARY: readonly DictionaryRow[] = ROWS;

const ALIAS_TO_INTERNAL: Record<string, string> = {
  "decision 8": "Decision 8",
  d8: "Decision 8",
  decision8: "Decision 8",
  "decision 8 (d8)": "Decision 8",
  q_a: "q_A",
  qa: "q_A",
  "historical quantile position": "q_A",
  s: "S",
  observed_spread: "S",
  "normalized spread": "S",
  hazard_spread: "S",
  "decision 8 floor": "Decision 8 floor",
  "d8 floor": "Decision 8 floor",
  "policy floor": "Decision 8 floor",
  floor: "Decision 8 floor",
  "0.10": "Decision 8 floor",
  full_reference: "FULL_REFERENCE",
  insufficient_evidence: "INSUFFICIENT_EVIDENCE",
  "insufficient evidence": "INSUFFICIENT_EVIDENCE",
  d8_insufficient: "INSUFFICIENT_EVIDENCE",
  thermal_spatial_differentiation_insufficient: "INSUFFICIENT_EVIDENCE",
  insufficient: "INSUFFICIENT_EVIDENCE",
  sufficient: "SUFFICIENT",
  thermal_ordering_permitted: "SUFFICIENT",
  zonefeaturevector: "ZoneFeatureVector",
  graph_populated: "GRAPH_POPULATED",
  "evidence dag": "GRAPH_POPULATED",
  evidence_graph: "GRAPH_POPULATED",
  "evidence graph": "GRAPH_POPULATED",
  "intervention priority": "INTERVENTION PRIORITY",
  "contextual preparedness priority": "INTERVENTION PRIORITY",
  "contextual preparedness priority — thermal differentiation unavailable":
    "INTERVENTION PRIORITY",
  backend_order: "backend order",
  "backend-order": "backend order",
  ready: "READY",
};

function normalizeKey(value: string): string {
  return value.trim().toLowerCase();
}

export function lookup(internal: string): DictionaryRow | undefined {
  const key = normalizeKey(internal);
  const canonical = ALIAS_TO_INTERNAL[key] ?? internal.trim();
  return ROWS.find(
    (row) =>
      row.internal === canonical || normalizeKey(row.internal) === key,
  );
}

export type ReadyContext =
  | "ranking_permitted"
  | "ranking_withheld"
  | "job_complete"
  | "historical_reference"
  | "snapshot_unavailable"
  | "source_replay";

export function publicStatusForReady(context: ReadyContext): PublicStatus {
  switch (context) {
    case "ranking_permitted":
      return PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED;
    case "ranking_withheld":
      return PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD;
    case "job_complete":
      return PUBLIC_STATUS.ANALYSIS_COMPLETE;
    case "historical_reference":
      return PUBLIC_STATUS.HISTORICAL_REFERENCE_AVAILABLE;
    case "snapshot_unavailable":
      return PUBLIC_STATUS.SNAPSHOT_UNAVAILABLE;
    case "source_replay":
      return PUBLIC_STATUS.REPLAY_EVIDENCE;
  }
}

export function publicStatusForRankingState(
  state: "READY" | "INSUFFICIENT_EVIDENCE",
): PublicStatus {
  return state === "READY"
    ? PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED
    : PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD;
}

/** Bare READY has no public stamp. Call publicStatusForReady instead. */
export function canonicalPublicStatus(internal: string): PublicStatus | null {
  const row = lookup(internal);
  if (row?.internal === "READY") {
    return null;
  }
  if (row?.publicStatus) {
    return row.publicStatus;
  }
  const key = normalizeKey(internal);
  if (key === "complete" || key === "partial") {
    return PUBLIC_STATUS.ANALYSIS_COMPLETE;
  }
  if (key === "replay") {
    return PUBLIC_STATUS.REPLAY_EVIDENCE;
  }
  if (
    key === "snapshot_unavailable" ||
    key === "not on this surface" ||
    key === "not_on_this_surface"
  ) {
    return PUBLIC_STATUS.SNAPSHOT_UNAVAILABLE;
  }
  return null;
}

export function publicPrimaryLabel(internal: string): string | null {
  const row = lookup(internal);
  if (!row) {
    return null;
  }
  if (row.surface === "never" || row.surface === "remove") {
    return null;
  }
  if (row.surface === "technical_details") {
    return null;
  }
  if (row.gate === "ordering_allowed") {
    return null;
  }
  return row.publicLabel;
}

export function technicalDetailsLabel(internal: string): string | null {
  const row = lookup(internal);
  if (!row || row.surface === "never" || row.surface === "remove") {
    return null;
  }
  return row.publicLabel;
}

export function neverShow(internal: string): boolean {
  return lookup(internal)?.surface === "never";
}

export function removeFromPrimary(internal: string): boolean {
  const surface = lookup(internal)?.surface;
  return surface === "remove" || surface === "never";
}

export function relativeOrderLabel(input: {
  orderingAllowed: boolean;
  useful: boolean;
  order?: number;
  of?: number;
}): string | null {
  if (!input.orderingAllowed || !input.useful) {
    return null;
  }
  if (input.order != null && input.of != null) {
    return `Relative order ${input.order} of ${input.of} within this analysis`;
  }
  return PUBLIC_NOUN.BACKEND_ORDER;
}

export function shippedAliasForPublicStatus(
  status: PublicStatus,
): string | null {
  if (status === PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED) {
    return SHIPPED_ALIAS.ORDER_SHOWN;
  }
  if (status === PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD) {
    return SHIPPED_ALIAS.ORDER_WITHHELD;
  }
  return null;
}

/**
 * Terms that must not appear as primary result / map / happening stamps.
 * Capability expansion may name HeatDose / WBGT / AfterHeat only as unpublished modules.
 */
export const FORBIDDEN_PRIMARY_TERMS = [
  "READY",
  "INTERVENTION PRIORITY",
  "CONTEXTUAL PREPAREDNESS PRIORITY",
  "backend order",
  "backend_order",
  "ZoneFeatureVector",
  "GRAPH_POPULATED",
  "Evidence DAG",
  "INSUFFICIENT_EVIDENCE",
  "INSUFFICIENT EVIDENCE",
  "FULL_REFERENCE",
  "q_A",
  "Decision 8",
  "D8",
  "S =",
  "FortyGuard",
  "historical quantile position",
  "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT",
  "TOP3_BOTTOM3",
  "low risk",
  "all-clear",
  "this place is fine",
  "chance of harm",
  "city-wide",
  "real-time",
  "current conditions",
  "current risk",
  "overnight recovery",
  "failed recovery",
] as const;

export const FORBIDDEN_CLAIM_PHRASES = [
  "intervention priority",
  "preparedness priority",
  "equal priority",
  "low risk",
  "low-risk",
  "all-clear",
  "all clear",
  "this place is fine",
  "chance of harm",
  "first to treat",
  "certified cooling",
  "city-wide",
  "citywide",
  "real-time",
  "realtime",
  "current conditions",
  "current risk",
  "overnight recovery",
  "failed recovery",
  "safe-dose",
  "personal dose",
  "harm reduction",
  "efficacy",
  "dispatch",
  "deploy automatically",
  "hottest",
  "combined score",
  "fortyguard",
] as const;

/** Allowed only as gated capability names with blocked / development maturity. No number. */
export const QUALIFIED_CAPABILITY_NOUNS = [
  "HeatDose",
  "AfterHeat",
  "WBGT",
  "Calibrated Probability",
] as const;

const DENIAL_OK: Record<string, readonly string[]> = {
  probability: ["not a probability", "not a chance", "numeric blocked"],
  risk: ["not treated as safe", "not a safety", "not a safety clearance"],
  recovery: ["not a recovery score"],
  forecast: ["not a forecast", "live now, forecast, or overnight"],
  overnight: ["live now, forecast, or overnight", "not a recovery"],
};

export function chromeUsesForbiddenPrimary(
  blob: string,
  term: string,
): boolean {
  if (term === "READY") {
    return /\bREADY\b/.test(blob) && !blob.includes("ALREADY");
  }
  if (!blob.includes(term)) {
    return false;
  }
  const lower = blob.toLowerCase();
  const key = term.toLowerCase();
  const exceptions = DENIAL_OK[key];
  if (exceptions?.some((phrase) => lower.includes(phrase))) {
    return false;
  }
  if (
    term === "chance of harm" &&
    blob.includes("not a chance of harm")
  ) {
    return false;
  }
  return true;
}

export type ScanNote = {
  term: string;
  verdict: "remove" | "qualify" | "deny-only" | "absent" | "code-not-ui";
  note: string;
};

export const SCAN_NOTES: readonly ScanNote[] = [
  {
    term: "intervention priority",
    verdict: "remove",
    note: "mapLayer.ts DEFAULT_MAP_LAYER is the public nighttime-pattern title. INTERVENTION PRIORITY must not return as a default.",
  },
  {
    term: "priority",
    verdict: "qualify",
    note: "Action copy may say do not use ranking for zone prioritization. Never claim INTERVENTION / preparedness / equal priority.",
  },
  {
    term: "risk",
    verdict: "deny-only",
    note: "low risk / current risk are forbidden claims. Withhold is not safe. Denial language only.",
  },
  {
    term: "danger",
    verdict: "absent",
    note: "No danger string in JudgeShell apps/web/src. Do not add. Legend must not say safe ↔ danger.",
  },
  {
    term: "probability",
    verdict: "deny-only",
    note: "q_A is not a probability. Capability module is numeric BLOCKED. Overlay may deny probability. Never print a percent chance.",
  },
  {
    term: "real-time",
    verdict: "deny-only",
    note: "Forbidden as a claim. Surface is replay. Chip may say not live.",
  },
  {
    term: "current",
    verdict: "qualify",
    note: "Not current conditions / not now is allowed. TimelineBar Current/Forecast/Scenario/Overnight is Command Center leftover; JudgeShell does not mount it. Do not restore as live tabs.",
  },
  {
    term: "city-wide",
    verdict: "deny-only",
    note: "25-zone analysis window is not the municipality. Denial only.",
  },
  {
    term: "forecast",
    verdict: "deny-only",
    note: "Allowed only in What evidence does not. Operational (0–12h) is not a forecast.",
  },
  {
    term: "overnight",
    verdict: "qualify",
    note: "03:00 historical comparison is not overnight recovery. AfterHeat is unpublished. Fake Overnight tab is not on JudgeShell.",
  },
  {
    term: "recovery",
    verdict: "qualify",
    note: "Job resubmit (CSS judge-recovery, recoveryHint) is orchestration, not thermal recovery. AfterHeat is not a recovery score. ZoneFeatureVector.recovery_score is never shown.",
  },
  {
    term: "WBGT",
    verdict: "qualify",
    note: "Capability name only. INTEGRATION PATHWAY / BLOCKED inputs. No number. Will not approximate from temperature alone.",
  },
  {
    term: "HeatDose",
    verdict: "qualify",
    note: "Capability name only. ANALYTICAL DEVELOPMENT. No number, curve, or gauge. Not personal burden.",
  },
];
