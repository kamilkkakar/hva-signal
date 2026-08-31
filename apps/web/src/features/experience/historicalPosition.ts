import type { AnalysisResultStub } from "@/api/analysisJobs";
import { presentThermalA } from "@/features/selectedAreaStory/thermalA";
import {
  HISTORY_UNAVAILABLE,
  HISTORY_UNAVAILABLE_REASON,
  historicalPositionSentence,
  RANKING_SUPPORTED_BODY,
  RANKING_WITHHELD_BODY,
} from "./copy";

export type HistoricalPositionView = {
  status: "available" | "unavailable";
  sentence: string;
  reason: string | null;
  percent: number | null;
};

export type SpatialDifferentiationView = {
  status: "withheld" | "supported" | "unknown";
  sentence: string;
};

/** Own-area historical position — never spatial ranking language. */
export function presentHistoricalPosition(
  result: AnalysisResultStub | null | undefined,
  geoid: string | null,
): HistoricalPositionView {
  const pane = presentThermalA(result, geoid);
  if (pane.kind === "order_shown" && pane.q_A != null) {
    return {
      status: "available",
      sentence: historicalPositionSentence(pane.q_A),
      reason: null,
      percent: Math.round(pane.q_A * 100),
    };
  }
  return {
    status: "unavailable",
    sentence: HISTORY_UNAVAILABLE,
    reason: HISTORY_UNAVAILABLE_REASON,
    percent: null,
  };
}

/** Cross-area spatial differentiation — never own-history percent language. */
export function presentSpatialDifferentiation(
  result: AnalysisResultStub | null | undefined,
  geoid: string | null,
): SpatialDifferentiationView {
  const pane = presentThermalA(result, geoid);
  if (pane.kind === "order_withheld" || pane.decision8 === "INSUFFICIENT") {
    return { status: "withheld", sentence: RANKING_WITHHELD_BODY };
  }
  if (pane.kind === "order_shown" || pane.decision8 === "SUFFICIENT") {
    return { status: "supported", sentence: RANKING_SUPPORTED_BODY };
  }
  return {
    status: "unknown",
    sentence: "Spatial comparison status is not yet available for this observation.",
  };
}

/** @deprecated Prefer presentHistoricalPosition + presentSpatialDifferentiation. */
export function presentHistoricalHero(
  result: AnalysisResultStub | null | undefined,
  geoid: string | null,
): {
  sentence: string;
  percent: number | null;
  withheld: boolean;
} {
  const history = presentHistoricalPosition(result, geoid);
  const spatial = presentSpatialDifferentiation(result, geoid);
  if (spatial.status === "withheld") {
    return { sentence: spatial.sentence, percent: null, withheld: true };
  }
  return {
    sentence: history.sentence,
    percent: history.percent,
    withheld: false,
  };
}
