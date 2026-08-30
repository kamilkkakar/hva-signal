import type { AnalysisResultStub } from "@/api/analysisJobs";
import { presentThermalA } from "@/features/selectedAreaStory/thermalA";
import { HISTORY_UNAVAILABLE, HISTORY_WITHHELD, historicalPositionSentence } from "./copy";

export type HistoricalPositionView = {
  sentence: string;
  percent: number | null;
  withheld: boolean;
};

export function presentHistoricalHero(
  result: AnalysisResultStub | null | undefined,
  geoid: string | null,
): HistoricalPositionView {
  const pane = presentThermalA(result, geoid);
  if (pane.kind === "order_withheld") {
    return { sentence: HISTORY_WITHHELD, percent: null, withheld: true };
  }
  if (pane.kind === "order_shown" && pane.q_A != null) {
    return {
      sentence: historicalPositionSentence(pane.q_A),
      percent: Math.round(pane.q_A * 100),
      withheld: false,
    };
  }
  return { sentence: HISTORY_UNAVAILABLE, percent: null, withheld: false };
}
