import {
  INTERACTION_BASE_LINE,
  INTERACTION_FILL_OPACITY,
  INTERACTION_HOVER_LINE,
  INTERACTION_HOVER_LINE_WIDTH,
  INTERACTION_LINE_WIDTH,
  INTERACTION_SELECT_LINE,
  INTERACTION_SELECT_LINE_WIDTH,
  INTERACTION_SHARED_FILL,
} from "./policy";
import type { InteractionCatalog, InteractionState } from "./types";

export type InteractionFillPaint = {
  "fill-color": string;
  "fill-opacity": unknown;
};

export type InteractionLinePaint = {
  "line-color": unknown;
  "line-width": unknown;
};

/**
 * Hover/select are outline emphasis. Fill is shared ink or off.
 * Never interpolates °C, q_A, or order into a client ramp.
 */
export function highlightFillPaint(
  catalog: InteractionCatalog | null,
  state: InteractionState,
): InteractionFillPaint {
  if (!state.layerActive || !catalog?.fill_authorized) {
    return {
      "fill-color": INTERACTION_SHARED_FILL,
      "fill-opacity": 0,
    };
  }
  return {
    "fill-color": INTERACTION_SHARED_FILL,
    "fill-opacity": [
      "case",
      ["==", ["get", "has_semantic_fill"], true],
      INTERACTION_FILL_OPACITY,
      0,
    ],
  };
}

export function highlightLinePaint(_state: InteractionState): InteractionLinePaint {
  return {
    "line-color": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      INTERACTION_SELECT_LINE,
      ["boolean", ["feature-state", "hover"], false],
      INTERACTION_HOVER_LINE,
      INTERACTION_BASE_LINE,
    ],
    "line-width": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      INTERACTION_SELECT_LINE_WIDTH,
      ["boolean", ["feature-state", "hover"], false],
      INTERACTION_HOVER_LINE_WIDTH,
      INTERACTION_LINE_WIDTH,
    ],
  };
}

export function featureStatePatch(
  state: InteractionState,
  geoid: string,
): { hover: boolean; selected: boolean } {
  return {
    hover: state.layerActive && state.hoverId === geoid,
    selected: state.layerActive && state.selectedId === geoid,
  };
}
