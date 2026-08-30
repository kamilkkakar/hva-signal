import { create } from "zustand";
import {
  buildAnalysisJobRequest,
  createAnalysisJob,
  getAnalysisJob,
} from "@/api/analysisJobs";
import type {
  AnalysisJobDraft,
  AnalysisJobPayload,
  AnalysisJobRequest,
} from "@/api/analysisJobs";
import {
  nextStallCount,
  shouldContinuePolling,
  shouldKeepPolling,
} from "@/utils/jobPolling";

export type AnalysisJobApi = {
  createJob: (request: AnalysisJobRequest) => Promise<AnalysisJobPayload>;
  getJob: (jobId: string) => Promise<AnalysisJobPayload>;
};

export type JobStoreState = {
  lastRequest: AnalysisJobRequest | null;
  jobId: string | null;
  snapshot: AnalysisJobPayload | null;
  submitting: boolean;
  polling: boolean;
  stalled: boolean;
  stallCount: number;
  observationStartedAt: number | null;
  consecutiveNetworkErrors: number;
  busy: boolean;
  error: string | null;
  canResubmit: boolean;
  submit: (draft: AnalysisJobDraft) => Promise<void>;
  poll: () => Promise<void>;
  resubmit: () => Promise<void>;
};

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return "Analysis request failed.";
}

function derived(state: {
  submitting: boolean;
  polling: boolean;
  lastRequest: AnalysisJobRequest | null;
  snapshot: AnalysisJobPayload | null;
  stalled: boolean;
}): Pick<JobStoreState, "busy" | "canResubmit"> {
  return {
    busy: state.submitting || state.polling,
    canResubmit:
      state.lastRequest != null &&
      (state.snapshot?.status === "unknown_job" || state.stalled),
  };
}

export function createJobStore(api: AnalysisJobApi) {
  return create<JobStoreState>((set, get) => ({
    lastRequest: null,
    jobId: null,
    snapshot: null,
    submitting: false,
    polling: false,
    stalled: false,
    stallCount: 0,
    observationStartedAt: null,
    consecutiveNetworkErrors: 0,
    busy: false,
    error: null,
    canResubmit: false,

    submit: async (draft) => {
      const lastRequest = buildAnalysisJobRequest(draft);
      const previous = get().snapshot;
      set({
        lastRequest,
        submitting: true,
        polling: false,
        stalled: false,
        stallCount: 0,
        observationStartedAt: null,
        consecutiveNetworkErrors: 0,
        error: null,
        ...derived({
          submitting: true,
          polling: false,
          lastRequest,
          snapshot: previous,
          stalled: false,
        }),
      });
      try {
        const snapshot = await api.createJob(lastRequest);
        const observationStartedAt = Date.now();
        const polling = shouldKeepPolling(snapshot.status, { elapsedMs: 0 });
        set({
          submitting: false,
          jobId: snapshot.job_id,
          snapshot,
          polling,
          stalled: false,
          stallCount: 0,
          observationStartedAt,
          consecutiveNetworkErrors: 0,
          error: null,
          ...derived({
            submitting: false,
            polling,
            lastRequest,
            snapshot,
            stalled: false,
          }),
        });
      } catch (err) {
        set({
          submitting: false,
          polling: false,
          stalled: false,
          stallCount: 0,
          error: errorMessage(err),
          ...derived({
            submitting: false,
            polling: false,
            lastRequest,
            snapshot: previous,
            stalled: false,
          }),
        });
      }
    },

    poll: async () => {
      const {
        jobId,
        lastRequest,
        snapshot: previous,
        stallCount: previousStall,
        observationStartedAt,
        consecutiveNetworkErrors,
      } = get();
      if (!jobId) {
        return;
      }
      const elapsedMs =
        observationStartedAt == null ? 0 : Date.now() - observationStartedAt;
      try {
        const snapshot = await api.getJob(jobId);
        const stallCount = nextStallCount(
          snapshot.status,
          previous?.status ?? null,
          previousStall,
        );
        const polling = shouldKeepPolling(snapshot.status, {
          elapsedMs,
          consecutiveNetworkErrors: 0,
        });
        const stalled =
          !polling &&
          snapshot.status !== "unknown_job" &&
          snapshot.status !== "complete" &&
          snapshot.status !== "partial" &&
          snapshot.status !== "failed";
        set({
          snapshot,
          polling,
          stallCount,
          stalled,
          consecutiveNetworkErrors: 0,
          error: null,
          ...derived({
            submitting: false,
            polling,
            lastRequest,
            snapshot,
            stalled,
          }),
        });
      } catch (err) {
        const nextErrors = consecutiveNetworkErrors + 1;
        const stillInFlight = shouldContinuePolling(previous?.status ?? null);
        const polling = shouldKeepPolling(previous?.status ?? null, {
          elapsedMs,
          consecutiveNetworkErrors: nextErrors,
        });
        set({
          polling,
          stalled: stillInFlight && !polling,
          consecutiveNetworkErrors: nextErrors,
          error: errorMessage(err),
          ...derived({
            submitting: false,
            polling,
            lastRequest,
            snapshot: get().snapshot,
            stalled: stillInFlight && !polling,
          }),
        });
      }
    },

    resubmit: async () => {
      const { lastRequest } = get();
      if (!lastRequest) {
        return;
      }
      await get().submit(lastRequest);
    },
  }));
}

export const useJobStore = createJobStore({
  createJob: (request) => createAnalysisJob(request),
  getJob: (jobId) => getAnalysisJob(jobId),
});
