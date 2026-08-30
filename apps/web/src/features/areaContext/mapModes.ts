import type { MapMode, ZoneMapProperties } from "./types";

export const MAP_MODES: readonly MapMode[] = [
  "THERMAL",
  "TREE_CANOPY",
  "INCOME",
  "OLDER_HOUSING",
];

const FILL_KEY: Record<
  Exclude<MapMode, "THERMAL">,
  keyof Pick<
    ZoneMapProperties,
    "canopy_cover_share" | "median_household_income" | "share_pre_1980_housing"
  >
> = {
  TREE_CANOPY: "canopy_cover_share",
  INCOME: "median_household_income",
  OLDER_HOUSING: "share_pre_1980_housing",
};

const ALLOW_KEY: Record<
  Exclude<MapMode, "THERMAL">,
  keyof Pick<
    ZoneMapProperties,
    | "canopy_comparison_allowed"
    | "income_comparison_allowed"
    | "older_housing_comparison_allowed"
  >
> = {
  TREE_CANOPY: "canopy_comparison_allowed",
  INCOME: "income_comparison_allowed",
  OLDER_HOUSING: "older_housing_comparison_allowed",
};

export function contextFillValue(
  mode: MapMode,
  properties: ZoneMapProperties,
): number | null {
  if (mode === "THERMAL") {
    return null;
  }
  if (!properties[ALLOW_KEY[mode]]) {
    return null;
  }
  const value = properties[FILL_KEY[mode]];
  return typeof value === "number" ? value : null;
}

export function layerLooksLikeProbability(mode: MapMode): boolean {
  return mode !== "THERMAL" && mode !== "TREE_CANOPY" && mode !== "INCOME" && mode !== "OLDER_HOUSING";
}
