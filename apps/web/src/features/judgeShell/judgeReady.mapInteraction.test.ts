import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const fixturePath = path.resolve(here, "../../../e2e/fixtures/i-map-zones.json");

const imap = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  _not_product_evidence: boolean;
  thermal_product_evidence: boolean;
  invented_mean_temperature_c: boolean;
  zone_ids: string[];
  contract: {
    hover_writes_selection: boolean;
    click_persists_after_hover_leave: boolean;
    same_geoid_click_toggles: boolean;
  };
};

type InteractionState = {
  hoverId: string | null;
  selectedId: string | null;
  layerActive: boolean;
  fitGeneration: number;
};

type Catalog = { zones: Array<{ geoid: string }>; fill_authorized?: boolean };

async function loadMapInteraction(): Promise<{
  reduceInteraction: (
    state: InteractionState,
    event: { type: string; geoid?: string | null },
    catalog: Catalog | null,
  ) => InteractionState;
  initialInteractionState: () => InteractionState;
  historicalCatalog?: (authorized: boolean) => Catalog;
} | null> {
  const stateFile = path.resolve(here, "../mapInteraction/state.ts");
  const fixturesFile = path.resolve(here, "../mapInteraction/fixtures.ts");
  if (!existsSync(stateFile)) {
    return null;
  }
  const state = (await import(pathToFileURL(stateFile).href)) as {
    reduceInteraction: (
      state: InteractionState,
      event: { type: string; geoid?: string | null },
      catalog: Catalog | null,
    ) => InteractionState;
    initialInteractionState: () => InteractionState;
  };
  let historicalCatalog: ((authorized: boolean) => Catalog) | undefined;
  if (existsSync(fixturesFile)) {
    const fixtures = (await import(pathToFileURL(fixturesFile).href)) as {
      historicalCatalog?: (authorized: boolean) => Catalog;
    };
    historicalCatalog = fixtures.historicalCatalog;
  }
  return { ...state, historicalCatalog };
}

describe("judgeShell I-MAP hover/click fixtures", () => {
  it("keeps I-MAP locator fixtures schematic and non-product", () => {
    expect(imap._not_product_evidence).toBe(true);
    expect(imap.thermal_product_evidence).toBe(false);
    expect(imap.invented_mean_temperature_c).toBe(false);
    expect(imap.zone_ids).toEqual([
      "FIX-0455000-01",
      "FIX-0455000-02",
      "FIX-0455000-03",
      "FIX-0455000-04",
      "FIX-0455000-05",
    ]);
    expect(JSON.stringify(imap)).not.toMatch(/fortyguard/i);
  });

  it("hover is transient and click persists when mapInteraction is present", async () => {
    const mod = await loadMapInteraction();
    if (!mod) {
      expect(imap.contract.hover_writes_selection).toBe(false);
      expect(imap.contract.click_persists_after_hover_leave).toBe(true);
      expect(imap.contract.same_geoid_click_toggles).toBe(true);
      return;
    }

    const first = imap.zone_ids[0];
    const second = imap.zone_ids[1];
    const catalog =
      mod.historicalCatalog?.(true) ??
      ({
        fill_authorized: true,
        zones: imap.zone_ids.map((geoid) => ({ geoid })),
      } as Catalog);

    let state = mod.initialInteractionState();
    state = mod.reduceInteraction(state, { type: "hover", geoid: first }, catalog);
    expect(state.hoverId).toBe(first);
    expect(state.selectedId).toBeNull();
    expect(imap.contract.hover_writes_selection).toBe(false);

    state = mod.reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    expect(state.hoverId).toBeNull();
    expect(state.selectedId).toBeNull();

    state = mod.reduceInteraction(state, { type: "select", geoid: first }, catalog);
    state = mod.reduceInteraction(state, { type: "hover", geoid: second }, catalog);
    state = mod.reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    expect(state.selectedId).toBe(first);
    expect(state.hoverId).toBeNull();

    state = mod.reduceInteraction(state, { type: "select", geoid: first }, catalog);
    expect(state.selectedId).toBeNull();
  });
});
