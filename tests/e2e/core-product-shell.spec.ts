/**
 * Anti-lost-UI gate: core product shell must never disappear.
 * Contract: docs/release/CORE_UI_CONTRACT.json (spec §0A.4)
 */
import { expect, test, type Page } from "@playwright/test";

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

test.describe("core product shell never disappears", () => {
  test.describe.configure({ timeout: 180_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("Explore City retains contract shell", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);

    // Machine-readable shell marker for contract consumers
    await expect(page.getByTestId("workspace")).toHaveAttribute(
      "data-core-product-shell",
      "present",
    );

    await expect(page.getByTestId("workspace-header")).toBeVisible();
    await expect(page.getByRole("heading", { name: /HVA-SIGNAL/i })).toBeVisible();
    await expect(page.getByTestId("mode-explore")).toBeVisible();
    await expect(page.getByTestId("mode-compare")).toBeVisible();
    await expect(page.getByTestId("city-selector")).toBeVisible();
    await expect(page.getByTestId("obs-published")).toBeVisible();
    await expect(page.getByTestId("obs-live")).toBeVisible();

    const citySelect = page.getByTestId("city-selector").locator("select");
    for (const city of ["phoenix-az", "las-vegas-nv", "tucson-az", "los-angeles-ca"]) {
      await expect(citySelect.locator(`option[value="${city}"]`)).toHaveCount(1);
    }

    await expect(page.getByTestId("map-stage")).toBeVisible();
    await expect(page.getByTestId("zone-panel")).toBeVisible();
    await expect(page.getByTestId("zone-name")).toBeVisible();
    await expect(page.getByTestId("zone-methods")).toBeVisible();

    const tabs = page.getByTestId("map-mode-tabs");
    await expect(tabs.locator('[data-mode="THERMAL"]')).toBeVisible();
    await expect(tabs.locator('[data-mode="TREE_CANOPY"]')).toBeVisible();
    await expect(tabs.locator('[data-mode="INCOME"]')).toBeVisible();
    await expect(tabs.locator('[data-mode="OLDER_HOUSING"]')).toBeVisible();

    await page.getByTestId("obs-live").click();
    await expect(page.getByTestId("live-controls")).toBeVisible();
    await page.getByTestId("obs-published").click();
  });

  test("Compare Cities retains contract shell", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);

    await page.getByTestId("mode-compare").click();
    await expect(page.getByTestId("compare-cities")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("cross-city-section")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("cross-city-bubble-explorer")).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByTestId("cross-city-axis-controls")).toBeVisible();
    await expect(page.getByTestId("cross-city-fill-controls")).toBeVisible();
    await expect(page.getByTestId("cross-city-summary")).toContainText("cities", {
      timeout: 60_000,
    });

    // tooltip behavior still available
    const bubble = page.locator("[data-testid='cross-city-bubble-explorer'] circle").first();
    if ((await bubble.count()) > 0) {
      await bubble.hover({ force: true });
      await expect(page.getByTestId("cross-city-tooltip")).toBeVisible();
    }

    // city focus / isolate still available
    const isolate = page.getByRole("button", { name: /Only show Phoenix/i });
    if ((await isolate.count()) > 0) {
      await isolate.click();
      const showAll = page.getByRole("button", { name: "Show all" });
      await expect(showAll).toBeVisible();
      await showAll.click();
    }

    // return to Explore — shell still present
    await page.getByTestId("mode-explore").click();
    await expect(page.getByTestId("explore-city")).toBeVisible();
    await expect(page.getByTestId("workspace")).toHaveAttribute(
      "data-core-product-shell",
      "present",
    );
  });
});
