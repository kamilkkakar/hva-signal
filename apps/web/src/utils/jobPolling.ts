import type { JobStatus } from "@/types";

const IN_FLIGHT: ReadonlySet<JobStatus> = new Set([
  "queued",
  "loading_context",
  "fetching_thermal",
  "assembling_partitions",
  "aggregating_zones",
  "validating_hazard_spread",
  "normalizing",
  "computing",
]);

/** Matches backend FortyGuard poll_timeout. Unchanged in-flight is valid. */
export const MAX_IN_FLIGHT_OBSERVATION_MS = 600_000;
export const POLL_INTERVAL_MS = 1500;
export const MAX_CONSECUTIVE_NETWORK_ERRORS = 3;

/** @deprecated Unchanged in-flight polls no longer stop the client. */
export const MAX_UNCHANGED_IN_FLIGHT_POLLS = Number.POSITIVE_INFINITY;

export type PollDecisionInput = {
  elapsedMs?: number;
  consecutiveNetworkErrors?: number;
};

export function shouldContinuePolling(status: JobStatus | null): boolean {
  if (status == null) {
    return false;
  }
  if (status === "unknown_job") {
    return false;
  }
  return IN_FLIGHT.has(status);
}

export function nextStallCount(
  status: JobStatus,
  previousStatus: JobStatus | null,
  previousStallCount: number,
): number {
  if (!shouldContinuePolling(status)) {
    return 0;
  }
  if (previousStatus === status) {
    return previousStallCount + 1;
  }
  return 0;
}

export function shouldKeepPolling(
  status: JobStatus | null,
  stallCountOrOptions: number | PollDecisionInput = 0,
): boolean {
  if (!shouldContinuePolling(status)) {
    return false;
  }
  const options: PollDecisionInput =
    typeof stallCountOrOptions === "number" ? {} : stallCountOrOptions;
  if (
    (options.consecutiveNetworkErrors ?? 0) >= MAX_CONSECUTIVE_NETWORK_ERRORS
  ) {
    return false;
  }
  if ((options.elapsedMs ?? 0) >= MAX_IN_FLIGHT_OBSERVATION_MS) {
    return false;
  }
  return true;
}

export function jobProgressLabel(status: JobStatus | null): string {
  switch (status) {
    case "queued":
      return "Queued";
    case "loading_context":
      return "Loading area context";
    case "fetching_thermal":
      return "Fetching thermal field";
    case "assembling_partitions":
      return "Assembling partitions";
    case "aggregating_zones":
      return "Aggregating zones";
    case "validating_hazard_spread":
      return "Validating hazard spread";
    case "normalizing":
      return "Normalizing";
    case "computing":
      return "Computing";
    case "complete":
      return "Complete";
    case "partial":
      return "Partial";
    case "failed":
      return "Failed";
    case "unknown_job":
      return "Job missing on this runtime";
    default:
      return "No job";
  }
}
