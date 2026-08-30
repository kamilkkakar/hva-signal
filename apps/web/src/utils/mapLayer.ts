import type { ZoneDecisionStub } from "@/api/analysisJobs";

export const THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT =
  "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT";

export const INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE";

export const ARCHITECTURE_THERMAL_DIFF_MESSAGE =
  "There is not enough thermal differentiation here to support a spatial thermal-ranking claim.";

export const INSUFFICIENT_REFERENCE_MESSAGE =
  "Required historical reference is incomplete. Thermal ordering is not evaluated. This is not a Decision 8 thermal-differentiation fallback.";

export const DEFAULT_MAP_LAYER = "Nighttime historical thermal pattern";

export const CONTEXTUAL_MAP_LAYER = "Nighttime historical thermal pattern";

export type MapLayerState = {
  label: string;
  message: string | null;
  allowPriorityChoropleth: boolean;
};

export function mapLayerFromLimitations(
  limitations: readonly string[],
): MapLayerState {
  if (limitations.includes(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT)) {
    return {
      label: CONTEXTUAL_MAP_LAYER,
      message: ARCHITECTURE_THERMAL_DIFF_MESSAGE,
      allowPriorityChoropleth: false,
    };
  }
  if (limitations.includes(INSUFFICIENT_REFERENCE)) {
    return {
      label: "THERMAL ORDERING NOT SUPPORTED",
      message: INSUFFICIENT_REFERENCE_MESSAGE,
      allowPriorityChoropleth: false,
    };
  }
  return {
    label: DEFAULT_MAP_LAYER,
    message: null,
    allowPriorityChoropleth: true,
  };
}

export type RankingPresentation = {
  state: "INSUFFICIENT_EVIDENCE" | "READY";
  scores: never[];
};

export function rankingPresentation(
  zones: ZoneDecisionStub[] | null | undefined,
): RankingPresentation {
  if (!zones || zones.length === 0 || !zones.some((zone) => zone.ranked)) {
    return { state: "INSUFFICIENT_EVIDENCE", scores: [] };
  }
  // Never invent a choropleth or rank order here. Agent I / geometry come later.
  return { state: "READY", scores: [] };
}
