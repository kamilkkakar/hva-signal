import { expect, test, type Page } from "@playwright/test";

async function openAdvancedDetails(page: Page) {
  const details = page.getByTestId("analysis-detail");
  await expect(details).toBeAttached({ timeout: 45_000 });
  if ((await details.getAttribute("open")) == null) {
    await page.getByTestId("advanced-technical-details").click();
  }
  await expect(details).toHaveAttribute("open", "");
}

const FROZEN_GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

type JobBody = {
  status?: string;
  request?: { analysis_time?: string };
  result?: {
    zones?: unknown[];
    reference_quality?: string;
    thermal_differentiation_state?: string;
    versions?: { zone_geometry_version?: string };
    hazard_spread?: {
      observed_spread?: number | null;
      zone_geometry_version?: string | null;
      differentiation_state?: string;
    };
    system_limitations?: string[];
  };
};

async function submitAndReadJob(
  page: import("@playwright/test").Page,
  request: import("@playwright/test").APIRequestContext,
): Promise<{ requestTime: string; job: JobBody }> {
  const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  const posted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes("/api/v1/analysis/jobs"),
  );
  await page.getByRole("button", { name: "Submit analysis" }).click();
  const post = await posted;
  const requestTime = JSON.parse(post.request().postData() ?? "{}")
    .analysis_time as string;
  const created = (await post.json()) as { job_id?: string };
  if (!created.job_id) {
    throw new Error("Analysis job POST did not return job_id.");
  }

  let job: JobBody = {};
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `${apiBase}/api/v1/analysis/jobs/${created.job_id}`,
        );
        job = (await response.json()) as JobBody;
        return job.status ?? null;
      },
      { timeout: 30_000 },
    )
    .toMatch(/complete|partial|failed/);

  return { requestTime, job };
}

