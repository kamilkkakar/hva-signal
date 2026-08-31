import type {
  ContextComparison,
  DominantPatternId,
  NarrativeSynthesisInput,
} from "./types";

const TEMPORAL_MEANINGFUL_C = 0.5;

export function formatDeltaPhrase(value: number): string {
  const abs = Math.abs(value).toFixed(2);
  if (value > 0) {
    return `${abs} °C higher`;
  }
  if (value < 0) {
    return `${abs} °C lower`;
  }
  return "essentially unchanged (°C)";
}

export function matchedMovedWithGeography(
  local: number | null,
  median: number | null,
  toleranceC = 0.35,
): boolean {
  if (local == null || median == null) {
    return false;
  }
  return Math.abs(local - median) <= toleranceC;
}

export function interpretContextFact(input: {
  kind: string;
  comparison: "higher" | "lower" | "similar" | null;
  comparisonAllowed: boolean;
}): { tone: ContextComparison["tone"]; interpretation: string | null } {
  if (!input.comparisonAllowed || input.comparison == null) {
    return {
      tone: "uncertain",
      interpretation: "Estimate shown with uncertainty; a geography comparison is not published.",
    };
  }
  if (input.kind === "canopy_cover_share") {
    if (input.comparison === "higher") {
      return {
        tone: "weaken",
        interpretation:
          "This does not support a simple low-canopy explanation for the selected thermal pattern.",
      };
    }
    if (input.comparison === "lower") {
      return {
        tone: "complicate",
        interpretation:
          "Lower canopy may warrant shade and exposure follow-up alongside thermal evidence.",
      };
    }
    return {
      tone: "neutral",
      interpretation: "Canopy is similar to the analysis-geography median.",
    };
  }
  if (input.kind === "share_pre_1980_housing") {
    if (input.comparison === "higher") {
      return {
        tone: "complicate",
        interpretation: "Older housing stock may warrant additional exposure investigation.",
      };
    }
    return {
      tone: "neutral",
      interpretation: null,
    };
  }
  if (input.kind === "median_household_income") {
    if (input.comparison === "lower") {
      return {
        tone: "complicate",
        interpretation: "Income context may complicate a purely thermal reading of local conditions.",
      };
    }
    return { tone: "neutral", interpretation: null };
  }
  return { tone: "neutral", interpretation: null };
}

export function resolveDominantPattern(input: NarrativeSynthesisInput): DominantPatternId {
  const hasThermal = input.thermalAvailable && input.selectedTemperatureC != null;
  const hasMatched =
    input.matchedChangeC != null && Number.isFinite(input.matchedChangeC);
  const temporalStrong =
    hasMatched && Math.abs(input.matchedChangeC as number) >= TEMPORAL_MEANINGFUL_C;
  const spatialPresent = input.spatialDiff === "SUFFICIENT";
  const spatialLimited = input.spatialDiff === "INSUFFICIENT";
  const prepGap = input.preparedness === "NOT_IDENTIFIED_IN_DATASET";
  const contextUseful = input.contextComparisons.some(
    (row) => row.comparisonAllowed && row.tone !== "uncertain",
  );

  if (!hasThermal && !hasMatched && !contextUseful && input.preparedness === "UNAVAILABLE") {
    return "INSUFFICIENT_EVIDENCE";
  }
  if (!hasThermal && !hasMatched) {
    if (prepGap) {
      return "PREPAREDNESS_GAP_REQUIRES_VERIFICATION";
    }
    if (contextUseful) {
      return "CONTEXT_WARRANTS_INVESTIGATION";
    }
    return "INSUFFICIENT_EVIDENCE";
  }
  if (spatialPresent && !temporalStrong) {
    return "SPATIAL_DIFFERENTIATION_PRESENT";
  }
  if (temporalStrong && (spatialLimited || input.spatialDiff === "UNKNOWN")) {
    return "TEMPORAL_CHANGE_DOMINATES";
  }
  if (temporalStrong && spatialPresent) {
    // Prefer temporal when matched change is meaningful and geography median tracks it.
    if (matchedMovedWithGeography(input.matchedChangeC, input.geographyMedianChangeC)) {
      return "TEMPORAL_CHANGE_DOMINATES";
    }
    return "SPATIAL_DIFFERENTIATION_PRESENT";
  }
  if (spatialLimited) {
    return "SPATIAL_DIFFERENTIATION_LIMITED";
  }
  if (prepGap && !temporalStrong && !spatialPresent) {
    return "PREPAREDNESS_GAP_REQUIRES_VERIFICATION";
  }
  if (contextUseful && !temporalStrong && !spatialPresent) {
    return "CONTEXT_WARRANTS_INVESTIGATION";
  }
  if (!hasThermal && !hasMatched) {
    return "INSUFFICIENT_EVIDENCE";
  }
  return spatialLimited ? "SPATIAL_DIFFERENTIATION_LIMITED" : "INSUFFICIENT_EVIDENCE";
}

export const PATTERN_COPY: Record<
  DominantPatternId,
  { title: string; payAttention: string }
> = {
  TEMPORAL_CHANGE_DOMINATES: {
    title: "Temporal change is stronger than spatial separation",
    payAttention:
      "Matched nighttime conditions differ across years more than areas differ at the selected observation.",
  },
  SPATIAL_DIFFERENTIATION_PRESENT: {
    title: "Spatial differentiation is present",
    payAttention:
      "Thermal differences across analysis areas are large enough to support a spatial comparison for this observation.",
  },
  SPATIAL_DIFFERENTIATION_LIMITED: {
    title: "Spatial differentiation is limited",
    payAttention:
      "Differences across analysis areas at the selected observation are too small to support a defensible ranking.",
  },
  CONTEXT_WARRANTS_INVESTIGATION: {
    title: "Context warrants further investigation",
    payAttention:
      "Thermal ranking is not the primary story; local context raises a useful investigation question.",
  },
  PREPAREDNESS_GAP_REQUIRES_VERIFICATION: {
    title: "Preparedness gap requires verification",
    payAttention:
      "No heat-relief site is identified in the available inventory — verify access on the ground.",
  },
  INSUFFICIENT_EVIDENCE: {
    title: "Evidence is insufficient for a thermal story",
    payAttention:
      "Available evidence does not support a defensible thermal ranking or temporal-change claim for this case.",
  },
};
