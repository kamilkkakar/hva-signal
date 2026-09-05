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

    // Published remains the default. Bounded Live is an explicit user action;
    // opening its controls must not submit a provider request.
    await expect(page.getByTestId("obs-published")).toHaveAttribute("aria-checked", "true");
    await expect(page.getByTestId("obs-live")).toBeVisible();
    await expect(page.getByTestId("live-controls")).toHaveCount(0);
    await page.getByTestId("obs-live").click();
    await expect(page.getByTestId("live-controls")).toBeVisible();
    await expect(page.getByTestId("live-city-search")).toBeVisible();
    await expect(page.getByTestId("run-live")).toBeVisible();
    await page.getByTestId("obs-published").click();
    await expect(page.getByTestId("live-controls")).toHaveCount(0);

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
  });

  test("Compare Cities retains contract shell", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);

    await page.getByTestId("mode-compare").click();
    await expect(page.getByTestId("compare-cities")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("cross-city-section")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("compare-lens-tabs")).toBeVisible();
    await expect(page.getByTestId("compare-snapshot-lens")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("compare-shared-scale")).toBeVisible();

    // Context lens preserves scatter + axis/fill controls
    await page.getByTestId("compare-lens-context").click();
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

  test("no WebGL keeps the evidence and decision path usable", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
        configurable: true,
        value: () => null,
      });
    });
    await page.goto("/");

    await expect(page.getByTestId("workspace")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("map-renderer-fallback")).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByTestId("map-interaction-stage")).toHaveAttribute(
      "data-map-renderer",
      "unavailable",
    );
    await expect(page.getByTestId("zone-panel")).toBeVisible();
    await expect(page.getByTestId("map-interaction-chrome")).toBeVisible();
    await expect(page.getByTestId("map-fit-aoi")).toBeDisabled();
  });

  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    test(`shared chart and comparison colours resolve at ${viewport.width}px`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto("/");
      await waitForWorkspaceMap(page);

      // These charts live under .ws, not the legacy .hx-app theme root.
      const nightAxis = page.getByTestId("matched-night-section").locator(".hx-axis-line").first();
      await expect(nightAxis).toHaveCSS("stroke", "rgb(28, 36, 32)", { timeout: 60_000 });

      await page.getByTestId("mode-compare").click();
      const snapshotTab = page.getByTestId("compare-lens-snapshot");
      await expect(snapshotTab).toHaveAttribute("aria-selected", "true");
      await expect(snapshotTab).toHaveCSS("background-color", "rgb(36, 56, 51)");
      await expect(snapshotTab).toHaveCSS("color", "rgb(247, 248, 245)");
      await snapshotTab.hover();
      await expect(snapshotTab).toHaveCSS("background-color", "rgb(36, 56, 51)");

      const contextTab = page.getByTestId("compare-lens-context");
      await contextTab.click();
      await expect(contextTab).toHaveCSS("background-color", "rgb(36, 56, 51)");
      await expect(contextTab).toHaveCSS("color", "rgb(247, 248, 245)");
      await page.mouse.move(0, 0);
      await expect(contextTab).toHaveCSS("background-color", "rgb(36, 56, 51)");

      const fill = page.getByTestId("cross-city-fill-controls");
      for (const label of ["Tree canopy", "Temperature"]) {
        const button = fill.getByRole("button", { name: label, exact: true });
        await button.click();
        await expect(button).toHaveAttribute("aria-pressed", "true");
        await expect(button).toHaveCSS("background-color", "rgb(36, 56, 51)");
        await expect(button).toHaveCSS("color", "rgb(247, 248, 245)");
        await page.mouse.move(0, 0);
        await expect(button).toHaveCSS("background-color", "rgb(36, 56, 51)");
      }

      const chart = page.getByTestId("cross-city-bubble-explorer");
      await expect(chart.locator(".hx-axis-line").first()).toHaveCSS("stroke", "rgb(28, 36, 32)");
      await expect(chart.locator(".hx-axis-tick").first()).toHaveCSS("stroke", "rgb(28, 36, 32)");
      await expect(chart.locator(".hx-axis-title").first()).toHaveCSS("fill", "rgb(92, 107, 99)");
    });
  }
});
