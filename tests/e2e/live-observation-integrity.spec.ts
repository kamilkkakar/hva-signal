import { readFileSync } from "node:fs";
import { expect, test, type Page, type Route } from "@playwright/test";

const empty = JSON.parse(readFileSync(
  "apps/api/tests/fixtures/live/phoenix_2021_empty_response.json", "utf8",
));
function populated(city = "Phoenix", time = "2024-07-08T15:00:00", value = 38.5) {
  const body = structuredClone(empty);
  const cityDir = city === "Phoenix" ? "phoenix" : "tucson";
  const geometry = JSON.parse(readFileSync("data/areas/cross-city/" + cityDir + "/geometry.geojson", "utf8"));
  body.analysis = {
    ...body.analysis, city, local_datetime: time,
    source_tile_count: 25, bindable_temperature_values: 25,
    zones: geometry.features.map((feature: { properties: { GEOID: string } }) => ({
      zone_id: String(feature.properties.GEOID), temperature_c: value,
      tile_count: 1, coverage_status: "valid",
    })),
  };
  return body;
}
async function live(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("obs-live")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("obs-live").click();
  await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-loading", "false", { timeout: 60_000 });
  await expect(page.getByTestId("map-stage")).toHaveAttribute("data-bindable-temperature-values", "25");
  await expect(page.getByTestId("run-live")).toBeEnabled();
}

test.describe("live observation integrity", () => {
  test.describe.configure({ timeout: 120_000 });
  // Every selected-time POST is fulfilled here; these tests never purchase vendor data.
  test("date edits and an empty historical response preserve the accepted observation", async ({ page }) => {
    let calls = 0;
    await page.route("**/api/v1/live/selected-time", async (route) => {
      calls += 1;
      const request = route.request().postDataJSON();
      expect(request.local_datetime).toBe(calls === 1 ? "2024-07-08T15:00:00" : "2021-08-14T15:00:00");
      await route.fulfill({ json: calls === 1 ? populated() : empty });
    });
    await live(page);
    await page.getByTestId("run-live").click();
    await expect(page.getByTestId("live-status")).toHaveAttribute("data-state", "success");
    await expect(page.getByTestId("zone-temp")).toContainText("38.5");
    await page.getByLabel("Observation date", { exact: true }).fill("2021-08-14");
    await expect(page.getByTestId("observation-provenance")).toContainText("8 Jul 2024");
    await expect(page.getByTestId("zone-observation")).toContainText("8 Jul 2024");
    await page.getByTestId("run-live").click();
    await expect(page.getByTestId("live-status")).toHaveAttribute("data-state", "error");
    await expect(page.getByTestId("live-status")).toContainText("No usable zone temperatures");
    await expect(page.getByTestId("live-status")).toContainText("last successful observation");
    await expect(page.getByTestId("observation-provenance")).toContainText("8 Jul 2024");
    await expect(page.getByTestId("zone-temp")).toContainText("38.5");
    expect(calls).toBe(2);
  });

  test("partial data displays the response time and leaves the missing zone unfilled", async ({ page }) => {
    const partial = populated("Phoenix", "2021-08-14T15:00:00");
    partial.status = "partial_observation";
    partial.acquisition_status = "cache_hit";
    partial.analysis.zones[0] = { ...partial.analysis.zones[0], temperature_c: null, tile_count: 0, coverage_status: "missing" };
    partial.analysis.bindable_temperature_values = 24;
    partial.analysis.source_tile_count = 24;
    await page.route("**/api/v1/live/selected-time", (route) => route.fulfill({ json: partial }));
    await live(page);
    await page.getByLabel("Observation date", { exact: true }).fill("2021-08-14");
    await page.getByTestId("run-live").click();
    await expect(page.getByTestId("live-status")).toHaveAttribute("data-state", "partial");
    await expect(page.getByTestId("live-status")).toContainText("24 of 25");
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-bindable-temperature-values", "24");
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-contract", "partial");
    await expect(page.getByTestId("observation-provenance")).toContainText("14 Aug 2021");
    await expect(page.getByTestId("zone-observation")).toContainText("14 Aug 2021");
    await expect(page.getByTestId("detail-observation")).toHaveText("14 Aug 2021 · 15:00 local");
  });

  test("a late response from the previous city cannot replace the current result", async ({ page }) => {
    let hold!: (route: Route) => void;
    const pending = new Promise<Route>((resolve) => { hold = resolve; });
    await page.route("**/api/v1/live/selected-time", async (route) => {
      if (route.request().postDataJSON().city_id === "phoenix") {
        hold(route);
        return;
      }
      await route.fulfill({ json: populated("Tucson", "2024-07-08T15:00:00", 29.5) });
    });
    await live(page);
    await page.getByTestId("run-live").click();
    const old = await pending;
    await page.getByLabel("Select city", { exact: true }).selectOption("tucson-az");
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-loading", "false");
    await expect(page.getByTestId("run-live")).toBeEnabled();
    await page.getByTestId("run-live").click();
    await expect(page.getByTestId("zone-temp")).toContainText("29.5");
    const oldResponse = page.waitForResponse((response) =>
      response.url().includes("/live/selected-time") &&
      response.request().postDataJSON().city_id === "phoenix");
    await old.fulfill({ json: populated() });
    await oldResponse;
    await expect(page.getByTestId("live-status")).toHaveAttribute("data-state", "success");
    await expect(page.getByTestId("zone-temp")).toContainText("29.5");
    await expect(page.getByTestId("observation-provenance")).toContainText("Cached live result");
  });
});
