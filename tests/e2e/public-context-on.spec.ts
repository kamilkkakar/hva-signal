import { expect, test, type Page } from "@playwright/test";

const CONTEXT_ON = /^(1|true|yes|on)$/i.test(
  (process.env.HVA_PUBLIC_CONTEXT ?? "").trim(),
);

async function waitForWorkspaceMap(page: Page) {
  await expect(page.getByTestId("workspace")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("explore-city")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("map-stage")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("map-stage")).not.toHaveAttribute(
    "data-geometry-feature-count",
    "0",
    { timeout: 60_000 },
  );
}

test.describe("workspace HVA_PUBLIC_CONTEXT=1", () => {
  test.describe.configure({ timeout: 120_000 });
  test.use({ timezoneId: "America/Phoenix" });
  test.skip(!CONTEXT_ON, "skipped unless HVA_PUBLIC_CONTEXT=1");

  test("workspace loads with zone panel and provenance", async ({ page }) => {
    await page.goto("/");
    await waitForWorkspaceMap(page);
    await expect(page.getByRole("heading", { name: /HVA-SIGNAL/i })).toBeVisible();

    await expect(page.getByTestId("zone-panel")).toBeVisible();
    await expect(page.getByTestId("zone-name")).toBeVisible();
    await expect(page.getByTestId("observation-provenance")).toBeVisible();

    const map = page.getByTestId("map-stage");
    await expect(map).toHaveAttribute("data-map-state", "sufficient", {
      timeout: 60_000,
    });
    await expect(map).toHaveAttribute("data-ranked-feature-count", "25");
    await expect(map).toHaveAttribute("data-geometry-feature-count", "25");

    const incomeTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]');
    if ((await incomeTab.count()) > 0) {
      await incomeTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "INCOME");
      await expect(page.getByTestId("zone-panel")).toBeVisible();
    }

    const blob = ((await page.locator("body").innerText()) ?? "").toLowerCase();
    expect(blob, "TEST_ONLY").not.toContain("test_only");
    expect(blob, "NO COOLING SITE").not.toContain("no cooling site");
  });
});
