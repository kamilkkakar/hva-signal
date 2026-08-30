import { ANALYSIS_AREA_GEOIDS, type SelectedAreaIdentity } from "./types";

/** Catalog GEOID order from join_audit. Never backend_order or Decision 8 rank. */
export function analysisAreaNumber(geoid: string | null | undefined): number | null {
  if (!geoid) {
    return null;
  }
  const index = (ANALYSIS_AREA_GEOIDS as readonly string[]).indexOf(geoid);
  return index >= 0 ? index + 1 : null;
}

export function analysisAreaLabel(geoid: string | null | undefined): string | null {
  const number = analysisAreaNumber(geoid);
  return number == null ? null : `Analysis Area ${number}`;
}

export function resolveIdentity(geoid: string | null | undefined): SelectedAreaIdentity {
  const areaNumber = analysisAreaNumber(geoid);
  return {
    geoid: geoid ?? null,
    areaNumber,
    label: areaNumber == null ? null : `Analysis Area ${areaNumber}`,
    inCatalog: areaNumber != null,
  };
}
