import type { InteractionCatalog, InteractionEvent, InteractionState } from "./types";

export function initialInteractionState(): InteractionState {
  return {
    hoverId: null,
    selectedId: null,
    layerActive: true,
    fitGeneration: 0,
  };
}

function zoneExists(catalog: InteractionCatalog | null, geoid: string | null): boolean {
  if (!catalog || !geoid) {
    return false;
  }
  return catalog.zones.some((zone) => zone.geoid === geoid);
}

export function reduceInteraction(
  state: InteractionState,
  event: InteractionEvent,
  catalog: InteractionCatalog | null,
): InteractionState {
  switch (event.type) {
    case "hover": {
      if (
        !state.layerActive ||
        !catalog?.fill_authorized ||
        !zoneExists(catalog, event.geoid)
      ) {
        return { ...state, hoverId: null };
      }
      return { ...state, hoverId: event.geoid };
    }
    case "select": {
      if (!zoneExists(catalog, event.geoid)) {
        return state;
      }
      if (state.selectedId === event.geoid) {
        return { ...state, selectedId: null };
      }
      return { ...state, selectedId: event.geoid };
    }
    case "clear_selection":
      return { ...state, selectedId: null };
    case "clear_layer":
      return { ...state, layerActive: false, hoverId: null, selectedId: null };
    case "restore_layer":
      return { ...state, layerActive: true };
    case "fit_aoi":
      return { ...state, fitGeneration: state.fitGeneration + 1 };
    case "reset_aoi":
      return {
        ...state,
        hoverId: null,
        fitGeneration: state.fitGeneration + 1,
      };
    default: {
      const _never: never = event;
      return _never;
    }
  }
}
