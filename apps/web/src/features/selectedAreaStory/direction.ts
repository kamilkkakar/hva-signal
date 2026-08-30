import { R0_TEXT, R1_TEXT, R2_TEXT, R3_TEXT, R4_TEXT, R5_TEXT } from "./copy";
import type { DirectionRule, PreparednessStatus, ThermalAPane, ThermalBPane } from "./types";

export function directionRules(input: {
  inCatalog: boolean;
  a: ThermalAPane;
  b: ThermalBPane;
  hasContextFacts: boolean;
  preparedness: PreparednessStatus;
}): DirectionRule[] {
  const rules: DirectionRule[] = [];
  if (!input.inCatalog) {
    rules.push({ id: "R0", text: R0_TEXT });
    return rules;
  }
  if (input.a.kind === "order_withheld") {
    rules.push({ id: "R1", text: R1_TEXT });
  }
  if (input.a.kind === "order_shown") {
    rules.push({ id: "R2", text: R2_TEXT });
  }
  if (input.b.temperatureC != null && Number.isFinite(input.b.temperatureC)) {
    rules.push({ id: "R3", text: R3_TEXT });
  }
  if (input.hasContextFacts) {
    rules.push({ id: "R4", text: R4_TEXT });
  }
  if (
    input.preparedness === "IDENTIFIED" ||
    input.preparedness === "NOT_IDENTIFIED_IN_DATASET" ||
    input.preparedness === "UNKNOWN"
  ) {
    rules.push({ id: "R5", text: R5_TEXT });
  }
  return rules;
}
