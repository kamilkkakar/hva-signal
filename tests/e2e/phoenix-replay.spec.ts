import { expect, test, type Page } from "@playwright/test";

const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

const FROZEN_GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

async function waitForWorkspaceMap(page: Page) {
  await expect(page.getByTestId("workspace")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("explore-city")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("map-stage")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("map-stage")).toHaveAttribute(
    "data-map-state",
    "sufficient",
    { timeout: 60_000 },
  );
}

test.describe("Phoenix workspace replay integration", () => {
  test.describe("America/New_York", () => {
    test.use({ timezoneId: "America/New_York" });

    test("Phoenix auto-loads and map reaches sufficient state in replay mode", async ({
      page,
    }) => {
      test.setTimeout(60_000);
      await page.goto("/");
      await waitForWorkspaceMap(page);

      const map = page.getByTestId("map-stage");
      await expect(map).toHaveAttribute("data-geometry-feature-count", "25");
      await expect(map).toHaveAttribute("data-ranked-feature-count", "25");

      await expect(page.getByTestId("observation-provenance")).toContainText("Published");
      await expect(page.getByTestId("observation-provenance")).not.toContainText("LIVE");

      const mapText = await map.innerText();
      expect(mapText).not.toMatch(/API KEY REQUIRED|carto\.com\/basemaps/i);
    });
  });

  test.describe("Pacific/Auckland", () => {
    test.use({ timezoneId: "Pacific/Auckland" });

    test("Phoenix workspace loads correctly regardless of timezone", async ({
      page,
    }) => {
      test.setTimeout(60_000);
      await page.goto("/");
      await waitForWorkspaceMap(page);

      const map = page.getByTestId("map-stage");
      await expect(map).toHaveAttribute("data-geometry-feature-count", "25");
      await expect(map).toHaveAttribute("data-ranked-feature-count", "25");

      await expect(page.getByTestId("zone-panel")).toBeVisible();
      await expect(page.getByTestId("zone-name")).toBeVisible();
    });
  });

  test.describe("API replay correctness (stateless)", () => {
    test("2022-07-01 03:00 INSUFFICIENT via API", async ({ request }) => {
      test.setTimeout(60_000);
      const created = await request.post(`${apiBase}/api/v1/analysis/jobs`, {
        data: {
          area_id: "phoenix-demo",
          analysis_time: "2022-07-01T03:00:00",
          analysis_mode: "retrospective",
          horizon_hours: 0,
          lookback_hours: 0,
          granularity_m: 100,
          data_mode: "replay",
        },
      });
      expect(created.status()).toBe(202);
      const { job_id: jobId } = (await created.json()) as { job_id?: string };
      expect(jobId).toBeTruthy();

      let job: Record<string, unknown> = {};
      await expect
        .poll(
          async () => {
            const resp = await request.get(`${apiBase}/api/v1/analysis/jobs/${jobId}`);
            job = (await resp.json()) as Record<string, unknown>;
            return (job.status as string) ?? null;
          },
          { timeout: 30_000 },
        )
        .toMatch(/complete|partial|failed/);

      expect(job.status).toBe("complete");
      const result = job.result as Record<string, unknown>;
      expect(result.thermal_differentiation_state).toBe("INSUFFICIENT");
      expect((result.zones as unknown[]).length).toBe(25);
      expect(JSON.stringify(job)).not.toMatch(/fortyguard_api_key/i);
    });

    test("2022-06-30 03:00 SUFFICIENT via API", async ({ request }) => {
      test.setTimeout(60_000);
      const created = await request.post(`${apiBase}/api/v1/analysis/jobs`, {
        data: {
          area_id: "phoenix-demo",
          analysis_time: "2022-06-30T03:00:00",
          analysis_mode: "retrospective",
          horizon_hours: 0,
          lookback_hours: 0,
          granularity_m: 100,
          data_mode: "replay",
        },
      });
      expect(created.status()).toBe(202);
      const { job_id: jobId } = (await created.json()) as { job_id?: string };
      expect(jobId).toBeTruthy();

      let job: Record<string, unknown> = {};
      await expect
        .poll(
          async () => {
            const resp = await request.get(`${apiBase}/api/v1/analysis/jobs/${jobId}`);
            job = (await resp.json()) as Record<string, unknown>;
            return (job.status as string) ?? null;
          },
          { timeout: 30_000 },
        )
        .toMatch(/complete|partial|failed/);

      expect(job.status).toBe("complete");
      const result = job.result as Record<string, unknown>;
      expect(result.thermal_differentiation_state).toBe("SUFFICIENT");
      expect((result.zones as unknown[]).length).toBe(25);
    });
  });
});
