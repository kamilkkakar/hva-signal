import { LAYER_MEANING, LAYER_TITLES } from "./policy";
import type {
  InteractionCatalog,
  InteractionCollection,
  InteractionZone,
  MapLayerKind,
  ProductSourceLabel,
} from "./types";

const EMPTY_COLLECTION: InteractionCollection = {
  type: "FeatureCollection",
  features: [],
};

export function emptyCatalog(
  kind: MapLayerKind = "none",
  extras: Partial<Pick<InteractionCatalog, "time_label" | "source_label">> = {},
): InteractionCatalog {
  return {
    kind,
    layer_title: LAYER_TITLES[kind],
    meaning: LAYER_MEANING[kind],
    time_label: extras.time_label ?? "—",
    source_label: extras.source_label ?? "UNAVAILABLE",
    fill_authorized: false,
    zones: [],
    collection: EMPTY_COLLECTION,
  };
}

export function buildCatalog(input: {
  kind: MapLayerKind;
  zones: InteractionZone[];
  collection?: InteractionCollection;
  time_label: string;
  source_label: ProductSourceLabel;
  fill_authorized: boolean;
  layer_title?: string;
  meaning?: string;
}): InteractionCatalog {
  const zones = [...input.zones].sort((left, right) => left.geoid.localeCompare(right.geoid));
  const collection = input.collection ?? {
    type: "FeatureCollection",
    features: [],
  };
  return {
    kind: input.kind,
    layer_title: input.layer_title ?? LAYER_TITLES[input.kind],
    meaning: input.meaning ?? LAYER_MEANING[input.kind],
    time_label: input.time_label,
    source_label: input.source_label,
    fill_authorized: input.fill_authorized,
    zones,
    collection,
  };
}

export function catalogZone(
  catalog: InteractionCatalog | null,
  geoid: string | null,
): InteractionZone | null {
  if (!catalog || !geoid) {
    return null;
  }
  return catalog.zones.find((zone) => zone.geoid === geoid) ?? null;
}

export function catalogHasGeometry(catalog: InteractionCatalog | null): boolean {
  return Boolean(catalog && catalog.collection.features.length > 0);
}

export function canvasAllowed(
  catalog: InteractionCatalog | null,
  layerActive: boolean,
): boolean {
  if (!catalog) {
    return false;
  }
  if (catalog.zones.length === 0 && !catalogHasGeometry(catalog)) {
    return false;
  }
  if (!layerActive && !catalogHasGeometry(catalog) && catalog.zones.length === 0) {
    return false;
  }
  return catalog.zones.length > 0 || catalogHasGeometry(catalog);
}
