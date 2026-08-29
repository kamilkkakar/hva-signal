import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { GeometryBindResult, PresentationCollection } from "./geometryJoin";
import { CONTEXTUAL_MAP_LAYER } from "./mapLayer";

export const CONTEXTUAL_PREPAREDNESS_PRIORITY = CONTEXTUAL_MAP_LAYER;

export const BACKEND_ORDERING_COPY =
  "Fill intensity reflects backend-authorized thermal ordering. Rank is not a probability or heat-severity class.";

export type MapVisualState = "idle" | "loading" | "insufficient" | "sufficient" | "error";

export type MapPresentation = {
  visualState: MapVisualState;
  outlineCount: number;
  rankedFillCount: number;
  thermalOrderingVisible: boolean;
  fallback: string | null;
  message: string | null;
  observedSpread: number | null;
  collection: PresentationCollection;
};

const EMPTY_COLLECTION: PresentationCollection = {
  type: "FeatureCollection",
  features: [],
};

function decision8State(result: AnalysisResultStub | null | undefined): string | null {
  return (
    result?.thermal_differentiation_state ??
    result?.hazard_spread?.differentiation_state ??
    null
  );
}

function thermalOrderingAuthorized(result: AnalysisResultStub): boolean {
  if (decision8State(result) !== "SUFFICIENT") {
    return false;
  }
  const zones = result.zones ?? [];
  if (zones.length === 0) {
    return false;
  }
  return zones.every((zone) => zone.thermal_ordering_permitted === true);
}

export function mapPresentationFromBind(
  bound: GeometryBindResult,
  result: AnalysisResultStub | null | undefined,
): MapPresentation {
  if (!bound.ok || !result) {
    return {
      visualState: "error",
      outlineCount: 0,
      rankedFillCount: 0,
      thermalOrderingVisible: false,
      fallback: null,
      message: bound.ok
        ? "Analysis result is not available for this geometry."
        : bound.reason,
      observedSpread: result?.hazard_spread?.observed_spread ?? null,
      collection: EMPTY_COLLECTION,
    };
  }
  const observedSpread = result.hazard_spread?.observed_spread ?? null;
  if (thermalOrderingAuthorized(result)) {
    return {
      visualState: "sufficient",
      outlineCount: bound.featureCount,
      rankedFillCount: bound.featureCount,
      thermalOrderingVisible: true,
      fallback: null,
      message: BACKEND_ORDERING_COPY,
      observedSpread,
      collection: bound.collection,
    };
  }
  return {
    visualState: "insufficient",
    outlineCount: bound.featureCount,
    rankedFillCount: 0,
    thermalOrderingVisible: false,
    fallback: CONTEXTUAL_PREPAREDNESS_PRIORITY,
    message: CONTEXTUAL_PREPAREDNESS_PRIORITY,
    observedSpread,
    collection: bound.collection,
  };
}

export function emptyMapPresentation(
  visualState: Extract<MapVisualState, "idle" | "loading">,
): MapPresentation {
  return {
    visualState,
    outlineCount: 0,
    rankedFillCount: 0,
    thermalOrderingVisible: false,
    fallback: null,
    message: null,
    observedSpread: null,
    collection: EMPTY_COLLECTION,
  };
}
