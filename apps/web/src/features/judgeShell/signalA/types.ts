/** Isolated Signal A judge view. Does not compute q_A, Decision 8, or S. */

export const SIGNAL_A_ZONE_COUNT = 25 as const;

export type SignalAKind =
  | "idle"
  | "loading"
  | "not_requested"
  | "history_not_prepared"
  | "history_too_thin"
  | "pending"
  | "order_shown"
  | "order_withheld"
  | "failed";

export type SignalATone =
  | "inert"
  | "pending"
  | "shown"
  | "withheld"
  | "not-prepared"
  | "failed";

export type SignalAInput = {
  kind?: SignalAKind;
  requested?: boolean;
  jobStatus?: string | null;
  hasResult?: boolean;
  failed?: boolean;
  historyPrepared?: boolean;
  historyTooThin?: boolean;
  /** Existing Decision 8 outcome. Read, do not compute. */
  differentiationState?: string | null;
  /** Existing per-zone authorize bits. Read, do not compute. */
  orderingPermitted?: boolean | null;
  limitations?: readonly string[] | null;
  referenceQuality?: string | null;
  zoneId?: string;
  order?: number;
};

export type SignalAMethodView = {
  title: string;
  q_A: string;
  decision8: string;
  S: string;
};

export type SignalAView = {
  kind: SignalAKind;
  stamp: string | null;
  tone: SignalATone;
  title: string;
  chip: string;
  questionPrimary: string;
  questionGate: string;
  oneSentence: string;
  independence: string;
  clock: string;
  geography: string;
  railSentence: string;
  body: string;
  featureLine: string | null;
  mapLayerTitle: string;
  mapOverlay: string;
  hoverLine: string | null;
  hoverEnabled: boolean;
  outlineCount: number;
  rankedFillCount: number;
  assistiveMapName: string;
  doesNotBlockSignalB: true;
  insufficientIsFeature: boolean;
  method: SignalAMethodView;
};
