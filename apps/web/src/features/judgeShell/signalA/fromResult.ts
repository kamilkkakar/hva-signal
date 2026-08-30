import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import type { SignalAInput } from "./types";

function differentiationState(
  result: AnalysisResultStub | null | undefined,
): string | null {
  return (
    result?.thermal_differentiation_state ??
    result?.hazard_spread?.differentiation_state ??
    null
  );
}

function limitationList(result: AnalysisResultStub | null | undefined): string[] {
  if (result?.system_limitations?.length) {
    return [...result.system_limitations];
  }
  return result?.limitations ? [...result.limitations] : [];
}

function orderingPermitted(
  result: AnalysisResultStub | null | undefined,
): boolean | null {
  const zones = result?.zones ?? [];
  if (zones.length === 0) {
    return null;
  }
  return zones.every((zone) => zone.thermal_ordering_permitted === true);
}

/** Bind existing job facts. Does not compute q_A, Decision 8, or S. */
export function signalAInputFromResult(input: {
  status?: JobStatus | null;
  result?: AnalysisResultStub | null;
  requested?: boolean;
  historyPrepared?: boolean;
  zoneId?: string;
  order?: number;
}): SignalAInput {
  const result = input.result ?? null;
  return {
    requested: input.requested,
    jobStatus: input.status ?? null,
    hasResult: result != null,
    failed: input.status === "failed",
    historyPrepared: input.historyPrepared,
    limitations: limitationList(result),
    differentiationState: differentiationState(result),
    orderingPermitted: orderingPermitted(result),
    referenceQuality: result?.reference_quality ?? result?.hazard_spread?.reference_quality ?? null,
    zoneId: input.zoneId,
    order: input.order,
  };
}
