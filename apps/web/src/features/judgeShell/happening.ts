import { PUBLIC_STATUS, publicStatusForRankingState } from "@/features/publicLanguage";
import type { JobStatus } from "@/types";
import { shouldContinuePolling } from "@/utils/jobPolling";
import {
  INSUFFICIENT_REFERENCE,
  THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
} from "@/utils/mapLayer";
import {
  HAPPENING_FAILED,
  HAPPENING_HISTORY_NOT_PREPARED,
  HAPPENING_JOB_LOST,
  HAPPENING_NOT_REQUESTED,
  HAPPENING_ORDER_SHOWN,
  HAPPENING_ORDER_WITHHELD,
  HAPPENING_STALLED,
  HAPPENING_WORKING,
} from "./copy";

export type HappeningStamp =
  | "NOT REQUESTED"
  | "WORKING"
  | typeof PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED
  | typeof PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD
  | "HISTORY NOT PREPARED"
  | "JOB LOST"
  | "FAILED";

export type HappeningView = {
  stamp: HappeningStamp;
  line: string;
  rankingState: "INSUFFICIENT_EVIDENCE" | "READY";
};

export function happeningView(input: {
  status: JobStatus | null;
  busy: boolean;
  stalled: boolean;
  rankingState: "INSUFFICIENT_EVIDENCE" | "READY";
  limitations: readonly string[];
}): HappeningView {
  const rankingState = input.rankingState;

  if (input.status === "unknown_job") {
    return { stamp: "JOB LOST", line: HAPPENING_JOB_LOST, rankingState };
  }
  if (input.stalled) {
    return { stamp: "JOB LOST", line: HAPPENING_STALLED, rankingState };
  }
  if (input.status === "failed") {
    return { stamp: "FAILED", line: HAPPENING_FAILED, rankingState };
  }
  if (input.busy || shouldContinuePolling(input.status)) {
    return { stamp: "WORKING", line: HAPPENING_WORKING, rankingState };
  }
  if (input.status == null) {
    return {
      stamp: "NOT REQUESTED",
      line: HAPPENING_NOT_REQUESTED,
      rankingState,
    };
  }
  if (input.limitations.includes(INSUFFICIENT_REFERENCE)) {
    return {
      stamp: "HISTORY NOT PREPARED",
      line: HAPPENING_HISTORY_NOT_PREPARED,
      rankingState,
    };
  }
  if (rankingState === "READY") {
    return {
      stamp: publicStatusForRankingState("READY"),
      line: HAPPENING_ORDER_SHOWN,
      rankingState,
    };
  }
  if (
    input.limitations.includes(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT) ||
    input.status === "complete" ||
    input.status === "partial"
  ) {
    return {
      stamp: publicStatusForRankingState("INSUFFICIENT_EVIDENCE"),
      line: HAPPENING_ORDER_WITHHELD,
      rankingState,
    };
  }
  return {
    stamp: "NOT REQUESTED",
    line: HAPPENING_NOT_REQUESTED,
    rankingState,
  };
}
