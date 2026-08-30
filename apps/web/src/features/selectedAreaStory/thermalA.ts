import type { AnalysisResultStub, ZoneDecisionStub } from "@/api/analysisJobs";
import type { Decision8State, ThermalAPane } from "./types";

function differentiationState(result: AnalysisResultStub | null | undefined): Decision8State {
  const raw = (
    result?.thermal_differentiation_state ??
    result?.hazard_spread?.differentiation_state ??
    ""
  ).toUpperCase();
  if (raw === "SUFFICIENT") {
    return "SUFFICIENT";
  }
  if (raw === "INSUFFICIENT") {
    return "INSUFFICIENT";
  }
  return null;
}

function zoneFor(
  result: AnalysisResultStub | null | undefined,
  geoid: string | null,
): ZoneDecisionStub | null {
  if (!geoid) {
    return null;
  }
  return result?.zones?.find((zone) => zone.zone_id === geoid) ?? null;
}

function orderingPermitted(result: AnalysisResultStub | null | undefined): boolean {
  const zones = result?.zones ?? [];
  if (zones.length === 0) {
    return false;
  }
  return zones.every((zone) => zone.thermal_ordering_permitted !== false);
}

/** q_A / D8 / order_shown only when Decision 8 is SUFFICIENT. Withheld never resurrects rank. */
export function presentThermalA(
  result: AnalysisResultStub | null | undefined,
  geoid: string | null,
): ThermalAPane {
  const zone = zoneFor(result, geoid);
  const decision8 = differentiationState(result);
  const hasRealPane = zone != null && decision8 != null;

  if (!hasRealPane) {
    return {
      kind: "absent",
      hasRealPane: false,
      decision8,
      q_A: null,
      orderShown: false,
      source: "fortyguard_replay",
    };
  }

  if (decision8 === "INSUFFICIENT") {
    return {
      kind: "order_withheld",
      hasRealPane: true,
      decision8,
      q_A: null,
      orderShown: false,
      source: "fortyguard_replay",
    };
  }

  const shown = orderingPermitted(result);
  const qA = typeof zone.q_A === "number" && Number.isFinite(zone.q_A) ? zone.q_A : null;
  return {
    kind: shown ? "order_shown" : "order_withheld",
    hasRealPane: true,
    decision8: "SUFFICIENT",
    q_A: shown ? qA : null,
    orderShown: shown,
    source: "fortyguard_replay",
  };
}
