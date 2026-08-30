import { EXPECTED_ZONE_COUNT, SIGNAL_A_FROZEN_HOUR } from "./types";
import type {
  HistoricalAvailability,
  HistoricalSection,
  SelectedTimeAvailability,
  SelectedTimeProvenanceSource,
  SelectedTimeSection,
  SnapshotZone,
} from "./types";

export type SignalFixtureScene =
  | "a_not_prepared_b_cached"
  | "a_not_prepared_b_unavailable"
  | "a_not_prepared_b_fetching"
  | "a_not_prepared_b_partial"
  | "a_not_prepared_b_ready"
  | "a_not_prepared_live_demo"
  | "a_insufficient_b_ready"
  | "inert";

function historical(
  availability: HistoricalAvailability,
  reason_code: string | null = null,
): HistoricalSection {
  return {
    kind: "historical_normalized",
    requested: availability !== "NOT_REQUESTED",
    availability,
    frozen_hour: SIGNAL_A_FROZEN_HOUR,
    reason_code,
  };
}

function zones(validCount: number, baseC: number): SnapshotZone[] {
  const shuffledIds = Array.from({ length: EXPECTED_ZONE_COUNT }, (_, index) => {
    const n = String(EXPECTED_ZONE_COUNT - index).padStart(2, "0");
    return `FIX-1714000-${n}`;
  });
  return shuffledIds.map((zone_id, index) => {
    const ordinal = EXPECTED_ZONE_COUNT - index;
    const valid = ordinal <= validCount;
    return {
      zone_id,
      mean_temperature_c: valid ? Number((baseC + (ordinal - 1) * 0.12).toFixed(2)) : null,
      coverage_status: valid ? "valid" : "missing",
    };
  });
}

function selectedTime(input: {
  availability: SelectedTimeAvailability;
  provenance_source?: SelectedTimeProvenanceSource;
  data_status?: SelectedTimeSection["data_status"];
  reason_code?: string | null;
  valid_count?: number | null;
  ready_scene?: SelectedTimeSection["ready_scene"];
  target_timestamp?: string | null;
}): SelectedTimeSection {
  const validCount = input.valid_count ?? null;
  const zoneRows =
    validCount == null
      ? []
      : zones(validCount, input.availability === "PARTIAL" ? 31.1 : 28.4);
  const missing = zoneRows
    .filter((row) => row.coverage_status === "missing")
    .map((row) => row.zone_id);
  const validTemps = zoneRows
    .map((row) => row.mean_temperature_c)
    .filter((value): value is number => value != null);
  return {
    kind: "selected_time_snapshot",
    requested: input.availability !== "NOT_REQUESTED",
    availability: input.availability,
    provenance_source: input.provenance_source ?? null,
    data_status: input.data_status ?? null,
    target_timestamp: input.target_timestamp ?? "2024-07-12T15:00:00",
    timezone: "America/Chicago",
    expected_zone_count: EXPECTED_ZONE_COUNT,
    valid_zone_count: validCount,
    missing_zone_ids: missing,
    zones: zoneRows,
    temperature_min_c: validTemps.length > 0 ? Math.min(...validTemps) : null,
    temperature_max_c: validTemps.length > 0 ? Math.max(...validTemps) : null,
    reason_code: input.reason_code ?? null,
    reference_version: null,
    reference_source: null,
    ready_scene: input.ready_scene,
  };
}

export function emptyHistorical(): HistoricalSection {
  return historical("NOT_REQUESTED");
}

export function emptySelectedTime(): SelectedTimeSection {
  return selectedTime({
    availability: "NOT_REQUESTED",
    target_timestamp: null,
    valid_count: null,
  });
}

export function fixturePair(scene: SignalFixtureScene): {
  historical: HistoricalSection;
  selectedTime: SelectedTimeSection;
} {
  switch (scene) {
    case "inert":
      return { historical: emptyHistorical(), selectedTime: emptySelectedTime() };
    case "a_not_prepared_b_cached":
      return {
        historical: historical("NOT_PREPARED", "REFERENCE_NOT_PREPARED"),
        selectedTime: selectedTime({
          availability: "READY",
          provenance_source: "replay",
          data_status: "replay",
          reason_code: "EVIDENCE_REUSED",
          valid_count: EXPECTED_ZONE_COUNT,
          ready_scene: "cached",
        }),
      };
    case "a_not_prepared_b_unavailable":
      return {
        historical: historical("NOT_PREPARED", "REFERENCE_NOT_PREPARED"),
        selectedTime: selectedTime({
          availability: "UNAVAILABLE",
          reason_code: "SNAPSHOT_UNAVAILABLE",
          valid_count: null,
        }),
      };
    case "a_not_prepared_b_fetching":
      return {
        historical: historical("NOT_PREPARED", "REFERENCE_NOT_PREPARED"),
        selectedTime: selectedTime({
          availability: "FETCHING",
          valid_count: null,
        }),
      };
    case "a_not_prepared_b_partial":
      return {
        historical: historical("NOT_PREPARED", "REFERENCE_NOT_PREPARED"),
        selectedTime: selectedTime({
          availability: "PARTIAL",
          provenance_source: "fortyguard_cached",
          data_status: "partial",
          reason_code: "SNAPSHOT_PARTIAL",
          valid_count: 18,
        }),
      };
    case "a_not_prepared_b_ready":
      return {
        historical: historical("NOT_PREPARED", "REFERENCE_NOT_PREPARED"),
        selectedTime: selectedTime({
          availability: "READY",
          provenance_source: "fortyguard_cached",
          data_status: "cached",
          reason_code: "EVIDENCE_REUSED",
          valid_count: EXPECTED_ZONE_COUNT,
          ready_scene: "ready",
        }),
      };
    case "a_not_prepared_live_demo":
      return {
        historical: historical("NOT_PREPARED", "REFERENCE_NOT_PREPARED"),
        selectedTime: selectedTime({
          availability: "UNAVAILABLE",
          reason_code: "LIVE_DEMO_NOT_REQUESTED",
          valid_count: null,
        }),
      };
    case "a_insufficient_b_ready":
      return {
        historical: historical("D8_INSUFFICIENT", "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"),
        selectedTime: selectedTime({
          availability: "READY",
          provenance_source: "replay",
          data_status: "replay",
          reason_code: "EVIDENCE_REUSED",
          valid_count: EXPECTED_ZONE_COUNT,
          ready_scene: "ready",
        }),
      };
  }
}
