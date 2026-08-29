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

export const MAX_UNCHANGED_IN_FLIGHT_POLLS = 4;

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
  stallCount: number,
): boolean {
  return (
    shouldContinuePolling(status) &&
    stallCount < MAX_UNCHANGED_IN_FLIGHT_POLLS
  );
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
