import { mapModeMeta } from "@/features/selectedAreaStory/copy";
import type { InteractionCatalog, InteractionFeature } from "@/features/mapInteraction";
import type { MapMode, ZoneMapProperties } from "./types";
import { contextFillValue } from "./mapModes";

export const CONTEXT_FILL_PROPERTY = "context_fill_value";

function zoneFor(geoid: string, zones: ZoneMapProperties[]): ZoneMapProperties | null {
  return (
    zones.find((row) => row.census_tract_geoid === geoid || row.zone_id === geoid) ?? null
  );
}

function featureGeoid(feature: InteractionFeature): string {
  return String(feature.properties.GEOID ?? feature.properties.zone_id ?? "");
}

/** Overlay context quantities onto an existing geometry catalog. THERMAL is a no-op. */
export function bindMapModeCatalog(input: {
  historical: InteractionCatalog | null;
  mode: MapMode;
  zones?: ZoneMapProperties[];
}): InteractionCatalog | null {
  const historical = input.historical;
  if (!historical) {
    return null;
  }
  if (input.mode === "THERMAL") {
    return historical;
  }

  const meta = mapModeMeta(input.mode);
  const zones = input.zones ?? [];
  const features = historical.collection.features.map((feature) => {
    const geoid = featureGeoid(feature);
    const row = zoneFor(geoid, zones);
    const value = row ? contextFillValue(input.mode, row) : null;
    return {
      ...feature,
      properties: {
        ...feature.properties,
        [CONTEXT_FILL_PROPERTY]: value,
        has_semantic_fill: value != null,
        value_display: value == null ? "—" : String(value),
      },
    };
  });
  const mappedZones = historical.zones.map((zone) => {
    const row = zoneFor(zone.geoid, zones);
    const value = row ? contextFillValue(input.mode, row) : null;
    return {
      ...zone,
      has_semantic_fill: value != null,
      value_kind: "none" as const,
      value_display: value == null ? "—" : String(value),
      relative_order: null,
      q_A_display: null,
      q_A_value: null,
      position_shown: false,
    };
  });

  return {
    ...historical,
    layer_title: meta.label,
    meaning: `${meta.source} · ${meta.year} · ${meta.unit}. ${meta.meaning}`,
    fill_kind: "context_quantity",
    fill_authorized: historical.fill_authorized,
    zones: mappedZones,
    collection: {
      type: "FeatureCollection",
      features,
    },
  };
}

export function contextFillCount(catalog: InteractionCatalog | null): number {
  if (!catalog || catalog.fill_kind !== "context_quantity") {
    return 0;
  }
  return catalog.collection.features.filter(
    (feature) => typeof feature.properties[CONTEXT_FILL_PROPERTY] === "number",
  ).length;
}

export function catalogUsesThermalRank(catalog: InteractionCatalog | null): boolean {
  return catalog?.fill_kind === "thermal_order" && catalog.fill_authorized === true;
}
