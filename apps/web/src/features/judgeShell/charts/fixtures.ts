import type { AnalysisResultStub, ZoneDecisionStub } from "@/api/analysisJobs";

function zone(
  id: string,
  q_A: number,
  permitted: boolean,
): ZoneDecisionStub {
  return {
    zone_id: id,
    thermal_ordering_permitted: permitted,
    q_A,
  };
}

/** Flat night: leftover q_A clustered near 0.2. Order withheld. */
export function clusteredResult(): AnalysisResultStub {
  const zones = Array.from({ length: 25 }, (_, index) =>
    zone(`04013000${String(index).padStart(3, "0")}`, 0.2 + (index % 3) * 0.004, false),
  );
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    hazard_spread: {
      differentiation_state: "INSUFFICIENT",
      historical_years: [2022, 2023, 2024],
      reference_hour: "03:00",
    },
    zones,
  };
}

/** Differentiated night: positions sit apart. Ordering supported. */
export function separatedResult(): AnalysisResultStub {
  const zones = Array.from({ length: 25 }, (_, index) =>
    zone(`04013000${String(index).padStart(3, "0")}`, (index + 0.5) / 25, true),
  );
  return {
    thermal_differentiation_state: "SUFFICIENT",
    hazard_spread: {
      differentiation_state: "SUFFICIENT",
      historical_years: [2022, 2023, 2024],
      reference_hour: "03:00",
    },
    zones,
  };
}

export const SELECTED_CLUSTERED_ID = "04013000000";
