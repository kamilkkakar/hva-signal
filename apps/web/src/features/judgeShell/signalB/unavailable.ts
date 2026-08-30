import { presentSelectedTime } from "@/features/signals/presentation";
import type { SelectedTimeSection, SelectedTimeView } from "@/features/signals/types";
import {
  GATE1_EXPECTED_ZONE_COUNT,
  GATE1_REASON_CODE,
  GATE1_VALID_ZONE_COUNT,
} from "./publicBGate";

/** Honest phoenix-demo B miss. GATE 1: 0/25 joins. No zone °C. Not a live path. */
export function phoenixDemoUnavailableSelectedTime(): SelectedTimeSection {
  return {
    kind: "selected_time_snapshot",
    requested: true,
    availability: "UNAVAILABLE",
    provenance_source: null,
    data_status: "unavailable",
    target_timestamp: null,
    timezone: "America/Phoenix",
    expected_zone_count: GATE1_EXPECTED_ZONE_COUNT,
    valid_zone_count: GATE1_VALID_ZONE_COUNT,
    missing_zone_ids: [],
    zones: [],
    temperature_min_c: null,
    temperature_max_c: null,
    reason_code: GATE1_REASON_CODE,
    reference_version: null,
    reference_source: null,
  };
}

export function phoenixDemoUnavailableSelectedTimeView(): SelectedTimeView {
  return presentSelectedTime(phoenixDemoUnavailableSelectedTime(), {
    liveDemoConfirmation: false,
  });
}
