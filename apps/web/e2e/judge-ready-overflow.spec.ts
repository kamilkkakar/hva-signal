import { expect, test } from "@playwright/test";
import {
  VIEWPORTS,
  expectNoPageHorizontalScroll,
  waitForMapLoaded,
} from "./judge-ready.helpers";

test.describe("workspace overflow / no page h-scroll", () => {
  test.describe.configure({ timeout: 90_000 });

  test("idle landing has no page-level horizontal scroll at 1024–1920", async ({
    page,
  }) => {
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: /HVA-SIGNAL/i }),
      ).toBeVisible();
      await expect(page.getByTestId("workspace")).toBeVisible();
      await expectNoPageHorizontalScroll(page, `${width} idle`);
    }
  });

  test("Phoenix auto-loaded map result has no page-level horizontal scroll", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto("/");
    await expect(page.getByTestId("workspace")).toBeVisible();
    const map = await waitForMapLoaded(page);
    await expect(map).toHaveAttribute("data-map-state", "sufficient", {
      timeout: 45_000,
    });

    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await expect(map).toBeVisible();
      await expectNoPageHorizontalScroll(page, `${width} loaded`);
    }
  });
});
