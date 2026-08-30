import path from "node:path";
import { expect, test } from "@playwright/test";

const out = path.join(process.cwd(), "screenshots");

test.describe("screenshots", () => {
  test("captures pending public states", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("decision-shell")).toBeVisible();
    await page.screenshot({
      path: path.join(out, "01-at-this-time-pending.png"),
      fullPage: true,
    });

    await page.locator('[data-area-id="area-12"]').click();
    await page.screenshot({
      path: path.join(out, "02-area-12-selected-pending.png"),
      fullPage: true,
    });

    await page.getByTestId("question-month-season").click();
    await page.screenshot({
      path: path.join(out, "03-month-season-pending.png"),
      fullPage: true,
    });

    await page.getByTestId("question-after-intervention").click();
    await page.screenshot({
      path: path.join(out, "04-intervention-pending.png"),
      fullPage: true,
    });

    await page.getByTestId("question-capacity-to-cope").click();
    await page.screenshot({
      path: path.join(out, "05-vulnerability-context.png"),
      fullPage: true,
    });

    await page.getByTestId("question-evidence-next").click();
    await page.screenshot({
      path: path.join(out, "06-direction-next.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByTestId("question-at-this-time").click();
    await page.screenshot({
      path: path.join(out, "07-mobile-pending.png"),
      fullPage: true,
    });
  });
});
