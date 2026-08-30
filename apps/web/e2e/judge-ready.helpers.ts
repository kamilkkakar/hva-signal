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
    const shell = document.querySelector(".shell") ?? document.querySelector("[data-testid='judge-shell']");
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

export async function fillAnalysisTime(page: Page, value: string) {
  const input = page.locator('input[name="analysis_time"]');
  await input.fill(value);
  await expect(input).toHaveValue(value);
}

export async function submitAnalysis(page: Page) {
  await page.getByRole("button", { name: "Submit analysis" }).click();
}

export async function waitForMapState(
  page: Page,
  state: "sufficient" | "insufficient",
) {
  const map = page.getByTestId("map-stage");
  await expect(map).toHaveAttribute("data-map-state", state, { timeout: 45_000 });
  return map;
}

export async function openAdvancedDetails(page: Page) {
  const details = page.getByTestId("analysis-detail");
  await expect(details).toBeAttached({ timeout: 45_000 });
  if ((await details.getAttribute("open")) == null) {
    await page.getByTestId("advanced-technical-details").click();
  }
  await expect(details).toHaveAttribute("open", "");
}

export async function waitForDecision8(page: Page) {
  await openAdvancedDetails(page);
  const panel = page.getByTestId("decision8-evidence-panel");
  await expect(panel).toBeVisible({ timeout: 45_000 });
  return panel;
}
