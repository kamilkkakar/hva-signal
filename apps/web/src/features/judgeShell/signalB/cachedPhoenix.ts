/** Public-safe cached phoenix-demo SelectedTimeSnapshot. Zone means only. */
import type { SelectedTimeSection } from "@/features/signals/types";
import seed from "./cachedPhoenixSnapshot.json";

export const CACHED_B_ACTIVITY_ID = "e0244934-0840-4072-bcb6-96cca26a9a20";
export const CACHED_B_FINGERPRINT =
  "319d2425f955a51527d3ddad1cbb0b2588d5336fff12f9ceabc035a9d38282f8";
export const CACHED_B_WORDING = "AVAILABLE NOW — CACHED EVIDENCE" as const;

type SeedZone = {
  zone_id: string;
  mean_temperature_c: number | null;
  tile_count: number;
  coverage_status: string;
};

type SeedDoc = {
  snapshot_request_fingerprint: string;
  activity_id: string;
  area_id: string;
  target_timestamp_local: string;
  timezone: string;
  expected_zone_count: number;
  valid_zone_count: number;
  missing_zone_ids: string[];
  temperature_min_c: number;
  temperature_max_c: number;
  source: string;
  data_status: string;
  zones: SeedZone[];
};

const doc = seed as SeedDoc;

export function phoenixDemoCachedSelectedTime(): SelectedTimeSection {
  if (doc.snapshot_request_fingerprint !== CACHED_B_FINGERPRINT) {
    throw new Error("cached Signal B seed fingerprint mismatch");
  }
  return {
    kind: "selected_time_snapshot",
    requested: true,
    availability: "READY",
    provenance_source: "fortyguard_cached",
    data_status: "cached",
    target_timestamp: doc.target_timestamp_local,
    timezone: doc.timezone,
    expected_zone_count: doc.expected_zone_count,
    valid_zone_count: doc.valid_zone_count,
    missing_zone_ids: doc.missing_zone_ids,
    zones: doc.zones.map((zone) => ({
      zone_id: zone.zone_id,
      mean_temperature_c: zone.mean_temperature_c,
      coverage_status: zone.coverage_status === "ok" ? "valid" : "missing",
    })),
    temperature_min_c: doc.temperature_min_c,
    temperature_max_c: doc.temperature_max_c,
    reason_code: null,
    reference_version: null,
    reference_source: null,
    ready_scene: "cached",
  };
}

export function selectedZoneTemperatureC(
  zoneId: string | null | undefined,
): number | null {
  if (!zoneId) {
    return null;
  }
  const zone = doc.zones.find((row) => row.zone_id === zoneId);
  return zone?.mean_temperature_c ?? null;
}
