import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import {
  BACKEND_ORDERING_COPY,
  INSUFFICIENT_TIME,
  SUFFICIENT_TIME,
  fillAnalysisTime,
  submitAnalysis,
  waitForDecision8,
  waitForMapState,
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

async function expectActionFraming(
  page: Page,
  expected: (typeof framing)["sufficient"] | (typeof framing)["insufficient"],
) {
  const card = page.getByTestId("action-v0");
  if ((await card.count()) === 0) {
    return false;
  }
  await expect(card).toBeVisible();
  await expect(card).toHaveAttribute("data-action-kind", expected.kind);
  await expect(page.getByTestId("action-v0-stamp")).toHaveText(expected.stamp);
  await expect(page.getByTestId("action-v0-says")).toHaveText(expected.says);
  await expect(page.getByTestId("action-v0-supports")).toHaveText(
    expected.supports,
  );
  await expect(page.getByTestId("action-v0-does-not")).toHaveText(
    expected.does_not,
  );
  const blob = ((await card.textContent()) ?? "").toLowerCase();
  for (const phrase of framing.forbidden_phrases) {
    expect(blob, phrase).not.toContain(phrase);
  }
  return true;
}

test.describe("judge-ready Phoenix sequence", () => {
  test.describe.configure({ timeout: 120_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("sufficient 2022-06-30 then 2022-07-01 insufficient chrome disappears", async ({
    page,
  }) => {
    await page.goto("/");
    await fillAnalysisTime(page, SUFFICIENT_TIME);
    await submitAnalysis(page);

    const panel = await waitForDecision8(page);
    await expect(page.getByTestId("decision8-observed-s")).toContainText(
      "0.135483870967741",
    );
    const map = await waitForMapState(page, "sufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "25");
    await expect(map).toHaveAttribute("data-geometry-feature-count", "25");
    await expect(page.locator("body")).toContainText(BACKEND_ORDERING_COPY);
    await expect(page.getByTestId("evidence-state")).toHaveText("READY");
    await expect(page.getByTestId("map-hover")).toHaveCount(0);
    const actionOnSufficient = await expectActionFraming(
      page,
      framing.sufficient,
    );

    await fillAnalysisTime(page, INSUFFICIENT_TIME);
    await submitAnalysis(page);

    await expect(page.getByTestId("decision8-observed-s")).toContainText(
      "0.043966547192353",
      { timeout: 45_000 },
    );
    await expect(panel).toBeVisible();
    const withheld = await waitForMapState(page, "insufficient");
    await expect(withheld).toHaveAttribute("data-ranked-feature-count", "0");
    await expect(withheld).toHaveAttribute("data-geometry-feature-count", "25");
    await expect(page.locator("body")).not.toContainText(BACKEND_ORDERING_COPY);
    await expect(page.getByTestId("evidence-state")).toHaveText(
      "INSUFFICIENT_EVIDENCE",
    );
    await expect(page.getByTestId("map-hover")).toHaveCount(0);
    await expect(page.getByTestId("decision8-suppression-reason")).toBeVisible();

    if (actionOnSufficient || (await page.getByTestId("action-v0").count()) > 0) {
      await expectActionFraming(page, framing.insufficient);
      await expect(page.getByTestId("action-v0-stamp")).not.toHaveText(
        framing.sufficient.stamp,
      );
    }
  });

  test("Action framing copy matches the 06-30 / 07-01 lock when mounted", async ({
    page,
  }) => {
    await page.goto("/");
    await fillAnalysisTime(page, SUFFICIENT_TIME);
    await submitAnalysis(page);
    await waitForMapState(page, "sufficient");

    const card = page.getByTestId("action-v0");
    if ((await card.count()) === 0) {
      test.info().annotations.push({
        type: "note",
        description: "Action v0 not mounted on this image; copy lock is unit-tested.",
      });
      await expect(card).toHaveCount(0);
      return;
    }

    await expectActionFraming(page, framing.sufficient);

    await fillAnalysisTime(page, INSUFFICIENT_TIME);
    await submitAnalysis(page);
    await waitForMapState(page, "insufficient");
    await expectActionFraming(page, framing.insufficient);
    await expect(page.getByTestId("action-v0")).not.toContainText(
      framing.sufficient.stamp,
    );
  });
});
