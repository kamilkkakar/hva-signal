import { selectedZoneTemperatureC } from "@/features/judgeShell/signalB/cachedPhoenix";
import { B_CLOCK, B_COVERAGE, B_TIMEZONE, B_WORDING } from "./copy";
import type { ThermalBPane } from "./types";

/** Absolute cached °C. Not q_A, Decision 8, or rank. No °C×canopy formula. */
export function presentThermalB(geoid: string | null | undefined): ThermalBPane {
  const temperatureC = selectedZoneTemperatureC(geoid);
  const finite = temperatureC != null && Number.isFinite(temperatureC);
  return {
    kind: finite ? "cached" : "missing",
    wording: B_WORDING,
    temperatureC: finite ? temperatureC : null,
    coverage: B_COVERAGE,
    clock: B_CLOCK,
    timezone: B_TIMEZONE,
    source: "fortyguard_cached",
    notQA: true,
    notDecision8: true,
    notRank: true,
  };
}

export function productThermalStatus(input: {
  aHasRealPane: boolean;
  bTemperatureC: number | null;
}): "AVAILABLE" | "UNKNOWN" {
  if (input.aHasRealPane) {
    return "AVAILABLE";
  }
  if (input.bTemperatureC != null && Number.isFinite(input.bTemperatureC)) {
    return "AVAILABLE";
  }
  return "UNKNOWN";
}
