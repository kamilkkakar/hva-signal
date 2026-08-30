import {
  CONTEXTUAL_MAP_LAYER,
  DEFAULT_MAP_LAYER,
  INSUFFICIENT_REFERENCE_MESSAGE,
  type MapLayerState,
  type RankingPresentation,
} from "@/utils/mapLayer";

export const JUDGE_LAYER_ORDER = "Nighttime historical thermal pattern";
export const JUDGE_LAYER_WITHHELD = "Nighttime historical thermal pattern";
export const JUDGE_LAYER_NOT_PREPARED = "Historical pattern not prepared";
export const JUDGE_LAYER_WINDOW = "25-zone window";

/** Remap intervention/preparedness titles without editing mapLayer.ts. */
export function judgeMapLayer(
  raw: MapLayerState,
  ranking: RankingPresentation,
  hasResult: boolean,
): MapLayerState {
  if (!hasResult) {
    return {
      label: JUDGE_LAYER_WINDOW,
      message: null,
      allowPriorityChoropleth: false,
    };
  }
  if (
    raw.message === INSUFFICIENT_REFERENCE_MESSAGE ||
    raw.label === "THERMAL ORDERING NOT SUPPORTED"
  ) {
    return { ...raw, label: JUDGE_LAYER_NOT_PREPARED, message: null };
  }
  if (
    raw.label === CONTEXTUAL_MAP_LAYER ||
    ranking.state === "INSUFFICIENT_EVIDENCE"
  ) {
    return { ...raw, label: JUDGE_LAYER_WITHHELD, message: null };
  }
  if (raw.label === DEFAULT_MAP_LAYER || ranking.state === "READY") {
    return { ...raw, label: JUDGE_LAYER_ORDER, message: null };
  }
  return { ...raw, message: null };
}
