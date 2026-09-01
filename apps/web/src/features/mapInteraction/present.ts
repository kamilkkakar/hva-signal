import { legendModeFromInteraction } from "@/features/mapEncoding";
import { canvasAllowed, catalogHasGeometry } from "./catalog";
import { detailFromState, hoverFromState } from "./detail";
import { mapInteractionIsEnabled } from "./flags";
import { legendFromCatalog } from "./legend";
import {
  EMPTY_CATALOG_COPY,
  LAYER_CLEARED_COPY,
  LAYER_TITLES,
  SELECT_PROMPT,
} from "./policy";
import { tableFromCatalog } from "./table";
import type { InteractionCatalog, InteractionState, MapInteractionView } from "./types";

function visualState(
  catalog: InteractionCatalog | null,
  state: InteractionState,
): MapInteractionView["visualState"] {
  if (!catalog || (catalog.zones.length === 0 && !catalogHasGeometry(catalog))) {
    return "empty";
  }
  if (!state.layerActive) {
    return "layer_cleared";
  }
  if (catalog.kind === "aoi_outline" || !catalog.fill_authorized) {
    return "outline_only";
  }
  return "semantic";
}

function announce(
  viewHover: MapInteractionView["hover"],
  viewDetail: MapInteractionView["detail"],
  state: InteractionState,
  catalog: InteractionCatalog | null,
): string {
  if (!state.layerActive) {
    return LAYER_CLEARED_COPY;
  }
  if (viewDetail) {
    const order = viewDetail.relative_order_line ? ` ${viewDetail.relative_order_line}.` : "";
    const evidence = viewDetail.position_shown
      ? viewDetail.position_meaning
      : `Temperature ${viewDetail.value_display}.`;
    return `Selected zone ${viewDetail.geoid}. ${evidence} ${viewDetail.observation_label}. Source ${viewDetail.source_story}.${order}`;
  }
  if (viewHover) {
    return `Hover ${viewHover.line}.`;
  }
  if (!catalog || catalog.zones.length === 0) {
    return EMPTY_CATALOG_COPY;
  }
  return SELECT_PROMPT;
}

export function presentMapInteraction(input: {
  enabled?: boolean;
  catalog: InteractionCatalog | null;
  state: InteractionState;
}): MapInteractionView {
  if (!mapInteractionIsEnabled(input.enabled)) {
    return {
      gated: true,
      visualState: "gated_off",
      canvasAllowed: false,
      layerTitle: LAYER_TITLES.none,
      meaningCopy: "Map interaction chrome is gated. The production Phoenix A map is unchanged.",
      positionLegendMode: null,
      legend: [],
      hover: null,
      detail: null,
      tableRows: [],
      selectedId: null,
      hoverId: null,
      layerActive: input.state.layerActive,
      fitGeneration: input.state.fitGeneration,
      canFitAoi: false,
      canClearLayer: false,
      canRestoreLayer: false,
      announce: "Map interaction is gated.",
      decorative: false,
    };
  }

  const catalog = input.catalog;
  const state = input.state;
  const hover = hoverFromState(state, catalog);
  const detail = detailFromState(state, catalog);
  const visual = visualState(catalog, state);
  const allowed = canvasAllowed(catalog, state.layerActive);

  return {
    gated: false,
    visualState: visual,
    canvasAllowed: allowed,
    layerTitle: !state.layerActive
      ? LAYER_TITLES.none
      : (catalog?.layer_title ?? LAYER_TITLES.none),
    meaningCopy:
      visual === "empty"
        ? EMPTY_CATALOG_COPY
        : !state.layerActive
          ? LAYER_CLEARED_COPY
          : (catalog?.meaning ?? EMPTY_CATALOG_COPY),
    positionLegendMode: legendModeFromInteraction({
      kind: catalog?.kind,
      fillAuthorized: Boolean(catalog?.fill_authorized),
      layerActive: state.layerActive,
      fillKind: catalog?.fill_kind,
    }),
    legend: legendFromCatalog(catalog, state.layerActive),
    hover,
    detail,
    tableRows: tableFromCatalog(catalog),
    selectedId: state.layerActive ? state.selectedId : null,
    hoverId: state.layerActive ? state.hoverId : null,
    layerActive: state.layerActive,
    fitGeneration: state.fitGeneration,
    canFitAoi: allowed,
    canClearLayer: allowed && state.layerActive,
    canRestoreLayer: allowed && !state.layerActive,
    announce: announce(hover, detail, state, catalog),
    decorative: false,
  };
}
