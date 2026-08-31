/** Deterministic analytical-story synthesis. No scores. No freeform LLM. */

export type SpatialDiffStatus = "SUFFICIENT" | "INSUFFICIENT" | "UNKNOWN";

export type HistoricalPositionStatus = "AVAILABLE" | "UNAVAILABLE";

export type PreparednessEvidenceStatus =
  | "IDENTIFIED"
  | "NOT_IDENTIFIED_IN_DATASET"
  | "UNKNOWN"
  | "UNAVAILABLE";

export type ContextComparisonTone = "strengthen" | "weaken" | "complicate" | "neutral" | "uncertain";

export type ContextComparison = {
  kind: string;
  label: string;
  valueDisplay: string;
  comparison: "higher" | "lower" | "similar" | null;
  comparisonAllowed: boolean;
  tone: ContextComparisonTone;
  interpretation: string | null;
};

export type DominantPatternId =
  | "TEMPORAL_CHANGE_DOMINATES"
  | "SPATIAL_DIFFERENTIATION_PRESENT"
  | "SPATIAL_DIFFERENTIATION_LIMITED"
  | "CONTEXT_WARRANTS_INVESTIGATION"
  | "PREPAREDNESS_GAP_REQUIRES_VERIFICATION"
  | "INSUFFICIENT_EVIDENCE";

export type EvidenceSignal = {
  id: string;
  label: string;
  value: string;
};

export type NarrativeSynthesisInput = {
  areaLabel: string | null;
  analysisAreaCount: number;
  selectedTemperatureC: number | null;
  observationStamp: string | null;
  spatialDiff: SpatialDiffStatus;
  historicalPosition: {
    status: HistoricalPositionStatus;
    percent: number | null;
    sentence: string;
  };
  matchedChangeC: number | null;
  geographyMedianChangeC: number | null;
  matchedNightsTotal: number | null;
  observedHighC: number | null;
  observedHighLabel: string | null;
  contextComparisons: ContextComparison[];
  preparedness: PreparednessEvidenceStatus;
  thermalAvailable: boolean;
};

export type NarrativeSynthesis = {
  dominantPattern: DominantPatternId;
  patternTitle: string;
  patternSummary: string;
  evidenceSummary: EvidenceSignal[];
  whatEvidenceShows: string[];
  whyItMatters: string[];
  verifyNext: string[];
};
