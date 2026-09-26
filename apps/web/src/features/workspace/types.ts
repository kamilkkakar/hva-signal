export type WorkspaceMode = "explore" | "compare";
export type ObservationMode = "published" | "live";

export type CityId = string;

export type CapabilityStatus =
  | "AVAILABLE"
  | "PARTIAL"
  | "UNAVAILABLE"
  | "INSUFFICIENT_EVIDENCE"
  | "READY_FOR_ACQUISITION";

export type CityConfig = {
  id: CityId;
  label: string;
  state: string;
  hasLocalAnalysis: boolean;
  apiCityId: string;
  timezone: string;
  capabilities: Readonly<Record<string, CapabilityStatus>>;
};

export const CITIES: readonly CityConfig[] = [
  { id: "phoenix-az", label: "Phoenix", state: "AZ", hasLocalAnalysis: true, apiCityId: "phoenix", timezone: "America/Phoenix", capabilities: { type1_live: "READY_FOR_ACQUISITION" } },
  { id: "las-vegas-nv", label: "Las Vegas", state: "NV", hasLocalAnalysis: false, apiCityId: "las_vegas", timezone: "America/Los_Angeles", capabilities: { type1_live: "READY_FOR_ACQUISITION" } },
  { id: "tucson-az", label: "Tucson", state: "AZ", hasLocalAnalysis: false, apiCityId: "tucson", timezone: "America/Phoenix", capabilities: { type1_live: "READY_FOR_ACQUISITION" } },
  { id: "los-angeles-ca", label: "Los Angeles", state: "CA", hasLocalAnalysis: false, apiCityId: "los_angeles", timezone: "America/Los_Angeles", capabilities: { type1_live: "READY_FOR_ACQUISITION" } },
] as const;

export function cityConfig(id: CityId, cities: readonly CityConfig[] = CITIES): CityConfig {
  const found = cities.find((c) => c.id === id);
  if (found) return found;
  return cities[0] ?? CITIES[0] as CityConfig;
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