test.describe("Phoenix AOI-local replay demo path", () => {
  test.describe("America/New_York", () => {
    test.use({ timezoneId: "America/New_York" });

    test("default submit is 2022-07-01 03:00 AOI-local INSUFFICIENT", async ({
      page,
      request,
    }) => {
      test.setTimeout(60_000);
      await page.goto("/");
      await expect(page.locator('input[name="analysis_time"]')).toHaveValue(
        "2022-07-01T03:00",
      );

      const { requestTime, job } = await submitAndReadJob(page, request);
      expect(requestTime).toBe("2022-07-01T03:00:00");
      expect(requestTime).not.toMatch(/Z$/);
      expect(job.status).toBe("complete");
      expect(job.result?.zones).toHaveLength(25);
      expect(
        job.result?.versions?.zone_geometry_version ??
          job.result?.hazard_spread?.zone_geometry_version,
      ).toBe(FROZEN_GEOMETRY);
      expect(job.result?.reference_quality).toBe("FULL_REFERENCE");
      expect(job.result?.thermal_differentiation_state).toBe("INSUFFICIENT");
      expect(job.result?.hazard_spread?.observed_spread).toBeCloseTo(
        0.0439665471923536,
        12,
      );
      expect(JSON.stringify(job.result)).not.toMatch(
        /phoenix_demo_unfrozen_zones/,
      );
      expect(JSON.stringify(job.result)).not.toMatch(/heatmap_tcm_hourly_1500/);

      await openAdvancedDetails(page);
      const panel = page.getByTestId("decision8-evidence-panel");
      await expect(panel).toBeVisible();
      await expect(page.getByTestId("decision8-observed-s")).toContainText(
        "0.043966547192353",
      );
      await expect(page.getByTestId("decision8-policy-floor")).toContainText(
        "0.10 q_A units",
      );
      await expect(page.getByTestId("decision8-policy-floor")).not.toContainText(
        "%",
      );
      await expect(page.getByTestId("decision8-reference-version")).toContainText(
        "PHX_ZTSI_REF_V1",
      );
      await expect(page.getByTestId("decision8-zone-geometry")).toContainText(
        FROZEN_GEOMETRY,
      );
      await expect(
        page.getByTestId("decision8-suppression-reason"),
      ).toBeVisible();
      await expect(page.getByTestId("source-banner")).toContainText("REPLAY");
      await expect(page.getByTestId("source-banner")).not.toContainText(
        "FORTYGUARD CACHED",
      );
      await expect(page.getByTestId("source-banner")).not.toContainText("LIVE");

      const map = page.getByTestId("map-stage");
      await expect(map).toHaveAttribute("data-map-state", "insufficient", {
        timeout: 30_000,
      });
      await expect(map).toHaveAttribute("data-geometry-feature-count", "25");
      await expect(map).toHaveAttribute("data-ranked-feature-count", "0");
      await expect(map).toHaveAttribute("data-map-source-count", "25");
      await expect(page.getByTestId("map-layer-label")).toContainText(
        "Nighttime historical thermal pattern",
      );
      await expect(page.locator("body")).not.toContainText(
        "Geometry and decision cards are not wired yet",
      );
    });
  });

  test.describe("Pacific/Auckland", () => {
    test.use({ timezoneId: "Pacific/Auckland" });

    test("selected 2022-06-30 remains AOI-local and reaches SUFFICIENT", async ({
      page,
      request,
    }) => {
      test.setTimeout(60_000);
      await page.goto("/");
      await page.locator('input[name="analysis_time"]').fill("2022-06-30T03:00");
      await expect(page.locator('input[name="analysis_time"]')).toHaveValue(
        "2022-06-30T03:00",
      );

      const { requestTime, job } = await submitAndReadJob(page, request);
      expect(requestTime).toBe("2022-06-30T03:00:00");
      expect(job.status).toBe("complete");
      expect(job.result?.zones).toHaveLength(25);
      expect(
        job.result?.versions?.zone_geometry_version ??
          job.result?.hazard_spread?.zone_geometry_version,
      ).toBe(FROZEN_GEOMETRY);
      expect(job.result?.reference_quality).toBe("FULL_REFERENCE");
      expect(job.result?.thermal_differentiation_state).toBe("SUFFICIENT");
      expect(job.result?.hazard_spread?.observed_spread).toBeCloseTo(
        0.1354838709677419,
        12,
      );
      expect(job.result?.zones?.some((zone) => (zone as { ranked?: boolean }).ranked)).toBe(
        true,
      );

      await openAdvancedDetails(page);
      const panel = page.getByTestId("decision8-evidence-panel");
      await expect(panel).toBeVisible();
      await expect(page.getByTestId("decision8-observed-s")).toContainText(
        "0.135483870967741",
      );
      await expect(page.getByTestId("decision8-policy-version")).toContainText(
        "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
      );
      await expect(page.getByTestId("decision8-reference-version")).toContainText(
        "PHX_ZTSI_REF_V1",
      );
      await expect(page.getByTestId("decision8-zone-geometry")).toContainText(
        FROZEN_GEOMETRY,
      );
      await expect(panel).not.toContainText("25 / 93");
      await expect(panel).not.toContainText("safe");
      await expect(page.getByTestId("source-banner")).toContainText("REPLAY");
      await expect(page.getByTestId("source-banner")).not.toContainText(
        "FORTYGUARD CACHED",
      );

      const map = page.getByTestId("map-stage");
      await expect(map).toHaveAttribute("data-map-state", "sufficient", {
        timeout: 30_000,
      });
      await expect(map).toHaveAttribute("data-geometry-feature-count", "25");
      await expect(map).toHaveAttribute("data-ranked-feature-count", "25");
      await expect(map).toHaveAttribute("data-map-source-count", "25");
      await expect(page.locator("body")).not.toContainText(
        "Fill intensity reflects backend-authorized thermal ordering",
      );
      await expect(page.locator("body")).not.toContainText(
        "Geometry and decision cards are not wired yet",
      );
    });
  });
});
