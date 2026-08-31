import { ANALYSIS_AREA_GEOIDS, type SelectedAreaIdentity } from "./types";
import {
  phoenixLocalDisplayName,
  phoenixLocalSecondaryLabel,
  resolvePhoenixLocalIdentity,
} from "@/features/areaIdentity";

/** Catalog GEOID order from join_audit. Never backend_order or Decision 8 rank. */
export function analysisAreaNumber(geoid: string | null | undefined): number | null {
  if (!geoid) {
    return null;
  }
  const index = (ANALYSIS_AREA_GEOIDS as readonly string[]).indexOf(geoid);
  return index >= 0 ? index + 1 : null;
}

/** Public primary label — geographic tract name, not Analysis Area N. */
export function analysisAreaLabel(geoid: string | null | undefined): string | null {
  if (!geoid) {
    return null;
  }
  if (!(ANALYSIS_AREA_GEOIDS as readonly string[]).includes(geoid)) {
    return null;
  }
  return phoenixLocalDisplayName(geoid);
}

export function analysisAreaSecondaryLabel(geoid: string | null | undefined): string | null {
  return phoenixLocalSecondaryLabel(geoid);
}

export function resolveIdentity(geoid: string | null | undefined): SelectedAreaIdentity {
  const areaNumber = analysisAreaNumber(geoid);
  const packaged = resolvePhoenixLocalIdentity(geoid ?? null);
  return {
    geoid: geoid ?? null,
    areaNumber,
    label: packaged?.display_name ?? (areaNumber == null ? null : phoenixLocalDisplayName(geoid)),
    inCatalog: areaNumber != null,
    secondaryLabel: packaged?.secondary_label ?? null,
    nameSource: packaged?.name_source ?? null,
  };
}
