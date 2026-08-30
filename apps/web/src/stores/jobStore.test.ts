import { describe, expect, it, vi } from "vitest";
import { createJobStore } from "./jobStore";
import type { AnalysisJobPayload } from "../api/analysisJobs";

const request = {
  area_id: "phoenix-demo",
  analysis_time: "2024-07-15T15:00:00.000Z",
  analysis_mode: "operational" as const,
  horizon_hours: 12,
  lookback_hours: 0,
  granularity_m: 100 as const,
  data_mode: "replay" as const,
};

describe("jobStore unknown_job recovery", () => {
  it("stops polling, keeps the last request, and resubmits the same payload", async () => {
    const createJob = vi
      .fn()
      .mockResolvedValueOnce({
        job_id: "job_old",
        status: "queued",
        recoverable: false,
        message: "Job accepted.",
      })
      .mockResolvedValueOnce({
        job_id: "job_new",
        status: "queued",
        recoverable: false,
        message: "Job accepted.",
      });

    const getJob = vi.fn(async (): Promise<AnalysisJobPayload> => ({
      job_id: "job_old",
      status: "unknown_job",
      recoverable: true,
      message: "The analysis job is no longer present on this runtime.",
    }));

    const store = createJobStore({ createJob, getJob });

    await store.getState().submit(request);
    expect(store.getState().polling).toBe(true);
    expect(store.getState().busy).toBe(true);

    await store.getState().poll();

    expect(store.getState().polling).toBe(false);
    expect(store.getState().busy).toBe(false);
    expect(store.getState().snapshot?.status).toBe("unknown_job");
    expect(store.getState().snapshot?.recoverable).toBe(true);
    expect(store.getState().lastRequest).toEqual(request);
    expect(store.getState().canResubmit).toBe(true);

    await store.getState().resubmit();
    expect(createJob).toHaveBeenCalledTimes(2);
    expect(createJob.mock.calls[1]?.[0]).toEqual(request);
    expect(store.getState().polling).toBe(true);
    expect(store.getState().jobId).toBe("job_new");
  });

  it("keeps polling an unchanged in-flight job", async () => {
    const createJob = vi.fn(async (): Promise<AnalysisJobPayload> => ({
      job_id: "job_queued",
      status: "queued",
      message: "Job accepted.",
    }));
    const getJob = vi.fn(async (): Promise<AnalysisJobPayload> => ({
      job_id: "job_queued",
      status: "queued",
      message: "Job accepted.",
    }));
    const store = createJobStore({ createJob, getJob });

    await store.getState().submit(request);
    expect(store.getState().polling).toBe(true);

    await store.getState().poll();
    await store.getState().poll();
    await store.getState().poll();
    await store.getState().poll();

    expect(store.getState().polling).toBe(true);
    expect(store.getState().busy).toBe(true);
    expect(store.getState().stalled).toBe(false);
    expect(store.getState().snapshot?.status).toBe("queued");
  });

  it("marks a job stalled after the observation horizon", async () => {
    const createJob = vi.fn(async (): Promise<AnalysisJobPayload> => ({
      job_id: "job_queued",
      status: "queued",
      message: "Job accepted.",
    }));
    const getJob = vi.fn(async (): Promise<AnalysisJobPayload> => ({
      job_id: "job_queued",
      status: "queued",
      message: "Job accepted.",
    }));
    const store = createJobStore({ createJob, getJob });

    await store.getState().submit(request);
    store.setState({ observationStartedAt: Date.now() - 600_000 });
    await store.getState().poll();

    expect(store.getState().polling).toBe(false);
    expect(store.getState().stalled).toBe(true);
    expect(store.getState().canResubmit).toBe(true);
  });

  it("does not keep polling after failed submit", async () => {
    const store = createJobStore({
      createJob: vi.fn(async () => {
        throw new Error("Analysis job was rejected (422).");
      }),
      getJob: vi.fn(),
    });

    await store.getState().submit(request);
    expect(store.getState().polling).toBe(false);
    expect(store.getState().busy).toBe(false);
    expect(store.getState().error).toMatch(/422/);
  });
});
