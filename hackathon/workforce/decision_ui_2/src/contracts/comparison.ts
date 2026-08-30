import type { AnalysisAreaId } from "./analysisArea";

export type ComparisonSlot = {
  readonly role: "focus" | "peer";
  readonly areaId: AnalysisAreaId | null;
};

export type ComparisonModel = {
  readonly slots: readonly [ComparisonSlot, ComparisonSlot];
};
