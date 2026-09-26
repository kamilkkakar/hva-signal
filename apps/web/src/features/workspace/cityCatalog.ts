import { apiUrl } from "@/api/baseUrl";
import type { CapabilityStatus, CityConfig } from "./types";

const CAPABILITY_STATES = new Set<CapabilityStatus>([
  "AVAILABLE",
  "PARTIAL",
  "UNAVAILABLE",
  "INSUFFICIENT_EVIDENCE",
  "READY_FOR_ACQUISITION",
]);

type ServerCity = {
  city_id?: unknown;
  display_name?: unknown;
  state?: unknown;
  timezone?: unknown;
  local_geography_version?: unknown;
  capabilities?: unknown;
};

function workspaceCityId(apiCityId: string, state: string): string {
  return `${apiCityId.replaceAll("_", "-")}-${state.toLowerCase()}`;
}

function parseCapabilities(value: unknown): Record<string, CapabilityStatus> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("City catalog entry is missing capability evidence.");
  }
  const parsed: Record<string, CapabilityStatus> = {};
  for (const [key, status] of Object.entries(value)) {
    if (!key || typeof status !== "string" || !CAPABILITY_STATES.has(status as CapabilityStatus)) {
      throw new Error("City catalog contains an unsupported capability state.");
    }
    parsed[key] = status as CapabilityStatus;
  }
  if (Object.keys(parsed).length === 0) {
    throw new Error("City catalog entry has no capability evidence.");
  }
  return parsed;
}

export function parseCityCatalog(payload: unknown): CityConfig[] {
  const rows = payload && typeof payload === "object"
    ? (payload as { cities?: unknown }).cities
    : null;
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error("Server city catalog is empty or malformed.");
  }
  const seen = new Set<string>();
  return rows.map((raw) => {
    const row = raw as ServerCity;
    if (typeof row.city_id !== "string" || !row.city_id ||
        typeof row.display_name !== "string" || !row.display_name ||
        typeof row.state !== "string" || !/^[A-Z]{2}$/.test(row.state) ||
        typeof row.timezone !== "string" || !row.timezone.includes("/")) {
      throw new Error("Server city catalog contains an invalid jurisdiction identity.");
    }
    const id = workspaceCityId(row.city_id, row.state);
    if (seen.has(id)) throw new Error(`Server city catalog repeats ${id}.`);
    seen.add(id);
    return {
      id,
      label: row.display_name,
      state: row.state,
      apiCityId: row.city_id,
      timezone: row.timezone,
      hasLocalAnalysis: typeof row.local_geography_version === "string",
      capabilities: parseCapabilities(row.capabilities),
    };
  });
}

export async function fetchCityCatalog(): Promise<CityConfig[]> {
  const response = await fetch(apiUrl("/api/v1/cities"), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`City catalog failed (${response.status}).`);
  return parseCityCatalog(await response.json());
}

export function supportsSelectedTimeLive(city: CityConfig): boolean {
  return ["AVAILABLE", "READY_FOR_ACQUISITION"].includes(
    city.capabilities.type1_live ?? "UNAVAILABLE",
  );
}

export function supportedObservationMode(
  city: CityConfig,
  requested: "published" | "live",
): "published" | "live" {
  return requested === "live" && !supportsSelectedTimeLive(city) ? "published" : requested;
}
