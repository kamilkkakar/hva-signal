import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import {
  SUFFICIENT_TIME,
  fillAnalysisTime,
  submitAnalysis,
  waitForMapState,
} from "./judge-ready.helpers";

const here = path.dirname(fileURLToPath(import.meta.url));
const imap = JSON.parse(
  readFileSync(path.join(here, "fixtures", "i-map-zones.json"), "utf8"),
) as {
  _not_product_evidence: boolean;
  zone_ids: string[];
  contract: {
    hover_writes_selection: boolean;
    click_persists_after_hover_leave: boolean;
    same_geoid_click_toggles: boolean;
  };
};

test.describe("judge-ready map hover/click", () => {
  test.describe.configure({ timeout: 90_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("I-MAP fixture hover is transient and click persists when chrome is mounted", async ({
    page,
  }) => {
    expect(imap._not_product_evidence).toBe(true);
    expect(imap.zone_ids).toHaveLength(5);
    expect(imap.contract.hover_writes_selection).toBe(false);
    expect(imap.contract.click_persists_after_hover_leave).toBe(true);

    await page.goto("/");
    await fillAnalysisTime(page, SUFFICIENT_TIME);
    await submitAnalysis(page);
    const map = await waitForMapState(page, "sufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "25");

    const chrome = page.getByTestId("map-interaction-chrome");
    const table = page.getByTestId("map-interaction-table");
    if ((await chrome.count()) === 0 || (await table.count()) === 0) {
      test.info().annotations.push({
        type: "note",
        description:
          "I-MAP chrome not mounted; MapStage hover chip stays off at rest.",
      });
      await expect(page.getByTestId("map-hover")).toHaveCount(0);
      await expect(chrome).toHaveCount(0);
      return;
    }

    const first = imap.zone_ids[0];
    const second = imap.zone_ids[1];
    const firstRow = table.locator(`tr[data-geoid="${first}"]`);
    if ((await firstRow.count()) === 0) {
      test.info().annotations.push({
        type: "note",
        description:
          "I-MAP fixture GEOIDs are schematic; live Phoenix tracts are not FIX-* cells.",
      });
      const liveButton = page
        .getByTestId("map-interaction-list")
        .locator("button")
        .first();
      await expect(liveButton).toBeVisible();
      await liveButton.click();
      await expect(page.getByTestId("map-interaction-detail")).toHaveAttribute(
        "data-has-selection",
        "true",
      );
      const selectedId = (await page.getByTestId("detail-geoid").textContent()) ?? "";
      expect(selectedId.length).toBeGreaterThan(0);
      await page.mouse.move(0, 0);
      await expect(page.getByTestId("detail-geoid")).toHaveText(selectedId);
      await liveButton.click();
      await expect(page.getByTestId("map-interaction-detail")).toHaveAttribute(
        "data-has-selection",
        "false",
      );
      return;
    }

    await firstRow.locator("button").click();
    await expect(page.getByTestId("detail-geoid")).toHaveText(first);
    await expect(firstRow).toHaveAttribute("data-selected", "true");

    if ((await table.locator(`tr[data-geoid="${second}"]`).count()) > 0) {
      await table.locator(`tr[data-geoid="${second}"]`).hover();
    }
    await page.mouse.move(0, 0);
    await expect(page.getByTestId("detail-geoid")).toHaveText(first);

    await firstRow.locator("button").click();
    await expect(page.getByTestId("map-interaction-detail")).toHaveAttribute(
      "data-has-selection",
      "false",
    );
  });
});
