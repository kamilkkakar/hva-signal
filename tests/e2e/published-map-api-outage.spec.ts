import { expect, test } from "@playwright/test";

for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 900 }]) {
  test(`published Phoenix retains 25 zones when geometry API is rate limited (${viewport.width}px)`, async ({ page }) => {
    await page.setViewportSize(viewport);
    let pilotGeometryRequests = 0;
    await page.route("**/api/v1/areas/phoenix-demo/geometry", async route => {
      pilotGeometryRequests += 1;
      await route.fulfill({ status: 429, body: "Too Many Requests" });
    });
    await page.goto("/");
    const stage = page.getByTestId("map-stage");
    await expect(page.getByTestId("obs-published")).toHaveAttribute("aria-checked", "true");
    await expect(stage).toHaveAttribute("data-geometry-feature-count", "25");
    await expect(stage).toHaveAttribute("data-ranked-feature-count", "25");
    await expect(stage).toHaveAttribute("data-map-state", "sufficient");
    await expect(page.getByText("No bindable zones.", { exact: false })).toHaveCount(0);
    expect(pilotGeometryRequests).toBe(0);
  });
}
