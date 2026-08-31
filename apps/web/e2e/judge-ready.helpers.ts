import { expect, type Page } from "@playwright/test";

export const VIEWPORTS = [1920, 1440, 1280, 1024] as const;

export const BACKEND_ORDERING_COPY =
  "Fill intensity reflects backend-authorized thermal ordering";

export const INSUFFICIENT_TIME = "2022-07-01T03:00";
export const SUFFICIENT_TIME = "2022-06-30T03:00";

export type PageBox = {
  rootScroll: number;
  rootClient: number;
  bodyScroll: number;
  bodyClient: number;
  shellScroll: number;
  shellClient: number;
};

export async function pageBox(page: Page): Promise<PageBox> {
  return page.evaluate(() => {
    const root = document.documentElement;
    const shell =
      document.querySelector("[data-testid='workspace']") ??
      document.querySelector(".ws") ??
      document.querySelector(".shell") ??
      document.querySelector("[data-testid='judge-shell']");
    return {
      rootScroll: root.scrollWidth,
      rootClient: root.clientWidth,
      bodyScroll: document.body.scrollWidth,
      bodyClient: document.body.clientWidth,
      shellScroll: shell instanceof HTMLElement ? shell.scrollWidth : 0,
      shellClient: shell instanceof HTMLElement ? shell.clientWidth : 0,
    };
  });
}

export function expectNoPageHScroll(box: PageBox, label: string) {
  expect(box.rootScroll, `${label} documentElement`).toBeLessThanOrEqual(
    box.rootClient + 1,
  );
  expect(box.bodyScroll, `${label} body`).toBeLessThanOrEqual(box.bodyClient + 1);
  if (box.shellClient > 0) {
    expect(box.shellScroll, `${label} shell`).toBeLessThanOrEqual(
      box.shellClient + 1,
    );
  }
}

export async function expectNoPageHorizontalScroll(page: Page, label: string) {
  expectNoPageHScroll(await pageBox(page), label);
}

async function openDetails(page: Page, testId: string) {
  const details = page.getByTestId(testId);
  if ((await details.count()) === 0) {
    return;
  }
  await details.evaluate((node) => {
    if (node instanceof HTMLDetailsElement) {
      node.open = true;
    }
  });
  await expect(details).toHaveAttribute("open", "");
}

export async function openDemoControls(page: Page) {
  await openDetails(page, "demo-controls");
}

export async function openEvidenceDisclosure(page: Page) {
  await openDetails(page, "evidence-disclosure");
}

export async function fillAnalysisTime(page: Page, value: string) {
  const input = page.locator('input[name="analysis_time"]');
  if ((await input.count()) === 0) return;
  await openDemoControls(page);
  await input.fill(value);
  await expect(input).toHaveValue(value);
}

export async function submitAnalysis(page: Page) {
  const btn = page.getByRole("button", { name: "Submit analysis" });
  if ((await btn.count()) === 0) return;
  await openDemoControls(page);
  await btn.click();
}

export async function waitForWorkspaceReady(page: Page) {
  await expect(page.getByTestId("workspace")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("explore-city")).toBeVisible({ timeout: 15_000 });
}

export async function waitForMapLoaded(page: Page) {
  const map = page.getByTestId("map-stage");
  await expect(map).toBeVisible({ timeout: 30_000 });
  await expect(map).not.toHaveAttribute("data-geometry-feature-count", "0", {
    timeout: 60_000,
  });
  return map;
}

export async function waitForMapState(
  page: Page,
  state: "sufficient" | "insufficient",
) {
  const map = page.getByTestId("map-stage");
  await expect(map).toHaveAttribute("data-map-state", state, { timeout: 45_000 });
  return map;
}

export async function openMapAdvancedChrome(page: Page) {
  const wrap = page.getByTestId("map-advanced-chrome");
  if ((await wrap.count()) === 0) {
    return;
  }
  if ((await wrap.getAttribute("open")) == null) {
    await wrap.locator("summary").first().click();
  }
  await expect(wrap).toHaveAttribute("open", "");
}

export async function openZoneIdentifierList(page: Page) {
  await openMapAdvancedChrome(page);
  const wrap = page.getByTestId("map-interaction-list-wrap");
  if ((await wrap.count()) === 0) return;
  if ((await wrap.getAttribute("open")) == null) {
    await wrap.locator("summary").first().click();
  }
  await expect(wrap).toHaveAttribute("open", "");
}

export async function openAdvancedDetails(page: Page) {
  await openEvidenceDisclosure(page);
  const details = page.getByTestId("analysis-detail");
  if ((await details.count()) === 0) return;
  await expect(details).toBeAttached({ timeout: 45_000 });
  if ((await details.getAttribute("open")) == null) {
    await page.getByTestId("advanced-technical-details").click();
  }
  await expect(details).toHaveAttribute("open", "");
}

export async function waitForDecision8(page: Page) {
  const panel = page.getByTestId("decision8-evidence-panel");
  if ((await panel.count()) === 0) return panel;
  await openAdvancedDetails(page);
  await expect(panel).toBeVisible({ timeout: 45_000 });
  return panel;
}
