import {
  BODY_FAILED,
  BODY_HISTORY_NOT_PREPARED,
  BODY_HISTORY_TOO_THIN,
  BODY_IDLE,
  BODY_LOADING,
  BODY_NOT_REQUESTED,
  BODY_ORDER_SHOWN,
  BODY_ORDER_WITHHELD,
  BODY_PENDING,
  FEATURE_WITHHOLD,
  FORBIDDEN_CHROME_METHOD,
  MAP_LAYER_ORDER_SHOWN,
  MAP_LAYER_ORDER_WITHHELD,
  METHOD_D8,
  METHOD_QA,
  METHOD_S,
  METHOD_TITLE,
  OVERLAY_HISTORY_LOCK,
  OVERLAY_IDLE,
  OVERLAY_LOADING,
  OVERLAY_ORDER_SHOWN,
  OVERLAY_ORDER_WITHHELD,
  RAIL_FAILED,
  RAIL_HISTORY_LOCK,
  RAIL_IDLE,
  RAIL_LOADING,
  RAIL_NOT_REQUESTED,
  RAIL_ORDER_SHOWN,
  RAIL_ORDER_WITHHELD,
  RAIL_PENDING,
  SIGA_ASSISTIVE_MAP,
  SIGA_CHIP,
  SIGA_CLOCK,
  SIGA_GEOGRAPHY,
  SIGA_INDEPENDENCE,
  SIGA_ONE_SENTENCE,
  SIGA_QUESTION_GATE,
  SIGA_QUESTION_PRIMARY,
  SIGA_TITLE,
  STAMP_FAILED,
  STAMP_HISTORY_NOT_PREPARED,
  STAMP_HISTORY_TOO_THIN,
  STAMP_NOT_REQUESTED,
  STAMP_ORDER_SHOWN,
  STAMP_ORDER_WITHHELD,
  STAMP_PENDING,
  formatOrderHover,
} from "./copy";
import type { SignalAInput, SignalAKind, SignalATone, SignalAView } from "./types";
import { SIGNAL_A_ZONE_COUNT } from "./types";

const IN_FLIGHT = new Set([
  "queued",
  "loading_context",
  "fetching_thermal",
  "assembling_partitions",
  "aggregating_zones",
  "normalizing",
  "validating_hazard_spread",
  "computing",
]);

const METHOD = {
  title: METHOD_TITLE,
  q_A: METHOD_QA,
  decision8: METHOD_D8,
  S: METHOD_S,
} as const;

function resolveKind(input: SignalAInput): SignalAKind {
  if (input.kind) {
    return input.kind;
  }
  if (input.failed === true || input.jobStatus === "failed") {
    return "failed";
  }
  if (input.requested === false) {
    return "not_requested";
  }
  if (input.historyPrepared === false) {
    return "history_not_prepared";
  }
  if (
    input.historyTooThin === true ||
    input.limitations?.includes("INSUFFICIENT_REFERENCE")
  ) {
    return "history_too_thin";
  }
  if (input.jobStatus != null && IN_FLIGHT.has(input.jobStatus)) {
    return "pending";
  }
  const state = input.differentiationState?.toUpperCase() ?? null;
  if (state === "INSUFFICIENT") {
    return "order_withheld";
  }
  if (state === "SUFFICIENT" && input.orderingPermitted !== false) {
    return "order_shown";
  }
  if (input.hasResult === false && input.jobStatus === "loading") {
    return "loading";
  }
  if (
    input.hasResult === true &&
    state == null &&
    (input.referenceQuality == null || input.referenceQuality === "")
  ) {
    return "history_not_prepared";
  }
  return "idle";
}

function toneFor(kind: SignalAKind): SignalATone {
  switch (kind) {
    case "order_shown":
      return "shown";
    case "order_withheld":
      return "withheld";
    case "history_not_prepared":
    case "history_too_thin":
      return "not-prepared";
    case "failed":
      return "failed";
    case "pending":
    case "loading":
      return "pending";
    default:
      return "inert";
  }
}

function stampFor(kind: SignalAKind): string | null {
  switch (kind) {
    case "order_shown":
      return STAMP_ORDER_SHOWN;
    case "order_withheld":
      return STAMP_ORDER_WITHHELD;
    case "history_not_prepared":
      return STAMP_HISTORY_NOT_PREPARED;
    case "history_too_thin":
      return STAMP_HISTORY_TOO_THIN;
    case "not_requested":
      return STAMP_NOT_REQUESTED;
    case "pending":
      return STAMP_PENDING;
    case "failed":
      return STAMP_FAILED;
    default:
      return null;
  }
}

