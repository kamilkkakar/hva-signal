import { expect, test } from "@playwright/test";
import {
  INSUFFICIENT_TIME,
  VIEWPORTS,
  expectNoPageHorizontalScroll,
  submitAnalysis,
  waitForDecision8,
} from "./judge-ready.helpers";

test.describe("judge-ready overflow / no page h-scroll", () => {
  test.describe.configure({ timeout: 90_000 });

  test("idle landing has no page-level horizontal scroll at 1024–1920", async ({
    page,
  }) => {
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "HVA-Signal" }),
      ).toBeVisible();
      await expect(page.locator('input[name="analysis_time"]')).toHaveValue(
        INSUFFICIENT_TIME,
      );
      await expectNoPageHorizontalScroll(page, `${width} idle`);
    }
  });

  test("2022-07-01 INSUFFICIENT result has no page-level horizontal scroll", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto("/");
    await expect(page.locator('input[name="analysis_time"]')).toHaveValue(
      INSUFFICIENT_TIME,
    );
    await submitAnalysis(page);

    const panel = await waitForDecision8(page);
    await expect(page.getByTestId("decision8-observed-s")).toContainText(
      "0.043966547192353",
    );
    await expect(page.getByTestId("decision8-zone-geometry")).toContainText(
      "US_CENSUS_TIGERLINE",
    );
    await expect(page.getByTestId("map-stage")).toHaveAttribute(
      "data-map-state",
      "insufficient",
      { timeout: 45_000 },
    );
    await expect(page.getByTestId("map-stage")).toHaveAttribute(
      "data-ranked-feature-count",
      "0",
    );

    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await expect(panel).toBeVisible();
      await expectNoPageHorizontalScroll(page, `${width} 2022-07-01`);
      const decision = page.getByRole("complementary", { name: "Decision panel" });
      if ((await decision.count()) > 0) {
        const decisionBox = await decision.evaluate((node) => ({
          scroll: node.scrollWidth,
          client: node.clientWidth,
        }));
        expect(decisionBox.scroll, `${width} decision rail`).toBeLessThanOrEqual(
          decisionBox.client + 1,
        );
      }
    }
  });
});
