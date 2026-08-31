import type { CrossCityId } from "./types";

export const CROSS_CITY_OUTLINE_COLORS: Record<CrossCityId, string> = {
  "phoenix-az": "#2F6FED",
  "los-angeles-ca": "#E67E22",
  "tucson-az": "#7B4DDB",
  "las-vegas-nv": "#0D9488",
};

export function outlineColorForCity(cityId: CrossCityId): string {
  return CROSS_CITY_OUTLINE_COLORS[cityId];
}
