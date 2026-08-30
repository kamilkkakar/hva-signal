import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { shouldContinuePolling } from "@/utils/jobPolling";
import {
  INSUFFICIENT_REFERENCE,
  THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
} from "@/utils/mapLayer";
import {
  SIGNAL_A_KICKER,
  SIGNAL_A_MESSAGE_FAILED,
  SIGNAL_A_MESSAGE_IDLE,
  SIGNAL_A_MESSAGE_NOT_PREPARED,
  SIGNAL_A_MESSAGE_SHOWN,
  SIGNAL_A_MESSAGE_WITHHELD,
  SIGNAL_A_MESSAGE_WORKING,
  SIGNAL_A_QUESTION,
  SIGNAL_A_TITLE,
  SIGNAL_B_KICKER,
  SIGNAL_B_MESSAGE,
  SIGNAL_B_QUESTION,
  SIGNAL_B_STAMP,
  SIGNAL_B_TITLE,
  STAMP_FAILED,
  STAMP_HISTORY_NOT_PREPARED,
  STAMP_NOT_REQUESTED,
  STAMP_ORDER_SHOWN,
  STAMP_ORDER_WITHHELD,
  STAMP_WORKING,
  VALUE_CLOCK,
  VALUE_CLOCK_LABEL,
  VALUE_SOURCE,
  VALUE_SOURCE_LABEL,
  VALUE_SURFACE,
  VALUE_SURFACE_LABEL,
  VALUE_WINDOW,
  VALUE_WINDOW_LABEL,
} from "./copy";
import type { ResultCardModel, ResultCardsView, ResultStamp } from "./types";

const A_VALUES = [
  { label: VALUE_CLOCK_LABEL, value: VALUE_CLOCK },
  { label: VALUE_WINDOW_LABEL, value: VALUE_WINDOW },
  { label: VALUE_SOURCE_LABEL, value: VALUE_SOURCE },
] as const;

const B_VALUES = [{ label: VALUE_SURFACE_LABEL, value: VALUE_SURFACE }] as const;

function signalBCard(): ResultCardModel {
  return {
    id: "b",
    kicker: SIGNAL_B_KICKER,
    title: SIGNAL_B_TITLE,
    question: SIGNAL_B_QUESTION,
    stamp: SIGNAL_B_STAMP,
    message: SIGNAL_B_MESSAGE,
    values: [...B_VALUES],
  };
}

function signalACard(stamp: ResultStamp, message: string): ResultCardModel {
  return {
    id: "a",
    kicker: SIGNAL_A_KICKER,
    title: SIGNAL_A_TITLE,
    question: SIGNAL_A_QUESTION,
    stamp,
    message,
    values: [...A_VALUES],
  };
}

export function resultCardsFromSnapshot(input: {
  snapshot: AnalysisJobPayload | null;
  rankingState: "INSUFFICIENT_EVIDENCE" | "READY";
  busy?: boolean;
}): ResultCardsView {
  const status = input.snapshot?.status ?? null;
  const limitations = input.snapshot?.result?.system_limitations ?? [];
  const b = signalBCard();

  if (status === "failed") {
    return { a: signalACard(STAMP_FAILED, SIGNAL_A_MESSAGE_FAILED), b };
  }
  if (input.busy || shouldContinuePolling(status)) {
    return { a: signalACard(STAMP_WORKING, SIGNAL_A_MESSAGE_WORKING), b };
  }
  if (status == null) {
    return { a: signalACard(STAMP_NOT_REQUESTED, SIGNAL_A_MESSAGE_IDLE), b };
  }
  if (limitations.includes(INSUFFICIENT_REFERENCE)) {
    return {
      a: signalACard(STAMP_HISTORY_NOT_PREPARED, SIGNAL_A_MESSAGE_NOT_PREPARED),
      b,
    };
  }
  if (input.rankingState === "READY") {
    return { a: signalACard(STAMP_ORDER_SHOWN, SIGNAL_A_MESSAGE_SHOWN), b };
  }
  if (
    limitations.includes(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT) ||
    status === "complete" ||
    status === "partial"
  ) {
    return { a: signalACard(STAMP_ORDER_WITHHELD, SIGNAL_A_MESSAGE_WITHHELD), b };
  }
  return { a: signalACard(STAMP_NOT_REQUESTED, SIGNAL_A_MESSAGE_IDLE), b };
}
