import { expect, test } from "@playwright/test";

test.describe("accessibility", () => {
  test("exposes landmarks, skip link, and keyboard map selection", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Decision questions" })).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("complementary", { name: "Action and direction" })).toBeVisible();
    await expect(page.getByRole("contentinfo")).toBeVisible();

    await page.keyboard.press("Tab");
    await expect(page.locator(".skip-link")).toBeFocused();

    const cell = page.locator('[data-area-id="area-3"]');
    await cell.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("selected-area")).toContainText("Analysis area 3");
  });
});
