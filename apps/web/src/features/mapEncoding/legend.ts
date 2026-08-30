import {
  LEGEND_AXIS,
  LEGEND_DENIAL,
  LEGEND_ERROR,
  LEGEND_HATCH_NOTE,
  LEGEND_HIGH_LABEL,
  LEGEND_IDLE,
  LEGEND_INSUFFICIENT,
  LEGEND_LOADING,
  LEGEND_LOW_LABEL,
  SIGNAL_A_INSUFFICIENT_LINE,
  SIGNAL_A_POS_STOPS,
} from "./tokens";

export type LegendMode = "sufficient" | "insufficient" | "idle" | "loading" | "error";

export type LegendHatchSample = {
  id: "low" | "mid" | "high";
  label: string;
};

export type HistoricalPositionLegendView = {
  mode: LegendMode;
  title: string;
  axis: string | null;
  lowLabel: string | null;
  highLabel: string | null;
  denial: string;
  hatchNote: string | null;
  stops: readonly string[];
  hatchSamples: LegendHatchSample[];
  outlineSwatch: string | null;
};

const HATCH_SAMPLES: LegendHatchSample[] = [
  { id: "low", label: "Sparse hatch" },
  { id: "mid", label: "Mid hatch" },
  { id: "high", label: "Dense hatch" },
];

export function historicalPositionLegend(
  mode: LegendMode,
): HistoricalPositionLegendView {
  if (mode === "sufficient") {
    return {
      mode,
      title: "Historical position",
      axis: LEGEND_AXIS,
      lowLabel: LEGEND_LOW_LABEL,
      highLabel: LEGEND_HIGH_LABEL,
      denial: LEGEND_DENIAL,
      hatchNote: LEGEND_HATCH_NOTE,
      stops: SIGNAL_A_POS_STOPS,
      hatchSamples: HATCH_SAMPLES,
      outlineSwatch: null,
    };
  }
  if (mode === "insufficient") {
    return {
      mode,
      title: "Historical position",
      axis: null,
      lowLabel: null,
      highLabel: null,
      denial: LEGEND_INSUFFICIENT,
      hatchNote: null,
      stops: [],
      hatchSamples: [],
      outlineSwatch: SIGNAL_A_INSUFFICIENT_LINE,
    };
  }
  const denial =
    mode === "loading" ? LEGEND_LOADING : mode === "error" ? LEGEND_ERROR : LEGEND_IDLE;
  return {
    mode,
    title: "Historical position",
    axis: null,
    lowLabel: null,
    highLabel: null,
    denial,
    hatchNote: null,
    stops: [],
    hatchSamples: [],
    outlineSwatch: null,
  };
}

/** JudgeMap host. Snapshot B keeps its own chrome. A uses the sequential legend. */
export function legendModeFromInteraction(input: {
  kind: string | null | undefined;
  fillAuthorized: boolean;
  layerActive: boolean;
  fillKind?: string | null;
}): LegendMode | null {
  if (input.fillKind === "context_quantity") {
    return null;
  }
  if (input.kind !== "historical_ordering" && input.kind !== "aoi_outline") {
    return null;
  }
  if (!input.layerActive) {
    return "idle";
  }
  if (input.kind === "historical_ordering" && input.fillAuthorized) {
    return "sufficient";
  }
  return "insufficient";
}

export function legendModeFromMap(input: {
  visualState: "idle" | "loading" | "insufficient" | "sufficient" | "error";
  thermalOrderingVisible: boolean;
}): LegendMode {
  if (input.thermalOrderingVisible) {
    return "sufficient";
  }
  if (input.visualState === "insufficient") {
    return "insufficient";
  }
  if (input.visualState === "loading") {
    return "loading";
  }
  if (input.visualState === "error") {
    return "error";
  }
  return "idle";
}
