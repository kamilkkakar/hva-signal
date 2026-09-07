import { cityConfig, type CityId } from "./types";
import { normalizeGeoid } from "./publishedCityMap";
import { formatObservationLabel } from "@/features/mapInteraction/zoneStory";

export type LiveZoneRow = {
  zone_id: string;
  temperature_c: number | null;
  tile_count: number;
  coverage_status: string;
};

export type LiveObservationResponse = {
  status?: string;
  acquisition_status?: string;
  observation_status?: string;
  message?: string;
  provenance?: {
    acquisition_language?: string;
    vendor_attempted?: boolean;
    cache_tier?: string | null;
    contract?: string;
  };
  result?: { request_fingerprint?: string };
  analysis?: {
    city?: string;
    local_datetime?: string;
    timezone?: string;
    aggregation_contract?: string;
    geometry_zone_count?: number;
    bindable_temperature_values?: number;
    source_tile_count?: number;
    zones?: LiveZoneRow[];
  };
};

export type LiveRequestIdentity = {
  cityId: CityId;
  requestedLocal: string;
  zoneIds: readonly string[];
};

export type StoredLiveObservation = LiveObservationResponse & {
  cityId: CityId;
  requestedLocal: string;
  analysis: NonNullable<LiveObservationResponse["analysis"]> & { zones: LiveZoneRow[] };
  source: "fortyguard_live" | "fortyguard_cached";
  partial: boolean;
};

export function cityTimezone(cityId: CityId): string {
  return cityId === "los-angeles-ca" || cityId === "las-vegas-nv"
    ? "America/Los_Angeles"
    : "America/Phoenix";
}

/** Validate the response itself, including old servers that call empty data a cache hit. */
export function acceptLiveObservation(
  body: LiveObservationResponse,
  request: LiveRequestIdentity,
): StoredLiveObservation {
  if (!body || !["cache_hit", "live_acquired", "partial_observation"].includes(body.status ?? "")) {
    throw new Error(body?.message ?? "Live observation is unavailable for this request.");
  }
  const analysis = body.analysis;
  const zones = analysis?.zones;
  if (!Array.isArray(zones) || zones.length === 0 ||
      !zones.some((row) => typeof row?.temperature_c === "number" && Number.isFinite(row.temperature_c))) {
    // Never forward the legacy cache-success message for an empty field.
    throw new Error("No usable zone temperatures were returned for the requested observation.");
  }
  if (analysis?.city !== cityConfig(request.cityId).label ||
      analysis.local_datetime !== request.requestedLocal ||
      analysis.timezone !== cityTimezone(request.cityId) ||
      analysis.aggregation_contract !== "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN") {
    throw new Error("The response does not match the requested city, time or observation contract.");
  }
  const expected = new Set(request.zoneIds.map(normalizeGeoid));
  const received = new Set(zones.map((row) => normalizeGeoid(row?.zone_id)));
  if (!expected.size || expected.size !== request.zoneIds.length ||
      zones.length !== expected.size || received.size !== expected.size ||
      analysis.geometry_zone_count !== expected.size ||
      [...received].some((id) => !expected.has(id))) {
    throw new Error("The response does not match the displayed city geography.");
  }
  let bindable = 0;
  let mappedTiles = 0;
  for (const row of zones) {
    if (!Number.isInteger(row.tile_count) || row.tile_count < 0) {
      throw new Error("The response contains invalid tile coverage.");
    }
    if (row.temperature_c === null) {
      if (row.coverage_status !== "missing" || row.tile_count !== 0) {
        throw new Error("The response contains inconsistent missing observations.");
      }
      continue;
    }
    if (typeof row.temperature_c !== "number" || !Number.isFinite(row.temperature_c) ||
        row.coverage_status !== "valid" || row.tile_count <= 0) {
      throw new Error("The response contains invalid zone temperatures.");
    }
    bindable += 1;
    mappedTiles += row.tile_count;
  }
  if (analysis.bindable_temperature_values !== bindable ||
      !Number.isInteger(analysis.source_tile_count) ||
      (analysis.source_tile_count ?? 0) < mappedTiles) {
    throw new Error("The response contains inconsistent temperature coverage.");
  }
  const acquisition = body.provenance?.acquisition_language;
  if (acquisition !== "cache_hit" && acquisition !== "live_acquisition") {
    throw new Error("The response is missing its acquisition provenance.");
  }
  return {
    ...body,
    cityId: request.cityId,
    requestedLocal: analysis.local_datetime,
    analysis: { ...analysis, zones },
    source: acquisition === "live_acquisition" ? "fortyguard_live" : "fortyguard_cached",
    partial: bindable < expected.size,
  };
}

export function liveObservationLabel(observation: StoredLiveObservation): string {
  const source = observation.source === "fortyguard_live" ? "Live acquisition" : "Cached live result";
  return source + " / " + formatObservationLabel(observation.requestedLocal) +
    " / FortyGuard Type-1 TCM" + (observation.partial ? " / Partial zone coverage" : "");
}
