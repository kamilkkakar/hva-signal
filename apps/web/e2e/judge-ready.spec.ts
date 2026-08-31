import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import {
  waitForMapState,
  waitForMapLoaded,
} from "./judge-ready.helpers";

const here = path.dirname(fileURLToPath(import.meta.url));
const framing = JSON.parse(
  readFileSync(path.join(here, "fixtures", "action-framing.json"), "utf8"),
) as {
  sufficient: {
    stamp: string;
    says: string;
    supports: string;
    does_not: string;
    kind: string;
  };
  insufficient: {
    stamp: string;
    says: string;
    supports: string;
    does_not: string;
    kind: string;
  };
  forbidden_phrases: string[];
};

test.describe("workspace Phoenix auto-load", () => {
  test.describe.configure({ timeout: 120_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("Phoenix auto-loads with map, zone panel, and spatial gate", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("workspace")).toBeVisible();
    await expect(page.getByTestId("explore-city")).toBeVisible();

    const map = await waitForMapState(page, "sufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "25");
    await expect(map).toHaveAttribute("data-geometry-feature-count", "25");

    await expect(page.getByTestId("zone-panel")).toBeVisible();
    await expect(page.getByTestId("zone-name")).toBeVisible();
    await expect(page.getByTestId("zone-temp")).toBeVisible();

    const gate = page.getByTestId("spatial-gate");
    await expect(gate).toBeVisible();

    await expect(page.getByTestId("observation-provenance")).toContainText("Published");
  });

  test("layer switching preserves zone selection", async ({ page }) => {
    await page.goto("/");
    const map = await waitForMapLoaded(page);
    await expect(map).toHaveAttribute("data-map-state", "sufficient", {
      timeout: 45_000,
    });

    const zoneName = await page.getByTestId("zone-name").textContent();
    expect(zoneName?.length).toBeGreaterThan(0);

    const canopyTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="TREE_CANOPY"]');
    if ((await canopyTab.count()) > 0) {
      await canopyTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "TREE_CANOPY");
      await expect(page.getByTestId("zone-name")).toHaveText(zoneName!);
    }

    const incomeTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]');
    if ((await incomeTab.count()) > 0) {
      await incomeTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "INCOME");
      await expect(page.getByTestId("zone-name")).toHaveText(zoneName!);
    }

    const thermalTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="THERMAL"]');
    if ((await thermalTab.count()) > 0) {
      await thermalTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "THERMAL");
      await expect(page.getByTestId("zone-name")).toHaveText(zoneName!);
    }
  });

  test("methods and analysis sections closed by default", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("workspace")).toBeVisible();
    await waitForMapLoaded(page);

    const methods = page.getByTestId("zone-methods");
    if ((await methods.count()) > 0) {
      const isOpen = await methods.evaluate(
        (el) => el instanceof HTMLDetailsElement && el.open,
      );
      expect(isOpen, "Methods should be closed by default").toBe(false);
    }

    const sections = [
      "matched-night-section",
      "observed-instants-section",
      "local-context-section",
      "all-zones-section",
    ];
    for (const testId of sections) {
      const section = page.getByTestId(testId);
      if ((await section.count()) > 0) {
        const isOpen = await section.evaluate(
          (el) => el instanceof HTMLDetailsElement && el.open,
        );
        expect(isOpen, `${testId} should be closed by default`).toBe(false);
      }
    }
  });
});
