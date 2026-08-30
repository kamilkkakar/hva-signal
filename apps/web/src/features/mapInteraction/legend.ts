import { INTERACTION_BASE_LINE, INTERACTION_SHARED_FILL, LAYER_CLEARED_COPY } from "./policy";
import type { InteractionCatalog, LegendItem } from "./types";

export function legendFromCatalog(
  catalog: InteractionCatalog | null,
  layerActive: boolean,
): LegendItem[] {
  if (!catalog) {
    return [
      {
        id: "empty",
        label: "No bindable layer",
        meaning: "The map is withheld. Nothing is being colored.",
        swatch: null,
      },
    ];
  }
  if (!layerActive) {
    return [
      {
        id: "cleared",
        label: "No active layer",
        meaning: LAYER_CLEARED_COPY,
        swatch: null,
      },
      {
        id: "outline",
        label: "AOI outline",
        meaning: "Geography of the analysis window remains visible.",
        swatch: INTERACTION_BASE_LINE,
      },
    ];
  }
  if (catalog.kind === "none") {
    return [
      {
        id: "none",
        label: "No active layer",
        meaning: catalog.meaning,
        swatch: null,
      },
    ];
  }
  if (catalog.kind === "aoi_outline" || !catalog.fill_authorized) {
    return [
      {
        id: "outline",
        label: "AOI outline",
        meaning: "Order withheld. Outline is geography only. Absence is not a cool or safe class.",
        swatch: INTERACTION_BASE_LINE,
      },
    ];
  }
  if (catalog.kind === "selected_time_snapshot") {
    return [
      {
        id: "valid",
        label: "Valid zone mean",
        meaning: "Shared fill. Color is not stretched to the snapshot min/max.",
        swatch: INTERACTION_SHARED_FILL,
      },
      {
        id: "missing",
        label: "Missing",
        meaning: "Outline only. Unknown is not 0 °C.",
        swatch: null,
      },
    ];
  }
  return [
    {
      id: "authorized",
      label: "Nighttime order",
      meaning:
        "Nighttime order 1 of N → N of N. Not °C. Not a probability. Shared interaction fill; the host may replace this ink.",
      swatch: INTERACTION_SHARED_FILL,
    },
    {
      id: "excluded",
      label: "Not authorized",
      meaning: "Outline only. Absence is not a cool or safe class.",
      swatch: null,
    },
  ];
}