function railFor(kind: SignalAKind): string {
  switch (kind) {
    case "order_shown":
      return RAIL_ORDER_SHOWN;
    case "order_withheld":
      return RAIL_ORDER_WITHHELD;
    case "history_not_prepared":
    case "history_too_thin":
      return RAIL_HISTORY_LOCK;
    case "not_requested":
      return RAIL_NOT_REQUESTED;
    case "pending":
      return RAIL_PENDING;
    case "failed":
      return RAIL_FAILED;
    case "loading":
      return RAIL_LOADING;
    default:
      return RAIL_IDLE;
  }
}

function bodyFor(kind: SignalAKind): string {
  switch (kind) {
    case "order_shown":
      return BODY_ORDER_SHOWN;
    case "order_withheld":
      return BODY_ORDER_WITHHELD;
    case "history_not_prepared":
      return BODY_HISTORY_NOT_PREPARED;
    case "history_too_thin":
      return BODY_HISTORY_TOO_THIN;
    case "not_requested":
      return BODY_NOT_REQUESTED;
    case "pending":
      return BODY_PENDING;
    case "failed":
      return BODY_FAILED;
    case "loading":
      return BODY_LOADING;
    default:
      return BODY_IDLE;
  }
}

function mapLayerTitleFor(kind: SignalAKind): string {
  if (kind === "order_shown") {
    return MAP_LAYER_ORDER_SHOWN;
  }
  if (kind === "order_withheld") {
    return MAP_LAYER_ORDER_WITHHELD;
  }
  return SIGA_ASSISTIVE_MAP;
}

function mapOverlayFor(kind: SignalAKind): string {
  switch (kind) {
    case "order_shown":
      return OVERLAY_ORDER_SHOWN;
    case "order_withheld":
      return OVERLAY_ORDER_WITHHELD;
    case "history_not_prepared":
    case "history_too_thin":
      return OVERLAY_HISTORY_LOCK;
    case "loading":
      return OVERLAY_LOADING;
    default:
      return OVERLAY_IDLE;
  }
}

function geographyReady(kind: SignalAKind, requested: boolean | undefined): boolean {
  if (requested === false || kind === "not_requested" || kind === "idle") {
    return false;
  }
  return (
    kind === "order_shown" ||
    kind === "order_withheld" ||
    kind === "history_not_prepared" ||
    kind === "history_too_thin" ||
    kind === "pending" ||
    kind === "failed" ||
    requested === true
  );
}

export function signalAHoverLine(input: {
  kind: SignalAKind;
  zoneId: string;
  order: number;
}): string | null {
  if (input.kind !== "order_shown") {
    return null;
  }
  return formatOrderHover(input.zoneId, input.order);
}

export function presentSignalA(input: SignalAInput = {}): SignalAView {
  const kind = resolveKind(input);
  const hoverEnabled = kind === "order_shown";
  const ready = geographyReady(kind, input.requested);
  const hoverLine =
    hoverEnabled && input.zoneId != null && input.order != null
      ? formatOrderHover(input.zoneId, input.order)
      : null;

  return {
    kind,
    stamp: stampFor(kind),
    tone: toneFor(kind),
    title: SIGA_TITLE,
    chip: SIGA_CHIP,
    questionPrimary: SIGA_QUESTION_PRIMARY,
    questionGate: SIGA_QUESTION_GATE,
    oneSentence: SIGA_ONE_SENTENCE,
    independence: SIGA_INDEPENDENCE,
    clock: SIGA_CLOCK,
    geography: SIGA_GEOGRAPHY,
    railSentence: railFor(kind),
    body: bodyFor(kind),
    featureLine: kind === "order_withheld" ? FEATURE_WITHHOLD : null,
    mapLayerTitle: mapLayerTitleFor(kind),
    mapOverlay: mapOverlayFor(kind),
    hoverLine,
    hoverEnabled,
    outlineCount: ready ? SIGNAL_A_ZONE_COUNT : 0,
    rankedFillCount: kind === "order_shown" ? SIGNAL_A_ZONE_COUNT : 0,
    assistiveMapName: SIGA_ASSISTIVE_MAP,
    doesNotBlockSignalB: true,
    insufficientIsFeature: kind === "order_withheld",
    method: { ...METHOD },
  };
}

export function judgeChromeStrings(view: SignalAView): string[] {
  return [
    view.stamp ?? "",
    view.mapLayerTitle,
    view.mapOverlay,
    view.railSentence,
    view.hoverLine ?? "",
    view.questionPrimary,
    view.questionGate,
    view.oneSentence,
    view.chip,
    view.title,
    view.body,
    view.featureLine ?? "",
    view.clock,
    view.geography,
    view.independence,
  ];
}

export function chromeLeaksMethod(view: SignalAView): boolean {
  const blob = judgeChromeStrings(view).join("\n");
  return FORBIDDEN_CHROME_METHOD.some((token) => blob.includes(token));
}
