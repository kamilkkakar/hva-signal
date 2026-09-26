import { apiUrl } from "@/api/baseUrl";
import type {
  CapabilityEvidence,
  CapabilityEvidenceState,
  CapabilityStatus,
  CityConfig,
  ValidationJurisdiction,
  WorkspaceCatalog,
} from "./types";

const CAPABILITY_STATES = new Set<CapabilityStatus>([
  "AVAILABLE",
  "PARTIAL",
  "UNAVAILABLE",
  "INSUFFICIENT_EVIDENCE",
  "READY_FOR_ACQUISITION",
]);

const EVIDENCE_STATES = new Set<CapabilityEvidenceState>([
  "VERIFIED",
  "PARTIAL",
  "UNAVAILABLE",
  "VALIDATION_FAILED",
  "NOT_YET_TESTED",
]);

const VALIDATION_CLASSES = new Set<ValidationJurisdiction["validationClass"]>([
  "SMALL_PLACE",
  "ALASKA",
  "HAWAII",
  "UNSUPPORTED",
]);

type ServerCity = {
  city_id?: unknown;
  display_name?: unknown;
  state?: unknown;
  timezone?: unknown;
  local_geography_version?: unknown;
  capabilities?: unknown;
  capability_evidence?: unknown;
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

function nonEmptyString(value: unknown, message: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(message);
  return value;
}

function parseEvidence(value: unknown): Record<string, CapabilityEvidence> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Capability evidence is missing or malformed.");
  }
  const parsed: Record<string, CapabilityEvidence> = {};
  for (const [key, raw] of Object.entries(value)) {
    if (!key || !raw || typeof raw !== "object" || Array.isArray(raw)) {
      throw new Error("Capability evidence is missing or malformed.");
    }
    const item = raw as Record<string, unknown>;
    if (typeof item.state !== "string" || !EVIDENCE_STATES.has(item.state as CapabilityEvidenceState)) {
      throw new Error("Capability evidence contains an unsupported state.");
    }
    parsed[key] = {
      state: item.state as CapabilityEvidenceState,
      reason: nonEmptyString(item.reason, "Capability evidence is missing its reason."),
      affectedScope: nonEmptyString(item.affected_scope, "Capability evidence is missing its scope."),
      nextCheck: nonEmptyString(item.next_check, "Capability evidence is missing its next check."),
    };
  }
  if (Object.keys(parsed).length === 0) throw new Error("Capability evidence is empty.");
  return parsed;
}

function parseValidationJurisdictions(value: unknown): ValidationJurisdiction[] {
  if (!Array.isArray(value)) throw new Error("Validation jurisdiction evidence is malformed.");
  const seen = new Set<string>();
  return value.map((raw) => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      throw new Error("Validation jurisdiction evidence is malformed.");
    }
    const row = raw as Record<string, unknown>;
    const jurisdictionId = nonEmptyString(row.jurisdiction_id, "Validation jurisdiction has no identity.");
    if (seen.has(jurisdictionId)) throw new Error(`Validation jurisdiction repeats ${jurisdictionId}.`);
    seen.add(jurisdictionId);
    if (row.selectable !== false) throw new Error("Validation jurisdictions must remain non-selectable.");
    if (typeof row.validation_class !== "string" ||
        !VALIDATION_CLASSES.has(row.validation_class as ValidationJurisdiction["validationClass"]) ||
        typeof row.state !== "string" || !EVIDENCE_STATES.has(row.state as CapabilityEvidenceState) ||
        !Array.isArray(row.affected_scope) || row.affected_scope.length === 0 ||
        !row.affected_scope.every((item) => typeof item === "string" && item)) {
      throw new Error("Validation jurisdiction evidence is malformed.");
    }
    return {
      jurisdictionId,
      displayName: nonEmptyString(row.display_name, "Validation jurisdiction has no display name."),
      regionCode: row.region_code == null ? null : nonEmptyString(row.region_code, "Invalid region code."),
      validationClass: row.validation_class as ValidationJurisdiction["validationClass"],
      selectable: false,
      state: row.state as CapabilityEvidenceState,
      reason: nonEmptyString(row.reason, "Validation jurisdiction has no reason."),
      affectedScope: row.affected_scope as string[],
      nextCheck: nonEmptyString(row.next_check, "Validation jurisdiction has no next check."),
      capabilities: parseEvidence(row.capabilities),
    };
  });
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
    const capabilities = parseCapabilities(row.capabilities);
    const capabilityEvidence = row.capability_evidence === undefined
      ? undefined
      : parseEvidence(row.capability_evidence);
    if (capabilityEvidence &&
        (Object.keys(capabilities).length !== Object.keys(capabilityEvidence).length ||
         Object.keys(capabilities).some((key) => !(key in capabilityEvidence)))) {
      throw new Error("City capability evidence does not match its capability contract.");
    }
    return {
      id,
      label: row.display_name,
      state: row.state,
      apiCityId: row.city_id,
      timezone: row.timezone,
      hasLocalAnalysis: typeof row.local_geography_version === "string",
      capabilities,
      capabilityEvidence,
    };
  });
}

export function parseWorkspaceCatalog(payload: unknown): WorkspaceCatalog {
  const record = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  const cities = parseCityCatalog(payload);
  if (cities.some((city) => city.capabilityEvidence === undefined)) {
    throw new Error("Workspace catalog is missing operational capability evidence.");
  }
  const validationJurisdictions = parseValidationJurisdictions(record.validation_jurisdictions);
  const cityIds = new Set(cities.map((city) => city.apiCityId));
  if (validationJurisdictions.some((item) => cityIds.has(item.jurisdictionId))) {
    throw new Error("Validation jurisdictions overlap the operational catalog.");
  }
  return { cities, validationJurisdictions };
}

export async function fetchCityCatalog(): Promise<WorkspaceCatalog> {
  const response = await fetch(apiUrl("/api/v1/cities"), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`City catalog failed (${response.status}).`);
  return parseWorkspaceCatalog(await response.json());
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
