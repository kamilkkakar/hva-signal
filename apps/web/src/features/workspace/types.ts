export type WorkspaceMode = "explore" | "compare";
export type ObservationMode = "published" | "live";

export type CityId = "phoenix-az" | "las-vegas-nv" | "tucson-az" | "los-angeles-ca";

export type CityConfig = {
  id: CityId;
  label: string;
  state: string;
  hasLocalAnalysis: boolean;
  apiCityId: string;
};

export const CITIES: readonly CityConfig[] = [
  { id: "phoenix-az", label: "Phoenix", state: "AZ", hasLocalAnalysis: true, apiCityId: "phoenix" },
  { id: "las-vegas-nv", label: "Las Vegas", state: "NV", hasLocalAnalysis: false, apiCityId: "las_vegas" },
  { id: "tucson-az", label: "Tucson", state: "AZ", hasLocalAnalysis: false, apiCityId: "tucson" },
  { id: "los-angeles-ca", label: "Los Angeles", state: "CA", hasLocalAnalysis: false, apiCityId: "los_angeles" },
] as const;

export function cityConfig(id: CityId): CityConfig {
  const found = CITIES.find((c) => c.id === id);
  if (found) return found;
  return CITIES[0] as CityConfig;
}

export type ZoneInfo = {
  geoid: string;
  label: string;
  secondaryLabel: string | null;
  temperatureC: number | null;
  canopyPct: number | null;
  incomeUsd: number | null;
  olderHousingPct: number | null;
  population: number | null;
};
