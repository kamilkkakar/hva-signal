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
        label: "Analysis geography",
        meaning: "The analysis window outline remains visible.",
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
        label: "Geography only",
        meaning:
          "No relative pattern is drawn for this night. Outlines are the analysis window. Absence is not a cool or safe class.",
        swatch: INTERACTION_BASE_LINE,
      },
    ];
  }
  if (catalog.kind === "selected_time_snapshot") {
    return [
      {
        id: "scale",
        label: "Fixed thermal scale",
        meaning: "Zone-mean absolute °C. 25–45 °C semantic scale — not stretched to this snapshot.",
        swatch: null,
      },
      {
        id: "valid",
        label: "Observed zone mean",
        meaning: "Filled polygon encodes °C on the fixed scale. Hover for the exact value.",
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
  /**
   * Authorized A: sequential scale lives on HistoricalPositionLegend.
   * Do not emit one shared sage swatch or "the encoding is the legend."
   */
  return [];
}
