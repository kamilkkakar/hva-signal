import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { presentActionFraming } from "../action/framing";
import {
  AWAITING_DOES_NOT,
  AWAITING_HEADLINE,
  AWAITING_SUMMARY,
  AWAITING_SUPPORTS,
  CONTEXT_CLOCK,
  CONTEXT_CLOCK_LABEL,
  CONTEXT_HISTORY,
  CONTEXT_HISTORY_LABEL,
  CONTEXT_ZONES,
  CONTEXT_ZONES_LABEL,
  FAILED_DOES_NOT,
  FAILED_HEADLINE,
  FAILED_SUMMARY,
  FAILED_SUPPORTS,
  HOW_DIFF_SUPPORTED,
  HOW_DIFF_UNEVALUATED,
  HOW_DIFF_WITHHELD,
  HOW_HISTORY,
  INSUFFICIENT_DOES_NOT,
  INSUFFICIENT_HEADLINE,
  INSUFFICIENT_SUMMARY,
  INSUFFICIENT_SUPPORTS,
  NOT_EVALUATED_DOES_NOT,
  NOT_EVALUATED_HEADLINE,
  NOT_EVALUATED_SUMMARY,
  NOT_EVALUATED_SUPPORTS,
  STAMP_AWAITING,
  STAMP_FAILED,
  STAMP_NOT_EVALUATED,
  STAMP_SUPPORTED,
  STAMP_WITHHELD,
  SUFFICIENT_DOES_NOT,
  SUFFICIENT_HEADLINE,
  SUFFICIENT_SUMMARY,
  SUFFICIENT_SUPPORTS,
} from "./copy";
import { formatPublicFloor, formatPublicSeparation } from "./precision";
import type { HowDeterminedView, ResultStoryKind, ResultStoryView } from "./types";

const KEY_CONTEXT = [
  { label: CONTEXT_ZONES_LABEL, value: CONTEXT_ZONES },
  { label: CONTEXT_CLOCK_LABEL, value: CONTEXT_CLOCK },
  { label: CONTEXT_HISTORY_LABEL, value: CONTEXT_HISTORY },
] as const;

function howFor(
  kind: ResultStoryKind,
  observed: string | null,
  floor: string | null,
): HowDeterminedView {
  const spatialDifferentiation =
    kind === "sufficient"
      ? HOW_DIFF_SUPPORTED
      : kind === "insufficient"
        ? HOW_DIFF_WITHHELD
        : HOW_DIFF_UNEVALUATED;
  return {
    historicalComparison: HOW_HISTORY,
    spatialDifferentiation,
    observedSeparation: kind === "sufficient" || kind === "insufficient" ? observed : null,
    minimumSeparation: kind === "sufficient" || kind === "insufficient" ? floor : null,
  };
}

function storyFor(
  kind: ResultStoryKind,
  observed: string | null,
  floor: string | null,
): ResultStoryView {
  const how = howFor(kind, observed, floor);
  const context = [...KEY_CONTEXT];
  switch (kind) {
    case "sufficient":
      return {
        kind,
        stamp: STAMP_SUPPORTED,
        headline: SUFFICIENT_HEADLINE,
        summary: SUFFICIENT_SUMMARY,
        context,
        supports: SUFFICIENT_SUPPORTS,
        doesNotEstablish: SUFFICIENT_DOES_NOT,
        how,
      };
    case "insufficient":
      return {
        kind,
        stamp: STAMP_WITHHELD,
        headline: INSUFFICIENT_HEADLINE,
        summary: INSUFFICIENT_SUMMARY,
        context,
        supports: INSUFFICIENT_SUPPORTS,
        doesNotEstablish: INSUFFICIENT_DOES_NOT,
        how,
      };
    case "awaiting":
      return {
        kind,
        stamp: STAMP_AWAITING,
        headline: AWAITING_HEADLINE,
        summary: AWAITING_SUMMARY,
        context,
        supports: AWAITING_SUPPORTS,
        doesNotEstablish: AWAITING_DOES_NOT,
        how,
      };
    case "failed":
      return {
        kind,
        stamp: STAMP_FAILED,
        headline: FAILED_HEADLINE,
        summary: FAILED_SUMMARY,
        context,
        supports: FAILED_SUPPORTS,
        doesNotEstablish: FAILED_DOES_NOT,
        how,
      };
    case "not_evaluated":
      return {
        kind,
        stamp: STAMP_NOT_EVALUATED,
        headline: NOT_EVALUATED_HEADLINE,
        summary: NOT_EVALUATED_SUMMARY,
        context,
        supports: NOT_EVALUATED_SUPPORTS,
        doesNotEstablish: NOT_EVALUATED_DOES_NOT,
        how,
      };
  }
}

export function presentResultStory(input: {
  snapshot: AnalysisJobPayload | null;
  busy?: boolean;
}): ResultStoryView {
  const snapshot = input.snapshot;
  const status = snapshot?.status ?? null;
  const spread = snapshot?.result?.hazard_spread;
  const observed = formatPublicSeparation(spread?.observed_spread);
  const floor = formatPublicFloor(spread?.floor ?? 0.1);

  if (status === "failed") {
    return storyFor("failed", observed, floor);
  }

  const framing = presentActionFraming({
    status: input.busy && status == null ? "queued" : status,
    result: snapshot?.result ?? null,
  });

  if (framing.kind === "sufficient") {
    return storyFor("sufficient", observed, floor);
  }
  if (framing.kind === "insufficient") {
    return storyFor("insufficient", observed, floor);
  }
  if (framing.kind === "awaiting" || input.busy) {
    return storyFor("awaiting", observed, floor);
  }
  return storyFor("not_evaluated", observed, floor);
}
