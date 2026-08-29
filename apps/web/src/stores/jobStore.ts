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
import { shouldKeepPolling, nextStallCount } from "@/utils/jobPolling";

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
        const polling = shouldKeepPolling(snapshot.status, 0);
        set({
          submitting: false,
          jobId: snapshot.job_id,
          snapshot,
          polling,
          stalled: false,
          stallCount: 0,
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
      const { jobId, lastRequest, snapshot: previous, stallCount: previousStall } =
        get();
      if (!jobId) {
        return;
      }
      try {
        const snapshot = await api.getJob(jobId);
        const stallCount = nextStallCount(
          snapshot.status,
          previous?.status ?? null,
          previousStall,
        );
        const polling = shouldKeepPolling(snapshot.status, stallCount);
        const stalled = !polling && snapshot.status !== "unknown_job" &&
          snapshot.status !== "complete" &&
          snapshot.status !== "partial" &&
          snapshot.status !== "failed";
        set({
          snapshot,
          polling,
          stallCount,
          stalled,
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
        set({
          polling: false,
          stalled: false,
          error: errorMessage(err),
          ...derived({
            submitting: false,
            polling: false,
            lastRequest,
            snapshot: get().snapshot,
            stalled: false,
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
