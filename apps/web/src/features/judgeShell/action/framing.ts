import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import {
  ACTION_V0_SCOPE,
  ACTION_V0_STATUS,
  AWAITING_DOES_NOT_COPY,
  AWAITING_SAYS_COPY,
  AWAITING_STAMP,
  AWAITING_SUPPORTS_COPY,
  INSUFFICIENT_DOES_NOT_COPY,
  INSUFFICIENT_SAYS_COPY,
  INSUFFICIENT_STAMP,
  INSUFFICIENT_SUPPORTS_COPY,
  NOT_EVALUATED_DOES_NOT_COPY,
  NOT_EVALUATED_SAYS_COPY,
  NOT_EVALUATED_STAMP,
  NOT_EVALUATED_SUPPORTS_COPY,
  SUFFICIENT_DOES_NOT_COPY,
  SUFFICIENT_SAYS_COPY,
  SUFFICIENT_STAMP,
  SUFFICIENT_SUPPORTS_COPY,
} from "./copy";
import type { ActionFramingView, ActionKind } from "./types";

const IN_FLIGHT: ReadonlySet<JobStatus> = new Set([
  "queued",
  "loading_context",
  "fetching_thermal",
  "assembling_partitions",
  "aggregating_zones",
  "normalizing",
  "validating_hazard_spread",
  "computing",
]);

function decision8State(result: AnalysisResultStub | null | undefined): string | null {
  return (
    result?.thermal_differentiation_state ??
    result?.hazard_spread?.differentiation_state ??
    null
  );
}

function limitationList(result: AnalysisResultStub): readonly string[] {
  if (result.system_limitations?.length) {
    return result.system_limitations;
  }
  return result.limitations ?? [];
}

function thermalOrderingAuthorized(result: AnalysisResultStub): boolean {
  if (decision8State(result) !== "SUFFICIENT") {
    return false;
  }
  const zones = result.zones ?? [];
  if (zones.length === 0) {
    return false;
  }
  return zones.every((zone) => zone.thermal_ordering_permitted === true);
}

function viewFor(kind: ActionKind): ActionFramingView {
  switch (kind) {
    case "sufficient":
      return {
        kind,
        stamp: SUFFICIENT_STAMP,
        says: SUFFICIENT_SAYS_COPY,
        supports: SUFFICIENT_SUPPORTS_COPY,
        doesNotEstablish: SUFFICIENT_DOES_NOT_COPY,
        status: ACTION_V0_STATUS,
        scope: ACTION_V0_SCOPE,
      };
    case "insufficient":
      return {
        kind,
        stamp: INSUFFICIENT_STAMP,
        says: INSUFFICIENT_SAYS_COPY,
        supports: INSUFFICIENT_SUPPORTS_COPY,
        doesNotEstablish: INSUFFICIENT_DOES_NOT_COPY,
        status: ACTION_V0_STATUS,
        scope: ACTION_V0_SCOPE,
      };
    case "not_evaluated":
      return {
        kind,
        stamp: NOT_EVALUATED_STAMP,
        says: NOT_EVALUATED_SAYS_COPY,
        supports: NOT_EVALUATED_SUPPORTS_COPY,
        doesNotEstablish: NOT_EVALUATED_DOES_NOT_COPY,
        status: ACTION_V0_STATUS,
        scope: ACTION_V0_SCOPE,
      };
    case "awaiting":
      return {
        kind,
        stamp: AWAITING_STAMP,
        says: AWAITING_SAYS_COPY,
        supports: AWAITING_SUPPORTS_COPY,
        doesNotEstablish: AWAITING_DOES_NOT_COPY,
        status: ACTION_V0_STATUS,
        scope: ACTION_V0_SCOPE,
      };
  }
}

export function presentActionFraming(input: {
  status?: JobStatus | null;
  result?: AnalysisResultStub | null;
}): ActionFramingView {
  const status = input.status ?? null;
  const result = input.result ?? null;

  if (status == null || IN_FLIGHT.has(status)) {
    return viewFor("awaiting");
  }

  if (status !== "complete" && status !== "partial") {
    return viewFor("not_evaluated");
  }

  if (result == null) {
    return viewFor("not_evaluated");
  }

  if (limitationList(result).includes("INSUFFICIENT_REFERENCE")) {
    return viewFor("not_evaluated");
  }

  const state = decision8State(result);
  if (state === "INSUFFICIENT") {
    return viewFor("insufficient");
  }
  if (state === "SUFFICIENT" && thermalOrderingAuthorized(result)) {
    return viewFor("sufficient");
  }
  return viewFor("not_evaluated");
}
