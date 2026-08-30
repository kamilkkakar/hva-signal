/** Bind-only historical-position figures. Does not compute q_A, Decision 8, or S. */

export type OrderingComparisonState = "supported" | "withheld" | "unavailable";

export type HistoricalPositionMark = {
  zoneId: string;
  /** Existing zone q_A on the frozen 0–1 scale. Read, never computed. */
  position: number;
};

export type HistoricalPositionInput = {
  marks: HistoricalPositionMark[];
  comparison: OrderingComparisonState;
  selectedZoneId: string | null;
  historicalYears: readonly number[] | null;
  referenceHour: string | null;
};

export type HistoricalPositionView = {
  visible: boolean;
  marks: HistoricalPositionMark[];
  comparison: OrderingComparisonState;
  comparisonStamp: string | null;
  selected: HistoricalPositionMark | null;
  /** Exact q_A for details only. Never chrome. */
  selectedExact: string | null;
  axisLow: string;
  axisHigh: string;
  meaning: string;
  frameCaption: string | null;
  assistive: string;
  selectedAssistive: string | null;
};
