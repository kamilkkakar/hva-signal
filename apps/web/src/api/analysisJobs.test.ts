import { describe, expect, it, vi } from "vitest";
import {
  buildAnalysisJobRequest,
  createAnalysisJob,
  getAnalysisJob,
} from "./analysisJobs";

const validDraft = {
  area_id: "phoenix-demo",
  analysis_time: "2024-07-15T15:00:00.000Z",
  analysis_mode: "operational" as const,
  horizon_hours: 12,
  granularity_m: 100,
};

describe("buildAnalysisJobRequest", () => {
  it("defaults data_mode to replay and lookback to 0", () => {
    const request = buildAnalysisJobRequest(validDraft);
    expect(request.data_mode).toBe("replay");
    expect(request.lookback_hours).toBe(0);
    expect(request.horizon_hours).toBe(12);
    expect(request.granularity_m).toBe(100);
  });

  it("rejects horizon outside 0–12", () => {
    expect(() =>
      buildAnalysisJobRequest({ ...validDraft, horizon_hours: 13 }),
    ).toThrow(/horizon/i);
    expect(() =>
      buildAnalysisJobRequest({ ...validDraft, horizon_hours: -1 }),
    ).toThrow(/horizon/i);
  });

  it("rejects granularity other than 60, 80, or 100", () => {
    expect(() =>
      buildAnalysisJobRequest({ ...validDraft, granularity_m: 50 }),
    ).toThrow(/granularity/i);
  });
});

describe("analysis job client", () => {
  it("POSTs /api/v1/analysis/jobs with the constrained payload", async () => {
    const fetchImpl = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          job_id: "job_abc",
          status: "queued",
          recoverable: false,
          message: "Job accepted.",
        }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      );
    }) as unknown as typeof fetch;

    const request = buildAnalysisJobRequest(validDraft);
    const job = await createAnalysisJob(request, fetchImpl);

    expect(job.job_id).toBe("job_abc");
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/analysis/jobs");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toMatchObject({
      area_id: "phoenix-demo",
      horizon_hours: 12,
      granularity_m: 100,
      data_mode: "replay",
    });
  });

  it("GETs /api/v1/analysis/jobs/:id", async () => {
    const fetchImpl = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          job_id: "job_abc",
          status: "unknown_job",
          recoverable: true,
          message: "The analysis job is no longer present on this runtime.",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }) as unknown as typeof fetch;

    const job = await getAnalysisJob("job_abc", fetchImpl);
    expect(job.status).toBe("unknown_job");
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/api/v1/analysis/jobs/job_abc");
  });
});
