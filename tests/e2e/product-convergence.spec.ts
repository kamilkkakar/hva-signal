import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";

const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
const fixturesDir = path.join(process.cwd(), "tests", "e2e", "fixtures");

const oracles = JSON.parse(
  readFileSync(path.join(fixturesDir, "phoenix-oracles.json"), "utf8"),
) as {
  hashes: { area_config: string };
  oracles: Array<{
    analysis_time: string;
    state: string;
    observed_spread: number;
    ranked_fills: number;
  }>;
};

const gazetteer = JSON.parse(
  readFileSync(path.join(fixturesDir, "place-search-gazetteer.json"), "utf8"),
) as {
  _not_product_evidence: boolean;
  thermal_product_evidence: boolean;
  invented_mean_temperature_c: boolean;
  queries: Record<string, string>;
  malformed_geoids: string[];
};

const unpublished = JSON.parse(
  readFileSync(path.join(fixturesDir, "unpublished-p1.json"), "utf8"),
) as {
  public_paths: string[];
  unpublished_geography_paths: string[];
  unpublished_job_fields: string[];
};

type JobBody = {
  status?: string;
  result?: {
    zones?: Array<{ ranked?: boolean }>;
    reference_quality?: string;
    thermal_differentiation_state?: string;
    area_config_sha256?: string;
    hazard_spread?: { observed_spread?: number | null };
  };
};

function historicalPayload(analysisTime: string) {
  return {
    area_id: "phoenix-demo",
    analysis_time: analysisTime,
    analysis_mode: "retrospective",
    horizon_hours: 0,
    lookback_hours: 0,
    granularity_m: 100,
    data_mode: "replay",
  };
}

async function submitAndPollJob(
  request: APIRequestContext,
  analysisTime: string,
): Promise<JobBody> {
  const created = await request.post(`${apiBase}/api/v1/analysis/jobs`, {
    data: historicalPayload(analysisTime),
  });
  expect(created.status()).toBe(202);
  const { job_id: jobId } = (await created.json()) as { job_id?: string };
  expect(jobId).toBeTruthy();

  let job: JobBody = {};
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `${apiBase}/api/v1/analysis/jobs/${jobId}`,
        );
        job = (await response.json()) as JobBody;
        return job.status ?? null;
      },
      { timeout: 30_000 },
    )
    .toMatch(/complete|partial|failed/);
  return job;
}

async function openApiPaths(request: APIRequestContext): Promise<string[]> {
  const response = await request.get(`${apiBase}/openapi.json`);
  expect(response.ok()).toBeTruthy();
  const schema = (await response.json()) as { paths?: Record<string, unknown> };
  return Object.keys(schema.paths ?? {});
}

test.describe("product convergence e2e (gated/mocked)", () => {
  test("place-search fixture is identity-only and invents no °C", () => {
    expect(gazetteer._not_product_evidence).toBe(true);
    expect(gazetteer.thermal_product_evidence).toBe(false);
    expect(gazetteer.invented_mean_temperature_c).toBe(false);
  });

  for (const oracle of oracles.oracles) {
    test(`Phoenix ${oracle.analysis_time} ${oracle.state} S=${oracle.observed_spread} ${oracle.ranked_fills} fills`, async ({
      request,
    }) => {
      test.setTimeout(60_000);
      const job = await submitAndPollJob(request, oracle.analysis_time);
      expect(job.status).toBe("complete");
      expect(job.result?.reference_quality).toBe("FULL_REFERENCE");
      expect(job.result?.thermal_differentiation_state).toBe(oracle.state);
      expect(job.result?.hazard_spread?.observed_spread).toBeCloseTo(
        oracle.observed_spread,
        12,
      );
      expect(job.result?.zones).toHaveLength(25);
      const ranked = (job.result?.zones ?? []).filter((zone) => zone.ranked)
        .length;
      expect(ranked).toBe(oracle.ranked_fills);
      expect(job.result?.area_config_sha256).toBe(oracles.hashes.area_config);
      expect(JSON.stringify(job)).not.toMatch(/fortyguard_api_key/i);
      expect(JSON.stringify(job)).not.toMatch(/FORTYGUARD LIVE/);
      expect(JSON.stringify(job)).not.toMatch(/allowance_remaining/);
    });
  }

  test("accountless: no login chrome and no login routes", async ({
    page,
    request,
  }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "HVA-Signal" }),
    ).toBeVisible();
    await expect(page.locator('input[name="analysis_time"]')).toHaveValue(
      "2022-07-01T03:00",
    );
    await expect(page.getByRole("link", { name: /sign in|log in|sign up/i })).toHaveCount(
      0,
    );
    await expect(
      page.getByRole("button", { name: /sign in|log in|sign up/i }),
    ).toHaveCount(0);
    await expect(page.locator('[data-testid="login"], [name="api_key"]')).toHaveCount(
      0,
    );
    await expect(page.getByTestId("city-search")).toHaveCount(0);

    const paths = await openApiPaths(request);
    expect(paths.sort()).toEqual([...unpublished.public_paths].sort());
    expect(paths.join(" ")).not.toMatch(/login|oauth|signup/i);
    const schema = await (await request.get(`${apiBase}/openapi.json`)).text();
    expect(schema.toLowerCase()).not.toContain("allowance_remaining");
    expect(schema.toLowerCase()).not.toContain("fortyguard_api_key");
  });

  test("allowance stays disabled on public ready payload", async ({
    request,
  }) => {
    const ready = await request.get(`${apiBase}/ready`);
    expect(ready.ok()).toBeTruthy();
    const body = (await ready.json()) as Record<string, unknown>;
    expect(body).not.toHaveProperty("allowance_remaining");
    expect(body).not.toHaveProperty("demo_allowance_enabled");
    expect(body).not.toHaveProperty("fortyguard_api_key");
    expect(JSON.stringify(body).toLowerCase()).not.toContain("allowance");
  });

  test("ambiguous place name is skipped while geography is unpublished", async ({
    page,
    request,
  }) => {
    const paths = await openApiPaths(request);
    const geographyOn = paths.some((item) => item.startsWith("/api/v1/places"));
    if (!geographyOn) {
      const search = await request.get(`${apiBase}/api/v1/places`, {
        params: { q: "Springfield" },
      });
      expect(search.status()).toBe(404);
      await page.goto("/");
      await expect(page.getByTestId("city-search")).toHaveCount(0);
      await expect(page.getByTestId("place-candidates")).toHaveCount(0);
      return;
    }

    const search = await request.get(`${apiBase}/api/v1/places`, {
      params: { q: "Springfield" },
    });
    expect(search.ok()).toBeTruthy();
    const body = (await search.json()) as {
      failure?: string;
      identity?: unknown;
    };
    expect(body.failure ?? gazetteer.queries.Springfield).toBe("AMBIGUOUS_PLACE");
    expect(body.identity ?? null).toBeNull();
  });

  test("malformed GEOID does not publish a place", async ({ request }) => {
    for (const geoid of gazetteer.malformed_geoids) {
      const response = await request.get(`${apiBase}/api/v1/places/${geoid}`);
      expect([400, 404, 422]).toContain(response.status());
    }
  });

  test("two-signal unpublished fields still 422 on P1 jobs", async ({
    request,
  }) => {
    for (const field of unpublished.unpublished_job_fields) {
      const response = await request.post(`${apiBase}/api/v1/analysis/jobs`, {
        data: { ...historicalPayload("2022-06-30T03:00:00"), [field]: true },
      });
      expect(response.status(), field).toBe(422);
    }
  });
});
